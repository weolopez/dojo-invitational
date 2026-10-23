"""
Generate original PBR source textures for the Hermes fighter (a FICTIONAL person).
Everything here is procedurally generated from scratch — not from any real person's
photo, not scraped, not a scan. Output goes ONLY inside entries/hermes/source/textures/.
"""
from PIL import Image, ImageDraw, ImageFilter
import os, math

DEST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "textures")
os.makedirs(DEST, exist_ok=True)

# ---- Iris (hazel, radial streaks, pupil, limbal ring, catchlight) ----
S = 1024
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
px = img.load()
cx = cy = S // 2
R = S * 0.46
for y in range(S):
    for x in range(S):
        dx = (x - cx) / R
        dy = (y - cy) / R
        r = math.hypot(dx, dy)
        if r < 0.33:                      # pupil
            px[x, y] = (6, 4, 4, 255)
        elif r < 0.92:                    # iris
            ang = math.atan2(dy, dx)
            streak = (math.sin(ang * 26 + r * 11) * 0.5 + 0.5)
            fib = (math.sin(ang * 60) * 0.5 + 0.5) * 0.25
            base_r = 95 + int(streak * 85 + fib * 40)
            base_g = 60 + int(streak * 55 + fib * 25)
            base_b = 28 + int(streak * 35)
            if r > 0.72:                  # limbal ring darkening
                k = (r - 0.72) / 0.2
                base_r = int(base_r * (1 - 0.55 * k))
                base_g = int(base_g * (1 - 0.55 * k))
                base_b = int(base_b * (1 - 0.55 * k))
            px[x, y] = (min(base_r, 255), min(base_g, 255), min(base_b, 255), 255)
        elif r < 1.18:                    # sclera
            px[x, y] = (246, 241, 232, 255)

hl = Image.new("L", (S, S), 0)
ImageDraw.Draw(hl).ellipse([int(S*0.36), int(S*0.22), int(S*0.52), int(S*0.38)], fill=200)
hl = hl.filter(ImageFilter.GaussianBlur(S // 40))
white = Image.new("RGBA", (S, S), (255, 255, 255, 0))
wp = white.load()
hp = hl.load()
for y in range(S):
    for x in range(S):
        a = hp[x, y]
        if a:
            wp[x, y] = (255, 255, 255, int(a * 0.6))
img = Image.alpha_composite(img, white)
img.save(os.path.join(DEST, "iris.png"))

# ---- Hair strand card (alpha) ----
W, H = 1024, 256
hair = Image.new("RGBA", (W, H), (0, 0, 0, 0))
hp = hair.load()
import random
random.seed(7)
for i in range(180):
    x0 = random.uniform(0, W)
    width = random.uniform(1.2, 3.0)
    wob = random.uniform(0.15, 0.4)
    phase = random.uniform(0, 6.28)
    tone = random.choice([(28, 20, 12), (44, 30, 18), (60, 42, 26), (20, 14, 9)])
    for y in range(H):
        xx = x0 + math.sin(y * 0.02 + phase) * wob * y
        a = int(255 * (1 - y / H) ** 0.6)
        for d in range(int(width)):
            X = int(xx + d)
            if 0 <= X < W and a > 0:
                hp[X, y] = (*tone, a)
hair.save(os.path.join(DEST, "hair_strand.png"))

# ---- Winged emblem (wardrobe accent, fictional, no logo/trademark) ----
E = 1024
emb = Image.new("RGBA", (E, E), (0, 0, 0, 0))
d = ImageDraw.Draw(emb)
gold = (198, 168, 108, 255)
gold_d = (150, 122, 70, 255)
def wing(mirror):
    pts = [(512, 420), (300, 240), (180, 320), (330, 470), (210, 600), (360, 540),
           (430, 540), (512, 650)]
    if mirror:
        pts = [(E - x, y) for x, y in pts]
    d.polygon(pts, fill=gold, outline=gold_d)
wing(False); wing(True)
for fx in [(230, 440, 360, 520), (E-230, 440, E-360, 520),
           (260, 540, 400, 540), (E-260, 540, E-400, 540)]:
    d.line(fx, fill=gold_d, width=6)
emb.save(os.path.join(DEST, "winged_emblem.png"))

# ---- report ----
for f in ["iris.png", "hair_strand.png", "winged_emblem.png"]:
    p = os.path.join(DEST, f)
    im = Image.open(p)
    print(f"TEX: {f} {im.size[0]}x{im.size[1]} {os.path.getsize(p)} bytes")
print("TEX: all written to", DEST)
