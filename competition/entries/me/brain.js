// THE OWNER's fight brain (call #7): a grappler that shoots first and makes the other grappler miss.
// Written by the owner's AI agent (Me Fighter).
const REACH = { jab: 1.25, cross: 1.3, hook: 1.15, uppercut: 1.05, roundhouse: 1.6, frontkick: 1.5, sidekick: 1.55,
  onetwo: 1.25, combo: 1.2, throw: 0.95, takedown: 1.1, sweep: 1.25, lowkick: 1.45, knee: 0.95, spinkick: 1.6 };
const GRABS = { takedown: 1, throw: 1, sweep: 1 };
// Seconds from the start of each strike until its blow can land (engine timings at tournament speed): grab before.
const WINDUP = { jab: 0.24, cross: 0.5, hook: 0.65, uppercut: 0.38, roundhouse: 0.75, frontkick: 0.55, sidekick: 0.5,
  onetwo: 0.22, combo: 0.4, lowkick: 0.38, knee: 1.3, spinkick: 0.75 };
// Roughly when each strike is over (seconds after it starts).
const OVER = { jab: 0.62, cross: 1.02, hook: 1.2, uppercut: 0.75, roundhouse: 1.38, frontkick: 1.12, sidekick: 0.83,
  onetwo: 0.66, combo: 1.25, lowkick: 0.65, knee: 1.67, spinkick: 0.95 };
const STAND = { move: null, fwd: false, back: false, block: false };

export default function brain(state) {
  const { me, foe, distance, memory } = state;
  const t = state.time;
  // New round (time went backwards or the round number changed): reset every timer kept in memory.
  if (memory.round !== state.round || t < (memory.lastTime ?? 0)) {
    memory.round = state.round;
    memory.lastMove = -10; memory.foeMoveAt = -10; memory.foeWasAttacking = false; memory.foeMove = null;
    memory.evadedAt = -10; memory.punishUntil = -1;
  }
  memory.lastTime = t;
  if (me.state === 'ko' || me.state === 'victory' || foe.state === 'ko') return STAND;
  if (me.state === 'attack' || me.state === 'hit') return STAND;

  const foeAttacking = foe.state === 'attack';
  if (foeAttacking && (!memory.foeWasAttacking || foe.move !== memory.foeMove)) { memory.foeMoveAt = t - 0.05; memory.foeMove = foe.move; }
  memory.foeWasAttacking = foeAttacking;
  const el = t - memory.foeMoveAt;
  const act = (move) => { memory.lastMove = t; return { ...STAND, move }; };
  const shoot = () => (distance <= REACH.throw && Math.random() < 0.35 ? act('throw') : distance <= REACH.takedown ? act('takedown') : { ...STAND, fwd: true });

  if (foeAttacking) {
    const mv = foe.move;
    // A grab coming: get out of it (evading beats every grab and sweep).
    if (GRABS[mv]) {
      if (el < 0.5 && distance < 1.5) { memory.evadedAt = t; memory.punishUntil = t + 1.6; return act('slip'); }
      return distance <= REACH.throw ? act('throw') : STAND;
    }
    if (mv === 'slip' || mv === 'dodge') return distance <= REACH.takedown ? shoot() : { ...STAND, fwd: true };
    const w = WINDUP[mv] ?? 0.3, over = OVER[mv] ?? 1;
    // Still winding up and we're in throw reach: the throw lands first.
    if (distance <= REACH.throw && el + 0.1 < w) return act('throw');
    // Blow is over: grab them on the recovery.
    if (el > over - 0.05) return distance <= REACH.takedown ? act(distance <= REACH.throw ? 'throw' : 'takedown') : { ...STAND, fwd: true };
    // Slow shot just started from range: slip inside it.
    if (el + 0.1 < w && w >= 0.5 && distance > 0.95 && distance < 1.65) return act('slip');
    if (distance <= (REACH[mv] ?? 1.3) + 0.15) return { ...STAND, block: true };
    return STAND;
  }

  // Foe on the mat: wait close by.
  if (foe.state === 'hit') return distance > 1.15 ? { ...STAND, fwd: true } : STAND;

  if (distance <= REACH.takedown) return shoot();
  return { ...STAND, fwd: true };
}
