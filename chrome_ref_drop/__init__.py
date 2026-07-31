"""
Chrome Reference Drop
=====================

Drop image files into the 3D View as reference empties, download from
browser URLs, and paste Chrome "Copy image" clipboard data as references.
"""

bl_info = {
    "name": "Chrome Reference Drop",
    "author": "4step",
    "version": (0, 1, 0),
    "blender": (4, 2, 0),
    "location": "3D View · Object > Reference Images · Ctrl+Shift+V",
    "description": "Paste/download browser images into the scene as reference empties",
    "category": "Import-Export",
}

import bpy

from . import drop, operators, prefs

_keymaps = []


def _register_keymaps():
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if not kc:
        return
    km = kc.keymaps.new(name="3D View", space_type="VIEW_3D")
    # Ctrl+Shift+V — paste reference (does not steal plain Ctrl+V)
    kmi = km.keymap_items.new(
        "object.reference_image_from_clipboard",
        type="V",
        value="PRESS",
        ctrl=True,
        shift=True,
    )
    _keymaps.append((km, kmi))


def _unregister_keymaps():
    for km, kmi in _keymaps:
        km.keymap_items.remove(kmi)
    _keymaps.clear()


def register():
    for cls in operators.classes + prefs.classes:
        bpy.utils.register_class(cls)

    bpy.types.VIEW3D_MT_object.append(prefs.menu_object)
    bpy.types.VIEW3D_MT_add.append(prefs.menu_add)
    _register_keymaps()
    drop.sync_handler_from_prefs()


def unregister():
    drop.unregister_handler()
    _unregister_keymaps()
    bpy.types.VIEW3D_MT_object.remove(prefs.menu_object)
    bpy.types.VIEW3D_MT_add.remove(prefs.menu_add)

    for cls in reversed(prefs.classes + operators.classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
