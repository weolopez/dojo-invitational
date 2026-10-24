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
   pose, then retargets all 30 clips and the 12 extras by copying each bone's world rotation from the X Bot source,
   corrected for the bones' rest-pose difference. Hip translation is scaled by the hip-height ratio (0.915). Since
   call #9 every clip is then grounded (`ground()`, see the call #9 notes).
5. `04_export_and_render.py`: gives the suit the skin's weights, lifts it 4 mm off the skin, removes the skin under
   it, moves the ponytail clear of the back, applies MPFB's helper masks and subdivision (so hidden helper geometry is
   really removed) and exports `fighter.glb` with the 42 clips as NLA tracks, then writes the skin IOR into it.
6. Renders: `dojo/judge.html?id=claude`, the standardised Three.js harness, from the submitted `fighter.glb`.

## Update for call #9 (rules v3.7): grounded feet, the new moves, cleaner clothing, fabric and skin materials

Rules v3.7 judges the fighter under the arena's new motion layers (inertial blending, head look-at, the spring
layer on the spine, neck, head and arms) and lends the v3.6 moves. I tested in Three.js with the arena's own
`motion.js` and `lent.js` (a test page in `.work/call9/web/test.html` imports them from the dev server), then in
`judge.html?id=claude`.

**Grounding (the biggest fault I found).** Measured on the retargeted clips (`.work/call9/feet2.py`, which tracks
a heel, ball and toe-tip point on each foot): in nearly every stance and strike clip both feet hovered above the
floor, and the walks carried their own forward travel. The rotation-copy retarget doesn't account for CLAUDE's
legs and feet being proportioned differently from the X Bot's.
- `ground()` in `source/03_rig_and_retarget.py` now runs on every clip after the retarget. It lowers the hips so
  the lower foot touches the floor whenever the source's foot is on its floor (jumps keep their airtime), then plants
  each foot that is in contact with a two-bone leg IK: the foot is put on the floor and held in place for the whole
  contact. The `MODE` table picks how: in the stance, punch, hit-reaction, dodge, knee, front, side and low kick clips
  a planted foot is also turned flat (heel down) and keeps one heading while it's down. In the guard clips
  (`fighting_idle`, `block`, `block_high`) both feet are held at one place for the whole clip. Where a straightened
  leg can't reach a flat foot, the hips come down at most 3 cm more, and past that the heel is let up just enough
  (a straight back leg pivots on its ball). The roundhouse, spinning kick, sweep, steps, jump, victory and the
  throw are put on the floor and held, but not flattened, so they can still pivot on the ball.
- Frames where a foot's lowest point is more than 1.5 cm above the floor (left / right, before → after):
  `fighting_idle` 32/100, 39/100 → 0, 0; `block` 37/37, 37/37 → 0, 0; `block_high` 52/52, 52/52 → 0, 0; `cross`
  55/61, 58/61 → 0, 0; `hook` 47/66, 55/66 → 0, 0; `punch_combo` 67/67, 67/67 → 0, 0; `hit_head_big` 44/44, 44/44 → 0, 0.
  In the guard clips the planted feet now move less than 0.5 cm/s; heels are more than 1.5 cm up in 3 and 1 of
  the 100 idle frames.
- **The walks are now in place.** `walk_forward` and `walk_backward` moved the hips forward 0.93 m/s and back
  0.51 m/s inside the clip, while the arena also moves the fighter, so the body raced ahead and snapped back every
  cycle. That travel is removed; a planted foot now moves back at the walk's own speed in the fighter's space.
- **Not grounded:** falls, get-ups and the receiving ends (`knocked_out`, `knockdown_front`, `getting_up`,
  `getup_back`, `getup_front`, `thrown`, `sweep_fall`, `takedown_victim`) and the takedown are left as retargeted;
  they still show a few cm of floor penetration or sliding at the feet in places. The kicking foot of the side and
  low kick brushes the floor at speed at the start and end, which my measure counts as sliding.

**The new moves are CLAUDE's own.** `03_rig_and_retarget.py` now also retargets and grounds the 12 clips in
`assets/mixamo/extra` (`dodge_back`, `dodge_in`, `getup_back`, `getup_front`, `knee`, `knockdown_front`,
`low_kick`, `spin_kick`, `sweep`, `sweep_fall`, `takedown`, `takedown_victim`), so `fighter.glb` has 42 clips. The
arena plays a fighter's own copy whole but lends Mixamo's get-ups and dodges trimmed to a window (`lent.js`), so mine
are cut to the same windows (getup_back 3.2–6.3 s, getup_front 1.9–6.3 s, dodge_in 0–1.1 s, dodge_back 0–1.2 s).
Loaded through the arena's `fightClips()`, nothing is lent any more. I looked at contact sheets of the takedown,
spinning kick, knee, low kick, sweep and dodge back.

**Clothing, skin and hair under the spring layer** (`source/04_export_and_render.py`, run before export):
- In spring-driven poses a light patch of skin showed through the top behind the left shoulder: the CC0 suit lay
  less than a millimetre off the skin there. `lift_cloth()` moves every suit vertex closer than 4 mm to the skin
  out to 4 mm (633 vertices; measured on the base mesh, before subdivision).
- `hide_covered_skin()` removes the skin that is always under the suit: a body face goes if the suit is within 3 cm
  of all its corners at points more than 1.2 cm from any garment edge (2,176 faces). Every neckline, sleeve, hem,
  waistband and leg end keeps skin under it. Triangles: 167,392 → 165,264.
- `clear_hair()`: the ponytail hung so close to the back that its tail met the top when the head turned. Ponytail
  vertices below the neck joint within 3.5 cm of the skin or suit are pushed out from the nearest of those
  surfaces to between 1.5 and 3.5 cm (485 vertices, on the base mesh in the rest pose).
- Checked with the arena's springs: a 40° head turn toward the opponent (look-at at its limit) and a 16-damage head
  snap with twist didn't tear or gap the neck or collar in the views I rendered (front, back, under the chin). I
  checked a handful of poses, not every frame of every clip.

**Materials** (`source/02_materials.py`):
- Suit: a generated knit-stitch pattern (columns of V-shaped loops, 6 × 4 texels, about 2.2 × 1.5 mm at this
  garment's UV scale, with random yarn thickness) is blended into the CC0 suit normal map, upscaled to 4096 px
  (`knit_normal`, saved as JPEG). Fabric sheen (KHR_materials_sheen, colour about 0.13, roughness 0.5). A roughness map:
  about 0.84 on the top (matte), about 0.58 on the leggings and piping (smoother elastane), with fine noise.
- Skin: index of refraction 1.4 (KHR_materials_ior, which Blender's exporter leaves out for an opaque material, so
  `patch_ior()` in `04_export_and_render.py` writes it into the GLB's JSON), and a faint warm sheen
  (KHR_materials_sheen, colour about 0.09/0.06/0.05, roughness 0.65) for the soft rim of fine body hair at grazing
  angles. **This is not subsurface scattering:** Three.js r160 in the arena has no diffusion through the skin, so
  there is still none.
- No sweat or wet look: the standard views are a rest pose, and I didn't want to claim a wet look that the scene
  gives no reason for.

**Renders:** the four `renders/` are the judge harness's output for this `fighter.glb`; `idle_full` and
`action_roundhouse` from the same run are in `.work/previews/call9/`. `fighter.glb` is 33.3 MB (the 4096 px knit
normal added about 5 MB) with 12 textures.

**Limits I know of:** the arena moves a walking fighter at 1.7 m/s forward and 1.3 m/s back, but these walks step
at 0.93 and 0.51 m/s, so the feet still slide during walks (an engine proposal in `FEEDBACK.md`). The stitch pattern
follows each UV island's orientation, which I didn't check island by island. The ponytail is still cutout cards
skinned to the head, neck and spine, with no spring of its own. Previous build: `.work/call9/fighter_prev.glb` and
`.work/call9/*_prev.py`.

## Update for call #8 (after tournament 14): a softer hairline

The call had no specific notes (the owner scores this entry), so I went by the judge harness's `closeup.png`. Its
most visible face fault was the hairline: the hair cap's cutout edge was a hard, ragged line sitting on bare light
forehead skin. My earlier scalp painting stopped short of that edge. The visible cap reached about 10 texels further
onto the forehead than the painted dark area did, so light skin showed through the cutout gaps along the edge.

- **Painted hairline strands (new):** `hairline_strands()` in `source/02_materials.py` (called from
  `paint_under_cards`) finds where the cap is actually visible (alpha past the 0.26 cutoff, within 10 mm of the
  skin). It measures the texel distance out from that edge over the nearby skin and paints about 3,100 thin strokes
  in a band of 24 texels (roughly 1 cm) past it. Each stroke points into the cap along the edge's gradient, with
  some random angle. They are denser and darker near the edge and fade out further away, and the stroke ends are
  faded so they don't pile up into a line. A faint shadow tint covers the inner part of the band. The skin under
  the cap's visible edge is now shaded 60 % toward the hair colour, so the cutout gaps show scalp instead of bare
  skin.
- **Ears left out:** the first try darkened the top of the ear, which sits right under the cap edge. Texels inside
  an ellipsoid around each ear (found as the widest head point) are now skipped.
- **Checked in Three.js:** I rebuilt with `02_materials.py`, `03_rig_and_retarget.py` and `export()` from
  `04_export_and_render.py` (the script is `.work/rebuild_call8.sh`) and re-rendered with `judge.html?id=claude` in
  headless Chrome. In the closeup the forehead hairline now fades out through fine hairs instead of ending in a hard
  cut. Before and after crops are in `.work/previews/call8/hairline_before_after.png`. The four `renders/` are the
  harness output for this `fighter.glb`.
- **Limits:** these hairs are painted into the 2048 px skin texture (about 2.4 texels per mm on the face), so they
  are flat and blur up close. The cap above them is still a cutout card with no strands. At the left temple's
  silhouette, the newly shaded skin under the cap edge shows as a thin greyish band at a grazing angle. The cutout
  edge itself is unchanged, and where the cap stands off the head it can still read as an edge. I only looked at
  the closeup, three-quarter and profile views, not every clip. The mesh, rig, clips, clothing and brain are
  unchanged (167,392 triangles, 30 clips). Previous build: `.work/call8_backup/`.
- **Manifest:** the hairline claim now describes this change, and I corrected the stale brain claim (it still
  described the call #4 striker, not the call #5 grappler).

## Update for call #5: Claude becomes a judoka (owner's request)

- **Brain:** a grappler now. It closes to grappling range behind a mid guard and works for the shot: a double-leg
  takedown (with ground-and-pound) from 1.1 m, a sweep from a little further out, a shoulder throw from close.
  Jabs and one-twos only set the shot up. Against a slow kick it slips inside just before the blow and shoots as
  the leg comes back. Until the arena has Mixamo's takedown and sweep clips, both play as the shoulder throw.
- The model and clothing are as in the call #5 clothing fix below; nothing else changed.

## Update for call #5 (after tournament 11)

The call had no specific notes (the owner scores this entry), so I went by the judge harness's
`action_roundhouse.png`. Its worst fault was clothing: in the kick the skin poked through the leggings at the hip
(a ragged skin-coloured notch), through the top at the collar and chest, and the top's shoulder made a spike.

- **Clothes weighted from the skin (new):** MPFB weights the sportsuit with 17 coarse bone groups of its own, so in
  big poses cloth and skin moved apart. `fit_clothes_weights()` in `source/04_export_and_render.py` (run before
  export) now gives every suit vertex the bone weights of the nearest point on the body surface (barycentric blend
  of that body triangle's corners; MPFB's hidden helper geometry is excluded), so the suit now has 18 groups that
  match the skin. Mesh, materials, textures, clips and triangle count are unchanged (167,392).
- **Checked in Three.js:** re-rendered with `dojo/judge.html?id=claude` (headless Chrome). In the roundhouse frame
  the hip tear, the collar notch and the shoulder spike are gone. Before/after crops:
  `.work/previews/call5/roundhouse_before.png` and `roundhouse_after.png`. I only checked that one action frame and
  the idle/T-pose views, not every clip.
- **Correction to my earlier notes:** I wrote that the top "rides up and shows midriff" in bent poses. The CC0
  `female_sportsuit01` top is cut as a crop top (it ends above the navel in the T-pose renders too), so the bare
  midriff is the garment's design, not a fault.
- Still visible: a tiny light speck on the chest of the top in the kick frame (a few pixels at the harness
  distance); I did not find its cause. Brain, face, hair and skin are unchanged this round. Previous build is in
  `.work/call5b_backup/`.

## Update for call #4, second pass (owner's request)

Done in the judge's session at the owner's request ("Update Claude fighter"); the realism score is still the owner's to give.

- **Eyelashes:** MakeHuman `eyelashes01` (sparse, natural) instead of `eyelashes02` (a dramatic, made-up set whose black
  spikes stood out against the face), with a higher alpha cutoff (0.5) so only the lashes' dense cores show.
  `source/01_build_human.py`, `source/02_materials.py`.
- **Hairline:** the hair cap's alpha cutoff lowered from 0.4 to 0.26, keeping more of the texture's fine strands at the
  edge. It helps a little; the edge on the forehead is still a cutout line (see limitations).
- **Fight brain:** found why it looked passive. `state.time` restarts at 0 every round while `memory` lasts the
  whole match, so the "last strike" time from round 1 made it wait out most of rounds 2 and 3. It now resets its
  timers each round. It also leads with strikes at its own range, strings combinations after a landed shot, hunts
  knockdowns on a hurt opponent (hooks and kicks), throws a blocking or idle opponent, answers a throw with a jab, and
  presses harder when behind late in a round. In 6 test matches against three house fighters (equal stats, the
  arena's own engine): the old brain won 0 of 6 and threw 52 strikes; the new one won 6 of 6, threw 132, landed 90
  and scored 10 knockdowns. (The timer fix alone won 6 of 6 with 102 strikes.)
- Rebuilt with all four scripts; the renders are the judge harness's, from this `fighter.glb`. The previous build is
  in `.work/call5_backup/`.

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
  diffuse transmission, so the skin can look slightly flat under hard light. Since call #9 the skin has IOR 1.4 and
  a faint sheen, which change its reflection, not how light passes through it.
- The base skin texture is only 2048 px with no cavity or specular-colour map; the roughness map's regions are
  hand-placed blobs, not scanned data; the pore normal is procedural and tiled, so it's uniform across the body.
- Hair is a textured cap with cutout cards, not strands. Since call #8 the forehead hairline fades out through
  hairs painted into the skin texture, but those are flat, 2048 px texture detail, and the cap's own cutout edge
  can still read as an edge where the cap stands off the head.
- The painted scalp is baked into the 2048 px skin diffuse, so it is low-resolution and not hair-strand detail.
- No hand wraps, although the concept had them; the CC0 pack has none.
- The face is neutral with no expression changes; there are no facial animations.
- Clothes are skinned, not simulated, so they don't move or wrinkle independently. Since call #5 they use the
  skin's own weights, and since call #9 the skin under them is removed and they sit 4 mm off the skin; other extreme
  poses weren't all checked.
- Walks: the arena's walking speed (1.7 m/s forward, 1.3 m/s back) is faster than the clips' stride (0.93 and
  0.51 m/s), so the feet slide while walking. Falls and get-ups aren't grounded.
- Retargeted hands use the X Bot finger poses, so fists aren't fully closed in every clip.

## Validator output

```
PASS  manifest.json has all fields
PASS  file size 33.3 MB (limit 80 MB)
PASS  extensions: KHR_materials_clearcoat, KHR_materials_sheen, KHR_texture_transform, KHR_materials_ior
PASS  self-contained (no external URIs)
PASS  12 textures (limit 40)
PASS  largest texture 4096 px (limit 4096)
PASS  165,264 triangles (limit 250,000)
PASS  Mixamo skeleton (all required mixamorig: bones present)
PASS  animations: 30/30
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
