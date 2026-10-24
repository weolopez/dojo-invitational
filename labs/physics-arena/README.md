# Next Dojo — physics animation demo

A working prototype of the "next dojo" animation system: instead of playing
isolated clips, the fighter is one connected state machine —

**ANIMATED** (clips in control) → **PHYSICS** (a hit hands the body to a
Rapier ragdoll) → **DOWN** (settled on the floor) → **RECOVERING** (the
settled pose blends into the `getting_up` clip) → **ANIMATED** again.

Built by Muse (Meta) at the owner's direction, on its own branch so the
tournament in `main` is untouched.

## Run it

Serve this folder statically and open `index.html`, with a fighter GLB next
to it named `fighter.glb` (any Dojo entry GLB works — it must have the
standard Mixamo `mixamorig:` skeleton and a `getting_up` clip):

```
npx serve labs/physics-arena   # or: python3 -m http.server
```

Or open the single-file build (`demo.html`, produced by `build-single.mjs`),
which embeds the fighter and needs no server at all.

Controls: Jab / Cross / Hook / Taunt play clips; **Uppercut** and
**Roundhouse** hand the body to physics with directional impulses (chest +
pelvis + a shin sweep, so the feet come out from under her instead of
planting); **Get up** appears once the doll settles; drag to orbit, wheel
to zoom.

## How it works

- **Ragdoll from the skeleton.** 14 capsule bodies are fitted to the Mixamo
  bones at bind pose (pelvis, spine, chest, head, upper/lower arms and
  legs, feet) with human-scale masses (density 350 ≈ a 50 kg fighter) and
  spherical joints at the anatomical pivots.
- **Two-way binding.** In ANIMATED mode the bodies are kinematic and track
  the animated bones, so the physics pose always matches the visible pose.
  The moment a fall starts, the bodies switch to dynamic with no pop —
  the handoff is seamless because the poses already agree.
- **Falls are simulated, not played.** Impulse direction decides the fall;
  no two falls are identical. Low friction on shins/feet (0.2) keeps a
  knocked-out doll from planting its feet and balancing back upright.
- **Recovery is a pose blend.** When the doll settles, its world pose is
  snapshotted; the `getting_up` clip then plays while every bone
  smoothstep-blends from the snapshot to the animated pose, and control
  returns to the clip system standing.
- **Scale-correct pose transfer.** The house GLB export puts a ~0.009
  scale on the armature, so all world↔local bone conversion goes through
  full matrices (never position/quaternion-only math, which silently
  collapses the skeleton to the origin).

## Honest simplifications (v1)

- **Recovery is a blend, not true active ragdoll.** The production design
  uses PD controllers driving the ragdoll toward the get-up pose; v1
  blends poses and tracks the bodies kinematically during recovery.
- **No self-collision.** Ragdoll bodies collide only with the ground;
  capsule self-collision wedged the doll upright and made it jitter.
  Limbs can interpenetrate during a fall.
- **Spherical joints have no angle limits yet** — elbows and knees can
  bend backwards in extreme falls.
- **Falls stay near the mark.** Impulses are tuned for readable,
  in-place knockdowns; the recovery blend assumes the doll settles near
  where it stood.
- One fighter, one opponent-less stage: no hit detection between two
  fighters yet — the fall buttons stand in for an opponent's strike.

## Files

- `index.html` — HUD + import map
- `src/main.js` — the whole system (state machine, ragdoll build, pose transfer)
- `vendor/` — pinned three.js 0.160 module, Rapier 0.14 (rapier3d-compat),
  GLTFLoader + RoomEnvironment addons
- `build-single.mjs` — esbuild script that produces the self-contained `demo.html`
- `test_demo.mjs` — headless-Chrome verification driver (idle → fall → settle → get-up → idle, plus a sideways fall; asserts zero console errors)
