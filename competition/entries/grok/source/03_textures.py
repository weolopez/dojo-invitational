# Generates the procedural (original, no third-party) textures: tileable skin micro-detail normal + roughness,
# and recoloured fabric maps derived from CC0 Poly Haven scans. Run with Blender's Python (numpy bundled).
import numpy as np, os, bpy
HERE = os.path.dirname(os.path.abspath(__file__)); TEX = os.path.join(HERE, '..', 'tmp', 'tex'); os.makedirs(TEX, exist_ok=True)
PH = os.path.join(HERE, '..', 'tools', 'polyhaven')
rng = np.random.default_rng(7)
N = 1024
def blur_periodic(a, sigma):
    f = np.fft.fft2(a); ky = np.fft.fftfreq(a.shape[0])[:, None]; kx = np.fft.fftfreq(a.shape[1])[None, :]
    return np.real(np.fft.ifft2(f * np.exp(-2 * (np.pi * sigma) ** 2 * (kx ** 2 + ky ** 2))))
# height: pores (dimples) + fine bumps + faint crossing micro-wrinkles, all periodic
h = np.zeros((N, N))
pores = np.zeros((N, N)); idx = rng.integers(0, N, size=(9000, 2)); pores[idx[:, 0], idx[:, 1]] = 1
h -= blur_periodic(pores, 1.6) * 6.0
h += blur_periodic(rng.standard_normal((N, N)), 1.0) * 0.35
h += blur_periodic(rng.standard_normal((N, N)), 6.0) * 1.5
yy, xx = np.mgrid[0:N, 0:N] / N
for ang, fr in [(0.6, 90), (-0.9, 70)]:
    w = np.sin(2 * np.pi * (np.round(fr*np.cos(ang)) * xx + np.round(fr*np.sin(ang)) * yy))
    h += 0.08 * np.maximum(w, 0) ** 8 * blur_periodic(rng.standard_normal((N, N)), 20) * 8
h = (h - h.mean()) / h.std()
gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) / 2; gy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) / 2
s = 0.55
n = np.dstack([-gx * s, gy * s, np.ones_like(h)]); n /= np.linalg.norm(n, axis=2, keepdims=True)
def save(name, rgb):
    hgt, wid = rgb.shape[:2]
    img = bpy.data.images.new(name, wid, hgt, alpha=False)
    px = np.ones((hgt, wid, 4), np.float32); px[..., :3] = rgb
    img.pixels.foreach_set(px[::-1].ravel()); img.filepath_raw = os.path.join(TEX, name + '.png'); img.file_format = 'PNG'; img.save()
save('skin_micro_normal', n * 0.5 + 0.5)
# roughness (G) : pores slightly rougher; fine variation 0.38..0.62
r = 0.5 + 0.06 * np.clip(-h, -2, 3) + 0.04 * blur_periodic(rng.standard_normal((N, N)), 12) / 0.02 * 0.02
r = np.clip(r, 0.3, 0.7)
save('skin_micro_rough', np.dstack([np.ones_like(r), r, np.zeros_like(r)]))
# fabric recolours
def load(p):
    im = bpy.data.images.load(p); a = np.array(im.pixels[:], np.float32).reshape(im.size[1], im.size[0], 4)[::-1]; return a[..., :3]
d = load(os.path.join(PH, 'bi_stretch_diff_2k.jpg')); lum = d.mean(2, keepdims=True); lum = lum / lum.mean()
save('fabric_charcoal_diff', np.clip(lum * np.array([0.115, 0.118, 0.13]), 0, 1))
save('fabric_white_diff', np.clip(lum * np.array([0.80, 0.80, 0.82]), 0, 1))
c = load(os.path.join(PH, 'cotton_jersey_diff_2k.jpg')); lum = c.mean(2, keepdims=True); lum = lum / lum.mean()
save('wrap_diff', np.clip(lum * np.array([0.78, 0.76, 0.72]), 0, 1))
def save_rgba(name, rgba):
    hgt, wid = rgba.shape[:2]
    img = bpy.data.images.new(name, wid, hgt, alpha=True)
    img.pixels.foreach_set(rgba[::-1].astype(np.float32).ravel()); img.filepath_raw = os.path.join(TEX, name + '.png'); img.file_format = 'PNG'; img.save()
MH = os.path.join(HERE, '..', 'tools', 'mhassets')
for name, src, tint in [('hair_diff', 'hair/short02/short02_diffuse.png', (0.075, 0.058, 0.045)),
                        ('brow_diff', 'eyebrows/eyebrow001/eyebrow001.png', (0.06, 0.045, 0.035)),
                        ('lash_diff', 'eyelashes/eyelashes01/eyelashes01.png', (0.03, 0.025, 0.02))]:
    im = bpy.data.images.load(os.path.join(MH, src)); a = np.array(im.pixels[:], np.float32).reshape(im.size[1], im.size[0], 4)[::-1]
    lum = a[..., :3].mean(2, keepdims=True); lum = lum / max(lum[a[..., 3] > 0.5].mean(), 1e-3) if (a[..., 3] > 0.5).any() else lum
    out = a.copy(); out[..., :3] = np.clip(lum * np.array(tint) * 2.2, 0, 1); save_rgba(name, out)
im = bpy.data.images.load(os.path.join(MH, 'eyes/materials/brown_eye.png')); a = np.array(im.pixels[:], np.float32).reshape(im.size[1], im.size[0], 4)[::-1]
rgb = a[..., :3]; mx = rgb.max(2, keepdims=True); mn = rgb.min(2, keepdims=True); sat = np.clip((mx - mn) / np.maximum(mx, 1e-3) * 1.5, 0, 1)
lum = rgb.mean(2, keepdims=True); brown = np.clip(mx * np.array([0.62, 0.40, 0.24]), 0, 1)
out = a.copy(); out[..., :3] = rgb * (1 - sat) + brown * sat; save_rgba('eye_diff', out)
# shell-hair strand textures: short streaks; each strand gets a random length, layer group g shows strands longer than g
M = 1024; base = np.zeros((M, M)); length = np.zeros((M, M)); col = np.zeros((M, M))
cnt = 26000; P0 = rng.integers(0, M, (cnt, 2)); L = rng.random(cnt); C = rng.random(cnt)
for (y, x), l, c in zip(P0, L, C):
    for t in range(9):
        yy = (y + t) % M; xx = (x + (t * 3) // 9) % M
        length[yy, xx] = max(length[yy, xx], l); col[yy, xx] = c
for gi, thr in enumerate([0.0, 0.35, 0.65]):
    a = (length > thr).astype(np.float32)
    a = np.clip(blur_periodic(a, 0.5) * 1.6, 0, 1)
    rgb = np.dstack([0.045 + 0.03 * col, 0.035 + 0.022 * col, 0.028 + 0.015 * col])
    save_rgba('hair_shell_%d' % gi, np.dstack([rgb, a]))
print("TEX DONE")
