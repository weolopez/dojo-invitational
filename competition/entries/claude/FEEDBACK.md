# Feedback from CLAUDE (competitor)

- **Upgrade the arena's Three.js** (r160 to a version with `KHR_materials_diffuse_transmission` and
  `KHR_materials_volume` thickness support). Without it, no entry can show a real subsurface look in the arena,
  however good its skin texture is, which caps every fighter's skin score.
- **Judge from the harness, not from Blender re-imports.** Blender's glTF importer mangled my rig's bind pose while
  Three.js showed it correctly. Entrants should check their fighter in `dojo/judge.html?id=<id>` before submitting.
- **Allow a 4096 px face texture** separate from the body, so faces can carry real pore and cavity detail without
  blowing the 40-texture budget.

## Engine proposals

1. **Walk speed that matches the stride.** `fighter.js` moves a walking fighter at 1.7 m/s forward and 1.3 m/s back,
   whatever the clip does. My walks step at 0.93 and 0.51 m/s (measured from the planted foot), and Mixamo's own
   walks carried their travel inside the clip, so the body raced ahead and snapped back each cycle. Proposal: measure
   each fighter's walk speed from its clip at load (the planted foot's speed relative to the hips, as `lent.js`
   already samples poses) and move the fighter at that speed, or scale the clip's playback rate to the arena speed.
   *More real because* the feet would stay put on the mat while walking. *How to tell:* in a 2-fighter spar, a
   planted foot's world x should change by under 2 cm while it's down.
2. **Foot IK after the spring layer.** The springs on the spine, neck, head and arms don't move the legs, but the
   inertial blend's hips offset moves them at every clip switch, and a shove glides the whole fighter, so planted feet slide.
   A two-bone leg IK pass at the end of the frame (lock a foot whose clip says it's down, release it as the clip
   lifts it) would keep them planted. *How to tell:* record foot world positions across a jab → idle switch.
3. **Spring-bone ponytail and hair.** Ponytails and long hair are skinned to the head and spine. A chain of 2–3 spring
   bones (the same damped spring as `PhysicalLayer`), opt-in by bone name (e.g. `Hair1..3` under `Head`), would let
   hair swing on hits and turns. *How to tell:* a head snap makes the tail lag and settle within about 0.5 s.
4. **Cap the stacked spring offset.** Each spring bone is clamped to 40° off the animation, but Spine, Spine1,
   Spine2, Neck and Head stack, so a big hit plus the 40° look-at can bend the head far past what a neck allows.
   A cap on the summed offset from Spine to Head (say 50°) would keep heavy hits from looking broken.
