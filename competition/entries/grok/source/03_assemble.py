# Assemble final fighter: bake shape keys, subdivide, build body-derived clothing, PBR materials, cornea, export GLB.
import bpy, bmesh, os, sys
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
TEX = os.path.join(ROOT, 'tmp', 'tex')
bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, 'tmp', 'rigged.blend'))
rig = bpy.data.objects['Human.rig_export']
body = bpy.data.objects['Human_export']
def activate(o):
    bpy.ops.object.mode_set(mode='OBJECT') if bpy.context.object and bpy.context.object.mode != 'OBJECT' else None
    for x in bpy.context.selected_objects: x.select_set(False)
    o.select_set(True); bpy.context.view_layer.objects.active = o
# 1. bake shape keys + subdivide everything (subsurf first in stack, then apply)
for o in [x for x in bpy.data.objects if x.type == 'MESH']:
    activate(o)
    if o.data.shape_keys: bpy.ops.object.shape_key_remove(all=True, apply_mix=True)
    for m in list(o.modifiers):
        if m.type == 'SUBSURF': o.modifiers.remove(m)
    lvl = 1
    if 'tongue' in o.name or 'teeth' in o.name: lvl = 0
    if lvl:
        m = o.modifiers.new('sub', 'SUBSURF'); m.levels = lvl; m.render_levels = lvl
        bpy.ops.object.modifier_move_to_index(modifier='sub', index=0)
        bpy.ops.object.modifier_apply(modifier='sub')
tongue = bpy.data.objects['Human.tongue01_export']
bpy.data.objects.remove(bpy.data.objects['Human.short02_export'])
# 2. clothing masks from bone weights + rest positions
bones = {b.name: b for b in rig.data.bones}
def bz(n): return (rig.matrix_world @ bones['mixamorig:' + n].head_local)
me = body.data
gi = {g.index: g.name.replace('mixamorig:', '') for g in body.vertex_groups}
W = []
for v in me.vertices:
    d = {}
    for g in v.groups:
        n = gi.get(g.group)
        if n: d[n] = d.get(n, 0) + g.weight
    W.append(d)
def w(i, *names): return sum(W[i].get(k, 0) for side in ('Left', 'Right') for k in [side + n for n in names]) + sum(W[i].get(n, 0) for n in names)
hipz = bz('Hips').z; kneez = bz('LeftLeg').z; neckz = bz('Neck').z
mw = body.matrix_world
P = [mw @ v.co for v in me.vertices]
arm_x = abs(bz('LeftArm').x)
fingers = ('HandThumb1','HandThumb2','HandThumb3','HandIndex1','HandIndex2','HandIndex3','HandMiddle1','HandMiddle2','HandMiddle3','HandRing1','HandRing2','HandRing3','HandPinky1','HandPinky2','HandPinky3')
def m_shorts(i):
    p = P[i]; return kneez + 0.17 < p.z < hipz + 0.085 and w(i, 'ForeArm', 'Hand', 'Arm', *fingers) < 0.01
def m_shirt(i):
    p = P[i]
    if w(i, 'ForeArm', 'Hand', *fingers) > 0.02: return False
    if abs(p.x) > arm_x + 0.13: return False
    return hipz - 0.02 < p.z < neckz - 0.035
def m_wrap(i):
    hand = w(i, 'Hand'); fa = w(i, 'ForeArm')
    if w(i, *fingers) > 0.35: return False
    hb = [bz('LeftHand'), bz('RightHand')]
    near = min((P[i] - h).length for h in hb) < 0.085
    return hand > 0.4 or (fa > 0.2 and near)
masks = {k: [f(i) for i in range(len(me.vertices))] for k, f in [('shorts', m_shorts), ('shirt', m_shirt), ('wrap', m_wrap)]}
def make_garment(name, mask, offset, thick, folds=0.0, smooth_it=3):
    activate(body); bpy.ops.object.duplicate(); g = bpy.context.object; g.name = name
    bm = bmesh.new(); bm.from_mesh(g.data)
    bm.verts.ensure_lookup_table()
    kill = [f for f in bm.faces if not all(mask[v.index] for v in f.verts)]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    # drop sliver faces bridging distant verts (they render as long thin lines)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if max(e.calc_length() for e in f.edges) > 0.04], context='FACES_ONLY')
    bmesh.ops.delete(bm, geom=[e for e in bm.edges if not e.link_faces], context='EDGES')
    loose = [v for v in bm.verts if not v.link_faces]; bmesh.ops.delete(bm, geom=loose, context='VERTS')
    for v in bm.verts: v.co += v.normal * offset
    # smooth the hem lines (boundary loops) so the face-selection staircase disappears
    bnd = [v for v in bm.verts if v.is_boundary]
    for _ in range(12):
        new = {}
        for v in bnd:
            nb = [e.other_vert(v) for e in v.link_edges if e.is_boundary]
            if len(nb) == 2: new[v] = v.co * 0.4 + (nb[0].co + nb[1].co) * 0.3
        for v, c in new.items(): v.co = c
    bm.to_mesh(g.data); bm.free()
    g.data.materials.clear()
    s = g.modifiers.new('sol', 'SOLIDIFY'); s.thickness = thick; s.offset = 1.0; s.use_even_offset = True
    bpy.ops.object.modifier_move_to_index(modifier='sol', index=0); bpy.ops.object.modifier_apply(modifier='sol')
    sm = g.modifiers.new('smooth', 'CORRECTIVE_SMOOTH'); sm.factor = 0.4; sm.iterations = smooth_it; sm.smooth_type = 'LENGTH_WEIGHTED'
    bpy.ops.object.modifier_move_to_index(modifier='smooth', index=0); bpy.ops.object.modifier_apply(modifier='smooth')
    if folds:
        tx = bpy.data.textures.new(name + '_folds', 'MARBLE'); tx.noise_scale = 0.06; tx.turbulence = 3.5; tx.marble_type = 'SHARP'; tx.noise_basis_2 = 'SIN'
        dm = g.modifiers.new('folds', 'DISPLACE'); dm.texture = tx; dm.strength = folds; dm.mid_level = 0.5; dm.texture_coords = 'GLOBAL'
        bpy.ops.object.modifier_move_to_index(modifier='folds', index=0); bpy.ops.object.modifier_apply(modifier='folds')
    # final cleanup: remove any sliver faces with edges > 4 cm (render as stray lines)
    bm = bmesh.new(); bm.from_mesh(g.data)
    sl = [f for f in bm.faces if max(e.calc_length() for e in f.edges) > 0.04]
    print('SLIVERS', name, len(sl))
    bmesh.ops.delete(bm, geom=sl, context='FACES')
    bm.to_mesh(g.data); bm.free()
    bpy.ops.object.shade_smooth()
    return g
shirt = make_garment('RashGuard', masks['shirt'], 0.0035, 0.0015, folds=0.0025)
shorts = make_garment('Shorts', masks['shorts'], 0.017, 0.0025, folds=0.009, smooth_it=10)
wraps = make_garment('HandWraps', masks['wrap'], 0.003, 0.0015)
# --- head regions: scalp (shell hair) and beard (stubble), in rest space relative to eyes / mouth
import numpy as np
eyes_o = bpy.data.objects['Human.high-poly_export']; teeth_o = bpy.data.objects['Human.teeth_base_export']
def bbox_c(o):
    vs = [o.matrix_world @ v.co for v in o.data.vertices]; return sum(vs, Vector()) / len(vs), vs
E, evs = bbox_c(eyes_o); Mth, tvs = bbox_c(teeth_o)
front_y = min(v.y for v in evs)  # Blender front is -Y
head_w = [W[i].get('Head', 0) + W[i].get('HeadTop_End', 0) for i in range(len(P))]
def scalp_val(i):
    p = P[i]
    if head_w[i] < 0.5: return 0.0
    dz = p.z - E.z; dy = p.y - E.y  # dy > 0 = behind the eyes
    if dy < 0.02:   line = 0.062 - 0.12 * abs(p.x - E.x) ** 2 * 10  # forehead hairline with temples
    elif dy < 0.075: line = 0.028                                   # above the ears
    else:            line = -0.06 + max(0.0, 0.11 - dy) * 0.4       # back of the head / nape
    return float(np.clip((dz - line) / 0.012, 0, 1))
def beard_val(i):
    p = P[i]
    if head_w[i] + W[i].get('Neck', 0) < 0.4: return 0.0
    dz = p.z - E.z; dy = p.y - E.y
    if dy > 0.07 or dz > -0.035: return 0.0
    if p.y > E.y + 0.035 and dz > -0.075: return 0.0  # cheeks behind the jaw line
    if dz < -0.165: return 0.0
    mx = (p.x - Mth.x) / 0.03; mz = (p.z - (Mth.z + 0.004)) / 0.013
    if mx * mx + mz * mz < 1.0 and p.y < Mth.y: return 0.0  # lips
    v = np.clip((-0.035 - dz) / 0.015, 0, 1) * np.clip((dz + 0.165) / 0.03, 0, 1)
    if dz > -0.06: v *= np.clip((Mth.y + 0.01 - p.y) / 0.02 + 0.3, 0, 1)  # thin on upper cheeks
    return float(v)
SC = [scalp_val(i) for i in range(len(P))]; BD = [beard_val(i) for i in range(len(P))]
# rasterise per-vertex values into the body UV layout
def raster(vals, size=2048):
    uvl = me.uv_layers.active.data; img = np.zeros((size, size), np.float32)
    for poly in me.polygons:
        vi = list(poly.vertices)
        if max(vals[k] for k in vi) <= 0: continue
        li = list(poly.loop_indices)
        for a, b, c in [(0, 1, 2), (0, 2, 3)] if len(li) == 4 else [(0, 1, 2)]:
            uv = np.array([uvl[li[a]].uv, uvl[li[b]].uv, uvl[li[c]].uv]) * size; vv = np.array([vals[vi[a]], vals[vi[b]], vals[vi[c]]])
            x0, y0 = np.floor(uv.min(0)).astype(int) - 1; x1, y1 = np.ceil(uv.max(0)).astype(int) + 1
            xs, ys = np.meshgrid(np.arange(max(x0, 0), min(x1, size)), np.arange(max(y0, 0), min(y1, size)))
            px = np.stack([xs + .5, ys + .5], -1); T = np.array([uv[1] - uv[0], uv[2] - uv[0]]).T
            if abs(np.linalg.det(T)) < 1e-9: continue
            l = np.einsum('ij,hwj->hwi', np.linalg.inv(T), px - uv[0]); l1, l2 = l[..., 0], l[..., 1]; l0 = 1 - l1 - l2
            ins = (l0 >= -0.02) & (l1 >= -0.02) & (l2 >= -0.02)
            val = l0 * vv[0] + l1 * vv[1] + l2 * vv[2]
            img[ys[ins], xs[ins]] = np.maximum(img[ys[ins], xs[ins]], val[ins])
    return img[::-1]  # top row first
def blur(a, s):
    f = np.fft.fft2(a); ky = np.fft.fftfreq(a.shape[0])[:, None]; kx = np.fft.fftfreq(a.shape[1])[None, :]
    return np.real(np.fft.ifft2(f * np.exp(-2 * (np.pi * s) ** 2 * (kx ** 2 + ky ** 2))))
scalp_m = np.clip(blur(raster(SC), 2), 0, 1); beard_m = np.clip(blur(raster(BD), 3), 0, 1)
skin_src = bpy.data.images.load(bpy.path.abspath(body.data.materials[0].node_tree.nodes['DiffuseTexture'].image.filepath))
S = np.array(skin_src.pixels[:], np.float32).reshape(skin_src.size[1], skin_src.size[0], 4)[::-1].copy()
rng = np.random.default_rng(3); n = S.shape[0]
dots = np.zeros((n, n), np.float32); ii = rng.integers(0, n, (int(n * n * 0.03), 2)); dots[ii[:, 0], ii[:, 1]] = 1; dots = np.clip(blur(dots, 0.45) * 5, 0, 1)
stub = beard_m * (0.25 + 0.35 * dots)          # beard shadow + individual stubble dots
scalp = scalp_m * (0.55 + 0.3 * dots)          # dark scalp under the shell hair
S[..., :3] *= (1 - np.clip(stub + scalp, 0, 0.85))[..., None]
skin_out = bpy.data.images.new('skin_diff', n, n, alpha=False); px = S.copy(); px[..., 3] = 1
skin_out.pixels.foreach_set(px[::-1].ravel()); skin_out.filepath_raw = os.path.join(TEX, 'skin_diff.png'); skin_out.file_format = 'PNG'; skin_out.save()
# shell hair: stacked alpha-tested layers over the scalp, each slightly combed backward/down
hair_shells = []
mask_scalp = [v > 0.02 for v in SC]
NSH = 6
for k in range(NSH):
    activate(body); bpy.ops.object.duplicate(); g = bpy.context.object; g.name = 'HairShell%d' % k
    bm = bmesh.new(); bm.from_mesh(g.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if not all(mask_scalp[v.index] for v in f.verts)], context='FACES')
    bmesh.ops.delete(bm, geom=[e for e in bm.edges if not e.link_faces], context='EDGES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    h = 0.0012 + 0.0011 * k
    dl = bm.verts.layers.deform.active
    for v in bm.verts: v.co += v.normal * h + Vector((0, 0.0006 * k, -0.0004 * k))
    bm.to_mesh(g.data); bm.free(); g.data.materials.clear(); bpy.ops.object.shade_smooth()
    hair_shells.append(g)
# hide body faces fully covered (eroded mask), avoids z-fighting
adj = [set() for _ in me.vertices]
for e in me.edges: a, b = e.vertices; adj[a].add(b); adj[b].add(a)
cover = [any(masks[k][i] for k in masks) for i in range(len(me.vertices))]
er = [cover[i] and all(cover[j] for j in adj[i]) for i in range(len(me.vertices))]
er2 = [er[i] and all(er[j] for j in adj[i]) for i in range(len(me.vertices))]
bm = bmesh.new(); bm.from_mesh(me)
bmesh.ops.delete(bm, geom=[f for f in bm.faces if all(er2[v.index] for v in f.verts)], context='FACES')
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
bm.to_mesh(me); bm.free()
# 3. materials
def img(path, color=True):
    im = bpy.data.images.load(path, check_existing=True)
    im.colorspace_settings.name = 'sRGB' if color else 'Non-Color'; return im
def new_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes['Principled BSDF']; return m, nt, bsdf
def tex(nt, path, color=True, scale=None):
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = img(path, color)
    if scale:
        tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (scale, scale, 1)
        nt.links.new(tc.outputs['UV'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], t.inputs['Vector'])
    return t
def normal(nt, bsdf, path, scale=None, strength=1.0):
    t = tex(nt, path, False, scale); n = nt.nodes.new('ShaderNodeNormalMap'); n.inputs['Strength'].default_value = strength
    nt.links.new(t.outputs['Color'], n.inputs['Color']); nt.links.new(n.outputs['Normal'], bsdf.inputs['Normal'])
def rough(nt, bsdf, path, scale=None):
    t = tex(nt, path, False, scale); sp = nt.nodes.new('ShaderNodeSeparateColor')
    nt.links.new(t.outputs['Color'], sp.inputs['Color']); nt.links.new(sp.outputs['Green'], bsdf.inputs['Roughness'])
def setmat(o, m): o.data.materials.clear(); o.data.materials.append(m)
MH = os.path.join(ROOT, 'tools', 'mhassets'); PH = os.path.join(ROOT, 'tools', 'polyhaven')
skin_img = os.path.join(TEX, 'skin_diff.png')
m, nt, b = new_mat('Skin'); t = tex(nt, skin_img); nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
normal(nt, b, os.path.join(TEX, 'skin_micro_normal.png'), 14, 0.45); rough(nt, b, os.path.join(TEX, 'skin_micro_rough.png'), 14)
b.inputs['Specular IOR Level'].default_value = 0.5
b.inputs['Sheen Weight'].default_value = 0.12; b.inputs['Sheen Roughness'].default_value = 0.35; b.inputs['Sheen Tint'].default_value = (0.55, 0.36, 0.28, 1)
setmat(body, m)
def fabric(name, diff, scale, roughv=None):
    m, nt, b = new_mat(name); t = tex(nt, diff, True, scale); nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
    normal(nt, b, os.path.join(PH, 'bi_stretch_nor_gl_2k.jpg'), scale, 1.0); rough(nt, b, os.path.join(PH, 'bi_stretch_rough_2k.jpg'), scale)
    b.inputs['Sheen Weight'].default_value = 0.4; b.inputs['Sheen Roughness'].default_value = 0.5; b.inputs['Sheen Tint'].default_value = (0.5, 0.5, 0.52, 1)
    return m
setmat(shirt, fabric('RashGuard', os.path.join(TEX, 'fabric_charcoal_diff.png'), 9))
setmat(shorts, fabric('Shorts', os.path.join(TEX, 'fabric_charcoal_diff.png'), 9))
m, nt, b = new_mat('HandWraps'); t = tex(nt, os.path.join(TEX, 'wrap_diff.png'), True, 16); nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
normal(nt, b, os.path.join(PH, 'cotton_jersey_nor_gl_2k.jpg'), 16, 1.0); rough(nt, b, os.path.join(PH, 'cotton_jersey_rough_2k.jpg'), 16)
setmat(wraps, m)
def alpha_mat(name, path, roughv):
    m, nt, b = new_mat(name); t = tex(nt, path); nt.links.new(t.outputs['Color'], b.inputs['Base Color']); nt.links.new(t.outputs['Alpha'], b.inputs['Alpha'])
    b.inputs['Roughness'].default_value = roughv; m.surface_render_method = 'BLENDED'; m.use_backface_culling = False
    return m
def mask_mat(name, path, roughv, scale=None):
    m, nt, b = new_mat(name); t = tex(nt, path, True, scale); nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
    mth = nt.nodes.new('ShaderNodeMath'); mth.operation = 'ROUND'; nt.links.new(t.outputs['Alpha'], mth.inputs[0]); nt.links.new(mth.outputs[0], b.inputs['Alpha'])
    b.inputs['Roughness'].default_value = roughv; m.surface_render_method = 'DITHERED'; m.use_backface_culling = False
    b.inputs['Sheen Weight'].default_value = 0.3; b.inputs['Sheen Roughness'].default_value = 0.3; b.inputs['Sheen Tint'].default_value = (0.35, 0.3, 0.26, 1)
    return m
shell_mats = [mask_mat('HairShell%d' % gi, os.path.join(TEX, 'hair_shell_%d.png' % gi), 0.42, 70) for gi in range(3)]
for k, g in enumerate(hair_shells): setmat(g, shell_mats[min(k // 2, 2)])
setmat(bpy.data.objects['Human.eyebrow001_export'], mask_mat('Brows', os.path.join(TEX, 'brow_diff.png'), 0.6))
setmat(bpy.data.objects['Human.eyelashes01_export'], alpha_mat('Lashes', os.path.join(TEX, 'lash_diff.png'), 0.6))
eyes = bpy.data.objects['Human.high-poly_export']
m, nt, b = new_mat('EyeIris'); t = tex(nt, os.path.join(TEX, 'eye_diff.png')); nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
mth = nt.nodes.new('ShaderNodeMath'); mth.operation = 'ROUND'; nt.links.new(t.outputs['Alpha'], mth.inputs[0]); nt.links.new(mth.outputs[0], b.inputs['Alpha']); m.surface_render_method = 'DITHERED'
b.inputs['Roughness'].default_value = 0.3; setmat(eyes, m)
# cornea shell: duplicate eyes, scale ~1.6% about each eyeball centre (split by connected parts)
activate(eyes); bpy.ops.object.duplicate(); cor = bpy.context.object; cor.name = 'Cornea'
bm = bmesh.new(); bm.from_mesh(cor.data)
xs = [v.co.x for v in bm.verts]; cx = (max(xs) + min(xs)) / 2
for side in (lambda v: v.co.x >= cx, lambda v: v.co.x < cx):
    vs = [v for v in bm.verts if side(v)]
    c = sum((v.co for v in vs), Vector()) / len(vs)
    for v in vs: v.co = c + (v.co - c) * 1.016
bm.to_mesh(cor.data); bm.free()
m, nt, b = new_mat('Cornea'); b.inputs['Base Color'].default_value = (1, 1, 1, 1); b.inputs['Roughness'].default_value = 0.03
b.inputs['Transmission Weight'].default_value = 1.0; b.inputs['IOR'].default_value = 1.376; b.inputs['Specular IOR Level'].default_value = 0.5
setmat(cor, m)
m, nt, b = new_mat('Teeth'); t = tex(nt, os.path.join(MH, 'teeth/teeth_base/teeth.png')); nt.links.new(t.outputs['Color'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = 0.25
setmat(bpy.data.objects['Human.teeth_base_export'], m)
m, nt, b = new_mat('Tongue'); t = tex(nt, os.path.join(MH, 'tongue/tongue01/tongue01_diffuse.png')); nt.links.new(t.outputs['Color'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = 0.35
setmat(tongue, m)
for o in bpy.data.objects:
    if o.type == 'MESH': print("TRIS", o.name, sum(len(p.vertices) - 2 for p in o.data.polygons))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'tmp', 'final.blend'))
rig.name = 'Armature'
bpy.ops.export_scene.gltf(filepath=os.path.join(ROOT, 'fighter.glb'), export_format='GLB', export_yup=True, export_apply=False,
    export_animation_mode='ACTIONS', export_force_sampling=True, export_skins=True, export_morph=False, export_def_bones=False,
    export_image_format='AUTO', export_draco_mesh_compression_enable=False, export_cameras=False, export_lights=False)
print("EXPORT DONE")
