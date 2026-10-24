import os, sys, bpy
from mathutils import Matrix, Vector
MIXAMO = "/workspace/dojo-invitational/assets/mixamo"
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=sys.argv[-2])
for o in list(bpy.data.objects):
    if o.name.startswith('Icosphere'): bpy.data.objects.remove(o)
scene = bpy.context.scene
scene.render.fps = 30
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
rig.animation_data_create()
to_rig = rig.matrix_world.inverted()
def hierarchy(bones):
    order = []

    def walk(b):
        order.append(b)
        for c in b.children:
            walk(c)
    for b in bones:
        if b.parent is None:
            walk(b)
    return order


order = hierarchy(rig.data.bones)
tgt_rest = {b.name: b.matrix_local.copy() for b in order}  # armature space
for pb in rig.pose.bones:
    pb.rotation_mode = "QUATERNION"

clips = ["throw","thrown"]+[("extra/"+c) for c in ["knockdown_front","getup_back","getup_front"]]
for clip in clips:
    bpy.ops.import_scene.fbx(filepath=os.path.join(MIXAMO, clip + ".fbx"))
    imported = list(bpy.context.selected_objects)
    src = next(o for o in imported if o.type == "ARMATURE")
    src_action = src.animation_data.action
    f0, f1 = (int(round(x)) for x in src_action.frame_range)

    # source matrices expressed in the target armature's space
    to_tgt = to_rig @ src.matrix_world
    src_rest = {b.name: to_tgt @ b.matrix_local for b in src.data.bones}
    hip_ratio = tgt_rest["mixamorig:Hips"].translation.z / src_rest["mixamorig:Hips"].translation.z
    correction = {}
    for b in order:
        if b.name not in src_rest:
            continue
        t_dir = (tgt_rest[b.name].to_3x3() @ Vector((0, 1, 0))).normalized()
        s_dir = (src_rest[b.name].to_3x3() @ Vector((0, 1, 0))).normalized()
        align = t_dir.rotation_difference(s_dir)
        correction[b.name] = src_rest[b.name].to_quaternion().inverted() @ align @ tgt_rest[b.name].to_quaternion()

    action = bpy.data.actions.new(clip.split("/")[-1])
    action.use_fake_user = True
    rig.animation_data.action = action
    previous = {}
    for f in range(f0, f1 + 1):
        scene.frame_set(f)
        posed = {}  # armature-space rotation of every target bone this frame
        for b in order:
            pb = rig.pose.bones[b.name]
            if b.name in correction:
                rot = (to_tgt @ src.pose.bones[b.name].matrix).to_quaternion() @ correction[b.name]
            else:
                parent_rest = tgt_rest[b.parent.name].to_quaternion() if b.parent else None
                rot = posed[b.parent.name] @ parent_rest.inverted() @ tgt_rest[b.name].to_quaternion() if b.parent \
                    else tgt_rest[b.name].to_quaternion()
            posed[b.name] = rot
            if b.parent:
                local_rest = tgt_rest[b.parent.name].to_quaternion().inverted() @ tgt_rest[b.name].to_quaternion()
                basis = local_rest.inverted() @ posed[b.parent.name].inverted() @ rot
            else:
                basis = tgt_rest[b.name].to_quaternion().inverted() @ rot
            if b.name in previous and previous[b.name].dot(basis) < 0:
                basis.negate()
            previous[b.name] = basis
            pb.rotation_quaternion = basis
            pb.keyframe_insert("rotation_quaternion", frame=f - f0 + 1, group=b.name)
            if b.parent is None and b.name in correction:
                head = (to_tgt @ src.pose.bones[b.name].matrix).translation * hip_ratio
                pose = Matrix.Translation(head) @ rot.to_matrix().to_4x4()
                pb.location = (tgt_rest[b.name].inverted() @ pose).translation
                pb.keyframe_insert("location", frame=f - f0 + 1, group=b.name)
    print(f"[retarget] {clip.split('/')[-1]} {f1 - f0 + 1} frames")
    for o in imported:
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.actions.remove(src_action)

rig.animation_data.action = None
new=set(c.split('/')[-1] for c in clips)
for a in list(bpy.data.actions):
    if a.name not in new: bpy.data.actions.remove(a)
for n in [c.split('/')[-1] for c in clips]:
    for fc in bpy.data.actions[n].fcurves:
        for k in fc.keyframe_points: k.interpolation='LINEAR'
for o in bpy.data.objects:
    if o.type=="ARMATURE" and o!=rig: bpy.data.objects.remove(o)
bpy.ops.export_scene.gltf(filepath=sys.argv[-1],export_format='GLB',export_animation_mode='ACTIONS',export_force_sampling=False,export_def_bones=False,export_image_format='AUTO')
