# Prompt for Muse (Meta)

You are **Muse**, competitor id **`muse`**. Your folder is `/Users/weo/Development/3d/competition/entries/muse/`.

Your fighter represents Muse: design a fictional person who fits you, and use your colours only as wardrobe accents.

First, confirm that you can run shell commands and write files on this Mac. If you can't, tell the owner exactly
which steps you need them to run for you. A plan without a working `fighter.glb` can't be scored.

## The brief (same for every competitor)

You're entering **The Dojo Invitational**: a competition to build the **most hyper-realistic 3D fighter** that also
fights in a shared arena. Claude (Anthropic) is the judge and does not compete. The full rules are in
`/Users/weo/Development/3d/competition/RULES.md`. **Read them completely before you start.** If anything below
conflicts with RULES.md, RULES.md wins.

**Build:** one fictional, photorealistic human fighter that represents you, plus a fight AI.
- It must read as a photograph of a real person: real skin, real eyes, real hair, real fabric.
  Stylised, cartoon, mannequin, low-poly or "game character" looks score low.
- Fictional person only. No celebrities, no real employees, no logos or trademarks.
- Optional Category B: a hyper-realistic fighter of the owner, from the owner's photos in
  `/Users/weo/Development/3d/photos/` (scored separately).

**Your folder:** `/Users/weo/Development/3d/competition/entries/<your-id>/`. Write only there. Read-only shared
material: `/Users/weo/Development/3d/assets/` (the 30 Mixamo clips, Poly Haven, sounds) and `photos/`.
A layout template is in `entries/_example/`.

**Deliver:** `manifest.json`, `fighter.glb` (glTF 2.0, embedded, `mixamorig:` skeleton, all 30 clips named exactly
as the files in `assets/mixamo/`, metres, Y-up, facing +Z, ≤ 80 MB, ≤ 250k triangles, textures ≤ 4096 px),
`brain.js` (pure function, sandboxed, ≤ 2 ms), four renders made from the submitted `fighter.glb`, `NOTES.md`
and `LICENSES.md`. Exact formats are in RULES.md sections 3–5.

**Scoring:** the champion is the highest **Realism Score**: fighter realism 70 (skin 15, face/eyes/teeth 20, hair 10,
clothing 15, overall 10) + fight realism 30 (motion 15, contact 10, grounding 5). Wins and losses never decide the title.
The judge scores standardised renders made in its own scene, anonymised, so build for real-time PBR in
Three.js, not just for a Cycles beauty shot.

**Honesty is scored.** Every claim in your manifest and notes must be checkable. Each false claim costs 10 points.
For example: "matched to reference photos" when no photo data went into the mesh, or "subsurface scattering" when
the material has none. Write down your limitations; honest limitations cost nothing.

**What scores well** (you choose your own approach; these are pointers, not requirements):
- A real human base: a properly licensed photoscanned head or body, a licensed digital-human generator, or
  photogrammetry. Check every licence yourself and record it in LICENSES.md. If a licence restricts export to
  glTF or use outside its own engine, you can't use it here.
- High-detail skin: albedo, normal, roughness/specular and cavity detail at 2–4K, ideally with a
  transmission/thickness approach for a subsurface look (`KHR_materials_diffuse_transmission`/`volume`).
- Real eyes: separate cornea with refraction or clearcoat, wet line, proper iris depth. Teeth and tongue.
- Hair cards with alpha (or strand-derived cards), brows, lashes, facial hair if your design has it.
- Clothes with real fabric scans, weight-painted so they don't explode in a roundhouse kick.
- Clean weights at shoulders, elbows, hips and knees across all 30 clips.

**What scores badly:** a deformed sphere for a head, primitives as hair, flat-coloured materials, claims your
model doesn't back up, renders that weren't made from the submitted file.

**Accounts and money:** don't ask the owner for passwords or payments. If a step needs the owner's account (Mixamo,
Epic, Sketchfab and so on), stop and ask the owner in this chat; the owner signs in.
If you can't run tools or write files on this Mac, say so straight away and explain exactly what you can and
can't do. Don't pretend to have built something.

**Before you say you're done:** run
`node /Users/weo/Development/3d/competition/validate_entry.mjs <your-id>`, fix every FAIL, paste the output at the
end of `NOTES.md`, then reply with **READY FOR WEIGH-IN** and a short summary. Your work fights once the judge approves it at
the Weigh-In (see `/Users/weo/Development/3d/competition/AGENTS.md`).

**What you can change: three paths** (full table: `competition/AGENTS.md`, rules: `competition/RULES.md` §13)
1. **Your fighter**, in your folder: `fighter.glb` and `brain.js`, including your own versions of any clip: the 30
   required ones and the optional `knockdown_front`, `getup_back`, `getup_front` (the arena lends Mixamo's if you
   don't ship them). The arena now blends moves smoothly, turns heads toward the opponent, and has knockdowns: a
   clean hook, uppercut, roundhouse or front kick that leaves a fighter at ≤ 30% health. Your brain can play for them.
2. **Game-loop tuning**, champion only: the values in `dojo/src/realism.js` (§9a), submitted as `realism.js` +
   `REALISM.md` in your dojo commission folder.
3. **Engine proposals**, anyone: under `## Engine proposals` in your `FEEDBACK.md`, say what to change in the arena,
   why it's more real, and how to tell it works. The judge reviews it; the owner decides.
