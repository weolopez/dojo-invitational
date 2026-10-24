export default function brain(state) {
  const { me, foe, distance } = state;
  const memory = state.memory ?? {};
  const gap = Number.isFinite(distance) ? Math.max(0, distance) : Infinity;

  if (me.state === 'ko' || me.state === 'victory' || me.state === 'taunt') {
    return { move: null, fwd: false, back: false, block: false };
  }

  if (me.state === 'attack' || me.state === 'hit') {
    return { move: null, fwd: false, back: false, block: false };
  }

  if (foe.state === 'attack') {
    if (gap <= 1.85) {
      return { move: null, fwd: false, back: false, block: true };
    }
    return { move: null, fwd: true, back: false, block: false };
  }

  // Knockdown play: once per round, when the foe is at <=30% hp and not blocking, go for a launcher.
  // A long 'hit' spell is treated as the knockdown so we stop chasing it for the rest of the round.
  if (memory.round !== state.round) { memory.round = state.round; memory.kdDone = false; memory.hitSince = null; }
  if (foe.state === 'hit') { memory.hitSince ??= state.time; if (state.time - memory.hitSince > 1.2) memory.kdDone = true; }
  else memory.hitSince = null;
  if (!memory.kdDone && foe.maxHp && foe.hp <= 0.3 * foe.maxHp && foe.state !== 'block') {
    if (gap > 1.15) return { move: null, fwd: true, back: false, block: false };
    return { move: gap <= 1.05 ? 'uppercut' : 'hook', fwd: false, back: false, block: false };
  }

  // Blocking foe in grab range: throws ignore block.
  if (foe.state === 'block' && gap < 0.95) {
    return { move: 'throw', fwd: false, back: false, block: false };
  }
  if (foe.state === 'block' && gap <= 1.3) {
    return { move: null, fwd: true, back: false, block: false };
  }

  if (gap > 1.6) {
    return { move: null, fwd: true, back: false, block: false };
  }

  if (gap <= 1.05) {
    return { move: 'uppercut', fwd: false, back: false, block: false };
  }

  return { move: 'roundhouse', fwd: false, back: false, block: false };
}
