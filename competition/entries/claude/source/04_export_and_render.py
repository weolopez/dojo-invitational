"""Stage 4: export fighter.glb from .work/claude_rigged.blend, then render the required views FROM THAT GLB
in a clean scene (judge HDRI + one key light, EEVEE). Writes fighter.glb, renders/*.png, .work/previews/action_*.png.
"""
import math
import os

import bpy
from mathutils import Vector

ENTRY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(ENTRY, ".work")
GLB = os.path.join(ENTRY, "fighter.glb")
HDRI = "/Users/weo/Development/3d/assets/polyhaven/hdri/basement_boxing_ring_2k.hdr"


def bake_modifiers():
    """Apply every modifier except the armature on each mesh (MPFB's helper masks and subdivision), so hidden
    helper geometry is really removed before export. The armature modifier is moved last first, because MPFB puts it
    first and the glTF exporter would otherwise skip the masks."""
    for obj in [o for o in bpy.data.objects if o.type == "MESH"]:
        arm = next((m for m in obj.modifiers if m.type == "ARMATURE"), None)
        if arm:
            with bpy.context.temp_override(object=obj, active_object=obj):
                bpy.ops.object.modifier_move_to_index(modifier=arm.name, index=len(obj.modifiers) - 1)
        for mod in [m for m in obj.modifiers if m.type != "ARMATURE"]:
            if not (mod.show_viewport and mod.show_render):
                obj.modifiers.remove(mod)  # switched off in MPFB's setup, so it isn't part of the look
                continue
            if mod.type == "SUBSURF":
                mod.levels = max(mod.levels, mod.render_levels)  # MPFB leaves the viewport level at 0
            try:
                with bpy.context.temp_override(object=obj, active_object=obj, selected_objects=[obj]):
                    bpy.ops.object.modifier_apply(modifier=mod.name)
            except RuntimeError:
                print(f"[export] {obj.name}: removed {mod.type} '{mod.name}' (Blender reports it as disabled)")
                obj.modifiers.remove(mod)
        print(f"[export] {obj.name}: {len(obj.data.vertices)} verts after baking modifiers")


def export():
    bpy.ops.wm.open_mainfile(filepath=os.path.join(WORK, "claude_rigged.blend"))
    bake_modifiers()
    for o in bpy.data.objects:
        o.hide_set(False)
        o.select_set(o.type in {"MESH", "ARMATURE"})
    bpy.ops.export_scene.gltf(filepath=GLB, export_format="GLB", use_selection=True, export_apply=False,
                              export_animations=True, export_animation_mode="NLA_TRACKS", export_force_sampling=True,
                              export_image_format="AUTO", export_yup=True)
    print(f"[export] fighter.glb {os.path.getsize(GLB) / 1e6:.1f} MB")


def setup_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=GLB)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in [e.identifier for e in scene.render.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.view_settings.view_transform = "AgX" if "AgX" in [v.identifier for v in scene.view_settings.bl_rna.properties["view_transform"].enum_items] else "Filmic"
    world = bpy.data.worlds.new("judge")
    world.use_nodes = True
    env = world.node_tree.nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(HDRI)
    world.node_tree.links.new(env.outputs["Color"], world.node_tree.nodes["Background"].inputs["Color"])
    scene.world = world
    key = bpy.data.objects.new("key", bpy.data.lights.new("key", "AREA"))
    key.data.energy, key.data.size = 350, 1.6
    key.location = (-1.8, -2.4, 2.5)
    key.rotation_euler = (Vector((0, 0, 1.3)) - key.location).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(key)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    arm = next(o for o in scene.objects if o.type == "ARMATURE")
    return scene, arm, cam


def pose(scene, arm, clip, frac):
    act = bpy.data.actions.get(clip)
    for t in list(arm.animation_data.nla_tracks):
        t.mute = True
    arm.animation_data.action = act
    if hasattr(arm.animation_data, "action_slot") and act.slots:
        arm.animation_data.action_slot = act.slots[0]
    f0, f1 = act.frame_range
    scene.frame_set(int(f0 + (f1 - f0) * frac))
    head = next(b for b in arm.pose.bones if b.name.endswith("Head"))
    return arm.matrix_world @ head.head


def shoot(scene, cam, name, angle_deg, dist, height, target, lens, folder):
    a = math.radians(angle_deg)
    cam.location = Vector((target.x + math.sin(a) * dist, target.y - math.cos(a) * dist, height))
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = lens
    scene.render.filepath = os.path.join(folder, f"{name}.png")
    bpy.ops.render.render(write_still=True)


def main():
    export()
    scene, arm, cam = setup_scene()
    renders = os.path.join(ENTRY, "renders")
    os.makedirs(renders, exist_ok=True)
    head = pose(scene, arm, "fighting_idle", 0.3)
    body = Vector((head.x, head.y, head.z * 0.55))
    # glTF +Z forward becomes Blender -Y, so the fighter faces the -Y camera.
    shoot(scene, cam, "front", 0, 4.6, head.z * 0.6, body, 50, renders)
    shoot(scene, cam, "three_quarter", 35, 4.6, head.z * 0.62, body, 50, renders)
    shoot(scene, cam, "profile", 90, 4.6, head.z * 0.6, body, 50, renders)
    shoot(scene, cam, "closeup", 20, 0.95, head.z + 0.05, head + Vector((0, 0, 0.06)), 85, renders)
    previews = os.path.join(WORK, "previews")
    for clip, frac, ang in (("roundhouse_kick", 0.45, 70), ("jab_cross", 0.4, 60), ("knocked_out", 0.6, 80)):
        head = pose(scene, arm, clip, frac)
        shoot(scene, cam, f"action_{clip}", ang, 5.0, 1.1, Vector((head.x, head.y, 0.95)), 45, previews)
    print("[render] done")


main()
