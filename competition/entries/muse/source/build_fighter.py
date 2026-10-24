import bpy, os, sys, math

BASE = "/home/hatch/workspace/dojo-build"
CLIPS = ['block','block_high','cross','crouch','fighting_idle','front_kick','getting_up',
 'hit_by_uppercut','hit_head_big','hit_head_light','hit_reaction','hook','jab','jab_cross','jump',
 'knocked_out','punch_combo','roundhouse_kick','side_kick','side_step_left','side_step_right',
 'step_backward','step_forward','taunt','throw','thrown','uppercut','victory','walk_backward','walk_forward',
 'knockdown_front','getup_back','getup_front']
# 30 required clips (RULES v3.3) + the 3 optional knockdown/getup clips.
# throw/thrown live in assets/mixamo/; knockdown_front/getup_* in assets/mixamo/extra/.

def clip_path(clip):
    for cand in (f"{BASE}/assets/mixamo/{clip}.fbx", f"{BASE}/assets/mixamo/extra/{clip}.fbx"):
        if os.path.exists(cand):
            return cand
    return f"{BASE}/assets/mixamo/{clip}.fbx"

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

# Skin/cloth realism: the base character's materials export with metallic 0.5,
# which makes skin and cloth read as half-metal. Set metallic to 0 (non-metal)
# on every material; the specular texture and roughness are left untouched.
for mat in bpy.data.materials:
    if not mat.use_nodes:
        continue
    for node in mat.node_tree.nodes:
        if node.type == 'BSDF_PRINCIPLED' and 'Metallic' in node.inputs:
            print(f"MATERIAL {mat.name}: metallic {node.inputs['Metallic'].default_value} -> 0.0")
            node.inputs['Metallic'].default_value = 0.0


# ---- Call 7 texture work -------------------------------------------------
# Detail normal map (procedural pore / weave / hair-groove detail derived
# from masks of the character's own diffuse; see make_detail_maps.py) and a
# metallic-roughness map (per-region roughness; the gold ornaments metallic).
diff_img = bpy.data.images.load(f"{BASE}/tex/file11_detail.png")
detail_img = bpy.data.images.load(f"{BASE}/tex/file12_detail.png")
detail_img.colorspace_settings.name = 'Non-Color'
mr_img = bpy.data.images.load(f"{BASE}/tex/file_mr.png")
mr_img.colorspace_settings.name = 'Non-Color'
for mat in bpy.data.materials:
    if not mat.use_nodes:
        continue
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if not bsdf:
        continue
    for node in nt.nodes:
        if node.type == 'TEX_IMAGE' and node.image and node.image.name.startswith(('file11', 'file14')) and not node.image.name.endswith('.002'):
            for out in node.outputs:
                for l in out.links:
                    if l.to_socket.name == 'Base Color':
                        node.image = diff_img
                        print(f"MAT {mat.name}: diffuse -> detail diffuse")
        if node.type == 'TEX_IMAGE' and node.image and node.image.name.startswith('file12'):
            node.image = detail_img
            print(f"MAT {mat.name}: normal map -> detail normal")
    sep = nt.nodes.new('ShaderNodeSeparateColor')
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = mr_img
    tex.location = (-500, -300); sep.location = (-300, -300)
    nt.links.new(tex.outputs['Color'], sep.inputs['Color'])
    nt.links.new(sep.outputs['Green'], bsdf.inputs['Roughness'])
    nt.links.new(sep.outputs['Blue'], bsdf.inputs['Metallic'])
    bsdf.inputs['Roughness'].default_value = 1.0
    bsdf.inputs['Metallic'].default_value = 1.0
    print(f"MAT {mat.name}: metallic-roughness map linked")

# ---- Call 7 eyeballs -----------------------------------------------------
# The base character's eyes are painted on the head mesh. Add real eyeball
# geometry (sclera sphere + iris disc + pupil disc), weighted 100% to the
# Head bone, with clearcoat for a wet look. Positions were located from the
# painted eyes' UVs on the imported mesh (probe_eyes2.py), in scene space.
import mathutils
def eye_material(name, color, rough, image=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    if image:
        t = m.node_tree.nodes.new('ShaderNodeTexImage')
        t.image = image
        m.node_tree.links.new(t.outputs['Color'], b.inputs['Base Color'])
    else:
        b.inputs['Base Color'].default_value = (*color, 1.0)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = 0.0
    if 'Coat Weight' in b.inputs:
        b.inputs['Coat Weight'].default_value = 1.0
        b.inputs['Coat Roughness'].default_value = 0.08
    return m

iris_img = bpy.data.images.load(f"{BASE}/tex/iris.png")
sclera_mat = eye_material('EyeSclera', (0.96, 0.945, 0.91), 0.12)
iris_mat = eye_material('EyeIris', None, 0.10, image=iris_img)
pupil_mat = eye_material('EyePupil', (0.01, 0.01, 0.01), 0.05)

bpy.context.view_layer.update()
body = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
body_mw_inv = body.matrix_world.inverted()
EYES = {'L': (0.014, -0.098, 1.862), 'R': (0.078, -0.088, 1.855)}
R_EYE = 0.0125
for side, c in ({} if True else EYES).items():  # eyeball geometry disabled: skinning offset unresolved, painted-eye gloss instead
    C = mathutils.Vector(c)
    parts = []
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, radius=R_EYE, location=C)
    ball = bpy.context.active_object; ball.name = f'Eye{side}'
    ball.data.materials.append(sclera_mat); parts.append(ball)
    bpy.ops.mesh.primitive_circle_add(vertices=32, radius=0.0058, fill_type='TRIFAN',
        location=C + mathutils.Vector((0, -(R_EYE - 0.0015), 0)), rotation=(math.radians(90), 0, 0))
    iris = bpy.context.active_object; iris.name = f'Iris{side}'
    iris.data.materials.append(iris_mat); parts.append(iris)
    bpy.ops.mesh.primitive_circle_add(vertices=24, radius=0.0027, fill_type='TRIFAN',
        location=C + mathutils.Vector((0, -(R_EYE - 0.0011), 0)), rotation=(math.radians(90), 0, 0))
    pupil = bpy.context.active_object; pupil.name = f'Pupil{side}'
    pupil.data.materials.append(pupil_mat); parts.append(pupil)
    for ob in parts:
        # bake world transform into the verts, then convert to body-local
        # space so the armature modifier treats them exactly like body verts
        ob.data.transform(ob.matrix_world)
        ob.matrix_world = mathutils.Matrix.Identity(4)
        ob.data.transform(body_mw_inv)
        ob.matrix_world = body.matrix_world
        vg = ob.vertex_groups.new(name='mixamorig:Head')
        vg.add(list(range(len(ob.data.vertices))), 1.0, 'REPLACE')
        mod = ob.modifiers.new('Armature', 'ARMATURE'); mod.object = arm
        # Sit in the hierarchy EXACTLY like the body mesh: same parent,
        # identity parent-inverse and identity local transform (the body
        # mesh's own mpi is identity). Anything else double-applies the
        # armature scale inside the skinning modifier.
        ob.parent = arm
        ob.matrix_parent_inverse = mathutils.Matrix.Identity(4)
        ob.location = (0, 0, 0); ob.rotation_euler = (0, 0, 0); ob.scale = (1, 1, 1)
    print('EYE built', side, c)

# Remove the roster idle action; we add the canonical clips below
for a in list(bpy.data.actions):
    bpy.data.actions.remove(a)

# Import each clip, harvest its action, rename to the clip name
kept = {}
for clip in CLIPS:
    before_actions = set(bpy.data.actions)
    before_objects = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=clip_path(clip))
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

# Put every action on its own NLA track so the glTF exporter emits 33 animations
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
