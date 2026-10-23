export default function brain(state) {
  const { me, foe, distance } = state;
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

  // Blocking foe in grab range: throws ignore block.
  if (foe.state === 'block' && gap <= 0.7) {
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
