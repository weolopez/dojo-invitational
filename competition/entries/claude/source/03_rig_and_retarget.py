"""Stage 3: put CLAUDE's MPFB Mixamo rig into the clips' T-pose rest, then retarget all 28 shared Mixamo clips.
Opens .work/claude_materials.blend, writes .work/claude_rigged.blend.

Retarget: for every frame, each bone's world rotation is copied from the source skeleton (X Bot clips in
assets/mixamo), corrected by the rest-pose difference between the two bones (both rests are T-poses after step 1),
then converted to the target bone's local rotation. Hip translation is scaled by the hip-height ratio.
"""
import glob
import math
import os

import bpy
from mathutils import Matrix, Quaternion, Vector

ENTRY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(ENTRY, ".work")
MIXAMO = "/Users/weo/Development/3d/assets/mixamo"
HIPS = "mixamorig:Hips"


def import_clip(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    new = set(bpy.data.objects) - before
    arm = next(o for o in new if o.type == "ARMATURE")
    return arm, new


def remove(objs):
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)


def ordered(arm):
    """Bones parents-first."""
    out = []
    def walk(b):
        out.append(b.name)
        for c in b.children:
            walk(c)
    for b in arm.data.bones:
        if b.parent is None:
            walk(b)
    return out


def match_rest_pose(target, source):
    """Swing the arm chains (A-pose to T-pose) so they point the same way as the source rest bones, in world space.
    Spine, hips and legs already match closely and are left alone, so no bone can be flipped end to end."""
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.mode_set(mode="POSE")
    for name in ordered(target):
        if name not in source.data.bones or not any(k in name for k in ("Shoulder", "Arm", "Hand")):
            continue
        sb = source.data.bones[name]
        d_src = (source.matrix_world @ sb.tail_local) - (source.matrix_world @ sb.head_local)
        if d_src.length < 1e-6:
            continue
        pb = target.pose.bones[name]
        head = target.matrix_world @ pb.head
        d_tgt = (target.matrix_world @ pb.tail) - head
        q = d_tgt.normalized().rotation_difference(d_src.normalized())
        if q.angle > math.radians(100):
            print(f"[rig] skipped {name}: {math.degrees(q.angle):.0f} degrees apart")
            continue
        world = target.matrix_world @ pb.matrix
        swung = Matrix.Translation(head) @ q.to_matrix().to_4x4() @ Matrix.Translation(-head) @ world
        pb.matrix = target.matrix_world.inverted() @ swung
        bpy.context.view_layer.update()
    bpy.ops.object.mode_set(mode="OBJECT")


def apply_pose_as_rest(target):
    """Bake the current pose into every skinned mesh, then make it the armature's rest pose."""
    for obj in [o for o in bpy.data.objects if o.type == "MESH"]:
        mod = next((m for m in obj.modifiers if m.type == "ARMATURE" and m.object == target), None)
        if not mod:
            continue
        if obj.data.shape_keys:
            # Keep the body shape (MPFB macro targets) by baking the current shape-key mix into the mesh.
            with bpy.context.temp_override(object=obj, active_object=obj, selected_objects=[obj]):
                bpy.ops.object.shape_key_remove(all=True, apply_mix=True)
        name = mod.name
        with bpy.context.temp_override(object=obj, active_object=obj, selected_objects=[obj]):
            bpy.ops.object.modifier_apply(modifier=name)
        new = obj.modifiers.new(name, "ARMATURE")
        new.object = target
        while obj.modifiers.find(name) > 0:
            with bpy.context.temp_override(object=obj, active_object=obj):
                bpy.ops.object.modifier_move_up(modifier=name)
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.mode_set(mode="POSE")
    bpy.ops.pose.armature_apply(selected=False)
    bpy.ops.object.mode_set(mode="OBJECT")


def world_rest_rot(arm, name):
    return (arm.matrix_world @ arm.data.bones[name].matrix_local).to_quaternion()


def retarget(target, source, clip_name, ratio):
    names = [n for n in ordered(target) if n in source.data.bones]
    rest_t = {n: world_rest_rot(target, n) for n in ordered(target)}
    rest_s = {n: world_rest_rot(source, n) for n in names}
    align = {n: rest_s[n].inverted() @ rest_t[n] for n in names}
    hips_rest_t = target.matrix_world @ target.data.bones[HIPS].head_local
    hips_rest_s = source.matrix_world @ source.data.bones[HIPS].head_local
    hips_rest_arm_rot = target.data.bones[HIPS].matrix_local.to_quaternion()

    act_src = source.animation_data.action
    f0, f1 = (int(round(v)) for v in act_src.frame_range)
    scene = bpy.context.scene
    action = bpy.data.actions.new(clip_name)
    target.animation_data_create()
    target.animation_data.action = action
    if hasattr(target.animation_data, "action_slot") and action.slots:
        target.animation_data.action_slot = action.slots[0]
    for pb in target.pose.bones:
        pb.rotation_mode = "QUATERNION"
    prev = {}
    for f in range(f0, f1 + 1):
        scene.frame_set(f)
        desired = {}
        for n in names:
            desired[n] = (source.matrix_world @ source.pose.bones[n].matrix).to_quaternion() @ align[n]
        for n in names:
            parent = target.data.bones[n].parent
            if parent is None:
                basis = rest_t[n].inverted() @ desired[n]
            else:
                pr = desired.get(parent.name, rest_t[parent.name])
                basis = rest_t[n].inverted() @ rest_t[parent.name] @ pr.inverted() @ desired[n]
            if n in prev and prev[n].dot(basis) < 0:
                basis = -basis
            prev[n] = basis
            pb = target.pose.bones[n]
            pb.rotation_quaternion = basis
            pb.keyframe_insert("rotation_quaternion", frame=f, group=n)
        hips_world = hips_rest_t + (source.matrix_world @ source.pose.bones[HIPS].head - hips_rest_s) * ratio
        delta_arm = target.matrix_world.inverted().to_3x3() @ (hips_world - hips_rest_t)
        pb = target.pose.bones[HIPS]
        pb.location = hips_rest_arm_rot.inverted() @ delta_arm
        pb.keyframe_insert("location", frame=f, group=HIPS)
    target.animation_data.action = None
    track = target.animation_data.nla_tracks.new()
    track.name = clip_name
    track.strips.new(clip_name, f0, action).name = clip_name
    return f1 - f0 + 1


def main():
    bpy.ops.wm.open_mainfile(filepath=os.path.join(WORK, "claude_materials.blend"))
    target = bpy.data.objects["Human.rig"]
    ref, ref_objs = import_clip(os.path.join(MIXAMO, "fighting_idle.fbx"))
    ref.animation_data.action = None
    for pb in ref.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    match_rest_pose(target, ref)
    apply_pose_as_rest(target)
    ratio = (target.matrix_world @ target.data.bones[HIPS].head_local).z / (ref.matrix_world @ ref.data.bones[HIPS].head_local).z
    remove(ref_objs)
    print(f"[rig] T-pose rest applied; hip ratio {ratio:.3f}")

    clips = sorted(p for p in glob.glob(os.path.join(MIXAMO, "*.fbx")) if "with_skin" not in p)
    for path in clips:
        name = os.path.splitext(os.path.basename(path))[0]
        src, objs = import_clip(path)
        frames = retarget(target, src, name, ratio)
        src_action = src.animation_data.action
        remove(objs)
        if src_action:
            bpy.data.actions.remove(src_action)
        print(f"[rig] {name}: {frames} frames")
    bpy.context.scene.frame_set(0)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(WORK, "claude_rigged.blend"))
    print("[rig] done")


main()
