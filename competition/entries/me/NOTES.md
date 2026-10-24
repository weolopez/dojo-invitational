# THE OWNER: notes

This is the owner's fighter: a FaceBuilder head fitted from the owner's own photos, on a MakeHuman body rebuilt from
scratch. At the owner's request, the body copies Grok's body model: it is generated from the same MPFB2 macros that
Grok publishes in `entries/grok/NOTES.md` and `entries/grok/source/01_build_human.py`. No file was copied from Grok's
folder; MPFB2, the MakeHuman assets and the Poly Haven fabrics were downloaded from their official sources into
`.work/`, and the scripts in `source/` were written for this entry.

**Who did what:** the owner chose the approach (copy Grok's body, keep their own head, match the body skin to their
face). The owner's coding agent (Claude Code, Opus 5.5) wrote and ran the scripts. No hand sculpting or painting.

## Pipeline (`node tools/build.mjs`, then `node tools/render.mjs`)

1. `source/01_build_body.py`: MPFB2 2.0.18 in headless Blender creates the body with gender 1.0, age 0.55, muscle 1.0,
   weight 0.62, proportions 0.95, height 0.55 (and Grok's race mix), the CC0 skin "middleage caucasian male" and the
   mixamo rig. No eyes, brows, lashes, teeth or hair are added: the head is replaced in stage 3.
2. `source/02_retarget.py`: retargets the 28 shared clips onto the MPFB rig with a per-bone world-space rotation
   correction for the A-pose/T-pose difference, with hip translation scaled by hip height and frame ranges kept.
3. `source/03_assemble.py` does the following:
   - Bakes the macro shape keys and applies one subdivision level.
   - Deletes the MPFB head and scales and places the FaceBuilder head on the MPFB skull (cranium length and top).
   - Trims the FaceBuilder neck at the neck bone and conforms its lowest 3 cm radially onto the body neck.
   - Copies head skin weights from the nearest vertex of the original MPFB head and neck.
   - Tints the body albedo per channel to the owner's median cheek colour. It fades the lower FaceBuilder neck
     texture, where the owner's shirt collar was baked in, to the tinted body-neck colour.
   - Builds the rash guard, shorts and hand wraps from body faces and deletes the skin they fully cover.
   - Adds procedural skin micro-normal and roughness maps and exports `fighter.glb`.
4. `tools/render.mjs` renders the four views with `.work/render.html`: three.js r160 in headless Chrome, the Poly
   Haven boxing-ring HDRI and one shadowed key light, with the pose `fighting_idle` at t = 0.4 s. The renders are
   direct canvas captures with no paint-over. Per RULES.md §12 they stay on the owner's Mac, and the face textures
   stay in `.work/`.

## Limitations

- The body is a parametric MakeHuman body, not a scan of the owner's body, and its proportions are Grok's, not the
  owner's.
- The face texture comes from three low-resolution (512×288) photos. It is soft, the eyes look downcast, the hair is
  painted into the texture with some dark smears on the crown, and the AirPod is still baked into the right ear.
- The neck join is a 1.5 cm overlap of two meshes, not a welded seam. The faded band is a flat skin tone with fine
  noise, and a faint edge can show up close.
- Skin match is a single per-channel gain from the cheeks. The body albedo is a different person's skin, so its pore
  and tone variation do not match the face exactly. Neither material has subsurface scattering.
- The clothing has no cloth simulation or seams. The folds and waistband gathers are fixed procedural displacement
  (v3.4), the shorts are still loose and boxy, and a few soft lumps remain on the shirt back and side.
- The feet: in `fighting_idle` the retargeted feet point down onto the toes. This was not fixed, and Grok's renders
  show the same thing. Clips were not reviewed frame by frame.

## Update log

- **Brain: fast counter-grappler (written by Claude, the judge's session, at the owner's explicit request; the owner
  waived the "judge doesn't build entry me" rule for this change).** Blocks quick punches; against a slow kick or
  punch it slips inside just before the blow, or guards it, then throws or takes down the foe as they recover. A
  foe covering up behind a block gets grabbed. Between exchanges: quick jabs and one-twos. Keeps the round-timer
  reset from the owner's agent. Uses the v3.5 moves (`slip`, `takedown`, `onetwo`). The model is unchanged.

- **Owner entry created:** the FaceBuilder head on the Mixamo X Bot body.
- **Body/material update (call 3):** proportion edits, procedural skin and fabric, and skinned shells on X Bot.
- **Body rebuild:** the X Bot body was deleted. The new body is an MPFB2 MakeHuman body built from Grok's recipe,
  with the skin tinted to the owner's face, a conformed and repainted neck join, and a Poly Haven fabric rash guard,
  shorts and hand wraps. The previous build is kept in `.work/backup_xbot_v3/`.

## Validator output (Oct 24, 2026, call 4 / v3.4)

```
PASS  manifest.json has all fields
PASS  file size 46.6 MB (limit 80 MB)
PASS  extensions: KHR_texture_transform, KHR_materials_sheen
PASS  self-contained (no external URIs)
PASS  10 textures (limit 40)
PASS  largest texture 2050 px (limit 4096)
PASS  213,571 triangles (limit 250,000)
PASS  Mixamo skeleton (all required mixamorig: bones present)
PASS  animations: 30/30
PASS  clip lengths within ±10 % of reference
PASS  bind-pose mesh height ≈ 1.79 m (expected 1.55–2.05 m; check scale if far off)
PASS  brain.js runs in the sandbox, valid outputs, 0.130 ms average (limit 2 ms)
PASS  renders/front.png 1920×1080 (long side ≥ 1920)
PASS  renders/three_quarter.png 1920×1080 (long side ≥ 1920)
PASS  renders/profile.png 1920×1080 (long side ≥ 1920)
PASS  renders/closeup.png 1920×1080 (long side ≥ 1920)
PASS  NOTES.md present and filled in
PASS  LICENSES.md present and filled in

All checks passed.
```

## Update (Oct 24, 2026): body, animation and realism pass
- **Feet and grounding:** `source/fix_feet.py` (using `source/src_metrics.py`) rewrites the Foot rotation and Hips translation tracks in all 28 clips. Foot pitch now follows the Mixamo source relative to rest. Before the fix, every clip had a constant offset of about 23°. Hip height follows the source's foot clearance, a mean change of 0.1–4.3 cm per clip. Clip lengths are unchanged.
- **Clothing:** `source/cloth.py` was run in Blender 4.2.3 on the box. It smooths and inflates the garments by 3 mm, smooths the hem loops, adds a ribbed hem-trim material and a darker shorts material, and changes the fabric texture scale from 9 to 30. I tried a collar extrusion, but it produced artifacts, so it is disabled.
- **Not done:** skin pores, closing the waist/hip gap, hiding the ball joints. The face was left alone as requested.
- **Renders:** `renders/` now holds the judge-harness output in the bind pose.
- **Throw clips (30 total):** `throw` and `thrown` (201 frames at 30 fps) were retargeted with `source/addclips.py`. It uses the same per-bone retarget math as `02_retarget.py`, but runs on the rig imported from fighter.glb because the original .blend was not available. Both clips then got the same foot and hip fix: `fix_feet.py ... throw,thrown`. That fix corrected about 23° of foot pitch, and a second pass left less than 0.2° residual. The other 28 clips were not changed. The bind-pose mesh did not change either, so the renders were not regenerated.
- **Timing fix:** the Blender re-export in `cloth.py` played the 28 original clips at 24 fps, which made them 0.8× their original length. `source/retime.py` multiplies their keyframe times by 1.25. It writes new time accessors with updated min/max and leaves throw/thrown alone. All 30 durations now match the reference list (for example fighting_idle 3.33 s, knocked_out 4.97 s, throw 6.70 s). After retiming, re-running the foot check gives a residual below 0.001° on every clip except thrown Right (0.16°), and a hip residual below 0.0001 cm. The roughly 10° fighting_idle residual came from the same timing error.

## Update (Oct 24, 2026, call 4 / rules v3.3)
- **Clothing rebuild:** `source/04_garments_v34.py` (Blender 4.2.3) rebuilds the rash guard and shorts from the old
  garments. It keeps the outward surface and voxel-remeshes it (1 cm). Laplacian smoothing then removes the wavy
  marble-stripe displacement, followed by a re-inflate and one subdivision level.
  - **Hems:** the neck, sleeve, shirt and leg hem loops are smoothed into clean edge loops at their original extents.
    Each gets a 2-ring ribbed trim material and a 3.5 mm turned-under edge.
  - **Gaps and folds:** the armpit holes are filled. Procedural sine creases are added (shorts legs, sleeve
    underarms, shirt flanks), along with elastic gathers on the shorts waistband.
  - **Waist:** the shirt hem is extended down to z = 0.975 m under the shorts waistband, which closes the waist gap.
  - **Skinning:** weights are transferred from the old garments (nearest-face interpolation, 4 influences).
  - **Triangles:** the count goes from 133k to 214k.
- **Extra clips:** `knockdown_front` (85 frames), `getup_back` (251 frames) and `getup_front` (259 frames) from
  `assets/mixamo/extra` were retargeted with `source/05_add_extra_clips.py` at 30 fps. They then got the same foot and
  hip fix (`fix_feet.py`), and their lengths are 2.83, 8.37 and 8.63 s. The Blender round-trip again shortened the
  older 30 clips to 0.8×, so `source/06_retime.py` restored them; every duration now matches the previous fighter.glb.
  Clips were not reviewed frame by frame.
- **Face:** unchanged. The eyes are still downcast, the hair is still painted and the neck seam is unchanged.
- **brain.js:** adds a knockdown play. When the foe is at or below 30% health, it throws an uppercut in close or a
  hook in hook reach (stepping in otherwise), once per round. A `hit` state lasting over 1.2 s is treated as the
  knockdown.
- **FEEDBACK.md:** adds Engine proposals (ragdoll falls, partial ragdoll hit reactions, active-ragdoll get-ups, foot
  IK, spring bones).
- **Renders:** `renders/` holds new judge-harness captures at 1920×1080 (bind pose, plus idle_full and
  action_roundhouse).

## Brain: step in and throw (Oct 24, 2026, call 4)
Written by the owner's AI agent (Me Fighter); not hand-tuned or tested in fights, only run through the validator.
- **Round reset:** all memory timers (last strike, hit-spell, throw plan, plan-check) and per-round flags reset when
  `round` changes or `time` goes backwards, fixing the round-timer trap.
- **Step in and throw:** when the foe is 0.95–1.4 m away and not attacking, about twice a second the brain rolls to
  commit (base 22%, +13% if the foe is blocking or idle, +15% if behind on health after 18 s of a 30 s round). Once
  committed it walks forward and throws inside 0.95 m. The plan is dropped if the foe starts attacking (block if in
  reach), the foe is down, or after 1 s. A non-attacking foe already inside 0.95 m is thrown directly.
- **Finisher:** at or below 30% foe health (once per round), hook in hook reach, roundhouse out to 1.6 m (replaces
  the previous uppercut/hook finisher).
- **Unchanged:** blocking strikes in reach, walking in, occasional front kick, jab-cross-power combos in close.

### Validator output (final)
```
PASS  manifest.json has all fields
PASS  file size 46.6 MB (limit 80 MB)
PASS  extensions: KHR_texture_transform, KHR_materials_sheen
PASS  self-contained (no external URIs)
PASS  10 textures (limit 40)
PASS  largest texture 2050 px (limit 4096)
PASS  213,571 triangles (limit 250,000)
PASS  Mixamo skeleton (all required mixamorig: bones present)
PASS  animations: 30/30
PASS  clip lengths within ±10 % of reference
PASS  bind-pose mesh height ≈ 1.79 m (expected 1.55–2.05 m; check scale if far off)
PASS  brain.js runs in the sandbox, valid outputs, 0.071 ms average (limit 2 ms)
PASS  renders/front.png 1920×1080 (long side ≥ 1920)
PASS  renders/three_quarter.png 1920×1080 (long side ≥ 1920)
PASS  renders/profile.png 1920×1080 (long side ≥ 1920)
PASS  renders/closeup.png 1920×1080 (long side ≥ 1920)
PASS  NOTES.md present and filled in
PASS  LICENSES.md present and filled in

All checks passed.
```

## Call #5 — Brain: v3.5 grappling moves (written by the owner's AI agent, Me Fighter)

- **What call #5 asked:** calls/me.md lists realism points only (neck seam, rippled shirt, boxy shorts, real hair).
  The owner asked for the latest grapple/throw abilities and animations. Rules v3.5 added the brain moves
  `sidekick, onetwo, combo, dodge, slip, takedown, sweep`; it adds **no new required clips** (still 30; takedown and
  sweep play as the throw until the arena has their clips). This fighter already ships all 30 required clips plus the
  optional `knockdown_front`, `getup_back`, `getup_front`, so **fighter.glb, renders and manifest are unchanged**.
- **brain.js rewritten** (backup of the previous file in .work/pre_call5/; note the brain.js found on disk at 12:56
  EDT had been replaced by a counter-grappler version not written in this run and without the finisher or step-in
  plan; it is kept there as brain_found_1256.js):
  - Kept: per-round timer reset, step-in-and-throw plan (foe 0.95–1.4 m and not attacking, decided twice a second,
    ~22% base, +13% vs a blocking/idle foe, +15% if behind after 18 s; abandoned on foe attack or after 1 s), and the
    hook/roundhouse finisher at ≤30% foe health.
  - New: slip inside slow shots (roundhouse, front/side kick, hook, uppercut, combo) about half the time and grab on
    the recovery; takedown (50/50 with throw) between 0.95 and 1.1 m; occasional sweep at 1.1–1.25 m vs a non-blocking
    foe; one-twos and occasional four-punch combos in close.
  - The shoulder throw stays the main grab, because the dojo/src engine on disk (config.js MOVES) does not yet define
    the v3.5 moves and silently ignores unknown ones; in that engine slip/takedown/sweep/onetwo/combo would be no-ops.
- **Not tested:** no fights were run; no win-rate or throw-rate numbers. Realism unchanged (no mesh/texture work).

### Validator output (call #5)
```
PASS  manifest.json has all fields
PASS  file size 46.6 MB (limit 80 MB)
PASS  extensions: KHR_texture_transform, KHR_materials_sheen
PASS  self-contained (no external URIs)
PASS  10 textures (limit 40)
PASS  largest texture 2050 px (limit 4096)
PASS  213,571 triangles (limit 250,000)
PASS  Mixamo skeleton (all required mixamorig: bones present)
PASS  animations: 30/30
PASS  clip lengths within ±10 % of reference
PASS  bind-pose mesh height ≈ 1.79 m (expected 1.55–2.05 m; check scale if far off)
PASS  brain.js runs in the sandbox, valid outputs, 0.101 ms average (limit 2 ms)
PASS  renders/front.png 1920×1080 (long side ≥ 1920)
PASS  renders/three_quarter.png 1920×1080 (long side ≥ 1920)
PASS  renders/profile.png 1920×1080 (long side ≥ 1920)
PASS  renders/closeup.png 1920×1080 (long side ≥ 1920)
PASS  NOTES.md present and filled in
PASS  LICENSES.md present and filled in

All checks passed.
```
