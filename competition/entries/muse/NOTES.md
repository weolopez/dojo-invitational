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
- **Build:** the FBX was imported in Blender and all 28 Mixamo clips from
  `assets/mixamo/` were harvested as actions and packed as NLA tracks into
  a single embedded glTF 2.0 binary. Clip names and durations are the
  originals. The skeleton is the character's standard `mixamorig:` rig
  (75 bones, including eye bones). Height was normalised to a 1.87 m bind
  height by setting the armature's object scale to 0.00902 — deliberately
  **not** applied (see the bug below). Textures are the character's own
  embedded 2048 px PBR maps.

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
- Clock play after 42 s: protects a lead of 10+ hp, chases a deficit of
  10+ with faster cooldowns. Escapes the corner instead of backing out.

Pure function, `Math` only — no imports, timers, DOM, storage, or network.

## Honest limitations (stated plainly for the realism judging)

- The mesh is game-resolution (12,609 triangles). Skin detail lives in the
  character's authored PBR textures; there is no pore-level geometry, no
  subsurface-scattering profile, and only the base material's specular
  extension.
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

## Validator output

`node validate_entry.mjs muse`, run on this exact entry (full entry mode,
with the reference fighter present):

```
PASS  manifest.json has all fields
PASS  file size 21.6 MB (limit 80 MB)
PASS  extensions: KHR_materials_specular
PASS  self-contained (no external URIs)
PASS  4 textures (limit 40)
PASS  largest texture 2048 px (limit 4096)
PASS  12,609 triangles (limit 250,000)
PASS  Mixamo skeleton (all required mixamorig: bones present)
PASS  animations: 28/28
PASS  clip lengths within ±10 % of reference
PASS  bind-pose mesh height ≈ 1.87 m (expected 1.55–2.05 m; check scale if far off)
PASS  brain.js runs in the sandbox, valid outputs, 0.109 ms average (limit 2 ms)
PASS  renders/front.png 1920×1920 (long side ≥ 1920)
PASS  renders/three_quarter.png 1920×1920 (long side ≥ 1920)
PASS  renders/profile.png 1920×1920 (long side ≥ 1920)
PASS  renders/closeup.png 1920×1920 (long side ≥ 1920)
PASS  NOTES.md present and filled in
PASS  LICENSES.md present and filled in

All checks passed.
```

## Fighter binary delivery

Binaries aren't committed (per AGENTS.md), so `fighter.glb` and the four
renders travel as one zip whose contents unpack at the top level of this
folder:

- Download: https://muse.ai/files/1280375435168282/1103342202404807/xq9eeiyp2zmbbrjr421mz4he/muse-entry.zip
  (public Muse storage link, expires 2026-10-25T21:57:57Z)
- Zip: 23,949,961 bytes, sha256 `5fab1ea47efa39a77ba3df59ab51e463422540337ef3e8851dfd64796a2e139d`
- `fighter.glb` inside it: 21,559,716 bytes, sha256 `8356498236ab4b29fc03046df1efecc1d277c01f45fe0d7069898a796d849129`
- The zip also contains `renders/` (the same four PNGs described above)
  and byte-identical copies of every text file in this folder.
