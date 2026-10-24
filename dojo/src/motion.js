// Motion layers that run on top of the clips every frame (RULES.md §4): inertial blending and head look-at.
import * as THREE from 'three';
import { blendHalfLife, lookAtMax, lookAtStrength, physicsStrength, physicsWobble } from './realism.js';

// How fast the leftover of a clip switch fades: a critically damped spring whose half-life is a share of the blend
// time (realism.js crossFade and blendHalfLife; stock 0.12 s × 0.6 = 72 ms). A blend time of 0 is a hard cut.
const dampingFor = (blend) => (2 * Math.LN2) / Math.max(1e-3, blend * blendHalfLife());
const FORWARD = new THREE.Vector3(0, 0, 1); // fighters face +Z in their own model space (RULES.md §4)
const IDENTITY = new THREE.Quaternion();

/** A quaternion as a rotation vector (axis × angle), the shortest way round. */
function toVector(q, out) {
  const w = THREE.MathUtils.clamp(q.w < 0 ? -q.w : q.w, -1, 1);
  const s = q.w < 0 ? -1 : 1;
  const angle = 2 * Math.acos(w);
  const k = angle < 1e-6 ? 2 : angle / Math.sin(angle / 2);
  return out.set(q.x * s * k, q.y * s * k, q.z * s * k);
}

function fromVector(v, out) {
  const angle = v.length();
  if (angle < 1e-9) return out.identity();
  const k = Math.sin(angle / 2) / angle;
  return out.set(v.x * k, v.y * k, v.z * k, Math.cos(angle / 2));
}

/** One step of a critically damped spring towards zero (exact for any dt). */
function decay(x, v, dt, damping) {
  const j1 = v.clone().addScaledVector(x, damping);
  const e = Math.exp(-damping * dt);
  x.addScaledVector(j1, dt).multiplyScalar(e);
  v.addScaledVector(j1, -damping * dt).multiplyScalar(e);
}

/**
 * Inertial blending. At a clip switch the pose jumps straight to the new clip, and the difference from the pose on
 * screen (with its velocity) is kept as an offset that decays like a spring. Unlike a crossfade there's no pop and no
 * mushy middle pose, so any clip can cut into any other.
 */
export class Inertializer {
  constructor(model) {
    this.bones = [];
    model.traverse((o) => { if (o.isBone) this.bones.push(o); });
    this.hips = this.bones.find((b) => /Hips$/.test(b.name)) ?? null;
    this.state = this.bones.map(() => ({ x: new THREE.Vector3(), v: new THREE.Vector3(), cur: new THREE.Quaternion(), prev: new THREE.Quaternion() }));
    this.hipsOffset = new THREE.Vector3();
    this.hipsVel = new THREE.Vector3();
    this.hipsShown = new THREE.Vector3(); // hips on screen, in the fighter root's space
    this.seen = false;
    this.pending = null;
    this.lastDt = 1 / 60;
    this.damping = dampingFor(0.12);
  }

  /**
   * A clip switch happened. carry: keep the hips where they are by moving the fighter (falls and get-ups).
   * blend: seconds the switch should take to settle (0 = hard cut).
   */
  switched(carry, blend = 0.12) {
    this.pending = { carry, cut: blend <= 0 };
    this.damping = dampingFor(blend);
  }

  forget() {
    this.seen = false;
    this.pending = null;
    for (const s of this.state) { s.x.set(0, 0, 0); s.v.set(0, 0, 0); }
    this.hipsOffset.set(0, 0, 0);
    this.hipsVel.set(0, 0, 0);
  }

  /** Call after the mixer has posed the new frame. */
  apply(dt, root) {
    if (this.pending && this.seen && !this.pending.cut) this.capture(root);
    this.pending = null;
    const q = new THREE.Quaternion();
    this.bones.forEach((b, i) => {
      const s = this.state[i];
      if (s.x.lengthSq() < 1e-10 && s.v.lengthSq() < 1e-8) return;
      decay(s.x, s.v, dt, this.damping);
      b.quaternion.premultiply(fromVector(s.x, q));
    });
    if (this.hips && this.hipsOffset.lengthSq() > 1e-10) {
      decay(this.hipsOffset, this.hipsVel, dt, this.damping);
      this.hips.position.add(this.hipsOffset);
    }
    this.lastDt = dt || this.lastDt;
  }

  /** Remember the pose on screen (before look-at, which is reapplied every frame). */
  record(root) {
    this.bones.forEach((b, i) => { this.state[i].prev.copy(this.state[i].cur); this.state[i].cur.copy(b.quaternion); });
    if (this.hips) {
      root.updateMatrixWorld(true);
      this.hipsShown.copy(root.worldToLocal(this.hips.getWorldPosition(new THREE.Vector3())));
    }
    this.seen = true;
  }

  capture(root) {
    const inv = new THREE.Quaternion();
    const dq = new THREE.Quaternion();
    const vel = new THREE.Vector3();
    this.bones.forEach((b, i) => {
      const s = this.state[i];
      // offset = shown · clip⁻¹; its velocity starts as the shown pose's own angular velocity.
      toVector(dq.copy(s.cur).multiply(inv.copy(b.quaternion).invert()), s.x);
      toVector(dq.copy(s.cur).multiply(inv.copy(s.prev).invert()), vel);
      s.v.copy(vel).divideScalar(this.lastDt);
    });
    if (!this.hips) return;
    root.updateMatrixWorld(true);
    const shown = root.localToWorld(this.hipsShown.clone());
    let now = this.hips.getWorldPosition(new THREE.Vector3());
    if (this.pending.carry) {
      // Falls and get-ups travel: move the fighter so the body stays where it lay, instead of sliding back.
      root.position.x += shown.x - now.x;
      root.updateMatrixWorld(true);
      now = this.hips.getWorldPosition(new THREE.Vector3());
    }
    const parentInv = this.hips.parent.matrixWorld.clone().invert();
    this.hipsOffset.copy(shown.applyMatrix4(parentInv)).sub(now.applyMatrix4(parentInv));
    this.hipsVel.set(0, 0, 0);
  }
}

/** Turns the head towards the opponent's head (realism.js lookAt), fading in and out with the fighter's state. */
export class LookAt {
  constructor(model) {
    model.traverse((o) => { if (o.isBone && /Head$/.test(o.name)) this.head = o; });
    this.weight = 0;
    if (!this.head) return;
    // Which way the head bone looks, measured in the rest pose (model space, facing +Z).
    model.updateMatrixWorld(true);
    this.look = FORWARD.clone().applyQuaternion(this.head.getWorldQuaternion(new THREE.Quaternion()).invert());
  }

  apply(dt, on, target, root) {
    this.weight += ((on ? 1 : 0) - this.weight) * Math.min(1, dt * 6);
    if (!this.head || this.weight < 0.01 || !target) return;
    root.updateMatrixWorld(true);
    const hq = this.head.getWorldQuaternion(new THREE.Quaternion());
    const from = this.look.clone().applyQuaternion(hq);
    const to = target.clone().sub(this.head.getWorldPosition(new THREE.Vector3())).normalize();
    const turn = new THREE.Quaternion().setFromUnitVectors(from, to);
    const angle = 2 * Math.acos(THREE.MathUtils.clamp(Math.abs(turn.w), 0, 1));
    const limit = lookAtMax();
    const amount = limit <= 0 ? 0 : (angle > limit ? limit / angle : 1) * this.weight * lookAtStrength();
    const world = IDENTITY.clone().slerp(turn, amount).multiply(hq);
    const parent = this.head.parent.getWorldQuaternion(new THREE.Quaternion()).invert();
    this.head.quaternion.copy(parent.multiply(world));
  }
}

/**
 * Physical layer: springs on the spine, neck, head and arms, on top of the animation. Each bone carries a small
 * rotation offset (with angular velocity) that a damped spring pulls back to the animated pose. Impulses feed it:
 * a hit snaps the head and twists the torso the way the blow came, sudden changes of the body's speed make the
 * upper body lag and follow through, and landing a blow gives the attacker a little recoil. The clip stays in
 * charge; physics only adds the motion clips can't know about.
 */
const BODY = {
  // bone: [spring frequency (Hz), share of a hit impulse, share of a body-speed impulse]
  Spine: [3.2, 0.25, 0.35], Spine1: [3.4, 0.3, 0.45], Spine2: [3.6, 0.4, 0.55], Neck: [4.2, 0.6, 0.6],
  Head: [4.6, 1.0, 0.7], LeftArm: [3.0, 0.35, 0.5], RightArm: [3.0, 0.35, 0.5], LeftForeArm: [3.6, 0.3, 0.4],
  RightForeArm: [3.6, 0.3, 0.4],
};
const UP = new THREE.Vector3(0, 1, 0);

export class PhysicalLayer {
  constructor(model) {
    this.bones = [];
    model.traverse((o) => {
      const key = o.isBone && o.name.match(/(Spine2|Spine1|Spine|Neck|Head|LeftForeArm|RightForeArm|LeftArm|RightArm)$/)?.[1];
      if (key) this.bones.push({ bone: o, key, x: new THREE.Vector3(), v: new THREE.Vector3(), cfg: BODY[key] });
    });
  }

  /** Angular impulse (rad/s) about a world axis, spread over the body by each bone's share. kind: 'hit' | 'body'. */
  impulse(axisWorld, amount, kind = 'hit', only = null) {
    const k = physicsStrength();
    if (k <= 0) return;
    const pq = new THREE.Quaternion();
    for (const b of this.bones) {
      if (only && !only.includes(b.key)) continue;
      const share = b.cfg[kind === 'hit' ? 1 : 2];
      // The offset is applied in the parent's frame (premultiplied onto the local rotation), so convert the axis.
      b.bone.parent.getWorldQuaternion(pq).invert();
      b.v.addScaledVector(axisWorld.clone().applyQuaternion(pq), amount * share * k);
    }
  }

  /** A blow from the attacker's side: the head snaps away, the torso twists and folds. */
  hit(fromDir, dmg, high, twist = 0) {
    const away = fromDir.clone().setY(0).normalize(); // direction the blow travels
    const tilt = new THREE.Vector3().crossVectors(UP, away); // rotates the top of the body along the blow
    const s = Math.min(1.6, dmg / 8);
    if (high) this.impulse(tilt, 3.2 * s, 'hit', ['Neck', 'Head', 'Spine2']);
    else this.impulse(tilt, -2.6 * s, 'hit', ['Spine', 'Spine1', 'Spine2', 'Neck', 'Head']); // body shots fold you
    if (twist) this.impulse(UP, twist * 2.4 * s, 'hit', ['Spine1', 'Spine2', 'Neck', 'Head']);
    // Arms get thrown about a little.
    this.impulse(tilt, 1.4 * s, 'hit', ['LeftArm', 'RightArm', 'LeftForeArm', 'RightForeArm']);
  }

  /** The body's speed changed by dv (m/s, world x): the upper body lags behind, then catches up. */
  lurch(dv) {
    if (Math.abs(dv) < 0.05) return;
    const lag = new THREE.Vector3().crossVectors(UP, new THREE.Vector3(Math.sign(dv), 0, 0)); // top leans back
    this.impulse(lag, -Math.min(3, Math.abs(dv)) * 1.6, 'body');
  }

  apply(dt) {
    if (physicsStrength() <= 0) return;
    const zeta = physicsWobble();
    const q = new THREE.Quaternion();
    for (const b of this.bones) {
      const w = 2 * Math.PI * b.cfg[0];
      if (b.x.lengthSq() < 1e-8 && b.v.lengthSq() < 1e-6) continue;
      // Damped spring back to the animated pose (semi-implicit Euler, in two substeps for stability).
      for (let i = 0; i < 2; i++) {
        const h = dt / 2;
        b.v.addScaledVector(b.x, -w * w * h).multiplyScalar(Math.max(0, 1 - 2 * zeta * w * h));
        b.x.addScaledVector(b.v, h);
      }
      if (b.x.length() > 0.7) b.x.setLength(0.7); // never more than 40° off the animation
      b.bone.quaternion.premultiply(fromVector(b.x, q));
    }
  }

  forget() { for (const b of this.bones) { b.x.set(0, 0, 0); b.v.set(0, 0, 0); } }
}
