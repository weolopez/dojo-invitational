// Hermes fight brain — The Dojo Invitational (see competition/RULES.md §5).
// Pure, sandboxed (only Math available), called 10x/second, must return in <2ms.
//
// Design: stats are equal for everyone, so combat is won on spacing, timing and
// discipline — not on move values. The reach/damage economy of the arena is:
//   jab      reach 1.25  dmg 5   fast
//   cross    reach 1.30  dmg 8
//   hook     reach 1.15  dmg 10
//   uppercut reach 1.05  dmg 14  short, high reward
//   frontkick reach 1.50 dmg 12  long poke
//   roundhouse reach 1.60 dmg 16 longest reach, biggest reward
// Blocking cuts incoming damage to 15%. A whiffed attack leaves the foe busy
// for its whole clip, which is the moment to punish.
//
// Strategy:
//  1. Read the foe's committed attack. If they are attacking and in our hurt
//     range, block (turns a 14-16 dmg hit into ~2) unless we can beat them to it.
//  2. Punish a whiffed/finished foe attack: when the foe is busy at close range
//     and we are free, land the biggest guaranteed hit for the current gap.
//  3. Own the spacing: kick from long range, box in the pocket, never sit flat.
//  4. Stagger our own attacks so we aren't caught mid-whiff; add light,
//     bounded randomness so we are not perfectly predictable (Math.random only).

export default function brain(state) {
  const { me, foe, distance, time, memory } = state;
  memory.last ??= -10;     // time of our last committed attack
  memory.lastFoe ??= null; // foe move we last reacted to
  memory.aggr ??= 0.5;     // adaptive aggression, nudged by the exchange

  const idle = { move: null, fwd: false, back: false, block: false };

  // Match over or someone down: stop acting.
  if (me.state === 'ko' || foe.state === 'ko') return idle;
  if (me.state === 'victory' || foe.state === 'victory') return idle;

  // We are mid-animation (attack/hit/taunt). Input is ignored by the arena while
  // busy, so return neutral and save the cooldown math for when we're free.
  if (me.state === 'attack' || me.state === 'hit' || me.state === 'taunt') return idle;

  const since = time - memory.last;          // seconds since our last attack
  const ready = since > 0.42;                // respect the ~0.12s cooldown + recovery
  const foeAttacking = foe.state === 'attack';
  const lowHp = me.hp < me.maxHp * 0.3;
  const foeLow = foe.hp < foe.maxHp * 0.3;
  const winning = me.hp - foe.hp;

  // --- 1. Defense: the foe has committed to an attack. ---
  if (foeAttacking) {
    // In danger range of most strikes -> block the big ones, but try to beat
    // short-reach moves (uppercut/hook) with our own longer poke when we're ready.
    if (distance <= 1.65) {
      // If the foe's move is short-reach and we're spaced to kick, counter-poke.
      if (ready && distance > 1.35 && distance <= 1.6) {
        memory.last = time;
        return { move: 'roundhouse', fwd: false, back: false, block: false };
      }
      // Otherwise turtle up — blocking a 16-dmg roundhouse saves ~14 hp.
      return { move: null, fwd: false, back: false, block: true };
    }
    // Their attack can't reach us; drift in to punish the recovery.
    return { move: null, fwd: true, back: false, block: false };
  }

  // --- 2. Punish: foe is busy (recovering from a whiff) and can't act. ---
  const foeBusy = foe.state === 'hit' || foe.state === 'taunt';
  if (foeBusy && ready) {
    memory.last = time;
    // Pick the hardest move that reaches the current gap.
    const move = pickByReach(distance);
    return { move, fwd: distance > 1.1, back: false, block: false };
  }

  // --- 3. Spacing + offense when the foe is neutral. ---
  // Finish aggressively if they're hurt; play safer if we're hurt and ahead.
  const wantRetreat = lowHp && winning > 8 && distance < 1.0;
  if (wantRetreat) return { move: null, fwd: false, back: true, block: false };

  // Too far: close the gap (kick range is 1.5-1.6, so walk in to that band).
  if (distance > 1.62) return { move: null, fwd: true, back: false, block: false };

  // In range and ready: choose a strike for the band, with a little variety.
  if (ready) {
    memory.last = time;
    const aggressive = foeLow || winning < -6; // press when behind or for the kill
    const move = pickOffense(distance, aggressive);
    // Step in slightly for the short, high-damage moves so they connect.
    const stepIn = (move === 'uppercut' || move === 'hook') && distance > 1.05;
    return { move, fwd: stepIn, back: false, block: false };
  }

  // On cooldown but in the pocket: hold stance, slight backstep if crowded so we
  // don't eat a counter, otherwise stay centered and ready.
  if (distance < 0.95) return { move: null, fwd: false, back: true, block: false };
  return idle;
}

// Hardest move whose reach covers the gap (used when punishing a free foe).
function pickByReach(d) {
  if (d <= 1.05) return 'uppercut';   // 14
  if (d <= 1.15) return 'hook';       // 10
  if (d <= 1.30) return 'cross';      // 8
  if (d <= 1.50) return 'frontkick';  // 12
  return 'roundhouse';                // 16, reach 1.6
}

// Offensive pick with bounded variety so we're not fully predictable.
function pickOffense(d, aggressive) {
  const r = Math.random();
  if (d > 1.5) return 'roundhouse';                 // only the long kicks reach
  if (d > 1.32) return r < 0.6 ? 'frontkick' : 'roundhouse';
  if (d > 1.15) return r < 0.5 ? 'cross' : (aggressive ? 'cross' : 'jab');
  if (d > 1.05) return r < 0.55 ? 'hook' : 'cross'; // hook 10 dmg in the pocket
  // Very close: uppercut is the biggest in-pocket payout.
  return r < (aggressive ? 0.7 : 0.5) ? 'uppercut' : 'hook';
}
