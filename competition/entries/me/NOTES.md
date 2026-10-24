# THE OWNER: notes

The owner's own fighter (RULES.md §12): a FaceBuilder head made from the owner's photos, on the Mixamo X Bot body.
This is the starting point, the same model the arena has used for the house fighter "You". From here on the owner and
their coding agents hand-craft it; each update below says who did what.

## How it's built

1. `source/build_photo_head_facebuilder.py`: FaceBuilder fits a head to three photos from `photos/` and projects a
   2048 px texture from them.
2. `source/build_fighter_with_my_head.py`: attaches that head to Mixamo's X Bot, matches the skull size, and packs
   all 28 Mixamo clips into one `fighter.glb`.

Both scripts ran from the project root (they read `photos/` and `assets/mixamo/`); the copies here are the record.

## Known weaknesses (the judge's notes on the house version: 33/100)

- The body is X Bot's plain plastic mannequin: no skin, no clothing, and a visible seam at the neck.
- The face texture is low resolution and the eyes look downcast (the photos were taken looking down).
- The hair is painted into the texture, with no volume.
- Only three photos were used; there's no profile or close-up data.

## Update log

- **Entry created (by Claude, the judge's session, on the owner's request):** copied the existing model, wrote this
  manifest, a starter pressure-fighter `brain.js` and these notes. No changes to the model itself.

## Validator output (entry created)

```
PASS  manifest.json has all fields
PASS  file size 6.6 MB (limit 80 MB)
PASS  extensions: KHR_materials_specular
PASS  self-contained (no external URIs)
PASS  1 textures (limit 40)
PASS  largest texture 2048 px (limit 4096)
PASS  81,860 triangles (limit 250,000)
PASS  Mixamo skeleton (all required mixamorig: bones present)
PASS  animations: 28/28
PASS  clip lengths within ±10 % of reference
PASS  bind-pose mesh height ≈ 1.82 m (expected 1.55–2.05 m; check scale if far off)
PASS  brain.js runs in the sandbox, valid outputs, 0.066 ms average (limit 2 ms)
PASS  renders/front.png 1920×1080 (long side ≥ 1920)
PASS  renders/three_quarter.png 1920×1080 (long side ≥ 1920)
PASS  renders/profile.png 1920×1080 (long side ≥ 1920)
PASS  renders/closeup.png 1920×1080 (long side ≥ 1920)
PASS  NOTES.md present and filled in
PASS  LICENSES.md present and filled in

All checks passed.
```
