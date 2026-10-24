// The paired Mixamo shoulder throw (clips 'throw' and 'thrown', RULES.md §4).
//
// The full clips run 6 s, from a run-up to lying on the mat; the fight uses only the grab-to-recovery window, in
// place (the arena moves fighters), with the victim turned to face the thrower as in the clip.
//
// Fighters approved before the clips were required don't have them, so the arena lends them Mixamo's, retargeted at
// load time. Rigs orient their joints differently, so the retarget works from a pose every fighter shares: frame 0 of
// its own fighting_idle. Each bone gets the source's rotation away from that stance, applied to the target's stance.
import * as THREE from 'three';
import { gltfLoader } from './assets.js';

export const THROW_WINDOW = [1.85, 4.0];
const FPS = 30;
const SOURCE_URL = '/fighters/me.glb'; // the house X Bot fighter: Mixamo's own skeleton and clips, untouched
const UP = new THREE.Vector3(0, 1, 0);

const boneKey = (name) => name.match(/(Hips|Spine\d?|Neck|Head(?:Top_End)?|(?:Left|Right)[A-Za-z]+\d*)$/)?.[1] ?? null;

function bonesOf(root) {
  const list = [];
  root.traverse((o) => { if (o.isBone) list.push(o); });
  return list; // parents before children
}

/** Evaluate a clip on a model at time t and return every bone's model-space rotation (and the hips position). */
function poseAt(root, clip, t) {
  const mixer = new THREE.AnimationMixer(root);
  mixer.clipAction(clip).play();
  mixer.setTime(t);
  root.updateMatrixWorld(true);
  const rot = new Map();
  let hips = null;
  for (const b of bonesOf(root)) {
    rot.set(b, b.getWorldQuaternion(new THREE.Quaternion()));
    if (/Hips$/.test(b.name)) hips = b.getWorldPosition(new THREE.Vector3());
  }
  mixer.stopAllAction();
  mixer.uncacheRoot(root);
  return { rot, hips };
}

/** Rebuild a window of a clip for one rig, in place, optionally turned about the vertical axis. */
function windowed(name, frames, target, turn) {
  // frames: [{ rot: Map(bone → model-space quaternion), hipsY }] for this rig.
  const bones = bonesOf(target);
  const hips = bones.find((b) => /Hips$/.test(b.name));
  target.updateMatrixWorld(true);
  const yaw = new THREE.Quaternion().setFromAxisAngle(UP, turn);
  const parentRot = (b) => b.parent.getWorldQuaternion(new THREE.Quaternion());
  const restHips = hips.getWorldPosition(new THREE.Vector3());
  const hipsParentInv = hips.parent.matrixWorld.clone().invert();
  const times = frames.map((_, i) => i / FPS);
  const tracks = [];
  for (const b of bones) {
    if (!frames[0].rot.has(b)) continue;
    const values = [];
    frames.forEach((f) => {
      const world = yaw.clone().multiply(f.rot.get(b));
      const pw = b.parent.isBone && f.rot.has(b.parent) ? yaw.clone().multiply(f.rot.get(b.parent)) : parentRot(b);
      const local = pw.invert().multiply(world);
      values.push(local.x, local.y, local.z, local.w);
    });
    tracks.push(new THREE.QuaternionKeyframeTrack(`${b.name}.quaternion`, times, values));
  }
  // Hips: keep the height (the fall), drop the travel across the floor.
  const pos = [];
  frames.forEach((f) => new THREE.Vector3(restHips.x, f.hipsY, restHips.z).applyMatrix4(hipsParentInv).toArray(pos, pos.length));
  tracks.push(new THREE.VectorKeyframeTrack(`${hips.name}.position`, times, pos));
  return new THREE.AnimationClip(name, frames.length / FPS, tracks);
}

/** The window of a rig's own throw clip (rigs that have it). */
function ownWindow(root, clip, turn) {
  const frames = [];
  for (let t = THROW_WINDOW[0]; t <= THROW_WINDOW[1] + 1e-6; t += 1 / FPS) {
    const p = poseAt(root, clip, t);
    frames.push({ rot: p.rot, hipsY: p.hips.y });
  }
  return windowed(clip.name, frames, root, turn);
}

let source = null;
function loadSource() {
  source ??= gltfLoader.loadAsync(SOURCE_URL).then((g) => {
    // (This copy is only ever sampled, never shown.)
    const clip = (n) => g.animations.find((c) => c.name === n);
    const idle = poseAt(g.scene, clip('fighting_idle'), 0);
    const sample = (name) => {
      const out = [];
      for (let t = THROW_WINDOW[0]; t <= THROW_WINDOW[1] + 1e-6; t += 1 / FPS) out.push(poseAt(g.scene, clip(name), t));
      return out;
    };
    return { root: g.scene, idle, throw: sample('throw'), thrown: sample('thrown') };
  }).catch(() => null);
  return source;
}

/** Retarget the source's window onto a rig that lacks the clip, relative to each rig's fighting_idle stance. */
function lent(src, name, target, turn) {
  const idleClip = target.userData.clips.fighting_idle;
  const tIdle = poseAt(target, idleClip, 0);
  const byKey = new Map(bonesOf(src.root).map((b) => [boneKey(b.name), b]));
  const pairs = bonesOf(target).map((b) => [b, byKey.get(boneKey(b.name))]).filter(([, s]) => s && src.idle.rot.has(s));
  const ratio = tIdle.hips.y / src.idle.hips.y; // scale the fall to this fighter's height
  const frames = src[name].map((f) => {
    const rot = new Map();
    for (const [t, s] of pairs) {
      // target = (source now · source stance⁻¹) · target stance, all in model space
      const delta = f.rot.get(s).clone().multiply(src.idle.rot.get(s).clone().invert());
      rot.set(t, delta.multiply(tIdle.rot.get(t)));
    }
    return { rot, hipsY: f.hips.y * ratio };
  });
  return windowed(name, frames, target, turn);
}

/**
 * The fight-ready throw clips for a loaded fighter: { throw, thrown, lent } (cached on the gltf).
 * Returns null if neither the fighter nor the shared source can provide them.
 */
export async function throwClips(gltf) {
  if (gltf.userData.throwClips !== undefined) return gltf.userData.throwClips;
  const root = gltf.scene;
  // Sampling poses moves the bones of this shared, cached model: put them back afterwards.
  const rest = bonesOf(root).map((b) => [b, b.position.clone(), b.quaternion.clone(), b.scale.clone()]);
  root.userData.clips = Object.fromEntries(gltf.animations.map((c) => [c.name, c]));
  const own = root.userData.clips;
  let result = null;
  if (own.throw && own.thrown) {
    result = { throw: ownWindow(root, own.throw, 0), thrown: ownWindow(root, own.thrown, Math.PI), lent: false };
  } else if (own.fighting_idle) {
    const src = await loadSource();
    if (src) result = { throw: lent(src, 'throw', root, 0), thrown: lent(src, 'thrown', root, Math.PI), lent: true };
  }
  for (const [b, p, q, s] of rest) { b.position.copy(p); b.quaternion.copy(q); b.scale.copy(s); }
  root.updateMatrixWorld(true);
  gltf.userData.throwClips = result;
  return result;
}
