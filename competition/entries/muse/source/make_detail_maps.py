"""Call-10 (v3.8) texture work

NOTE: run this script from a directory that does not contain an
inspect.py (e.g. the entry folder itself), or stdlib `inspect` gets
shadowed during the numpy import and the script fails on startup.
 for the muse fighter.

Judge's cap, repeated in calls/muse.md and scores.json: poreless skin,
painted eyes with no depth, sculpted-shell hair, baked costume folds,
build scripts not in the entry folder. This script attacks the first
three with texture work only (eyeball geometry stays disabled: the
skinning offset is unresolved, see build_fighter_v38.py):

- Eyes: the painted eyes are repainted in the diffuse at their measured
  UV boxes (probe_eyes2.py candidates, confirmed by crop inspection):
  warm sclera with shaded corners, a striated brown iris with a dark
  limbal ring, a pupil, a catchlight, and an upper-lid shadow + lash
  line. The eye boxes in the metallic-roughness map are set to
  roughness 0.07 (green channel 18) so the painted eyes take a wet
  specular highlight -- the value the v3.7 manifest claimed but the
  shipped MR map did not contain (measured 0.18-0.19 at the eye UVs).
- Skin: low-frequency mottling (value +/-3.5%, faint warm/cool shift)
  masked to skin, to break the flat poreless look without touching
  cloth, hair or gold.
- Pores: the pore speckle in the detail normal map is denser and a
  little stronger than call 7 (threshold 0.9965, amplitude 2.6, was
  0.9975 / 2.2); hair strand grooves slightly stronger (1.0, was 0.8).
  Strength stays 1.6 -- the call-7 main-chat build showed stronger
  detail reads as pockmarks in the closeup.

Inputs: tex/file11_detail.png (shipped diffuse; both GLB materials
embed identical copies of it), tex/file12.png (base normal),
tex/file_mr.png (shipped metallic-roughness map).
Outputs: tex/file11_v38.png, tex/file12_v38.png, tex/file_mr_v38.png.
The head material's original file14 texture is not used: the v3.7
export embedded file11_detail for both materials (verified: the two
GLB diffuse images are pixel-identical).
"""
import numpy as np
from PIL import Image, ImageFilter, ImageDraw

TEX = "/home/hatch/workspace/dojo-build/tex"
rng = np.random.default_rng(11)

# Painted-eye boxes, measured from tex/file11_detail.png (dark-pixel
# components in the face band y 165-200, which excludes the eyebrows at
# y 152-164 and the nostrils at y ~225). The probe_eyes2.py UV candidates
# do NOT land on the painted eyes in this texture and must not be used.
# Format: (x0, y0, x1, y1) in texture pixels, y down from the top.
EYE_BOXES = [(306, 169, 344, 185), (401, 169, 439, 186)]


def blur(a, rad):
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(rad))
    return np.asarray(im).astype(np.float32) / 255.0


def skin_mask(diff):
    r, g, b = diff[..., 0], diff[..., 1], diff[..., 2]
    mx, mn = diff.max(axis=2), diff.min(axis=2)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    val = mx
    h = np.zeros_like(mx)
    mc = (mx - mn) > 1e-6
    idx = mc & (mx == r); h[idx] = ((g - b) / (mx - mn))[idx] % 6
    idx = mc & (mx == g); h[idx] = ((b - r) / (mx - mn))[idx] + 2
    idx = mc & (mx == b); h[idx] = ((r - g) / (mx - mn))[idx] + 4
    h = h / 6.0
    return (h > 0.02) & (h < 0.11) & (sat > 0.12) & (sat < 0.62) & (val > 0.35)


def eye_boxes(diff):
    """Return the measured painted-eye boxes, verifying dark pixels inside."""
    val = diff.max(axis=2)
    boxes = []
    for (x0, y0, x1, y1) in EYE_BOXES:
        dark = int((val[y0:y1, x0:x1] < 0.35).sum())
        assert dark > 200, f"eye box {(x0, y0, x1, y1)} has only {dark} dark px"
        boxes.append((float(x0), float(y0), float(x1), float(y1)))
        print(f"eye box x {x0}-{x1} y {y0}-{y1} ({dark} dark px)")
    return boxes


def repaint_eyes(diff):
    """Return repainted diffuse (float 0-1) and a list of almond masks."""
    out = diff.copy()
    H, W, _ = diff.shape
    masks = []
    for (x0, y0, x1, y1) in eye_boxes(diff):
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        rx, ry = (x1 - x0) / 2 * 1.15, (y1 - y0) / 2 * 1.10
        iris_r = min(rx * 0.55, ry * 0.80)
        yy, xx = np.mgrid[0:H, 0:W]
        ex = (xx - cx) / rx
        ey = (yy - cy) / ry
        almond = (ex ** 2 + ey ** 2) <= 1.0
        # Restrict work to a tight window for speed.
        wx0, wx1 = int(max(0, cx - rx - 3)), int(min(W, cx + rx + 3))
        wy0, wy1 = int(max(0, cy - ry - 3)), int(min(H, cy + ry + 3))
        sub = np.zeros((H, W), bool)
        sub[wy0:wy1, wx0:wx1] = almond[wy0:wy1, wx0:wx1]
        dx = (xx - cx) / max(iris_r, 1e-6)
        dy = (yy - cy) / max(iris_r, 1e-6)
        rr = np.sqrt(dx ** 2 + dy ** 2)
        ang = np.arctan2(dy, dx)
        stria = 0.85 + 0.30 * np.sin(ang * 26.0 + 1.7 * np.sin(ang * 5.0))
        iris_col = np.array([0.30, 0.19, 0.10]) * stria[..., None]
        iris_col = np.clip(iris_col, 0, 1)
        limbal = (rr >= 0.82) & (rr <= 1.0)
        pupil = rr <= 0.45
        sclera = sub & (rr > 1.0)
        # Sclera: warm white, pinker toward the horizontal corners,
        # slightly shaded under the upper lid.
        corner = np.clip(np.abs(ex), 0, 1)
        top_shade = np.clip(0.90 + 0.10 * (ey + 1) / 2, 0.90, 1.0)
        scl_col = (np.array([0.94, 0.91, 0.87]) * (1 - corner[..., None] * 0.35)
                   + np.array([0.86, 0.74, 0.70]) * corner[..., None] * 0.35)
        scl_col = scl_col * top_shade[..., None]
        painted = out.copy()
        painted[sclera] = scl_col[sclera]
        iris_m = sub & (rr <= 1.0) & ~pupil
        painted[iris_m] = iris_col[iris_m]
        painted[sub & limbal] = np.array([0.10, 0.07, 0.05])
        painted[sub & pupil] = np.array([0.02, 0.02, 0.025])
        # Upper-lid shadow + lash line along the almond's top edge.
        lid = sub & (ey < -0.55) & (ey > -1.0)
        painted[lid] = painted[lid] * 0.82
        lash = sub & (ey < -0.88)
        painted[lash] = np.array([0.08, 0.06, 0.05])
        # Catchlight: small white disc up-left of the pupil centre.
        ccx, ccy = cx - iris_r * 0.35, cy - iris_r * 0.35
        cc = ((xx - ccx) ** 2 + (yy - ccy) ** 2) <= (max(iris_r * 0.16, 1.5) ** 2)
        painted[sub & cc] = np.array([0.98, 0.98, 0.97])
        # Feather the almond edge so the repaint does not alias.
        m = blur(sub.astype(np.float32), 1.2)
        out = out * (1 - m[..., None]) + painted * m[..., None]
        masks.append((cx, cy, rx, ry))
    return out, masks


def main():
    diff = np.asarray(Image.open(f"{TEX}/file11_detail.png").convert("RGB")
                      ).astype(np.float32) / 255.0
    H, W, _ = diff.shape
    # --- diffuse: eye repaint + skin mottling ---
    repainted, eye_masks = repaint_eyes(diff)
    skin = skin_mask(diff)
    skin_s = blur(skin.astype(np.float32), 3)
    mott = np.asarray(Image.fromarray(
        (rng.random((64, 64)).astype(np.float32) * 255).astype(np.uint8)
    ).resize((W, H), Image.BICUBIC)).astype(np.float32) / 255.0
    mott = blur(mott, 2)
    mott = (mott - 0.5) * 2  # -1..1
    out = repainted.copy()
    out[..., 0] = np.clip(out[..., 0] * (1 + 0.035 * mott * skin_s)
                            * (1 + 0.02 * mott * skin_s), 0, 1)
    out[..., 1] = np.clip(out[..., 1] * (1 + 0.035 * mott * skin_s), 0, 1)
    out[..., 2] = np.clip(out[..., 2] * (1 + 0.035 * mott * skin_s)
                            * (1 - 0.02 * mott * skin_s), 0, 1)
    Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8), "RGB").save(
        f"{TEX}/file11_v38.png")
    print("skin px", int(skin.sum()), "-> file11_v38.png")

    # --- MR map: eye boxes to roughness 0.07 ---
    mr = np.asarray(Image.open(f"{TEX}/file_mr.png").convert("RGB"))
    mr_f = mr.astype(np.float32)
    yy, xx = np.mgrid[0:H, 0:W]
    for (cx, cy, rx, ry) in eye_masks:
        ex = (xx - cx) / (rx * 1.1)
        ey = (yy - cy) / (ry * 1.1)
        m = blur(((ex ** 2 + ey ** 2) <= 1.0).astype(np.float32), 2)
        mr_f[..., 1] = mr_f[..., 1] * (1 - m) + 18 * m
        mr_f[..., 2] = mr_f[..., 2] * (1 - m)
    Image.fromarray(np.clip(mr_f, 0, 255).astype(np.uint8), "RGB").save(
        f"{TEX}/file_mr_v38.png")
    print("-> file_mr_v38.png; eye roughness now 0.07 in the eye boxes")

    # --- detail normal: denser pores, stronger hair strands ---
    nrm = np.asarray(Image.open(f"{TEX}/file12.png").convert("RGB")
                     ).astype(np.float32) / 255.0 * 2 - 1
    skin_s2 = blur(skin.astype(np.float32), 3)
    hair = (diff.max(axis=2) > 0.05) & (diff.max(axis=2) < 0.38) & ~skin
    hair_s = blur(hair.astype(np.float32), 3)
    cloth_s = blur((~(skin | hair)).astype(np.float32), 3)
    noise_fine = blur(rng.random((H, W), dtype=np.float32), 0.8)
    dots = (rng.random((H, W), dtype=np.float32) > 0.9965).astype(np.float32)
    dots = blur(dots, 0.7) * 2.6
    yy2, xx2 = np.mgrid[0:H, 0:W]
    weave = (np.sin(xx2 * np.pi / 1.6) + np.sin(yy2 * np.pi / 1.6)) * 0.5
    streak_src = rng.random((H, W), dtype=np.float32)
    streak = np.asarray(Image.fromarray(
        (streak_src * 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(0.6)).resize((W, H))).astype(np.float32) / 255.0
    streak = np.asarray(Image.fromarray(
        (streak * 255).astype(np.uint8)).filter(
        ImageFilter.BoxBlur(6))).astype(np.float32) / 255.0
    height = (skin_s2 * (dots * 0.9 + noise_fine * 0.35)
              + cloth_s * (weave * 0.35 + noise_fine * 0.2)
              + hair_s * (streak * 1.0 + noise_fine * 0.25))
    gy, gx = np.gradient(height)
    detail = np.dstack([-gx, gy, np.ones_like(gx)])
    combined = nrm.copy()
    combined[..., 0] += detail[..., 0] * 1.6
    combined[..., 1] += detail[..., 1] * 1.6
    norm = np.linalg.norm(combined, axis=2, keepdims=True)
    combined = combined / np.maximum(norm, 1e-6)
    Image.fromarray(((combined * 0.5 + 0.5) * 255).astype(np.uint8), "RGB").save(
        f"{TEX}/file12_v38.png")
    print("-> file12_v38.png")

    # --- debug crops of the repainted eyes ---
    v38 = Image.open(f"{TEX}/file11_v38.png")
    for tag, (x0, y0, x1, y1) in zip("LR", EYE_BOXES):
        cx, cy = int((x0 + x1) / 2), int((y0 + y1) / 2)
        v38.crop((cx - 90, cy - 60, cx + 90, cy + 60)).resize(
            (720, 240), Image.LANCZOS).save(f"/tmp/eye_v38_{tag}.png")
    print("debug crops -> /tmp/eye_v38_L.png, /tmp/eye_v38_R.png")


if __name__ == "__main__":
    main()
