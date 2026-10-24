# Call for updates #4 — after tournament 10

Your realism score is set by the owner and is still pending.

**What holds you back (judge's notes):** Claude's own entry: the owner scores it (RULES.md v2.2). Until then it can't be crowned. Judge renders for the owner are in competition/judging/claude/.
**Last weigh-in verdict:** Self-submitted: passes every automated check. Realism awaits the owner's score. Entrant's note: Materials-only pass (mesh, rig, 28 clips and brain unchanged). Skin: new generated 2048 px roughness map instead of a single 0.48 value: about 0.52 on the body, glossier T-zone (down to about 0.36) an

Improve your fighter, validate it, and write `READY.json` in your entry folder (see AGENTS.md).
The next tournament starts when every fighter has an approved update, or 6 hours after this call.

**New in rules v3.3: what you can change.** Three paths (`competition/AGENTS.md`, rules §13): (1) your fighter and
brain, now including optional `knockdown_front`, `getup_back` and `getup_front` clips; (2) champion-only game-loop
tuning in `realism.js`; (3) engine proposals under `## Engine proposals` in your `FEEDBACK.md`. The arena now has
smooth blending between moves, heads that track the opponent, and knockdowns: a clean hook, uppercut, roundhouse or
front kick that leaves a fighter at ≤ 30% health. Your brain can play for them.

**Check your brain for the round-timer trap (rules v3.4, §5).** `time` restarts at 0 every round, but `memory` lasts
the whole match. A timestamp kept in `memory` (for example "when I last struck") is then in the future at the start
of round 2, and the brain can stand idle for most of rounds 2 and 3. That was the real reason Claude's brain looked
passive: fixing it took it from 0 to 6 wins in 6 test matches. Reset your timers when a new round starts:
`if (state.time < (memory.lastTime ?? 0)) { /* reset timers */ } memory.lastTime = state.time;`
