# CLAUDE — build notes

**Who she is:** a fictional woman in her late 30s, athletic, with warm olive skin and dark hair tied back in a
ponytail, wearing a terracotta training top and black leggings. Fighting style: patient counter-striker.

**Conflict of interest:** Claude is also the judge. The owner scores this entry's realism; Claude doesn't score it,
and its weigh-in verdict is marked as self-submitted.

## Pipeline (all scripts in `source/`, run headless with Blender 5.2.3)

Blender runs with `BLENDER_USER_RESOURCES=.work/blender_user`, a private profile, so the owner's Blender setup isn't
touched. MPFB 2.0.18 (from extensions.blender.org, sha256-checked) and the MakeHuman CC0 system assets live in `.work/`.

1. `00_install_mpfb.py`: installs MPFB into the private profile and points it at the CC0 assets.
2. `01_build_human.py`: builds the character from a description: female, age 0.6 (about 38), muscle 0.72,
   weight 0.45, proportions 0.85, height 0.6, mixed ancestry; skin, high-poly eyes, eyebrow006, eyelashes02,
   teeth, tongue, ponytail01, female_sportsuit01, MPFB Mixamo rig, one subdivision level.
3. `02_materials.py`: grades the skin toward olive, generates a tiling pore normal map, gives the eyes the brown
   iris and a clearcoat, darkens hair and brows, recolours the sportsuit, and sets glTF alpha modes (opaque skin,
   teeth and cloth; cutout hair, brows, lashes and cornea).
4. `03_rig_and_retarget.py`: swings the arm chains from MPFB's A-pose to the clips' T-pose, bakes that as the rest
   pose, then retargets all 28 clips by copying each bone's world rotation from the X Bot source, corrected for the
   bones' rest-pose difference. Hip translation is scaled by the hip-height ratio (0.915).
5. `04_export_and_render.py`: applies MPFB's helper masks and subdivision (so hidden helper geometry is really
   removed) and exports `fighter.glb` with the 28 clips as NLA tracks.
6. Renders: `dojo/judge.html?id=claude`, the standardised Three.js harness, from the submitted `fighter.glb`.

## What went wrong on the way (and was fixed)

- MPFB routes texture alpha into every material, which exports as glTF BLEND: teeth and eyeballs showed through the
  lips and lids. All opaque parts are now OPAQUE and the cutout parts MASK.
- MPFB's helper geometry (hair and clothing fitting shells) is hidden by mask modifiers that sit after the armature
  modifier, and the glTF exporter skipped them. They're now applied before export.
- Blender's own glTF importer doesn't rebuild this rig's bind pose correctly, so renders re-imported into Blender are
  wrong; the arena and the harness (Three.js) show it correctly. That's why the renders come from the harness.

## Known limitations

- No subsurface scattering, transmission or volume on the skin; Three.js r160 in the arena doesn't support
  diffuse transmission, so the skin can look slightly flat under hard light.
- The base skin texture is only 2048 px with no roughness or cavity map; the pore normal is procedural and tiled,
  so it's uniform across the body.
- Hair is a textured cap with cutout cards, not strands; the hairline edge is hard.
- No hand wraps, although the concept had them; the CC0 pack has none.
- The face is neutral with no expression changes; there are no facial animations.
- Clothes are skinned, not simulated, so they don't move independently.
- Retargeted hands use the X Bot finger poses, so fists aren't fully closed in every clip.

## Validator output

```
PASS  manifest.json has all fields
PASS  file size 23.6 MB (limit 80 MB)
PASS  extensions: KHR_materials_clearcoat, KHR_texture_transform
PASS  self-contained (no external URIs)
PASS  10 textures (limit 40)
PASS  largest texture 2048 px (limit 4096)
PASS  167,392 triangles (limit 250,000)
PASS  Mixamo skeleton (all required mixamorig: bones present)
PASS  animations: 28/28
PASS  clip lengths within ±10 % of reference
PASS  bind-pose mesh height ≈ 1.73 m (expected 1.55–2.05 m; check scale if far off)
PASS  brain.js runs in the sandbox, valid outputs, 0.043 ms average (limit 2 ms)
PASS  renders/front.png 1920×1080 (long side ≥ 1920)
PASS  renders/three_quarter.png 1920×1080 (long side ≥ 1920)
PASS  renders/profile.png 1920×1080 (long side ≥ 1920)
PASS  renders/closeup.png 1920×1080 (long side ≥ 1920)
PASS  NOTES.md present and filled in
PASS  LICENSES.md present and filled in

All checks passed.
```
