// Clips the arena prepares or lends at load time (RULES.md §4).
//
// The paired Mixamo shoulder throw ('throw' and 'thrown'): the full clips run 6 s, from a run-up to lying on the mat;
// the fight uses only the grab-to-recovery window, in place (the arena moves fighters), with the victim turned to
// face the thrower as in the clip.
// Falls and get-ups ('knockdown_front', 'getup_back', 'getup_front'): played in place, whole.
//
// A fighter without one of these clips borrows Mixamo's from the lending library (build_lent_clips.py), retargeted.
// Rigs orient their joints differently, so the retarget works from a pose every fighter shares: frame 0 of its own
// fighting_idle. Each bone gets the source's rotation away from that stance, applied to the target's stance.
import * as THREE from 'three';
import { gltfLoader } from './assets.js';

export const THROW_WINDOW = [1.85, 4.0];
const FPS = 30;
const SOURCE_URL = '/fighters/lent.glb'; // Mixamo's X Bot with the clips above (build_lent_clips.py)
const EXTRAS = ['knockdown_front', 'getup_back', 'getup_front'];
// Mixamo's get-ups lie still for 2–3 s before rising, and stand for 2 s after: lend just the rise (measured on the
// hips height).
const LENT_WINDOWS = { getup_back: [3.2, 6.3], getup_front: [1.9, 6.3] };
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

/** A rig's own clip over a window (the whole clip by default), in place. */
function ownWindow(root, clip, turn, window = THROW_WINDOW) {
  const frames = [];
  for (let t = window[0]; t <= window[1] + 1e-6; t += 1 / FPS) {
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
    const sample = (name, window) => {
      const out = [];
      for (let t = window[0]; t <= window[1] + 1e-6; t += 1 / FPS) out.push(poseAt(g.scene, clip(name), t));
      return out;
    };
    const src = { root: g.scene, idle, throw: sample('throw', THROW_WINDOW), thrown: sample('thrown', THROW_WINDOW) };
    for (const name of EXTRAS) src[name] = sample(name, LENT_WINDOWS[name] ?? [0, clip(name).duration]);
    return src;
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
 * The fight-ready prepared clips for a loaded fighter (cached on the gltf):
 * { clips: { throw, thrown, knockdown_front, getup_back, getup_front }, lent: [names borrowed from the library] }.
 */
export async function fightClips(gltf) {
  if (gltf.userData.fightClips) return gltf.userData.fightClips;
  const root = gltf.scene;
  // Sampling poses moves the bones of this shared, cached model: put them back afterwards.
  const rest = bonesOf(root).map((b) => [b, b.position.clone(), b.quaternion.clone(), b.scale.clone()]);
  root.userData.clips = Object.fromEntries(gltf.animations.map((c) => [c.name, c]));
  const own = root.userData.clips;
  const clips = {};
  const lentNames = [];
  const turns = { thrown: Math.PI };
  const needed = ['throw', 'thrown', ...EXTRAS];
  const src = needed.some((n) => !own[n]) && own.fighting_idle ? await loadSource() : null;
  for (const name of needed) {
    const turn = turns[name] ?? 0;
    const window = name === 'throw' || name === 'thrown' ? THROW_WINDOW : null;
    if (own[name]) clips[name] = ownWindow(root, own[name], turn, window ?? [0, own[name].duration]);
    else if (src) { clips[name] = lent(src, name, root, turn); lentNames.push(name); }
  }
  for (const [b, p, q, s] of rest) { b.position.copy(p); b.quaternion.copy(q); b.scale.copy(s); }
  root.updateMatrixWorld(true);
  gltf.userData.fightClips = { clips, lent: lentNames };
  return gltf.userData.fightClips;
}
