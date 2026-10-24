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
   weight 0.45, proportions 0.85, height 0.6, mixed ancestry; skin, high-poly eyes, eyebrow002, eyelashes02,
   teeth, tongue, ponytail01, female_sportsuit01, MPFB Mixamo rig, one subdivision level.
3. `02_materials.py`: grades the skin toward olive, adds a blood-flush tint and a roughness map placed from face
   landmarks, generates a tiling pore normal map, gives the eyes the brown
   iris (red cast shifted to dark brown) and a clearcoat, darkens the hair, recolours the brows dark brown,
   paints scalp and brow shading into the skin under the hair cap and brows (see below), recolours the sportsuit
   (terracotta top with charcoal piping, black leggings),
   and sets glTF alpha modes (opaque skin, teeth and cloth; cutout hair, brows, lashes and cornea).
4. `03_rig_and_retarget.py`: swings the arm chains from MPFB's A-pose to the clips' T-pose, bakes that as the rest
   pose, then retargets all 30 clips by copying each bone's world rotation from the X Bot source, corrected for the
   bones' rest-pose difference. Hip translation is scaled by the hip-height ratio (0.915).
5. `04_export_and_render.py`: applies MPFB's helper masks and subdivision (so hidden helper geometry is really
   removed) and exports `fighter.glb` with the 30 clips as NLA tracks.
6. Renders: `dojo/judge.html?id=claude`, the standardised Three.js harness, from the submitted `fighter.glb`.

## Update for call #4 (after tournament 10)

The call had no specific notes (the owner scores this entry). The real gap: rules v3.0 added two required clips,
`throw` and `thrown` (Mixamo's paired shoulder throw), and this entry still had 28 clips, so the arena was lending it
Mixamo's throw retargeted at load time. The validator failed on it (`animations: 28/30 — missing: throw, thrown`).

- **Own throw clips (new):** `03_rig_and_retarget.py` was re-run unchanged; it picks up every clip in
  `assets/mixamo/`, so `throw` and `thrown` (201 frames each) are now retargeted onto CLAUDE's own rig the same way as the
  other 28. `fighter.glb` was re-exported with `export()` from `04_export_and_render.py` (mesh and materials unchanged:
  167,392 triangles, 11 textures; 24.8 → 25.2 MB).
- **Checked in Three.js:** I loaded two copies of the new `fighter.glb` in headless Chrome, prepared them with the
  arena's own `fightClips()` (`dojo/src/lent.js`), and rendered the throw window (`.work/previews/call4/throw_*.png`).
  `throw` and `thrown` are now this fighter's own clips (not lent); the grab, the over-the-shoulder throw and the victim
  landing on her back read correctly. The two fighters' placement (±0.45 m) in that check is my guess, not the arena's
  exact code. Visible limits in those frames: in the grab, the victim's head and arm overlap the thrower's arm a little,
  as in the source paired clip on bodies of a different size; and in the bent poses the top rides up and shows midriff.
- **Brain:** the brain now throws a foe who is blocking or standing idle within 0.95 m (throws can't be blocked), so the
  new clips actually show in fights. Everything else in `brain.js` is unchanged.
- **Not shipped:** the optional v3.2 clips `knockdown_front`, `getup_back` and `getup_front`. The arena trims the
  lying-still start of the get-ups only when it lends them (`LENT_WINDOWS` in `lent.js`) and plays a fighter's own clip
  whole, so my own copies would lie still for 2–3 s. The arena keeps lending them.
- No skin, face, hair or clothing changes this round. The renders in `renders/` were re-made with the judge harness
  (`dojo/judge.html?id=claude`, headless Chrome) from this `fighter.glb`; they came out byte-identical to the call #3 renders, because the bind-pose mesh and materials
  didn't change.

## Update for call #3 (after tournament 8)

The call again had no specific notes (the owner scores this entry), so I went by the judge-harness renders in
`competition/judging/claude/`. This is a materials-only pass: the mesh, rig, retarget, clips and brain are unchanged
(same 167,392 triangles, 28 clips).

- **Skin roughness map (new):** the skin used to be one roughness value (0.48) everywhere. `position_map` now
  rasterises the body's UV triangles to get each skin texel's rest-pose 3D position, and `skin_regions` places
  masks from the face's own landmarks (nose tip = the most forward head point, ears = the widest). A generated
  2048 px roughness map (`claude_skin_roughness`, exported as the glTF metallicRoughness texture) is about 0.52 on
  the body, lower on the forehead/nose T-zone (down to about 0.36) and lips (down to about 0.30), with fine noise
  of about ±0.03 so the highlight breaks up.
- **Blood flush (new):** cheeks, nose tip and ears are tinted toward a deeper rose in the skin diffuse, so the face
  isn't one flat tone. Honestly, the effect is subtle at the harness's distance.
- **Training top:** the bright orange CC0 piping, which read like a costume on terracotta, is now charcoal (like
  the leggings). The CC0 top's lighter and darker blue panels had become blotchy light/dark terracotta; only 40 % of
  that contrast is kept now. The dye is also darker (HSV 12°, 0.76, 0.42), because the arena light rendered the old
  one as salmon pink. It now renders as a muted brick-terracotta. The lighter band around the neckline is still
  visible: it comes from the collar rib in the CC0 normal map and geometry, not the colour.
- Not used: the CC0 sportsuit AO map. Its UV layout doesn't match the diffuse's, so baking it in would put the
  shadows in the wrong places.

The four renders in `renders/` are copies of the judge harness's output (`dojo/judge.html?id=claude`, headless
Chrome) for this `fighter.glb`.

## Update for call #1 (after tournament 6)

The judge's call had no specific notes for this entry (the owner scores it), so I went by the judge-harness renders
in `competition/judging/claude/`. Their three most visible face faults were these, and this update fixes them:

- **Hairline / scalp:** bare light skin showed under the hair cap's cutout edge. `paint_under_cards` now maps every
  head texel of the skin texture to its rest-pose 3D position, finds the nearest point on the ponytail cap and reads
  the cap's alpha there, then paints the skin there near the hair colour, plus a soft feather past the edge. MPFB's
  hidden helper shells are skipped, and the ponytail below the nape is ignored so it doesn't stain the upper back.
  Result: the scalp under the cap is dark and the temples blend in. **Still a limitation:** the cap's own cutout edge
  is still a crisp, ragged line on the forehead; the feather only softens the skin side.
- **Brows:** eyebrow006 is a thin plucked line that hardly showed. Changed to eyebrow002 (fuller, natural arch),
  recoloured from black to dark brown, alpha cutoff 0.36. MPFB's brow material used the diffuse image as a bump
  height, which the glTF exporter turned into a meaningless normal map that rendered the brows black; that bump is
  removed and the texture is wired straight into Base Color. A faint brow shading is also painted into the skin.
- **Eyes:** the CC0 "brown" iris is a saturated red-brown and looked red in the arena. Its saturated pixels are
  rebuilt as hue 24° brown keeping their brightness detail; the sclera is unchanged.
- **Training top:** the terracotta read as pale salmon under the arena light; it's now darker (HSV 13°, 0.72, 0.56).
- Hair roughness 0.55 → 0.68 to cut the plastic sheen a little.

The motion, rig, retarget, brain and mesh are unchanged (same 167,392 triangles). The four renders in `renders/` are
copies of the judge harness's output (`dojo/judge.html?id=claude`, run in headless Chrome) for this `fighter.glb`.

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
- The base skin texture is only 2048 px with no cavity or specular-colour map; the roughness map's regions are
  hand-placed blobs, not scanned data; the pore normal is procedural and tiled, so it's uniform across the body.
- Hair is a textured cap with cutout cards, not strands; the cap's cutout edge on the forehead is still crisp
  (the painted scalp only softens the skin beneath it).
- The painted scalp is baked into the 2048 px skin diffuse, so it is low-resolution and not hair-strand detail.
- No hand wraps, although the concept had them; the CC0 pack has none.
- The face is neutral with no expression changes; there are no facial animations.
- Clothes are skinned, not simulated, so they don't move independently. In extreme poses (e.g. the roundhouse kick
  in the harness's `action_roundhouse.png`) the top clips: a sliver of chest skin shows through near the collar, and
  the shoulder of the top bulges. The leggings also crease sharply at the hip.
- Retargeted hands use the X Bot finger poses, so fists aren't fully closed in every clip.

## Validator output

```
PASS  manifest.json has all fields
PASS  file size 25.2 MB (limit 80 MB)
PASS  extensions: KHR_materials_clearcoat, KHR_texture_transform
PASS  self-contained (no external URIs)
PASS  11 textures (limit 40)
PASS  largest texture 2048 px (limit 4096)
PASS  167,392 triangles (limit 250,000)
PASS  Mixamo skeleton (all required mixamorig: bones present)
PASS  animations: 30/30
PASS  clip lengths within ±10 % of reference
PASS  bind-pose mesh height ≈ 1.73 m (expected 1.55–2.05 m; check scale if far off)
PASS  brain.js runs in the sandbox, valid outputs, 0.044 ms average (limit 2 ms)
PASS  renders/front.png 1920×1080 (long side ≥ 1920)
PASS  renders/three_quarter.png 1920×1080 (long side ≥ 1920)
PASS  renders/profile.png 1920×1080 (long side ≥ 1920)
PASS  renders/closeup.png 1920×1080 (long side ≥ 1920)
PASS  NOTES.md present and filled in
PASS  LICENSES.md present and filled in

All checks passed.
```
