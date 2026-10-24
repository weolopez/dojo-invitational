// THE OWNER's fight brain: a pressure fighter.
// Walks forward behind a high guard, blocks strikes that can land, fires short combinations in close, and throws an
// opponent who turtles up behind a block. Starter brain: the owner's agents are welcome to improve it.
const REACH = { jab: 1.25, cross: 1.3, hook: 1.15, uppercut: 1.05, roundhouse: 1.6, frontkick: 1.5, throw: 0.95 };
const STAND = { move: null, fwd: false, back: false, block: false };

export default function brain(state) {
  const { me, foe, distance, memory } = state;
  memory.lastMove ??= -10;
  memory.combo ??= 0;
  if (memory.round !== undefined && memory.round !== state.round) memory.kdDone = false;
  if (me.state === 'ko' || foe.state === 'ko' || me.state === 'victory') return STAND;

  const foeReach = foe.move ? REACH[foe.move] ?? 1.3 : 1.3;
  if (foe.state === 'attack' && distance <= foeReach + 0.1) return { ...STAND, block: true };

  const ready = state.time - memory.lastMove > 0.38;
  const strike = (move) => { memory.lastMove = state.time; memory.combo++; return { ...STAND, move }; };

  // A foe hiding behind a block gets thrown.
  if (ready && foe.state === 'block' && distance <= REACH.throw) return strike('throw');
  // Close the distance.
  if (distance > REACH.cross) {
    if (ready && distance <= REACH.frontkick && Math.random() < 0.25) return strike('frontkick');
    return { ...STAND, fwd: true };
  }
  if (!ready) return STAND;
  // Knockdown play: once the foe is at or below 30 % health, a clean hook (in reach) or uppercut can drop them,
  // once per round. Track a long 'hit' spell as the knockdown so we stop chasing it for the rest of the round.
  if (memory.round !== state.round) { memory.round = state.round; memory.kdDone = false; memory.hitSince = null; }
  if (foe.state === 'hit') { memory.hitSince ??= state.time; if (state.time - memory.hitSince > 1.2) memory.kdDone = true; }
  else memory.hitSince = null;
  if (!memory.kdDone && foe.hp <= 0.3 * foe.maxHp && foe.state !== 'block') {
    if (distance > REACH.hook) return { ...STAND, fwd: true };
    memory.combo = 0;
    return strike(distance <= REACH.uppercut ? 'uppercut' : 'hook');
  }
  // In close: jab, cross, then a power shot; reset the combination after three.
  if (memory.combo >= 3) memory.combo = 0;
  return strike(['jab', 'cross', me.hp >= foe.hp ? 'hook' : 'uppercut'][memory.combo]);
}
