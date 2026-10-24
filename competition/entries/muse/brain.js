// Muse fight brain — Dojo Invitational entry.
// Pure function, called 10x/sec by the arena. Only Math is used (sandbox-safe:
// no imports, no fetch, no timers, no DOM, no eval). Move data below mirrors
// MOVES in dojo/src/config.js as published in competition/RULES.md section 5
// (v3.5-v3.7 move set).
//
// Style: disciplined counter-striker. Fight at the edge of roundhouse range,
// block what can hurt, slip or dodge what can be evaded, punish whiffs and
// hit-stuns, and manage the clock: protect a lead late, chase a deficit late.
// At foe hp <= 30 it hunts the knockdown with the knockdown strikes (hook,
// uppercut, roundhouse, front kick, spin kick, knee). Against a guard it
// prefers the takedown (unblockable, ground-and-pound) over the throw; a
// sweep drops a foe who is not blocking. Stats are equal for everyone, so
// this brain is the whole edge.

const MOVES = {
  jab:        { dmg: 5,  reach: 1.25, cool: 0.55 },
  cross:      { dmg: 8,  reach: 1.30, cool: 0.65 },
  hook:       { dmg: 10, reach: 1.15, cool: 0.75 },
  uppercut:   { dmg: 14, reach: 1.05, cool: 0.90 },
  roundhouse: { dmg: 16, reach: 1.60, cool: 1.00 },
  frontkick:  { dmg: 12, reach: 1.50, cool: 0.85 },
  sidekick:   { dmg: 13, reach: 1.55, cool: 0.95 },
  lowkick:    { dmg: 9,  reach: 1.45, cool: 0.80 },
  spinkick:   { dmg: 17, reach: 1.60, cool: 1.15 },
  knee:       { dmg: 12, reach: 0.95, cool: 0.80 },
  onetwo:     { dmg: 12, reach: 1.25, cool: 0.85 },  // 5 + 7 over two blows
  combo:      { dmg: 20, reach: 1.20, cool: 1.15 },  // 4 + 4 + 5 + 7 over four blows
  // Grabs (RULES.md section 5): unblockable, they miss a foe who is
  // mid-strike, dodging or already down. The cool values here are this
  // brain's own pacing, not arena stats.
  throw:      { dmg: 13, reach: 0.95, cool: 1.00 },
  takedown:   { dmg: 26, reach: 1.10, cool: 1.60 },  // 8 + four ground blows (4+4+5+5)
  sweep:      { dmg: 9,  reach: 1.25, cool: 0.95 },  // drops a foe who is not blocking
  // Footwork: no damage; strikes and grabs miss during most of either.
  dodge:      { dmg: 0,  reach: 0,    cool: 0.70 },  // steps back 0.55 m
  slip:       { dmg: 0,  reach: 0,    cool: 0.70 },  // steps in 0.6 m, smothers kicks
};

const KICKS = ['roundhouse', 'frontkick', 'sidekick', 'lowkick', 'spinkick'];
const GRABS = ['throw', 'takedown'];

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
  // Round-timer reset (RULES v3.4): `time` restarts at 0 every round but
  // `memory` lasts the whole match, so a cooldown set late in round 1
  // (coolUntil > 30) would otherwise keep `ready` false for all of round 2,
  // and a stale foeThrewAt would fake a whiff window at round start.
  memory.lastTime ??= 0;
  if (time < memory.lastTime) { memory.coolUntil = 0; memory.foeThrewAt = -10; }
  memory.lastTime = time;

  if (me.state === 'ko' || foe.state === 'ko') return idle;
  if (me.state === 'hit' || me.state === 'attack') return idle;

  const hpDiff = me.hp - foe.hp;
  const late = time > 24; // final 6 s of a 30 s round (RULES section 8); time restarts each round
  const protecting = late && hpDiff >= 10;   // ahead late: bank the lead
  const chasing = late && hpDiff <= -10;     // behind late: take risks
  const foeFragile = foe.hp <= 30;           // one clean knockdown strike = knockdown

  // Remember when the foe starts an attack so we can punish the recovery.
  if (foe.state === 'attack' && memory.lastFoeState !== 'attack') memory.foeThrewAt = time;
  memory.lastFoeState = foe.state;

  const attack = (move) => {
    memory.lastAttack = time;
    memory.coolUntil = time + MOVES[move].cool * (chasing ? 0.8 : 1);
    return { move, fwd: false, back: false, block: false };
  };
  const ready = time >= memory.coolUntil;
  const cornered = Math.abs(me.x) > 3.55;

  // ---- Defense -------------------------------------------------------------
  if (foe.state === 'attack' && foe.move && MOVES[foe.move]) {
    const reach = MOVES[foe.move].reach;
    if (GRABS.includes(foe.move)) {
      // A guard does nothing against a grab; evade it or give ground.
      if (distance <= reach + 0.3 && ready && Math.random() < 0.65) return attack('dodge');
      if (distance <= reach + 0.3) return { move: null, fwd: false, back: !cornered, block: false };
    } else if (distance <= reach + 0.15) {
      // A kick can be slipped: stepping inside smothers it (half damage,
      // no knockdown) and leaves us in punishing range.
      if (KICKS.includes(foe.move) && ready && Math.random() < 0.30) return attack('slip');
      if (ready && Math.random() < 0.18) return attack('dodge');
      const p = MOVES[foe.move].dmg >= 12 ? 0.92 : 0.72;
      if (Math.random() < (protecting ? Math.min(1, p + 0.08) : p)) {
        return { move: null, fwd: false, back: false, block: true };
      }
    } else if (distance <= reach + 0.9 && ready) {
      // Out of range: their strike will whiff. Step in to punish the recovery.
      return { move: null, fwd: true, back: false, block: false };
    }
  }

  // ---- Press a hit-stun: they cannot block while reacting ------------------
  if (foe.state === 'hit' && ready) {
    if (distance <= 0.97) return attack(pickWeighted([['knee', 3], ['uppercut', 4], ['hook', 3]]));
    if (distance <= 1.1) return attack(pickWeighted([['uppercut', 4], ['hook', 4], ['cross', 2]]));
    if (distance <= 1.22) return attack(pickWeighted([['combo', 4], ['cross', 3], ['hook', 2]]));
    if (distance <= 1.32) return attack(pickWeighted([['cross', 4], ['hook', 3], ['jab', 2], ['onetwo', 2]]));
    if (distance <= 1.62) return attack(pickWeighted([['frontkick', 3], ['roundhouse', 3], ['jab', 1]]));
    return { move: null, fwd: true, back: false, block: false };
  }

  // ---- Punish a whiffed attack that just ended in range ---------------------
  if (foe.state !== 'attack' && time - memory.foeThrewAt < 0.45 && ready) {
    if (distance <= 1.1) return attack(pickWeighted([['uppercut', 3], ['hook', 4], ['cross', 3]]));
    if (distance <= 1.35) return attack(pickWeighted([['cross', 4], ['hook', 3], ['frontkick', 2], ['onetwo', 2]]));
    if (distance <= 1.65) return attack(pickWeighted([['roundhouse', 4], ['frontkick', 4]]));
  }

  // ---- Knockdown play: the foe is fragile, hunt the knockdown strikes -------
  if (foeFragile && ready && foe.state !== 'attack') {
    if (distance <= 0.97) return attack(pickWeighted([['knee', 4], ['uppercut', 4], ['hook', 3]]));
    if (distance <= 1.06) return attack(pickWeighted([['uppercut', 5], ['hook', 4]]));
    if (distance <= 1.16) return attack(pickWeighted([['hook', 5], ['uppercut', 3]]));
    if (distance <= 1.52) return attack(pickWeighted([['frontkick', 4], ['roundhouse', 3]]));
    if (distance <= 1.62) return attack(pickWeighted([['spinkick', 4], ['roundhouse', 4], ['frontkick', 2]]));
  }

  // ---- Spacing and offence by range band ------------------------------------
  if (foe.state === 'block') {
    // A guard stops strikes but not a grab, and a blocking foe is not
    // mid-strike, so a grab cannot miss for that reason. The takedown pays
    // more (ground-and-pound) and reaches further than the throw.
    if (distance <= 1.1 && ready && Math.random() < 0.55) return attack('takedown');
    if (distance <= 0.95 && ready) return attack('throw');
    if (distance > 1.25) return { move: null, fwd: true, back: false, block: false };
    if (ready && Math.random() < 0.35) return attack('jab');
    return idle;
  }

  if (distance > 1.68) {
    if (protecting && distance > 2.2) return idle; // let them come to us
    return { move: null, fwd: true, back: false, block: false };
  }
  if (distance > 1.38) {
    if (ready) return attack(pickWeighted([['roundhouse', 5], ['spinkick', 3], ['frontkick', 4], ['sidekick', 3], ['lowkick', 2], ['jab', 1]]));
    return { move: null, fwd: !protecting, back: false, block: false };
  }
  if (distance > 1.12) {
    if (ready) {
      // The sweep drops a foe who is not blocking (checked above), but only
      // inside its 1.25 m reach: mix it in only in the inner part of the band.
      if (distance <= 1.27) return attack(pickWeighted([['cross', 4], ['jab', 3], ['frontkick', 2], ['hook', 2], ['sweep', 3], ['onetwo', 3], ['lowkick', 2]]));
      return attack(pickWeighted([['cross', 4], ['jab', 3], ['frontkick', 2], ['hook', 2], ['onetwo', 3], ['lowkick', 2]]));
    }
    return idle;
  }
  // Phone-booth range. A grab only when the foe is not mid-strike
  // (it misses then) and we are inside its reach.
  if (ready) {
    if (distance <= 1.1 && foe.state !== 'attack' && Math.random() < 0.14) return attack('takedown');
    if (distance <= 0.95 && foe.state !== 'attack' && Math.random() < 0.16) return attack('throw');
    return attack(pickWeighted([['hook', 4], ['uppercut', 4], ['knee', 3], ['cross', 2], ['jab', 1]]));
  }
  // Not ready and inside the foe's grab reach: dodge or step out of 0.95 m
  // rather than wait in range of an unblockable grab (unless cornered).
  if (distance <= 0.95 && !cornered) {
    if (Math.random() < 0.35) return attack('dodge');
    return { move: null, fwd: false, back: Math.random() < 0.65, block: false };
  }
  return { move: null, fwd: false, back: !cornered && Math.random() < 0.4, block: false };
}
