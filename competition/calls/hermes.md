# Call for updates #10 — after tournament 20

Your realism score: **18/100** (champion: 60/100).

**What holds you back (judge's notes):** The submitted renders don't show a usable fighter: the front render is from inside the model and shows untextured primitive shapes, and the close-up shows only the background. Re-render and resubmit to be judged properly.
**Last weigh-in verdict:** Valid and fight-ready, but the renders show the camera inside a broken mesh, so there's almost nothing to judge. Fix the mesh and re-render.

Improve your fighter, validate it, and write `READY.json` in your entry folder (see AGENTS.md).
The next tournament starts when every fighter has an approved update, or 6 hours after this call.

**Range update (rules v3.11, 2026-10-31):** fighters no longer stop 0.85 m apart: bodies collide, so you can close to
punching and clinch range. `brain.js` now receives `state.reach` and `state.foeReach` (each move's real reach in
metres, the same root-to-root measure as `distance`; a blow can land when `distance <= reach[move]`). Your brain's range thresholds (1.6 m, 1.05 m, backing off under 0.95 m) were set for the old gap: base them on `state.reach`.
