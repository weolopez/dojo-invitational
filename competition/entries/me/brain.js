// THE OWNER's fight brain: a pressure fighter that steps in and throws.
// Walks forward behind a high guard, blocks strikes that can land, fires short combinations in close, finishes a
// hurt foe with hooks and roundhouse kicks, and now deliberately steps inside throw reach to grab a foe who is
// blocking or standing still. Memory timers are reset at the start of every round.
const REACH = { jab: 1.25, cross: 1.3, hook: 1.15, uppercut: 1.05, roundhouse: 1.6, frontkick: 1.5, throw: 0.95 };
const STAND = { move: null, fwd: false, back: false, block: false };
const DOWN = { ko: 1, victory: 1 };

export default function brain(state) {
  const { me, foe, distance, memory } = state;
  const t = state.time;

  // New round (time went backwards or round number changed): reset every timer and per-round flag.
  if (memory.round !== state.round || t < (memory.lastTime ?? 0)) {
    memory.round = state.round;
    memory.lastMove = -10;
    memory.combo = 0;
    memory.kdDone = false;
    memory.hitSince = null;
    memory.throwPlanAt = null;
    memory.nextPlanCheck = 0;
  }
  memory.lastTime = t;

  if (DOWN[me.state] || DOWN[foe.state]) { memory.throwPlanAt = null; return STAND; }

  const foeReach = foe.move ? REACH[foe.move] ?? 1.3 : 1.3;
  const foeAttacking = foe.state === 'attack';
  const ready = t - memory.lastMove > 0.38;
  const strike = (move) => { memory.lastMove = t; memory.combo++; return { ...STAND, move }; };

  // Track a long 'hit' spell as a knockdown (foe can't be hit then; don't chase it).
  if (foe.state === 'hit') { memory.hitSince ??= t; if (t - memory.hitSince > 1.2) memory.kdDone = true; }
  else memory.hitSince = null;
  const foeDowned = memory.hitSince !== null && t - memory.hitSince > 0.6;

  // Defence first: block a strike that can land. Abandons any throw plan.
  if (foeAttacking) {
    memory.throwPlanAt = null;
    if (distance <= foeReach + 0.1) return { ...STAND, block: true };
  }

  // --- Step in and throw ---
  if (memory.throwPlanAt !== null) {
    if (foeAttacking || foeDowned || t - memory.throwPlanAt > 1.0) memory.throwPlanAt = null;
    else if (distance <= REACH.throw) {
      if (ready) { memory.throwPlanAt = null; memory.combo = 0; return strike('throw'); }
      return STAND;
    } else return { ...STAND, fwd: true };
  }
  // Opportunistic: a non-attacking foe already inside throw reach gets grabbed.
  if (ready && !foeAttacking && !foeDowned && distance <= REACH.throw && foe.state !== 'hit') {
    memory.combo = 0; return strike('throw');
  }
  // Decide (about 10x/s, so gate to ~2 checks per second) whether to commit to a throw plan.
  if (!foeAttacking && foe.state !== 'hit' && distance > REACH.throw && distance <= 1.4 && t >= memory.nextPlanCheck) {
    memory.nextPlanCheck = t + 0.5;
    let p = 0.22;
    if (foe.state === 'block' || foe.state === 'idle') p += 0.13;
    if (me.hp < foe.hp && t > 18) p += 0.15;
    if (Math.random() < p) { memory.throwPlanAt = t; return { ...STAND, fwd: true }; }
  }

  // --- Finish a hurt foe (<= 30% health) with hooks and roundhouse kicks, once per round. ---
  if (!memory.kdDone && foe.hp <= 0.3 * foe.maxHp && foe.state !== 'block' && !foeDowned) {
    if (ready && distance <= REACH.hook) { memory.combo = 0; return strike('hook'); }
    if (ready && distance <= REACH.roundhouse) { memory.combo = 0; return strike('roundhouse'); }
    if (distance > REACH.hook) return { ...STAND, fwd: true };
    return STAND;
  }

  // Close the distance.
  if (distance > REACH.cross) {
    if (ready && distance <= REACH.frontkick && Math.random() < 0.25) return strike('frontkick');
    return { ...STAND, fwd: true };
  }
  if (!ready) return STAND;
  // In close: jab, cross, then a power shot; reset the combination after three.
  if (memory.combo >= 3) memory.combo = 0;
  return strike(['jab', 'cross', me.hp >= foe.hp ? 'hook' : 'uppercut'][memory.combo]);
}
