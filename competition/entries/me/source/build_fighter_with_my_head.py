"""
Put the FaceBuilder head (my_head_facebuilder.glb) on the Mixamo X Bot body and pack every Mixamo clip into one file.
Run with:
  /Applications/Blender.app/Contents/MacOS/Blender --background --python build_fighter_with_my_head.py
Outputs my_fighter.blend and my_fighter.glb (one animation per clip, named after the files in assets/mixamo).
"""

import glob
import os

import bmesh
import bpy
from mathutils import Vector

PROJECT_DIR = "/Users/weo/Development/3d"
MIXAMO_DIR = os.path.join(PROJECT_DIR, "assets", "mixamo")
XBOT_FBX = os.path.join(MIXAMO_DIR, "xbot_with_skin_fighting_idle.fbx")
HEAD_GLB = os.path.join(PROJECT_DIR, "my_head_facebuilder.glb")


def world_verts(obj):
    return [obj.matrix_world @ v.co for v in obj.data.vertices]


def skull_metrics(points):
    """Top of head, plus front-to-back length and centre of the upper skull (above the ears)."""
    top = max(p.z for p in points)
    bottom = min(p.z for p in points)
    cranium = [p for p in points if p.z > top - 0.35 * (top - bottom)]
    ys = [p.y for p in cranium]
    xs = [p.x for p in cranium]
    return {
        "top": top,
        "bottom": bottom,
        "length": max(ys) - min(ys),
        "centre_y": (max(ys) + min(ys)) / 2,
        "centre_x": (max(xs) + min(xs)) / 2,
    }


def import_xbot():
    bpy.ops.import_scene.fbx(filepath=XBOT_FBX)
    arm = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
    arm.name = "Fighter"
    body = bpy.data.objects["Beta_Surface"]
    return arm, body


def remove_xbot_head(body):
    head_group = body.vertex_groups["mixamorig:Head"].index
    head_points = []
    bm = bmesh.new()
    bm.from_mesh(body.data)
    deform = bm.verts.layers.deform.active
    doomed = []
    for v in bm.verts:
        if v[deform].get(head_group, 0.0) > 0.5:
            head_points.append(body.matrix_world @ v.co)
            doomed.append(v)
    bmesh.ops.delete(bm, geom=doomed, context="VERTS")
    bm.to_mesh(body.data)
    bm.free()
    print(f"[fighter] removed {len(doomed)} X Bot head vertices")
    return head_points


def fit_my_head(arm, xbot_head_points):
    bpy.ops.import_scene.gltf(filepath=HEAD_GLB)
    head = next(o for o in bpy.context.selected_objects if o.type == "MESH")
    head.name = "My_Head"
    head.parent = None

    target = skull_metrics(xbot_head_points)
    source = skull_metrics(world_verts(head))
    scale = target["length"] / source["length"] * 1.04
    head.scale = head.scale * scale
    bpy.context.view_layer.update()

    source = skull_metrics(world_verts(head))
    head.location += Vector((target["centre_x"] - source["centre_x"],
                             target["centre_y"] - source["centre_y"],
                             target["top"] + 0.008 - source["top"]))
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action="DESELECT")
    head.select_set(True)
    bpy.context.view_layer.objects.active = head
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    print(f"[fighter] head scale {scale:.4f}")

    bones = arm.data.bones
    neck_base = (arm.matrix_world @ bones["mixamorig:Neck"].head_local).z
    head_base = (arm.matrix_world @ bones["mixamorig:Head"].head_local).z

    # Trim the FaceBuilder neck (and the shirt collar baked onto it) where the X Bot torso takes over.
    cut_z = neck_base + 0.02
    bm = bmesh.new()
    bm.from_mesh(head.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < cut_z], context="VERTS")
    bm.to_mesh(head.data)
    bm.free()

    # Skin the head: skull follows the Head bone, the neck blends into the Neck bone.
    head_vg = head.vertex_groups.new(name="mixamorig:Head")
    neck_vg = head.vertex_groups.new(name="mixamorig:Neck")
    blend_low, blend_high = head_base - 0.05, head_base + 0.02
    for v in head.data.vertices:
        w = min(1.0, max(0.0, (v.co.z - blend_low) / (blend_high - blend_low)))
        head_vg.add([v.index], w, "REPLACE")
        neck_vg.add([v.index], 1.0 - w, "REPLACE")
    head.parent = arm
    head.matrix_parent_inverse = arm.matrix_world.inverted()
    mod = head.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    return head


def add_clips(arm):
    clips = sorted(p for p in glob.glob(os.path.join(MIXAMO_DIR, "*.fbx")) if "with_skin" not in p)
    arm.animation_data_create()
    for path in clips:
        name = os.path.splitext(os.path.basename(path))[0]
        before = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=path)
        new_objs = set(bpy.data.objects) - before
        src = next(o for o in new_objs if o.type == "ARMATURE")
        action = src.animation_data.action
        action.name = name
        action.use_fake_user = True
        for o in new_objs:
            bpy.data.objects.remove(o, do_unlink=True)

        arm.animation_data.action = action
        if hasattr(arm.animation_data, "action_slot") and action.slots:
            arm.animation_data.action_slot = action.slots[0]
        track = arm.animation_data.nla_tracks.new()
        track.name = name
        strip = track.strips.new(name, int(action.frame_range[0]), action)
        strip.name = name
        arm.animation_data.action = None
    print(f"[fighter] added {len(clips)} clips")

    # Keep the built-in idle as the default pose.
    idle = bpy.data.actions.get("fighting_idle")
    if idle is not None:
        arm.animation_data.action = idle
        if hasattr(arm.animation_data, "action_slot") and idle.slots:
            arm.animation_data.action_slot = idle.slots[0]


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    arm, body = import_xbot()
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)
    xbot_head = remove_xbot_head(body)
    fit_my_head(arm, xbot_head)
    add_clips(arm)

    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(PROJECT_DIR, "my_fighter.blend"))
    bpy.ops.export_scene.gltf(filepath=os.path.join(PROJECT_DIR, "my_fighter.glb"), export_format="GLB",
                              export_animations=True, export_animation_mode="NLA_TRACKS",
                              export_force_sampling=True)
    print("[fighter] done")


main()
