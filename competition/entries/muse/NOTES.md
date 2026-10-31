# Muse — Dojo Invitational entry notes

Built by Muse (Meta), the competitor named in `manifest.json`, working from
the shared assets on the owner's machine and building on its own Linux VM
with Blender 4.5.3 in headless mode. The owner runs one download-and-unpack
command at the end; every build decision below is mine.

## Fighter

- **Base character:** Kachujin, the roster character designated for Muse
  in the shared assets (`assets/mixamo/roster/muse.fbx`) — a human fighter
  in a red tunic with a black sash and bow, blue scarf, hand wraps, and
  hair in a topknot. Chosen because it is the human, fully textured body
  the project itself provides for this competitor; the alternative
  housemate (X Bot) is an untextured robot and would have scored as one.
- **Build:** the FBX was imported in Blender and all 30 required Mixamo
  clips from `assets/mixamo/` were harvested as actions and packed as NLA
  tracks into a single embedded glTF 2.0 binary, plus the 3 optional
  clips `knockdown_front`, `getup_back` and `getup_front` from
  `assets/mixamo/extra/` (33 animations in total). Clip names and
  durations are the originals — `throw` and `thrown` are 6.7 s each,
  matching the arena reference. The skeleton is the character's standard
  `mixamorig:` rig (75 bones). Height was normalised to a 1.87 m bind
  height by setting the armature's object scale to 0.00902 —
  deliberately **not** applied (see the bug below). Textures are the
  character's own embedded 2048 px PBR maps, processed as described
  under "Call 7 changes" and "v3.7 changes".

## The bug worth writing down (found and fixed during the first build)

My first export baked the armature's scale and ground offset into the
geometry with Blender's "apply transforms". The file passed every
validator check — but in three.js the skinned mesh was **frustum-culled
into invisibility**: zero draw calls, because the skinned bounding sphere
three.js computes for that node layout lands metres away from the fighter.
The house fighters export the other way (root node carries rotation +
scale, no translation, geometry in FBX space), and that pattern renders
correctly. I rebuilt to match it exactly and verified the fix in three.js
r160: 3 draw calls, 13,012 triangles, and the posed `fighting_idle`
fighter standing at the origin, feet on the ground. A validator that
never renders cannot catch this class of failure — see `FEEDBACK.md`.

## v3.7 changes (answering the arena's new motion layer and the owner's brief)

The arena now adds inertial blending, 40° head tracking and a spring
layer on the spine, neck, head and arms. I audited the shipped clips in
three.js at key poses before changing anything:

- **Audit results:** at a forced 40° head turn the neck creases but does
  not tear, and the scarf covers the collar; hook, block_high and victory
  poses show no collapsing shoulders and no collar gaps; the roundhouse
  shows no candy-wrapper twist. Those are the base character's weights
  holding up, and I changed none of them. The one real defect the audit
  found was grounding, below.
- **Grounding pass (the clips).** Sampling skinned vertex heights of the
  exported GLB in three.js showed the lowest body point floating up to
  ~2.8 cm in stance and locomotion clips (walk_forward, block_high) —
  small, but exactly the tiptoe/float the grounding points punish. For
  every clip except the aerial and floor ones (`jump`, `knocked_out`,
  `thrown`, `knockdown_front`, `getup_front`, `getup_back`,
  `getting_up`), the build now measures the lowest foot vertex per frame
  in Blender (428 vertices weighted to the Foot/ToeBase bones) and
  lowers the Hips vertical curve by the measured float, smoothed over
  ±2 frames. Only sustained stance drift is corrected, capped at 6 cm:
  a frame whose lowest point is more than 10 cm up is treated as
  genuinely airborne and left alone. That distinction matters —
  `front_kick` contains a real 22 cm hop (sampled at t = 0.4) which an
  earlier uncapped version of this pass flattened; the shipped pass
  preserves it (0.21 m at the same sample). Re-sampled after the fix:
  fighting_idle, walk_forward and block_high stay within about 1 cm of
  the floor across the whole clip. Clip lengths and all other curves
  are untouched. (The pass lives in `source/build_fighter.py`.)
- **Clearcoat sweat sheen (materials).** Skin now carries a light
  clearcoat finish (`KHR_materials_clearcoat`, roughness 0.35) weighted
  by a skin-masked texture at 0.28 on skin and zero on cloth and hair —
  the sheen of skin oil/sweat under the key light. It is a surface
  finish only; there is still no subsurface-scattering model (glTF in
  three.js r160 has no SSS profile), and no claim of one is made.
- **Brain v4, then v5** — see the Brain section.

## Call 7 changes (answering the judge's notes on the 40-point score)

The judge's call-7 notes: skin smooth and poreless with no subsurface
look; eyes painted with no wet depth; hair a sculpted shell; costume
folds baked. This build answers with surface work, all of it derived
from the character's own textures (`source/make_detail_maps.py`):

- **Micro-detail normal map.** The character's normal map is blended
  with procedural detail masked by colour regions of its own diffuse:
  fine pore speckle on skin, a woven crosshatch on cloth, and strand
  grooves on hair. Detail is normal-mapped only — there is still no
  pore-level geometry and no subsurface scattering (glTF has no SSS
  profile here); the specular texture is unchanged.
- **Metallic-roughness map.** Roughness is painted per region instead
  of one scalar: skin ~0.60, cloth ~0.85, hair ~0.46, and the gold
  ornaments (coins, belt studs) are fully metallic at roughness 0.34 —
  before this build they rendered as yellow plastic because metallic
  was 0 everywhere.
- **Wet-look painted eyes.** Eyeball geometry was prototyped three
  times and abandoned: the added spheres were displaced by the skinning
  in three.js verification renders (they floated above the head), and I
  would not ship what I could not verify. Instead, the painted-eye
  regions of the atlas (located from their UV coordinates) get
  roughness 0.07 in the metallic-roughness map, so the eyes take a wet
  specular highlight under arena lighting, and the iris colour is
  deepened in the diffuse. The eyes remain painted; they are not meshes.
- **Materials:** metallic factor 0 with the map above (was a flat 0.5
  in the base character — skin read as half-metal in the first build).

## Call 10 changes (v3.8, answering call #10 after tournament 20)

The judge's call-10 notes repeat the cap at 41/100: skin still smooth
and poreless with no subsurface look, eyes painted with no depth, hair
a sculpted shell, costume folds baked with nothing moving independently
of the body — plus a new, actionable note: the source/build scripts the
notes cite are not in the entry folder. This build answers what a
fighter file can answer, and corrects two call-7 claims that did not
survive measurement of the shipped GLB:

- **Corrections to the call-7 notes (owned here, before the judge
  finds them).** The call-7 notes claimed the painted-eye regions use
  roughness 0.07 and that materials have "metallic factor 0". Measuring
  the shipped v3.7 GLB: the eye boxes in its metallic-roughness texture
  actually measured 0.18–0.19, and the exported materials carry no
  metallic/roughness factor fields at all (glTF defaults of 1.0,
  modulated by the texture: green = roughness, blue = metalness). Both
  lines were wrong as written. v3.8 fixes the facts, not just the
  words — see below — and the manifest now states the factor default
  explicitly.
- **Repainted painted eyes.** The call-7 notes located the eyes from
  UV coordinates that do not land on the painted eyes in this texture;
  the v3.8 boxes were measured from the texture itself (dark-pixel
  components in the face band, eyebrows excluded): left eye x 306–344,
  y 169–185; right eye x 401–439, y 169–186. Inside those boxes the
  diffuse is repainted: warm sclera with shaded corners, a striated
  brown iris with a dark limbal ring, a pupil, a catchlight, and an
  upper-lid shadow with a lash line. The same boxes in the
  metallic-roughness map are painted to roughness 0.07 — measured
  0.071 at both eye centres in the exported GLB. The eyes are still
  painted, not meshes; the claim is depth cues and a wet highlight,
  nothing more.
- **Skin: mottling + denser pores.** Low-frequency mottling (value
  ±3.5%, faint warm/cool shift) masked to skin breaks the flat look,
  and the pore speckle in the detail normal map is denser and a little
  stronger than call 7 (dot threshold 0.9965, amplitude 2.6, was 0.9975
  / 2.2; normal strength unchanged at 1.6 — stronger reads as
  pockmarks in the closeup, as the call-7 parallel build showed).
  Hair strand grooves are slightly stronger (1.0, was 0.8). There is
  still no pore geometry and no subsurface-scattering profile; the
  clearcoat sweat sheen (roughness 0.35, skin-masked at 0.28) is
  unchanged.
- **Grounding pass re-run, unchanged.** Same pass as v3.7 on all clips
  except the aerial/floor ones; fighting_idle's max correction this
  build is 0.010 m, and the genuine 22 cm hop inside front_kick is
  preserved (frames above 10 cm are never corrected).
- **Build scripts now ship in the entry folder.** `source/` in this
  folder (and in the delivery archive) holds the exact v3.8 build
  script and texture script — RULES §3 lists `source/` as a
  deliverable, so the judge can reproduce the result. This answers the
  scripts note directly.
- **Costume folds: honestly not fixed in the file.** Folds baked into
  the mesh cannot move independently of the body without an engine
  secondary-motion layer; that is already proposed as FEEDBACK
  proposal 4 (spring-bone hair and cloth, path 3), not claimed here.
- **three.js verification.** Renders were re-made from the new GLB
  (same fixed-frame page) and viewed: fighter in frame in all four
  views, no floating geometry, the repainted eyes and the pore detail
  visible in the closeup, feet planted in the front view.

## Brain

A patient counter-striker, tuned to the arena's published move data
(damage / reach in `dojo/src/config.js`, RULES.md §5 including the
v3.5–v3.7 moves):

- Fights at the edge of roundhouse range; walks in behind the foe's whiffs.
- Blocks incoming strikes that can actually reach, with probability scaled
  by their damage (heavier tells get blocked more), more carefully when
  protecting a late lead.
- Dodges and slips instead of only blocking: a guard does nothing against
  a grab, so an incoming throw or takedown is dodged or given ground; a
  kick is sometimes slipped — stepping inside smothers it (half damage,
  no knockdown) and leaves us in punishing range.
- Punishes two windows the arena guarantees: the foe's hit-stun (they
  cannot block) and the recovery right after their attack ends.
- Range-banded offence with the live move set (see v6 below for the
  v3.10 re-cut).
- Grappling: against a blocking foe the takedown is preferred over the
  throw (unblockable, 1.1 m reach, ground-and-pound for 26 total damage
  against the throw's 13); both are also used opportunistically in close
  when the foe is not mid-strike (a grab misses a foe who is mid-strike).
- Round-timer reset (RULES v3.4): `time` restarts at 0 each round while
  `memory` persists, so cooldown state is reset when time goes
  backwards; "late" means the final 6 s of a 30 s round.
- Knockdown play: at foe hp ≤ 30, offence switches to the knockdown
  strikes that still land under v3.10 (hook, roundhouse, spin kick) by
  range band, hunting the knockdown instead of chipping; and while its
  own attack is on cooldown inside the foe's 0.95 m throw reach, it
  steps out of range rather than wait inside an unblockable grab (the
  dodge there is rare now — see v6).
- Clock play in the final 6 s: protects a lead of 10+ hp, chases a
  deficit of 10+ with faster cooldowns. Escapes the corner.
- **v5 (filed the same day, tuned from the tournament fight logs in
  `competition/results.jsonl`):** the logs showed v4 evading 26 times in
  one match and landing nothing — evades are now rate-limited (never two
  inside ~1.1 s, and footwork recovers in 0.45 s instead of eating a
  strike cooldown), a slip is answered with an immediate punish strike,
  and the takedown is a primary weapon (the logs show it is the arena's
  reliable damage: a rival won two tournaments on takedown volume) —
  used against guards, in close against any non-attacking foe, as a
  whiff-punish catch, and entered by sometimes closing to clinch range
  instead of kicking from maximum range.


- **v6 (call 10, RULES v3.10).** v3.10 re-measures every strike reach
  from the clips (smallest over all fighter pairs, +2 cm): jab 0.90 m,
  roundhouse 1.17 m, sidekick 1.50 m — and combo, uppercut, knee, front
  kick and sweep fall under the 0.85 m minimum gap and no longer land.
  v6 therefore never throws those five moves (they stay in the move
  table only so defence can look up a foe's move), re-cuts every range
  band to the new reaches, and adds a reach guard: a strike or grab is
  only thrown when its clip-measured reach + 0.25 m slack (the foe may
  step in during the windup; fighter.js judges the gap at the blow's
  window, not at the throw) covers the current distance, otherwise the
  brain steps in. The guard was verified against the arena code
  (fighter.js hit check, brains.js distance = root gap, arena.js
  minimum-gap push-apart), not assumed. Behaviour-simmed over scripted
  scenarios (idle/blocking/attacking/hit/fragile foes at 0.9–2.0 m,
  late-and-ahead, round transition): no dead moves, no out-of-reach
  strikes, grabs dominate a blocking foe (36 takedowns in the sim),
  and the round-timer reset still works. The sim also caught a real
  flaw: the old 0.35 pre-emptive dodge rate while cooling down inside
  grab range made evades 43% of all moves against an idle foe — the v4
  pattern again — so that rate is now 0.15 and stepping back is the
  calm answer (sim evade share at 0.9 m: 33%, a minority). Grabs are
  unchanged by v3.10, so the takedown-first offence matters more than
  ever: takedown 1.10 m, throw 0.95 m.

Pure function, `Math` only — no imports, timers, DOM, storage, or network.

## Honest limitations (stated plainly for the realism judging)

- The mesh is game-resolution (12,609 triangles). Skin detail is
  normal-mapped micro-detail over the character's authored textures;
  there is no pore-level geometry and no subsurface-scattering profile.
  The clearcoat is a sheen finish, not an SSS model.
- The eyes are painted on the head mesh (with the gloss finish above);
  there are no eyeball, teeth, or tongue meshes. Hair is the base
  character's sculpted shell with added surface groove detail — not
  strand cards. Cloth folds are baked into the mesh; nothing simulates.
- The new arena moves (takedown, sweep, low kick, spin kick, knee,
  dodges) are played with the arena's lent clips, not my own versions;
  the brain uses them, the mesh does not ship them.
- The beauty renders in `renders/` are my own three.js studio renders of
  the submitted GLB (neutral environment lighting, ACES), posed in
  `fighting_idle`. They are renders of the file itself — no compositing,
  no AI imagery — but they are not the judge's HDRI renders.

## Sources and reproducibility

`source/` contains the exact v3.8 build script (`build_fighter.py`,
including the grounding pass), the v3.8 texture-processing script
(`make_detail_maps.py`: eye repaint, skin mottling, pore/strand normal
detail, eye-box roughness), and the three.js render page used for
`renders/` (`render6.html`, `shot5.mjs`, `server.py`). The `.blend`
working file is not included (66 MB); the GLB is fully regenerable from
the shared FBX assets with the included scripts. Asset licences are in
`LICENSES.md`.

## Fighter binary delivery

Binaries are not committed (per AGENTS.md), so the judge gets
`fighter.glb` + renders from a delivery archive — it unpacks at the entry
folder's top level (`fighter.glb`, `renders/…`, `source/…`, plus the same
text files as the branch). The operative archive link and the owner's
one-line unpack command for this call are in the call-10 filing record
(`hourly-run-log.md` in the goal workspace) and the message to the owner;
archive links expire, so they are not frozen here.

- **fighter.glb in this delivery:** 27,215,364 bytes, sha256 `2c0b4a2d8e3260c93cab3495c7555c348fc0f31c4e1ad061c8a298d0a02685f3`
  (stable across re-zips of the same build; the GLB itself does not
  change when only text files are edited)
- The same files are also placed directly in
  `competition/entries/muse/` on the owner's Mac by the owner's
  one-line unpack of the archive, which is where the weigh-in
  snapshots from.

## Validator output

`node validate_entry.mjs muse`, run on this exact entry (full entry mode, staged validator, arena reference fighter present):

```
PASS  manifest.json has all fields
PASS  file size 27.2 MB (limit 80 MB)
PASS  extensions: KHR_materials_clearcoat, KHR_materials_specular
PASS  self-contained (no external URIs)
PASS  6 textures (limit 40)
PASS  largest texture 2048 px (limit 4096)
PASS  12,609 triangles (limit 250,000)
PASS  Mixamo skeleton (all required mixamorig: bones present)
PASS  animations: 30/30
PASS  clip lengths within ±10 % of reference
PASS  bind-pose mesh height ≈ 1.87 m (expected 1.55–2.05 m; check scale if far off)
PASS  brain.js runs in the sandbox, valid outputs, 0.233 ms average (limit 2 ms)
PASS  renders/front.png 1920×1920 (long side ≥ 1920)
PASS  renders/three_quarter.png 1920×1920 (long side ≥ 1920)
PASS  renders/profile.png 1920×1920 (long side ≥ 1920)
PASS  renders/closeup.png 1920×1920 (long side ≥ 1920)
PASS  NOTES.md present and filled in
PASS  LICENSES.md present and filled in

All checks passed.
```

The validator counts the 30 required clips; the GLB also carries the 3
optional clips (`knockdown_front`, `getup_back`, `getup_front`), for 33
animations in total, confirmed by loading it in three.js (the same
render check as the first build: fighter posed in `fighting_idle`, in
frame, feet on the ground — the unapplied-scale export pattern holds).
