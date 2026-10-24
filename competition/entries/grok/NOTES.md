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
5. `tools/render/` holds the renderer: three.js 0.160.0 (r160) with headless Chrome via puppeteer-core. It uses the CC0 `basement_boxing_ring_2k.hdr` as environment and blurred background, ACES Filmic tone mapping, one directional key light with soft shadows and a shadow-catcher floor. The pose is `fighting_idle` at t = 0.4 s. (v2 renders; v3 replaced them, see below.) All four PNGs in `renders/` are straight canvas captures from `fighter.glb`, with no paint-over. Run it with `node tools/render/render.mjs`.

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
The deterministic brain blocks if the opponent attacks within 1.85 m, advances if the attack is farther away, and closes to 1.6 m. v3: it **throws a blocking opponent when the gap is under 0.95 m** (throws ignore block) and walks in to 1.3 m on a blocker. v3 knockdown play (same as entry `me`): once per round, when the foe is at ≤30 % hp and not blocking, it closes to 1.15 m and uses an uppercut (≤1.05 m) or hook; a hit-state longer than 1.2 s is taken as the knockdown and ends the play for that round (per-round flag in `state.memory`). Otherwise uppercuts within 1.05 m and roundhouse kicks at longer in-range distances. No randomness. The local `sim/` result below was measured on the v2 brain and was not re-run for v3.

**Local combat check:** `sim/sim.mjs` recorded 400/400 round wins against its simple random-aggressive baseline, with Grok starting on either side. This is an approximate local simulation, not the official arena; its baseline self-play favors player 1, so the result is not evidence of tournament performance.

## Known limitations (honest)
- v7: see "v7 changes" below. The collar-shoulder lip line is mostly gone, but a jagged lighter V edge still shows on the sternum where the collar yoke ends on the shirt. The shorts front still has body-following bulges, and the hair and skin are unchanged.
- This is a parametric MakeHuman digital human, not a scan. Up close the face reads as a good CG human, not a photograph.
- Hair is a short buzz cut made of shells; it has no volume beyond about 7 mm and its silhouette edge is smooth. There are no longer hair styles.
- Stubble is painted into the albedo; it has no geometric depth, and the dots can read slightly coarse up close.
- Clothing folds (v3) are still procedural, not cloth simulation, and do not respond to pose. The seams are displaced grooves, not separate panels, and there is no seam/stitch normal map. The original v2 MARBLE displacement is still under the v3 folds, so a few blotchy patches remain on the shorts (most visible from behind).
- Skin has no SSS: three.js r160 does not load KHR_materials_diffuse_transmission, and volume needs transmission. No AO/cavity map was baked in v2.
- Deformation was spot-checked visually in single frames of roundhouse_kick (t=0.9 s), uppercut (0.65 s), knocked_out (2.6 s) and crouch (1.2 s); no breakage was seen at render scale. Clips were not reviewed frame by frame.
- Lashes are alpha BLEND and can show sorting artefacts at some angles.
- Performance at 50 fps in the shared arena has not been measured.

## Bonus: voice pack (unscored)
`voice/` contains 10 short PG-13 lines generated with macOS `say -v Daniel`, about 456 KB total in AAC .m4a. `voice/lines.json` maps the events taunt, round_start, got_hit, ko_foe and victory to the files. **The arena does not play these files**; they are an unscored extra and no required file depends on them.

## v7 changes (call #9) – judge notes
Only two meshes changed: RashGuard (positions and normals) and Shorts (positions and normals). Topology, UVs, joints and weights are unchanged on both. All other meshes and all 17 images are md5-identical to v6, including the body/face, eyes, cornea, teeth, lashes, brows, hair shells and wraps. No animation was re-exported or edited. Materials are unchanged; the knit normal scale is still 0.38. The triangle count is unchanged at 243,870.
- **Collar lip (fixed on the shoulders, partly at the sternum).** `source/fix_collar_v7.py` (run with BAND 3 cm, FLOOR 1.5 mm, blend 0) re-solves the collar yoke's height above the skin as a smooth envelope. Inside 3 cm of the place where the yoke climbs onto the shirt edge, the height is relaxed harmonically for 400 passes. It is floored at shirt height + 1.5 mm wherever the v5 shirt lies underneath, so the yoke ramps over the edge instead of stepping. The largest vertex move is 20.9 mm, and normals are recomputed. In the before/after closeups, the stepped line across both shoulders (front and back) is gone. **Still visible:** where the yoke ends on the chest, it shows a jagged, slightly lighter V edge below the neckline.
- **Sternum patch: not fixed.** I tried blending the yoke normals toward the shirt normals, but it made a larger visible patch, so I discarded it. The lighter V under the neckline remains (see above).
- **Shorts.** `source/fix_shorts_v7.py` (run with 80 iterations, 2 mm). The leg openings are closed by the turned hem, so the hem line is the fold. Per leg and per 3.75° sector, the fold height was measured: it varied by 21.6 mm on the left leg and 17.1 mm on the right. Each sector was shifted to the median fold height (0.7086 m and 0.7080 m), with a 6 cm falloff, so the hem now reads as a level line. The hem ring was then pinned and 80 Taubin passes smoothed the rest. Vertices are kept at least 2 mm off the body (or at their original offset if that was closer); 1,826 vertices were pushed out. The mean move is 0.81 mm and the max is 24.0 mm (at the hem). Small-scale lumps are reduced, but the large bulges on the front and crotch follow the body, so they remain. A 500-pass version made them sharper and was discarded.
- **Hair: skipped.** No safe improvement fitted in this pass; the hair shells are unchanged.
- **Skin SSS: skipped.** Same reason as before (r160); the skin is unchanged.
- **Renders:** `renders/` holds new judge harness output (judge.html, Three.js r160, 1920×1080). Before/after detail closeups (shorts, collar, shoulders) are in the working folder grok_renders/v7/{before,after}. They are not part of the entry.

## Validator output (`node validate_entry.mjs grok`, v7)
```
PASS  manifest.json has all fields
PASS  file size 46.0 MB (limit 80 MB)
PASS  extensions: KHR_materials_transmission, KHR_materials_ior, KHR_materials_sheen, KHR_texture_transform
PASS  self-contained (no external URIs)
PASS  17 textures (limit 40)
PASS  largest texture 2050 px (limit 4096)
PASS  243,870 triangles (limit 250,000)
PASS  Mixamo skeleton (all required mixamorig: bones present)
PASS  animations: 30/30
PASS  clip lengths within ±10 % of reference
PASS  bind-pose mesh height ≈ 1.79 m (expected 1.55–2.05 m; check scale if far off)
PASS  brain.js runs in the sandbox, valid outputs, 0.159 ms average (limit 2 ms)
PASS  renders/front.png 1920×1080 (long side ≥ 1920)
PASS  renders/three_quarter.png 1920×1080 (long side ≥ 1920)
PASS  renders/profile.png 1920×1080 (long side ≥ 1920)
PASS  renders/closeup.png 1920×1080 (long side ≥ 1920)
PASS  NOTES.md present and filled in
PASS  LICENSES.md present and filled in

All checks passed.
```

## v6 changes (v3.7 rules, spring layer)
The v5 glb was spliced with numpy (`source/glbio.py`), and nothing was re-exported from Blender. The face, eyes, eyebrows, lashes, teeth, tongue, all 6 hair shells and all 17 textures are byte-identical to v5 (checked with an md5 per mesh and per image). Only the body mesh, the rash guard mesh, one material value and the fighting_idle leg keys changed.

I ran a stress pass of 21 shots in the v3.7 arena code with the PhysicalLayer springs and a simulated ±40° look-at: idle feet, head snap, uppercut, body fold, kicks, slip and dodge, throw and thrown, knockdown, KO, get-ups, punches and hooks. The renders are in `/workspace/grok_renders/v6/before_stress` (v5) and `after_stress` (v6).

- **Collar and shoulder seam** (`source/fix_collar_v6.py`, args `4 1.0`):
  - The v5 collar was 8,704 loose quad vertices with flat normals and a separate 0..1 UV square per quad. That gave faceting, per-quad knit tiling and gaps.
  - It is now welded to 2,304 vertices with 4 Laplacian passes of skin-weight smoothing (top 4 influences), smooth normals and cylindrical UVs.
  - Shirt triangles under the collar were deleted.
  - The rash guard went from 31,416 to 31,267 tris.
- **Skin poke-through** (`source/cull_hidden_v6.py`, `RING=1 SINK=0`):
  - Body triangles lying fully under the rash guard or shorts were deleted, keeping 1 vertex ring under every garment edge.
  - The body went from 89,232 to 87,607 tris.
  - This removed the orange skin spots that showed at the collar and shoulders when the neck springs or look-at moved the head.
  - I also tried sinking hidden vertices and a dropped collar skirt. Both opened gaps, so neither ships.
- **fighting_idle front foot** (`source/fix_heel_v6.py fighting_idle Left`):
  - I used the same two-bone IK as the v5 rear-foot fix, changing rotation keys only.
  - Before: 20° mean toe-down with the ankle 5.9 cm up. After: 2.8° with the ankle 1.7 cm up.
  - Key times and clip length are unchanged.
- **Material:** the rash guard knit normal scale went from 0.6 to 0.38, to soften the diamond-shaped knit patches seen at grazing angles. There is still no SSS, because three r160 has no diffuse transmission, so it was skipped.
- **Size:** the bin was compacted to drop data that earlier splices left unreferenced (`source/compact_v6.py`). The file went from 62.0 MB to 45.7 MB. Total tris went from 245,644 to 243,870.

**Not fixed or not tested:**
- **Collar lip:** a faint stepped line is still visible where the collar band meets the shirt at the shoulders in the closeup.
- **Sternum patch:** a lighter triangle on the shirt below the collar V comes from the shirt's own UVs and is unchanged.
- **Knit diamonds:** they are weaker but still visible on the chest in the extreme head-snap view.
- **Shorts hem:** not changed in v6.
- **Moving clips:** the other stance clips are not foot-planted, so crouch, step and side_step still briefly go up on the ball.
- **Neck:** no neck weight smoothing beyond the collar band, and no separate neck-tearing fix. The stress shots showed no neck tearing.
- **lent clips:** the new lent.glb moves (takedown, sweep, spinkick, knee, lowkick, dodge) could not be rendered or checked, because lent.glb is not on the build box.

## Validator output (`node validate_entry.mjs grok`, v6)
```
PASS  manifest.json has all fields
PASS  file size 45.7 MB (limit 80 MB)
PASS  extensions: KHR_materials_transmission, KHR_materials_ior, KHR_materials_sheen, KHR_texture_transform
PASS  self-contained (no external URIs)
PASS  17 textures (limit 40)
PASS  largest texture 2050 px (limit 4096)
PASS  243,870 triangles (limit 250,000)
PASS  Mixamo skeleton (all required mixamorig: bones present)
PASS  animations: 30/30
PASS  clip lengths within ±10 % of reference
PASS  bind-pose mesh height ≈ 1.79 m (expected 1.55–2.05 m; check scale if far off)
PASS  brain.js runs in the sandbox, valid outputs, 0.141 ms average (limit 2 ms)
PASS  renders/front.png 1920×1080 (long side ≥ 1920)
PASS  renders/three_quarter.png 1920×1080 (long side ≥ 1920)
PASS  renders/profile.png 1920×1080 (long side ≥ 1920)
PASS  renders/closeup.png 1920×1080 (long side ≥ 1920)
PASS  NOTES.md present and filled in
PASS  LICENSES.md present and filled in

All checks passed.
```
The newer `dojo-physics/competition/validate_entry.mjs` also prints "All checks passed." for this entry (45.7 MB, 243,870 tris, 30/30 clips).

## v5 changes (call #5) – judge notes
Built by splicing new garment meshes and materials into the call #4 GLB (`source/garments_v5.py`, `source/splice_mesh.py`,
`source/materials_v5.py`, `source/weave_tex.py`, `source/fix_heel.py`). Face, eyes, pores, hair and skin textures are byte-identical;
animations were not re-exported (only the fighting_idle right-leg rotation keys were rewritten, same times).
1. **Rash guard**: the Bi-Stretch rib normal map (the source of the ripple bands) is replaced by a fine procedural knit; the
   body is Taubin-smoothed; a new snug crew-neck collar band (128x16 grid, rolled top edge, skin weights from nearest body
   vertex) covers the old flat off-shoulder cut. It is lower at the front and higher at the nape.
2. **Shorts**: the marble blotches were removed (Taubin plus smoothing of the distance-to-body field); the leg hems are
   snapped to planar edge loops with a turned 2 cm hem and a stitch groove. Colour is charcoal via baseColorFactor.
3. **Red line under the jaw**: caused by the reddish skin sheen (0.55,0.36,0.28) at grazing angles; it is now a faint
   neutral sheen (0.09,0.075,0.065).
4. **fighting_idle rear heel**: the rear (right) foot was raised about 5 cm on its ball. Two-bone IK drops the ankle and
   flattens the foot (pitch now about 3 deg toe-down); the average ankle height above rest is 1.7 cm (it was 5.1 cm). Clip lengths are unchanged.
5. **Skin SSS**: skipped. three r160 has no diffuse transmission/SSS, and faking it with transmission breaks the skin.

Remaining limitations: the collar's overlap edge on the shoulders reads as a faint yoke seam; the shorts keep some broad
fold shapes and the hem silhouette is not perfectly even; the front (left) foot in fighting_idle is still on its ball (by design for the stance);
a very faint warm rim can remain under the jaw.

## Validator output (`node validate_entry.mjs grok`, v5)
```
PASS  manifest.json has all fields
PASS  file size 62.0 MB (limit 80 MB)
PASS  extensions: KHR_materials_transmission, KHR_materials_ior, KHR_materials_sheen, KHR_texture_transform
PASS  self-contained (no external URIs)
PASS  17 textures (limit 40)
PASS  largest texture 2050 px (limit 4096)
PASS  245,644 triangles (limit 250,000)
PASS  Mixamo skeleton (all required mixamorig: bones present)
PASS  animations: 30/30
PASS  clip lengths within ±10 % of reference
PASS  bind-pose mesh height ≈ 1.79 m (expected 1.55–2.05 m; check scale if far off)
PASS  brain.js runs in the sandbox, valid outputs, 0.137 ms average (limit 2 ms)
PASS  renders/front.png 1920×1080 (long side ≥ 1920)
PASS  renders/three_quarter.png 1920×1080 (long side ≥ 1920)
PASS  renders/profile.png 1920×1080 (long side ≥ 1920)
PASS  renders/closeup.png 1920×1080 (long side ≥ 1920)
PASS  NOTES.md present and filled in
PASS  LICENSES.md present and filled in

All checks passed.
```

## v3 changes (call #4)
Everything below was spliced into the v2 GLB at the glTF JSON/binary level (`source/glbio.py`, `source/splice.py`, `source/splice_mesh.py`). The face, eyes, cornea transmission, hair shells, skin textures and sheen were not re-exported, so they are byte-identical to v2. The original is backed up as `.work/fighter_orig.glb` (not shipped).
- **New clips (30 required + 3 extra = 33):** `source/addclips.py` retargets `assets/mixamo` throw and thrown, plus the optional knockdown_front, getup_back and getup_front, with the same world-space method as `02_retarget.py`. It keys at 30 fps and exports only the new actions, so the Blender glTF re-import 0.8× timing bug cannot affect the 28 existing clips; their durations were checked to be unchanged. The validator confirms all clip lengths are within ±10 % of reference. Lengths: throw 6.70 s, thrown 6.70 s, knockdown_front 2.83 s, getup_back 8.37 s, getup_front 8.63 s.
- **Feet plant, all 33 clips:** `source/fix_feet.py` with `source/src_metrics.py` (two passes) measures each source Mixamo clip's foot/toe pitch relative to the floor and corrects the retargeted foot and toe bones to match. It removed about 23° of toe-standing per clip, and the hips moved 1.5–1.8 cm. In `fighting_idle` the residual is about 1e-6°. In the judge `idle_full` render the lead foot is flat; the rear foot is on its ball, as in the Mixamo source stance.
- **Training wear folds and seams:** `source/folds_grok.py` imports the GLB in rest pose and displaces the original garment meshes radially from the nearest bone axis. Skin weights are kept, and the new verts get interpolated weights.
  - **Shorts:** one subdivide pass (12,096 → 48,384 tris), Laplacian smoothing with offset restore, then:
    - a 8 mm downward hang toward the hem, with vertical drape creases;
    - crotch drag folds;
    - an elastic waistband with gathers and a stitch groove;
    - side-seam and inseam grooves and a hem stitch line.
  - **Rash guard:** same 27,064 tris. It has:
    - underarm bunching;
    - a set-in sleeve seam ring, plus side and shoulder seam grooves;
    - compression wrinkles above the waist and armpit-to-sternum pull folds.
- **Skin SSS: not added.** three r160 does not support KHR_materials_diffuse_transmission, and volume/transmission on skin would make it see-through, so this was judged too risky for the champion's skin. Skin is unchanged.
- **Totals:** 241,292 tris (v2: 205,004), 54.2 MB (v2: 50.4 MB).
- **Renders:** `renders/` now holds the official judge harness output (`dojo/judge.html?id=grok`): front, three_quarter, profile, closeup, idle_full and action_roundhouse, at 1920×1080.
- `FEEDBACK.md` added with engine proposals.

## Validator output (`node validate_entry.mjs grok`, v3)
```
PASS  manifest.json has all fields
PASS  file size 54.2 MB (limit 80 MB)
PASS  extensions: KHR_materials_transmission, KHR_materials_ior, KHR_materials_sheen, KHR_texture_transform
PASS  self-contained (no external URIs)
PASS  17 textures (limit 40)
PASS  largest texture 2050 px (limit 4096)
PASS  241,292 triangles (limit 250,000)
PASS  Mixamo skeleton (all required mixamorig: bones present)
PASS  animations: 30/30
PASS  clip lengths within ±10 % of reference
PASS  bind-pose mesh height ≈ 1.79 m (expected 1.55–2.05 m; check scale if far off)
PASS  brain.js runs in the sandbox, valid outputs, 0.123 ms average (limit 2 ms)
PASS  renders/front.png 1920×1080 (long side ≥ 1920)
PASS  renders/three_quarter.png 1920×1080 (long side ≥ 1920)
PASS  renders/profile.png 1920×1080 (long side ≥ 1920)
PASS  renders/closeup.png 1920×1080 (long side ≥ 1920)
PASS  NOTES.md present and filled in
PASS  LICENSES.md present and filled in

All checks passed.
```
