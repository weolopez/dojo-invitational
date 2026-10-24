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
  `mixamorig:` rig (75 bones, including eye bones). Height was
  normalised to a 1.87 m bind height by setting the armature's object
  scale to 0.00902 — deliberately **not** applied (see the bug below).
  Textures are the character's own embedded 2048 px PBR maps.
- **Call 4 material fix (2026-10-24):** the base character's materials
  exported with metallic factor 0.5, which makes skin and cloth read as
  half-metal. Both materials now export with metallic factor 0; the
  specular texture and roughness (0.553) are unchanged. This does not add
  pore detail or subsurface scattering — those are still absent, see
  limitations below.
- **Call 7 skin fix (2026-10-24):** the shared 2048 px normal map now
  carries fine pore-scale normal detail (blurred two-scale noise blended
  into the existing normal map at low amplitude; the same map feeds skin,
  cloth and hair, because the base character shares one normal map — it
  is not skin-masked). Both materials keep metallic factor 0 and use
  roughness 0.68 (was 0.553 in the base export). A subsurface weight was
  set in Blender but does NOT appear in the exported GLB (the GLB's
  extensions are only KHR_materials_specular), so no subsurface claim is
  made for the delivered file.
- **Call 7 eyes — tried and rejected:** separate eyeball spheres skinned
  to the `mixamorig:Leye`/`Reye` bones were built and rendered in
  three.js, and rejected: they read as protruding balls in front of the
  face, because the head mesh's own painted-eye surface occludes any
  inset sphere. The right eye bone also floats about 2.5 cm in front of
  the face surface in the rest pose (the left sits 0.68 cm from it), so
  a bone-centred right sphere floats even further. The delivered eyes
  are therefore still the base character's painted eyes — see
  limitations. Hair is still the sculpted shell and costume folds are
  still baked into the mesh; neither was changed in this call.

## The bug worth writing down (found and fixed during this build)

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
- Throw (call 4): a throw cannot be blocked, so it is used against a
  blocking foe inside its 0.95 m reach, and occasionally in close range
  when the foe is not mid-strike (a throw misses a foe who is
  mid-strike). Reach 13 dmg per RULES.md §5; the 1.00 s in the brain is
  its own pacing between throws, not an arena stat.
- Clock play in the final 6 s of a round (time > 24 s of a 30 s round):
  protects a lead of 10+ hp, chases a deficit of 10+ with faster
  cooldowns. Escapes the corner instead of backing out. Call 7 fix:
  round time restarts at 0 each round but `memory` persists, so the
  brain now resets its cooldown and foe-throw timestamps when it sees
  time go backwards — the old 42 s threshold could never fire in a
  30 s round.

Pure function, `Math` only — no imports, timers, DOM, storage, or network.

## Honest limitations (stated plainly for the realism judging)

- The mesh is game-resolution (12,609 triangles). Skin detail lives in
  the character's authored PBR textures plus the call-7 pore-scale
  normal detail (shared map, not skin-masked, as above); there is no
  pore-level geometry, no subsurface-scattering profile in the GLB,
  and only the base material's specular extension.
- There are no separate teeth, tongue, or eyeball meshes; the eyes and
  mouth are part of the base character's head mesh and texture. Hair is
  modelled/textured as part of the base character, not strand cards.
- The outfit is part of the base character mesh — no cloth simulation,
  no separate garment meshes.
- The beauty renders in `renders/` are my own three.js studio renders of
  the submitted GLB (neutral environment lighting, ACES), posed in
  `fighting_idle`. They are renders of the file itself — no compositing,
  no AI imagery — but they are not the judge's HDRI renders. One tooling
  note: three.js r160's `SkinnedMesh.computeBoundingBox()` returned
  unusable values for this rig in my headless setup, so the render
  framing uses the fighter's verified dimensions (1.85 m posed height at
  the origin, facing +Z) instead of the computed box.

## Sources and reproducibility

`source/` contains the exact build script (`build_fighter.py`) and the
three.js render page used for `renders/` (`render6.html`, `shot5.mjs`,
`server.py`). The `.blend` working file is not included (66 MB); the GLB
is fully regenerable from the shared FBX assets with the included script.
Asset licences are in `LICENSES.md`.

## Fighter binary delivery

Binaries are not committed (per AGENTS.md), so the judge gets
`fighter.glb` + renders from this archive — it unpacks at the entry
folder's top level (`fighter.glb`, `renders/…`, plus the same text
files as the branch):

- **Archive:** https://muse.ai/files/1280375435168282/1095807963216793/zir1xh1u5vwc1flxuztibkx3/muse-entry-call7.zip
  (26,779,220 bytes, sha256 `03276936f74bfeaff15fa9da03920f98ff82b97809733175b8bb8f6be5f7729b`;
  link expires 2026-10-26 18:05 UTC)
- **fighter.glb inside:** 24,462,932 bytes, sha256
  `a21ea365f2f0bf029c6a555eef2b425e9bdad5e1a58da32835356127d7b23b77`
- The same files are also placed directly in
  `competition/entries/muse/` on the owner's Mac by the owner's
  one-line unpack of this archive, which is where the weigh-in
  snapshots from.

## Validator output

`node validate_entry.mjs muse`, run on this exact entry:

```
PASS  manifest.json has all fields
PASS  file size 24.5 MB (limit 80 MB)
PASS  extensions: KHR_materials_specular
PASS  self-contained (no external URIs)
PASS  4 textures (limit 40)
PASS  largest texture 2048 px (limit 4096)
PASS  12,609 triangles (limit 250,000)
PASS  Mixamo skeleton (all required mixamorig: bones present)
PASS  animations: 30/30
PASS  clip lengths within ±10 % of reference
PASS  bind-pose mesh height ≈ 1.87 m (expected 1.55–2.05 m; check scale if far off)
PASS  brain.js runs in the sandbox, valid outputs, 0.781 ms average (limit 2 ms)
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
animations in total, confirmed by loading it in three.js (posed
`fighting_idle` in frame in all four renders — the same render check as
the first build, so the unapplied-scale export pattern still holds).
