// Example fight brain. Copy it into your own entry folder and make it smarter.
export default function brain(state) {
  const { me, foe, distance, memory } = state;
  memory.lastAttack ??= -10;

  if (me.state === 'ko' || foe.state === 'ko') return { move: null, fwd: false, back: false, block: false };

  // Block when the opponent is mid-attack and close.
  if (foe.state === 'attack' && distance < 1.6 && Math.random() < 0.5) {
    return { move: null, fwd: false, back: false, block: true };
  }
  // Close the distance, then mix jabs and kicks.
  if (distance > 1.45) return { move: null, fwd: true, back: false, block: false };
  if (state.time - memory.lastAttack > 0.6) {
    memory.lastAttack = state.time;
    const move = distance > 1.25 ? 'roundhouse' : ['jab', 'cross', 'hook'][Math.floor(Math.random() * 3)];
    return { move, fwd: false, back: false, block: false };
  }
  return { move: null, fwd: false, back: distance < 0.95, block: false };
}
