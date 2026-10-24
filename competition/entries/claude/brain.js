// CLAUDE's fight brain: a patient counter-striker.
// Holds just outside the opponent's reach, blocks committed attacks, and punishes the recovery after a whiff
// or a blocked strike. Mixes in long kicks when the opponent stands still at kicking range.
const REACH = { jab: 1.25, cross: 1.3, hook: 1.15, uppercut: 1.05, roundhouse: 1.6, frontkick: 1.5 };
const STAND = { move: null, fwd: false, back: false, block: false };

export default function brain(state) {
  const { me, foe, distance, memory } = state;
  memory.lastMove ??= -10;
  memory.foeWasAttacking ??= false;
  memory.punishUntil ??= -1;

  if (me.state === 'ko' || foe.state === 'ko' || me.state === 'victory') return STAND;

  const foeAttacking = foe.state === 'attack';
  const foeReach = foe.move ? REACH[foe.move] ?? 1.3 : 1.3;
  // A foe that just finished an attack, or got hit, is open for a moment.
  if (memory.foeWasAttacking && !foeAttacking) memory.punishUntil = state.time + 0.5;
  if (foe.state === 'hit') memory.punishUntil = state.time + 0.4;
  memory.foeWasAttacking = foeAttacking;

  // 1. Defend: block anything that can reach us.
  if (foeAttacking && distance <= foeReach + 0.15) return { ...STAND, block: true };

  const ready = state.time - memory.lastMove > 0.45;
  const strike = (move) => { memory.lastMove = state.time; return { ...STAND, move }; };

  // 2. Punish the opening with the best strike that reaches.
  if (ready && state.time < memory.punishUntil) {
    if (distance <= REACH.hook) return strike(me.hp < foe.hp ? 'uppercut' : 'hook');
    if (distance <= REACH.cross) return strike('cross');
    if (distance <= REACH.roundhouse) return strike('roundhouse');
    return { ...STAND, fwd: true };
  }

  // 3. Clinch range: a foe who turtles up (or stands still) inside 0.95 m gets thrown; throws beat the block.
  if (ready && distance <= 0.95 && (foe.state === 'block' || foe.state === 'idle')) return strike('throw');

  // 4. Range control: hover at kicking range, just outside punching range.
  if (distance > 1.7) return { ...STAND, fwd: true };
  if (distance < 1.1) return ready && Math.random() < 0.5 ? strike('jab') : { ...STAND, back: true };

  // 5. Opportunistic kicks at long range; a trailing foe on low health gets pressed.
  if (ready && (foe.state === 'idle' || foe.state === 'walk_b')) {
    if (foe.hp < 30 && distance <= REACH.cross) return strike('cross');
    if (Math.random() < 0.35) return strike(distance > 1.4 ? 'roundhouse' : 'frontkick');
  }
  return STAND;
}
