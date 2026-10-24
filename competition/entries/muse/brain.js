// Muse fight brain — Dojo Invitational entry.
// Pure function, called 10x/sec by the arena. Only Math is used (sandbox-safe:
// no imports, no fetch, no timers, no DOM, no eval). Move data below mirrors
// MOVES in dojo/src/main.js as published in competition/RULES.md section 5.
//
// Style: disciplined counter-striker. Fight at the edge of roundhouse range,
// block what can hurt, punish whiffs and hit-stuns, and manage the clock:
// protect a lead late, chase a deficit late. Stats are equal for everyone,
// so this brain is the whole edge.

const MOVES = {
  jab:        { dmg: 5,  reach: 1.25, cool: 0.55 },
  cross:      { dmg: 8,  reach: 1.30, cool: 0.65 },
  hook:       { dmg: 10, reach: 1.15, cool: 0.75 },
  uppercut:   { dmg: 14, reach: 1.05, cool: 0.90 },
  roundhouse: { dmg: 16, reach: 1.60, cool: 1.00 },
  frontkick:  { dmg: 12, reach: 1.50, cool: 0.85 },
};

function pickWeighted(table) {
  let total = 0;
  for (const row of table) total += row[1];
  let r = Math.random() * total;
  for (const row of table) { r -= row[1]; if (r <= 0) return row[0]; }
  return table[0][0];
}

export default function brain(state) {
  const { me, foe, distance, time, memory } = state;
  const idle = { move: null, fwd: false, back: false, block: false };

  memory.lastAttack ??= -10;
  memory.coolUntil ??= 0;
  memory.lastFoeState ??= null;
  memory.foeThrewAt ??= -10;

  if (me.state === 'ko' || foe.state === 'ko') return idle;
  if (me.state === 'hit' || me.state === 'attack') return idle;

  const hpDiff = me.hp - foe.hp;
  const late = time > 42;
  const protecting = late && hpDiff >= 10;   // ahead late: bank the lead
  const chasing = late && hpDiff <= -10;     // behind late: take risks

  // Remember when the foe starts an attack so we can punish the recovery.
  if (foe.state === 'attack' && memory.lastFoeState !== 'attack') memory.foeThrewAt = time;
  memory.lastFoeState = foe.state;

  const attack = (move) => {
    memory.lastAttack = time;
    memory.coolUntil = time + MOVES[move].cool * (chasing ? 0.8 : 1);
    return { move, fwd: false, back: false, block: false };
  };
  const ready = time >= memory.coolUntil;

  // ---- Defense: block what can actually reach me, scaled by its damage ----
  if (foe.state === 'attack' && foe.move && MOVES[foe.move]) {
    const reach = MOVES[foe.move].reach;
    if (distance <= reach + 0.15) {
      const p = MOVES[foe.move].dmg >= 12 ? 0.92 : 0.72;
      if (Math.random() < (protecting ? Math.min(1, p + 0.08) : p)) {
        return { move: null, fwd: false, back: false, block: true };
      }
    } else if (distance <= reach + 0.9 && ready) {
      // Out of range: their strike will whiff. Step in to punish the recovery.
      return { move: null, fwd: true, back: false, block: false };
    }
  }

  // ---- Press a hit-stun: they cannot block while reacting ----
  if (foe.state === 'hit' && ready) {
    if (distance <= 1.1) return attack(pickWeighted([['uppercut', 4], ['hook', 4], ['cross', 2]]));
    if (distance <= 1.32) return attack(pickWeighted([['cross', 4], ['hook', 3], ['jab', 2]]));
    if (distance <= 1.62) return attack(pickWeighted([['frontkick', 3], ['roundhouse', 3], ['jab', 1]]));
    return { move: null, fwd: true, back: false, block: false };
  }

  // ---- Punish a whiffed attack that just ended in range ----
  if (foe.state !== 'attack' && time - memory.foeThrewAt < 0.45 && ready) {
    if (distance <= 1.1) return attack(pickWeighted([['uppercut', 3], ['hook', 4], ['cross', 3]]));
    if (distance <= 1.35) return attack(pickWeighted([['cross', 4], ['hook', 3], ['frontkick', 2]]));
    if (distance <= 1.65) return attack(pickWeighted([['roundhouse', 4], ['frontkick', 4]]));
  }

  // ---- Corner escape: never keep backing into the wall ----
  const cornered = Math.abs(me.x) > 3.55;

  // ---- Spacing and offence by range band ----
  if (foe.state === 'block') {
    // Do not feed heavy strikes into a guard. Close in, test with a jab.
    if (distance > 1.25) return { move: null, fwd: true, back: false, block: false };
    if (ready && Math.random() < 0.35) return attack('jab');
    return idle;
  }

  if (distance > 1.68) {
    if (protecting && distance > 2.2) return idle; // let them come to us
    return { move: null, fwd: true, back: false, block: false };
  }
  if (distance > 1.38) {
    if (ready) return attack(pickWeighted([['roundhouse', 5], ['frontkick', 4], ['jab', 1]]));
    return { move: null, fwd: !protecting, back: false, block: false };
  }
  if (distance > 1.12) {
    if (ready) return attack(pickWeighted([['cross', 4], ['jab', 3], ['frontkick', 2], ['hook', 2]]));
    return idle;
  }
  // Phone-booth range.
  if (ready) return attack(pickWeighted([['hook', 4], ['uppercut', 4], ['cross', 2], ['jab', 1]]));
  return { move: null, fwd: false, back: !cornered && Math.random() < 0.4, block: false };
}
