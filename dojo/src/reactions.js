// Reactions chosen by where the blow lands (engine proposal 2 from CLAUDE's FEEDBACK.md).
//
// Sources: the four strike reactions every fighter ships (hit_head_light, hit_head_big, hit_by_uppercut,
// hit_reaction), and a library of 31 Mixamo hit reactions lent to every fighter (assets/mixamo/reactions, built into
// the lending library by build_lent_clips.py and retargeted in lent.js): head hits light, medium and big from a left,
// right or straight punch, stomach, rib, kidney and side hits, and small and large standing reactions.
// At load, the four shipped reactions and the one-sided body hits also get an upper-body mirror image
// (`<clip>_mirror`), and the side every clip throws the head toward is measured.
// When a blow lands, the pool is chosen by the zone it hit (head, chin, body, thigh), its strength and whether it came
// straight on or from the side; only clips that move the head away from the blow are kept; then one is picked at
// random, not repeating the last. A fighter can ship its own version of any of these clips, mirrors included.
import * as THREE from 'three';

export const REACTIONS = ['hit_head_light', 'hit_head_big', 'hit_by_uppercut', 'hit_reaction'];
// The lent library (file names in assets/mixamo/reactions). Head hits: strength, where the punch came from, and two
// Mixamo series (a: "Head Hit", b: "... Hit To Head").
export const LIBRARY = [
  ...['light', 'medium', 'big'].flatMap((s) => ['left', 'right', 'straight'].flatMap((d) => ['a', 'b'].map((v) => `head_${s}_${d}_${v}`))),
  'body_stomach', 'body_stomach_big', 'body_rib', 'body_rib_big', 'body_kidney', 'body_kidney_big', 'body_side', 'body_side_big',
  'react_small_left', 'react_small_right', 'react_large_left', 'react_large_right', 'react_large_front',
];
// One-sided clips that also get a mirror image.
const MIRRORED = [...REACTIONS, 'body_rib', 'body_rib_big', 'body_kidney', 'body_kidney_big', 'body_side', 'body_side_big'];
// Blows that come straight on; the rest come from the side.
const STRAIGHT = new Set(['jab', 'cross', 'onetwo', 'frontkick', 'sidekick', 'knee']);
const FPS = 30;
const partner = (name) => (name.includes('Left') ? name.replace('Left', 'Right') : name.includes('Right') ? name.replace('Right', 'Left') : name);
// Reflection across the body's mid-plane (model x = 0), applied to a rotation: (x, y, z, w) → (x, −y, −z, w).
const reflect = (q) => new THREE.Quaternion(q.x, -q.y, -q.z, q.w);
// The upper body: what a blow from the other side moves differently. The hips and legs keep the original clip, so the
// fighter's stance (which foot leads) doesn't flip.
const UPPER = /(Spine\d?|Neck|Head|Shoulder|Arm|Hand)/;

function bonesOf(root) {
  const list = [];
  root.traverse((o) => { if (o.isBone) list.push(o); });
  return list; // parents before children
}

/** Samples a clip: model-space rotations and positions of every bone at time t. One mixer per clip. */
function sampler(root, clip, bones) {
  const mixer = new THREE.AnimationMixer(root);
  mixer.clipAction(clip).play();
  return {
    at(t) {
      mixer.setTime(t);
      root.updateMatrixWorld(true);
      const rot = bones.map((b) => b.getWorldQuaternion(new THREE.Quaternion()));
      const pos = bones.map((b) => b.getWorldPosition(new THREE.Vector3()));
      return { rot, pos };
    },
    done() { mixer.stopAllAction(); mixer.uncacheRoot(root); },
  };
}

/**
 * The upper body's mirror image of a clip on this rig. In the hips' own frame (the hips' turn taken out), each upper
 * bone's movement away from its rest pose is taken from its partner on the other side and reflected, then applied to
 * the bone's own rest rotation, so it works even where a rig's left and right rest poses aren't exact mirror images.
 * The hips and legs play the original.
 */
function mirrorClip(root, clip, bones, rest) {
  const index = new Map(bones.map((b, i) => [b.name, i]));
  const pair = bones.map((b) => index.get(partner(b.name)) ?? index.get(b.name));
  const h = bones.findIndex((b) => /Hips$/.test(b.name));
  const hips = h >= 0 ? bones[h] : null;
  const upper = bones.map((b) => h >= 0 && UPPER.test(b.name));
  const frames = Math.max(2, Math.round(clip.duration * FPS) + 1);
  const times = [];
  const values = bones.map(() => []);
  const hipsPos = [];
  const clipAt = sampler(root, clip, bones);
  for (let i = 0; i < frames; i++) {
    const t = Math.min(clip.duration, i / FPS);
    times.push(t);
    const s = clipAt.at(t);
    // From the hips' current frame to their rest frame, and back.
    const undo = h >= 0 ? rest[h].clone().multiply(s.rot[h].clone().invert()) : null;
    const redo = undo?.clone().invert();
    const world = bones.map((b, k) => {
      if (!upper[k]) return s.rot[k];
      const j = pair[k];
      const delta = undo.clone().multiply(s.rot[j]).multiply(rest[j].clone().invert());
      return redo.clone().multiply(reflect(delta)).multiply(rest[k]);
    });
    bones.forEach((b, k) => {
      const parentWorld = b.parent.isBone ? world[index.get(b.parent.name)] : b.parent.getWorldQuaternion(new THREE.Quaternion());
      const local = parentWorld.clone().invert().multiply(world[k]);
      values[k].push(local.x, local.y, local.z, local.w);
    });
    if (hips) {
      const p = hips.parent.worldToLocal(s.pos[h].clone());
      hipsPos.push(p.x, p.y, p.z);
    }
  }
  clipAt.done();
  const tracks = bones.map((b, k) => new THREE.QuaternionKeyframeTrack(`${b.name}.quaternion`, times, values[k]));
  if (hips) tracks.push(new THREE.VectorKeyframeTrack(`${hips.name}.position`, times, hipsPos));
  return new THREE.AnimationClip(`${clip.name}_mirror`, clip.duration, tracks);
}

/**
 * Which way a clip throws the head across the body: +1 toward the fighter's left (model +x), −1 toward the right,
 * 0 if it hardly moves sideways (under 3 cm). Measured on a point 12 cm in front of the face, relative to the hips
 * with the hips' turn taken out, so a head turn and a lean both count and the stance doesn't.
 */
function headSide(root, clip, bones, rest) {
  const k = bones.findIndex((b) => /Head$/.test(b.name));
  const h = bones.findIndex((b) => /Hips$/.test(b.name));
  if (k < 0 || h < 0) return 0;
  const clipAt = sampler(root, clip, bones);
  const nose = (t) => {
    const s = clipAt.at(t);
    const undo = rest[h].clone().multiply(s.rot[h].clone().invert());
    const face = new THREE.Vector3(0, 0, 0.12).applyQuaternion(s.rot[k].clone().multiply(rest[k].clone().invert()));
    return s.pos[k].clone().add(face).sub(s.pos[h]).applyQuaternion(undo);
  };
  const start = nose(0);
  let best = 0;
  for (let t = 0; t <= clip.duration; t += 2 / FPS) { // every other frame is plenty for the peak
    const x = nose(t).x - start.x;
    if (Math.abs(x) > Math.abs(best)) best = x;
  }
  clipAt.done();
  return Math.abs(best) < 0.03 ? 0 : Math.sign(best);
}

/**
 * Mirror images and the side each reaction throws the head toward, for a loaded fighter. clips: every clip the
 * fighter has (its own and the lent ones). The bones must be in the rest pose when this is called; they're left in
 * some sampled pose (the caller puts them back).
 */
export function prepareReactions(root, clips) {
  const bones = bonesOf(root);
  root.updateMatrixWorld(true);
  const rest = bones.map((b) => b.getWorldQuaternion(new THREE.Quaternion()));
  const out = {};
  const sides = {};
  for (const name of MIRRORED) {
    if (!clips[name]) continue;
    out[`${name}_mirror`] = clips[`${name}_mirror`] ?? mirrorClip(root, clips[name], bones, rest);
  }
  for (const name of [...REACTIONS, ...LIBRARY]) {
    for (const n of [name, `${name}_mirror`]) {
      const clip = out[n] ?? clips[n];
      if (clip) sides[n] = headSide(root, clip, bones, rest);
    }
  }
  return { clips: out, sides };
}

/** The pool of reactions for a blow: zone, strength and how it came in. */
function pool(move, zone) {
  const straight = STRAIGHT.has(move.name);
  // (Mixamo's head hits come from a left, right or straight punch: a jab is the attacker's left, so straight blows
  // use them too; the side filter in chooseReaction keeps the ones that match the hand.)
  const head = (s) => ['left', 'right', 'straight'].flatMap((d) => ['a', 'b'].map((v) => `head_${s}_${d}_${v}`));
  if (move.name === 'uppercut' || move.react === 'hit_by_uppercut') return ['hit_by_uppercut', 'head_big_straight_a', 'head_big_straight_b'];
  if (zone === 'thigh') return ['react_small_left', 'react_small_right'];
  if (zone === 'head' || (!zone && move.high)) {
    if (move.dmg >= 10) return ['hit_head_big', ...head('big')];
    if (move.dmg >= 7) return ['hit_head_light', ...head('medium')];
    return ['hit_head_light', ...head('light')];
  }
  const big = move.dmg >= 12;
  if (straight) return big ? ['body_stomach_big', 'react_large_front', 'hit_reaction'] : ['body_stomach', 'hit_reaction'];
  return big ? ['body_rib_big', 'body_kidney_big', 'body_side_big', 'react_large_left', 'react_large_right']
    : ['body_rib', 'body_kidney', 'body_side', 'hit_reaction'];
}

/**
 * The reaction for a blow that landed. zone: 'head' | 'body' | 'thigh' (from contact.js; a guess from the move without
 * it); side: the attacker's striking side ('Left' | 'Right'), or null. last: the reaction played last time, to avoid.
 */
export function chooseReaction(move, zone, side, actions, sides, last = null) {
  // An attacker's right hand or leg lands on the defender's left (model +x), so the head goes to the right (−x).
  const away = side === 'Right' ? -1 : side === 'Left' ? 1 : (Math.random() < 0.5 ? -1 : 1);
  const straight = STRAIGHT.has(move.name);
  const names = pool(move, zone).flatMap((n) => [n, `${n}_mirror`]).filter((n) => actions[n]);
  // Keep the clips that move the head away from the blow; for a blow straight on, also the ones that go straight back.
  let fit = names.filter((n) => sides[n] === away || (straight && sides[n] === 0));
  if (!fit.length) fit = names.filter((n) => sides[n] !== -away);
  if (!fit.length) fit = names;
  if (fit.length > 1 && last) fit = fit.filter((n) => n !== last);
  return fit.length ? fit[Math.floor(Math.random() * fit.length)] : null;
}
