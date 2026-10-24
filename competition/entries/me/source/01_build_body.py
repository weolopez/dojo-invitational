"""
Stage 1: generate the body with MPFB2 2.0.18 (CC0 MakeHuman base mesh + system assets) and its mixamo rig.
The body macros follow Grok's published recipe (entries/grok/NOTES.md, "Pipeline" step 1); the skin is MakeHuman's
CC0 "middleage caucasian male" so it can be tinted to the owner's FaceBuilder face. No head accessories are added:
the MPFB head is replaced by the owner's FaceBuilder head in stage 3.
Run through tools/build.mjs (it sets BLENDER_USER_RESOURCES to .work/blender_user where MPFB is installed).
"""

import os

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "..", ".work")

bpy.ops.preferences.addon_enable(module="bl_ext.user_default.mpfb")
from bl_ext.user_default.mpfb.services.assetservice import AssetService  # noqa: E402
from bl_ext.user_default.mpfb.services.exportservice import ExportService  # noqa: E402
from bl_ext.user_default.mpfb.services.humanservice import HumanService  # noqa: E402
from bl_ext.user_default.mpfb.services.objectservice import ObjectService  # noqa: E402

MACROS = {"gender": 1.0, "age": 0.55, "muscle": 1.0, "weight": 0.62, "proportions": 0.95, "height": 0.55,
          "cupsize": 0.3, "firmness": 0.8, "race": {"african": 0.45, "caucasian": 0.25, "asian": 0.30}}

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)
basemesh = HumanService.create_human(macro_detail_dict=MACROS)
skin = AssetService.find_asset_absolute_path("middleage_caucasian_male.mhmat", asset_subdir="skins")
HumanService.set_character_skin(skin, basemesh, skin_type="GAMEENGINE")
HumanService.add_builtin_rig(basemesh, "mixamo")

root = ExportService.create_character_copy(basemesh, name_suffix="_export")
body = ObjectService.find_object_of_type_amongst_nearest_relatives(root, "Basemesh")
ExportService.bake_modifiers_remove_helpers(body, bake_masks=True, bake_subdiv=True, remove_helpers=True, also_proxy=True)
keep = {root} | set(ObjectService.get_list_of_children(root))
for o in list(bpy.data.objects):
    if o not in keep:
        bpy.data.objects.remove(o)
for o in bpy.data.objects:
    print("[body]", o.name, o.type, len(o.data.polygons) if o.type == "MESH" else "")
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(WORK, "body.blend"))
