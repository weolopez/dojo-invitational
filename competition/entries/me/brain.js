// THE OWNER's fight brain (call #5, rules v3.5): a pressure fighter who grapples.
// Written by the owner's AI agent (Me Fighter). Keeps the call #4 features: per-round timer reset, the
// step-in-and-throw plan and the hook/roundhouse finisher. Adds the v3.5 moves: slip inside slow kicks and grab on
// the recovery (grabs catch a foe winding up or recovering), takedown from 0.95-1.1 m, sweep from 1.1-1.25 m against
// a foe who isn't blocking, one-twos and the odd four-punch combo in close.
// The plain shoulder throw stays the main grab, since it works in every arena version.
const REACH = { jab: 1.25, cross: 1.3, hook: 1.15, uppercut: 1.05, roundhouse: 1.6, frontkick: 1.5, sidekick: 1.55,
  onetwo: 1.25, combo: 1.2, throw: 0.95, takedown: 1.1, sweep: 1.25 };
// Slow shots worth slipping, and roughly when their blow is over (seconds after they start).
const SLOW = { roundhouse: 1.5, frontkick: 1.2, sidekick: 0.95, hook: 1.3, uppercut: 0.85, combo: 1.4 };
const STAND = { move: null, fwd: false, back: false, block: false };

export default function brain(state) {
  const { me, foe, distance, memory } = state;
  const t = state.time;

  // New round: time went backwards (or round changed) -> reset every timer kept in memory.
  if (memory.round !== state.round || t < (memory.lastTime ?? 0)) {
    memory.round = state.round;
    memory.lastMove = -10; memory.foeMoveAt = -10; memory.foeWasAttacking = false;
    memory.slippedAt = -10; memory.counterUntil = -1; memory.planUntil = -1;
    memory.lastDecide = -10; memory.finished = false;
  }
  memory.lastTime = t;

  if (me.state === 'ko' || me.state === 'victory' || foe.state === 'ko') return STAND;

  const foeAttacking = foe.state === 'attack';
  if (foeAttacking && !memory.foeWasAttacking) memory.foeMoveAt = t;
  memory.foeWasAttacking = foeAttacking;
  const elapsed = t - memory.foeMoveAt;
  const ready = t - memory.lastMove > 0.35;
  const act = (move) => { memory.lastMove = t; memory.planUntil = -1; return { ...STAND, move }; };
  const foeHurt = foe.hp <= 0.3 * foe.maxHp;
  const behind = me.hp / me.maxHp < foe.hp / foe.maxHp;
  // Grab chooser: throw inside 0.95 m, takedown to 1.1 m, otherwise walk in.
  const grab = () => (distance <= REACH.throw ? act('throw')
    : distance <= REACH.takedown ? act(Math.random() < 0.5 ? 'takedown' : 'throw') : { ...STAND, fwd: true });

  // 1. Foe striking.
  if (foeAttacking) {
    memory.planUntil = -1; // abandon any step-in
    const slow = SLOW[foe.move];
    if (slow !== undefined) {
      if (elapsed > slow) { memory.counterUntil = t + 0.6; return ready ? grab() : { ...STAND, fwd: distance > REACH.throw }; }
      if (ready && elapsed < 0.3 && distance > 1.0 && distance < 1.55 && t - memory.slippedAt > 1.5 && Math.random() < 0.5) {
        memory.slippedAt = t; memory.counterUntil = t + slow + 0.6;
        return act('slip');
      }
    }
    if (distance <= (REACH[foe.move] ?? 1.3) + 0.1) return { ...STAND, block: true };
    return STAND;
  }

  // Foe likely on the mat (just knocked down): don't waste moves.
  if (foe.state === 'hit' && t - memory.lastMove < 2.2 && t - memory.lastMove > 0.8) return STAND;

  // 2. Recovering from a slow shot we slipped or guarded: grab them.
  if (t < memory.counterUntil && ready && foe.state !== 'hit') return grab();

  // 3. Finisher on a hurt foe: hook up close, roundhouse from range.
  if (foeHurt && ready && foe.state !== 'hit') {
    if (distance <= REACH.hook) return act('hook');
    if (distance <= REACH.roundhouse && Math.random() < 0.6) return act('roundhouse');
  }

  // 4. Step-in-and-throw plan in progress.
  if (t < memory.planUntil) return distance <= REACH.throw && ready ? act('throw') : { ...STAND, fwd: true };

  // Foe already inside throw reach and not attacking: throw.
  if (ready && distance <= REACH.throw && foe.state !== 'hit') return act('throw');

  // 5. Decide twice a second whether to commit to a grab.
  if (ready && t - memory.lastDecide >= 0.5 && distance > REACH.throw && distance <= 1.4 && foe.state !== 'hit') {
    memory.lastDecide = t;
    const still = foe.state === 'block' || foe.state === 'idle';
    let p = 0.22 + (still ? 0.13 : 0) + (behind && t > 18 ? 0.15 : 0);
    if (Math.random() < p) {
      if (foe.state !== 'block' && distance > REACH.takedown && distance <= REACH.sweep && Math.random() < 0.3) return act('sweep');
      memory.planUntil = t + 1.0;
      return { ...STAND, fwd: true };
    }
  }

  // 6. Pressure style: walk in, combinations in close, front kick from range.
  if (distance > 1.45) return Math.random() < 0.1 && ready && distance <= REACH.frontkick ? act('frontkick') : { ...STAND, fwd: true };
  if (!ready || Math.random() > 0.4) return foe.state === 'block' ? STAND : { ...STAND, block: Math.random() < 0.05 };
  if (distance <= REACH.combo && Math.random() < 0.2) return act('combo');
  if (distance <= REACH.onetwo) return act(Math.random() < 0.5 ? 'onetwo' : Math.random() < 0.5 ? 'jab' : 'cross');
  if (distance <= REACH.cross) return act('cross');
  return { ...STAND, fwd: true };
}
