// Next Dojo — physics animation demo (v1)
//
// A single connected animation system for a Mixamo-rigged fighter:
//   ANIM clips -> physics ragdoll fall -> settled pose -> get-up blend -> ANIM
// Physics: Rapier (rapier3d-compat). Rendering: three.js.
// v1 simplifications (see README.md): recovery is a pose-blend into the
// getting_up clip (active-ragdoll PD control is the next iteration); falls
// are kept near the mark with modest impulses; spherical joints have no
// angle limits yet.

import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import RAPIER from 'rapier';

const $ = (id) => document.getElementById(id);
const stateEl = $('state');
const errEl = $('err');
function fail(msg) { errEl.style.display = 'block'; errEl.textContent = 'Error: ' + msg; stateEl.textContent = 'ERROR'; }
window.addEventListener('error', (e) => fail(e.message));

const OPTS = new URLSearchParams(location.search);
const GLB_URL = OPTS.get('glb') || './fighter.glb';

// ---------- renderer / scene ----------
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setSize(innerWidth, innerHeight);
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
renderer.outputColorSpace = THREE.SRGBColorSpace;
document.body.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x14120e);
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;

const camera = new THREE.PerspectiveCamera(40, innerWidth / innerHeight, 0.05, 100);
const orbit = { theta: 0.55, phi: 1.18, dist: 4.4, target: new THREE.Vector3(0, 0.9, 0) };
function placeCamera() {
  const sp = Math.sin(orbit.phi), y = Math.cos(orbit.phi);
  camera.position.set(
    orbit.target.x + orbit.dist * sp * Math.sin(orbit.theta),
    orbit.target.y + orbit.dist * y,
    orbit.target.z + orbit.dist * sp * Math.cos(orbit.theta));
  camera.lookAt(orbit.target);
}
let dragging = false, px = 0, py = 0;
renderer.domElement.addEventListener('pointerdown', (e) => { dragging = true; px = e.clientX; py = e.clientY; });
addEventListener('pointerup', () => { dragging = false; });
addEventListener('pointermove', (e) => {
  if (!dragging) return;
  orbit.theta -= (e.clientX - px) * 0.005;
  orbit.phi = THREE.MathUtils.clamp(orbit.phi - (e.clientY - py) * 0.005, 0.25, 1.5);
  px = e.clientX; py = e.clientY;
});
addEventListener('wheel', (e) => { orbit.dist = THREE.MathUtils.clamp(orbit.dist + e.deltaY * 0.003, 2.2, 9); });
addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});

const key = new THREE.DirectionalLight(0xfff1dd, 2.4); key.position.set(-2.5, 4.2, 3); scene.add(key);
const rim = new THREE.DirectionalLight(0xbcd2ff, 1.1); rim.position.set(2.5, 2.5, -3); scene.add(rim);
const groundMesh = new THREE.Mesh(
  new THREE.CircleGeometry(6, 48),
  new THREE.MeshStandardMaterial({ color: 0x1a1712, roughness: 0.95 }));
groundMesh.rotation.x = -Math.PI / 2; scene.add(groundMesh);

// ---------- load fighter ----------
await RAPIER.init();
const world = new RAPIER.World({ x: 0, y: -9.81, z: 0 });
world.createCollider(RAPIER.ColliderDesc.cuboid(8, 0.1, 8).setTranslation(0, -0.1, 0).setFriction(1.0)
  .setCollisionGroups((1 << 16) | 2));

async function loadFighter() {
  // Single-file build injects the GLB as base64 (no fetch, no CORS).
  if (window.__GLB_B64) {
    const bin = atob(window.__GLB_B64);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return new GLTFLoader().parseAsync(bytes.buffer, '');
  }
  return new GLTFLoader().loadAsync(GLB_URL);
}
const gltf = await loadFighter();
const fighter = gltf.scene;
scene.add(fighter);
fighter.updateMatrixWorld(true);

const boneByKey = new Map();
fighter.traverse((o) => { if (o.isBone) boneByKey.set(o.name.replace(/[^a-zA-Z0-9]/g, ''), o); });
const bone = (short) => boneByKey.get('mixamorig' + short);
const REQUIRED = ['Hips', 'Spine', 'Spine1', 'Spine2', 'Neck', 'Head',
  'LeftArm', 'LeftForeArm', 'LeftHand', 'RightArm', 'RightForeArm', 'RightHand',
  'LeftUpLeg', 'LeftLeg', 'LeftFoot', 'LeftToeBase', 'RightUpLeg', 'RightLeg', 'RightFoot', 'RightToeBase'];
for (const r of REQUIRED) if (!bone(r)) throw new Error('missing bone ' + r);

// ---------- ragdoll construction (from the bind pose) ----------
const SEGMENTS = [
  // [boneName, childBoneName|null, radius, parentSegmentBone|null]
  ['Hips', 'Spine', 0.135, null],
  ['Spine', 'Spine2', 0.12, 'Hips'],
  ['Spine2', 'Neck', 0.145, 'Spine'],
  ['Head', null, 0.11, 'Spine2'],
  ['LeftArm', 'LeftForeArm', 0.055, 'Spine2'],
  ['LeftForeArm', 'LeftHand', 0.048, 'LeftArm'],
  ['RightArm', 'RightForeArm', 0.055, 'Spine2'],
  ['RightForeArm', 'RightHand', 0.048, 'RightArm'],
  ['LeftUpLeg', 'LeftLeg', 0.078, 'Hips'],
  ['LeftLeg', 'LeftFoot', 0.06, 'LeftUpLeg'],
  ['LeftFoot', 'LeftToeBase', 0.045, 'LeftLeg'],
  ['RightUpLeg', 'RightLeg', 0.078, 'Hips'],
  ['RightLeg', 'RightFoot', 0.06, 'RightUpLeg'],
  ['RightFoot', 'RightToeBase', 0.045, 'RightLeg'],
];
const _v1 = new THREE.Vector3(), _v2 = new THREE.Vector3(), _q1 = new THREE.Quaternion();

function boneWorld(name) {
  const b = bone(name); b.getWorldPosition(_v1); b.getWorldQuaternion(_q1);
  return { pos: _v1.clone(), quat: _q1.clone() };
}

const segs = new Map(); // boneName -> segment record
SEGMENTS.forEach(([name, child, radius, parent], i) => {
  const bw = boneWorld(name);
  let end;
  if (child) { end = boneWorld(child).pos; }
  else { // Head: extend past the head bone along Neck->Head
    const neck = boneWorld('Neck').pos;
    end = bw.pos.clone().add(bw.pos.clone().sub(neck).normalize().multiplyScalar(0.19));
  }
  const mid = bw.pos.clone().add(end).multiplyScalar(0.5);
  const dir = end.clone().sub(bw.pos);
  const len = Math.max(dir.length(), 0.05);
  const bodyQuat = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.clone().normalize());
  const body = world.createRigidBody(
    RAPIER.RigidBodyDesc.kinematicPositionBased().setTranslation(mid.x, mid.y, mid.z)
      .setRotation({ x: bodyQuat.x, y: bodyQuat.y, z: bodyQuat.z, w: bodyQuat.w })
      .setAngularDamping(3.5).setLinearDamping(0.08));
  // Self-collision OFF in v1: every ragdoll body shares group bit 1 and only
  // collides with the ground (bit 0). Overlapping capsules at the joints
  // otherwise wedge and jitter the doll upright.
  const col = world.createCollider(
    RAPIER.ColliderDesc.capsule(len / 2, radius).setFriction(0.9).setRestitution(0.0)
      .setDensity(350) // ~human segment masses; Rapier's default density makes gram-scale bodies
      .setCollisionGroups((2 << 16) | 1), body);
  segs.set(name, {
    name, bone: bone(name), body, radius, parent,
    bindBodyPos: mid.clone(), bindBodyQuat: bodyQuat.clone(),
    bindBonePos: bw.pos.clone(), bindBoneQuat: bw.quat.clone(),
    offPos: mid.clone().sub(bw.pos), // body origin relative to bone, in bind world frame
    offQuat: bodyQuat.clone().invert().multiply(bw.quat.clone()), // body -> bone rotation
    depth: 0,
  });
});
// collision filters: exclude parent/child segment pairs; compute joint anchors
for (const s of segs.values()) {
  let d = 0, p = s.parent;
  while (p) { d++; p = segs.get(p)?.parent; }
  s.depth = d;
}
for (const s of segs.values()) {
  if (!s.parent) continue;
  const par = segs.get(s.parent);
  if (OPTS.has('nojoints')) continue;
  // spherical joint at this segment's bone origin (bind world)
  const jointPos = s.bindBonePos;
  const a1 = jointPos.clone().sub(par.bindBodyPos).applyQuaternion(par.bindBodyQuat.clone().invert());
  const a2 = jointPos.clone().sub(s.bindBodyPos).applyQuaternion(s.bindBodyQuat.clone().invert());
  world.createImpulseJoint(RAPIER.JointData.spherical(
    { x: a1.x, y: a1.y, z: a1.z }, { x: a2.x, y: a2.y, z: a2.z }), par.body, s.body, true);
}
if (OPTS.has('nocollide')) for (const s of segs.values()) s.body.collider(0).setCollisionGroups(0);
// Low friction on shins/feet: in a real KO the feet slide out instead of
// planting and letting the doll balance back upright.
for (const s of segs.values())
  if (s.name.endsWith('Leg') || s.name.endsWith('Foot')) s.body.collider(0).setFriction(0.2);
const segOrder = [...segs.values()].sort((a, b) => a.depth - b.depth);

// ---------- animation ----------
const mixer = new THREE.AnimationMixer(fighter);
const actions = new Map();
for (const clip of gltf.animations) actions.set(clip.name, mixer.clipAction(clip));
let currentAction = null;
function playClip(name, { loop = false, fade = 0.15 } = {}) {
  const a = actions.get(name);
  if (!a) return null;
  a.reset(); a.enabled = true;
  a.setLoop(loop ? THREE.LoopRepeat : THREE.LoopOnce);
  a.clampWhenFinished = !loop;
  if (currentAction && currentAction !== a) { a.fadeIn(fade); currentAction.fadeOut(fade); }
  a.play(); currentAction = a;
  return a;
}
playClip('fighting_idle', { loop: true, fade: 0 });

// bind locals for every bone (for world-pose reconstruction in ragdoll mode)
const bindLocal = new Map();
fighter.traverse((o) => {
  if (o.isBone) bindLocal.set(o, { pos: o.position.clone(), quat: o.quaternion.clone(), scale: o.scale.clone() });
});
const allBonesByDepth = [];
fighter.traverse((o) => { if (o.isBone) allBonesByDepth.push(o); });
function depthOf(o) { let d = 0, p = o.parent; while (p) { d++; p = p.parent; } return d; }
allBonesByDepth.sort((a, b) => depthOf(a) - depthOf(b));
// per-segment constant: bone->body offset in bone-local frame
for (const s of segs.values()) {
  s.localOff = s.offPos.clone().applyQuaternion(s.bindBoneQuat.clone().invert());
  s.offVecBone = s.localOff.clone().applyQuaternion(s.offQuat);
}

// world transform helpers
const _p = new THREE.Vector3(), _p2 = new THREE.Vector3(), _q = new THREE.Quaternion(), _q2 = new THREE.Quaternion();
function bodyFromBone(seg, bonePos, boneQuat, outPos, outQuat) {
  outQuat.copy(seg.offQuat).invert().premultiply(boneQuat); // boneQuat * offQuat^-1
  outPos.copy(seg.localOff).applyQuaternion(boneQuat).add(bonePos);
}
function boneFromBody(seg, bodyPos, bodyQuat, outPos, outQuat) {
  outQuat.copy(bodyQuat).multiply(seg.offQuat);
  outPos.copy(seg.offVecBone).applyQuaternion(bodyQuat).multiplyScalar(-1).add(bodyPos);
}

// World matrices of non-bone ancestors (armature/root never move). The
// armature carries the export scale (0.00902), so all world<->local
// conversion must go through full matrices — pos/quat-only math is wrong.
const baseWorldMat = new Map();
fighter.updateMatrixWorld(true);
fighter.traverse((o) => { if (!o.isBone) baseWorldMat.set(o, o.matrixWorld.clone()); });
const segByBone = new Map([...segs.values()].map((s) => [s.bone, s]));
for (const s of segs.values()) s.bindWorldScale = s.bone.getWorldScale(new THREE.Vector3());
const bindLocalMat = new Map();
for (const [o, bl] of bindLocal) bindLocalMat.set(o, new THREE.Matrix4().compose(bl.pos, bl.quat, bl.scale));

const _mA = new THREE.Matrix4(), _mB = new THREE.Matrix4();
// Drive the skeleton from an explicit world pose for segment bones.
// poseFor: (seg) => {pos, quat} in world space (bind world scale applied here).
function applyWorldPose(poseFor) {
  const worldMat = new Map(baseWorldMat);
  for (const o of allBonesByDepth) {
    const parent = o.parent;
    const parentMat = parent ? worldMat.get(parent) : null;
    const seg = segByBone.get(o);
    let desired;
    if (seg) {
      const p = poseFor(seg);
      desired = new THREE.Matrix4().compose(p.pos, p.quat, seg.bindWorldScale);
    } else if (parentMat) {
      desired = parentMat.clone().multiply(bindLocalMat.get(o));
    } else {
      desired = o.matrixWorld.clone();
    }
    worldMat.set(o, desired);
    if (parentMat) {
      _mA.copy(parentMat).invert().multiply(desired);
      _mA.decompose(o.position, o.quaternion, o.scale);
    } else {
      desired.decompose(o.position, o.quaternion, o.scale);
    }
  }
  fighter.updateMatrixWorld(true);
}

// ---------- state machine ----------
let mode = 'ANIM'; // ANIM | RAGDOLL | RECOVER
let onceUntil = 0; // clock time when a one-shot clip ends
let settleTime = 0, settled = false, ragdollTime = 0;
let recover = null; // {snapshot: Map, action, dur, t0}
const clock = new THREE.Clock();

function setModeLabel() {
  stateEl.textContent =
    mode === 'ANIM' ? 'ANIMATED — clips in control' :
    mode === 'RAGDOLL' ? (settled ? 'DOWN — settled (ready to get up)' : 'PHYSICS — falling') :
    'RECOVERING — ragdoll blending into getting_up';
  $('bGetUp').disabled = !(mode === 'RAGDOLL' && settled);
}
function trackBodiesToBones() {
  for (const s of segOrder) {
    s.bone.getWorldPosition(_p); s.bone.getWorldQuaternion(_q);
    bodyFromBone(s, _p, _q, _p2, _q2);
    s.body.setNextKinematicTranslation({ x: _p2.x, y: _p2.y, z: _p2.z });
    s.body.setNextKinematicRotation({ x: _q2.x, y: _q2.y, z: _q2.z, w: _q2.w });
  }
}
function fall(kind) {
  if (mode !== 'ANIM') return;
  for (const s of segOrder) {
    s.body.setBodyType(RAPIER.RigidBodyType.Dynamic, true);
    s.body.setLinvel({ x: 0, y: 0, z: 0 }, true);
    s.body.setAngvel({ x: 0, y: 0, z: 0 }, true);
  }
  const chest = segs.get('Spine2'), head = segs.get('Head'), pelvis = segs.get('Hips');
  const shinL = segs.get('LeftLeg').body, shinR = segs.get('RightLeg').body;
  const t = chest.body.translation();
  if (kind === 'back') {
    chest.body.applyImpulseAtPoint({ x: 0, y: 32, z: -42 }, { x: t.x, y: t.y + 0.1, z: t.z }, true);
    pelvis.body.applyImpulse({ x: 0, y: -2, z: -12 }, true);
    shinL.applyImpulse({ x: 0, y: 2, z: -20 }, true); // legs sweep out from under her
    shinR.applyImpulse({ x: 0, y: 2, z: -20 }, true);
    head.body.applyImpulse({ x: 0, y: 4, z: -7 }, true);
  } else {
    chest.body.applyImpulseAtPoint({ x: 50, y: 20, z: 0 }, { x: t.x, y: t.y + 0.05, z: t.z }, true);
    pelvis.body.applyImpulse({ x: 16, y: -2, z: 0 }, true);
    shinL.applyImpulse({ x: 20, y: 2, z: 0 }, true);
    shinR.applyImpulse({ x: 20, y: 2, z: 0 }, true);
    head.body.applyImpulse({ x: 7, y: 2, z: 0 }, true);
  }
  mode = 'RAGDOLL'; settled = false; settleTime = 0; ragdollTime = 0; setModeLabel();
}
function getUp() {
  if (mode !== 'RAGDOLL' || !settled) return;
  // snapshot the settled world pose
  const snapshot = new Map();
  applyWorldPose((seg) => {
    const t = seg.body.translation(), r = seg.body.rotation();
    boneFromBody(seg, _p.set(t.x, t.y, t.z), _q.set(r.x, r.y, r.z, r.w), _p2, _q2);
    return { pos: _p2.clone(), quat: _q2.clone() };
  });
  for (const [k, s] of segs) {
    s.bone.getWorldPosition(_p); s.bone.getWorldQuaternion(_q);
    snapshot.set(k, { pos: _p.clone(), quat: _q.clone() });
    s.body.setBodyType(RAPIER.RigidBodyType.KinematicPositionBased, true);
  }
  const action = playClip('getting_up', { loop: false, fade: 0 });
  const dur = action.getClip().duration;
  recover = { snapshot, dur, t: 0 };
  mode = 'RECOVER'; setModeLabel();
}
function reset() {
  mode = 'ANIM'; recover = null; settled = false;
  for (const s of segOrder) s.body.setBodyType(RAPIER.RigidBodyType.KinematicPositionBased, true);
  playClip('fighting_idle', { loop: true, fade: 0.1 });
  setModeLabel();
}

// ---------- UI ----------
$('bJab').onclick = () => strike('jab');
$('bCross').onclick = () => strike('cross');
$('bHook').onclick = () => strike('hook');
$('bTaunt').onclick = () => strike('taunt');
$('bFallBack').onclick = () => fall('back');
$('bFallSide').onclick = () => fall('side');
$('bGetUp').onclick = () => getUp();
$('bReset').onclick = () => reset();
function strike(name) {
  if (mode !== 'ANIM') return;
  const a = playClip(name, { loop: false, fade: 0.08 });
  if (a) onceUntil = clock.elapsedTime + a.getClip().duration - 0.12;
}
// hooks for automated checks
window.__demo = { mode: () => mode, settled: () => settled, fall, getUp, strike, reset,
  pelvis: () => { const t = segs.get('Hips').body.translation(); return { x: +t.x.toFixed(2), y: +t.y.toFixed(2), z: +t.z.toFixed(2) }; },
  feed: () => {
    const s = segs.get('Hips');
    s.bone.getWorldPosition(_p); s.bone.getWorldQuaternion(_q);
    const bp = _p.clone(), bq = _q.clone();
    bodyFromBone(s, _p, _q, _p2, _q2);
    const f = (v) => [+v.x.toFixed(4), +v.y.toFixed(4), +v.z.toFixed(4), v.w !== undefined ? +v.w.toFixed(4) : null];
    return { bonePos: f(bp), boneQuat: f(bq), localOff: f(s.localOff), offQuat: f(s.offQuat), outPos: f(_p2), outQuat: f(_q2) };
  },
  bodies: () => [...segs.values()].map((s) => {
    const t = s.body.translation();
    return s.name + ':' + (Number.isFinite(t.x) ? t.y.toFixed(2) : 'NaN') + ':' + s.body.bodyType();
  }).join(' '),
  testBall: () => {
    const b = world.createRigidBody(RAPIER.RigidBodyDesc.dynamic().setTranslation(0, 3, 0));
    world.createCollider(RAPIER.ColliderDesc.ball(0.2).setDensity(350), b);
    window.__ball = b;
    return 'created';
  },
  ballPos: () => { const t = window.__ball.translation(); return { x: +t.x.toFixed(2), y: +t.y.toFixed(2), z: +t.z.toFixed(2) }; },
  debug: () => {
    const out = {};
    const hips = segs.get('Hips');
    const t = hips.body.translation(), r = hips.body.rotation();
    boneFromBody(hips, _p.set(t.x, t.y, t.z), _q.set(r.x, r.y, r.z, r.w), _p2, _q2);
    out.__hips = {
      parentName: hips.bone.parent ? hips.bone.parent.name + ':' + hips.bone.parent.type : null,
      local: [+hips.bone.position.x.toFixed(3), +hips.bone.position.y.toFixed(3), +hips.bone.position.z.toFixed(3)],
      poseFor: [+_p2.x.toFixed(3), +_p2.y.toFixed(3), +_p2.z.toFixed(3)],
      bodyT: [+t.x.toFixed(3), +t.y.toFixed(3), +t.z.toFixed(3)],
    };
    for (const name of ['Hips', 'Spine2', 'Head']) {
      const s = segs.get(name);
      s.bone.getWorldPosition(_p); s.bone.getWorldQuaternion(_q);
      out[name] = {
        bindBody: [+s.bindBodyPos.x.toFixed(3), +s.bindBodyPos.y.toFixed(3), +s.bindBodyPos.z.toFixed(3)],
        bindBone: [+s.bindBonePos.x.toFixed(3), +s.bindBonePos.y.toFixed(3), +s.bindBonePos.z.toFixed(3)],
        boneNow: [+_p.x.toFixed(3), +_p.y.toFixed(3), +_p.z.toFixed(3)],
        boneQuat: [+_q.x.toFixed(3), +_q.y.toFixed(3), +_q.z.toFixed(3), +_q.w.toFixed(3)],
      };
    }
    return out;
  } };

// ---------- frame loop ----------
function frame() {
  requestAnimationFrame(frame);
  const dt = Math.min(clock.getDelta(), 0.05);
  const now = clock.elapsedTime;

  if (mode === 'ANIM') {
    if (onceUntil && now > onceUntil) { onceUntil = 0; playClip('fighting_idle', { loop: true, fade: 0.22 }); }
    mixer.update(dt);
    fighter.updateMatrixWorld(true);
    if (!OPTS.has('notrack')) trackBodiesToBones();
    world.step();
  } else if (mode === 'RAGDOLL') {
    world.step();
    applyWorldPose((seg) => {
      const t = seg.body.translation(), r = seg.body.rotation();
      boneFromBody(seg, _p.set(t.x, t.y, t.z), _q.set(r.x, r.y, r.z, r.w), _p2, _q2);
      return { pos: _p2.clone(), quat: _q2.clone() };
    });
    ragdollTime += dt;
    const v = segs.get('Hips').body.linvel();
    const speed = Math.hypot(v.x, v.y, v.z);
    // Joint-stack tremor can hold the pelvis speed over a strict threshold
    // indefinitely; accept a loose threshold, and force-settle after 2.75 s —
    // by then a real fighter is down regardless.
    if (speed < 0.3) settleTime += dt; else settleTime = 0;
    if (!settled && (settleTime > 0.5 || ragdollTime > 2.75)) { settled = true; setModeLabel(); }
  } else if (mode === 'RECOVER' && recover) {
    mixer.update(dt);
    recover.t += dt;
    const raw = Math.min(recover.t / recover.dur, 1);
    const w = raw * raw * (3 - 2 * raw); // smoothstep
    fighter.updateMatrixWorld(true);
    // capture animation pose, then blend snapshot -> animation
    const animPose = new Map();
    for (const s of segOrder) {
      s.bone.getWorldPosition(_p); s.bone.getWorldQuaternion(_q);
      animPose.set(s.name, { pos: _p.clone(), quat: _q.clone() });
    }
    applyWorldPose((seg) => {
      const snap = recover.snapshot.get(seg.name), anim = animPose.get(seg.name);
      return {
        pos: snap.pos.clone().lerp(anim.pos, w),
        quat: snap.quat.clone().slerp(anim.quat, w),
      };
    });
    trackBodiesToBones();
    world.step();
    if (raw >= 1) { recover = null; mode = 'ANIM'; playClip('fighting_idle', { loop: true, fade: 0.25 }); setModeLabel(); }
  }

  placeCamera();
  renderer.render(scene, camera);
}
setModeLabel();
stateEl.textContent = 'ANIMATED — clips in control';
frame();
