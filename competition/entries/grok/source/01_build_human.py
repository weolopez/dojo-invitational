# Step 1: generate the fictional fighter with MPFB2 (CC0 MakeHuman base + system assets), mixamo rig.
import bpy, sys, os, importlib
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp')
def imp(pkg, key):
    for m in list(sys.modules):
        if m.endswith(pkg):
            return getattr(importlib.import_module(m), key)
    raise ValueError(pkg)
HumanService = imp("mpfb.services.humanservice", "HumanService")
AssetService = imp("mpfb.services.assetservice", "AssetService")
ExportService = imp("mpfb.services.exportservice", "ExportService")
ObjectService = imp("mpfb.services.objectservice", "ObjectService")

for o in list(bpy.data.objects): bpy.data.objects.remove(o)
macro = {"gender": 1.0, "age": 0.55, "muscle": 1.0, "weight": 0.62, "proportions": 0.95, "height": 0.55,
         "cupsize": 0.3, "firmness": 0.8, "race": {"african": 0.45, "caucasian": 0.25, "asian": 0.30}}
bm = HumanService.create_human(macro_detail_dict=macro)
skin = AssetService.find_asset_absolute_path("young_african_male.mhmat", asset_subdir="skins")
HumanService.set_character_skin(skin, bm, skin_type="GAMEENGINE")
HumanService.add_builtin_rig(bm, "mixamo")
for sub, f, t in [("eyes", "high-poly.mhclo", "Eyes"), ("eyebrows", "eyebrow001.mhclo", "Eyebrows"),
                  ("eyelashes", "eyelashes01.mhclo", "Eyelashes"), ("teeth", "teeth_base.mhclo", "Teeth"),
                  ("tongue", "tongue01.mhclo", "Tongue"), ("hair", sys.argv[-1] if sys.argv[-1].endswith('.mhclo') else "short02.mhclo", "Hair")]:
    p = AssetService.find_asset_absolute_path(f, asset_subdir=sub)
    print("ASSET", f, p)
    if p: HumanService.add_mhclo_asset(p, bm, asset_type=t, material_type="GAMEENGINE")
root = ExportService.create_character_copy(bm, name_suffix="_export")
ebm = ObjectService.find_object_of_type_amongst_nearest_relatives(root, "Basemesh")
ExportService.bake_modifiers_remove_helpers(ebm, bake_masks=True, bake_subdiv=True, remove_helpers=True, also_proxy=True)
# drop the original (unbaked) character
keep = {root} | set(ObjectService.get_list_of_children(root))
for o in list(bpy.data.objects):
    if o not in keep: bpy.data.objects.remove(o)
for o in bpy.data.objects:
    print("OBJ", o.name, o.type, len(o.data.polygons) if o.type == 'MESH' else '', [m.name for m in o.material_slots] if o.type=='MESH' else '')
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "human.blend"))
