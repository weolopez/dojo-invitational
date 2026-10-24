"""Build CLAUDE, a fictional fighter, from MakeHuman CC0 assets with MPFB 2.0.18, rigged with MPFB's Mixamo rig.
Run: BLENDER_USER_RESOURCES=<entry>/.work/blender_user Blender --background --python source/01_build_human.py
Writes .work/claude_human.blend and preview renders in .work/previews/.
"""
import math
import os

import bpy
from mathutils import Vector

ENTRY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(ENTRY, ".work")

from bl_ext.user_default.mpfb.services.humanservice import HumanService  # noqa: E402

# A fictional woman in her late 30s: athletic, olive-toned, dark hair tied back (see NOTES.md for the design).
HUMAN = {
    "phenotype": {
        "gender": 0.0, "age": 0.6, "muscle": 0.72, "weight": 0.45, "proportions": 0.85, "height": 0.6,
        "cupsize": 0.4, "firmness": 0.65,
        "race": {"caucasian": 0.55, "african": 0.25, "asian": 0.2},
    },
    "rig": "mixamo",
    "skin_mhmat": "middleage_caucasian_female.mhmat",
    "skin_material_type": "MAKESKIN",
    "eyes": "high-poly.mhclo",
    "eyes_material_type": "MAKESKIN",
    "eyebrows": "eyebrow002.mhclo",
    "eyelashes": "eyelashes02.mhclo",
    "teeth": "teeth_base.mhclo",
    "tongue": "tongue01.mhclo",
    "hair": "ponytail01.mhclo",
    "proxy": "",
    "clothes": ["female_sportsuit01.mhclo"],
    "clothes_material_type": "MAKESKIN",
    "targets": [],
    "expressions": [],
    "skin_material_settings": {},
    "eyes_material_settings": {},
}


def preview(name, cam_loc, look_at, lens):
    scene = bpy.context.scene
    cam = scene.camera
    cam.location = Vector(cam_loc)
    cam.rotation_euler = (Vector(look_at) - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = lens
    scene.render.filepath = os.path.join(WORK, "previews", f"{name}.png")
    bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    settings = HumanService.get_default_deserialization_settings()
    settings["subdiv_levels"] = 1
    basemesh = HumanService.deserialize_from_dict(HUMAN, settings)
    print("[build] basemesh", basemesh.name, len(basemesh.data.vertices), "verts")
    for o in bpy.data.objects:
        print("[build] object", o.name, o.type, (o.parent.name if o.parent else ""))

    os.makedirs(os.path.join(WORK, "previews"), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(WORK, "claude_human.blend"))

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in [e.identifier for e in scene.render.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y = 1080, 1350
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    env = world.node_tree.nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load("/Users/weo/Development/3d/assets/polyhaven/hdri/basement_boxing_ring_2k.hdr")
    world.node_tree.links.new(env.outputs["Color"], world.node_tree.nodes["Background"].inputs["Color"])
    scene.world = world
    key = bpy.data.objects.new("key", bpy.data.lights.new("key", "AREA"))
    key.data.energy, key.data.size = 400, 1.5
    key.location = (-1.6, -2.2, 2.4)
    key.rotation_euler = (Vector((0, 0, 1.4)) - key.location).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(key)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    top = max((basemesh.matrix_world @ Vector(c)).z for c in basemesh.bound_box)
    print("[build] height", round(top, 3))
    preview("front", (0, -4.2, top * 0.55), (0, 0, top * 0.52), 50)
    preview("face", (0.25, -0.9, top - 0.1), (0, 0, top - 0.12), 85)


main()
