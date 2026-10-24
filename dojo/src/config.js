// Shared game data: roster, moves, controls, AI personalities and timing.

// Stats are multipliers around 1.0: power scales damage, speed scales footwork and attack speed,
// reach scales attack range, hp is starting health.
export const ROSTER = [
  { id: 'me', name: 'You', tag: 'Photo-scanned head', style: 'All-rounder', color: '#e8b04a', tint: 0,
    stats: { power: 1.05, speed: 1.0, reach: 1.0, hp: 105 } },
  { id: 'claude', name: 'Claude', tag: 'Anthropic', style: 'Patient counter-striker', color: '#d97757', tint: 0.45,
    stats: { power: 1.0, speed: 1.05, reach: 1.05, hp: 105 } },
  { id: 'gemini', name: 'Gemini', tag: 'Google', style: 'Quick combos', color: '#6d7cf2', tint: 0.45,
    stats: { power: 0.9, speed: 1.2, reach: 1.0, hp: 95 } },
  { id: 'grok', name: 'Grok', tag: 'xAI', style: 'Heavy hitter', color: '#9aa0a6', tint: 0.55, dark: true,
    stats: { power: 1.25, speed: 0.88, reach: 1.0, hp: 115 } },
  { id: 'hermes', name: 'Hermes', tag: 'Nous Research', style: 'Fastest feet', color: '#d4af37', tint: 0.4,
    stats: { power: 0.85, speed: 1.3, reach: 0.95, hp: 90 } },
  { id: 'muse', name: 'Muse', tag: 'Meta', style: 'Long-range kicks', color: '#d946ef', tint: 0.4,
    stats: { power: 1.0, speed: 1.1, reach: 1.15, hp: 95 } },
  { id: 'aaron', name: 'Aaron', tag: 'The masked one', style: 'Glass cannon', color: '#22c55e', tint: 0.4,
    stats: { power: 1.2, speed: 1.15, reach: 1.0, hp: 85 } },
];

export const EQUAL_STATS = { power: 1, speed: 1, reach: 1, hp: 100 };
export const ENTRY_COLORS = ['#e8734a', '#4f86f7', '#c9ced6', '#e0b23c', '#c55df0', '#3fbf6f', '#ff5d8f', '#36c5d6'];

// Competitors that build dojos (competition/RULES.md §9). The owner's house fighter doesn't.
export const DOJO_BUILDERS = ['claude', 'gemini', 'grok', 'hermes', 'muse', 'aaron', 'me'];

// Moves: clip, damage, reach (m), active window as fraction of the clip, reaction played on the target.
export const MOVES = {
  jab: { clip: 'jab', dmg: 5, reach: 1.25, from: 0.25, to: 0.5, react: 'hit_head_light' },
  cross: { clip: 'cross', dmg: 8, reach: 1.3, from: 0.3, to: 0.55, react: 'hit_head_light' },
  hook: { clip: 'hook', dmg: 10, reach: 1.15, from: 0.35, to: 0.6, react: 'hit_head_big' },
  uppercut: { clip: 'uppercut', dmg: 14, reach: 1.05, from: 0.35, to: 0.6, react: 'hit_by_uppercut' },
  roundhouse: { clip: 'roundhouse_kick', dmg: 16, reach: 1.6, from: 0.35, to: 0.6, react: 'hit_head_big' },
  frontkick: { clip: 'front_kick', dmg: 12, reach: 1.5, from: 0.3, to: 0.55, react: 'hit_reaction' },
  // Throw (grab): short reach, ignores block, but whiffs if the target is mid-strike (strikes beat throws).
  // Fighters with the paired Mixamo shoulder throw (clips 'throw' and 'thrown', RULES.md §4) use it; others fall back
  // to the slowed hook (attacker) and knocked_out then getting_up (defender).
  throw: { clip: 'hook', dmg: 13, reach: 0.95, from: 0.3, to: 0.55, react: 'knocked_out', grab: true, timeScale: 0.7,
    paired: { clip: 'throw', react: 'thrown', from: 0.03, to: 0.14, timeScale: 1.25 } },
  // More strikes from the shared clips. `hits` lists every blow of a combination (fractions of the clip, measured
  // from when each hand or foot is furthest forward); each blow can be blocked or land on its own.
  sidekick: { clip: 'side_kick', dmg: 13, reach: 1.55, from: 0.3, to: 0.45, react: 'hit_reaction' },
  onetwo: { clip: 'jab_cross', reach: 1.25, react: 'hit_head_light', timeScale: 1.15,
    hits: [{ from: 0.17, to: 0.28, dmg: 5 }, { from: 0.29, to: 0.42, dmg: 7 }] },
  combo: { clip: 'punch_combo', reach: 1.2, react: 'hit_head_light', timeScale: 1.1,
    hits: [{ from: 0.25, to: 0.35, dmg: 4 }, { from: 0.37, to: 0.46, dmg: 4 }, { from: 0.47, to: 0.56, dmg: 5 }, { from: 0.58, to: 0.68, dmg: 7 }] },
  // Footwork, played from each fighter's own step clips in place while the arena moves them: `shift` metres along the
  // way they face (minus = back) over the window `move`, and strikes miss them during `evade`. Throws miss too.
  dodge: { clip: 'dodge_back', alt: 'slip_back', dmg: 0, footwork: true, shift: -0.55, move: [0.05, 0.7], evade: [0.0, 0.8], timeScale: 1.2 },
  slip: { clip: 'dodge_in', alt: 'slip_in', dmg: 0, footwork: true, shift: 0.6, move: [0.05, 0.55], evade: [0.0, 0.85], timeScale: 1.2 },
  // Mixamo's MMA low kick, Muay Thai knee (close range only) and spinning back kick (lent.js); until a fighter
  // has them they play as the front kick, uppercut and roundhouse.
  lowkick: { clip: 'low_kick', dmg: 9, reach: 1.45, from: 0.32, to: 0.47, react: 'hit_reaction', needs: 'low_kick', fallback: 'frontkick' },
  knee: { clip: 'knee', dmg: 12, reach: 0.95, from: 0.66, to: 0.8, react: 'hit_reaction', needs: 'knee', fallback: 'uppercut' },
  spinkick: { clip: 'spin_kick', dmg: 17, reach: 1.6, from: 0.42, to: 0.56, react: 'hit_head_big', needs: 'spin_kick', fallback: 'roundhouse' },
  // (A kick that lands from closer than JAM metres is smothered: half damage, and it can't knock anyone down.)
  // Grappling with Mixamo's sweep and double-leg takedown (lent.js). A sweep is a low kick that drops a foe who
  // isn't blocking; a takedown is unblockable like a throw, ends in ground-and-pound, and whiffs on a foe mid-strike.
  // Until the clips are in the lending library, both fall back to the throw.
  // (Timings measured on Mixamo's clips: the sweep's foot connects at about half-way; the takedown makes contact at
  // 8–16% of its window, and its four ground punches land at 51, 71, 84 and 96%.)
  sweep: { clip: 'sweep', dmg: 9, reach: 1.25, from: 0.42, to: 0.56, react: 'sweep_fall', knockdown: true, needs: 'sweep', fallback: 'throw' },
  takedown: { clip: 'takedown', dmg: 8, reach: 1.1, from: 0.08, to: 0.16, react: 'takedown_victim', grab: true, needs: 'takedown',
    fallback: 'throw', timeScale: 1.2, ground: [{ at: 0.51, dmg: 4 }, { at: 0.71, dmg: 4 }, { at: 0.84, dmg: 5 }, { at: 0.96, dmg: 5 }] },
};
// Knockdowns: which power shots can drop a fighter, and which of them drop you on your front (the others: your back).
// You get up the way you landed. The health threshold and time on the mat are champion-tunable (realism.js).
export const KICKS = ['roundhouse', 'frontkick', 'sidekick', 'lowkick', 'spinkick'];
export const JAM = 1.0;
export const KNOCKDOWN = { moves: ['hook', 'uppercut', 'roundhouse', 'frontkick', 'spinkick', 'knee'], front: ['hook', 'roundhouse', 'spinkick'] };

export const MOVE_LABELS = { jab: 'Jab', cross: 'Cross', hook: 'Hook', uppercut: 'Uppercut', roundhouse: 'Roundhouse', frontkick: 'Front kick', throw: 'Throw' };

export const KEYMAP = {
  p1: { fwd: 'KeyD', back: 'KeyA', block: 'KeyS', taunt: 'KeyH',
        moves: { KeyJ: 'jab', KeyK: 'cross', KeyL: 'hook', KeyI: 'uppercut', KeyU: 'roundhouse', KeyO: 'frontkick', KeyP: 'throw' } },
  p2: { fwd: 'ArrowLeft', back: 'ArrowRight', block: 'ArrowDown', taunt: 'Digit0',
        moves: { Digit1: 'jab', Digit2: 'cross', Digit3: 'hook', Digit4: 'uppercut', Digit5: 'roundhouse', Digit6: 'frontkick', Digit7: 'throw' } },
};

// House fighting personalities: aggression (chance to strike when in range), block (chance per frame to
// block an incoming attack), kicks (share of kicks vs punches), power (preference for hooks/uppercuts).
export const PERSONALITIES = {
  default: { aggression: 0.35, block: 0.04, kicks: 0.3, power: 0.3, think: 0.5 },
  me: { aggression: 0.55, block: 0.05, kicks: 0.3, power: 0.4, think: 0.35 },
  claude: { aggression: 0.45, block: 0.09, kicks: 0.25, power: 0.35, think: 0.3 },
  gemini: { aggression: 0.7, block: 0.03, kicks: 0.15, power: 0.15, think: 0.25 },
  grok: { aggression: 0.55, block: 0.03, kicks: 0.2, power: 0.8, think: 0.4 },
  hermes: { aggression: 0.5, block: 0.06, kicks: 0.4, power: 0.2, think: 0.25 },
  muse: { aggression: 0.5, block: 0.05, kicks: 0.45, power: 0.3, think: 0.35 },
  aaron: { aggression: 0.8, block: 0.02, kicks: 0.3, power: 0.5, think: 0.3 },
};

export const ARENA_HALF = 4.2;
export const MIN_GAP = 0.85;
export const ROUNDS_TO_WIN = 2;

// Timing for normal play and for the faster tournament broadcast.
export const TIMING = {
  play: { roundTime: 60, roundIntro: 1.1, roundBreak: 3.6, victoryDelay: 0.9 },
  tournament: { roundTime: 30, roundIntro: 0.7, roundBreak: 1.8, victoryDelay: 0.5 },
};

// How many fights (tournament bouts + sparring) may run at once across all dojos. 1 = one fight at a time: bracket
// matches are fought one after another in a single dojo and no sparring runs beside a bout (RULES.md §8).
export const SCHEDULE = { maxConcurrentFights: 1 };
