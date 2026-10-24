"""
The arena's lending library: Mixamo's X Bot with the clips the arena lends to fighters that don't ship their own
(dojo/src/lent.js): fighting_idle (the shared reference stance), the paired throw, and the extras in
assets/mixamo/extra/ (getup_back, getup_front, knockdown_front).
Run with:
  /Applications/Blender.app/Contents/MacOS/Blender --background --python build_lent_clips.py
Writes dojo/public/fighters/lent.glb.
"""
import glob
import os

import bpy

PROJECT_DIR = "/Users/weo/Development/3d"
MIXAMO_DIR = os.path.join(PROJECT_DIR, "assets", "mixamo")
OUT = os.path.join(PROJECT_DIR, "dojo", "public", "fighters", "lent.glb")
CLIPS = [os.path.join(MIXAMO_DIR, f"{n}.fbx") for n in ("throw", "thrown")] + sorted(
    glob.glob(os.path.join(MIXAMO_DIR, "extra", "*.fbx")))


def import_fbx(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    new_objs = set(bpy.data.objects) - before
    return next(o for o in new_objs if o.type == "ARMATURE"), new_objs


def add_track(arm, name, action):
    action.name = name
    arm.animation_data.action = action
    if hasattr(arm.animation_data, "action_slot") and action.slots:
        arm.animation_data.action_slot = action.slots[0]
    track = arm.animation_data.nla_tracks.new()
    track.name = name
    track.strips.new(name, int(action.frame_range[0]), action).name = name
    arm.animation_data.action = None


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    arm, _ = import_fbx(os.path.join(MIXAMO_DIR, "xbot_with_skin_fighting_idle.fbx"))
    arm.animation_data_create()
    add_track(arm, "fighting_idle", arm.animation_data.action)
    for path in CLIPS:
        src, objs = import_fbx(path)
        action = src.animation_data.action
        action.use_fake_user = True
        for o in objs:
            bpy.data.objects.remove(o, do_unlink=True)
        add_track(arm, os.path.splitext(os.path.basename(path))[0], action)
    bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", export_animations=True,
                              export_animation_mode="NLA_TRACKS", export_force_sampling=True)
    print(f"[lent] {len(CLIPS) + 1} clips, {os.path.getsize(OUT) / 1e6:.1f} MB")


main()
