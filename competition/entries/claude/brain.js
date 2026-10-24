// CLAUDE's fight brain: a judoka.
// Closes to grappling range behind a mid guard and works for the takedown: a double-leg takedown that ends in
// ground-and-pound (blows on the opponent once they're down), a foot sweep, or a shoulder throw. Punches (jab,
// one-two) are only there to set up the shot: a foe who covers up is easier to take down. Against a slow kick it
// slips inside and shoots as the leg comes back. It keeps the round-reset fix from call #4.
const REACH = { jab: 1.25, cross: 1.3, hook: 1.15, uppercut: 1.05, roundhouse: 1.6, frontkick: 1.5, sidekick: 1.55,
  onetwo: 1.25, combo: 1.2, sweep: 1.25, throw: 0.95, takedown: 1.1 };
const SLOW = { roundhouse: 1.5, frontkick: 1.2, sidekick: 0.95, hook: 1.3, uppercut: 0.85, combo: 1.4 };
// When each slow shot's blow starts (seconds after it starts): slip just before it, so the slip covers it.
const BLOW = { roundhouse: 0.75, frontkick: 0.6, sidekick: 0.55, hook: 0.7, uppercut: 0.45, combo: 0.5 };
const STAND = { move: null, fwd: false, back: false, block: false };

export default function brain(state) {
  const { me, foe, distance, memory } = state;
  const t = state.time;
  // state.time restarts at 0 every round, but memory lasts the whole match: on a new round, forget the old timers.
  if (t < (memory.lastTime ?? 0)) {
    memory.lastMove = -10;
    memory.foeMoveAt = -10;
    memory.setupUntil = -1;
    memory.slippedAt = -10;
  }
  memory.lastTime = t;
  memory.lastMove ??= -10;
  memory.foeMoveAt ??= -10;
  memory.setupUntil ??= -1;
  memory.slippedAt ??= -10;

  if (me.state === 'ko' || foe.state === 'ko' || me.state === 'victory') return STAND;

  const foeAttacking = foe.state === 'attack';
  if (foeAttacking && !memory.foeWasAttacking) memory.foeMoveAt = t;
  memory.foeWasAttacking = foeAttacking;
  const elapsed = t - memory.foeMoveAt;

  const ready = t - memory.lastMove > 0.35;
  const act = (move) => { memory.lastMove = t; return { ...STAND, move }; };
  // The shot: a takedown from grappling range, a sweep a little further out, a throw from close.
  const shoot = () => {
    if (distance <= REACH.throw) return act(Math.random() < 0.6 ? 'takedown' : 'throw');
    if (distance <= REACH.takedown) return act('takedown');
    if (distance <= REACH.sweep) return act('sweep');
    return { ...STAND, fwd: true };
  };

  // 1. Defence. A slow kick or punch: slip inside early, or guard it, then shoot as it comes back.
  if (foeAttacking) {
    const slow = SLOW[foe.move];
    if (slow !== undefined && elapsed > slow) return ready ? shoot() : { ...STAND, fwd: true };
    if (slow !== undefined && ready && elapsed > BLOW[foe.move] - 0.3 && elapsed < BLOW[foe.move] && distance > 1.0 && distance < 1.6 && t - memory.slippedAt > 1.5) {
      memory.slippedAt = t;
      return act('slip');
    }
    if (distance <= (REACH[foe.move] ?? 1.3) + 0.05) return { ...STAND, block: true };
    return STAND;
  }

  // 2. Right after a set-up punch, or a foe covering up: shoot.
  if (ready && (t < memory.setupUntil || foe.state === 'block') && distance <= REACH.sweep) return shoot();
  // A foe standing still in grappling range: shoot.
  if (ready && foe.state === 'idle' && distance <= REACH.takedown) return shoot();

  // 3. A foe on the mat from our sweep or throw: wait over them (no hitting a downed fighter outside a takedown).
  if (foe.state === 'hit' && foe.hp < foe.maxHp && t - memory.lastMove < 2.5) return distance > 1.2 ? { ...STAND, fwd: true } : STAND;

  // 4. Close to grappling range; set up the shot with a jab or one-two.
  if (distance > 1.3) return { ...STAND, fwd: true };
  if (!ready) return STAND;
  if (Math.random() < 0.45) {
    memory.setupUntil = t + 0.9;
    return act(Math.random() < 0.5 ? 'jab' : 'onetwo');
  }
  if (distance > REACH.takedown) return { ...STAND, fwd: true };
  return Math.random() < 0.5 ? shoot() : STAND;
}
