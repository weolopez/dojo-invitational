"""Stage 2: realism pass on materials for CLAUDE. Opens .work/claude_human.blend, writes .work/claude_materials.blend.
- Skin: diffuse graded from the CC0 'middleage caucasian female' map toward a warm olive tone; a procedurally generated,
  tiling pore/micro-detail normal map (made here, see make_pore_normal); a blood-flush tint on cheeks, nose tip and
  ears and a roughness map (T-zone and lips glossier), both placed from face landmarks found in the rest mesh.
- Eyes: CC0 brown iris texture with its red cast shifted to a dark brown; clearcoat for a wet cornea.
- Hair, brows: darkened to near-black brown, alpha kept.
- Scalp and brow shading: the hair cap and brow cards are projected onto the skin texture (paint_under_cards), so
  the skin under the hairline and brows is dark instead of bare skin showing through the cutout gaps.
- Sportsuit: blue top recoloured to an even terracotta with charcoal piping, grey leggings to charcoal black.
"""
import colorsys
import os

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

ENTRY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(ENTRY, ".work")
TEX = os.path.join(WORK, "textures")
DATA = os.path.join(WORK, "mpfb_user", "data")
HAIR_CUTOFF = 0.26


def pixels(img):
    a = np.empty(img.size[0] * img.size[1] * 4, dtype=np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(img.size[1], img.size[0], 4)


def save_copy(img, arr, name):
    os.makedirs(TEX, exist_ok=True)
    out = bpy.data.images.new(name, img.size[0], img.size[1], alpha=True)
    out.pixels.foreach_set(np.ascontiguousarray(arr).ravel())
    out.filepath_raw = os.path.join(TEX, f"{name}.png")
    out.file_format = "PNG"
    out.save()
    out.colorspace_settings.name = img.colorspace_settings.name
    return out


def image_nodes(mat):
    return [n for n in mat.node_tree.nodes if n.type == "TEX_IMAGE" and n.image]


def principled(mat):
    return next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def blur_wrap(a, r):
    """Box blur with wrap-around, so the result tiles."""
    for axis in (0, 1):
        acc = np.zeros_like(a)
        for k in range(-r, r + 1):
            acc += np.roll(a, k, axis=axis)
        a = acc / (2 * r + 1)
    return a


def make_pore_normal(size=1024, seed=7):
    """Tiling skin micro-detail: fine pores plus soft larger undulation, converted to a tangent-space normal map."""
    rng = np.random.default_rng(seed)
    pores = blur_wrap(rng.random((size, size)), 1)
    pores = (pores - pores.mean()) / pores.std()
    dimples = np.where(rng.random((size, size)) > 0.985, -2.5, 0.0)
    dimples = blur_wrap(dimples, 2)
    soft = blur_wrap(rng.random((size, size)), 8)
    soft = (soft - soft.mean()) / soft.std()
    h = 0.55 * pores + 1.2 * dimples + 0.35 * soft
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5
    strength = 0.35
    n = np.stack([-dx * strength, -dy * strength, np.ones_like(h)], axis=-1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    rgba = np.concatenate([n * 0.5 + 0.5, np.ones((size, size, 1))], axis=-1).astype(np.float32)
    img = bpy.data.images.new("claude_skin_pores_normal", size, size, alpha=False)
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = os.path.join(TEX, "claude_skin_pores_normal.png")
    img.file_format = "PNG"
    os.makedirs(TEX, exist_ok=True)
    img.save()
    img.colorspace_settings.name = "Non-Color"
    return img


def position_map(obj, h, w):
    """Rest-pose 3D position of every skin texel of the visible body (helper shells skipped), by rasterising the
    mesh's UV triangles. Returns an (h, w, 3) array and an (h, w) coverage mask."""
    verts, tris, uvs = rest_mesh(obj)
    gi = obj.vertex_groups["body"].index
    body = {v.index for v in obj.data.vertices if any(g.group == gi and g.weight > 0.5 for g in v.groups)}
    pos = np.zeros((h, w, 3), np.float32)
    hit = np.zeros((h, w), bool)
    for t, tuv in zip(tris, uvs):
        if not all(k in body for k in t):
            continue
        p = np.array([tuple(verts[k]) for k in t], np.float32)
        px = np.array([[q.x * w - 0.5, q.y * h - 0.5] for q in tuv])
        x0, y0 = np.maximum(np.floor(px.min(0)).astype(int), 0)
        x1, y1 = np.minimum(np.ceil(px.max(0)).astype(int), (w - 1, h - 1))
        if x1 < x0 or y1 < y0:
            continue
        (ax, ay), (bx, by), (cx, cy) = px
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-9:
            continue
        ys, xs = np.mgrid[y0:y1 + 1, x0:x1 + 1]
        l0 = ((by - cy) * (xs - cx) + (cx - bx) * (ys - cy)) / den
        l1 = ((cy - ay) * (xs - cx) + (ax - cx) * (ys - cy)) / den
        l2 = 1 - l0 - l1
        m = (l0 >= -0.02) & (l1 >= -0.02) & (l2 >= -0.02)
        if not m.any():
            continue
        lam = np.stack([l0[m], l1[m], l2[m]], -1)
        pos[ys[m], xs[m]] = lam @ p
        hit[ys[m], xs[m]] = True
    return pos, hit


def blob(pos, centre, radii):
    """Smooth ellipsoidal falloff (1 at the centre, 0 past the radii) around a 3D point."""
    d = ((pos - np.array(centre, np.float32)) / np.array(radii, np.float32)) ** 2
    return np.clip(1.0 - d.sum(-1), 0, 1) ** 2


def skin_regions(pos, hit):
    """Masks for regional skin variation, placed from the face's own landmarks in the rest pose (MakeHuman faces -Y):
    the nose tip is the most forward head point, the ears the widest."""
    head = hit & (pos[..., 2] > pos[..., 2][hit].max() - 0.25)
    hp = pos[head]
    nose = hp[hp[:, 1].argmin()]
    ear = hp[np.abs(hp[:, 0]).argmax()]
    x_ear, z_ear = abs(ear[0]), ear[2]
    nx, ny, nz = nose
    flush = np.zeros(pos.shape[:2], np.float32)
    for sx in (-1, 1):
        flush = np.maximum(flush, 0.8 * blob(pos, (sx * 0.042, ny + 0.045, nz + 0.0), (0.028, 0.03, 0.026)))
        flush = np.maximum(flush, 0.9 * blob(pos, (sx * x_ear, ear[1], z_ear), (0.02, 0.035, 0.045)))
    flush = np.maximum(flush, blob(pos, (nx, ny + 0.004, nz - 0.002), (0.016, 0.02, 0.016)))
    # T-zone (forehead centre, nose) is oilier and shinier; lips are glossier still.
    tzone = np.maximum(blob(pos, (0, ny + 0.06, nz + 0.075), (0.04, 0.05, 0.035)),
                       blob(pos, (nx, ny + 0.01, nz + 0.02), (0.014, 0.03, 0.04)))
    lips = blob(pos, (nx, ny + 0.022, nz - 0.042), (0.024, 0.02, 0.011))
    return flush * head, tzone * head, lips * head


def make_skin_roughness(pos, hit, tzone, lips, size):
    """Roughness map: 0.52 on the body, down to ~0.36 on the T-zone and ~0.3 on the lips, plus a little fine
    noise so the specular breaks up. Stored in G (glTF metallicRoughness)."""
    rng = np.random.default_rng(11)
    noise = blur_wrap(rng.random((size, size)).astype(np.float32), 2)
    noise = (noise - noise.mean()) / noise.std()
    r = 0.52 - 0.16 * tzone - 0.22 * lips + 0.03 * noise
    r = np.clip(np.where(hit, r, 0.52), 0.25, 0.75)
    rgba = np.stack([r, r, r, np.ones_like(r)], -1).astype(np.float32)
    img = bpy.data.images.new("claude_skin_roughness", size, size, alpha=False)
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = os.path.join(TEX, "claude_skin_roughness.png")
    img.file_format = "PNG"
    img.save()
    img.colorspace_settings.name = "Non-Color"
    return img


def skin(obj, cards):
    mat = obj.active_material
    node = image_nodes(mat)[0]
    a = pixels(node.image)
    rgb = a[..., :3]
    lum = rgb.mean(axis=-1, keepdims=True)
    warm = np.array([1.0, 0.86, 0.72], dtype=np.float32)
    rgb = np.clip(rgb * warm * 0.86 + (lum * warm * 0.86 - rgb * warm * 0.86) * 0.08, 0, 1)
    h, w = a.shape[:2]
    pos, hit = position_map(obj, h, w)
    flush, tzone, lips = skin_regions(pos, hit)
    # Blood flush: cheeks, nose tip and ears shift toward a deeper rose.
    f = flush[..., None] * 0.75
    rgb = rgb * (1 - f) + rgb * np.array([1.0, 0.8, 0.78], np.float32) * f
    a[..., :3] = rgb
    if cards:
        paint_under_cards(obj, a, *cards)
    node.image = save_copy(node.image, a, "claude_skin_diffuse")
    bsdf = principled(mat)
    nt = mat.node_tree
    rough = nt.nodes.new("ShaderNodeTexImage")
    rough.image = make_skin_roughness(pos, hit, tzone, lips, h)
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(rough.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
    print(f"[materials] skin regions: {int(hit.sum())} body texels, flush {int((flush > 0.05).sum())}, "
          f"t-zone {int((tzone > 0.05).sum())}, lips {int((lips > 0.05).sum())}")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = make_pore_normal()
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (18.0, 18.0, 1.0)
    nt.links.new(coord.outputs["UV"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
    nmap = nt.nodes.new("ShaderNodeNormalMap")
    nmap.inputs["Strength"].default_value = 0.6
    nt.links.new(tex.outputs["Color"], nmap.inputs["Color"])
    nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])


def eyes(mat):
    node = image_nodes(mat)[0]
    src = bpy.data.images.load(os.path.join(DATA, "eyes", "materials", "brown_eye.png"))
    a = pixels(src)
    rgb = a[..., :3]
    mx, mn = rgb.max(-1), rgb.min(-1)
    sat = (mx - mn) / np.maximum(mx, 1e-4)
    # The CC0 iris is a saturated red-brown that reads as red under arena light; rebuild it as a dark brown
    # (hue 24 deg) keeping its brightness detail. The weight fades out on the pale, pink-veined sclera.
    w = np.clip((sat - 0.35) / 0.2, 0, 1) * (rgb[..., 0] > rgb[..., 2] * 1.3)
    brown = np.array(colorsys.hsv_to_rgb(24 / 360, 0.62, 1.0), dtype=np.float32)
    iris = brown * (mx * 0.78)[..., None]
    a[..., :3] = rgb * (1 - w[..., None]) + iris * w[..., None]
    node.image = save_copy(src, a, "claude_eye_diffuse")
    bsdf = principled(mat)
    bsdf.inputs["Roughness"].default_value = 0.08
    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = 1.0
        bsdf.inputs["Coat Roughness"].default_value = 0.02


def darken_hair(mat, name, roughness, colour=None):
    """Darken hair cards to near-black brown; or, given a colour, recolour them to it (keeping their light/dark
    strand variation), for the brows, whose CC0 texture is black."""
    for node in image_nodes(mat):
        a = pixels(node.image)
        if colour is None:
            a[..., :3] = np.clip(a[..., :3] * np.array([0.32, 0.25, 0.21]) + 0.012, 0, 1)
        else:
            lum = a[..., :3].mean(-1, keepdims=True)
            rel = np.clip(lum / max(lum[a[..., 3] > 0.3].mean(), 1e-4), 0.5, 1.6)
            a[..., :3] = np.clip(np.array(colour) * (0.7 + 0.3 * rel), 0, 1)
        node.image = save_copy(node.image, a, name)
    bsdf = principled(mat)
    bsdf.inputs["Roughness"].default_value = roughness
    if colour is not None:
        # MPFB's brow material uses the diffuse image as a bump height (exported as a meaningless normal map) and
        # routes the colour through a "diffuseIntensity" mix; wire the recoloured texture straight in instead.
        nt = mat.node_tree
        for n in [n for n in nt.nodes if n.type == "BUMP"]:
            nt.nodes.remove(n)
        diffuse = next(n for n in image_nodes(mat) if any(l.to_socket.name == "Alpha" for l in n.outputs["Alpha"].links))
        nt.links.new(diffuse.outputs["Color"], bsdf.inputs["Base Color"])
        for n in [n for n in image_nodes(mat) if n.name != diffuse.name]:
            nt.nodes.remove(n)


def rest_mesh(obj):
    """Triangles of obj in its rest shape (shape keys applied, other modifiers off): verts, tri vertex ids, tri UVs."""
    saved = [(m, m.show_viewport) for m in obj.modifiers]
    for m, _ in saved:
        m.show_viewport = False
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    me.calc_loop_triangles()
    verts = [obj.matrix_world @ v.co for v in me.vertices]
    uv = me.uv_layers.active.data
    tris = [tuple(t.vertices) for t in me.loop_triangles]
    uvs = [tuple(Vector(uv[l].uv) for l in t.loops) for t in me.loop_triangles]
    ev.to_mesh_clear()
    for m, vis in saved:
        m.show_viewport = vis
    return verts, tris, uvs


class CardSampler:
    """Nearest-point lookup on a hair or brow card mesh, returning that point's texture alpha."""

    def __init__(self, obj):
        self.verts, self.tris, self.uvs = rest_mesh(obj)
        self.bvh = BVHTree.FromPolygons(self.verts, self.tris)
        img = image_nodes(obj.active_material)[0].image
        self.alpha = pixels(img)[..., 3]
        self.rgb = pixels(img)[..., :3]

    def sample(self, co, maxdist):
        loc, _, i, d = self.bvh.find_nearest(co, maxdist)
        if loc is None:
            return 0.0, maxdist
        a, b, c = (self.verts[k] for k in self.tris[i])
        ua, ub, uc = (u.to_3d() for u in self.uvs[i])
        u = barycentric_transform(loc, a, b, c, ua, ub, uc)
        h, w = self.alpha.shape
        return float(self.alpha[min(int(u.y % 1 * h), h - 1), min(int(u.x % 1 * w), w - 1)]), d

    def mean_colour(self):
        m = self.alpha > 0.6
        return self.rgb[m].mean(axis=0)


def blur(a, r, passes=3):
    for _ in range(passes):
        a = blur_wrap(a, r)
    return a


def hairline_strands(rgb, cap, seen, colour, band=24, seed=11):
    """Call #8: a real hairline isn't a line. Past the hair cap's cutout edge, fine short hairs thin out over about
    1 cm (24 texels here) of forehead and temple. They are painted into the skin as thin strokes pointing into the
    cap, denser and darker near the edge, plus a faint shadow tint, so the cap's hard cutout edge sits in a soft
    gradient instead of on bare skin."""
    rng = np.random.default_rng(seed)
    h, w = cap.shape
    # Distance (texels, 4-neighbour steps) outward from the visible cap, over the skin texels near the hair only.
    dist = np.full((h, w), np.inf, np.float32)
    dist[cap] = 0
    cur = cap.copy()
    for k in range(1, band + 1):
        grown = cur.copy()
        grown[1:] |= cur[:-1]
        grown[:-1] |= cur[1:]
        grown[:, 1:] |= cur[:, :-1]
        grown[:, :-1] |= cur[:, 1:]
        grown &= seen | cap
        dist[grown & ~cur] = k
        cur = grown
    # Direction into the cap: the gradient of the blurred cap mask.
    soft = blur(cap.astype(np.float32), 4)
    gy, gx = np.gradient(soft)
    norm = np.hypot(gx, gy)
    ys, xs = np.nonzero((dist > 0) & (dist <= band) & (norm > 1e-4))
    d = dist[ys, xs] / band
    keep = rng.random(len(ys)) < 0.2 * (1 - d) ** 1.1
    ys, xs, d = ys[keep], xs[keep], d[keep]
    ang = np.arctan2(gy[ys, xs], gx[ys, xs]) + rng.normal(0, 0.22, len(ys))
    length = d * band + rng.uniform(0.5, 2.0, len(ys))
    strength = rng.uniform(0.3, 0.6, len(ys)) * (1 - d) ** 0.5
    # Each stroke runs from its root on the skin to just inside the cap, splatted bilinearly every half texel; it is
    # faint at the root and fades again where it meets the cap, so the ends don't pile up into a line at the edge.
    acc = np.zeros((h, w), np.float32)
    steps = np.arange(0, band + 2.5, 0.5, dtype=np.float32)
    for t0 in steps:
        on = t0 <= length
        if not on.any():
            break
        fx = xs[on] + np.cos(ang[on]) * t0
        fy = ys[on] + np.sin(ang[on]) * t0
        u = t0 / length[on]
        wgt = strength[on] * np.sin(np.pi * np.clip(0.15 + 0.85 * u, 0, 1)) ** 0.7 * 0.5
        x0, y0 = np.floor(fx).astype(int), np.floor(fy).astype(int)
        ax, ay = fx - x0, fy - y0
        for ox, oy, ww in ((0, 0, (1 - ax) * (1 - ay)), (1, 0, ax * (1 - ay)), (0, 1, (1 - ax) * ay), (1, 1, ax * ay)):
            xi, yi = np.clip(x0 + ox, 0, w - 1), np.clip(y0 + oy, 0, h - 1)
            np.add.at(acc, (yi, xi), wgt * ww)
    acc = (1 - np.exp(-1.6 * acc)) * 0.8 * ~cap
    shadow = np.where(np.isfinite(dist) & ~cap, np.clip(1 - dist / (band * 0.6), 0, 1) ** 1.5 * 0.3, 0)
    # Skin under the visible cap shows only through its cutout gaps at the edge; there it should read as scalp.
    shadow = np.where(cap, 0.6, shadow)
    for wgt, col in ((shadow, colour * 1.1), (acc, colour * 1.05)):
        wgt = wgt[..., None]
        rgb[:] = rgb * (1 - wgt) + col * wgt
    print(f"[materials] hairline: {len(ys)} strands over {int(((dist > 0) & (dist <= band)).sum())} band texels")


def paint_under_cards(skin_obj, skin_arr, hair_obj, brow_obj):
    """Project the hair cap and brow cards straight down onto the skin texture and darken the skin there.
    Every skin texel near the head is mapped to its 3D rest position; the nearest point on the card mesh gives the
    card's alpha (coverage), faded out with distance from the card. Coverage is blurred so the hairline is soft."""
    verts, tris, uvs = rest_mesh(skin_obj)
    # Only the visible body: MPFB's helper shells (hidden by the "body" mask at export) sit right on the cards.
    gi = skin_obj.vertex_groups["body"].index
    body = {v.index for v in skin_obj.data.vertices if any(g.group == gi and g.weight > 0.5 for g in v.groups)}
    h, w = skin_arr.shape[:2]
    hair, brow = CardSampler(hair_obj), CardSampler(brow_obj)
    # The ponytail hangs onto the upper back; only the cap over the skull counts as scalp.
    nape = max(v.z for v in hair.verts) - 0.21
    cover = {"hair": np.zeros((h, w), np.float32), "brow": np.zeros((h, w), np.float32)}
    # For the hairline strands (call #8): where the cap is visible (alpha past its cutout) and which texels were looked at.
    cap = np.zeros((h, w), bool)
    seen = np.zeros((h, w), bool)
    # The ears sit right under the cap's edge; keep the scalp shading and strands off them (the widest head point).
    top = max(verts[k].z for k in body)
    ear = max((verts[k] for k in body if verts[k].z > top - 0.25), key=lambda v: abs(v.x))
    ears = [Vector((sx * abs(ear.x), ear.y, ear.z)) for sx in (-1, 1)]

    def on_ear(co):
        return any(((co.x - e.x) / 0.02) ** 2 + ((co.y - e.y) / 0.035) ** 2 + ((co.z - e.z) / 0.045) ** 2 < 1
                   for e in ears)
    reach = {"hair": 0.03, "brow": 0.015}
    full = {"hair": 0.010, "brow": 0.008}
    for t, tuv in zip(tris, uvs):
        if not all(k in body for k in t):
            continue
        p = [verts[k] for k in t]
        centre = (p[0] + p[1] + p[2]) / 3
        near = [(n, s) for n, s in (("hair", hair), ("brow", brow))
                if s.bvh.find_nearest(centre, reach[n] + 0.02)[0] and (n == "brow" or centre.z > nape)]
        if not near:
            continue
        px = np.array([[q.x * w - 0.5, q.y * h - 0.5] for q in tuv])
        x0, y0 = np.floor(px.min(0)).astype(int)
        x1, y1 = np.ceil(px.max(0)).astype(int)
        (ax, ay), (bx, by), (cx, cy) = px
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-9:
            continue
        for y in range(max(y0, 0), min(y1 + 1, h)):
            for x in range(max(x0, 0), min(x1 + 1, w)):
                l0 = ((by - cy) * (x - cx) + (cx - bx) * (y - cy)) / den
                l1 = ((cy - ay) * (x - cx) + (ax - cx) * (y - cy)) / den
                l2 = 1 - l0 - l1
                if min(l0, l1, l2) < -0.02:
                    continue
                co = p[0] * l0 + p[1] * l1 + p[2] * l2
                for n, s in near:
                    a, d = s.sample(co, reach[n])
                    if n == "hair":
                        a *= min(max((co.z - nape) / 0.02, 0.0), 1.0)
                        if on_ear(co):
                            continue
                        seen[y, x] = True
                        cap[y, x] |= a > HAIR_CUTOFF and d < full[n]
                    fade = 1.0 - min(max((d - full[n]) / (reach[n] - full[n]), 0.0), 1.0)
                    cover[n][y, x] = max(cover[n][y, x], a * fade)
    rgb = skin_arr[..., :3]
    # The hair cap is a shell over the scalp; below it the scalp shows only through the cutout gaps, so it is
    # painted almost the hair colour. Brows are painted lighter, to add density under the sparse brow cards.
    # A wide, faint feather past the cap edge stands in for the fine hairs of a real hairline.
    hair_c = cover["hair"] * 0.3 + blur(cover["hair"], 3) * 0.4 + blur(cover["hair"], 6) * 0.55
    # Brows: the strand alpha, slightly dilated and boosted, gives a soft base under the sparse brow strands.
    brow_c = np.clip(blur(cover["brow"], 1, 2) * 1.8, 0, 1)
    for c, col, k in ((hair_c, hair.mean_colour() * 1.15, 0.85), (brow_c, brow.mean_colour() * 0.9, 0.35)):
        wgt = np.clip(c * k, 0, 1)[..., None]
        rgb[:] = rgb * (1 - wgt) + col * wgt
    hairline_strands(rgb, cap, seen, hair.mean_colour())
    print(f"[materials] painted under cards: hair {int((cover['hair'] > 0.05).sum())} texels, "
          f"brows {int((cover['brow'] > 0.05).sum())} texels")


def sportsuit(mat):
    node = next(n for n in image_nodes(mat) if "diffuse" in n.image.name.lower() or len(image_nodes(mat)) == 1)
    a = pixels(node.image)
    rgb = a[..., :3]
    mx, mn = rgb.max(-1), rgb.min(-1)
    sat = (mx - mn) / np.maximum(mx, 1e-4)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    blue = (b > r * 1.15) & (b > g) & (sat > 0.18)
    grey = sat < 0.12
    orange = (r > g * 1.2) & (r > b * 2.0) & (sat > 0.45)
    terracotta = np.array(colorsys.hsv_to_rgb(12 / 360, 0.76, 0.42), dtype=np.float32)
    shade = (mx / max(mx[blue].mean() if blue.any() else 1, 1e-3))[..., None]
    # The CC0 top's lighter and darker blue panels (collar band, inner neckline) turned into blotchy light/dark
    # terracotta patches; keep only 40 % of that contrast so the fabric reads as one dyed knit.
    shade = np.clip(1.0 + 0.4 * (shade - 1.0), 0.82, 1.08)
    rgb[blue] = np.clip(terracotta * shade[blue], 0, 1)
    # Bright orange piping on terracotta looked like a costume; make it charcoal, like the leggings.
    piping = np.array([0.075, 0.07, 0.068], np.float32)
    rgb[orange] = piping * (0.85 + 0.3 * (mx[orange] / max(mx[orange].mean(), 1e-3)))[..., None]
    rgb[grey] = np.clip(rgb[grey] * 0.32, 0, 1)
    a[..., :3] = rgb
    node.image = save_copy(node.image, a, "claude_trainingwear_diffuse")
    principled(mat).inputs["Roughness"].default_value = 0.78


def set_alpha(mat, cutout, cutoff=0.4):
    """glTF alpha: skin, teeth and cloth are opaque; hair, brows, lashes and the eyes' clear cornea shell use an
    alpha cutoff (MASK).
    MakeHuman materials route texture alpha into every BSDF, which exports as BLEND and breaks depth sorting."""
    nt = mat.node_tree
    bsdf = principled(mat)
    alpha_in = bsdf.inputs["Alpha"]
    src = alpha_in.links[0].from_socket if alpha_in.links else None
    for link in list(alpha_in.links):
        nt.links.remove(link)
    if cutout and src is not None:
        clip = nt.nodes.new("ShaderNodeMath")
        clip.operation = "GREATER_THAN"
        clip.inputs[1].default_value = cutoff
        nt.links.new(src, clip.inputs[0])
        nt.links.new(clip.outputs[0], alpha_in)
    else:
        alpha_in.default_value = 1.0
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "DITHERED"
    mat.use_backface_culling = not cutout


def main():
    bpy.ops.wm.open_mainfile(filepath=os.path.join(WORK, "claude_human.blend"))
    done = []
    meshes = [o for o in bpy.data.objects if o.type == "MESH" and o.active_material]
    hair_obj = next(o for o in meshes if "ponytail" in o.name.lower())
    brow_obj = next(o for o in meshes if "eyebrow" in o.name.lower())
    # Hair and brows are darkened before the skin, whose scalp and brow shading takes their final colour.
    darken_hair(hair_obj.active_material, "claude_hair_diffuse", 0.68); done.append("hair")
    darken_hair(brow_obj.active_material, "claude_brows_diffuse", 0.6, colour=(0.21, 0.135, 0.095)); done.append("brows")
    for obj in meshes:
        n = obj.name.lower()
        if obj.name == "Human":
            skin(obj, (hair_obj, brow_obj)); done.append("skin + scalp/brow shading")
        elif "high-poly" in n:
            eyes(obj.active_material); done.append("eyes")
        elif "sportsuit" in n:
            sportsuit(obj.active_material); done.append("trainingwear")
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            for slot in obj.material_slots:
                if slot.material and slot.material.use_nodes:
                    n = obj.name.lower()
                    # A slightly lower cutoff keeps a few more of the brow texture's soft outer strands; on the hair it
                    # keeps the fine strands at the hairline, so the edge is less of a cut-out line (call #5). A higher
                    # cutoff on the lashes keeps only their dense cores: finer lashes.
                    cutoff = 0.36 if "eyebrow" in n else HAIR_CUTOFF if "ponytail" in n else 0.5 if "eyelash" in n else 0.4
                    set_alpha(slot.material, cutout=any(k in n for k in ("ponytail", "eyebrow", "eyelash", "high-poly")),
                              cutoff=cutoff)
    print("[materials]", ", ".join(done), "+ alpha modes")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(WORK, "claude_materials.blend"))


main()
