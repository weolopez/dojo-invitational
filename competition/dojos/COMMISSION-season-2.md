# Dojo commission: season 2

To: **GROK** (competitor id `grok`)
From: the judge of The Dojo Invitational

GROK is the most realistic fighter in tournament 1 of the Dojo Invitational, with a judge's realism score of 55/100. (GROK won the bracket, but the title goes to realism, not wins.)

**You've earned the right to build the hyper-realistic dojo that every fight of the next season takes place in.**

Final standings for season 1:

| # | Fighter | Realism score | Tournament result |
|---|---|---|---|
| 1 | GROK | 55 / 100 | won the bracket |
| 2 | GEMINI | 45 / 100 |  |
| 3 | HERMES | 18 / 100 |  |

## Your brief

Build one **photorealistic fighting dojo**: the kind of place a stranger would take for a photograph of a real,
lived-in training hall. You choose the concept (a traditional dojo at dawn, a rain-soaked rooftop gym, a
concrete warehouse with skylights, a mountain temple hall), within the rules below. It should feel like your
fighter's home ground.

Read `/Users/weo/Development/3d/competition/RULES.md` first. **Section 9 is your spec**, and it wins over anything
here.

**Your folder:** `/Users/weo/Development/3d/competition/dojos/season-2-grok/`.
Write only there. Don't touch your fighter entry while you build.

**Must-haves:**
- A clear fight lane: x ∈ [−4.5, 4.5], y ∈ [0, 2.6], z ∈ [−1.2, 1.2] m, floor top at exactly y = 0, fighters along x.
  The camera sits around z = +4…+8, y = 1.6, looking toward −z, so dress the back and sides and keep z > +2 open.
- `dojo.glb` (glTF 2.0, embedded, metres, Y-up, ≤ 150 MB, ≤ 1.5 M triangles, textures ≤ 4096 px), an optional
  `sky.hdr`, `manifest.json` (exact fields in RULES.md §9), `renders/wide.png` and `renders/detail.png` made from the
  submitted files, `NOTES.md`, and `LICENSES.md` listing every asset with its source and licence.
- ≥ 50 fps with two fighters at 1920×1080 in Chrome on this Mac.
- Fictional or generic place only. No logos, trademarks or recognisable real venues.

**What reads as real:** scanned or high-quality PBR materials (worn wood, tatami, plaster, concrete) at real-world
scale; believable light sources with soft shadows (bake lighting into lightmaps or vertex colours if needed for
speed); clutter with purpose, like mats, a weapon rack, towels, a water bottle, scuffs and dust; and correct
proportions (doors about 2.1 m, ceilings 3–5 m).

**Honesty is scored:** every claim must be checkable, and each false one costs points.

**When you're done:** run
`node /Users/weo/Development/3d/competition/validate_entry.mjs --dojo /Users/weo/Development/3d/competition/dojos/season-2-grok`,
fix every FAIL, paste the output at the end of `NOTES.md`, and reply **DOJO COMPLETE**. The arena picks it up
automatically at the start of the next season after it passes.
