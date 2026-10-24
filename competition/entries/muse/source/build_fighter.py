import bpy, os, sys, math

BASE = "/home/hatch/workspace/dojo-build"
CLIPS = ['block','block_high','cross','crouch','fighting_idle','front_kick','getting_up',
 'hit_by_uppercut','hit_head_big','hit_head_light','hit_reaction','hook','jab','jab_cross','jump',
 'knocked_out','punch_combo','roundhouse_kick','side_kick','side_step_left','side_step_right',
 'step_backward','step_forward','taunt','uppercut','victory','walk_backward','walk_forward']

def clean():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def world_bbox(objs):
    import mathutils
    mn = mathutils.Vector((1e9,)*3); mx = mathutils.Vector((-1e9,)*3)
    dg = bpy.context.evaluated_depsgraph_get()
    for ob in objs:
        if ob.type != 'MESH': continue
        ev = ob.evaluated_get(dg)
        for v in ev.bound_box:
            w = ev.matrix_world @ mathutils.Vector(v)
            mn = mathutils.Vector(map(min, mn, w)); mx = mathutils.Vector(map(max, mx, w))
    return mn, mx

clean()
bpy.context.scene.render.fps = 30
bpy.ops.import_scene.fbx(filepath=f"{BASE}/assets/roster-muse.fbx")
arm = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
print("BASE ARMATURE:", arm.name, "bones:", len(arm.data.bones))
print("BASE MESHES:", [m.name for m in meshes])
mn, mx = world_bbox(meshes)
height = mx.z - mn.z
print(f"BASE BBOX: min={tuple(round(v,3) for v in mn)} max={tuple(round(v,3) for v in mx)} height={height:.3f}")

# Normalize height to 1.88 m via the armature OBJECT scale, never applied.
# Proven pattern (the house fighters): the exported root node keeps
# rotation + scale and no translation, geometry stays in FBX space
# (grounded, y 0..2.08), and the exporter writes matching inverse bind
# matrices. Baking scale/location into the geometry (transform_apply)
# produces a GLB that three.js frustum-culls into invisibility.
TARGET_H = 1.88
if abs(height - TARGET_H) > 0.01:
    s = TARGET_H / height
    arm.scale = tuple(c * s for c in arm.scale)
    print(f"ARMATURE SCALE SET (unapplied): {tuple(round(c,5) for c in arm.scale)}")

# Remove the roster idle action; we add the canonical 28 below
for a in list(bpy.data.actions):
    bpy.data.actions.remove(a)

# Import each clip, harvest its action, rename to the clip name
kept = {}
for clip in CLIPS:
    before_actions = set(bpy.data.actions)
    before_objects = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=f"{BASE}/assets/mixamo/{clip}.fbx")
    new_actions = [a for a in bpy.data.actions if a not in before_actions]
    new_objects = [o for o in bpy.context.scene.objects if o not in before_objects]
    if not new_actions:
        print("!! NO ACTION for", clip); continue
    act = new_actions[0]
    act.name = clip
    act.use_fake_user = True
    kept[clip] = (round(act.frame_range[0],1), round(act.frame_range[1],1))
    for o in new_objects:
        bpy.data.objects.remove(o, do_unlink=True)
    # drop any duplicate actions created by the import beyond the first
    for a in new_actions[1:]:
        bpy.data.actions.remove(a)
print("CLIPS KEPT:", kept)

# Put every action on its own NLA track so the glTF exporter emits 28 animations
arm.animation_data_create()
for clip in CLIPS:
    act = bpy.data.actions.get(clip)
    if not act: continue
    track = arm.animation_data.nla_tracks.new()
    track.name = clip
    strip = track.strips.new(clip, int(act.frame_range[0]), act)
    strip.name = clip
arm.animation_data.action = bpy.data.actions.get('fighting_idle')

os.makedirs(f"{BASE}/entry", exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=f"{BASE}/entry/source_muse_fighter.blend")
bpy.ops.export_scene.gltf(
    filepath=f"{BASE}/entry/fighter.glb",
    export_format='GLB',
    export_animations=True,
    export_animation_mode='NLA_TRACKS',
    export_nla_strips=True,
    export_yup=True,
    export_apply=False,
    export_image_format='AUTO',
)
print("EXPORT DONE")
