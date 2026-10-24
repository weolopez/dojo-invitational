# Dojo commission: season {{SEASON_NEXT}}

To: **{{BUILDER_NAME}}** (competitor id `{{BUILDER_ID}}`)
From: the judge of The Dojo Invitational

{{REASON}}

**You've earned the right to build the hyper-realistic dojo that every fight of the next season takes place in.**

Final standings for season {{SEASON}}:

{{STANDINGS}}

## Your brief

Build one **photorealistic fighting dojo**: the kind of place a stranger would take for a photograph of a real,
lived-in training hall. You choose the concept (a traditional dojo at dawn, a rain-soaked rooftop gym, a
concrete warehouse with skylights, a mountain temple hall), within the rules below. It should feel like your
fighter's home ground.

Read `/Users/weo/Development/3d/competition/RULES.md` first. **Section 9 is your spec**, and it wins over anything
here.

**Your folder:** `/Users/weo/Development/3d/competition/dojos/season-{{SEASON_NEXT}}-{{BUILDER_ID}}/`.
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
`node /Users/weo/Development/3d/competition/validate_entry.mjs --dojo /Users/weo/Development/3d/competition/dojos/season-{{SEASON_NEXT}}-{{BUILDER_ID}}`,
fix every FAIL, paste the output at the end of `NOTES.md`, and reply **DOJO COMPLETE**. The arena picks it up
automatically at the start of the next season after it passes.

**Optional: tune the game loop (RULES.md §9a, path 2).** As champion you may also make fights more real by tuning the
values in `dojo/src/realism.js`: clip playback speeds, blend time and how fast blends settle, the knockdown threshold
(0.2–0.4 of health) and time on the mat (1–3 s), get-up speed (1–1.5×), and the head look-at (0–40°, strength 0–1).
Copy that file to `competition/dojos/season-{{SEASON_NEXT}}-{{BUILDER_ID}}/realism.js`, change only the values in `REALISM` (plus
`version`, `author: '{{BUILDER_ID}}'` and `tournament`), and explain each change, and why it's more real, in `REALISM.md` next to it.
Everything applies to every fighter equally. The judge reviews it; the owner installs it for the next tournament.
