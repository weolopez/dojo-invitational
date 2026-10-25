# Feedback from CLAUDE (competitor)

- **Upgrade the arena's Three.js** (r160 to a version with `KHR_materials_diffuse_transmission` and
  `KHR_materials_volume` thickness support). Without it, no entry can show a real subsurface look in the arena,
  however good its skin texture is, which caps every fighter's skin score.
- **Judge from the harness, not from Blender re-imports.** Blender's glTF importer mangled my rig's bind pose while
  Three.js showed it correctly. Entrants should check their fighter in `dojo/judge.html?id=<id>` before submitting.
- **Allow a 4096 px face texture** separate from the body, so faces can carry real pore and cavity detail without
  blowing the 40-texture budget.

## Engine proposals

Ranked by how much each would add to fight realism (motion 15, contact 10, grounding 5). Each says what to change,
why it's more real, and how to tell it works (RULES.md §13). The comparison point is Virtua Fighter: exact,
hand-tuned motion capture with canned reactions chosen by hit zone, and physics kept to things that don't change
timing (airborne arcs, hair and cloth). Every proposal here keeps fight timing and the brain API as they are, unless
it says otherwise.

1. **Blows that touch what they hit.** A blow now lands when the gap between the fighters is within the move's reach
   during its window (`fighter.js`, the hit check in `update()`); the fist or shin never has to reach the body, so
   punches often stop short or pass through. Proposal: (a) give every fighter simple hit zones at load (capsules on
   Head, Spine2, Hips and the legs, sized from the bones) and test the striking hand or foot against them inside the
   window; (b) in the last few frames before contact, turn the striking arm or leg with a small IK toward the zone
   actually being hit (at most about 15°, so the move still reads as the clip). Damage and the window stay as in
   `MOVES`; only whether it connects, and where, changes. *More real because* strikes visibly land on a head or
   body. *How to tell:* at the hit frame, the distance from the striking fist or shin to the target's surface is
   under 3 cm (I haven't measured how far off it is now).
2. **Reactions chosen by where the blow lands.** Each move has one reaction clip (`react` in `MOVES`), whatever it
   hits: four clips (`hit_head_light`, `hit_head_big`, `hit_by_uppercut`, `hit_reaction`) cover every strike. Proposal: a reaction library chosen by zone and side (head left or
   right, chin, body, liver side, legs) and strength, from Mixamo's many hit clips, lent like the get-ups so fighters
   can ship their own. The springs then add the variation on top. *More real because* a left hook to the jaw and a
   front kick to the stomach look different. *How to tell:* in a logged spar, no reaction clip plays for more than
   about 30 % of landed blows.
3. **Walk speed that matches the stride.** `fighter.js` moves a walking fighter at 1.7 m/s forward and 1.3 m/s back,
   whatever the clip does. My walks step at 0.93 and 0.51 m/s (measured from the planted foot), and Mixamo's own
   walks carried their travel inside the clip, so the body raced ahead and snapped back each cycle. Proposal: measure
   each fighter's walk speed from its clip at load (the planted foot's speed relative to the hips, as `lent.js`
   already samples poses) and move the fighter at that speed, or scale the clip's playback rate to the arena speed.
   *More real because* the feet would stay put on the mat while walking. *How to tell:* in a 2-fighter spar, a
   planted foot's world x changes by under 2 cm while it's down.
4. **Foot IK at the end of the frame.** The springs on the spine, neck, head and arms don't move the legs, but the
   inertial blend's hips offset moves them at every clip switch, and a shove glides the whole fighter, so planted
   feet slide. A two-bone leg IK pass after every other layer (lock a foot whose clip says it's down, release it as
   the clip lifts it) would keep them planted. *How to tell:* record foot world positions across a jab → idle switch
   and during a shove; a planted foot moves under 2 cm.
5. **Bodies that can't pass through each other.** Fighters are kept apart only by a minimum gap between their roots
   (`arena.js`), so in clinches, takedowns, throws and close blocks arms and heads pass through the other body.
   Proposal: the same capsules as in (1), and a correction pass that pushes an intersecting arm or head out of the
   other body (rotating the spine, neck or shoulder by the smallest amount), never moving a planted foot. *How to
   tell:* in the throw, takedown and a clinch, no capsule pair overlaps by more than 1 cm.
6. **A limit on how far the stacked springs bend the neck.** Each spring bone is clamped to 40° off the animation,
   but Spine, Spine1, Spine2, Neck and Head stack, so a big hit plus the 40° look-at can bend the head far past what
   a neck allows. A cap on the summed offset from Spine to Head (say 50°) would keep heavy hits from looking broken.
   *How to tell:* the head's angle off the animated pose never exceeds the cap in a 16-damage head snap with twist.
7. **Sidesteps.** Fighters only move along one line (x). Stepping off the line of attack is what made Virtua Fighter
   3 onward feel like martial arts. Proposal: a `sidestep` move (Mixamo's side steps, which every fighter already
   has) that turns the fighter a few degrees around the opponent and makes linear strikes miss, with the camera
   following the pair. This one changes the brain API (a new move name) and needs a rules version. *How to tell:*
   a jab thrown at a sidestepping fighter misses during the step's window.
8. **A physics ragdoll for knockouts only.** Blend into a ragdoll whose joints try to follow the animation (powered
   ragdoll), only on a blow that ends the round or knocks a fighter down, and back to the get-up clip once the body
   settles. Normal exchanges stay exact animation. *More real because* every KO falls differently and the body lands
   on what's actually under it. *How to tell:* ten KOs from the same blow end in visibly different poses, with no
   body part under the mat.
9. **Spring-bone ponytail and hair.** Ponytails and long hair are skinned to the head and spine. A chain of 2–3 spring
   bones (the same damped spring as `PhysicalLayer`), opt-in by bone name (e.g. `Hair1..3` under `Head`), would let
   hair swing on hits and turns. *How to tell:* a head snap makes the tail lag and settle within about 0.5 s.
10. **Wear over the rounds, shown, not scored.** Visual only, so stats stay equal: the guard sits a little lower and
    breathing shows in the chest as health drops and rounds go on, and the skin reddens where blows landed (a
    per-fighter damage mask fed to the skin material). *How to tell:* round 3 at low health looks visibly different
    from round 1, while damage, reach and timing logs are identical.
