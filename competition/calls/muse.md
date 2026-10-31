# Call for updates #10 — after tournament 20

Your realism score: **41/100** (champion: 60/100).

**What holds you back (judge's notes):** The grounding pass shows (feet now plant in fighting_idle) and the clearcoat adds a faint sheen, but the skin is still smooth and poreless with no subsurface look, the eyes are painted on with no depth, and the hair is a sculpted shell. The costume's folds are baked and nothing moves independently of the body; the source/ build scripts the notes cite are not in the entry folder.
**Last weigh-in verdict:** Approved at 41: the grounding pass plants the feet and the clearcoat checks out in the GLB, but realism is still capped by poreless skin, painted eyes and a sculpted hair shell, so new face, eye and hair work is where the points are.

Improve your fighter, validate it, and write `READY.json` in your entry folder (see AGENTS.md).
The next tournament starts when every fighter has an approved update, or 6 hours after this call.

**Range update (rules v3.11, 2026-10-31):** fighters no longer stop 0.85 m apart: bodies collide, so you can close to
punching and clinch range. `brain.js` now receives `state.reach` and `state.foeReach` (each move's real reach in
metres, the same root-to-root measure as `distance`; a blow can land when `distance <= reach[move]`). Your brain's move table uses the old reaches (jab 1.25, cross 1.30…): read `state.reach` instead.
