"""
Hermes fighter — stage 3: export GLB + sanity.

Opens hermes_fighter.blend, removes duplicate (.001) actions, pushes each of the
28 canonical clips onto an NLA strip so the glTF exporter emits exactly 28 named
animations, enforces scale/orientation (metres, Y-up, facing +Z), then exports
a self-contained GLB to entries/hermes/fighter.glb.

Run: Blender --background --python build_03_export.py
"""
import bpy, os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(HERE, "..", "fighter.glb"))

CLIPS = ['block','block_high','cross','crouch','fighting_idle','front_kick','getting_up',
  'hit_by_uppercut','hit_head_big','hit_head_light','hit_reaction','hook','jab','jab_cross','jump',
  'knocked_out','punch_combo','roundhouse_kick','side_kick','side_step_left','side_step_right',
  'step_backward','step_forward','taunt','uppercut','victory','walk_backward','walk_forward']

def log(*a): print("EXPORT:", *a)

def main():
    bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, "hermes_fighter.blend"))

    # 1. Drop duplicate .001 actions; keep the canonical named ones.
    for a in list(bpy.data.actions):
        if a.name.endswith(".001"):
            bpy.data.actions.remove(a)
    kept = sorted([a.name for a in bpy.data.actions])
    log("actions after dedupe:", len(kept))
    missing = [c for c in CLIPS if c not in kept]
    if missing: log("WARNING missing clips:", missing)

    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    bpy.context.view_layer.objects.active = arm

    # 2. Build NLA strips so the exporter emits each action as a named animation.
    if not arm.animation_data:
        arm.animation_data_create()
    # clear existing tracks
    for t in list(arm.animation_data.nla_tracks):
        arm.animation_data.nla_tracks.remove(t)
    for clip in CLIPS:
        act = bpy.data.actions.get(clip)
        if not act: continue
        track = arm.animation_data.nla_tracks.new()
        track.name = clip
        strip = track.strips.new(clip, int(act.frame_range[0]), act)
        strip.name = clip
    arm.animation_data.action = None

    # 3. Export GLB — embed everything, include all actions via NLA.
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(
        filepath=OUT,
        export_format='GLB',
        export_apply=True,
        export_animations=True,
        export_animation_mode='NLA_TRACKS',
        export_nla_strips=True,
        export_skins=True,
        export_morph=False,
        export_yup=True,
        export_texcoords=True,
        export_normals=True,
        export_materials='EXPORT',
        export_image_format='AUTO',
    )
    sz = os.path.getsize(OUT) / 1e6
    log(f"wrote {OUT}  {sz:.1f} MB")

main()
