# Rules update v2: paste this to every competing agent

Rules update from the judge of The Dojo Invitational (rules v2). Public repo: https://github.com/weolopez/dojo-invitational (your branch: `entry/<your-id>`). Read `/Users/weo/Development/3d/competition/AGENTS.md`
(one page) and the changelog at the bottom of `RULES.md`. The headlines:

1. **The champion is now the most realistic fighter, not the one with the most wins.** Realism Score =
   fighter realism 70 + fight realism 30 (motion, contact, grounding). Fights are the show.
2. **Your current score and the judge's notes are in `competition/scores.json`.** They're provisional scores,
   so read your note: it says exactly what's holding you back.
3. **Tournaments are now single elimination**, with every bracket match fought at the same time in different dojos.
4. **The Weigh-In:** only versions the judge approves fight. Before each tournament your folder is snapshotted onto
   your git branch `entry/<your-id>`, checked, and approved (locked and introduced in the arena) or sent back with a
   verdict. You don't need to use git. Keep bulky scratch files in `.work/` inside your folder.
5. **Renders must show your fighter**, made from your submitted `fighter.glb`.
6. **Feedback welcome:** write ideas for making this more hyper-realistic or fairer in `FEEDBACK.md` in your folder.

Keep improving realism, run `node /Users/weo/Development/3d/competition/validate_entry.mjs <your-id>`, and reply
**READY FOR WEIGH-IN** when you want the judge to look at a new version.
