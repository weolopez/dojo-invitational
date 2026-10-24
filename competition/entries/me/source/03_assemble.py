"""
Stage 3: put the owner's FaceBuilder head on the MPFB body, dress it and export fighter.glb.
- bakes the macro shape keys and applies one Catmull-Clark level to the body
- deletes the MPFB head, fits the FaceBuilder head (my_head_facebuilder.glb, from source/build_photo_head_facebuilder.py)
  to the MPFB skull, trims its neck and conforms the lower neck radially onto the body neck; head weights are copied
  from the nearest vertex of the original MPFB head/neck, so it deforms like the head it replaced
- tints the CC0 body skin to the colour of the owner's neck in the FaceBuilder texture
- builds a rash guard, shorts and hand wraps from body faces (bone-weight / height masks, offset + solidify), so they
  share the body skin weights; folds are procedural displacement, not cloth simulation
- generates tileable procedural skin micro-normal / roughness maps and recoloured CC0 Poly Haven fabrics
Face textures stay in .work/ (RULES.md section 12: no face textures in source/).
"""

import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

HERE = os.path.dirname(os.path.abspath(__file__))
ENTRY = os.path.abspath(os.path.join(HERE, ".."))
WORK = os.path.join(ENTRY, ".work")
TEX = os.path.join(WORK, "tex")
PH = os.path.join(WORK, "polyhaven")
HEAD_GLB = "/Users/weo/Development/3d/my_head_facebuilder.glb"
os.makedirs(TEX, exist_ok=True)
rng = np.random.default_rng(11)

bpy.ops.wm.open_mainfile(filepath=os.path.join(WORK, "rigged.blend"))
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
body = next(o for o in bpy.data.objects if o.type == "MESH")
body.name = "Body"


def activate(o):
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for x in bpy.context.selected_objects:
        x.select_set(False)
    o.select_set(True)
    bpy.context.view_layer.objects.active = o


def apply_modifier(o, mod):
    activate(o)
    bpy.ops.object.modifier_move_to_index(modifier=mod.name, index=0)
    bpy.ops.object.modifier_apply(modifier=mod.name)


def bone_head(name):
    return rig.matrix_world @ rig.data.bones["mixamorig:" + name].head_local


def smoothstep(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def delete_verts(obj, doomed):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if doomed(v)], context="VERTS")
    bm.to_mesh(obj.data)
    bm.free()


def vertex_tables(obj):
    names = {g.index: g.name for g in obj.vertex_groups}
    pts = [obj.matrix_world @ v.co for v in obj.data.vertices]
    wts = [{names[g.group]: g.weight for g in v.groups if g.weight > 0} for v in obj.data.vertices]
    return pts, wts


def load_rgb(path):
    im = bpy.data.images.load(path, check_existing=True)
    a = np.array(im.pixels[:], np.float32).reshape(im.size[1], im.size[0], im.channels)
    return a[::-1, :, :3]  # top row first


def save_png(name, rgb, alpha=None):
    h, wd = rgb.shape[:2]
    im = bpy.data.images.new(name, wd, h, alpha=alpha is not None)
    px = np.ones((h, wd, 4), np.float32)
    px[..., :3] = rgb
    if alpha is not None:
        px[..., 3] = alpha
    im.pixels.foreach_set(px[::-1].ravel())
    im.filepath_raw = os.path.join(TEX, name + ".png")
    im.file_format = "PNG"
    im.save()
    return im.filepath_raw


def mean_uv_colour(obj, img, keep):
    """Mean texel colour (sRGB, 0-1) under the UVs of the vertices where keep(co) is true."""
    uv = obj.data.uv_layers.active.data
    hgt, wid = img.shape[:2]
    samples = []
    for poly in obj.data.polygons:
        for li, vi in zip(poly.loop_indices, poly.vertices):
            if keep(obj.matrix_world @ obj.data.vertices[vi].co):
                u, v = uv[li].uv
                samples.append(img[int((1 - v % 1) * (hgt - 1)), int((u % 1) * (wid - 1))])
    return np.median(np.array(samples), axis=0), len(samples)


def mean_uv_colour_pts(points, keep):
    """Like mean_uv_colour, on the original (pre-trim) body using its saved per-loop UVs."""
    hgt, wid = body_rgb.shape[:2]
    samples = [body_rgb[int((1 - v % 1) * (hgt - 1)), int((u % 1) * (wid - 1))]
               for vi, (u, v) in BODY_UV if keep(points[vi])]
    return np.median(np.array(samples), axis=0), len(samples)


# ---------------------------------------------------------------- body: bake shape, subdivide
activate(body)
if body.data.shape_keys:
    bpy.ops.object.shape_key_remove(all=True, apply_mix=True)
for m in [m for m in body.modifiers if m.type == "SUBSURF"]:
    body.modifiers.remove(m)
sub = body.modifiers.new("sub", "SUBSURF")
sub.levels = sub.render_levels = 1
apply_modifier(body, sub)

neck, head_bone = bone_head("Neck"), bone_head("Head")
P_full, W_full = vertex_tables(body)
BODY_UV = [(vi, tuple(body.data.uv_layers.active.data[li].uv)) for poly in body.data.polygons
           for li, vi in zip(poly.loop_indices, poly.vertices)]
head_kd_pts = [i for i, wt in enumerate(W_full) if wt.get("mixamorig:Head", 0) + wt.get("mixamorig:Neck", 0) > 0.05]
head_kd = KDTree(len(head_kd_pts))
for k, i in enumerate(head_kd_pts):
    head_kd.insert(P_full[i], k)
head_kd.balance()

# ---------------------------------------------------------------- remove the MPFB head
head_pts = [P_full[i] for i, wt in enumerate(W_full) if wt.get("mixamorig:Head", 0) > 0.5]
delete_verts(body, lambda v: W_full[v.index].get("mixamorig:Head", 0) > 0.5)
print(f"[assemble] removed {len(head_pts)} MPFB head vertices")


def skull(points):
    top = max(p.z for p in points)
    bottom = min(p.z for p in points)
    cranium = [p for p in points if p.z > top - 0.35 * (top - bottom)]
    xs, ys = [p.x for p in cranium], [p.y for p in cranium]
    return top, max(ys) - min(ys), (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2


# ---------------------------------------------------------------- fit the FaceBuilder head
bpy.ops.import_scene.gltf(filepath=HEAD_GLB)
head = next(o for o in bpy.context.selected_objects if o.type == "MESH")
for o in list(bpy.context.selected_objects):
    if o is not head:
        bpy.data.objects.remove(o, do_unlink=True)
head.name = "OwnerHead"
head.parent = None
activate(head)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

t_top, t_len, t_x, t_y = skull(head_pts)
_, s_len, _, _ = skull([v.co for v in head.data.vertices])
scale = t_len / s_len * 1.02
for v in head.data.vertices:
    v.co *= scale
s_top, _, s_x, s_y = skull([v.co for v in head.data.vertices])
offset = Vector((t_x - s_x, t_y - s_y, t_top + 0.004 - s_top))
for v in head.data.vertices:
    v.co += offset
print(f"[assemble] head scale {scale:.4f}")

# The FaceBuilder neck's lower part carries the baked shirt collar: trim it, then conform the remaining lower neck
# radially onto the body neck so the two surfaces meet.
NECK_CUT = neck.z - 0.005
BAND = 0.03
delete_verts(head, lambda v: v.co.z < NECK_CUT)

P, W = vertex_tables(body)
neck_ring = [P[i] for i in range(len(P)) if NECK_CUT - 0.04 < P[i].z < NECK_CUT + BAND + 0.01
             and W[i].get("mixamorig:Neck", 0) + W[i].get("mixamorig:Head", 0) > 0.3]
axis = sum(neck_ring, Vector()) / len(neck_ring)
BINS = 72


def body_radius(z):
    """Body neck radius around the neck axis per angle bin at height z (nearest available height below)."""
    sums, counts = np.zeros(BINS), np.zeros(BINS)
    for p in neck_ring:
        if abs(p.z - z) < 0.012:
            k = int((math.atan2(p.y - axis.y, p.x - axis.x) + math.pi) / (2 * math.pi) * BINS) % BINS
            sums[k] += math.hypot(p.x - axis.x, p.y - axis.y)
            counts[k] += 1
    good = np.flatnonzero(counts)
    if len(good) < BINS // 3:
        return None
    return np.interp(np.arange(BINS), good, sums[good] / counts[good], period=BINS)


top_ring_z = max(p.z for p in neck_ring)
profiles = {}
for v in head.data.vertices:
    c = v.co
    t = 1.0 - smoothstep(NECK_CUT, NECK_CUT + BAND, c.z)
    if t <= 0:
        continue
    zk = round(min(c.z, top_ring_z - 0.01), 3)
    if zk not in profiles:
        profiles[zk] = body_radius(zk)
    prof = profiles[zk]
    if prof is None:
        continue
    ang = math.atan2(c.y - axis.y, c.x - axis.x)
    k = (ang + math.pi) / (2 * math.pi) * BINS
    rb = float(np.interp(k, np.arange(BINS + 1), np.append(prof, prof[0]))) + 0.0015
    rh = math.hypot(c.x - axis.x, c.y - axis.y)
    r = rh + (rb - rh) * t
    c.x, c.y = axis.x + math.cos(ang) * r, axis.y + math.sin(ang) * r

# drop the body neck under the head, keeping 1.5 cm of overlap below the head's lower edge
delete_verts(body, lambda v: v.co.z > NECK_CUT + 0.015)

# head weights from the nearest vertex of the original MPFB head / neck
for name in {n for i in head_kd_pts for n in W_full[i]}:
    head.vertex_groups.new(name=name)
for v in head.data.vertices:
    _, k, _ = head_kd.find(v.co)
    for name, wt in W_full[head_kd_pts[k]].items():
        head.vertex_groups[name].add([v.index], wt, "REPLACE")
head.parent = rig
mod = head.modifiers.new("Armature", "ARMATURE")
mod.object = rig

# ---------------------------------------------------------------- skin tint: body neck -> owner's neck colour
head_img_node = next(n for n in head.data.materials[0].node_tree.nodes if n.type == "TEX_IMAGE" and n.image)
head_img_path = os.path.join(WORK, "owner_head_texture.png")
head_img_node.image.filepath_raw = head_img_path
head_img_node.image.file_format = "PNG"
head_img_node.image.save()
face_rgb = load_rgb(head_img_path)
body_tex_node = body.data.materials[0].node_tree.nodes["DiffuseTexture"]
body_rgb = load_rgb(bpy.path.abspath(body_tex_node.image.filepath))
# owner: lit cheeks (front of the face, between the nose and the jaw line); body: the same region of the MPFB face
cheeks = lambda p: head_bone.z + 0.0 < p.z < head_bone.z + 0.05 and p.y < t_y - 0.04 and 0.025 < abs(p.x - t_x) < 0.06  # noqa: E731,E501
owner_c, n_owner = mean_uv_colour(head, face_rgb, cheeks)
body_c, n_body = mean_uv_colour_pts(P_full, cheeks)
gain = np.clip(owner_c / np.maximum(body_c, 1e-3), 0.6, 1.6)
print(f"[assemble] owner cheeks {owner_c.round(3)} ({n_owner}), body cheeks {body_c.round(3)} ({n_body}), "
      f"gain {gain.round(3)}")
skin = np.clip(body_rgb * gain, 0, 1)


def raster(obj, values, size):
    """Rasterise per-vertex values (0-1) into obj's UV layout (top row first), max-combining overlaps."""
    uv = obj.data.uv_layers.active.data
    img = np.zeros((size, size), np.float32)
    for poly in obj.data.polygons:
        vi = list(poly.vertices)
        if max(values[k] for k in vi) <= 0:
            continue
        li = list(poly.loop_indices)
        for a, b, c in [(0, k, k + 1) for k in range(1, len(li) - 1)]:
            tri = np.array([uv[li[a]].uv, uv[li[b]].uv, uv[li[c]].uv]) * size
            val = np.array([values[vi[a]], values[vi[b]], values[vi[c]]])
            x0, y0 = np.maximum(np.floor(tri.min(0)).astype(int) - 1, 0)
            x1, y1 = np.minimum(np.ceil(tri.max(0)).astype(int) + 1, size)
            m = np.array([tri[1] - tri[0], tri[2] - tri[0]]).T
            if x1 <= x0 or y1 <= y0 or abs(np.linalg.det(m)) < 1e-9:
                continue
            xs, ys = np.meshgrid(np.arange(x0, x1), np.arange(y0, y1))
            bary = np.einsum("ij,hwj->hwi", np.linalg.inv(m), np.stack([xs + 0.5, ys + 0.5], -1) - tri[0])
            l1, l2 = bary[..., 0], bary[..., 1]
            inside = (l1 >= -0.02) & (l2 >= -0.02) & (l1 + l2 <= 1.02)
            v = (1 - l1 - l2) * val[0] + l1 * val[1] + l2 * val[2]
            img[ys[inside], xs[inside]] = np.maximum(img[ys[inside], xs[inside]], v[inside])
    return img[::-1]


# The FaceBuilder texture has the owner's shirt collar baked onto the lower neck: fade that band to the tinted body
# neck colour, so the collar disappears and the head-to-body seam has one skin tone.
neck_fill, _ = mean_uv_colour(body, skin, lambda p: NECK_CUT - 0.03 < p.z < NECK_CUT + 0.015)
# the band rises toward the nape, where the photos barely cover the neck and the texture is smeared
fade = []
for v in head.data.vertices:
    back = smoothstep(axis.y, axis.y + 0.04, v.co.y)
    fade.append(1.0 - smoothstep(NECK_CUT + 0.012 + 0.03 * back, NECK_CUT + 0.04 + 0.04 * back, v.co.z))
mask = raster(head, fade, face_rgb.shape[0])
mask = np.clip(np.real(np.fft.ifft2(np.fft.fft2(mask) * np.exp(-2 * (np.pi * 3) ** 2 * (
    np.fft.fftfreq(mask.shape[0])[:, None] ** 2 + np.fft.fftfreq(mask.shape[1])[None, :] ** 2)))), 0, 1)
grain = 1 + 0.035 * rng.standard_normal(mask.shape)
face_rgb = face_rgb * (1 - mask[..., None]) + np.clip(neck_fill * grain[..., None], 0, 1) * mask[..., None]
head_img_node.image = bpy.data.images.load(save_png("owner_head_neckfix", face_rgb))
print(f"[assemble] neck fill {neck_fill.round(3)}")

# ---------------------------------------------------------------- clothing from body faces
P, W = vertex_tables(body)
hips, knee, l_arm = bone_head("Hips"), bone_head("LeftLeg"), bone_head("LeftArm")
hands = [bone_head("LeftHand"), bone_head("RightHand")]
FINGERS = [f"Hand{d}{k}" for d in ("Thumb", "Index", "Middle", "Ring", "Pinky") for k in (1, 2, 3)]


def w(i, *names):
    return sum(W[i].get("mixamorig:" + s + n, 0) for n in names for s in ("", "Left", "Right"))


def m_shirt(i):
    p = P[i]
    return (w(i, "ForeArm", "Hand", *FINGERS) < 0.02 and abs(p.x) < abs(l_arm.x) + 0.13
            and hips.z - 0.02 < p.z < neck.z - 0.035)


def m_shorts(i):
    p = P[i]
    return knee.z + 0.17 < p.z < hips.z + 0.085 and w(i, "ForeArm", "Hand", "Arm", *FINGERS) < 0.01


def m_wrap(i):
    if w(i, *FINGERS) > 0.35:
        return False
    near = min((P[i] - h).length for h in hands) < 0.085
    return w(i, "Hand") > 0.4 or (w(i, "ForeArm") > 0.2 and near)


masks = {k: [f(i) for i in range(len(P))] for k, f in (("shirt", m_shirt), ("shorts", m_shorts), ("wrap", m_wrap))}


def garment(name, mask, offset, thickness, folds=0.0, smooth_iterations=3):
    activate(body)
    bpy.ops.object.duplicate()
    g = bpy.context.object
    g.name = name
    bm = bmesh.new()
    bm.from_mesh(g.data)
    bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if not all(mask[v.index] for v in f.verts)], context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    for v in bm.verts:
        v.co += v.normal * offset
    hem = [v for v in bm.verts if v.is_boundary]
    for _ in range(12):  # relax the hem loops so the face-selection staircase disappears
        moved = {}
        for v in hem:
            nb = [e.other_vert(v) for e in v.link_edges if e.is_boundary]
            if len(nb) == 2:
                moved[v] = v.co * 0.4 + (nb[0].co + nb[1].co) * 0.3
        for v, c in moved.items():
            v.co = c
    bm.to_mesh(g.data)
    bm.free()
    g.data.materials.clear()
    sol = g.modifiers.new("solidify", "SOLIDIFY")
    sol.thickness, sol.offset, sol.use_even_offset = thickness, 1.0, True
    apply_modifier(g, sol)
    sm = g.modifiers.new("smooth", "CORRECTIVE_SMOOTH")
    sm.factor, sm.iterations, sm.smooth_type = 0.4, smooth_iterations, "LENGTH_WEIGHTED"
    apply_modifier(g, sm)
    if folds:
        tx = bpy.data.textures.new(name + "_folds", "MARBLE")
        tx.noise_scale, tx.turbulence, tx.marble_type, tx.noise_basis_2 = 0.06, 3.5, "SHARP", "SIN"
        dm = g.modifiers.new("folds", "DISPLACE")
        dm.texture, dm.strength, dm.mid_level, dm.texture_coords = tx, folds, 0.5, "GLOBAL"
        apply_modifier(g, dm)
    bm = bmesh.new()
    bm.from_mesh(g.data)
    slivers = [f for f in bm.faces if max(e.calc_length() for e in f.edges) > 0.04]
    bmesh.ops.delete(bm, geom=slivers, context="FACES")
    bm.to_mesh(g.data)
    bm.free()
    bpy.ops.object.shade_smooth()
    return g


shirt = garment("RashGuard", masks["shirt"], 0.0035, 0.0015, folds=0.0025)
shorts = garment("Shorts", masks["shorts"], 0.017, 0.0025, folds=0.009, smooth_iterations=10)
wraps = garment("HandWraps", masks["wrap"], 0.003, 0.0015)

# delete body faces fully under clothing (two rings in from the hem), so skin can't poke through
adj = [set() for _ in P]
for e in body.data.edges:
    a, b = e.vertices
    adj[a].add(b)
    adj[b].add(a)
covered = [any(masks[k][i] for k in masks) for i in range(len(P))]
for _ in range(2):
    covered = [covered[i] and all(covered[j] for j in adj[i]) for i in range(len(P))]
bm = bmesh.new()
bm.from_mesh(body.data)
bm.verts.ensure_lookup_table()
bmesh.ops.delete(bm, geom=[f for f in bm.faces if all(covered[v.index] for v in f.verts)], context="FACES_ONLY")
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
bm.to_mesh(body.data)
bm.free()

# ---------------------------------------------------------------- textures


def blur_periodic(a, sigma):
    f = np.fft.fft2(a)
    ky, kx = np.fft.fftfreq(a.shape[0])[:, None], np.fft.fftfreq(a.shape[1])[None, :]
    return np.real(np.fft.ifft2(f * np.exp(-2 * (np.pi * sigma) ** 2 * (kx ** 2 + ky ** 2))))


N = 1024
pores = np.zeros((N, N))
pores[tuple(rng.integers(0, N, size=(2, 8000)))] = 1
height = -blur_periodic(pores, 1.5) * 6 + blur_periodic(rng.standard_normal((N, N)), 1.0) * 0.4 \
    + blur_periodic(rng.standard_normal((N, N)), 7.0) * 1.4
height = (height - height.mean()) / height.std()
gx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) / 2
gy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) / 2
nrm = np.dstack([-gx * 0.5, gy * 0.5, np.ones_like(height)])
nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
skin_normal = save_png("skin_micro_normal", nrm * 0.5 + 0.5)
rough = np.clip(0.52 + 0.05 * np.clip(-height, -2, 3) + 0.05 * blur_periodic(rng.standard_normal((N, N)), 14) * 8,
                0.32, 0.72)
skin_rough = save_png("skin_micro_rough", np.dstack([np.ones_like(rough), rough, np.zeros_like(rough)]))
skin_diff = save_png("owner_body_skin", skin)


def recolour(src, name, rgb):
    a = load_rgb(os.path.join(PH, src))
    lum = a.mean(2, keepdims=True)
    return save_png(name, np.clip(lum / lum.mean() * np.array(rgb), 0, 1))


charcoal = recolour("bi_stretch_diff_2k.jpg", "fabric_charcoal", (0.11, 0.115, 0.125))
wrap_white = recolour("cotton_jersey_diff_2k.jpg", "wrap_offwhite", (0.78, 0.76, 0.72))

# ---------------------------------------------------------------- materials


def new_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    return m, m.node_tree, m.node_tree.nodes["Principled BSDF"]


def tex_node(nt, path, colour=True, tile=None):
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(path, check_existing=True)
    t.image.colorspace_settings.name = "sRGB" if colour else "Non-Color"
    if tile:
        tc, mp = nt.nodes.new("ShaderNodeTexCoord"), nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (tile, tile, 1)
        nt.links.new(tc.outputs["UV"], mp.inputs["Vector"])
        nt.links.new(mp.outputs["Vector"], t.inputs["Vector"])
    return t


def pbr(name, diffuse, normal, roughness, tile=None, normal_strength=1.0, sheen=0.0):
    m, nt, b = new_mat(name)
    nt.links.new(tex_node(nt, diffuse, True, tile).outputs["Color"], b.inputs["Base Color"])
    nmap = nt.nodes.new("ShaderNodeNormalMap")
    nmap.inputs["Strength"].default_value = normal_strength
    nt.links.new(tex_node(nt, normal, False, tile).outputs["Color"], nmap.inputs["Color"])
    nt.links.new(nmap.outputs["Normal"], b.inputs["Normal"])
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(tex_node(nt, roughness, False, tile).outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], b.inputs["Roughness"])
    if sheen:
        b.inputs["Sheen Weight"].default_value = sheen
        b.inputs["Sheen Roughness"].default_value = 0.4
    return m


def set_mat(o, m):
    o.data.materials.clear()
    o.data.materials.append(m)


set_mat(body, pbr("Skin", skin_diff, skin_normal, skin_rough, None, 0.0))
# micro detail tiles across the body UVs, base colour does not: rebuild the mapping on the detail maps only
nt = body.data.materials[0].node_tree
for t in [n for n in nt.nodes if n.type == "TEX_IMAGE" and n.image.colorspace_settings.name == "Non-Color"]:
    tc, mp = nt.nodes.new("ShaderNodeTexCoord"), nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (14, 14, 1)
    nt.links.new(tc.outputs["UV"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], t.inputs["Vector"])
next(n for n in nt.nodes if n.type == "NORMAL_MAP").inputs["Strength"].default_value = 0.45

fabric = pbr("TrainingFabric", charcoal, os.path.join(PH, "bi_stretch_nor_gl_2k.jpg"),
             os.path.join(PH, "bi_stretch_rough_2k.jpg"), 9, 1.0, 0.4)
set_mat(shirt, fabric)
set_mat(shorts, fabric)
set_mat(wraps, pbr("HandWraps", wrap_white, os.path.join(PH, "cotton_jersey_nor_gl_2k.jpg"),
                   os.path.join(PH, "cotton_jersey_rough_2k.jpg"), 16))

head_mat = head.data.materials[0]
hb = head_mat.node_tree.nodes.get("Principled BSDF")
if hb:
    hb.inputs["Roughness"].default_value = 0.55
    hb.inputs["Metallic"].default_value = 0.0

# ---------------------------------------------------------------- export
total = 0
for o in bpy.data.objects:
    if o.type == "MESH":
        tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
        total += tris
        print(f"[assemble] {o.name}: {tris} triangles")
print(f"[assemble] total {total} triangles")
rig.name = "Armature"
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(WORK, "final.blend"))
bpy.ops.export_scene.gltf(filepath=os.path.join(ENTRY, "fighter.glb"), export_format="GLB", export_yup=True,
                          export_apply=False, export_animation_mode="ACTIONS", export_force_sampling=True,
                          export_skins=True, export_morph=False, export_def_bones=False, export_image_format="AUTO",
                          export_cameras=False, export_lights=False)
print("[assemble] exported fighter.glb")
