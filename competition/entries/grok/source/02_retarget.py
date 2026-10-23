# Step 2: retarget all 28 Mixamo clips (assets/mixamo/*.fbx, read-only) onto the MPFB mixamo rig.
# Per bone: R_tgt(t) = R_src(t) * R_src_rest^-1 * Q_align * R_tgt_rest (world space), where Q_align turns the
# target rest bone onto the source rest bone direction (A-pose -> T-pose). Hips translation scaled by hip height.
import bpy, glob, os, sys
from mathutils import Matrix, Vector, Quaternion
HERE = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = "/Users/weo/Development/3d/assets/mixamo"
CLIPS = ['block','block_high','cross','crouch','fighting_idle','front_kick','getting_up','hit_by_uppercut','hit_head_big',
 'hit_head_light','hit_reaction','hook','jab','jab_cross','jump','knocked_out','punch_combo','roundhouse_kick','side_kick',
 'side_step_left','side_step_right','step_backward','step_forward','taunt','uppercut','victory','walk_backward','walk_forward']
only = [a for a in sys.argv[sys.argv.index('--')+1:]] if '--' in sys.argv else []
infile = os.path.join(HERE, '..', 'tmp', 'human.blend')
bpy.ops.wm.open_mainfile(filepath=infile)
scene = bpy.context.scene
scene.render.fps = 30
rig = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
rig.animation_data_create()
tb = rig.data.bones
order = []
def walk(b):
    order.append(b.name); [walk(c) for c in b.children]
for b in tb:
    if b.parent is None: walk(b)
Rw = rig.matrix_world
T_rest = {b.name: Rw @ b.matrix_local for b in tb}
for clip in (only or CLIPS):
    bpy.ops.import_scene.fbx(filepath=os.path.join(SRC_DIR, clip + '.fbx'))
    src = [o for o in bpy.context.selected_objects if o.type == 'ARMATURE'][0]
    sact = src.animation_data.action
    f0, f1 = [int(round(x)) for x in sact.frame_range]
    S_rest = {b.name: src.matrix_world @ b.matrix_local for b in src.data.bones}
    hip_ratio = T_rest['mixamorig:Hips'].translation.z / S_rest['mixamorig:Hips'].translation.z
    C = {}
    for n in order:
        if n not in S_rest: continue
        tr = T_rest[n].to_quaternion(); sr = S_rest[n].to_quaternion()
        tdir = (T_rest[n].to_3x3() @ Vector((0, 1, 0))).normalized()
        sdir = (S_rest[n].to_3x3() @ Vector((0, 1, 0))).normalized()
        qa = tdir.rotation_difference(sdir)
        C[n] = sr.inverted() @ qa @ tr
    frames = {}
    for f in range(f0, f1 + 1):
        scene.frame_set(f)
        frames[f] = {n: (src.matrix_world @ src.pose.bones[n].matrix) for n in C}
    act = bpy.data.actions.new(clip)
    act.use_fake_user = True
    rig.animation_data.action = act
    for pb in rig.pose.bones: pb.rotation_mode = 'QUATERNION'
    prevq = {}
    for f in range(f0, f1 + 1):
        M = {}
        for n in order:
            b = tb[n]
            if n in C:
                rot = frames[f][n].to_quaternion() @ C[n]
            else:
                rot = None
            if b.parent is None:
                head = frames[f][n].translation * hip_ratio if n in C else T_rest[n].translation
                head = head.copy()
            else:
                off = T_rest[b.parent.name].inverted() @ T_rest[n]
                head = (M[b.parent.name] @ off).translation
                if rot is None:
                    rot = (M[b.parent.name] @ off).to_quaternion()
            M[n] = Matrix.Translation(head) @ rot.to_matrix().to_4x4()
            pb = rig.pose.bones[n]
            if b.parent is None:
                basis = T_rest[n].inverted() @ M[n]
            else:
                basis = (T_rest[b.parent.name].inverted() @ T_rest[n]).inverted() @ M[b.parent.name].inverted() @ M[n]
            q = basis.to_quaternion()
            if n in prevq and prevq[n].dot(q) < 0: q.negate()
            prevq[n] = q
            pb.rotation_quaternion = q
            pb.keyframe_insert('rotation_quaternion', frame=f - f0 + 1, group=n)
            if b.parent is None:
                pb.location = basis.translation
                pb.keyframe_insert('location', frame=f - f0 + 1, group=n)
    print("CLIP", clip, f1 - f0 + 1, "frames")
    # remove source
    for o in list(bpy.context.selected_objects): bpy.data.objects.remove(o)
    bpy.data.actions.remove(sact)
rig.animation_data.action = bpy.data.actions.get('fighting_idle')
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, '..', 'tmp', 'rigged.blend'))
