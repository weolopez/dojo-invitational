import bpy, os, math
from mathutils import Vector
BASE = "/home/hatch/workspace/dojo-build"
OUT = f"{BASE}/call7_hourly"
CLIPS = ['block','block_high','cross','crouch','fighting_idle','front_kick','getting_up',
 'hit_by_uppercut','hit_head_big','hit_head_light','hit_reaction','hook','jab','jab_cross','jump',
 'knocked_out','punch_combo','roundhouse_kick','side_kick','side_step_left','side_step_right',
 'step_backward','step_forward','taunt','throw','thrown','uppercut','victory','walk_backward','walk_forward',
 'knockdown_front','getup_back','getup_front']
def clip_path(clip):
    for cand in (f"{BASE}/assets/mixamo/{clip}.fbx", f"{BASE}/assets/mixamo/extra/{clip}.fbx"):
        if os.path.exists(cand): return cand
    return f"{BASE}/assets/mixamo/{clip}.fbx"
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.fps = 30
bpy.ops.import_scene.fbx(filepath=f"{BASE}/assets/roster-muse.fbx")
arm = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
body = meshes[0]
print("BASE ARMATURE:", arm.name, "bones:", len(arm.data.bones))
def world_bbox(objs):
    mn = Vector((1e9,)*3); mx = Vector((-1e9,)*3)
    dg = bpy.context.evaluated_depsgraph_get()
    for ob in objs:
        if ob.type != 'MESH': continue
        ev = ob.evaluated_get(dg)
        for v in ev.bound_box:
            w = ev.matrix_world @ Vector(v)
            mn = Vector(map(min, mn, w)); mx = Vector(map(max, mx, w))
    return mn, mx
mn, mx = world_bbox(meshes)
height = mx.z - mn.z
print(f"BASE BBOX height={height:.3f}")
if abs(height - 1.88) > 0.01:
    s = 1.88 / height
    arm.scale = tuple(c * s for c in arm.scale)
    print(f"ARMATURE SCALE SET: {tuple(round(c,5) for c in arm.scale)}")
# Materials
pore_img = bpy.data.images.load(f"{BASE}/call7_assets/pore_normal.png"); pore_img.name = "pore_normal"
for mat in bpy.data.materials:
    if not mat.use_nodes: continue
    for node in mat.node_tree.nodes:
        if node.type == 'BSDF_PRINCIPLED':
            if 'Metallic' in node.inputs: node.inputs['Metallic'].default_value = 0.0
            if 'Roughness' in node.inputs: node.inputs['Roughness'].default_value = 0.68
            if 'Subsurface Weight' in node.inputs: node.inputs['Subsurface Weight'].default_value = 0.35
        if node.type == 'NORMAL_MAP':
            for link in node.inputs['Color'].links:
                src = link.from_node
                if src.type == 'TEX_IMAGE':
                    print(f"MAT {mat.name}: normal -> pore_normal"); src.image = pore_img
# --- Eyes at REST pose, before any clip/NLA exists (probe-validated) ---
bpy.context.view_layer.update()
inv = arm.matrix_world.inverted()
def make_material(name, base, rough, tex=None, coat_w=0.0, coat_r=0.1):
    mat = bpy.data.materials.new(name); mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs['Base Color'].default_value = base
    if 'Metallic' in bsdf.inputs: bsdf.inputs['Metallic'].default_value = 0.0
    if 'Roughness' in bsdf.inputs: bsdf.inputs['Roughness'].default_value = rough
    if 'Coat Weight' in bsdf.inputs: bsdf.inputs['Coat Weight'].default_value = coat_w
    if 'Coat Roughness' in bsdf.inputs: bsdf.inputs['Coat Roughness'].default_value = coat_r
    if tex:
        tn = mat.node_tree.nodes.new('ShaderNodeTexImage'); tn.image = bpy.data.images.load(tex)
        mat.node_tree.links.new(tn.outputs['Color'], bsdf.inputs['Base Color'])
    mat.use_backface_culling = False
    return mat
eye_white = make_material("EyeWhite", (0.96, 0.96, 0.94, 1.0), 0.15, coat_w=0.6, coat_r=0.08)
iris_mat = make_material("Iris", (1.0, 1.0, 1.0, 1.0), 0.22, tex=f"{BASE}/call7_assets/iris.png", coat_w=0.7, coat_r=0.05)
def add_skinned_mesh(name, verts, faces, uvs, mat, bone_name):
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    if uvs:
        uv_layer = me.uv_layers.new(name="map1")
        for i, uv in enumerate(uvs): uv_layer.data[i].uv = uv
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    ob.parent = arm
    mod = ob.modifiers.new(name='Armature', type='ARMATURE'); mod.object = arm
    grp = ob.vertex_groups.new(name=bone_name); grp.add(list(range(len(verts))), 1.0, 'REPLACE')
    me.materials.append(mat); return ob
def sphere_verts(center, radius, seg=24, rings=16):
    verts = []
    for j in range(rings+1):
        phi = math.pi * j / rings
        for i in range(seg):
            th = 2*math.pi * i / seg
            verts.append((center.x + radius*math.sin(phi)*math.cos(th), center.y + radius*math.sin(phi)*math.sin(th), center.z + radius*math.cos(phi)))
    faces = []
    for j in range(rings):
        for i in range(seg):
            a = j*seg + i; b = j*seg + (i+1)%seg; c = (j+1)*seg + (i+1)%seg; d = (j+1)*seg + i
            if j == 0: faces.append((a, c, d))
            elif j == rings-1: faces.append((a, b, c))
            else: faces.append((a, b, c, d))
    return verts, faces
leye_fwd = None
for bone_name in []:  # eyes disabled: separate balls occlude/regress vs painted eyes; see NOTES
    pb = arm.pose.bones[bone_name]
    bone_center = inv @ (arm.matrix_world @ pb.head)
    near = sorted(body.data.vertices, key=lambda v: (Vector(v.co) - bone_center).length)[:12]
    avg_pos = Vector((0,0,0)); avg_n = Vector((0,0,0))
    for v in near: avg_pos += Vector(v.co); avg_n += Vector(v.normal)
    avg_pos /= len(near); avg_n.normalize()
    nearest = (Vector(near[0].co) - bone_center).length
    if nearest < 1.2:
        center = bone_center; fwd = avg_n
    else:
        # Reye bone floats ~2.5 in front of the socket: anchor the sphere to the
        # face surface instead, still skinned 100% to the eye bone so it tracks.
        center = avg_pos + avg_n * 0.65; fwd = None
    if bone_name.endswith('Leye'):
        leye_fwd = fwd
    else:
        fwd = Vector((-leye_fwd.x, leye_fwd.y, leye_fwd.z)); fwd.normalize()
    print(f"EYE {bone_name} bone {tuple(round(v,2) for v in bone_center)} center {tuple(round(v,2) for v in center)} forward {tuple(round(v,3) for v in fwd)} nearest {round(nearest,2)}")
    right = fwd.cross(Vector((0,1,0))); right.normalize()
    up2 = right.cross(fwd); up2.normalize()
    sv, sf = sphere_verts(center, 1.35)
    add_skinned_mesh(f"Eye_{bone_name.split(':')[1]}", sv, sf, None, eye_white, bone_name)
    R = 1.37; IR = 0.60; N = 24
    iverts = [tuple(center)]; iuvs = [(0.5, 0.5)]
    for i in range(N):
        ang = 2*math.pi*i/N; u = IR*math.cos(ang); v = IR*math.sin(ang)
        zc = math.sqrt(max(R*R - u*u - v*v, 0.01))
        p = center + right*u + up2*v + fwd*zc
        iverts.append(tuple(p)); iuvs.append((0.5 + u/(2*IR), 0.5 + v/(2*IR)))
    ifaces = [(0, 1+(i+1)%N, 1+i) for i in range(N)]
    add_skinned_mesh(f"Iris_{bone_name.split(':')[1]}", iverts, ifaces, iuvs, iris_mat, bone_name)
# --- Clips ---
for a in list(bpy.data.actions): bpy.data.actions.remove(a)
kept = {}
for clip in CLIPS:
    before_actions = set(bpy.data.actions); before_objects = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=clip_path(clip))
    new_actions = [a for a in bpy.data.actions if a not in before_actions]
    new_objects = [o for o in bpy.context.scene.objects if o not in before_objects]
    if not new_actions: print("!! NO ACTION for", clip); continue
    act = new_actions[0]; act.name = clip; act.use_fake_user = True
    kept[clip] = (round(act.frame_range[0],1), round(act.frame_range[1],1))
    for o in new_objects: bpy.data.objects.remove(o, do_unlink=True)
    for a in new_actions[1:]: bpy.data.actions.remove(a)
print("CLIPS KEPT:", kept)
arm.animation_data_create()
for clip in CLIPS:
    act = bpy.data.actions.get(clip)
    if not act: continue
    track = arm.animation_data.nla_tracks.new(); track.name = clip
    strip = track.strips.new(clip, int(act.frame_range[0]), act); strip.name = clip
arm.animation_data.action = bpy.data.actions.get('fighting_idle')
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=f"{OUT}/source_muse_fighter.blend")
bpy.ops.export_scene.gltf(filepath=f"{OUT}/fighter.glb", export_format='GLB', export_animations=True,
    export_animation_mode='NLA_TRACKS', export_nla_strips=True, export_yup=True, export_apply=False, export_image_format='AUTO')
print("EXPORT DONE")
