// CLAUDE's fight brain: a counter-striker who also leads.
// Blocks committed attacks and punishes the recovery after a whiff or a blocked strike, as before. New in call #5
// (it was too passive: 9 strikes in a whole match): it leads with strikes at its own range instead of only waiting,
// strings combinations after a landed shot, hunts knockdowns on a hurt opponent (hooks and kicks, which drop them),
// throws an opponent who turtles up, and presses harder when it's behind late in a round. It also resets its timers
// each round (they used to carry over and freeze it for most of rounds 2 and 3).
const REACH = { jab: 1.25, cross: 1.3, hook: 1.15, uppercut: 1.05, roundhouse: 1.6, frontkick: 1.5, throw: 0.95 };
const COMBO = { jab: 'cross', cross: 'hook', hook: 'uppercut', uppercut: 'jab', frontkick: 'cross', roundhouse: 'jab' };
const STAND = { move: null, fwd: false, back: false, block: false };

export default function brain(state) {
  const { me, foe, distance, memory } = state;
  // state.time restarts at 0 every round, but memory lasts the whole match: on a new round, forget the old timers.
  // (Before call #5 they made this brain wait out most of rounds 2 and 3, the real reason it looked so passive.)
  if (state.time < (memory.lastTime ?? 0)) {
    memory.lastMove = -10;
    memory.punishUntil = -1;
    memory.comboUntil = -1;
    memory.lastStrike = null;
  }
  memory.lastTime = state.time;
  memory.lastMove ??= -10;
  memory.lastStrike ??= null;
  memory.foeWasAttacking ??= false;
  memory.punishUntil ??= -1;
  memory.comboUntil ??= -1;

  if (me.state === 'ko' || foe.state === 'ko' || me.state === 'victory') return STAND;

  const foeAttacking = foe.state === 'attack';
  const foeReach = foe.move ? REACH[foe.move] ?? 1.3 : 1.3;
  // A foe that just finished an attack is open for a moment; a foe we just hit is open for the follow-up.
  if (memory.foeWasAttacking && !foeAttacking) memory.punishUntil = state.time + 0.5;
  if (foe.state === 'hit') memory.comboUntil = state.time + 0.6;
  memory.foeWasAttacking = foeAttacking;

  const foeHurt = foe.hp <= foe.maxHp * 0.4;
  const behindLate = me.hp < foe.hp && state.time > 18;
  const tempo = behindLate ? 0.32 : 0.4; // seconds between our strikes
  const ready = state.time - memory.lastMove > tempo;
  const strike = (move) => { memory.lastMove = state.time; memory.lastStrike = move; return { ...STAND, move }; };
  const best = (moves) => moves.find((m) => distance <= REACH[m]);

  // 1. Defend. A throw can't be blocked, but a strike beats it: jab, or step out. Block only strikes that can land.
  if (foeAttacking && foe.move === 'throw' && distance <= REACH.throw + 0.1) {
    return ready && distance <= REACH.jab ? strike('jab') : { ...STAND, back: true };
  }
  if (foeAttacking && distance <= foeReach + 0.05) return { ...STAND, block: true };

  // 2. Punish the opening with the best strike that reaches.
  if (ready && state.time < memory.punishUntil) {
    const m = best(foeHurt ? ['hook', 'uppercut', 'roundhouse'] : ['hook', 'cross', 'roundhouse']);
    return m ? strike(m) : { ...STAND, fwd: true };
  }

  // 3. Combination: after a landed shot, the next one in the chain, if it reaches.
  if (ready && state.time < memory.comboUntil && memory.lastStrike) {
    const next = COMBO[memory.lastStrike];
    if (distance <= REACH[next]) return strike(next);
  }

  // 4. Clinch range: a foe who turtles up (or stands still) inside throwing range gets thrown; throws beat the block.
  if (ready && distance <= REACH.throw && (foe.state === 'block' || foe.state === 'idle')) return strike('throw');

  // 5. Knockdown hunt: a hurt foe gets pressed with the moves that drop them (hooks and kicks).
  if (foeHurt) {
    if (distance > REACH.hook) return ready && distance <= REACH.roundhouse && Math.random() < 0.5 ? strike('roundhouse') : { ...STAND, fwd: true };
    return ready ? strike(Math.random() < 0.6 ? 'hook' : 'uppercut') : STAND;
  }

  // 6. Range control: work at our own range, leading with strikes rather than only waiting.
  if (distance > 1.65) return { ...STAND, fwd: true };
  if (!ready) return distance < 0.95 ? { ...STAND, back: true } : STAND;
  const lead = behindLate ? 0.9 : 0.75;
  if (Math.random() > lead) return distance < 1.05 ? { ...STAND, back: true } : STAND;
  if (distance <= REACH.cross) return strike(Math.random() < 0.6 ? 'jab' : 'cross');
  if (distance <= REACH.frontkick) return strike('frontkick');
  return strike('roundhouse');
}
