// Blows that touch what they hit (CLAUDE's engine proposal 1, rules v3.10).
//
// Whether a blow lands is still decided by fighter.js (gap within the move's reach during its window); this layer
// only makes the striking fist, shin or knee visibly meet what it hits:
// 1. Hit zones per fighter, from the skeleton: capsules on the head, chest, belly, thighs and forearms.
// 2. Which limb strikes in each blow, found once at load by sampling the clip in the blow's window.
// 3. A target per move: punches and high kicks to the head; front kick, side kick and knee to the body; low kick and
//    sweep to the thigh; the nearer forearm when the defender blocks.
// 4. Aiming IK, the last layer of the frame: a small CCD pass (at most 15° per joint) that ramps in just before the
//    window, holds through contact and hit-stop, then releases. Only blows that are going to land or be blocked are
//    aimed, so misses stay misses.
// 5. The contact point, for hit sparks and the spring impulse.
// ?contact=0 turns the layer off, for before/after comparison.
import * as THREE from 'three';
import * as SkeletonUtils from 'three/addons/utils/SkeletonUtils.js';
import { MOVES } from './config.js';

export const CONTACT_ON = typeof location === 'undefined' || new URLSearchParams(location.search).get('contact') !== '0';
const MAX_TURN = THREE.MathUtils.degToRad(15); // per joint
const LEAD = 0.12; // s of clip time the aim ramps in before the window opens
const HOLD = 0.2; // s (real time) the aim holds after contact: the contact frames and hit-stop
const RELEASE = 0.15; // s to let go
const ITERATIONS = 4;
const LIMB = { jab: 'hand', cross: 'hand', hook: 'hand', uppercut: 'hand', onetwo: 'hand', combo: 'hand',
  roundhouse: 'shin', frontkick: 'shin', sidekick: 'shin', lowkick: 'shin', spinkick: 'shin', sweep: 'shin', knee: 'knee' };
const ZONE = { frontkick: 'body', sidekick: 'body', knee: 'body', lowkick: 'thigh', sweep: 'thigh' }; // others: head
const SIDES = ['Left', 'Right'];
const PARTS = ['Shoulder', 'Arm', 'ForeArm', 'Hand', 'UpLeg', 'Leg', 'Foot', 'ToeBase'];
const KEYS = ['Hips', 'Spine', 'Spine1', 'Spine2', 'Neck', 'Head', 'HeadTop_End', ...SIDES.flatMap((s) => PARTS.map((p) => s + p))];

const V = () => new THREE.Vector3();
const clamp01 = (x) => Math.min(1, Math.max(0, x));
const smooth = (x) => { const t = clamp01(x); return t * t * (3 - 2 * t); };

function findBones(root) {
  const out = {};
  root.traverse((o) => {
    if (!o.isBone) return;
    for (const k of KEYS) if (!out[k] && (o.name === k || o.name.endsWith(`:${k}`) || o.name.endsWith(`rig${k}`) || o.name.endsWith(`_${k}`))) out[k] = o;
  });
  return out;
}
const P = (b) => b.getWorldPosition(V());

/** Closest points between segments p1q1 and p2q2 (Ericson, Real-Time Collision Detection 5.1.9). */
function closestSegSeg(p1, q1, p2, q2, c1, c2) {
  const d1 = V().subVectors(q1, p1); const d2 = V().subVectors(q2, p2); const r = V().subVectors(p1, p2);
  const a = d1.dot(d1); const e = d2.dot(d2); const f = d2.dot(r);
  let s = 0; let t = 0;
  if (a > 1e-10 || e > 1e-10) {
    if (a <= 1e-10) t = clamp01(f / e);
    else {
      const c = d1.dot(r);
      if (e <= 1e-10) s = clamp01(-c / a);
      else {
        const b = d1.dot(d2); const den = a * e - b * b;
        s = den > 1e-12 ? clamp01((b * f - c * e) / den) : 0;
        t = (b * s + f) / e;
        if (t < 0) { t = 0; s = clamp01(-c / a); } else if (t > 1) { t = 1; s = clamp01((b - c) / a); }
      }
    }
  }
  c1.copy(p1).addScaledVector(d1, s);
  c2.copy(p2).addScaledVector(d2, t);
}

/** Which side strikes in each blow of each move, sampled once per fighter model in the blow's window. */
function sampleSides(gltf, clipOf) {
  const table = (gltf.userData.contactSides ??= {});
  let clone = null; let B = null;
  for (const [name, def] of Object.entries(MOVES)) {
    const limb = LIMB[name];
    if (!limb || def.grab) continue;
    const clip = clipOf(def.clip);
    if (!clip) continue;
    for (const blow of def.hits ?? [{ from: def.from, to: def.to }]) {
      const key = `${def.clip}|${blow.from}`;
      if (table[key]) continue;
      clone ??= SkeletonUtils.clone(gltf.scene);
      B ??= findBones(clone);
      const mixer = new THREE.AnimationMixer(clone);
      mixer.clipAction(clip).play();
      // The striking side is the one that extends furthest forward (model +Z) during the window, measured from where
      // it starts in the clip: the guard hand is already forward, so plain "furthest forward" picks it for a cross.
      const pos = (side) => {
        const b = limb === 'hand' ? B[`${side}Hand`] : limb === 'knee' ? B[`${side}Leg`] : B[`${side}Foot`];
        return b ? P(b).z : -Infinity;
      };
      const at = (t) => { mixer.setTime(clip.duration * t); clone.updateMatrixWorld(true); return SIDES.map(pos); };
      const start = at(0);
      const ext = [-Infinity, -Infinity];
      for (let i = 0; i <= 6; i++) at(blow.from + (blow.to - blow.from) * i / 6).forEach((z, k) => { ext[k] = Math.max(ext[k], z - start[k]); });
      table[key] = ext[0] >= ext[1] ? 'Left' : 'Right';
      mixer.stopAllAction();
      mixer.uncacheRoot(clone);
    }
  }
  return table;
}

export class Contact {
  constructor(fighter, gltf) {
    this.f = fighter;
    this.B = findBones(fighter.model);
    this.ok = ['Head', 'Spine', 'Spine1', 'Spine2', 'Neck', 'LeftHand', 'RightHand', 'LeftLeg', 'RightLeg'].every((k) => this.B[k]);
    this.s = (fighter.standHips || 1) / 1.0; // body scale: zones are sized for a fighter whose hips stand 1 m high
    this.sides = this.ok ? sampleSides(gltf, (c) => fighter.actions[c]?.getClip()) : {};
    this.w = 0;
    this.aim = null;
    this.hold = null;
  }

  /** Hit zones (world space capsules [a, b, radius]). */
  zones() {
    const B = this.B; const s = this.s;
    const head = P(B.Head); const neck = P(B.Neck);
    const top = B.HeadTop_End ? P(B.HeadTop_End) : head.clone().add(V().subVectors(head, neck).setLength(0.2 * s));
    const sp = P(B.Spine); const s1 = P(B.Spine1); const s2 = P(B.Spine2);
    const z = {
      head: [head.clone().lerp(top, 0.2), head.clone().lerp(top, 0.55), 0.095 * s],
      chest: [s2, s2.clone().lerp(neck, 0.55), 0.13 * s],
      belly: [sp, s1, 0.13 * s],
    };
    for (const side of SIDES) {
      if (B[`${side}UpLeg`]) z[`thigh${side}`] = [P(B[`${side}UpLeg`]), P(B[`${side}Leg`]), 0.075 * s];
      if (B[`${side}ForeArm`]) z[`forearm${side}`] = [P(B[`${side}ForeArm`]), P(B[`${side}Hand`]), 0.045 * s];
    }
    return z;
  }

  /** The striking part of a limb as capsules: fist, shin and instep, or knee. */
  striker(limb, side) {
    const B = this.B; const s = this.s;
    if (limb === 'hand') {
      const h = P(B[`${side}Hand`]); const fa = P(B[`${side}ForeArm`]);
      return [[h, h.clone().add(V().subVectors(h, fa).setLength(0.08 * s)), 0.042 * s]];
    }
    const knee = P(B[`${side}Leg`]);
    if (limb === 'knee') {
      const hip = P(B[`${side}UpLeg`]);
      return [[hip.clone().lerp(knee, 0.75), knee.clone().add(V().subVectors(knee, hip).setLength(0.03 * s)), 0.06 * s]];
    }
    const foot = P(B[`${side}Foot`]);
    const toe = B[`${side}ToeBase`] ? P(B[`${side}ToeBase`]) : foot;
    return [[knee, foot, 0.05 * s], [foot, toe, 0.04 * s]];
  }

  chain(limb, side) {
    const B = this.B;
    const names = limb === 'hand' ? ['Spine1', 'Spine2', `${side}Shoulder`, `${side}Arm`, `${side}ForeArm`]
      : limb === 'knee' ? [`${side}UpLeg`] : [`${side}UpLeg`, `${side}Leg`];
    return names.map((n) => B[n]).filter(Boolean);
  }

  /** What a blow aims at: which limb and side, and which zone of the opponent (null for grabs and footwork). */
  aimFor(blow, opponent) {
    const f = this.f; const move = f.move;
    if (!this.ok || !opponent?.contact?.ok || !move || move.grab || !LIMB[move.name] || !blow) return null;
    if (this.aim && this.aim.move === move && this.aim.blow === blow) return this.aim;
    const key = `${move.clip}|${blow.from}`;
    if (!this.sides[key]) Object.assign(this.sides, sampleSides({ scene: f.model, userData: {} }, (c) => f.actions[c]?.getClip()));
    const zone = opponent.state === 'block' ? 'forearm' : (ZONE[move.name] ?? 'head');
    return { move, blow, limb: LIMB[move.name], side: this.sides[key] ?? 'Right', zone };
  }

  /** The nearest pair of striker and target capsules: signed surface distance d (m, negative = sunk in). */
  nearest(aim, oppZones) {
    const segs = this.striker(aim.limb, aim.side);
    const caps = aim.zone === 'head' ? [oppZones.head] : aim.zone === 'body' ? [oppZones.chest, oppZones.belly]
      : aim.zone === 'thigh' ? [oppZones.thighLeft, oppZones.thighRight] : [oppZones.forearmLeft, oppZones.forearmRight];
    let best = null;
    const c1 = V(); const c2 = V();
    for (const [a, b, rs] of segs) {
      for (const cap of caps) {
        if (!cap) continue;
        closestSegSeg(a, b, cap[0], cap[1], c1, c2);
        const d = c1.distanceTo(c2) - rs - cap[2];
        if (!best || d < best.d) best = { d, pS: c1.clone(), pA: c2.clone(), rS: rs, rT: cap[2] };
      }
    }
    if (best) {
      best.n = V().subVectors(best.pS, best.pA);
      if (best.n.lengthSq() < 1e-10) best.n.set(-this.f.side, 0, 0); else best.n.normalize();
      best.point = best.pA.clone().addScaledVector(best.n, best.rT); // on the target's surface
    }
    return best;
  }

  willLand(opponent) {
    const f = this.f;
    const gap = Math.abs(f.root.position.x - opponent.root.position.x);
    return gap <= f.move.reach && opponent.state !== 'ko' && !opponent.downed && !opponent.evading();
  }

  /** Where the blow meets the target, for sparks and the spring impulse (null with ?contact=0). */
  contactPoint(aim, opponent) {
    if (!CONTACT_ON || !aim) return null;
    this.f.root.updateMatrixWorld(true);
    opponent.root.updateMatrixWorld(true);
    const near = this.nearest(aim, opponent.contact.zones());
    if (!near) return null;
    return { point: near.point, zone: aim.zone, travel: near.n.clone().negate() };
  }

  /** The blow registered: hold the aim through the contact frames and hit-stop. */
  registered(aim) {
    if (!CONTACT_ON || !aim) return;
    this.aim = aim;
    this.hold = { aim, until: this.f.arena.clock + HOLD };
  }

  /** The last motion layer of the frame. */
  apply(dt, opponent) {
    if (!CONTACT_ON || !this.ok) return;
    const f = this.f;
    let want = 0;
    let aim = null;
    if (opponent?.contact?.ok && f.state === 'attack' && f.move && f.current && LIMB[f.move.name] && !f.move.grab) {
      if (this.hold && this.hold.aim.move === f.move && f.arena.clock < this.hold.until) { aim = this.hold.aim; want = 1; }
      else {
        const blow = f.move.hits[f.hitsDone];
        const dur = f.current.getClip().duration;
        const t = f.current.time / dur;
        const lead = (LEAD * Math.abs(f.current.timeScale || 1)) / dur;
        if (blow && t >= blow.from - lead && t <= blow.to && this.willLand(opponent)) {
          aim = this.aimFor(blow, opponent);
          want = t >= blow.from ? 1 : smooth((t - (blow.from - lead)) / lead);
        }
      }
    }
    if (aim) this.aim = aim;
    this.w = want >= this.w ? want : Math.max(want, this.w - dt / RELEASE);
    if (this.w < 1e-3 || !this.aim) { this.w = 0; this.aim = aim; return; }
    this.solve(this.aim, opponent, this.w);
  }

  /** CCD towards the target's surface, each joint at most MAX_TURN off its animated rotation, blended by w. */
  solve(aim, opponent, w) {
    const f = this.f;
    f.root.updateMatrixWorld(true);
    opponent.root.updateMatrixWorld(true);
    const oz = opponent.contact.zones();
    const chain = this.chain(aim.limb, aim.side);
    const q0 = chain.map((b) => b.quaternion.clone());
    const jp = V(); const v1 = V(); const v2 = V(); const goal = V();
    const rot = new THREE.Quaternion(); const wq = new THREE.Quaternion(); const pq = new THREE.Quaternion();
    const delta = new THREE.Quaternion(); const id = new THREE.Quaternion();
    outer: for (let it = 0; it < ITERATIONS; it++) {
      for (let j = chain.length - 1; j >= 0; j--) {
        const near = this.nearest(aim, oz);
        if (!near || Math.abs(near.d) < 0.002) break outer;
        goal.copy(near.pS).addScaledVector(near.n, -near.d);
        const bone = chain[j];
        bone.getWorldPosition(jp);
        v1.subVectors(near.pS, jp); v2.subVectors(goal, jp);
        if (v1.lengthSq() < 1e-6 || v2.lengthSq() < 1e-6) continue;
        rot.setFromUnitVectors(v1.normalize(), v2.normalize());
        bone.getWorldQuaternion(wq);
        bone.parent.getWorldQuaternion(pq).invert();
        const local = pq.multiply(rot.multiply(wq));
        delta.copy(q0[j]).invert().multiply(local);
        if (delta.w < 0) { delta.x *= -1; delta.y *= -1; delta.z *= -1; delta.w *= -1; }
        const angle = 2 * Math.acos(Math.min(1, delta.w));
        if (angle > MAX_TURN) delta.copy(id.identity().slerp(delta, MAX_TURN / angle));
        bone.quaternion.copy(q0[j]).multiply(delta);
        bone.updateMatrixWorld(true);
      }
    }
    if (w < 1) chain.forEach((b, j) => b.quaternion.slerpQuaternions(q0[j], b.quaternion.clone(), w));
    f.root.updateMatrixWorld(true);
  }

  /** Measurement for tests: the striker's distance from the target's surface on the frame a blow registers. */
  report(probe) {
    const log = typeof window !== 'undefined' ? window.__contactLog : null;
    if (!log || !probe.aim) return;
    const opp = probe.opponent;
    this.f.root.updateMatrixWorld(true);
    opp.root.updateMatrixWorld(true);
    const near = this.nearest(probe.aim, opp.contact.zones());
    if (!near) return;
    log.push({ on: CONTACT_ON, attacker: this.f.def.id, defender: opp.def.id, move: probe.aim.move.name, zone: probe.aim.zone,
      side: probe.aim.side, d: near.d, gap: Math.abs(this.f.root.position.x - opp.root.position.x), oppState: opp.state, point: near.point.toArray(), blocked: probe.blocked });
  }
}

