"""Addon preferences and UI menu."""

from __future__ import annotations

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, StringProperty


def _on_handle_file_drops_update(self, context):
    from . import drop

    drop.sync_handler_from_prefs(context)


class ChromeRefDropPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    cache_dir: StringProperty(
        name="Download Cache",
        description="Folder for images downloaded from browser URLs (blank = temp dir)",
        subtype="DIR_PATH",
        default="",
    )
    default_size: FloatProperty(
        name="Default Size",
        description="Default empty display size for new reference images",
        default=5.0,
        min=0.001,
        max=1000.0,
    )
    align_to_view: BoolProperty(
        name="Align to View",
        description="Face new reference images toward the active 3D View",
        default=True,
    )
    place_at_view: BoolProperty(
        name="Prefer View Focus when Cursor at Origin",
        description="If the 3D cursor is still at world origin, place refs at the view focus",
        default=True,
    )
    image_depth: EnumProperty(
        name="Image Depth",
        description="Draw reference in front of or behind objects",
        items=(
            ("DEFAULT", "Default", "Use Blender default depth"),
            ("FRONT", "Front", "Draw in front of objects"),
            ("BACK", "Back", "Draw behind objects"),
        ),
        default="DEFAULT",
    )
    handle_file_drops: BoolProperty(
        name="Also Handle File Drops",
        description=(
            "Register a FileHandler for image drops in the 3D View. "
            "Off by default because Blender already creates reference empties "
            "for local image files; enabling this may show a drop chooser"
        ),
        default=False,
        update=_on_handle_file_drops_update,
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "cache_dir")
        layout.prop(self, "default_size")
        layout.prop(self, "align_to_view")
        layout.prop(self, "place_at_view")
        layout.prop(self, "image_depth")
        layout.prop(self, "handle_file_drops")

        col = layout.column(align=True)
        col.label(text="Chrome tip:", icon="INFO")
        col.label(text="Best quality: right-click image → Copy image, then")
        col.label(text="Object → Reference Images → Paste from Clipboard")
        col.label(text="(or Ctrl+Shift+V in the 3D View).")


class VIEW3D_MT_reference_images(bpy.types.Menu):
    bl_label = "Reference Images"
    bl_idname = "VIEW3D_MT_reference_images"

    def draw(self, context):
        layout = self.layout
        layout.operator(
            "object.reference_image_from_clipboard",
            text="Paste from Clipboard",
            icon="PASTEDOWN",
        )
        layout.operator(
            "object.reference_image_from_url",
            text="From URL…",
            icon="URL",
        )
        layout.operator(
            "object.reference_image_import_files",
            text="Import File(s)…",
            icon="FILE_IMAGE",
        )


def menu_object(self, context):
    self.layout.menu("VIEW3D_MT_reference_images", icon="IMAGE_REFERENCE")


def menu_add(self, context):
    self.layout.operator_context = "INVOKE_DEFAULT"
    self.layout.operator(
        "object.reference_image_from_clipboard",
        text="Reference Image (Clipboard)",
        icon="IMAGE_REFERENCE",
    )


classes = (
    ChromeRefDropPreferences,
    VIEW3D_MT_reference_images,
)
