"""Operators: drop import, URL import, clipboard paste as reference."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    FloatProperty,
    StringProperty,
)
from bpy_extras.io_utils import ImportHelper

from . import util

# Lazy Windows clipboard
_clipboard_win = None


def _win_clip():
    global _clipboard_win
    if sys.platform != "win32":
        return None
    if _clipboard_win is None:
        from . import clipboard_win as _clipboard_win
    return _clipboard_win


class OBJECT_OT_reference_image_from_path(bpy.types.Operator):
    """Import a local image (or downloaded cache path) as a reference empty"""

    bl_idname = "object.reference_image_from_path"
    bl_label = "Reference Image from Path"
    bl_options = {"REGISTER", "UNDO"}

    # FileHandler single-file contract
    filepath: StringProperty(subtype="FILE_PATH", options={"SKIP_SAVE", "HIDDEN"})

    # FileHandler multi-file contract
    directory: StringProperty(subtype="DIR_PATH", options={"SKIP_SAVE", "HIDDEN"})
    files: CollectionProperty(
        type=bpy.types.OperatorFileListElement, options={"SKIP_SAVE", "HIDDEN"}
    )

    align_to_view: BoolProperty(
        name="Align to View",
        default=True,
        description="Rotate the reference empty to face the active 3D View",
    )
    size: FloatProperty(
        name="Size",
        default=5.0,
        min=0.001,
        description="Empty display size",
    )

    @classmethod
    def poll(cls, context):
        return context.scene is not None

    def _iter_paths(self):
        paths = []
        if self.files and self.directory:
            for f in self.files:
                if f.name:
                    paths.append(os.path.join(self.directory, f.name))
        elif self.filepath:
            paths.append(self.filepath)
        return paths

    def execute(self, context):
        paths = self._iter_paths()
        if not paths:
            self.report({"ERROR"}, "No filepath provided")
            return {"CANCELLED"}

        created = []
        errors = []
        for raw in paths:
            try:
                local = util.resolve_to_local_image(raw)
                if not util.looks_like_image_path(str(local)) and not local.is_file():
                    errors.append(f"Not an image: {raw}")
                    continue
                ob = util.create_reference_empty(
                    context,
                    local,
                    size=self.size,
                    align_to_view=self.align_to_view,
                )
                created.append(ob.name)
            except Exception as e:
                errors.append(f"{Path(raw).name or raw[:40]}: {e}")

        if not created:
            self.report({"ERROR"}, "; ".join(errors) if errors else "Import failed")
            return {"CANCELLED"}

        msg = f"Added reference image(s): {', '.join(created)}"
        if errors:
            msg += f" ({len(errors)} failed)"
        self.report({"INFO"}, msg)
        return {"FINISHED"}

    def invoke(self, context, event):
        # Drop path already set by FileHandler
        if self.filepath or (self.files and self.directory):
            return self.execute(context)
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


class OBJECT_OT_reference_image_from_url(bpy.types.Operator):
    """Download an image URL and add it as a reference empty"""

    bl_idname = "object.reference_image_from_url"
    bl_label = "Reference Image from URL"
    bl_options = {"REGISTER", "UNDO"}

    url: StringProperty(
        name="URL",
        description="http(s) or data:image URL",
        default="",
        options={"SKIP_SAVE"},
    )
    align_to_view: BoolProperty(name="Align to View", default=True)
    size: FloatProperty(name="Size", default=5.0, min=0.001)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "url")
        layout.prop(self, "align_to_view")
        layout.prop(self, "size")

    def invoke(self, context, event):
        # Pre-fill from text clipboard when possible
        clip = context.window_manager.clipboard or ""
        url = util.extract_url_from_text(clip)
        if url:
            self.url = url
        prefs = util.get_prefs(context)
        if prefs:
            self.size = prefs.default_size
            self.align_to_view = prefs.align_to_view
        return context.window_manager.invoke_props_dialog(self, width=480)

    def execute(self, context):
        url = (self.url or "").strip()
        if not url:
            self.report({"ERROR"}, "URL is empty")
            return {"CANCELLED"}
        try:
            local = util.resolve_to_local_image(url)
            ob = util.create_reference_empty(
                context,
                local,
                size=self.size,
                align_to_view=self.align_to_view,
            )
        except Exception as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        self.report({"INFO"}, f"Added reference: {ob.name}")
        return {"FINISHED"}


class OBJECT_OT_reference_image_from_clipboard(bpy.types.Operator):
    """
    Paste a browser image as a reference empty.

    Supports:
    - Image pixels on the clipboard (Chrome: right-click → Copy image)
    - Image URL / HTML snippet text on the clipboard
    """

    bl_idname = "object.reference_image_from_clipboard"
    bl_label = "Paste Reference Image from Clipboard"
    bl_options = {"REGISTER", "UNDO"}

    align_to_view: BoolProperty(name="Align to View", default=True)
    size: FloatProperty(name="Size", default=5.0, min=0.001)

    @classmethod
    def poll(cls, context):
        return context.scene is not None

    def execute(self, context):
        prefs = util.get_prefs(context)
        if prefs:
            self.size = prefs.default_size
            self.align_to_view = prefs.align_to_view

        # 1) Pixel image on clipboard (best quality for Chrome "Copy image")
        win = _win_clip()
        if win is not None:
            try:
                img_data = win.get_clipboard_image_bytes()
            except Exception:
                img_data = None
            if img_data:
                data, ext = img_data
                try:
                    local = util.write_bytes_as_image(data, preferred_ext=ext)
                    ob = util.create_reference_empty(
                        context,
                        local,
                        size=self.size,
                        align_to_view=self.align_to_view,
                    )
                    self.report({"INFO"}, f"Pasted reference: {ob.name}")
                    return {"FINISHED"}
                except Exception as e:
                    self.report({"WARNING"}, f"Clipboard image failed: {e}")

        # 2) Text / URL on clipboard (Blender WM + Win32 Unicode)
        clip_text = context.window_manager.clipboard or ""
        if win is not None and not util.extract_url_from_text(clip_text):
            try:
                win_text = win.get_clipboard_text() or ""
                if win_text:
                    clip_text = win_text
            except Exception:
                pass

        url = util.extract_url_from_text(clip_text)
        if url:
            try:
                local = util.resolve_to_local_image(url)
                ob = util.create_reference_empty(
                    context,
                    local,
                    size=self.size,
                    align_to_view=self.align_to_view,
                )
                self.report({"INFO"}, f"Downloaded reference: {ob.name}")
                return {"FINISHED"}
            except Exception as e:
                self.report({"ERROR"}, str(e))
                return {"CANCELLED"}

        self.report(
            {"ERROR"},
            "Clipboard has no image or image URL. "
            "In Chrome: right-click image → Copy image, then run this again.",
        )
        return {"CANCELLED"}


class OBJECT_OT_reference_image_import_files(bpy.types.Operator, ImportHelper):
    """Pick image files and add them as reference empties"""

    bl_idname = "object.reference_image_import_files"
    bl_label = "Import Reference Image(s)"
    bl_options = {"REGISTER", "UNDO"}

    filename_ext = ""
    filter_glob: StringProperty(
        default="*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.gif;*.tif;*.tiff;*.hdr;*.exr;*.tga",
        options={"HIDDEN"},
    )
    files: CollectionProperty(type=bpy.types.OperatorFileListElement)
    directory: StringProperty(subtype="DIR_PATH")

    align_to_view: BoolProperty(name="Align to View", default=True)
    size: FloatProperty(name="Size", default=5.0, min=0.001)

    def execute(self, context):
        paths = []
        if self.files:
            for f in self.files:
                paths.append(os.path.join(self.directory, f.name))
        elif self.filepath:
            paths.append(self.filepath)

        created = []
        for p in paths:
            try:
                ob = util.create_reference_empty(
                    context,
                    p,
                    size=self.size,
                    align_to_view=self.align_to_view,
                )
                created.append(ob.name)
            except Exception as e:
                self.report({"WARNING"}, f"{Path(p).name}: {e}")

        if not created:
            self.report({"ERROR"}, "No images imported")
            return {"CANCELLED"}
        self.report({"INFO"}, f"Added: {', '.join(created)}")
        return {"FINISHED"}


classes = (
    OBJECT_OT_reference_image_from_path,
    OBJECT_OT_reference_image_from_url,
    OBJECT_OT_reference_image_from_clipboard,
    OBJECT_OT_reference_image_import_files,
)
