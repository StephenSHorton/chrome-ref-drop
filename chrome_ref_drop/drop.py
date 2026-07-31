"""Optional FileHandler for image drops (disabled by default).

Blender already ships VIEW3D_FH_empty_image, which turns local image file
drops into reference empties. Registering a second handler for the same
extensions makes the 3D View show a chooser on every drop — noisy for little
gain.

Enable in Preferences → Chrome Reference Drop → "Also handle file drops"
if you want our operator (URL-aware resolve + size/depth prefs) instead of
or alongside the built-in path.
"""

from __future__ import annotations

import bpy

from . import util

_handler_registered = False


class VIEW3D_FH_chrome_ref_drop(bpy.types.FileHandler):
    """Accept image file drops in the 3D View → reference empties via our operator."""

    bl_idname = "VIEW3D_FH_chrome_ref_drop"
    bl_label = "Chrome Reference Drop"
    bl_import_operator = "object.reference_image_from_path"
    bl_file_extensions = util.FILEHANDLER_EXTENSIONS

    @classmethod
    def poll_drop(cls, context):
        return context.area is not None and context.area.type == "VIEW_3D"


classes = (VIEW3D_FH_chrome_ref_drop,)


def register_handler():
    global _handler_registered
    if _handler_registered:
        return
    for cls in classes:
        bpy.utils.register_class(cls)
    _handler_registered = True


def unregister_handler():
    global _handler_registered
    if not _handler_registered:
        return
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass
    _handler_registered = False


def sync_handler_from_prefs(context=None):
    """Register/unregister FileHandler to match the preference toggle."""
    prefs = util.get_prefs(context)
    want = bool(prefs and prefs.handle_file_drops)
    if want:
        register_handler()
    else:
        unregister_handler()
