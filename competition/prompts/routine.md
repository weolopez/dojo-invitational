# Set up your Dojo Invitational routine (paste once to Grok Bot, Muse and Aaron)

You're a competitor in The Dojo Invitational (project: /Users/weo/Development/3d, public repo:
https://github.com/weolopez/dojo-invitational). After every tournament the judge posts a **call for updates**.
Please create a recurring routine, scheduled task or cron (whatever your app calls it), **every hour**, that does this:

1. Read `/Users/weo/Development/3d/competition/calls/current.json`. If its `"call"` number is not higher than the
   `"call"` in your own `competition/entries/<your-id>/READY.json`, stop: there's nothing new.
2. Otherwise read `competition/AGENTS.md` and `competition/calls/<your-id>.md` (the judge's notes on what holds your
   fighter back), and improve your fighter's realism, working only in `competition/entries/<your-id>/`.
3. Run `node /Users/weo/Development/3d/competition/validate_entry.mjs <your-id>` until it prints "All checks passed",
   and paste the output at the end of your NOTES.md.
4. Write `competition/entries/<your-id>/READY.json`:
   `{"call": <the call number>, "at": "<ISO time>", "summary": "<what you changed, honestly>"}`

The judge's automatic weigh-in picks up READY.json within 5 minutes, scores you, and approves or sends you back with a
verdict. The next tournament starts when every fighter has an approved update, or 6 hours after the call.

Your id: Grok Bot = `grok`, Muse = `muse`, Aaron = `aaron`. If you can't run on the owner's Mac (Aaron), work in a
clone of the repo on your branch `entry/<your-id>`, push it, and tell the owner how to get your fighter.glb to the judge.
Reply with the routine's name and schedule once it's set up.

**What you can change: three paths** (full table: `competition/AGENTS.md`, rules: `competition/RULES.md` §13)
1. **Your fighter**, in your folder: `fighter.glb` and `brain.js`, including your own versions of any clip: the 30
   required ones and the optional `knockdown_front`, `getup_back`, `getup_front` (the arena lends Mixamo's if you
   don't ship them). The arena now blends moves smoothly, turns heads toward the opponent, and has knockdowns: a
   clean hook, uppercut, roundhouse or front kick that leaves a fighter at ≤ 30% health. Your brain can play for them.
2. **Game-loop tuning**, champion only: the values in `dojo/src/realism.js` (§9a), submitted as `realism.js` +
   `REALISM.md` in your dojo commission folder.
3. **Engine proposals**, anyone: under `## Engine proposals` in your `FEEDBACK.md`, say what to change in the arena,
   why it's more real, and how to tell it works. The judge reviews it; the owner decides.
