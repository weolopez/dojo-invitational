# GROK – build notes (Category A)

Fictional muscular male fighter representing Grok. Not modelled on any real person or photo. The wardrobe is plain charcoal and off-white with no logos.

## Pipeline (reproducible: `source/`)
1. `source/01_build_human.py`: MPFB2 2.0.18 in headless Blender creates the human from macros (v2: gender 1.0, age 0.55, muscle 1.0, weight 0.62, proportions 0.95, height 0.55, mixed ethnicity sliders). It adds the MakeHuman CC0 skin "young african male", the mixamo rig (52 bones), high-poly eyes, eyebrow001, eyelashes01, teeth and tongue (short02 hair is added by MPFB but deleted in assemble in v2).
2. `source/02_retarget.py`: our own world-space rotation retarget of the 28 supplied `assets/mixamo/*.fbx` clips onto the MPFB rig. It compensates for the A-pose to T-pose rest difference per bone, scales hip translation by the hip-height ratio, and keeps the original frame ranges.
3. `source/03_textures.py` generates these textures:
   - Original procedural tileable 1024 px skin micro-normal and roughness maps (pores, fine bumps, faint micro-wrinkles), built from FFT-blurred noise.
   - Recoloured Poly Haven fabric albedos.
   - Tinted brow and lash albedos, and a brown-shifted iris.
   - v2: three 1024 px RGBA hair-shell textures (about 26k short random strands each, thresholds 0 / 0.35 / 0.65).
4. `source/03_assemble.py` does the following:
   - Bakes the macro shape keys and applies one level of Catmull-Clark subdivision to every mesh except the teeth and tongue.
   - Builds the rash guard, shorts and hand wraps from body faces selected by bone weights and height. They are offset along the normal and solidified, so they inherit the body skin weights. Fully covered body faces are deleted. v2: shorts end 0.17 m above the knee and sit 17 mm off the skin (looser); folds are a MARBLE-noise Displace modifier (9 mm shorts, 2.5 mm rash guard); hem boundary loops are smoothed; sliver faces with edges over 4 cm are removed.
   - v2 hair: computes scalp and beard masks from the eye and mouth positions, paints a hairline shadow and stubble dots into the skin albedo (`tmp/tex/skin_diff.png`), and builds 6 hair shells from the scalp faces (offset 1.2 mm + 1.1 mm per layer, slight comb), which inherit the body skin weights.
   - Sets up the PBR materials, adds a transmissive cornea shell and exports `fighter.glb`.
5. `tools/render/` holds the renderer: three.js 0.160.0 (r160) with headless Chrome via puppeteer-core. It uses the CC0 `basement_boxing_ring_2k.hdr` as environment and blurred background, ACES Filmic tone mapping, one directional key light with soft shadows and a shadow-catcher floor. The pose is `fighting_idle` at t = 0.4 s. All four PNGs in `renders/` are straight canvas captures from `fighter.glb`, with no paint-over. Run it with `node tools/render/render.mjs`.

## Materials
- **Skin:** MakeHuman albedo (2048 px), plus a tiled procedural micro-normal (×14, strength 0.45) and roughness map (0.3–0.7). There is a small KHR_materials_sheen layer. **There is no subsurface scattering or transmission on skin.**
- **Eyes:**
  - The eyeball uses a brown-tinted MakeHuman eye texture with alphaMode MASK (needed so the transmissive cornea shows it).
  - The cornea is a 1.6 % larger shell with transmission 1.0, IOR 1.376 and roughness 0.03.
- **Hair:** 6 shell layers, alphaMode MASK (alpha test, depth write on, so no sorting), double-sided, roughness 0.42, sheen 0.3, texture tiled ×70. Brows are also MASK; lashes are still alpha BLEND.
- **Stubble:** albedo darkening only (no geometry).
- **Clothing:**
  - Charcoal rash guard and shorts: Poly Haven Bi-Stretch diffuse, normal and roughness, tiled ×9 through KHR_texture_transform, with sheen 0.4.
  - Off-white wraps: Poly Haven Cotton Jersey, tiled ×16.

## Fight brain (`brain.js`)
The deterministic brain blocks if the opponent attacks within 1.85 m, advances if the attack is farther away, and closes to 1.6 m. It throws uppercuts within 1.05 m, where their shorter recovery gives better damage per second, and roundhouse kicks at longer in-range distances. It has no memory or randomness.

**Local combat check:** `sim/sim.mjs` recorded 400/400 round wins against its simple random-aggressive baseline, with Grok starting on either side. This is an approximate local simulation, not the official arena; its baseline self-play favors player 1, so the result is not evidence of tournament performance.

## Known limitations (honest)
- This is a parametric MakeHuman digital human, not a scan. Up close the face reads as a good CG human, not a photograph.
- Hair is a short buzz cut made of shells; it has no volume beyond about 7 mm and its silhouette edge is smooth. There are no longer hair styles.
- Stubble is painted into the albedo; it has no geometric depth, and the dots can read slightly coarse up close.
- Clothing folds come from procedural displacement, not cloth simulation. They do not respond to pose, and there are no seams or a waistband.
- Skin has no SSS: three.js r160 does not load KHR_materials_diffuse_transmission, and volume needs transmission. No AO/cavity map was baked in v2.
- Deformation was spot-checked visually in single frames of roundhouse_kick (t=0.9 s), uppercut (0.65 s), knocked_out (2.6 s) and crouch (1.2 s); no breakage was seen at render scale. Clips were not reviewed frame by frame.
- Lashes are alpha BLEND and can show sorting artefacts at some angles.
- Performance at 50 fps in the shared arena has not been measured.

## Bonus: voice pack (unscored)
`voice/` contains 10 short PG-13 lines generated with macOS `say -v Daniel`, about 456 KB total in AAC .m4a. `voice/lines.json` maps the events taunt, round_start, got_hit, ko_foe and victory to the files. **The arena does not play these files**; they are an unscored extra and no required file depends on them.

## Validator output (`node validate_entry.mjs grok`, v2)

```
PASS  manifest.json has all fields
PASS  file size 50.4 MB (limit 80 MB)
PASS  extensions: KHR_materials_transmission, KHR_materials_ior, KHR_materials_sheen, KHR_texture_transform
PASS  self-contained (no external URIs)
PASS  17 textures (limit 40)
PASS  largest texture 2050 px (limit 4096)
PASS  205,004 triangles (limit 250,000)
PASS  Mixamo skeleton (all required mixamorig: bones present)
PASS  animations: 28/28
PASS  clip lengths within ±10 % of reference
PASS  bind-pose mesh height ≈ 1.79 m (expected 1.55–2.05 m; check scale if far off)
PASS  brain.js runs in the sandbox, valid outputs, 0.043 ms average (limit 2 ms)
PASS  renders/front.png 1920×1080 (long side ≥ 1920)
PASS  renders/three_quarter.png 1920×1080 (long side ≥ 1920)
PASS  renders/profile.png 1920×1080 (long side ≥ 1920)
PASS  renders/closeup.png 1920×1080 (long side ≥ 1920)
PASS  NOTES.md present and filled in
PASS  LICENSES.md present and filled in

All checks passed.
```
