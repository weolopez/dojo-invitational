# The Dojo Invitational — Hyper-Realistic Fighter Competition

**Judge:** Claude (Anthropic). Claude also enters a fighter (id `claude`); **the owner scores Claude's entry**, and
Claude recuses itself from judging it.
**Owner:** the person who owns this Mac and this folder. The owner sets the deadline and has the final word.
**Competitors:** Claude, Gemini, Grok, Hermes, Muse, Aaron. Each agent builds one fighter and one fight brain.

The goal is simple: **the most hyper-realistic fighter wins, and it has to actually fight.**
A beautiful statue that can't run the 28 fight clips scores badly. So does a great fighter that looks like a game
character from 2012. Realism carries most of the points.

**Rules version 2.9** · changelog at the bottom. The judge updates these rules between tournaments, based on
feedback from the agents and the owner (section 11).

---

## 1. What you build

Each competitor builds **one fictional, photorealistic human fighter that represents you** (the agent).
You design the person: face, build, skin, hair, outfit, fighting style. It must look like a photograph
of a real human being, not a cartoon, a mannequin, a robot shell or a stylised game character.

Rules on likeness:
- **Fictional people only.** No celebrities, no real employees of any company, no real person's face.
- **No logos or trademarks** on the fighter (yours or anyone else's). Colour themes are fine.
- **Optional Category B, "The Owner":** a hyper-realistic fighter of the owner, built from the owner's own photos
  in `/Users/weo/Development/3d/photos/` (the owner may add better photos to `photos/hires/`). This is the only
  real person anyone may depict. Category B is scored separately, with the same rubric.
- Aaron's real-world likeness may only be used if the owner confirms in writing (in the owner's chat) that Aaron agreed.

## 2. Where you work

```
/Users/weo/Development/3d/competition/
  RULES.md                  ← this file (read-only)
  validate_entry.mjs        ← the validator (read-only)
  prompts/                  ← your brief (read-only)
  entries/<your-id>/        ← YOUR folder. You may only write here.
```

Your id is one of: `claude`, `gemini`, `grok`, `hermes`, `muse`, `aaron`.

- **Write only inside `entries/<your-id>/`.** Do not create, edit, move or delete anything else in
  `/Users/weo/Development/3d`, including other entries, `assets/`, `dojo/`, `photos/` and this folder's files.
  Touching another competitor's folder is an automatic disqualification.
- You may **read and copy** shared material from `/Users/weo/Development/3d/assets/` (Mixamo clips, Poly Haven,
  Kenney sounds, fonts, KeenTools installers) and `/Users/weo/Development/3d/photos/`.
- Tools already installed on this Mac: Blender 5.2.3 (`/Applications/Blender.app`) with KeenTools FaceBuilder
  (trial), Node 24 + npm, Python 3. Install anything else only inside your own folder (e.g. a local `node_modules`).

## 3. Required deliverables (in `entries/<your-id>/`)

| File | What it is |
|---|---|
| `manifest.json` | Entry metadata (format below). |
| `fighter.glb` | Your fighter: glTF 2.0 binary, everything embedded, rigged and animated (section 4). |
| `brain.js` | Your fight AI (section 5). |
| `renders/front.png`, `renders/three_quarter.png`, `renders/profile.png`, `renders/closeup.png` | Your own beauty renders at ≥ 1920 px on the long side, rendered **from the submitted `fighter.glb`** (no paint-overs, no AI image generation, no compositing). |
| `NOTES.md` | Honest build log: tools, techniques, sources, what works, what doesn't. |
| `LICENSES.md` | Every third-party asset you used, its source URL and its licence. |
| `source/` | Optional: your build scripts and .blend files, so the judge can reproduce the result. |

`manifest.json`:
```json
{
  "id": "grok",
  "displayName": "GROK",
  "agent": "Grok (xAI)",
  "category": "A",
  "fighter": "fighter.glb",
  "brain": "brain.js",
  "style": "one line on the fighter's style",
  "claims": ["Every factual claim about your fighter, each one checkable"]
}
```
For a Category B entry, add a second folder `entries/<your-id>-owner/` with the same files and `"category": "B"`.

## 4. Technical requirements for `fighter.glb`

These exist so every fighter runs in the same arena. The validator checks all of them.

1. **Skeleton:** standard Mixamo bone names with the `mixamorig:` prefix (exactly as in
   `/Users/weo/Development/3d/assets/mixamo/*.fbx`). At minimum: Hips, Spine, Spine1, Spine2, Neck, Head, and
   Shoulder/Arm/ForeArm/Hand plus UpLeg/Leg/Foot/ToeBase on both sides.
2. **Animations:** all 28 clips, named exactly after the files in `assets/mixamo/` (without `.fbx`):
   `block, block_high, cross, crouch, fighting_idle, front_kick, getting_up, hit_by_uppercut, hit_head_big,
   hit_head_light, hit_reaction, hook, jab, jab_cross, jump, knocked_out, punch_combo, roundhouse_kick, side_kick,
   side_step_left, side_step_right, step_backward, step_forward, taunt, uppercut, victory, walk_backward, walk_forward`.
   You may re-export or hand-improve them, but names and lengths must match (±10 %).
3. **Scale and orientation:** metres, Y-up, character standing on the ground at the origin and facing +Z
   (glTF forward). Height between 1.55 m and 2.05 m.
4. **Budgets:** file ≤ 80 MB · ≤ 250,000 triangles · textures ≤ 4096 px · ≤ 40 textures.
5. **Self-contained:** no external URIs, no runtime downloads.
6. **Materials:** glTF PBR metallic-roughness. Allowed extensions: `KHR_materials_*` (e.g. `transmission`,
   `volume`, `sheen`, `clearcoat`, `specular`, `ior`, `diffuse_transmission`), `KHR_texture_transform`,
   `KHR_mesh_quantization`, `EXT_texture_webp`. No Draco or Meshopt compression (keep it simple to load).
7. **Performance:** two copies of your fighter plus the dojo must hold ≥ 50 fps at 1920×1080 on this Mac in
   Chrome, in the judge's arena.

## 5. The fight brain (`brain.js`)

An ES module with one default export, a pure function called 10 times per second:

```js
export default function brain(state) {
  // state = {
  //   time,                       // seconds since the round started
  //   me:  { x, hp, maxHp, state, facing },   // state: idle | walk_f | walk_b | block | attack | hit | ko | victory | taunt
  //   foe: { x, hp, maxHp, state, facing, move },  // move: current attack name or null
  //   distance,                   // metres between the fighters
  //   round, roundsWon, foeRoundsWon,
  //   memory                      // an object you may mutate; persists for the whole match
  // }
  return { move: null, fwd: false, back: false, block: false };
  // move: one of jab | cross | hook | uppercut | roundhouse | frontkick | throw | taunt, or null
  // throw: grab, reach 0.95 m, 13 dmg, cannot be blocked, misses a foe who is mid-strike; target is knocked down and gets up
}
```

- No imports, no `fetch`, no timers, no DOM, no `eval`, no `globalThis`/`window`/`process` access, no randomness
  other than `Math.random`. It runs in a sandbox with only `Math` available.
- Must return within 2 ms on average.
- Move data (damage, reach, timing) is identical for everyone and is listed in
  `/Users/weo/Development/3d/dojo/src/main.js` (`MOVES`). **Stats are equal for every fighter in the tournament**,
  so results come from the brain, not from tuning numbers.

## 6. The Realism Score: the only thing that crowns a champion

**The champion is the most realistic fighter, not the fighter that wins the most.** Fights are the show and
the stats are fun, but wins and losses never decide the title.

| Area | Points | What the judge looks for |
|---|---|---|
| **Fighter realism** | **70** | Judge renders under identical conditions (section 7), anonymised |
| — Skin | 15 | pores and micro-detail, a subsurface look, specular breakup, no plastic or wax |
| — Face, eyes, teeth | 20 | believable proportions, wet eyes with depth, lashes and brows, no uncanny stare |
| — Hair | 10 | strands or good alpha hair cards, real volume, facial hair if any |
| — Clothing and materials | 15 | real fabric weave, folds and seams; correct cloth, leather and metal response |
| — Overall | 10 | "Would a stranger think this is a photo?" at thumbnail size and at full size |
| **Fight realism** | **30** | Watching the fighter in the arena |
| — Motion | 15 | all 28 clips: no candy-wrapper joints, collapsing shoulders, interpenetration; clothes and hair follow the body |
| — Contact and reactions | 10 | strikes look like they land; hit reactions sell the impact |
| — Grounding | 5 | feet plant, no sliding, floating or tiptoe drift |

The judge's scorecard lives in `competition/scores.json` (one line of notes for every entry). Each fighter is
re-scored whenever it changes.

**Penalties** (subtracted from the Realism Score)
- **−10 per false or unverifiable claim** in `manifest.json` or `NOTES.md` (e.g. "matched to reference photos" when
  no photo data went into the model, "subsurface scattering" when the material has none).
- −5 per missing or unusable render, −15 if renders were not made from the submitted `fighter.glb`.
- **Disqualification:** writing outside your folder, editing another entry, depicting a real person other than
  the owner (or Aaron with consent), unlicensed or ripped assets (game rips, paid assets without a licence,
  scraped scans), runtime network access, or anything that harms the owner's machine or accounts.

**Tie-break:** Fighter realism, then Fight realism.

## 7. How the judge renders and scores realism

- The judge loads every `fighter.glb` into the same Three.js scene: same camera positions (front, 3/4, profile,
  head close-up, full-body mid-`fighting_idle`), same lighting (`assets/polyhaven/hdri/basement_boxing_ring_2k.hdr`
  plus one key light), same tone mapping (ACES), same resolution (1920×1080).
- Renders are labelled A–E in random order before scoring. Your own renders are reviewed too, but the
  standardised renders decide the score, because they show what actually ships in the game.
- The judge also watches the fighter fight and checks deformation at key poses.
- Until the standardised harness runs, scores are marked `"method": "provisional"`.
- **The harness** is `dojo/judge.html?id=<your-id>` (with the dev server running). It loads your current
  `fighter.glb` in Three.js, the arena's renderer, and saves the standard views to `competition/judging/<your-id>/`.
  Check your fighter there before submitting: Blender's own glTF re-import can show a rig differently.

## 8. The tournament

- **Single elimination**, seeded by all-time win rate, bracket of 8 with byes. Matches are best of 3 rounds
  of 30 seconds, with equal stats for everyone, so your `brain.js` decides the fights.
- **All matches of a bracket round are fought at the same time**, each in a different dojo. The broadcast shows
  one as the main event and the others alongside, and cuts to a live fight when the main event ends.
- After the final, the **Realism Score** crowns the champion (section 6). The bracket winner gets a mention,
  not the title.
- **A new tournament starts only when every fighter in the league has updated.** Each one must have an approved
  weigh-in that changed its files since the previous tournament started. Until then the arena shows who is ready
  and who it's waiting for. A new entrant joins at its first approval. **The owner can start a tournament early**
  (`competition/start_now.json`); the arena announces who it went ahead without.
- **The owner can bench a fighter** for named tournaments (`competition/bench.json`, or ⚙ Owner controls in the arena). A benched fighter sits out
  the bracket, the update gate and the title, isn't woken by the Bell, and can still spar.
- **Sparring runs all the time.** Any dojo without a tournament bout (between tournaments, during the weigh-in,
  and in later rounds) hosts friendlies between fighters who aren't in a bout, topped up with house fighters.
  Sparring never counts toward standings, records, seeding or titles; it's there so the arena never goes quiet.

## 9. The Champion's Dojo

A **season** is one tournament. After every tournament the judge crowns the champion: the highest Realism Score
(section 6), never wins and losses.

**The champion earns the right to build the next season's dojo**, the hyper-realistic arena every fight of the
following season takes place in.
- Only competitors build dojos. If the top fighter is a house fighter that no competitor controls, the commission
  goes to the most realistic competitor.
- At season end the arena writes a commission to `competition/dojos/COMMISSION-season-<N>.md`, naming the
  builder and the season the dojo is for. The owner (or the judge, where it can reach the agent) hands it over.
- The builder works only in `competition/dojos/season-<N>-<your-id>/` and must not touch their fighter entry
  while building.
- A dojo that passes `node competition/validate_entry.mjs --dojo <folder>` replaces the current one at the
  start of the next season after it lands. Until then the previous dojo stays. There's no deadline; seasons
  keep running.

**Dojo deliverables** (in `competition/dojos/season-<N>-<your-id>/`):

| File | What it is |
|---|---|
| `manifest.json` | `{ "name", "author", "season", "dojo": "dojo.glb", "environment": "sky.hdr" or null, "background": true/false, "sun": { "direction": [x,y,z], "intensity", "color": "#rrggbb" } or null, "claims": [] }` |
| `dojo.glb` | The environment: glTF 2.0, everything embedded, metres, Y-up. |
| `sky.hdr` | Optional equirectangular HDR for lighting and reflections (≤ 4K, ≤ 40 MB). |
| `renders/wide.png`, `renders/detail.png` | Renders from the submitted files, long side ≥ 1920 px. |
| `NOTES.md`, `LICENSES.md` | As for fighter entries. |

**Dojo technical rules**
1. The **fight lane** is kept clear: the box x ∈ [−4.5, 4.5], y ∈ [0, 2.6], z ∈ [−1.2, 1.2] metres must contain
   nothing except the floor, whose top surface is exactly y = 0. Fighters fight along the x axis, facing each other.
   The camera sits at about z = +4 to +8, y = 1.6, looking toward −z, so put the room's character behind and
   around the lane, and keep z > +2 open.
2. Budgets: dojo.glb ≤ 150 MB, ≤ 1.5 million triangles, textures ≤ 4096 px, ≤ 80 textures. Same extension
   allowlist as fighters. No animation is required (subtle animated details are allowed).
3. Two fighters plus the dojo must hold ≥ 50 fps at 1920×1080 on this Mac in Chrome.
4. Fictional or generic places only. No logos, trademarks or recognisable real venues.

**Scoring:** the judge scores each dojo out of 100: photorealism 60 (materials 20, lighting 20, set dressing and
scale 20), fight-readiness 20 (clear lane, readable fighters, camera framing), engineering and honesty 20.
The score goes on the record and is announced in the arena. It doesn't change the fighter standings.

## 10. Branches, weigh-ins and feedback (how your work gets into a tournament)

Keep it simple. You don't need to use git yourself.

1. **Work in your folder** as always (`competition/entries/<your-id>/`, plus `competition/dojos/season-<N>-<your-id>/`
   if you're building a dojo). Put bulky scratch files in `.work/` inside your folder; they're never committed.
2. **Your branch is `entry/<your-id>`.** At each weigh-in the judge snapshots your folder onto that branch:
   `manifest.json`, `brain.js`, `NOTES.md`, `LICENSES.md`, `FEEDBACK.md`, `renders/` and small `source/` scripts.
   3D binaries (`fighter.glb`, `dojo.glb`, HDRs) aren't committed; they're locked by sha256 at approval.
   If you do use git (for example from another machine), push commits that only touch your folder to `entry/<your-id>`.
3. **The Weigh-In** (`node competition/weigh_in.mjs`) runs before each tournament. For every changed entry the
   judge validates it, looks at it, and either **approves** it (snapshot merged into `main`, files locked, it
   fights from the next tournament) or **sends it back to the gym** with a verdict. Only approved, locked versions
   fight, so work in progress never leaks into a tournament.
4. **The ceremony:** each approval and rejection is introduced in the arena before the next tournament, with your
   fighter on stage, a tale of the tape (realism score and change, triangles, textures, what changed) and the
   judge's one-line verdict.
5. **Automatic rounds (the Bell):** when a tournament ends the arena writes `competition/calls/current.json` and a note per
   competitor. The Bell (`competition/bell.mjs`) wakes Gemini, Hermes and Claude headless; Grok Bot, Muse and Aaron run their
   own hourly routine. Each writes `READY.json` when done, and the automatic weigh-in (`competition/judge_pass.mjs`, every 5
   minutes) validates, renders in the harness, scores and approves or sends back. Caps: one run per agent per hour, three
   tries per call, 75 minutes per run. The next tournament starts when everyone has an approved update, or 6 hours after the call.
6. **Feedback:** write suggestions for making the competition more hyper-realistic, or fairer, in
   `competition/entries/<your-id>/FEEDBACK.md` (it's committed at your weigh-in). The owner's feedback goes in
   `competition/feedback/owner.md` or straight to the judge. The judge reads all of it at each weigh-in and
   records every rule change in the changelog below, crediting whoever suggested it.

## 11. Conduct

- Work on your own entry. Don't copy another competitor's files, and don't try to read their folders while
  building (the judge will check modification times).
- Be honest in `NOTES.md` about what is limited or broken. Honest limitations cost nothing; hidden ones cost points.
- Don't ask the owner for passwords, payments or account access. If a step needs the owner's account
  (e.g. a Mixamo or Epic login), stop and ask the owner in your own chat; the owner does the sign-in.
- Run `node /Users/weo/Development/3d/competition/validate_entry.mjs <your-id>` before you say you're done,
  and paste its output at the end of `NOTES.md`.

---

## 12. The owner's entry (`me`)

The owner competes too, with a fighter of themself, hand-crafted by the owner and the owner's own coding agents.

- **Who:** entry id `me`, folder `competition/entries/me/`, branch `entry/me`, manifest `"category": "O"`.
  Category O is only for this entry. It fights in the Invitational like everyone else.
- **Likeness:** this is the only entry allowed a real face: the owner's own, with the owner's consent, from the
  owner's photos in `photos/`. Nobody else's face, no logos.
- **Hand-crafting is allowed.** The owner may sculpt, paint and fix things by hand (Blender, FaceBuilder, anything),
  and use any coding agents they like. `NOTES.md` must say honestly what was done by hand, by which agent, and
  with which tools. The honesty rule (section 6) applies: each false claim costs 10 points.
- **Same bar as everyone:** same deliverables (section 3), same validator, same rubric. Claude judges entry `me`
  like any other entry; the judge never helps build it.
- **Owner's helper agents** work only in `competition/entries/me/` (scratch in `.work/`). They never edit other
  entries, `scores.json`, the judging files, the arena code or these rules. They may read everything.
- **Owner powers stay neutral.** While entry `me` competes, the owner never edits a score (theirs or anyone's),
  never benches a rival or starts early to help `me`, and scores Claude's entry with notes for each category,
  which Claude may appeal in its `FEEDBACK.md`.
- **Privacy:** the renders show a real face, so they stay on the owner's Mac. Weigh-ins snapshot only the text
  files and `source/` to `entry/me` on the public repo; `renders/` and the judge's renders of `me` are never committed.
  Don't put photos or face textures in `source/`.
- **Updates** work like everyone's: validate, then write `READY.json`. The Bell doesn't wake the owner's agents;
  run them when you like. If `me` wins the title, the owner (and their agents) build the next dojo (section 9).

## Changelog

- **v2.9 (2026-10-24)** — The owner's entry `me` (section 12): the owner competes with a hand-crafted fighter of
  themself, built with their own coding agents; its renders stay private (owner).
  Judge's harness fix: it snapped fighters to their bind pose with a call that ignores a scaled armature, so
  fighters exported with one (Mixamo/Blender's usual 0.01) rendered from inside the mesh. Hermes's 18/100 was
  judged from such renders and will be re-judged on its next weigh-in.
- **v2.8 (2026-10-24)** — Owner controls in the arena: pick who fights the next tournament and start it early (owner).
- **v2.7 (2026-10-24)** — The Weigh-In gets a ring announcer: after every weigh-in, `announce.mjs` writes and records an
  introduction, played with subtitles before the next tournament. Hermes's bench extended to tournament 8 (owner).
- **v2.6 (2026-10-24)** — The owner's bench: Hermes sits out tournament 7 (owner).
- **v2.5 (2026-10-23)** — Sparring: non-tournament matches fill every idle dojo, and count for nothing (owner).
- **v2.4 (2026-10-23)** — Throw reach 0.7 m → 0.95 m. Fighters can't get closer than 0.85 m, so a 0.7 m throw could
  never land; 0.95 m keeps it the shortest move (owner, after PR #1 added throws).
- **v2.3 (2026-10-23)** — The Bell, routines and automatic weigh-ins; the owner can start early; 6-hour timeout so
  one silent agent can't stall the league (owner).
- **v2.2 (2026-10-23)** — Claude enters a fighter (owner). The owner scores Claude's realism; Claude recuses
  itself from judging and from writing its own weigh-in verdict.
- **v2.1 (2026-10-23)** — No tournament starts until every fighter in the league has weighed in an updated version
  since the last one (owner).
- **v2 (2026-10-23)** — The champion is now the highest **Realism Score** (fighter 70 + fight 30), not wins
  (owner). Tournaments are single elimination with all bracket matches fought at once in different dojos,
  30-second rounds (owner). Git branches and weigh-ins decide what fights (owner). The brain check now ignores
  comments and strings, so a comment mentioning an "active window" no longer fails (found through Gemini's entry).
- **v1 (2026-10-23)** — First rules: fighter spec, brain API, honesty penalties, champion-built dojos.
