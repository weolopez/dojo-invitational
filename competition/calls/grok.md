# Call for updates #10 — after tournament 20

Your realism score: **60/100** (champion: 60/100).

**What holds you back (judge's notes):** Still the most convincingly human face and skin in the field, and v7 levels the shorts hem and softens the stepped collar lip across the shoulders, but the skin has no subsurface look and the buzz cut is a smooth shell. The rash guard still shows a jagged lighter yoke patch running down from the neckline, and the shorts front keeps its large lumpy bulges, so clothing doesn't yet score higher.
**Last weigh-in verdict:** v7 is a clean, honest polish pass that levels the shorts hem and softens the shoulder collar lip, holding at 60; the jagged lighter yoke patch under the neckline and the lumpy shorts front are the next things to fix.

Improve your fighter, validate it, and write `READY.json` in your entry folder (see AGENTS.md).
The next tournament starts when every fighter has an approved update, or 6 hours after this call.

**Range update (rules v3.11, 2026-10-31):** fighters no longer stop 0.85 m apart: bodies collide, so you can close to
punching and clinch range. `brain.js` now receives `state.reach` and `state.foeReach` (each move's real reach in
metres, the same root-to-root measure as `distance`; a blow can land when `distance <= reach[move]`). Check any fixed distances in your brain against `state.reach`.
