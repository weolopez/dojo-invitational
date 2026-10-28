# Build Notes — Gemini (`competition/entries/gemini/`)

## 1. Hyper-Realism Architecture & Material Upgrades (Call #8)
Our entry (`competition/entries/gemini/`) builds a tournament-ready human MMA & shoot-wrestling fighter (`fighter.glb`, 60.2 MB, 52,922 triangles, 30/30 animations), a frame-data-driven fight AI (`brain.js` v3.7), and a custom-mastered combat sound effects pack (`sfx/`) from `/Users/weo/Development/3d/assets/mixamo/roster/gemini.fbx`, the Mixamo skeletal clips in `/Users/weo/Development/3d/assets/mixamo/*.fbx`, and the Kenney CC0 audio packs in `/Users/weo/Development/3d/assets/kenney/`.

### Six Major Upgrades in `source/upgrade_and_render.py`
1. **5-Primitive Mesh Split & Dedicated Physically Based glTF 2.0 Materials (Zero Emissive Maps):**
   - `Mesh 0` is split by connected topological components into 5 primitives assigned to 5 separate glTF 2.0 materials so skin, eyeballs, hair, upper gear, and lower gear never share conflicting PBR factors:
     - `Ch48_skin` (material `1`, assigned to head/neck skin `Comp 0`, bare fingers on `Comp 2, 3`, and teeth `Comp 8`): `KHR_materials_ior` (`ior: 1.40`), `roughnessFactor: 1.0`, `normalTexture.scale: 1.25`, `KHR_materials_specular` (`specularFactor: 0.38`, `specularColorFactor: [1.0, 0.88, 0.80]`), `KHR_materials_sheen` (`sheenColorFactor: [0.62, 0.25, 0.16]`, `sheenRoughnessFactor: 0.58`), and `KHR_materials_clearcoat` (`clearcoatFactor: 0.12`, `clearcoatRoughnessFactor: 0.28`).
     - `Ch48_eyes` (material `3`, assigned to eyeballs `Comp 6, 7` and caruncles `Comp 9, 10`): `KHR_materials_ior` (`ior: 1.38`), `roughnessFactor: 0.031`, `KHR_materials_clearcoat` (`clearcoatFactor: 1.0`, `clearcoatRoughnessFactor: 0.01`), and `KHR_materials_specular` (`specularFactor: 1.0`).
     - `Ch48_upper_gear` (material `4`, assigned to torso rashguard `Comp 1`, full-length sleeves `Comp 4, 5`, and wrist wraps/MMA gloves on `Comp 2, 3`) and `Ch48_lower_gear` (material `0`, assigned to crew-neck collar `Comp 5`, shoulder/chest yoke `Comp 4, 6, 7, 8, 16, 17`, grappling spats `Comp 2, 3, 12, 13, 0, 1`, and wrestling shoes `Comp 9, 10, 14, 15`): `normalTexture.scale: 0.65`, `roughnessFactor: 1.0`, `KHR_materials_specular` (`specularFactor: 0.45`), and `KHR_materials_sheen` (`sheenColorFactor: [0.18, 0.22, 0.30]`, `sheenRoughnessFactor: 0.55`).
     - `Ch48_hair` (material `2`, assigned to `Prim 2` hair and tapered eyelash cards): `alphaMode: "BLEND"`, `roughnessFactor: 0.68`, `KHR_materials_specular` (`specularFactor: 0.35`), and `KHR_materials_sheen` (`sheenColorFactor: [0.24, 0.18, 0.14]`, `sheenRoughnessFactor: 0.38`).
2. **4096×4096 Dermatological Voronoi Pores & 2048×2048 Calibrated Roughness/Specular Maps (`.work/process_textures.c`):**
   - Extracts the raw 4096×4096 PNG maps from `assets/mixamo/roster/gemini.fbx` and synthesizes a full 4096×4096 `Ch48_1001_Diffuse` and 4096×4096 `Ch48_1001_Normal` map plus 2048×2048 `Ch48_1001_Glossiness` (glTF `metallicRoughness`), `Ch48_1001_Specular`, `Ch48_1002_Diffuse`, `Ch48_1002_Normal`, `Ch48_1002_Glossiness`, and `Ch48_1002_Specular` maps.
   - Synthesizes multi-scale cellular Voronoi sebaceous pores across the facial and neck skin (`frequencies 1150` and `1950`, `±18` normal delta in `Ch48_1001_Normal`, pore-cavity roughness modulation `128..190` in `Ch48_1001_Glossiness`, and micro-shadowing in `Ch48_1001_Diffuse`), plus anatomical facial vascular warmth across the cheeks, nose bridge, and lips.
3. **Anatomical Neck Broadening & Seamless Crew-Neck Collar Integration:**
   - Removes the 6 floating sci-fi spacesuit armor pods (`Comp 11, 18, 19, 20, 21, 22` in `Prim 0`) and 3 duplicate opaque eyelash cards (`Comp 23, 24, 25`).
   - Broadens the cylindrical neck (`+26%` lateral X width, `+16%` Z depth) via a $C^\infty$ smooth 3D spatial weight strictly below the jawline (`y <= y_top(z)`), leaving the jaw, chin, and face geometry 100% undistorted.
   - Welds the crew-neck collar (`Comp 5`, `d=0..12`) from the neck base (`Comp 0`, `dn=1`) to the shared `d=13` torso boundary (`Comp 7, 8`) via Gaussian angular interpolation and harmonizes `Spine2`/`Neck`/`Head` (`[13, 38, 39]`) skinning weights across the collar seam.
4. **Cohesive Ripstop/Interlock MMA Rashguard, Grappling Spats, Wrist Wraps, Gloves & Wrestling Shoes:**
   - Runs 95 passes of Laplacian smoothing on the upper torso/shoulder yoke plus 14 cycles of volume-preserving Taubin (`λ=0.48, μ=-0.50`) smoothing across the unified `Prim 0 + Prim 1` body manifold, and tapers the lower-leg boot flares to follow the calf and ankle silhouette.
   - Maps connected components cleanly to athletic MMA gear:
     - **Upper body (`Comp 1, 4, 5` in `Prim 1` and `Comp 4, 6, 7, 8, 16, 17` in `Prim 0`):** Long-sleeve slate-navy ripstop/interlock compression rashguard with anti-aliased woven ripstop grid in diffuse and roughness, and ribbed dark slate-charcoal crew-neck collar binding (`Comp 5`, `d=0..3`).
     - **Hands (`Comp 2, 3` in `Prim 1`):** Crimson-burgundy herringbone cotton wrist wraps (`|X| < 0.632`), open-finger pebbled black leather MMA gloves (`0.632 <= |X| < 0.716`), and bare human fingers (`|X| >= 0.716`).
     - **Lower body (`Comp 2, 3, 12, 13, 0, 1` in `Prim 0`):** Charcoal-obsidian ripstop grappling spats/tights from hip to ankle.
     - **Footwear (`Comp 9, 10, 14, 15` in `Prim 0`):** Low-top pebbled black leather wrestling shoes (`Comp 9, 10`) with matte dark charcoal rubber outsoles (`Comp 14, 15`).
5. **Straight-Ahead Hazel-Chestnut Human Eyes & Tapered Feathery Eyelashes:**
   - Reconstructs the eyeball UV islands (`Comp 6, 7` in `Prim 1`) with centered pupils (`(0.9462, 0.3130)` and `(0.8686, 0.3130)`), radial hazel-chestnut iris stroma fibras, dark limbal rings, vascularized sclera with upper-eyelid ambient occlusion, and 3.2° outward eyeball rotation so the corneal apex points straight forward (`+Z`).
   - Narrows the upper/lower eyelid opening by 22% to eliminate scleral show and tapers the alpha-blended eyelash cards (`Prim 2`, `Ch48_1003_Diffuse`) at both canthi.
6. **Analytical Two-Bone Leg IK & Flat-Foot Grounding (`30/30` Animations):**
   - Normalizes the 65-bone `mixamorig:` skeleton to meter scale (`1.73 m` bind-pose height) with all 30 combat animations (including `throw` and `thrown`).
   - Applies analytical two-bone leg IK and flat-foot orientation across `fighting_idle` (`frames 1..99`, preserving frame 0 at Mixamo reference stance) and stance clips (`block`, `block_high`, `crouch`) so both feet rest flat on the floor (`Foot Y=0.0918 m, ToeBase Y=0.0040 m, Toe_End Y=0.0032 m`).

## 2. Custom Combat Sound Effects Suite (`sfx/` & `source/build_sound_effects.py`)
Inside `competition/entries/gemini/sfx/`, we include a two-part audio suite documented in `sfx/sfx_manifest.json`:
- **8 Studio-Mastered Multi-Layer `.wav` Combat Effects (44.1 kHz, 16-bit):** Synthesized and layered by `source/build_sound_effects.py` (`jab_snap.wav`, `cross_heavy.wav`, `hook_crunch.wav`, `uppercut_launch.wav`, `frontkick_thud.wav`, `roundhouse_whip.wav`, `guard_block.wav`, and `ko_bell_gong.wav`).
- **11 Curated CC0 Kenney `.ogg` Clips:** Direct drop-in `.ogg` combat clips (`impactPunch_heavy_000..002.ogg`, `impactPunch_medium_000..001.ogg`, `impactSoft_heavy_000.ogg`, `impactBell_heavy_000.ogg`, `footstep_carpet_000.ogg`, `cloth1..3.ogg`).

## 3. Fight AI Architecture (`brain.js` v3.7)
`brain.js` runs in **~0.040 ms** per call and utilizes all 19 arena moves (`jab`, `cross`, `hook`, `uppercut`, `overhand`, `backfist`, `elbow`, `knee`, `LowKick`, `frontkick`, `sidekick`, `roundhouse`, `spinkick`, `sweep`, `onetwo`, `combo`, `throw`, `takedown`, plus `dodge`, `slip`, `dash`, `backdash`, `block`, `block_high`, `crouch`, `taunt`):
- **Unblockable Grapple Mixup (`< 1.18 m`):** Punishes turtling/blocking opponents with unblockable `throw` (20 dmg) and `takedown` (18 dmg).
- **Evasive Counter-Fighting:** Uses `slip` (invulnerable `0.04..0.28s` against linear strikes) and `dodge` (invulnerable `0.05..0.32s` against hooks/kicks) followed by guaranteed recovery-frame punishes (`combo`, `onetwo`, `uppercut`).
- **Outside Kick Spacing (`1.31 m – 1.72 m`):** Controls mid-range with `lowkick`, `frontkick`, `roundhouse`, `sidekick`, and `spinkick`.

## 4. Honest Limitations
- **Base Character Origin:** The underlying mesh topology and UV layout originate from the shared Adobe Mixamo character asset (`assets/mixamo/roster/gemini.fbx`) rather than a custom bespoke sculpt or photogrammetry scan, so the polygon wireframe topology on the chest and legs retains the original Mixamo edge flow even after Laplacian/Taubin surface smoothing.
- **Skeletal Skinning Only:** Hair cards and garment geometry are skinned to the standard 65-bone `mixamorig:` skeleton without secondary cloth or hair physics bones.

## 5. Validator Output (`validate_entry.mjs gemini`)
```text
PASS  manifest.json has all fields
PASS  file size 60.2 MB (limit 80 MB)
PASS  extensions: KHR_materials_clearcoat, KHR_materials_ior, KHR_materials_sheen, KHR_materials_specular
PASS  self-contained (no external URIs)
PASS  13 textures (limit 40)
PASS  largest texture 4096 px (limit 4096)
PASS  52,922 triangles (limit 250,000)
PASS  Mixamo skeleton (all required mixamorig: bones present)
PASS  animations: 30/30
PASS  clip lengths within ±10 % of reference
PASS  bind-pose mesh height ≈ 1.73 m (expected 1.55–2.05 m; check scale if far off)
PASS  brain.js runs in the sandbox, valid outputs, 0.040 ms average (limit 2 ms)
PASS  renders/front.png 1920×1080 (long side ≥ 1920)
PASS  renders/three_quarter.png 1920×1080 (long side ≥ 1920)
PASS  renders/profile.png 1920×1080 (long side ≥ 1920)
PASS  renders/closeup.png 1920×1080 (long side ≥ 1920)
PASS  NOTES.md present and filled in
PASS  LICENSES.md present and filled in

All checks passed.
```
