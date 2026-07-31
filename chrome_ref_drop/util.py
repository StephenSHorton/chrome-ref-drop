"""Shared helpers: resolve sources, download URLs, create reference empties."""

from __future__ import annotations

import base64
import hashlib
import mimetypes
import os
import re
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlparse

import bpy
from mathutils import Vector

IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".jpe",
    ".jfif",
    ".webp",
    ".bmp",
    ".gif",
    ".tif",
    ".tiff",
    ".hdr",
    ".exr",
    ".tga",
    ".svg",
}

# FileHandler bl_file_extensions uses semicolon-separated list
FILEHANDLER_EXTENSIONS = (
    ".png;.jpg;.jpeg;.jpe;.jfif;.webp;.bmp;.gif;.tif;.tiff;.hdr;.exr;.tga"
)

_URL_RE = re.compile(r"^https?://", re.IGNORECASE)
_DATA_URL_RE = re.compile(
    r"^data:(image/([a-z0-9.+-]+));base64,(.+)$",
    re.IGNORECASE | re.DOTALL,
)

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36 ChromeRefDrop/0.1"
)


def get_prefs(context=None):
    context = context or bpy.context
    addon = context.preferences.addons.get(__package__)
    if addon:
        return addon.preferences
    return None


def cache_dir() -> Path:
    prefs = get_prefs()
    if prefs and prefs.cache_dir.strip():
        path = Path(bpy.path.abspath(prefs.cache_dir)).expanduser()
    else:
        path = Path(tempfile.gettempdir()) / "chrome_ref_drop"
    path.mkdir(parents=True, exist_ok=True)
    return path


def is_http_url(text: str) -> bool:
    return bool(text and _URL_RE.match(text.strip()))


def is_data_url(text: str) -> bool:
    return bool(text and text.strip().lower().startswith("data:image"))


def looks_like_image_path(path: str) -> bool:
    if not path:
        return False
    ext = Path(path.split("?", 1)[0].split("#", 1)[0]).suffix.lower()
    return ext in IMAGE_EXTENSIONS


def extract_url_from_text(text: str) -> Optional[str]:
    """Pull the first http(s) image-ish URL out of clipboard/HTML snippets."""
    if not text:
        return None
    text = text.strip()
    if is_http_url(text) or is_data_url(text):
        return text.splitlines()[0].strip()

    # text/uri-list style
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#"):
            continue
        if is_http_url(line) or is_data_url(line):
            return line

    # HTML fragment from browsers: <img src="...">
    m = re.search(
        r"""(?i)(?:src|href)\s*=\s*["'](https?://[^"']+|data:image[^"']+)["']""",
        text,
    )
    if m:
        return m.group(1)

    # bare URL somewhere in the text
    m = re.search(r"https?://[^\s<>\"']+", text)
    if m:
        return m.group(0).rstrip(").,;]")
    return None


def _ext_from_content_type(content_type: str) -> str:
    if not content_type:
        return ".png"
    ct = content_type.split(";")[0].strip().lower()
    mapping = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
        "image/bmp": ".bmp",
        "image/tiff": ".tiff",
        "image/svg+xml": ".svg",
        "image/x-icon": ".ico",
        "image/vnd.microsoft.icon": ".ico",
    }
    if ct in mapping:
        return mapping[ct]
    guessed = mimetypes.guess_extension(ct)
    return guessed or ".png"


def _filename_from_url(url: str, ext: str) -> str:
    parsed = urlparse(url)
    name = Path(unquote(parsed.path)).name
    if name and Path(name).suffix:
        stem = Path(name).stem
        return f"{stem}{ext}" if not Path(name).suffix.lower() in IMAGE_EXTENSIONS else name
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
    return f"browser_{digest}{ext}"


def download_data_url(url: str) -> Path:
    m = _DATA_URL_RE.match(url.strip())
    if not m:
        raise ValueError("Unsupported data URL (expected data:image/...;base64,...)")
    mime = m.group(1).lower()
    ext = _ext_from_content_type(mime)
    raw = base64.b64decode(m.group(3))
    digest = hashlib.sha1(raw).hexdigest()[:12]
    out = cache_dir() / f"data_{digest}{ext}"
    if not out.exists():
        out.write_bytes(raw)
    return out


def download_http_url(url: str, timeout: float = 30.0) -> Path:
    """Download an image URL into the cache dir. Returns local path."""
    if is_data_url(url):
        return download_data_url(url)
    if url.lower().startswith("blob:"):
        raise ValueError(
            "blob: URLs cannot be downloaded from Blender. "
            "Right-click the image → Copy image, then use Paste as Reference."
        )

    url = url.strip()
    # Prefer a stable cache key
    key = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
    # Probe existing cache with any known extension
    for ext in IMAGE_EXTENSIONS:
        candidate = cache_dir() / f"url_{key}{ext}"
        if candidate.exists() and candidate.stat().st_size > 0:
            return candidate

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": _USER_AGENT,
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content_type = resp.headers.get("Content-Type", "")
            data = resp.read()
            final_url = resp.geturl()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} downloading image: {url}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error downloading image: {e.reason}") from e

    if not data:
        raise RuntimeError("Downloaded image was empty")

    # Reject obvious HTML error pages
    head = data[:256].lstrip().lower()
    if head.startswith(b"<!doctype html") or head.startswith(b"<html"):
        raise RuntimeError(
            "URL returned HTML, not an image. Try 'Copy image address' on the actual image."
        )

    ext = _ext_from_content_type(content_type)
    # Prefer extension from final URL path when content-type is generic
    url_ext = Path(urlparse(final_url).path).suffix.lower()
    if url_ext in IMAGE_EXTENSIONS and content_type in ("", "application/octet-stream"):
        ext = url_ext

    # Sniff magic bytes if needed
    if ext == ".png" and data[:3] == b"\xff\xd8\xff":
        ext = ".jpg"
    elif data[:8] == b"\x89PNG\r\n\x1a\n":
        ext = ".png"
    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        ext = ".webp"
    elif data[:6] in (b"GIF87a", b"GIF89a"):
        ext = ".gif"

    out = cache_dir() / f"url_{key}{ext}"
    out.write_bytes(data)
    return out


def resolve_to_local_image(source: str) -> Path:
    """
    Resolve a drop/paste source to a local image file path.

    Accepts: local path, http(s) URL, data:image URL, or text containing a URL.
    """
    if not source:
        raise ValueError("Empty image source")

    source = source.strip().strip('"')

    # Windows file URL
    if source.lower().startswith("file:"):
        parsed = urlparse(source)
        # file:///C:/path or file://localhost/C:/path
        path = unquote(parsed.path)
        if re.match(r"^/[A-Za-z]:", path):
            path = path[1:]
        path = path.replace("/", os.sep)
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(f"file URL not found: {source}")
        return p

    if is_data_url(source) or is_http_url(source):
        return download_http_url(source)

    maybe_url = extract_url_from_text(source)
    if maybe_url and (is_http_url(maybe_url) or is_data_url(maybe_url)):
        return download_http_url(maybe_url)

    # Local filesystem path
    p = Path(bpy.path.abspath(source)).expanduser()
    if p.is_file():
        return p

    raise FileNotFoundError(f"Could not resolve image source: {source[:200]}")


def find_view3d(context):
    """Return (window, area, region, space, region_3d) for a VIEW_3D, preferring context."""
    if (
        context.area
        and context.area.type == "VIEW_3D"
        and context.region
        and context.space_data
        and context.space_data.type == "VIEW_3D"
    ):
        return (
            context.window,
            context.area,
            context.region,
            context.space_data,
            context.space_data.region_3d,
        )

    for window in context.window_manager.windows:
        screen = window.screen
        if not screen:
            continue
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            space = area.spaces.active
            if not space or space.type != "VIEW_3D":
                continue
            region = None
            for r in area.regions:
                if r.type == "WINDOW":
                    region = r
                    break
            if region is None:
                continue
            return window, area, region, space, space.region_3d
    return None, None, None, None, None


def placement_for_reference(context, align_to_view: bool = True):
    """Return (location Vector, rotation Quaternion) for a new reference empty."""
    from mathutils import Quaternion

    location = context.scene.cursor.location.copy()
    rotation = Quaternion((1, 0, 0, 0))

    _w, _a, _r, _space, r3d = find_view3d(context)
    if r3d is None:
        return location, rotation

    if align_to_view:
        # Match empty_image_add align='VIEW': face the viewport
        rotation = r3d.view_matrix.to_3x3().inverted().to_quaternion()

    # If cursor is at origin default and we have a view, place near view focus
    prefs = get_prefs(context)
    use_view_loc = prefs.place_at_view if prefs else True
    if use_view_loc:
        # Prefer 3D cursor when user moved it; else view location
        cursor = context.scene.cursor.location
        if cursor.length_squared < 1e-12:
            location = r3d.view_location.copy()
        else:
            location = cursor.copy()

    return location, rotation


def create_reference_empty(
    context,
    image_path: str | Path,
    *,
    name: Optional[str] = None,
    size: Optional[float] = None,
    align_to_view: bool = True,
    use_alpha: bool = True,
    depth: str = "DEFAULT",
) -> bpy.types.Object:
    """Load an image and create an IMAGE empty (reference) linked to the scene."""
    image_path = Path(image_path)
    if not image_path.is_file():
        raise FileNotFoundError(str(image_path))

    prefs = get_prefs(context)
    if size is None:
        size = prefs.default_size if prefs else 5.0
    if depth == "DEFAULT":
        depth = prefs.image_depth if prefs else "DEFAULT"

    img = bpy.data.images.load(str(image_path), check_existing=True)
    # Pack optional? keep external so reloads work; user can pack manually

    obj_name = name or Path(img.name).stem or "Reference"
    # Avoid unhelpfully long names from query-string downloads
    if len(obj_name) > 60:
        obj_name = obj_name[:57] + "..."

    ob = bpy.data.objects.new(obj_name, None)
    ob.empty_display_type = "IMAGE"
    ob.data = img
    ob.empty_display_size = float(size)
    ob.use_empty_image_alpha = use_alpha
    if depth and depth != "DEFAULT":
        # BACK / FRONT / DEFAULT
        try:
            ob.empty_image_depth = depth
        except (TypeError, ValueError):
            pass

    location, rotation = placement_for_reference(context, align_to_view=align_to_view)
    ob.location = location
    if align_to_view:
        ob.rotation_mode = "QUATERNION"
        ob.rotation_quaternion = rotation

    # Link to active collection
    coll = context.collection or context.scene.collection
    coll.objects.link(ob)

    # Select new empty
    for obj in context.selected_objects:
        obj.select_set(False)
    ob.select_set(True)
    context.view_layer.objects.active = ob

    return ob


def write_bytes_as_image(data: bytes, preferred_ext: str = ".png") -> Path:
    """Write raw image bytes to the cache and return the path (sniffs format)."""
    if not data:
        raise ValueError("No image data")
    ext = preferred_ext
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        ext = ".png"
    elif data[:3] == b"\xff\xd8\xff":
        ext = ".jpg"
    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        ext = ".webp"
    elif data[:6] in (b"GIF87a", b"GIF89a"):
        ext = ".gif"
    elif data[:2] == b"BM":
        ext = ".bmp"

    digest = hashlib.sha1(data).hexdigest()[:12]
    out = cache_dir() / f"clip_{digest}{ext}"
    if not out.exists():
        out.write_bytes(data)
    return out
