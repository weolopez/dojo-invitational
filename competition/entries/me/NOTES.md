# THE OWNER: notes

This is the owner's fighter: a FaceBuilder head fitted from the owner's own photos on the Mixamo X Bot body.
The source model and the face-photo workflow are recorded in `source/`.

## Current build

- The original FaceBuilder head and its photo-projected texture are unchanged.
- `source/upgrade_body.py` reshapes the X Bot body using its existing Mixamo vertex weights: broader shoulders and
  chest, a narrower waist and hips, and thicker arms and thighs. This is a proportion adjustment to the X Bot
  mannequin, not a scan or a detailed anatomical sculpt.
- The same script generates procedural skin and charcoal-knit PBR textures, then extracts skinned shells from the
  body surface for a sleeveless training top and shorts.
- The Mixamo skeleton and all 28 required animation clips are preserved.
- The four renders were captured from the rebuilt `fighter.glb` using the local Three.js renderer in `.work/render.html`
  and the repository's Poly Haven boxing-ring HDRI. They are direct renders with no paint-over.

## Limitations

- The base is still X Bot geometry. Its separated body sections leave visible gaps at the neck, torso and hips; the
  clothing shells have rough cut edges and do not bridge every gap.
- The material maps are procedural surface detail, not scanned skin or fabric. The outfit has no cloth simulation,
  tailored seams or realistic folds.
- The face texture is based on three owner photos. The eyes still look downcast, the hair is painted into the texture,
  and the neck seam remains visible.
- This pass makes the body more masculine in proportion, but does not replace the underlying mannequin anatomy.

## Update log

- **Owner entry created:** the starting fighter was the existing FaceBuilder head on the Mixamo X Bot body; no model
  changes were made at entry creation.
- **Body/material update:** generated procedural skin and fabric maps, added basic skinned clothing shells and adjusted
  the body proportions toward a masculine build. Re-exported the model while retaining all 28 clips.

## Validator output

```
PASS  manifest.json has all fields
PASS  file size 11.1 MB (limit 80 MB)
PASS  extensions: KHR_texture_transform
PASS  self-contained (no external URIs)
PASS  7 textures (limit 40)
PASS  largest texture 2048 px (limit 4096)
PASS  91,952 triangles (limit 250,000)
PASS  Mixamo skeleton (all required mixamorig: bones present)
PASS  animations: 28/28
PASS  clip lengths within ±10 % of reference
PASS  bind-pose mesh height ≈ 1.82 m (expected 1.55–2.05 m; check scale if far off)
PASS  brain.js runs in the sandbox, valid outputs, 0.082 ms average (limit 2 ms)
PASS  renders/front.png 1920×1080 (long side ≥ 1920)
PASS  renders/three_quarter.png 1920×1080 (long side ≥ 1920)
PASS  renders/profile.png 1920×1080 (long side ≥ 1920)
PASS  renders/closeup.png 1920×1080 (long side ≥ 1920)
PASS  NOTES.md present and filled in
PASS  LICENSES.md present and filled in

All checks passed.
```
