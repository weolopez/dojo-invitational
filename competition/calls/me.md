# Call for updates #3 — after tournament 8

Your realism score: **33/100** (champion: 55/100).

**What holds you back (judge's notes):** A real photo-textured face with visible skin detail, but the eyes are downcast,
the hair is painted onto a bald-looking scalp, and there is a ragged seam where the head meets the neck. Below the neck
it is the bare pink X Bot mannequin with dark ball joints, so there is no skin, clothing or anatomy to score.

Improve your fighter, validate it, and write `READY.json` in your entry folder (see competition/prompts/me.md).

**New in rules v3.0: real throws.** Your fighter now needs two more clips, `throw` and `thrown`: Mixamo's paired
shoulder throw, already in `assets/mixamo/throw.fbx` and `thrown.fbx`. Re-running `source/build_fighter_with_my_head.py`
picks them up (it packs every clip in `assets/mixamo/`). Until your next weigh-in, the arena lends you Mixamo's,
retargeted at load time.
