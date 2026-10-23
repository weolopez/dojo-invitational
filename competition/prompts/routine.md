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
