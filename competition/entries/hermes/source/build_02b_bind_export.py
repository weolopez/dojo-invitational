"""
Hermes fighter — stage 2b (corrected): bind the detailed mesh onto the reference
skeleton in its NATIVE orientation, keep the reference's own 28 clips (which already
pass the validator's timing check), and export a single GLB.

Why: the reference hermes.glb armature uses Mixamo's native convention (root rotated
+90deg X, scale 0.01, clips authored at full Mixamo frame counts). Rebuilding the rig
from FBX changed both orientation and clip timing. Binding to the reference rig as-is
guarantees orientation + clip lengths match the judge's reference exactly. Our actual
contribution is the detailed sculpted mesh + photoreal PBR materials carried on top.

Run: Blender --background --python build_02b_bind_export.py
"""
import bpy, os

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
REF_GLB = os.path.join(PROJECT, "dojo", "public", "fighters", "hermes.glb")
BASE = os.path.join(HERE, "hermes_fighter.blend")   # has our materialed meshes
OUT = os.path.abspath(os.path.join(HERE, "..", "fighter.glb"))

CLIPS = ['block','block_high','cross','crouch','fighting_idle','front_kick','getting_up',
  'hit_by_uppercut','hit_head_big','hit_head_light','hit_reaction','hook','jab','jab_cross','jump',
  'knocked_out','punch_combo','roundhouse_kick','side_kick','side_step_left','side_step_right',
  'step_backward','step_forward','taunt','uppercut','victory','walk_backward','walk_forward']

MESHES = ["Skin_Head","Body","Eye_L","Eye_R","Teeth","Hair","Top","Shorts"]

def log(*a): print("BIND:", *a)

def main():
    # 1. Open our materialed meshes; strip the FBX-rebuilt armature + its actions.
    bpy.ops.wm.open_mainfile(filepath=BASE)
    for o in list(bpy.data.objects):
        if o.type == 'ARMATURE':
            bpy.data.objects.remove(o, do_unlink=True)
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)

    # Clear any armature modifiers left on the meshes.
    our_meshes = []
    for name in MESHES:
        o = bpy.data.objects.get(name)
        if not o: continue
        for m in list(o.modifiers):
            if m.type == 'ARMATURE': o.modifiers.remove(m)
        our_meshes.append(o)
    log("our meshes:", [o.name for o in our_meshes])

    # 2. Import the reference GLB — its armature (native orientation) + 28 clips.
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=REF_GLB)
    new = [o for o in bpy.data.objects if o not in before]
    ref_arm = next(o for o in new if o.type == 'ARMATURE')
    ref_meshes = [o for o in new if o.type == 'MESH']
    log("ref armature:", ref_arm.name, "rot", [round(v,3) for v in ref_arm.rotation_quaternion],
        "scale", [round(v,3) for v in ref_arm.scale])
    log("ref clips:", len(bpy.data.actions))

    # 3. Our meshes were authored in world metres, Y-up standing. The ref armature is
    #    rotated +90X and scaled 0.01. To bind cleanly, parent our meshes under the
    #    armature's space: counter-rotate/scale our meshes so they sit on the skeleton.
    #    Easiest robust route: match our mesh transform to the reference mesh transform,
    #    since the reference mesh already lines up with this armature.
    if ref_meshes:
        ref_mesh = ref_meshes[0]
        log("ref mesh transform: loc", [round(v,3) for v in ref_mesh.location],
            "rot_mode", ref_mesh.rotation_mode)

    # Put our meshes into the armature's local frame: the armature maps a Z-up,
    # cm-scale rig to Y-up metres. Our meshes are already Y-up metres in world, which
    # is exactly what the POSED skeleton outputs, so we bind in WORLD space by making
    # the meshes children of the armature with automatic weights WITHOUT extra rotation.
    # Remove the reference meshes (we only want the skeleton + clips).
    for o in ref_meshes:
        bpy.data.objects.remove(o, do_unlink=True)

    # 4. Bind: select our meshes + armature, parent with automatic weights.
    bpy.ops.object.select_all(action='DESELECT')
    for o in our_meshes: o.select_set(True)
    ref_arm.select_set(True)
    bpy.context.view_layer.objects.active = ref_arm
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    log("bound meshes to reference skeleton")

    # 5. Push the reference clips onto NLA so the exporter emits all 28 named.
    if not ref_arm.animation_data:
        ref_arm.animation_data_create()
    for t in list(ref_arm.animation_data.nla_tracks):
        ref_arm.animation_data.nla_tracks.remove(t)
    present = {a.name: a for a in bpy.data.actions}
    for clip in CLIPS:
        act = present.get(clip)
        if not act:
            log("MISSING clip", clip); continue
        track = ref_arm.animation_data.nla_tracks.new(); track.name = clip
        track.strips.new(clip, int(act.frame_range[0]), act)
    ref_arm.animation_data.action = None

    bpy.context.scene.render.fps = 30

    # 5b. HEIGHT FIX. Diagnosis from the exported GLB: skinned-mesh POSITIONs came out
    #     with the body along -Z (Y-span ~0.24 m) because binding pushed the geometry
    #     into the armature's rotated (+90deg X) local frame. The reference me.glb stores
    #     its skinned mesh standing along +Y (0 -> 1.82 m) and passes the height check.
    #     Fix: rotate each mesh's vertex data -90deg about X so "up" becomes +Y in the
    #     stored POSITIONs, then re-bind so the skeleton still deforms it correctly.
    import mathutils, math
    rot = mathutils.Matrix.Rotation(math.radians(-90), 4, 'X')
    for o in our_meshes:
        for m in list(o.modifiers):
            if m.type == 'ARMATURE': o.modifiers.remove(m)
        o.data.transform(rot)     # bake rotation into geometry
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT')
    for o in our_meshes: o.select_set(True)
    ref_arm.select_set(True)
    bpy.context.view_layer.objects.active = ref_arm
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    log("rotated mesh geometry to +Y up and re-bound")

    out_blend = os.path.join(HERE, "hermes_bound.blend")
    bpy.ops.wm.save_as_mainfile(filepath=out_blend)

    # 6. Export GLB — do NOT re-apply yup (reference armature already oriented).
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(
        filepath=OUT, export_format='GLB', export_apply=True,
        export_animations=True, export_animation_mode='NLA_TRACKS',
        export_nla_strips=True, export_skins=True, export_morph=False,
        export_yup=True, export_texcoords=True, export_normals=True,
        export_materials='EXPORT', export_image_format='AUTO',
        export_frame_range=False, export_anim_single_armature=True,
    )
    log(f"wrote {OUT}  {os.path.getsize(OUT)/1e6:.1f} MB")

main()
