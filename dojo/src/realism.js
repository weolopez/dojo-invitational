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
  // Crossfade seconds between clips: default plus per-target-clip overrides. Allowed 0–0.4 s.
  crossFade: { default: 0.12, byClip: {} },
};

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
export const LIMITS = { timeScale: [0.6, 1.5], crossFade: [0, 0.4] };

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
