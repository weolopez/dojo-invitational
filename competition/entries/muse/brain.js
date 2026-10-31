// Muse fight brain — Dojo Invitational entry, v6.
// Pure function, called 10x/sec by the arena. Only Math is used (sandbox-safe:
// no imports, no fetch, no timers, no DOM, no eval). Move data below mirrors
// MOVES in dojo/src/config.js under RULES v3.10: strike reaches are now
// measured from the clips (smallest over all fighter pairs, +2 cm), so
// jab is 0.90 m, roundhouse 1.17 m, sidekick 1.50 m -- and combo,
// uppercut, knee, front kick and sweep (reach under the 0.85 m minimum
// gap) no longer land at all. This brain NEVER throws those five moves;
// its close game is hook / cross / onetwo, its long game roundhouse /
// sidekick, and grabs (unchanged by v3.10) carry more of the offence
// than ever. Cooldowns below are this brain's own pacing, not arena
// timings; damage figures match config.js.
//
// Style: disciplined counter-striker with a grappling core. The tournament
// fight logs (results.jsonl, reviewed after every tournament) drive the
// tuning: strike hit-rates are low for everyone in this arena, while a
// landed takedown converts into guaranteed ground-and-pound damage, so the
// takedown is a primary weapon, not just an anti-guard tool. Defence mixes
// blocks with rate-limited dodges and slips (v4 evaded 26 times in one
// match and starved its own offence; v5 caps evades and always answers a
// slip with a punish strike). v6 re-cuts every range band to the v3.10
// clip-measured reaches and drops the five dead moves. At foe hp <= 30
// it hunts the knockdown with the knockdown strikes that still land
// (hook, roundhouse, spin kick). Stats are equal for everyone, so this
// brain is the edge.

// v3.10 reaches (config.js). DEAD under v3.10 -- never thrown by this
// brain, kept in the table only so defence can look up a foe's move:
// uppercut 0.70, frontkick 0.48, combo 0.70, knee 0.30, sweep 0.64.
const MOVES = {
  jab:        { dmg: 5,  reach: 0.90, cool: 0.50 },
  cross:      { dmg: 8,  reach: 0.84, cool: 0.60 },
  hook:       { dmg: 10, reach: 0.82, cool: 0.70 },
  uppercut:   { dmg: 14, reach: 0.70, cool: 0.85 },  // DEAD v3.10
  roundhouse: { dmg: 16, reach: 1.17, cool: 0.95 },
  frontkick:  { dmg: 12, reach: 0.48, cool: 0.80 },  // DEAD v3.10
  sidekick:   { dmg: 13, reach: 1.50, cool: 0.90 },
  lowkick:    { dmg: 9,  reach: 0.92, cool: 0.75 },
  spinkick:   { dmg: 17, reach: 0.82, cool: 1.05 },
  knee:       { dmg: 12, reach: 0.30, cool: 0.75 },  // DEAD v3.10
  onetwo:     { dmg: 12, reach: 0.92, cool: 0.80 },  // 5 + 7 over two blows
  combo:      { dmg: 20, reach: 0.70, cool: 1.05 },  // DEAD v3.10
  // Grabs (RULES.md section 5): unblockable, they miss a foe who is
  // mid-strike, dodging or already down, but catch a foe winding up or
  // recovering. The cool values here are this brain's own pacing.
  throw:      { dmg: 13, reach: 0.95, cool: 0.95 },
  takedown:   { dmg: 26, reach: 1.10, cool: 1.50 },  // 8 + four ground blows (4+4+5+5)
  sweep:      { dmg: 9,  reach: 0.64, cool: 0.90 },  // DEAD v3.10 (was 1.25)
  // Footwork: no damage; strikes and grabs miss during most of either.
  // attack() gives footwork a shorter cooldown than the table value.
  dodge:      { dmg: 0,  reach: 0,    cool: 0.70 },  // steps back 0.55 m
  slip:       { dmg: 0,  reach: 0,    cool: 0.70 },  // steps in 0.6 m, smothers kicks
};

const KICKS = ['roundhouse', 'frontkick', 'sidekick', 'lowkick', 'spinkick'];
const GRABS = ['throw', 'takedown'];
const FOOTWORK = ['dodge', 'slip'];

// v3.10 reach guard: never throw a strike or grab that cannot reach at
// the current distance (reach + 0.25 m slack: the foe may step in during
// the windup, and fighter.js judges the gap at the blow's window, not at
// the throw). If nothing in the table reaches, step in instead of
// wasting a cooldown window on a whiff -- under v3.10 most of the old
// range bands sit beyond the new clip-measured reaches, so this guard,
// not the band edges, is what keeps the offence real. The five dead
// moves never appear in a table at all, whatever the slack.
function pickWeighted(table, distance) {
  const ok = table.filter(([m]) => (MOVES[m].reach + 0.25) >= distance);
  if (!ok.length) return null;
  let total = 0;
  for (const row of ok) total += row[1];
  let r = Math.random() * total;
  for (const row of ok) { r -= row[1]; if (r <= 0) return row[0]; }
  return ok[0][0];
}

export default function brain(state) {
  const { me, foe, distance, time, memory } = state;
  const idle = { move: null, fwd: false, back: false, block: false };

  memory.lastAttack ??= -10;
  memory.coolUntil ??= 0;
  memory.lastFoeState ??= null;
  memory.foeThrewAt ??= -10;
  memory.evadeUntil ??= 0;
  memory.slippedAt ??= -10;
  // Round-timer reset (RULES v3.4): `time` restarts at 0 every round but
  // `memory` lasts the whole match, so a cooldown set late in round 1
  // (coolUntil > 30) would otherwise keep `ready` false for all of round 2,
  // and a stale foeThrewAt would fake a whiff window at round start.
  memory.lastTime ??= 0;
  if (time < memory.lastTime) {
    memory.coolUntil = 0; memory.foeThrewAt = -10;
    memory.evadeUntil = 0; memory.slippedAt = -10;
  }
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
    // Footwork recovers faster than a strike; strikes use the table.
    const cool = FOOTWORK.includes(move) ? 0.45 : MOVES[move].cool;
    memory.coolUntil = time + cool * (chasing ? 0.8 : 1);
    if (FOOTWORK.includes(move)) {
      // Rate-limit evades: never two inside ~1.1 s (the v4 log lesson).
      memory.evadeUntil = time + 1.1;
      if (move === 'slip') memory.slippedAt = time;
    }
    return { move, fwd: false, back: false, block: false };
  };
  // Strike from a table, or step in when nothing in it can reach.
  const strike = (table) => {
    const m = pickWeighted(table, distance);
    return m ? attack(m) : { move: null, fwd: true, back: false, block: false };
  };
  const ready = time >= memory.coolUntil;
  const canEvade = time >= memory.evadeUntil;
  const cornered = Math.abs(me.x) > 3.55;

  // ---- Defense -------------------------------------------------------------
  if (foe.state === 'attack' && foe.move && MOVES[foe.move]) {
    const reach = MOVES[foe.move].reach;
    if (GRABS.includes(foe.move)) {
      // A guard does nothing against a grab; evade it or give ground.
      if (distance <= reach + 0.3 && ready && canEvade && Math.random() < 0.65) return attack('dodge');
      if (distance <= reach + 0.3) return { move: null, fwd: false, back: !cornered, block: false };
    } else if (distance <= reach + 0.15) {
      // A kick can be slipped: stepping inside smothers it (half damage,
      // no knockdown) and leaves us in punishing range.
      if (KICKS.includes(foe.move) && ready && canEvade && Math.random() < 0.22) return attack('slip');
      if (ready && canEvade && Math.random() < 0.10) return attack('dodge');
      const p = MOVES[foe.move].dmg >= 12 ? 0.92 : 0.72;
      if (Math.random() < (protecting ? Math.min(1, p + 0.08) : p)) {
        return { move: null, fwd: false, back: false, block: true };
      }
    } else if (distance <= reach + 0.9 && ready) {
      // Out of range: their strike will whiff. Step in to punish the recovery.
      return { move: null, fwd: true, back: false, block: false };
    }
  }

  // ---- Answer a slip: we stepped inside, now punish before they reset -----
  if (time - memory.slippedAt < 0.6 && foe.state !== 'attack' && ready) {
    if (distance <= 1.0) return strike([['hook', 4], ['cross', 3], ['onetwo', 3]]);
    if (distance <= 1.3) return strike([['cross', 4], ['hook', 3]]);
  }

  // ---- Press a hit-stun: they cannot block while reacting ------------------
  if (foe.state === 'hit' && ready) {
    if (distance <= 0.97) return strike([['hook', 4], ['cross', 3], ['onetwo', 3]]);
    if (distance <= 1.1) return strike([['hook', 4], ['cross', 4], ['onetwo', 2]]);
    if (distance <= 1.22) return strike([['onetwo', 4], ['cross', 3], ['hook', 2], ['sidekick', 2]]);
    if (distance <= 1.32) return strike([['cross', 4], ['hook', 3], ['jab', 2], ['onetwo', 2]]);
    if (distance <= 1.62) return strike([['roundhouse', 3], ['sidekick', 3], ['jab', 1]]);
    return { move: null, fwd: true, back: false, block: false };
  }

  // ---- Punish a whiffed attack that just ended in range ---------------------
  // Grabs catch a foe who is recovering: close in, the punish is sometimes
  // the takedown itself (the log lesson: it is the reliable damage).
  if (foe.state !== 'attack' && time - memory.foeThrewAt < 0.45 && ready) {
    if (distance <= 1.12 && Math.random() < 0.35) return attack('takedown');
    if (distance <= 1.1) return strike([['hook', 4], ['cross', 4], ['onetwo', 2]]);
    if (distance <= 1.35) return strike([['cross', 4], ['hook', 3], ['lowkick', 2], ['onetwo', 2]]);
    if (distance <= 1.65) return strike([['roundhouse', 4], ['sidekick', 4]]);
  }

  // ---- Knockdown play: the foe is fragile, hunt the knockdown strikes -------
  if (foeFragile && ready && foe.state !== 'attack') {
    if (distance <= 1.1 && Math.random() < 0.18) return attack('takedown');
    if (distance <= 0.97) return strike([['hook', 5], ['cross', 3], ['onetwo', 2]]);
    if (distance <= 1.06) return strike([['hook', 5], ['cross', 4]]);
    if (distance <= 1.16) return strike([['hook', 5], ['spinkick', 3]]);
    if (distance <= 1.52) return strike([['roundhouse', 5], ['sidekick', 2]]);
    if (distance <= 1.62) return strike([['roundhouse', 4], ['sidekick', 4]]);
  }

  // ---- Spacing and offence by range band ------------------------------------
  if (foe.state === 'block') {
    // A guard stops strikes but not a grab, and a blocking foe is not
    // mid-strike, so a grab cannot miss for that reason. The takedown pays
    // more (ground-and-pound) and reaches further than the throw.
    if (distance <= 1.1 && ready && Math.random() < 0.60) return attack('takedown');
    if (distance <= 0.95 && ready) return attack('throw');
    if (distance > 1.25) return { move: null, fwd: true, back: false, block: false };
    if (ready && distance <= 1.05 && Math.random() < 0.35) return attack('jab');
    return idle;
  }

  if (distance > 1.68) {
    if (protecting && distance > 2.2) return idle; // let them come to us
    return { move: null, fwd: true, back: false, block: false };
  }
  if (distance > 1.38) {
    // Sometimes close to clinch range instead of kicking from the edge:
    // the takedown game needs distance <= 1.1, and kicks from maximum
    // range are the ones that whiff (the log lesson again).
    if (ready && distance <= 1.55 && foe.state !== 'attack' && Math.random() < 0.35) {
      return { move: null, fwd: true, back: false, block: false };
    }
    if (ready) return strike([['sidekick', 4], ['roundhouse', 3]]);
    return { move: null, fwd: !protecting, back: false, block: false };
  }
  if (distance > 1.12) {
    if (ready) {
      // Only sidekick (1.50 m) and roundhouse (1.17 m, inner part) reach
      // this band under v3.10; the reach guard drops the rest and the
      // fallback steps in. The sweep that used to live here is dead
      // under v3.10 (0.64 m).
      return strike([['sidekick', 4], ['roundhouse', 3], ['cross', 2], ['jab', 1]]);
    }
    return idle;
  }
  // Phone-booth range. The takedown is the primary weapon here (the log
  // lesson); a grab only when the foe is not mid-strike (it misses then).
  if (ready) {
    if (distance <= 1.1 && foe.state !== 'attack' && Math.random() < 0.35) return attack('takedown');
    if (distance <= 0.95 && foe.state !== 'attack' && Math.random() < 0.12) return attack('throw');
    return strike([['hook', 4], ['cross', 3], ['onetwo', 3], ['jab', 1]]);
  }
  // Not ready and inside the foe's grab reach: step out of 0.95 m rather
  // than wait in range of an unblockable grab (unless cornered). Dodge
  // only rarely here: the sim showed the old 0.35 pre-emptive dodge rate
  // made evades 43% of all moves against an idle foe -- the v4 evade
  // starvation pattern again, just slower. Stepping back is the calm
  // answer; the dodge stays for real grab threats (defence section).
  if (distance <= 0.95 && !cornered) {
    if (canEvade && Math.random() < 0.15) return attack('dodge');
    return { move: null, fwd: false, back: Math.random() < 0.65, block: false };
  }
  return { move: null, fwd: false, back: !cornered && Math.random() < 0.4, block: false };
}
