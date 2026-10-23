// Gemini Tournament Fight Brain — Frame-Data Spacing, Whiff/Block Punish & Hit-Confirm AI
// Pure ES module function, zero external dependencies, < 0.05 ms per call.

export default function brain(state) {
  const { time, me, foe, distance, memory } = state;

  // Initialize persistent match memory
  if (memory.init !== true) {
    memory.init = true;
    memory.lastFoeState = 'idle';
    memory.foeAttackStart = -10;
    memory.foeAttackMove = null;
    memory.lastMeHp = me.hp;
    memory.lastFoeHp = foe.hp;
    memory.foeHitLanded = false;
    memory.lastAttackTime = -10;
    memory.foeBlockTicks = 0;
    memory.aggression = 0;
  }

  // Reset per-round trackers if clock rewound for a new round
  if (time < memory.lastTime - 1.0) {
    memory.lastFoeState = 'idle';
    memory.foeAttackStart = -10;
    memory.foeAttackMove = null;
    memory.foeHitLanded = false;
    memory.lastAttackTime = -10;
    memory.foeBlockTicks = 0;
  }
  memory.lastTime = time;

  // Do nothing if either fighter is knocked out or round is over
  if (me.state === 'ko' || foe.state === 'ko' || me.state === 'victory' || foe.state === 'victory') {
    return { move: null, fwd: false, back: false, block: false };
  }

  // Exact arena move reach & active-window end times (in seconds)
  const FOE_REACH = {
    jab: 1.25,
    cross: 1.30,
    hook: 1.15,
    uppercut: 1.05,
    frontkick: 1.50,
    roundhouse: 1.60
  };
  const FOE_ACTIVE_END = {
    jab: 0.42,
    cross: 0.50,
    hook: 0.62,
    uppercut: 0.65,
    frontkick: 0.62,
    roundhouse: 0.72
  };

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

  // Helper: pick highest-reward move for current exact distance
  function bestStrikeForDistance(dist, preferFast) {
    if (dist <= 1.03) return preferFast ? 'jab' : 'uppercut';      // 14 dmg (or 5 dmg fast)
    if (dist <= 1.13) return preferFast ? 'jab' : 'hook';          // 10 dmg
    if (dist <= 1.23) return preferFast ? 'jab' : 'cross';         // 8 dmg (or 5 dmg fast)
    if (dist <= 1.29) return 'cross';                              // 8 dmg, 1.30m reach
    if (dist <= 1.48) return 'frontkick';                          // 12 dmg, 0.30 startup, 1.50m reach
    if (dist <= 1.59) return 'roundhouse';                         // 16 dmg, 1.60m reach
    return null;
  }

  // 1. FREE PUNISH: Opponent is in hit-stun or taunting (cannot block or counter!)
  if (foe.state === 'hit' || foe.state === 'taunt') {
    const punish = bestStrikeForDistance(distance, false);
    if (punish !== null) {
      memory.lastAttackTime = time;
      return { move: punish, fwd: false, back: false, block: false };
    }
    return { move: null, fwd: true, back: false, block: false };
  }

  // 2. DEFENSE & WHIFF/RECOVERY PUNISH: Opponent is mid-attack
  if (foe.state === 'attack') {
    const atkName = foe.move || memory.foeAttackMove || 'roundhouse';
    const foeReach = FOE_REACH[atkName] || 1.60;
    const activeEnd = FOE_ACTIVE_END[atkName] || 0.68;
    const elapsed = time - memory.foeAttackStart;

    // If their active window is over OR they already hit our block, they are in recovery and CANNOT block!
    if (elapsed > activeEnd || memory.foeHitLanded) {
      const counter = bestStrikeForDistance(distance, elapsed < activeEnd + 0.15);
      if (counter !== null) {
        memory.lastAttackTime = time;
        return { move: counter, fwd: false, back: false, block: false };
      }
      // Step in to punish their recovery if slightly out of range
      return { move: null, fwd: distance > 1.0, back: false, block: false };
    }

    // Foe strike is still in startup/active phase:
    // If we are near the outer edge of their reach, micro-space backward to make them whiff for 0 damage
    if (distance > foeReach - 0.10 && distance <= foeReach + 0.18 && me.x > -3.9 && me.x < 3.9) {
      return { move: null, fwd: false, back: true, block: false };
    }

    // If we are outside their reach entirely, punish immediately with a longer-range kick!
    if (distance > foeReach + 0.04 && distance <= 1.59) {
      const outrangeStrike = distance <= 1.48 ? 'frontkick' : 'roundhouse';
      memory.lastAttackTime = time;
      return { move: outrangeStrike, fwd: false, back: false, block: false };
    }

    // Inside their danger zone during active frames -> solid block (85% damage reduction, zero hit-stun)
    if (distance <= foeReach + 0.12) {
      return { move: null, fwd: false, back: false, block: true };
    }
  }

  // 3. OFFENSIVE SPACING & PRESSURE (Opponent is idle, walking, or blocking)
  // Out of maximum attack range (> 1.59m): advance into the 1.32m–1.56m kicking sweet spot
  if (distance > 1.59) {
    // If we hold a strong HP lead in the final 8 seconds, let the opponent come to us
    if (time > 52.0 && (me.hp / me.maxHp) > (foe.hp / foe.maxHp) + 0.08) {
      return { move: null, fwd: false, back: distance < 2.1, block: false };
    }
    return { move: null, fwd: true, back: false, block: false };
  }

  // Kicking sweet spot (1.31m to 1.59m): we can land frontkick (12 dmg) & roundhouse (16 dmg)
  // while all opponent punches (max 1.30m) cannot reach us!
  if (distance > 1.30 && distance <= 1.59) {
    const kickMove = distance <= 1.48 ? 'frontkick' : 'roundhouse';
    memory.lastAttackTime = time;
    return { move: kickMove, fwd: false, back: false, block: false };
  }

  // Close-range pocket (<= 1.30m):
  // If opponent is turtling in block, use high-chip heavy strikes (uppercut = 3 chip, roundhouse = 3 chip)
  if (foe.state === 'block') {
    if (distance <= 1.04) {
      memory.lastAttackTime = time;
      return { move: 'uppercut', fwd: false, back: false, block: false };
    }
    // Step back slightly into kick range to chip safely from outside punch range
    if (distance < 1.32 && me.x > -3.8 && me.x < 3.8) {
      return { move: null, fwd: false, back: true, block: false };
    }
  }

  // Opponent is idle or walking in close range (<= 1.30m):
  // Mix fast frame-trap strikes (jab/cross) with heavy knockdowns (uppercut/hook)
  if (distance <= 1.04) {
    const pick = ((Math.round(time * 10) % 3) === 0) ? 'jab' : 'uppercut';
    memory.lastAttackTime = time;
    return { move: pick, fwd: false, back: false, block: false };
  }
  if (distance <= 1.14) {
    const pick = ((Math.round(time * 10) % 2) === 0) ? 'hook' : 'jab';
    memory.lastAttackTime = time;
    return { move: pick, fwd: false, back: false, block: false };
  }

  memory.lastAttackTime = time;
  return { move: 'cross', fwd: false, back: false, block: false };
}
