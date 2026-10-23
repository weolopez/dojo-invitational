"""
Turn the Mixamo roster bodies in assets/mixamo/roster/*.fbx into game-ready fighters with all 28 clips.
Run with:
  /Applications/Blender.app/Contents/MacOS/Blender --background --python build_roster.py
Writes dojo/public/fighters/<name>.glb for every roster body, plus me.glb copied from my_fighter.glb.
"""

import glob
import os
import shutil

import bpy

PROJECT_DIR = "/Users/weo/Development/3d"
MIXAMO_DIR = os.path.join(PROJECT_DIR, "assets", "mixamo")
ROSTER_DIR = os.path.join(MIXAMO_DIR, "roster")
OUT_DIR = os.path.join(PROJECT_DIR, "dojo", "public", "fighters")
XBOT_FBX = os.path.join(MIXAMO_DIR, "xbot_with_skin_fighting_idle.fbx")
MAX_TEXTURE = 1024
HIPS = "mixamorig:Hips"


def import_fbx(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    new_objs = set(bpy.data.objects) - before
    arm = next(o for o in new_objs if o.type == "ARMATURE")
    return arm, new_objs


def normalize_bone_names(arm):
    """Some Mixamo characters use prefixes like 'mixamorig1:'; the clips use 'mixamorig:'."""
    for bone in arm.data.bones:
        prefix, sep, rest = bone.name.partition(":")
        if sep and prefix != "mixamorig" and prefix.startswith("mixamorig"):
            bone.name = f"mixamorig:{rest}"


def hips_height(arm):
    return (arm.matrix_world @ arm.data.bones[HIPS].head_local).z


def load_clips():
    """Import every skeleton-only clip once and keep its action."""
    clips = {}
    for path in sorted(glob.glob(os.path.join(MIXAMO_DIR, "*.fbx"))):
        if "with_skin" in path:
            continue
        name = os.path.splitext(os.path.basename(path))[0]
        arm, objs = import_fbx(path)
        action = arm.animation_data.action
        action.name = f"src_{name}"
        action.use_fake_user = True
        clips[name] = action
        for o in objs:
            bpy.data.objects.remove(o, do_unlink=True)
    return clips


def scaled_copy(action, name, ratio):
    copy = action.copy()
    copy.name = name
    fcurves = copy.fcurves if hasattr(copy, "fcurves") else [
        fc for layer in copy.layers for strip in layer.strips for bag in strip.channelbags for fc in bag.fcurves]
    for fc in fcurves:
        if fc.data_path == f'pose.bones["{HIPS}"].location':
            for kp in fc.keyframe_points:
                kp.co.y *= ratio
                kp.handle_left.y *= ratio
                kp.handle_right.y *= ratio
    return copy


def shrink_textures():
    for img in bpy.data.images:
        if img.size[0] > MAX_TEXTURE or img.size[1] > MAX_TEXTURE:
            s = MAX_TEXTURE / max(img.size)
            img.scale(max(1, int(img.size[0] * s)), max(1, int(img.size[1] * s)))


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for path in sorted(glob.glob(os.path.join(ROSTER_DIR, "*.fbx"))):
        name = os.path.splitext(os.path.basename(path))[0]
        bpy.ops.wm.read_factory_settings(use_empty=True)
        xbot, _ = import_fbx(XBOT_FBX)
        xbot_hips = hips_height(xbot)
        clips = load_clips()
        build_fighter_in_place(name, path, clips, xbot_hips)
    shutil.copy(os.path.join(PROJECT_DIR, "my_fighter.glb"), os.path.join(OUT_DIR, "me.glb"))
    print("[roster] done")


def build_fighter_in_place(name, path, clips, xbot_hips):
    """Same scene as the loaded clips: drop the X Bot reference, then build this fighter."""
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for action in list(bpy.data.actions):
        if not action.name.startswith("src_"):
            bpy.data.actions.remove(action)
    arm, _ = import_fbx(path)
    normalize_bone_names(arm)
    for action in list(bpy.data.actions):
        if not action.name.startswith("src_"):
            bpy.data.actions.remove(action)
    ratio = hips_height(arm) / xbot_hips
    arm.animation_data_create()
    for clip, src in clips.items():
        act = scaled_copy(src, clip, ratio)
        arm.animation_data.action = act
        if hasattr(arm.animation_data, "action_slot") and act.slots:
            arm.animation_data.action_slot = act.slots[0]
        track = arm.animation_data.nla_tracks.new()
        track.name = clip
        track.strips.new(clip, int(act.frame_range[0]), act).name = clip
        arm.animation_data.action = None
    for action in list(bpy.data.actions):
        if action.name.startswith("src_"):
            bpy.data.actions.remove(action)
    shrink_textures()
    out = os.path.join(OUT_DIR, f"{name}.glb")
    bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", export_animations=True,
                              export_animation_mode="NLA_TRACKS", export_force_sampling=True)
    print(f"[roster] {name}: hips ratio {ratio:.3f}, {len(clips)} clips, {os.path.getsize(out) / 1e6:.1f} MB")


main()
