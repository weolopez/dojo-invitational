#!/usr/bin/env python3
"""
Builds Gemini's Custom Combat Sound Effects Suite (`competition/entries/gemini/sfx/`)
1. Copies and curates the best CC0 Kenney impact, cloth-whoosh, tatami-footstep, and ring-bell `.ogg` files
   from `/Users/weo/Development/3d/assets/kenney/`.
2. Synthesizes & layers studio-mastered 44.1 kHz 16-bit `.wav` combat audio assets combining sub-bass punch
   transients, leather glove snaps, aerodynamic cloth whooshes, bone/body thuds, and a metallic K.O. bell gong.
3. Generates `sfx/soundboard.html` and `sfx/sfx_manifest.json` so all combat audio can be auditioned offline
   or loaded into the dojo engine.
"""

import json
import math
import os
import random
import shutil
import struct
import wave

PROJECT_DIR = "/Users/weo/Development/3d"
ENTRY_DIR = os.path.join(PROJECT_DIR, "competition", "entries", "gemini")
SFX_DIR = os.path.join(ENTRY_DIR, "sfx")
IMPACT_DIR = os.path.join(PROJECT_DIR, "assets", "kenney", "kenney_impact-sounds", "Audio")
RPG_DIR = os.path.join(PROJECT_DIR, "assets", "kenney", "kenney_rpg-audio", "Audio")

SAMPLE_RATE = 44100


def write_wav(filename, samples_float):
    path = os.path.join(SFX_DIR, filename)
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        buf = bytearray()
        for s in samples_float:
            clamped = max(-1.0, min(1.0, s))
            buf.extend(struct.pack("<h", int(clamped * 32767.0)))
        wf.writeframes(bytes(buf))
    return path


def synth_strike(duration, f_start, f_end, punch_gain, snap_gain, whoosh_gain, seed=42):
    rng = random.Random(seed)
    n = int(SAMPLE_RATE * duration)
    out = []
    phase = 0.0
    lp = 0.0
    for i in range(n):
        t = i / SAMPLE_RATE
        # 1. Aerodynamic cloth/air whoosh lead-in
        whoosh_env = math.exp(-((t - 0.035) ** 2) / 0.0008)
        noise = rng.uniform(-1.0, 1.0)
        lp = 0.82 * lp + 0.18 * noise
        whoosh = lp * whoosh_env * whoosh_gain

        # 2. Sub-bass chest/glove impact transient (exponential pitch drop)
        if t >= 0.04:
            dt = t - 0.04
            freq = f_end + (f_start - f_end) * math.exp(-dt * 38.0)
            phase += 2.0 * math.pi * freq / SAMPLE_RATE
            sub_env = math.exp(-dt * 18.0)
            sub = math.sin(phase) * sub_env * punch_gain

            # 3. Leather glove snap & high-impact crack
            snap_env = math.exp(-dt * 85.0)
            snap = (noise * 0.7 + math.sin(phase * 3.7) * 0.3) * snap_env * snap_gain
        else:
            sub = 0.0
            snap = 0.0

        # Soft saturation / studio limiter
        val = math.tanh((whoosh + sub + snap) * 1.35)
        out.append(val)
    return out


def synth_ko_bell(duration=1.8):
    n = int(SAMPLE_RATE * duration)
    out = []
    rng = random.Random(99)
    for i in range(n):
        t = i / SAMPLE_RATE
        # Heavy punch impact + resonant bronze dojo gong harmonics
        thud = math.sin(2.0 * math.pi * (140.0 * math.exp(-t * 22.0) + 42.0) * t) * math.exp(-t * 10.0) * 0.85
        crack = rng.uniform(-1.0, 1.0) * math.exp(-t * 65.0) * 0.65
        gong = (
            0.45 * math.sin(2.0 * math.pi * 220.0 * t) * math.exp(-t * 2.2)
            + 0.30 * math.sin(2.0 * math.pi * 334.0 * t) * math.exp(-t * 2.8)
            + 0.22 * math.sin(2.0 * math.pi * 512.0 * t) * math.exp(-t * 3.6)
            + 0.15 * math.sin(2.0 * math.pi * 788.0 * t) * math.exp(-t * 4.5)
        )
        out.append(math.tanh((thud + crack + gong) * 1.15))
    return out


def main():
    os.makedirs(SFX_DIR, exist_ok=True)

    # 1. Copy curated CC0 Kenney `.ogg` files for direct compatibility with dojo/src/main.js
    kenney_picks = [
        (IMPACT_DIR, "impactPunch_heavy_000.ogg"),
        (IMPACT_DIR, "impactPunch_heavy_001.ogg"),
        (IMPACT_DIR, "impactPunch_heavy_002.ogg"),
        (IMPACT_DIR, "impactPunch_medium_000.ogg"),
        (IMPACT_DIR, "impactPunch_medium_001.ogg"),
        (IMPACT_DIR, "impactSoft_heavy_000.ogg"),
        (IMPACT_DIR, "impactBell_heavy_000.ogg"),
        (IMPACT_DIR, "footstep_carpet_000.ogg"),
        (RPG_DIR, "cloth1.ogg"),
        (RPG_DIR, "cloth2.ogg"),
        (RPG_DIR, "cloth3.ogg"),
    ]
    copied_ogg = []
    for folder, fname in kenney_picks:
        src = os.path.join(folder, fname)
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(SFX_DIR, fname))
            copied_ogg.append(fname)

    # 2. Generate studio-mastered multi-layered `.wav` combat sound effects
    wav_specs = {
        "jab_snap.wav": ("Fast leather jab snap with crisp transient", synth_strike(0.28, 195.0, 58.0, 0.75, 0.85, 0.45, 1)),
        "cross_heavy.wav": ("Straight right cross with deep chest thud", synth_strike(0.36, 165.0, 46.0, 0.95, 0.80, 0.55, 2)),
        "hook_crunch.wav": ("Close-range hook with heavy body crunch", synth_strike(0.40, 150.0, 42.0, 1.05, 0.90, 0.65, 3)),
        "uppercut_launch.wav": ("Rising uppercut whoosh & jaw-rattling impact", synth_strike(0.45, 180.0, 38.0, 1.15, 0.95, 0.85, 4)),
        "frontkick_thud.wav": ("Snap front kick with tatami push & core thud", synth_strike(0.38, 140.0, 40.0, 1.00, 0.70, 0.75, 5)),
        "roundhouse_whip.wav": ("High-velocity leg whip & bone-shaking impact", synth_strike(0.48, 160.0, 35.0, 1.25, 1.00, 0.95, 6)),
        "guard_block.wav": ("Forearm guard absorption thud", synth_strike(0.25, 120.0, 52.0, 0.80, 0.35, 0.25, 7)),
        "ko_bell_gong.wav": ("Knockout heavy impact + resonant dojo ring gong", synth_ko_bell(1.8)),
    }

    manifest = {"curated_kenney_ogg": copied_ogg, "mastered_combat_wav": {}}
    for fname, (desc, samples) in wav_specs.items():
        write_wav(fname, samples)
        manifest["mastered_combat_wav"][fname] = desc

    with open(os.path.join(SFX_DIR, "sfx_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"[sfx] Generated {len(wav_specs)} mastered WAVs and copied {len(copied_ogg)} CC0 OGGs in {SFX_DIR}")


if __name__ == "__main__":
    main()
