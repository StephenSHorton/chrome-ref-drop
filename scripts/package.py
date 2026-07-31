#!/usr/bin/env python3
"""Build an installable Blender extension zip + optional static repo index.

The archive root is the `chrome_ref_drop/` package (required by Blender's
Install from Disk / extensions flow).

Also writes a Blender static-repository ``index.json`` so drag-and-drop
install URLs can include ``?repository=…&blender_version_min=…`` the same
way https://www.blender.org/lab/mcp-server/ does.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "chrome_ref_drop"
MANIFEST = PACKAGE / "blender_manifest.toml"

REPO = "StephenSHorton/chrome-ref-drop"
PAGES_BASE = f"https://stephenshorton.github.io/chrome-ref-drop"
DEFAULT_REPO_JSON = f"{PAGES_BASE}/index.json"

SKIP_DIR_NAMES = {"__pycache__", ".git", ".github"}
SKIP_SUFFIXES = {".pyc", ".pyo", ".zip"}


def read_manifest() -> dict[str, Any]:
    """Tiny TOML subset reader for our manifest (no external deps)."""
    text = MANIFEST.read_text(encoding="utf-8")
    data: dict[str, Any] = {}
    section = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            data.setdefault(section, {})
            continue
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip()
        parsed: Any
        if val.startswith("["):
            # simple string array
            inner = val.strip("[]").strip()
            items = []
            for part in inner.split(","):
                part = part.strip().strip('"').strip("'")
                if part:
                    items.append(part)
            parsed = items
        elif val.startswith('"') and val.endswith('"'):
            parsed = val[1:-1]
        else:
            parsed = val
        if section:
            data[section][key] = parsed
        else:
            data[key] = parsed
    return data


def read_version() -> str:
    version = read_manifest().get("version")
    if not version:
        raise SystemExit("Could not parse version from blender_manifest.toml")
    return str(version)


def should_include(path: Path) -> bool:
    rel_parts = path.relative_to(PACKAGE).parts
    if any(part in SKIP_DIR_NAMES for part in rel_parts):
        return False
    if path.suffix.lower() in SKIP_SUFFIXES:
        return False
    return True


def build_zip(out_path: Path) -> list[str]:
    if not PACKAGE.is_dir():
        raise SystemExit(f"Missing package directory: {PACKAGE}")
    if not MANIFEST.is_file():
        raise SystemExit(f"Missing manifest: {MANIFEST}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()

    written: list[str] = []
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(PACKAGE.rglob("*")):
            if not path.is_file() or not should_include(path):
                continue
            arcname = Path("chrome_ref_drop") / path.relative_to(PACKAGE)
            zf.write(path, arcname.as_posix())
            written.append(arcname.as_posix())

    if "chrome_ref_drop/blender_manifest.toml" not in written:
        raise SystemExit("Zip is missing chrome_ref_drop/blender_manifest.toml")
    if "chrome_ref_drop/__init__.py" not in written:
        raise SystemExit("Zip is missing chrome_ref_drop/__init__.py")
    return written


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def release_asset_url(version: str, filename: str) -> str:
    return f"https://github.com/{REPO}/releases/download/v{version}/{filename}"


def pages_zip_url(filename: str = "chrome_ref_drop-latest.zip") -> str:
    """Direct zip on GitHub Pages — no redirects (required for Blender drag-install).

    GitHub *Releases* download URLs 302 through a CDN whose final path does not
    end in ``.zip`` and drops query params, so Blender silently ignores the drop.
    Hosting the same zip on Pages keeps ``….zip?repository=…&blender_version_min=…``.
    """
    return f"{PAGES_BASE}/{filename}"


def latest_download_url(filename: str = "chrome_ref_drop-latest.zip") -> str:
    # Prefer Pages for installs; GitHub Releases remain a backup download source.
    return pages_zip_url(filename)


def drag_install_url(
    zip_url: str,
    *,
    repository: str | None = None,
    blender_version_min: str = "4.2.0",
) -> str:
    """Blender drag-and-drop install URL (see extensions static repository docs).

    Use a zip URL that **exactly** matches the index entry's archive file name
    (e.g. ``chrome_ref_drop-0.1.0.zip``, not ``-latest.zip``). Blender looks the
    dropped package up in the remote index; a filename mismatch yields
    “extension dropped was not found in remote repository”.

    ``repository`` defaults to a same-folder relative ``./index.json`` (encoded),
    matching Blender's documented self-hosted example.
    """
    # Relative index next to the zip — same pattern as the manual example:
    #   my-addon.zip?repository=.%2Findex.json&blender_version_min=4.2.0
    if repository is None:
        repository = "./index.json"
    return (
        f"{zip_url}"
        f"?repository={quote(repository, safe='')}"
        f"&blender_version_min={quote(blender_version_min, safe='')}"
    )


def build_repo_index(zip_path: Path, archive_url: str) -> dict[str, Any]:
    """Build a static-repo index entry.

    Prefer a *relative* ``archive_url`` (``./chrome_ref_drop-X.Y.Z.zip``) so it
    resolves next to ``index.json`` on Pages — same pattern as community repos
    and Blender's own ``server-generate`` output.

    Note: do **not** put permissions here; they live in the zip manifest.
    Official platform listings also omit them from index entries.
    """
    m = read_manifest()
    version = str(m["version"])
    # Relative path matches the file we publish beside index.json
    if not archive_url or archive_url.startswith("https://"):
        archive_url = f"./chrome_ref_drop-{version}.zip"
    entry = {
        "schema_version": str(m.get("schema_version", "1.0.0")),
        "id": str(m["id"]),
        "name": str(m["name"]),
        "tagline": str(m.get("tagline", "")),
        "version": version,
        "type": str(m.get("type", "add-on")),
        "maintainer": str(m.get("maintainer", "")),
        "license": list(m.get("license") or ["SPDX:GPL-3.0-or-later"]),
        "blender_version_min": str(m.get("blender_version_min", "4.2.0")),
        # Exclusive upper bound (same idea as Launch kits: support through 5.x)
        "blender_version_max": "6.0.0",
        "website": str(m.get("website", f"https://github.com/{REPO}")),
        "tags": list(m.get("tags") or []),
        "archive_url": archive_url,
        "archive_size": zip_path.stat().st_size,
        "archive_hash": f"sha256:{sha256_file(zip_path)}",
    }
    return {"version": "v1", "blocklist": [], "data": [entry]}


def write_install_urls(path: Path, version: str, blender_version_min: str) -> None:
    """Machine-readable install URLs for the landing page / README."""
    versioned = f"chrome_ref_drop-{version}.zip"
    latest_name = "chrome_ref_drop-latest.zip"
    # Drag must use the versioned filename that appears in index.json archive_url.
    drag = drag_install_url(
        pages_zip_url(versioned),
        blender_version_min=blender_version_min,
    )
    payload = {
        "version": version,
        "blender_version_min": blender_version_min,
        "repository": f"{PAGES_BASE}/index.json",
        "repository_relative": "./index.json",
        # Direct Pages URLs (drag-install safe)
        "download_versioned": pages_zip_url(versioned),
        "download_latest": pages_zip_url(latest_name),
        # GitHub Releases (may redirect; fine for manual browser download)
        "download_github_versioned": release_asset_url(version, versioned),
        "download_github_latest": (
            f"https://github.com/{REPO}/releases/latest/download/{latest_name}"
        ),
        "drag_versioned": drag,
        # Alias kept for callers; points at versioned zip (not -latest) on purpose
        "drag_latest": drag,
        "pages": PAGES_BASE,
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output zip path (default: dist/chrome_ref_drop-<version>.zip)",
    )
    parser.add_argument(
        "--name-only",
        action="store_true",
        help="Print the default artifact filename and exit",
    )
    parser.add_argument(
        "--drag-url-only",
        action="store_true",
        help="Print the latest drag-and-drop install URL and exit",
    )
    parser.add_argument(
        "--repo-index",
        type=Path,
        help="Write Blender static repository index.json to this path",
    )
    parser.add_argument(
        "--archive-url",
        type=str,
        default="",
        help="Public URL of the zip for index.json (default: GitHub release asset)",
    )
    parser.add_argument(
        "--install-urls",
        type=Path,
        help="Write install-urls.json (for the landing page to embed)",
    )
    args = parser.parse_args(argv)

    manifest = read_manifest()
    version = str(manifest["version"])
    vmin = str(manifest.get("blender_version_min", "4.2.0"))
    default_name = f"chrome_ref_drop-{version}.zip"

    if args.name_only:
        print(default_name)
        return 0

    if args.drag_url_only:
        # Must match index.json archive filename (versioned, not -latest)
        print(
            drag_install_url(
                pages_zip_url(default_name),
                blender_version_min=vmin,
            )
        )
        return 0

    out = args.output or (ROOT / "dist" / default_name)
    files = build_zip(out.resolve())
    size = out.stat().st_size
    print(f"Built {out} ({size} bytes, {len(files)} files)")
    for f in files:
        print(f"  {f}")

    # Relative path by default — resolves next to index.json on Pages
    archive_url = args.archive_url or f"./chrome_ref_drop-{version}.zip"
    if args.repo_index:
        index = build_repo_index(out.resolve(), archive_url)
        args.repo_index.parent.mkdir(parents=True, exist_ok=True)
        args.repo_index.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote repo index {args.repo_index}")

    urls_path = args.install_urls or (ROOT / "dist" / "install-urls.json")
    write_install_urls(urls_path, version, vmin)
    print(f"Wrote {urls_path}")
    print("Drag URL (versioned zip + relative index, Pages-hosted):")
    print(
        drag_install_url(
            pages_zip_url(default_name),
            blender_version_min=vmin,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
