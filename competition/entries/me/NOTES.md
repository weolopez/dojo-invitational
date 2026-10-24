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
- The clothing has no cloth simulation, seams or waistband. The folds are fixed displacement, and the shorts are loose
  and boxy.
- The feet: in `fighting_idle` the retargeted feet point down onto the toes. This was not fixed, and Grok's renders
  show the same thing. Clips were not reviewed frame by frame.

## Update log

- **Owner entry created:** the FaceBuilder head on the Mixamo X Bot body.
- **Body/material update (call 3):** proportion edits, procedural skin and fabric, and skinned shells on X Bot.
- **Body rebuild:** the X Bot body was deleted. The new body is an MPFB2 MakeHuman body built from Grok's recipe,
  with the skin tinted to the owner's face, a conformed and repainted neck join, and a Poly Haven fabric rash guard,
  shorts and hand wraps. The previous build is kept in `.work/backup_xbot_v3/`.

## Validator output (Oct 24, 2026, final)

```
PASS  manifest.json has all fields
PASS  file size 43.3 MB (limit 80 MB)
PASS  extensions: KHR_texture_transform, KHR_materials_sheen
PASS  self-contained (no external URIs)
PASS  10 textures (limit 40)
PASS  largest texture 2050 px (limit 4096)
PASS  133,040 triangles (limit 250,000)
PASS  Mixamo skeleton (all required mixamorig: bones present)
PASS  animations: 30/30
PASS  bind-pose mesh height ≈ 1.79 m (expected 1.55–2.05 m; check scale if far off)
PASS  brain.js runs in the sandbox, valid outputs, 0.163 ms average (limit 2 ms)
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
