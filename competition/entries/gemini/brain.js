// Gemini Tournament Fight Brain (Rules v3.7)
// Frame-Data Spacing, Grapple/Takedown/Sweep Guard-Break, Slip/Dodge Evasion & Knockdown Hunter AI
// Pure ES module function, zero external dependencies, < 0.05 ms per call.

const FOE_REACH = {
  jab: 1.25,
  cross: 1.30,
  hook: 1.15,
  uppercut: 1.05,
  onetwo: 1.30,
  combo: 1.30,
  knee: 0.95,
  lowkick: 1.35,
  frontkick: 1.50,
  sidekick: 1.55,
  roundhouse: 1.60,
  spinkick: 1.65,
  throw: 0.95,
  takedown: 1.10,
  sweep: 1.25
};

const FOE_ACTIVE_END = {
  jab: 0.42,
  cross: 0.50,
  hook: 0.62,
  uppercut: 0.65,
  onetwo: 0.72,
  combo: 1.15,
  knee: 0.55,
  lowkick: 0.54,
  frontkick: 0.62,
  sidekick: 0.65,
  roundhouse: 0.72,
  spinkick: 0.78,
  throw: 0.48,
  takedown: 0.52,
  sweep: 0.62
};

const KICK_MOVES = new Set(['lowkick', 'frontkick', 'sidekick', 'roundhouse', 'spinkick']);
const GRAPPLE_MOVES = new Set(['throw', 'takedown', 'sweep']);

export default function brain(state) {
  const { time, me, foe, distance, memory } = state;

  // Initialize persistent match memory
  if (memory.init !== true) {
    memory.init = true;
    memory.lastTime = time;
    memory.lastFoeState = 'idle';
    memory.foeAttackStart = -10;
    memory.foeAttackMove = null;
    memory.lastMeHp = me.hp;
    memory.lastFoeHp = foe.hp;
    memory.foeHitLanded = false;
    memory.foeBlockTicks = 0;
    memory.mixCounter = 0;
  }

  // Reset per-round trackers whenever the round clock resets
  if (time < (memory.lastTime ?? 0)) {
    memory.lastFoeState = 'idle';
    memory.foeAttackStart = -10;
    memory.foeAttackMove = null;
    memory.foeHitLanded = false;
    memory.foeBlockTicks = 0;
  }
  memory.lastTime = time;

  // Respect downed, thrown, or post-round states (nobody can hit a downed fighter)
  if (
    me.state === 'ko' ||
    foe.state === 'ko' ||
    me.state === 'down' ||
    foe.state === 'down' ||
    me.state === 'thrown' ||
    foe.state === 'thrown' ||
    me.state === 'victory' ||
    foe.state === 'victory'
  ) {
    return { move: null, fwd: false, back: false, block: false };
  }

  // Track opponent attack transitions and whether their strike already connected
  if (foe.state === 'attack') {
    if (memory.lastFoeState !== 'attack') {
      memory.foeAttackStart = time;
      memory.foeAttackMove = foe.move || 'roundhouse';
      memory.foeHitLanded = false;
    }
    if (me.hp < memory.lastMeHp) {
      memory.foeHitLanded = true;
    }
  } else {
    memory.foeHitLanded = false;
  }

  if (foe.state === 'block') {
    memory.foeBlockTicks += 1;
  } else {
    memory.foeBlockTicks = 0;
  }

  memory.lastFoeState = foe.state;
  memory.lastMeHp = me.hp;
  memory.lastFoeHp = foe.hp;

  // Knockdown mode when opponent is at or below 35% HP:
  // A clean hook, uppercut, knee, frontkick, roundhouse, or spinkick at <= 30% HP scores a knockdown!
  const foeLowHp = (foe.hp / (foe.maxHp || 100)) <= 0.36;

  function bestPunishForDistance(dist, preferFast, forceKnockdown) {
    if (forceKnockdown) {
      if (dist <= 0.94) return 'knee';
      if (dist <= 1.04) return 'uppercut';
      if (dist <= 1.14) return 'hook';
      if (dist <= 1.48) return 'frontkick';
      if (dist <= 1.59) return 'roundhouse';
      if (dist <= 1.64) return 'spinkick';
    }
    if (dist <= 0.94) return preferFast ? 'knee' : 'throw';
    if (dist <= 1.04) return preferFast ? 'jab' : 'uppercut';
    if (dist <= 1.09) return preferFast ? 'onetwo' : 'takedown';
    if (dist <= 1.14) return preferFast ? 'onetwo' : 'hook';
    if (dist <= 1.24) return preferFast ? 'onetwo' : 'sweep';
    if (dist <= 1.29) return preferFast ? 'cross' : 'combo';
    if (dist <= 1.34) return 'lowkick';
    if (dist <= 1.48) return 'frontkick';
    if (dist <= 1.54) return 'sidekick';
    if (dist <= 1.59) return 'roundhouse';
    if (dist <= 1.64) return 'spinkick';
    return null;
  }

  // 1. FREE PUNISH: Opponent is in hit-stun or taunting
  if (foe.state === 'hit' || foe.state === 'taunt') {
    const punish = bestPunishForDistance(distance, false, foeLowHp);
    if (punish !== null) {
      memory.mixCounter += 1;
      return { move: punish, fwd: false, back: false, block: false };
    }
    return { move: null, fwd: true, back: false, block: false };
  }

  // 2. DEFENSE, SLIP/DODGE & WHIFF/RECOVERY PUNISH: Opponent is mid-attack
  if (foe.state === 'attack') {
    const atkName = foe.move || memory.foeAttackMove || 'roundhouse';
    const foeReach = FOE_REACH[atkName] || 1.60;
    const activeEnd = FOE_ACTIVE_END[atkName] || 0.68;
    const elapsed = time - memory.foeAttackStart;

    // Once foe's active window ends, they are in recovery and CANNOT block throws/takedowns/sweeps or strikes!
    if (elapsed > activeEnd || memory.foeHitLanded) {
      // Recovering kickers cannot counter throws, takedowns, or sweeps
      if (KICK_MOVES.has(atkName)) {
        if (distance <= 0.94) return { move: 'throw', fwd: false, back: false, block: false };
        if (distance <= 1.09) return { move: 'takedown', fwd: false, back: false, block: false };
        if (distance <= 1.24) return { move: 'sweep', fwd: false, back: false, block: false };
      }
      const counter = bestPunishForDistance(distance, elapsed < activeEnd + 0.14, foeLowHp);
      if (counter !== null) {
        memory.mixCounter += 1;
        return { move: counter, fwd: false, back: false, block: false };
      }
      return { move: null, fwd: distance > 0.95, back: false, block: false };
    }

    // Unblockable grapples (throw/takedown/sweep) CANNOT be blocked -> back-step / dodge out or interrupt!
    if (GRAPPLE_MOVES.has(atkName)) {
      if (distance <= foeReach + 0.12) {
        return { move: 'dodge', fwd: false, back: true, block: false };
      }
      if (distance <= 1.48) {
        return { move: 'frontkick', fwd: false, back: false, block: false };
      }
    }

    // Against long-startup opponent kicks at mid-close range (0.95m..1.35m), slip inside (< 1.0m)
    // to smother their kick to half damage and set up an immediate clinch throw/takedown!
    if (KICK_MOVES.has(atkName) && elapsed < 0.25 && distance > 0.92 && distance <= 1.32) {
      return { move: 'slip', fwd: true, back: false, block: false };
    }

    // Near outer edge of their reach: micro-space or dodge backward to make them whiff for 0 damage
    if (distance > foeReach - 0.12 && distance <= foeReach + 0.16 && me.x > -3.9 && me.x < 3.9) {
      if (elapsed < 0.28 && distance <= foeReach + 0.04) {
        return { move: 'dodge', fwd: false, back: true, block: false };
      }
      return { move: null, fwd: false, back: true, block: false };
    }

    // Outside their reach entirely: counter-snipe with a longer-range kick
    if (distance > foeReach + 0.04 && distance <= 1.64) {
      const outrangeStrike = distance <= 1.34 ? 'lowkick' : (distance <= 1.48 ? 'frontkick' : (distance <= 1.59 ? 'roundhouse' : 'spinkick'));
      return { move: outrangeStrike, fwd: false, back: false, block: false };
    }

    // Inside danger zone during active frames -> solid guard
    if (distance <= foeReach + 0.12) {
      return { move: null, fwd: false, back: false, block: true };
    }
  }

  // 3. GUARD BREAK: Opponent is blocking -> Throws, Takedowns & Sweeps beat block!
  if (foe.state === 'block') {
    if (distance <= 0.94) {
      return { move: 'throw', fwd: false, back: false, block: false };
    }
    if (distance <= 1.09) {
      return { move: 'takedown', fwd: false, back: false, block: false };
    }
    if (distance <= 1.24) {
      return { move: 'sweep', fwd: false, back: false, block: false };
    }
    // Step in to grapple a turtling opponent
    return { move: null, fwd: true, back: false, block: false };
  }

  // 4. OFFENSIVE SPACING & MIXUPS (Opponent is idle, walking, or evading)
  if (distance > 1.64) {
    if (time > 23.0 && (me.hp / (me.maxHp || 100)) > (foe.hp / (foe.maxHp || 100)) + 0.10) {
      return { move: null, fwd: false, back: distance < 2.1, block: false };
    }
    return { move: null, fwd: true, back: false, block: false };
  }

  const slot = (Math.round(time * 12) + memory.mixCounter) % 5;

  // Long kicking range (1.31m to 1.64m): out-ranges all punches and grapples
  if (distance > 1.30) {
    memory.mixCounter += 1;
    if (foeLowHp) {
      if (distance <= 1.48) return { move: 'frontkick', fwd: false, back: false, block: false };
      if (distance <= 1.59) return { move: 'roundhouse', fwd: false, back: false, block: false };
      return { move: 'spinkick', fwd: false, back: false, block: false };
    }
    if (distance <= 1.35) {
      return { move: slot === 0 ? 'frontkick' : 'lowkick', fwd: false, back: false, block: false };
    }
    if (distance <= 1.49) {
      return { move: slot === 0 ? 'roundhouse' : 'frontkick', fwd: false, back: false, block: false };
    }
    if (distance <= 1.55) {
      return { move: slot <= 1 ? 'sidekick' : 'roundhouse', fwd: false, back: false, block: false };
    }
    return { move: slot === 0 ? 'spinkick' : 'roundhouse', fwd: false, back: false, block: false };
  }

  // Close-to-mid pocket (<= 1.30m): mix combos, knees, hooks/uppercuts, and sudden takedowns/sweeps
  memory.mixCounter += 1;
  if (foeLowHp) {
    if (distance <= 0.94) return { move: slot === 0 ? 'throw' : 'knee', fwd: false, back: false, block: false };
    if (distance <= 1.04) return { move: 'uppercut', fwd: false, back: false, block: false };
    if (distance <= 1.14) return { move: 'hook', fwd: false, back: false, block: false };
    return { move: 'frontkick', fwd: false, back: false, block: false };
  }

  if (distance <= 0.94) {
    const pick = slot === 0 ? 'throw' : (slot <= 2 ? 'knee' : 'uppercut');
    return { move: pick, fwd: false, back: false, block: false };
  }
  if (distance <= 1.05) {
    const pick = slot === 0 ? 'takedown' : (slot <= 2 ? 'uppercut' : 'onetwo');
    return { move: pick, fwd: false, back: false, block: false };
  }
  if (distance <= 1.15) {
    const pick = slot === 0 ? 'takedown' : (slot <= 2 ? 'hook' : 'onetwo');
    return { move: pick, fwd: false, back: false, block: false };
  }
  const pick = slot === 0 ? 'sweep' : (slot <= 2 ? 'onetwo' : 'combo');
  return { move: pick, fwd: false, back: false, block: false };
}
