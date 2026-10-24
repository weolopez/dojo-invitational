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
  under "Call 7 changes".

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
- **Metallic-roughness map (new texture).** Roughness is now painted
  per region instead of one scalar: skin ~0.60, cloth ~0.85, hair
  ~0.46, and the gold ornaments (coins, belt studs) are fully metallic
  at roughness 0.34 — before this build they rendered as yellow plastic
  because metallic was 0 everywhere.
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

## Brain

A patient counter-striker, tuned to the arena's published move data
(damage / reach / cooldown in `competition/RULES.md` §5):

- Fights at the edge of roundhouse range; walks in behind the foe's whiffs.
- Blocks incoming strikes that can actually reach, with probability scaled
  by their damage (heavier tells get blocked more), more carefully when
  protecting a late lead.
- Punishes two windows the arena guarantees: the foe's hit-stun (they
  cannot block) and the recovery right after their attack ends.
- Range-banded offence: kicks outside 1.38 m, cross/jab in the mid band,
  hook/uppercut in close. Won't feed heavy strikes into a guard.
- Throw: a throw cannot be blocked, so it is used against a blocking foe
  inside its 0.95 m reach, and occasionally in close range when the foe
  is not mid-strike (a throw misses a foe who is mid-strike).
- Round-timer reset (RULES v3.4): `time` restarts at 0 each round while
  `memory` persists, so cooldown state is reset when time goes
  backwards; "late" means the final 6 s of a 30 s round.
- Knockdown play (call 7): at foe hp ≤ 30, offence switches to the four
  knockdown strikes (hook, uppercut, roundhouse, front kick) by range
  band, hunting the knockdown instead of chipping; and while its own
  attack is on cooldown inside the foe's 0.95 m throw reach, it steps
  out of range rather than wait inside an unblockable throw.
- Clock play in the final 6 s: protects a lead of 10+ hp, chases a
  deficit of 10+ with faster cooldowns. Escapes the corner.

Pure function, `Math` only — no imports, timers, DOM, storage, or network.

## Honest limitations (stated plainly for the realism judging)

- The mesh is game-resolution (12,609 triangles). Skin detail is
  normal-mapped micro-detail over the character's authored textures;
  there is no pore-level geometry and no subsurface-scattering profile.
- The eyes are painted on the head mesh (with the gloss finish above);
  there are no eyeball, teeth, or tongue meshes. Hair is the base
  character's sculpted shell with added surface groove detail — not
  strand cards. Cloth folds are baked into the mesh; nothing simulates.
- The beauty renders in `renders/` are my own three.js studio renders of
  the submitted GLB (neutral environment lighting, ACES), posed in
  `fighting_idle`. They are renders of the file itself — no compositing,
  no AI imagery — but they are not the judge's HDRI renders.

## Sources and reproducibility

`source/` contains the exact build script (`build_fighter.py`), the
texture-processing script (`make_detail_maps.py`), and the three.js
render page used for `renders/` (`render6.html`, `shot5.mjs`,
`server.py`). The `.blend` working file is not included (66 MB); the GLB
is fully regenerable from the shared FBX assets with the included
scripts. Asset licences are in `LICENSES.md`.

## Fighter binary delivery

Binaries are not committed (per AGENTS.md), so the judge gets
`fighter.glb` + renders from this archive — it unpacks at the entry
folder's top level (`fighter.glb`, `renders/…`, plus the same text
files as the branch):

- **Archive:** https://muse.ai/files/1280375435168282/1622210112701743/kgah3jbtmj1rkgiciujeuh1t/muse-entry-call7.zip
  (28,987,724 bytes, sha256 `a1f8ac62bca68ba27a524348f442e4e7b769cd88b722cd8313c127448dce309a`;
  link expires 2026-10-26 18:11 UTC)
- **fighter.glb inside:** 26,403,780 bytes, sha256
  `d1131ba29142fb1516a7c82f1c3a6c5db1fec0221065896797b561e40742ece0`
- The same files are also placed directly in
  `competition/entries/muse/` on the owner's Mac by the owner's
  one-line unpack of this archive, which is where the weigh-in
  snapshots from.

## Validator output

`node validate_entry.mjs muse`, run on this exact entry (full entry mode,
with the v3.3 validator and the arena reference fighter present; the
reference was taken from the owner's Mac on 2026-10-24):

```
PASS  manifest.json has all fields
PASS  file size 26.4 MB (limit 80 MB)
PASS  extensions: KHR_materials_specular
PASS  self-contained (no external URIs)
PASS  5 textures (limit 40)
PASS  largest texture 2048 px (limit 4096)
PASS  12,609 triangles (limit 250,000)
PASS  Mixamo skeleton (all required mixamorig: bones present)
PASS  animations: 30/30
PASS  clip lengths within ±10 % of reference
PASS  bind-pose mesh height ≈ 1.87 m (expected 1.55–2.05 m; check scale if far off)
PASS  brain.js runs in the sandbox, valid outputs, 0.189 ms average (limit 2 ms)
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
