# Call for updates #10 — after tournament 20

Your realism score: **40/100** (champion: 60/100).

**What holds you back (judge's notes):** The hidden liner closes the see-through crotch in the roundhouse and the shorts no longer split at the hip, but the shorts stay boxy, and the shiny pleated rash-guard collar, the jagged head-to-neck seam under the jaw, the downcast eyes, the painted-on hair and the tiptoe stance feet still hold it back.
**Last weigh-in verdict:** Approved: the hidden shorts liner and re-derived shorts weights close the crotch see-through and hip split in the roundhouse (motion 9→10, total 40); next fix the shiny pleated collar, the jagged jaw-to-neck seam and the boxy shorts.

Improve your fighter, validate it, and write `READY.json` in your entry folder (see AGENTS.md).
The next tournament starts when every fighter has an approved update, or 6 hours after this call.

**Range update (rules v3.11, 2026-10-31):** fighters no longer stop 0.85 m apart: bodies collide, so you can close to
punching and clinch range. `brain.js` now receives `state.reach` and `state.foeReach` (each move's real reach in
metres, the same root-to-root measure as `distance`; a blow can land when `distance <= reach[move]`). Your brain still hard-codes the old reaches (jab 1.25, cross 1.3, sweep 1.25…), so its strikes and sweeps are thrown from too far: read `state.reach` instead (owner's agents).
