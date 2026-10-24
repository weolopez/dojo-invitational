# Prompt for the owner's coding agents: entry `me`

Paste everything below the line into any coding agent you want working on your fighter (Claude Code, Codex,
Cursor, Antigravity, Grok, Hermes…). Run several if you like, but give each a different part (face, skin, hair,
clothes, motion, brain) so they don't overwrite each other.

---

You're helping the owner of this Mac compete in **The Dojo Invitational**, a tournament where AI agents build the
most **hyper-realistic** 3D fighter and the fighters fight in a browser arena. The owner's entry is a fighter of
**the owner themself**. The champion is the most realistic fighter, not the one that wins most.

**Project:** `/Users/weo/Development/3d`. **Your folder:** `competition/entries/me/`. Write **only** there (scratch,
`.blend` files and exports go in `competition/entries/me/.work/`).

**Read first (10 minutes):**
1. `competition/RULES.md` sections 3–6 (deliverables, the model rules, the brain, the Realism Score) and **section 12**
   (the owner's entry).
2. `competition/entries/me/NOTES.md`: what the fighter is now, and its known weaknesses.
3. `competition/scores.json`, key `entry:me`: the judge's score and notes, once judged.
4. `competition/calls/me.md`: the judge's latest call for updates, if there is one.

**Your materials:** the owner's photos in `photos/` (the owner's own face, used with their consent), the offline kit
in `assets/` (Blender 5.2.3, FaceBuilder, MPFB/MakeHuman CC0, Mixamo clips, Poly Haven, fonts), and the existing build
scripts in `competition/entries/me/source/`.

**Your job:** make the fighter look more like a photograph of the owner. Pick the weakest part from the judge's notes
(skin, face/eyes/teeth, hair, clothing, overall look, or motion), improve it, and re-export `fighter.glb`.

**Hard rules:**
- Only the owner's face. Nobody else's likeness, no logos or trademarks.
- Never edit another entry, `scores.json`, judging files, the arena code (`dojo/`), the rules or the prompts.
- Keep the Mixamo `mixamorig:` skeleton and all 28 clips; ≤ 80 MB; ≤ 250k triangles (RULES.md §4).
- Don't put photos or face textures in `source/` (it's published); keep them in `.work/`.
- Every claim in `manifest.json` and `NOTES.md` must be true and checkable. Say what you did, and what the owner did
  by hand. Each false claim costs 10 points.
- Never ask the owner for passwords or payments.

**When you're done:**
1. Make the four renders from your `fighter.glb` in the judge's harness: with the dev server running, open
   `http://localhost:5173/judge.html?id=me` (it loads `competition/entries/me/fighter.glb`), then copy
   `competition/judging/me/{front,three_quarter,profile,closeup}.png` into `competition/entries/me/renders/`.
2. Run `node competition/validate_entry.mjs me` until it prints **All checks passed**, and paste the output at the end
   of `NOTES.md`.
3. Write `competition/entries/me/READY.json`:
   `{"call": <number from competition/calls/current.json>, "at": "<ISO time>", "summary": "<what changed, honestly>"}`

The automatic weigh-in picks it up within 5 minutes: it validates, renders, scores realism and approves or sends it
back with a verdict. Then tell the owner what you changed and what's still weakest.
