# FEEDBACK (entry `me`)

## Engine proposals

### 1. Ragdoll falls driven by the hit impulse
- **What to change:** when a knockdown fires, blend the last ~0.15 s of the hit-reaction clip into a ragdoll built
  from the mixamorig bones (capsules on hips, spine, head and limbs, joint limits from the bind pose). Apply the
  attacker's move as an impulse at the struck bone (direction from attacker to target, magnitude scaled by move
  damage). When the body's velocity settles, blend into the canned `getup_front` / `getup_back` from the pose the
  physics ended in.
- **Why it's more real:** every fall is different and follows the punch. A hook spins the body and an uppercut lifts
  it before it drops. Canned `knockdown_front` falls the same way every time and ignores where the hit landed.
- **How to tell it works:** replay the same knockdown three times from different hit directions and check that the
  pelvis lands in different places. The pelvis landing direction should match the impulse within ±30°. No limb should
  pass through the floor (all bone z ≥ 0 within 1 cm), and nothing should explode (joint angular speed < 30 rad/s).

### 2. Partial upper-body ragdoll hit reactions
- **What to change:** on a non-knockdown hit, run a powered ragdoll only on spine → head and the struck-side arm.
  Its motors track the current animation pose, and the impulse lands at the struck bone. Legs stay on the clip.
  Fade the physics weight from 1 to 0 over about 0.4 s.
- **Why it's more real:** head and torso snap away from where the punch landed, so jabs, hooks and uppercuts read
  differently, while the feet stay planted.
- **How to tell it works:** after a jab the head displacement points along the attacker→target vector, after a hook
  it points sideways, and after an uppercut it points up. Feet must not slide more than 1 cm during the reaction.
  The pose returns to the clip within 0.5 s, with a joint error under 3°.

### 3. Active-ragdoll get-ups
- **What to change:** pick `getup_front` or `getup_back` from the ragdoll's final pelvis orientation, not from the
  move. Before blending in, align the clip's root yaw and position to the lying pose. Then drive the first ~0.5 s of
  the get-up with motor targets from the clip, which keeps limbs from popping.
- **Why it's more real:** the fighter gets up from where and how they actually fell, with no teleport.
- **How to tell it works:** at the blend frame, root position jumps less than 5 cm and bone rotations jump less than
  15°. A fighter that lands face down always uses `getup_front`.

### 4. Foot IK / ground contact
- **What to change:** add two-bone IK on UpLeg→Leg→Foot after clip sampling, pinning each foot to the floor while
  the clip has it in contact (foot speed < 0.2 m/s and height < 3 cm). Adjust the pelvis down if needed, and pitch
  the foot to the floor normal.
- **Why it's more real:** it removes the foot sliding and floating that come from blending and retargeting
  differences, which judges notice on every frame.
- **How to tell it works:** in `fighting_idle` and the walks, a planted foot slides less than 1 cm and stays at a
  height of 0 ± 0.5 cm. Debug lines for knee direction never flip.

### 5. Spring-bone cloth and hair
- **What to change:** add optional extra bones in the glb (e.g. `spring:*` under Hips for the shorts hem and under
  Head for hair), simulated as damped springs (stiffness, damping and gravity in the node extras) with sphere
  colliders on the thighs and head.
- **Why it's more real:** the shorts and hair lag and settle after kicks and knockdowns, not stuck rigidly to the
  skeleton.
- **How to tell it works:** after a roundhouse, the shorts-hem bones overshoot and settle within about 0.6 s. Nothing
  penetrates the thigh colliders. A fighter without spring bones behaves exactly as before.
