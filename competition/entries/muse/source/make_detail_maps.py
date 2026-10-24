import numpy as np
from PIL import Image, ImageFilter
import colorsys

TEX = "/home/hatch/workspace/dojo-build/tex"
rng = np.random.default_rng(7)

diff = np.asarray(Image.open(f"{TEX}/file11.png").convert("RGB")).astype(np.float32) / 255.0
H, W, _ = diff.shape
r, g, b = diff[..., 0], diff[..., 1], diff[..., 2]
mx = diff.max(axis=2); mn = diff.min(axis=2)
sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
val = mx
# hue approx via colorsys on downsampled? do vectorized hue:
h = np.zeros_like(mx)
maskc = (mx - mn) > 1e-6
idx = maskc & (mx == r); h[idx] = ((g - b) / (mx - mn))[idx] % 6
idx = maskc & (mx == g); h[idx] = ((b - r) / (mx - mn))[idx] + 2
idx = maskc & (mx == b); h[idx] = ((r - g) / (mx - mn))[idx] + 4
h = h / 6.0

skin = (h > 0.015) & (h < 0.115) & (sat > 0.055) & (sat < 0.62) & (val > 0.30)
hair = (val > 0.05) & (val < 0.38) & (h > 0.01) & (h < 0.12) & (sat > 0.15) & ~skin
gold = (r > 0.58) & (g > 0.40) & (g < 0.70) & (b < 0.26) & ((r - b) > 0.42) & (sat > 0.5)
cloth = ~(skin | hair | gold)

def blur(a, rad):
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(rad))
    return np.asarray(im).astype(np.float32) / 255.0

def soften(m, rad=3):
    return blur(m.astype(np.float32), rad)

skin_s, hair_s, gold_s, cloth_s = soften(skin), soften(hair), soften(gold), soften(cloth)

# ---- heightfield detail ----
noise_fine = rng.random((H, W), dtype=np.float32)
noise_fine = blur(noise_fine, 0.8)
dots = (rng.random((H, W), dtype=np.float32) > 0.9975).astype(np.float32)
dots = blur(dots, 1.0) * 0.55                      # pore speckle (subtle)
yy, xx = np.mgrid[0:H, 0:W]
weave = (np.sin(xx * np.pi / 1.6) + np.sin(yy * np.pi / 1.6)) * 0.5   # fabric crosshatch
streak_src = rng.random((H, W), dtype=np.float32)
streak = np.asarray(Image.fromarray((streak_src * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6)).resize((W, H))).astype(np.float32) / 255.0
streak = np.asarray(Image.fromarray((streak * 255).astype(np.uint8)).filter(ImageFilter.BoxBlur(6))).astype(np.float32) / 255.0  # vertical-ish smear approx

height = (skin_s * (dots * 0.5 + noise_fine * 0.22)
          + cloth_s * (weave * 0.35 + noise_fine * 0.2)
          + hair_s * (streak * 0.8 + noise_fine * 0.25)
          + gold_s * noise_fine * 0.15)

# ---- blend detail into existing normal map ----
nrm = np.asarray(Image.open(f"{TEX}/file12.png").convert("RGB")).astype(np.float32) / 255.0 * 2 - 1
gy, gx = np.gradient(height)
detail = np.dstack([-gx, gy, np.ones_like(gx)])   # tangent-space-ish detail (v orientation to check in render)
strength = 1.1
n = nrm + detail * strength * np.dstack([np.ones_like(gx)] * 2 + [np.zeros_like(gx)]) * 0  # placeholder
combined = nrm.copy()
combined[..., 0] += detail[..., 0] * strength
combined[..., 1] += detail[..., 1] * strength
norm = np.linalg.norm(combined, axis=2, keepdims=True)
combined = combined / np.maximum(norm, 1e-6)
out_n = ((combined * 0.5 + 0.5) * 255).astype(np.uint8)
Image.fromarray(out_n, "RGB").save(f"{TEX}/file12_detail.png")

# ---- metallic-roughness map (G = roughness, B = metalness) ----
rough = np.full((H, W), 0.66, np.float32)
rough = rough * (1 - skin_s) + (0.60 + (noise_fine - 0.5) * 0.10) * skin_s
rough = rough * (1 - cloth_s) + (0.85 + (noise_fine - 0.5) * 0.06) * cloth_s
rough = rough * (1 - hair_s) + (0.46 + (streak - 0.5) * 0.12) * hair_s
rough = rough * (1 - gold_s) + 0.34 * gold_s
metal = gold_s.copy()
mr = np.zeros((H, W, 3), np.uint8)
mr[..., 1] = (np.clip(rough, 0.03, 1) * 255).astype(np.uint8)
mr[..., 2] = (np.clip(metal, 0, 1) * 255).astype(np.uint8)
Image.fromarray(mr, "RGB").save(f"{TEX}/file_mr.png")

# ---- debug mask view ----
dbg = np.zeros((H, W, 3), np.uint8)
dbg[skin] = (240, 190, 150); dbg[hair] = (110, 70, 40); dbg[gold] = (255, 205, 40); dbg[cloth] = (70, 90, 140)
Image.fromarray(dbg).resize((512, 512)).save("/tmp/masks.png")
print("skin px", int(skin.sum()), "hair px", int(hair.sum()), "gold px", int(gold.sum()), "cloth px", int(cloth.sum()))
print("maps written")
# ---- painted-eye wet finish ----------------------------------------------
# The eyes are painted on the head mesh. Give the painted eye regions a
# near-zero roughness in the MR map so they catch a wet specular highlight
# under arena lighting, and deepen the iris colour in a diffuse copy.
eg = np.zeros((H, W), np.float32)
for (eu, ev) in ((0.189, 0.911), (0.237, 0.910)):
    ex, ey = eu * W, (1 - ev) * H
    dist = ((xx - ex) / (0.017 * W)) ** 2 + ((yy - ey) / (0.011 * H)) ** 2
    eg = np.maximum(eg, np.clip(1 - dist, 0, 1))
eg_s = blur(eg, 1.2)
rough = rough * (1 - eg_s) + 0.07 * eg_s
mr[..., 1] = (np.clip(rough, 0.03, 1) * 255).astype(np.uint8)
Image.fromarray(mr, "RGB").save(f"{TEX}/file_mr.png")
dif2 = diff.copy()
deep = 1 - 0.30 * eg_s[..., None]
dif2 = dif2 * deep + (dif2 * np.array([1.06, 0.92, 0.80])) * (0.30 * eg_s[..., None])
Image.fromarray((np.clip(dif2, 0, 1) * 255).astype(np.uint8), "RGB").save(f"{TEX}/file11_detail.png")
print("eye gloss + diffuse copy written, eye px:", int((eg > 0.3).sum()))


# ---- coat weight map (v3.7): skin gets a light clearcoat "sweat sheen" (72/255
# ~ 0.28), everything else zero. Vectorized from the same skin mask.
coat = np.where(skin, 72, 0).astype(np.uint8)
Image.fromarray(coat, "L").filter(ImageFilter.GaussianBlur(1.2)).save(f"{TEX}/file_coat.png")
print("coat saved")
