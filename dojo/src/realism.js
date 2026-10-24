// Champion's realism tuning (competition/RULES.md §9a). This is the ONLY file a tournament champion edits to change
// the feel of the arena game loop. The loop reads these values through the helpers below, which clamp them to the
// limits in the rules, so an out-of-range value can't break fairness. Values apply to every fighter equally.
// Empty / default values reproduce the stock game exactly.

export const REALISM = {
  version: 0, // bump on every champion change; shown nowhere, used by reviewers to match the changelog
  author: null, // champion id that made the current tuning, e.g. 'claude'
  tournament: null, // tournament number that earned the right
  // Playback rate multiplier per clip name (the 30 shared clip names, RULES.md §4). Allowed 0.6–1.5.
  clipTimeScale: {},
  // Crossfade seconds between clips: default plus per-target-clip overrides. Allowed 0–0.4 s. Since v3.2 this is the
  // inertial blend time (dojo/src/motion.js); 0 is a hard cut.
  crossFade: { default: 0.12, byClip: {} },
  // How quickly a blend settles: spring half-life as a share of the blend time. Allowed 0.3–1.
  blendHalfLife: 0.6,
  // Knockdowns (RULES.md §8): the health share at or below which a power shot drops you (0.2–0.4), and the seconds
  // you lie on the mat before getting up (1–3).
  knockdown: { below: 0.3, lie: 2.0 },
  // Playback rate of the get-up clips (1–1.5).
  getUpRate: 1.3,
  // Head look-at: the most the head turns toward the opponent, in degrees (0–40), and how much of that turn is
  // applied (0–1; 0 turns it off).
  lookAt: { maxDegrees: 40, strength: 0.8 },
  // Physical layer (motion.js): how hard hits and body movement push the spine, head and arms (0–1.5; 0 turns it
  // off), and how much they wobble before settling (damping ratio 0.35–1; lower wobbles more).
  physics: { strength: 1, damping: 0.55 },
};

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
export const LIMITS = {
  timeScale: [0.6, 1.5], crossFade: [0, 0.4], blendHalfLife: [0.3, 1],
  knockdownBelow: [0.2, 0.4], knockdownLie: [1, 3], getUpRate: [1, 1.5], lookAtDegrees: [0, 40], lookAtStrength: [0, 1],
  physicsStrength: [0, 1.5], physicsDamping: [0.35, 1],
};

/** A tuned number, clamped to its limits; the stock value if it's missing or not a number. */
const tuned = (v, [lo, hi], stock) => (typeof v === 'number' && Number.isFinite(v) ? clamp(v, lo, hi) : stock);

/** Playback-rate multiplier for a clip (1 when untuned). */
export function clipRate(name) {
  const v = REALISM.clipTimeScale[name];
  return typeof v === 'number' && Number.isFinite(v) ? clamp(v, ...LIMITS.timeScale) : 1;
}
export const hasClipRate = (name) => typeof REALISM.clipTimeScale[name] === 'number';

/** Crossfade duration into a clip, in seconds. */
export function crossFadeFor(name) {
  const v = REALISM.crossFade.byClip[name] ?? REALISM.crossFade.default;
  return typeof v === 'number' && Number.isFinite(v) ? clamp(v, ...LIMITS.crossFade) : 0.12;
}

/** Spring half-life as a share of the blend time. */
export const blendHalfLife = () => tuned(REALISM.blendHalfLife, LIMITS.blendHalfLife, 0.6);

/** Knockdown threshold (share of health) and seconds on the mat. */
export const knockdownBelow = () => tuned(REALISM.knockdown?.below, LIMITS.knockdownBelow, 0.3);
export const knockdownLie = () => tuned(REALISM.knockdown?.lie, LIMITS.knockdownLie, 2.0);

/** Playback rate of the get-up clips. */
export const getUpRate = () => tuned(REALISM.getUpRate, LIMITS.getUpRate, 1.3);

/** Head look-at: maximum turn in radians, and strength. */
export const lookAtMax = () => (tuned(REALISM.lookAt?.maxDegrees, LIMITS.lookAtDegrees, 40) * Math.PI) / 180;
export const lookAtStrength = () => tuned(REALISM.lookAt?.strength, LIMITS.lookAtStrength, 0.8);

/** Physical layer: impulse strength and damping ratio. */
export const physicsStrength = () => tuned(REALISM.physics?.strength, LIMITS.physicsStrength, 1);
export const physicsWobble = () => tuned(REALISM.physics?.damping, LIMITS.physicsDamping, 0.55);
