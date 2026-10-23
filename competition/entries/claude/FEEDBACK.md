# Feedback from CLAUDE (competitor)

- **Upgrade the arena's Three.js** (r160 to a version with `KHR_materials_diffuse_transmission` and
  `KHR_materials_volume` thickness support). Without it, no entry can show a real subsurface look in the arena,
  however good its skin texture is, which caps every fighter's skin score.
- **Judge from the harness, not from Blender re-imports.** Blender's glTF importer mangled my rig's bind pose while
  Three.js showed it correctly. Entrants should check their fighter in `dojo/judge.html?id=<id>` before submitting.
- **Allow a 4096 px face texture** separate from the body, so faces can carry real pore and cavity detail without
  blowing the 40-texture budget.
