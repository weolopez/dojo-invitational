"""Stage 2: realism pass on materials for CLAUDE. Opens .work/claude_human.blend, writes .work/claude_materials.blend.
- Skin: diffuse graded from the CC0 'middleage caucasian female' map toward a warm olive tone; a procedurally generated,
  tiling pore/micro-detail normal map (made here, see make_pore_normal); roughness 0.48.
- Eyes: CC0 brown iris texture; clearcoat for a wet cornea.
- Hair, brows: darkened to near-black brown, alpha kept.
- Sportsuit: blue top recoloured to terracotta, grey leggings to charcoal black.
"""
import colorsys
import os

import bpy
import numpy as np

ENTRY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(ENTRY, ".work")
TEX = os.path.join(WORK, "textures")
DATA = os.path.join(WORK, "mpfb_user", "data")


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


def skin(mat):
    node = image_nodes(mat)[0]
    a = pixels(node.image)
    rgb = a[..., :3]
    lum = rgb.mean(axis=-1, keepdims=True)
    warm = np.array([1.0, 0.86, 0.72], dtype=np.float32)
    rgb = np.clip(rgb * warm * 0.86 + (lum * warm * 0.86 - rgb * warm * 0.86) * 0.08, 0, 1)
    a[..., :3] = rgb
    node.image = save_copy(node.image, a, "claude_skin_diffuse")
    bsdf = principled(mat)
    bsdf.inputs["Roughness"].default_value = 0.48
    nt = mat.node_tree
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
    node.image = bpy.data.images.load(os.path.join(DATA, "eyes", "materials", "brown_eye.png"))
    bsdf = principled(mat)
    bsdf.inputs["Roughness"].default_value = 0.08
    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = 1.0
        bsdf.inputs["Coat Roughness"].default_value = 0.02


def darken_hair(mat, name):
    for node in image_nodes(mat):
        a = pixels(node.image)
        a[..., :3] = np.clip(a[..., :3] * np.array([0.32, 0.25, 0.21]) + 0.012, 0, 1)
        node.image = save_copy(node.image, a, name)
    principled(mat).inputs["Roughness"].default_value = 0.55


def sportsuit(mat):
    node = next(n for n in image_nodes(mat) if "diffuse" in n.image.name.lower() or len(image_nodes(mat)) == 1)
    a = pixels(node.image)
    rgb = a[..., :3]
    mx, mn = rgb.max(-1), rgb.min(-1)
    sat = (mx - mn) / np.maximum(mx, 1e-4)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    blue = (b > r * 1.15) & (b > g) & (sat > 0.18)
    grey = sat < 0.12
    terracotta = np.array(colorsys.hsv_to_rgb(13 / 360, 0.66, 0.78), dtype=np.float32)
    shade = (mx / max(mx[blue].mean() if blue.any() else 1, 1e-3))[..., None]
    rgb[blue] = np.clip(terracotta * shade[blue], 0, 1)
    rgb[grey] = np.clip(rgb[grey] * 0.32, 0, 1)
    a[..., :3] = rgb
    node.image = save_copy(node.image, a, "claude_trainingwear_diffuse")
    principled(mat).inputs["Roughness"].default_value = 0.78


def set_alpha(mat, cutout):
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
        clip.inputs[1].default_value = 0.4
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
    for obj in bpy.data.objects:
        if obj.type != "MESH" or not obj.active_material:
            continue
        mat = obj.active_material
        n = obj.name.lower()
        if obj.name == "Human":
            skin(mat); done.append("skin")
        elif "high-poly" in n:
            eyes(mat); done.append("eyes")
        elif "ponytail" in n:
            darken_hair(mat, "claude_hair_diffuse"); done.append("hair")
        elif "eyebrow" in n:
            darken_hair(mat, "claude_brows_diffuse"); done.append("brows")
        elif "sportsuit" in n:
            sportsuit(mat); done.append("trainingwear")
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            for slot in obj.material_slots:
                if slot.material and slot.material.use_nodes:
                    set_alpha(slot.material, cutout=any(k in obj.name.lower() for k in ("ponytail", "eyebrow", "eyelash", "high-poly")))
    print("[materials]", ", ".join(done), "+ alpha modes")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(WORK, "claude_materials.blend"))


main()
