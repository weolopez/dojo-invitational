// Physics-based animation layering (dojo/PHYSICS.md). Visual only: the clips, inertial blending and look-at still
// decide the pose the game logic sees; this layer runs after them, drives a Rapier ragdoll toward that pose, steps the
// physics at a fixed 60 Hz, and blends the physics pose back onto the bones with a per-bone weight (0 = clip wins).
// Off unless PHYSICS.enabled (config.js) or ?physics=1 in the URL.
import * as THREE from 'three';
import { PHYSICS } from './config.js';

let RAPIER = null;
let loading = null;

/** True when the layer is switched on: the config flag, or ?physics=1 / ?physics=0 in the page URL. */
export function physicsEnabled() {
  const q = typeof location !== 'undefined' ? new URLSearchParams(location.search).get('physics') : null;
  if (q === '1' || q === 'true') return true;
  if (q === '0' || q === 'false') return false;
  return !!PHYSICS.enabled;
}

/** Load Rapier's WASM once. Resolves to null (layer stays off) if it can't load. */
export function loadPhysics() {
  loading ??= import('@dimforge/rapier3d-compat')
    .then(async (m) => { const R = m.default ?? m; await R.init(); RAPIER = R; return R; })
    .catch((e) => { console.warn('[physics] Rapier failed to load, layer off:', e); return null; });
  return loading;
}

// The ragdoll: body name -> mixamorig bone, the bone that ends the segment, the parent body, the joint, the group
// (upper body goes floppy on a hit, legs stay on the clip), and the capsule radius as a share of the standing height.
const PARTS = [
  { name: 'hips', bone: 'Hips', end: 'Spine', parent: null, group: 'core', r: 0.075 },
  { name: 'spine', bone: 'Spine', end: 'Spine2', parent: 'hips', group: 'upper', r: 0.075 },
  { name: 'chest', bone: 'Spine2', end: 'Neck', parent: 'spine', group: 'upper', r: 0.085 },
  { name: 'head', bone: 'Head', end: 'HeadTop_End', parent: 'chest', group: 'upper', r: 0.06, len: 0.12 },
  { name: 'armL', bone: 'LeftArm', end: 'LeftForeArm', parent: 'chest', group: 'upper', r: 0.03 },
  { name: 'foreL', bone: 'LeftForeArm', end: 'LeftHand', parent: 'armL', group: 'upper', r: 0.026, hinge: true },
  { name: 'armR', bone: 'RightArm', end: 'RightForeArm', parent: 'chest', group: 'upper', r: 0.03 },
  { name: 'foreR', bone: 'RightForeArm', end: 'RightHand', parent: 'armR', group: 'upper', r: 0.026, hinge: true },
  { name: 'thighL', bone: 'LeftUpLeg', end: 'LeftLeg', parent: 'hips', group: 'lower', r: 0.045 },
  { name: 'shinL', bone: 'LeftLeg', end: 'LeftFoot', parent: 'thighL', group: 'lower', r: 0.035, hinge: true },
  { name: 'footL', bone: 'LeftFoot', end: 'LeftToeBase', parent: 'shinL', group: 'lower', r: 0.025 },
  { name: 'thighR', bone: 'RightUpLeg', end: 'RightLeg', parent: 'hips', group: 'lower', r: 0.045 },
  { name: 'shinR', bone: 'RightLeg', end: 'RightFoot', parent: 'thighR', group: 'lower', r: 0.035, hinge: true },
  { name: 'footR', bone: 'RightFoot', end: 'RightToeBase', parent: 'shinR', group: 'lower', r: 0.025 },
];
const FLOOR = 0x0001;
const PART = 0x0002;
const groups = (member, filter) => ((member & 0xffff) << 16) | (filter & 0xffff);

const _v = new THREE.Vector3();
const _v2 = new THREE.Vector3();
const _q = new THREE.Quaternion();
const _q2 = new THREE.Quaternion();
const _s = new THREE.Vector3();
const _m = new THREE.Matrix4();

/** Rotation vector (axis × angle) of q, shortest way round. */
function rotVec(q, out) {
  const s = q.w < 0 ? -1 : 1;
  const w = Math.min(1, Math.abs(q.w));
  const angle = 2 * Math.acos(w);
  const k = angle < 1e-6 ? 2 : angle / Math.sin(angle / 2);
  return out.set(q.x * s * k, q.y * s * k, q.z * s * k);
}
const smooth = (t) => { const x = Math.min(1, Math.max(0, t)); return x * x * (3 - 2 * x); };

/** One Rapier world per arena; holds both fighters' ragdolls and the mat. */
export class PhysicsWorld {
  constructor() {
    this.world = new RAPIER.World({ x: 0, y: -9.81, z: 0 });
    this.world.timestep = 1 / PHYSICS.hz;
    this.world.createCollider(RAPIER.ColliderDesc.cuboid(20, 0.05, 20).setTranslation(0, -0.05, 0)
      .setCollisionGroups(groups(FLOOR, 0xffff)).setFriction(0.9));
    this.ragdolls = new Set();
    this.acc = 0;
    this.steps = 0;
  }

  add(r) { this.ragdolls.add(r); }
  remove(r) { this.ragdolls.delete(r); r.destroy(); }

  /** After all fighters animated: drive, step at the fixed rate, write the blended pose back. */
  step(dt) {
    const h = 1 / PHYSICS.hz;
    this.acc = Math.min(this.acc + Math.max(0, dt), h * PHYSICS.maxSubsteps);
    for (const r of this.ragdolls) r.capture(dt);
    while (this.acc >= h - 1e-9) {
      for (const r of this.ragdolls) r.drive(h);
      this.world.step();
      this.acc -= h;
      this.steps++;
    }
    for (const r of this.ragdolls) r.writeBack(dt);
  }
}

/** A fighter's ragdoll, built from its bind pose at the fighter's own scale. */
export class Ragdoll {
  constructor(physics, fighter) {
    this.physics = physics;
    this.fighter = fighter;
    const world = physics.world;
    const bones = {};
    fighter.model.traverse((o) => { if (o.isBone) bones[o.name.replace(/^mixamorig\d*:?/, '')] = o; });
    fighter.root.updateMatrixWorld(true);
    const height = (() => {
      const top = bones.HeadTop_End ?? bones.Head; const bot = bones.LeftToeBase ?? bones.LeftFoot;
      return top && bot ? top.getWorldPosition(_v).y - bot.getWorldPosition(_v2).y : 1.75;
    })();
    this.parts = [];
    this.byName = {};
    for (const p of PARTS) {
      const bone = bones[p.bone];
      if (!bone) continue;
      const pos = bone.getWorldPosition(new THREE.Vector3());
      const rot = bone.getWorldQuaternion(new THREE.Quaternion());
      // Segment from this bone to its end bone, in the bone's own (unscaled) frame.
      const endBone = bones[p.end];
      const seg = endBone ? endBone.getWorldPosition(new THREE.Vector3()).sub(pos) : new THREE.Vector3(0, (p.len ?? 0.1) * height / 1.75, 0);
      const len = Math.max(0.04, seg.length());
      const local = seg.clone().applyQuaternion(rot.clone().invert());
      const radius = Math.min(p.r * height / 1.75, len * 0.45);
      const body = world.createRigidBody(RAPIER.RigidBodyDesc.dynamic()
        .setTranslation(pos.x, pos.y, pos.z).setRotation({ x: rot.x, y: rot.y, z: rot.z, w: rot.w })
        .setLinearDamping(0.4).setAngularDamping(1.5).setCcdEnabled(true));
      const half = Math.max(0.005, len / 2 - radius);
      const along = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), local.clone().normalize());
      const mid = local.clone().multiplyScalar(0.5);
      world.createCollider(RAPIER.ColliderDesc.capsule(half, radius).setTranslation(mid.x, mid.y, mid.z)
        .setRotation({ x: along.x, y: along.y, z: along.z, w: along.w }).setDensity(1000)
        .setCollisionGroups(groups(PART, FLOOR)).setFriction(0.8), body);
      const part = { ...p, boneObj: bone, body, len, local, target: { pos: new THREE.Vector3(), rot: new THREE.Quaternion(), vel: new THREE.Vector3(), ang: new THREE.Vector3() },
        prevPos: new THREE.Vector3(), prevRot: new THREE.Quaternion(), anim: { pos: new THREE.Vector3(), rot: new THREE.Quaternion() } };
      this.parts.push(part);
      this.byName[p.name] = part;
      if (p.parent && this.byName[p.parent]) {
        const parent = this.byName[p.parent];
        // Joint at this bone's head, expressed in both bodies' frames.
        const a1 = pos.clone().sub(parent.boneObj.getWorldPosition(_v)).applyQuaternion(parent.boneObj.getWorldQuaternion(_q).invert());
        let data;
        if (p.hinge) {
          // Elbows and knees: hinge about the bone's local X (Mixamo convention), limited to one way.
          data = RAPIER.JointData.revolute({ x: a1.x, y: a1.y, z: a1.z }, { x: 0, y: 0, z: 0 }, { x: 1, y: 0, z: 0 });
        } else {
          data = RAPIER.JointData.spherical({ x: a1.x, y: a1.y, z: a1.z }, { x: 0, y: 0, z: 0 });
        }
        const joint = world.createImpulseJoint(data, parent.body, body, true);
        if (p.hinge && joint.setLimits) joint.setLimits(-2.6, 2.6);
        joint.setContactsEnabled?.(false);
      }
    }
    // Per-group motor stiffness (0 = limp, 1 = tracks the clip) and blend weight (0 = clip, 1 = physics).
    this.stiff = { core: 1, upper: 1, lower: 1 };
    this.weight = { core: PHYSICS.weight.core, upper: PHYSICS.weight.upper, lower: PHYSICS.weight.lower };
    this.hitAt = -1e9;
    this.fallState = null; // null | 'down' | 'rising'
    this.riseAt = 0;
    this.time = 0;
    this.fresh = true;
    physics.add(this);
  }

  destroy() {
    for (const p of this.parts) this.physics.world.removeRigidBody(p.body);
    this.parts = [];
  }

  /** Snap every body to the clip pose, at rest (a new round). */
  reset() {
    this.fresh = true;
    this.hitAt = -1e9;
    this.fallState = null;
  }

  /** The clip's (pre-physics) hips world pose from the last frame, for game logic; null before the first frame. */
  animHips() {
    const p = this.byName.hips;
    return p && !this.fresh ? p.anim : null;
  }

  /** A landed, unblocked hit: an impulse at the struck bone, and the upper body goes soft for a moment. */
  hit(attacker, move, high) {
    const part = this.byName[high ? 'head' : 'chest'] ?? this.byName.chest;
    if (!part) return;
    const from = attacker.root.position;
    const to = this.fighter.root.position;
    const dir = _v.set(to.x - from.x, 0, to.z - from.z);
    if (dir.lengthSq() < 1e-6) dir.set(-this.fighter.side * -1, 0, 0);
    dir.normalize();
    if (move.name === 'uppercut') dir.y += 0.8;
    dir.normalize().multiplyScalar(PHYSICS.impulsePerDamage * (move.dmg ?? 8));
    const t = part.body.translation();
    part.body.applyImpulseAtPoint({ x: dir.x, y: dir.y, z: dir.z }, { x: t.x, y: t.y + 0.02, z: t.z }, true);
    this.hitAt = this.time;
  }

  /** Read the clip pose (after the mixer, inertial blend and look-at) as this frame's targets. */
  capture(dt) {
    this.time += dt;
    this.fighter.root.updateMatrixWorld(true);
    for (const p of this.parts) {
      p.boneObj.matrixWorld.decompose(p.anim.pos, p.anim.rot, _s);
      const tg = p.target;
      if (this.fresh || dt <= 0) { tg.vel.set(0, 0, 0); tg.ang.set(0, 0, 0); }
      else {
        tg.vel.copy(p.anim.pos).sub(p.prevPos).divideScalar(dt);
        rotVec(_q.copy(p.anim.rot).multiply(_q2.copy(p.prevRot).invert()), tg.ang).divideScalar(dt);
      }
      tg.pos.copy(p.anim.pos); tg.rot.copy(p.anim.rot);
      p.prevPos.copy(p.anim.pos); p.prevRot.copy(p.anim.rot);
    }
    if (this.fresh) {
      for (const p of this.parts) {
        p.body.setTranslation(p.target.pos, true); p.body.setRotation(p.target.rot, true);
        p.body.setLinvel({ x: 0, y: 0, z: 0 }, true); p.body.setAngvel({ x: 0, y: 0, z: 0 }, true);
      }
      this.fresh = false;
    }
    this.envelope();
  }

  /** Stiffness and weight per group from the hit and knockdown timers (PHYSICS.hit / PHYSICS.knockdown). */
  envelope() {
    const P = PHYSICS;
    const f = this.fighter;
    const down = (f.downed || f.state === 'ko') && !f.gettingUp;
    if (P.knockdown.enabled) {
      if (down && this.fallState !== 'down') this.fallState = 'down';
      else if (!down && this.fallState === 'down') { this.fallState = 'rising'; this.riseAt = this.time; }
      else if (this.fallState === 'rising' && this.time - this.riseAt > P.knockdown.rampUp) this.fallState = null;
    }
    const base = P.weight;
    let s = { core: 1, upper: 1, lower: 1 };
    let w = { core: base.core, upper: base.upper, lower: base.lower };
    const since = this.time - this.hitAt;
    if (since < P.hit.soft + P.hit.recover) {
      const k = since < P.hit.soft ? 0 : smooth((since - P.hit.soft) / P.hit.recover);
      s.upper = P.hit.stiffness + (1 - P.hit.stiffness) * k;
      w.upper = Math.max(w.upper, P.hit.weight * (1 - k));
    }
    if (this.fallState === 'down') {
      s = { core: P.knockdown.stiffness, upper: P.knockdown.stiffness, lower: P.knockdown.stiffness };
      w = { core: P.knockdown.weight, upper: P.knockdown.weight, lower: P.knockdown.weight };
    } else if (this.fallState === 'rising') {
      const k = smooth((this.time - this.riseAt) / P.knockdown.rampUp);
      const ks = P.knockdown.stiffness + (1 - P.knockdown.stiffness) * k;
      s = { core: ks, upper: Math.min(ks, s.upper), lower: ks };
      for (const g of ['core', 'upper', 'lower']) w[g] = Math.max(w[g], P.knockdown.weight * (1 - k));
    }
    this.stiff = s; this.weight = w;
  }

  /** Velocity-matching motors: each body's velocity moves toward the one that reaches the clip pose, by stiffness. */
  drive(h) {
    const gain = PHYSICS.gain;
    for (const p of this.parts) {
      const s = this.stiff[p.group];
      const b = p.body;
      const t = b.translation(); const r = b.rotation();
      const lv = b.linvel(); const av = b.angvel();
      _v.set(p.target.pos.x - t.x, p.target.pos.y - t.y, p.target.pos.z - t.z).multiplyScalar(gain).add(p.target.vel);
      rotVec(_q.copy(p.target.rot).multiply(_q2.set(r.x, r.y, r.z, r.w).invert()), _v2).multiplyScalar(gain).add(p.target.ang);
      b.setLinvel({ x: lv.x + (_v.x - lv.x) * s, y: lv.y + (_v.y - lv.y) * s, z: lv.z + (_v.z - lv.z) * s }, true);
      b.setAngvel({ x: av.x + (_v2.x - av.x) * s, y: av.y + (_v2.y - av.y) * s, z: av.z + (_v2.z - av.z) * s }, true);
    }
  }

  /** Blend physics onto the bones: rotation per bone by weight, clamped to PHYSICS.maxDeviation from the clip; hips
   * position too. Parents first, so children see their parent's new pose. */
  writeBack() {
    const maxDev = (PHYSICS.maxDeviation * Math.PI) / 180;
    for (const p of this.parts) {
      const w = this.weight[p.group];
      if (w <= 1e-3) continue;
      const bone = p.boneObj;
      const r = p.body.rotation();
      _q.set(r.x, r.y, r.z, r.w);
      if (_q.dot(p.anim.rot) < 0) _q.set(-_q.x, -_q.y, -_q.z, -_q.w);
      const want = _q2.copy(p.anim.rot).slerp(_q, w);
      const ang = p.anim.rot.angleTo(want);
      if (ang > maxDev) want.copy(p.anim.rot).rotateTowards(want, maxDev);
      const parent = bone.parent;
      parent.updateWorldMatrix(true, false);
      parent.matrixWorld.decompose(_v2, _q, _s);
      bone.quaternion.copy(_q.invert().multiply(want));
      if (p.name === 'hips') {
        const t = p.body.translation();
        _v.set(t.x, t.y, t.z).lerp(p.anim.pos, 1 - w);
        bone.position.copy(parent.worldToLocal(_v));
      }
      bone.updateMatrixWorld(true);
    }
  }
}
