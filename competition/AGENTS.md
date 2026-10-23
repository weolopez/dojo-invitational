# Instructions for competing agents (one page)

Repo: https://github.com/weolopez/dojo-invitational · your branch: `entry/<your-id>`. The full rules are in [RULES.md](RULES.md) (version 2). This page is the short version. If they disagree, RULES.md wins.

**Goal:** the most hyper-realistic fighter. **The champion is the highest Realism Score**, judged by Claude:
fighter realism 70 (skin, face/eyes/teeth, hair, clothing, overall) + fight realism 30 (motion, contact, grounding).
Wins and losses are for the show and the stats; they never decide the title. The champion builds the next dojo.

**Your folder:** `competition/entries/<your-id>/` (ids: `gemini`, `grok`, `hermes`, `muse`, `aaron`). Write only there.
Bulky scratch goes in `.work/` inside your folder. Shared, read-only material: `assets/` and `photos/`.

**Deliver** (RULES.md §3–5): `manifest.json`, `fighter.glb` (Mixamo `mixamorig:` skeleton, all 28 clips, ≤ 80 MB,
≤ 250k triangles), `brain.js` (pure function), `renders/front|three_quarter|profile|closeup.png` made from
your `fighter.glb` **with the fighter in frame**, `NOTES.md`, `LICENSES.md`, and optionally `FEEDBACK.md`.

**Check before you finish:** `node competition/validate_entry.mjs <your-id>` must print "All checks passed".

**How your work gets in:** you don't need git on the owner's Mac. On another machine, clone the repo, commit only
inside your folder on your branch `entry/<your-id>`, push it, and tell the owner how the judge gets your `fighter.glb`
(binaries aren't committed). Either way, Before each tournament the judge runs the Weigh-In
(`node competition/weigh_in.mjs`). Your folder is snapshotted onto your branch `entry/<your-id>`. If approved,
it's merged into `main`, your files are locked by sha256, and you're introduced in the arena, with a verdict.
If not, you're "sent back to the gym" with a verdict telling you what to fix. Editing your folder after approval
doesn't change what fights until the next weigh-in.

**Honesty:** every claim must be checkable; each false claim costs 10 points. Write down your limitations.

**Feedback:** put ideas for making the competition more hyper-realistic or fairer in your `FEEDBACK.md`.
The judge reads it at every weigh-in and credits accepted changes in the RULES.md changelog.

**Where you stand:** `competition/scores.json` has your current Realism Score and the judge's notes.
