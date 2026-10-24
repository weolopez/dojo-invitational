# Physics-based animation layering

A visual layer that runs a Rapier ragdoll under each fighter and blends it onto the skeleton. **Off by default.**
Gameplay is unchanged: hits, damage, blocking, knockdown rules, stats, timing and the brain API all run on the clip
pose exactly as before. Two places read the hips for game logic (when a downed fighter has reached the mat, and
whether they lie face up or face down). Both read the clip's hips, not the physics hips.

## How to toggle
- URL: `?physics=1` turns it on and `?physics=0` forces it off. Examples: `http://localhost:5173/?physics=1`, or with
  the tournament: `/?tournament&physics=1`.
- Default: `PHYSICS.enabled` in `src/config.js` (false).
- When it's on, the first match loads `@dimforge/rapier3d-compat`, with its WASM inlined, through a dynamic `import()`.
  The page doesn't download it while the layer is off. If Rapier fails to load, the layer stays off and logs a warning.

## Design (`src/physics.js`)
- **World:** one Rapier world per arena, holding a static mat and both ragdolls. It uses a **fixed 60 Hz timestep**
  with an accumulator capped at `maxSubsteps`. Rapier is deterministic for the same inputs and step count, and no
  random numbers are used.
- **Ragdoll:** 14 capsules mapped to mixamorig bones:

  | Group | Bodies |
  |---|---|
  | Core | Hips |
  | Upper | Spine, Spine2, Head, both upper and lower arms |
  | Lower | Both thighs, shins and feet |

  - Each capsule is built from the bind pose when the fighter loads, so its length comes from the bone-to-child
    distance and its radius scales with the fighter's standing height. That means it works at any fighter scale.
  - A body's frame is its bone's world frame, so writing back is a straight rotation copy.
  - Joints:
    - Spherical at the hips, spine, neck, shoulders, ankles and thighs.
    - Revolute (hinge on the bone's local X) at the elbows and knees, limited to ±2.6 rad.
    - Rapier has no cone limits on spherical joints. Instead, the write-back clamps every bone to
      `maxDeviation` (70°) from its clip rotation, which acts as the joint limit.
  - Parts collide only with the mat, not with each other or with the other fighter.
- **Each frame**, after the AnimationMixer, inertial blending and head look-at have run for both fighters
  (`Arena.update` → `physics.step(dt)`), the layer does four things:
  1. **Capture.** Read each mapped bone's world transform as the target, and get the target velocity by finite
     difference.
  2. **Drive (velocity-matching motors).** For each body:
     - `v_des = target_vel + gain·(target_pos − pos)` (same for angular, using the rotation vector).
     - `v ← v + stiffness·(v_des − v)`.
     - With stiffness 1 the body tracks the clip. With 0 it's a free ragdoll under gravity and impulses. Values in
       between give a springy follow.
  3. **Step** Rapier zero to four times at 1/60 s.
  4. **Write back.** Parents go first. For each bone, slerp the clip rotation toward the body rotation by the group's
     weight, clamp to `maxDeviation`, convert to the bone's local rotation and update its matrices. The hips also
     blend position. A weight of 0 skips the bone, so the clip wins.
- **Hit reactions (partial ragdoll):**
  - A landed, unblocked strike applies an impulse at the struck body: the head for high blows, Spine2 for body
    shots.
  - The impulse direction runs from attacker to defender, horizontally, with an upward component for uppercuts. Its
    size is `impulsePerDamage × damage`.
  - For `hit.soft` (0.3 s) the upper body's motor stiffness drops to `hit.stiffness` and its blend weight rises to
    `hit.weight`. Over `hit.recover` (0.3 s) both ease back.
  - Hips and legs keep stiffness 1 and weight 0, so the feet stay on the clip.
- **Knockdowns:**
  - While a fighter is downed or KO'd, every group goes to `knockdown.stiffness` (near zero) and `knockdown.weight`,
    so the body falls loosely, following the knockdown clip.
  - When the get-up starts, stiffness ramps to 1 and weight to 0 over `knockdown.rampUp` (0.8 s).
  - Set `knockdown.enabled: false` to keep falls purely canned.
- **New round:** the bodies snap to the clip pose at rest.

## Knobs (`src/config.js` → `PHYSICS`)
These knobs are in `config.js`, not `realism.js`. `realism.js` is the champion's file, limited to the RULES.md §9a
knobs, and new knobs there would need a rules change (path 3, engine proposal).

| Knob | Default | Meaning |
|---|---|---|
| `enabled` | false | Default on/off (the URL overrides it) |
| `hz` | 60 | Fixed physics rate |
| `maxSubsteps` | 4 | Most physics steps per frame |
| `gain` | 30 /s | How hard a fully stiff body chases the clip |
| `maxDeviation` | 70° | Largest allowed rotation away from the clip, per bone |
| `weight.{core,upper,lower}` | 0 | Resting physics blend (0 = the clip wins) |
| `impulsePerDamage` | 0.9 N·s | Hit impulse per damage point |
| `hit.soft` / `hit.recover` | 0.3 / 0.3 s | Partial ragdoll: time the upper body stays soft, then time to recover |
| `hit.stiffness` / `hit.weight` | 0.08 / 1 | Upper-body stiffness and blend during a hit reaction |
| `knockdown.enabled` | true | Loose fall during knockdowns and KOs |
| `knockdown.stiffness` / `.weight` / `.rampUp` | 0.04 / 0.85 / 0.8 s | Fall looseness, how much physics shows, and the get-up ramp |

## How to tell it works
- With `?physics=0`, or with no parameter, the game is unchanged. All the code paths check `fighter.ragdoll` or
  `arena.physics`, and both are null.
- With `?physics=1` the console shows no warnings, and `__dojo.physics` exists in dev with 2×14 bodies.
- **Hit:** have one fighter hook the other from about 1 m. The defender's head and chest whip away from the attacker
  for about 0.3 s, then return to the reaction clip within about 0.3 s. Feet don't slide. A jab moves the head along
  the attacker→defender line, and an uppercut moves it up.
- **Knockdown:** the fall is looser and differs with hit direction. The get-up starts from the clip and blends in over
  0.8 s.
- **Performance:** measured headless (SwiftShader, CPU only, 1200 frames). The physics step costs about 0.14 ms per 60 Hz frame
  for two 14-body ragdolls. Logic plus physics takes 0.29 ms per frame, compared with 0.11 ms with physics off. That is under 2% of the
  16.7 ms budget for 60 fps. Rendering is unchanged, so fps is limited by the renderer, the same as before.

## Limitations
- There's no fist/shin-vs-body collision between fighters, so strikes can still pass through (optional, not done).
- Joint limits are approximate: hinges on the bone's local X, plus a per-bone deviation clamp in place of true cone
  limits. A fighter whose elbow or knee doesn't bend about local X gets a loose hinge.
- Physics positions only the hips; other bones blend rotation only, so limb lengths never stretch.
- During a loose knockdown, the physics body and the canned clip can disagree about where the fighter lies. The
  get-up hides this with its 0.8 s ramp, but a short slide can show.
