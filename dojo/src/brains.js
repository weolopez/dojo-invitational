// Fight AIs: the house CPU (with personalities) and competition entry brains (competition/RULES.md §5).
import { MOVES, PERSONALITIES } from './config.js';

export class CpuBrain {
  constructor(personality = PERSONALITIES.default) {
    this.p = personality;
    this.think = 0;
    this.plan = { fwd: false, back: false, block: false };
  }

  input(dt, me, foe) {
    const p = this.p;
    this.think -= dt;
    const gap = Math.abs(me.root.position.x - foe.root.position.x);
    if (foe.state === 'block' && gap < 0.95 && Math.random() < 0.5) { this.plan = { fwd: false, back: false, block: false }; me.attack('throw'); return this.plan; }
    if (foe.state === 'attack' && gap < 1.7 && Math.random() < p.block) this.plan = { fwd: false, back: false, block: true };
    if (this.think > 0) return this.plan;
    this.think = p.think * (0.6 + Math.random() * 0.8);
    this.plan = { fwd: false, back: false, block: false };
    if (foe.state === 'ko' || me.state === 'ko') return this.plan;
    if (gap > 1.45) this.plan.fwd = true;
    else if (gap < 0.95 && Math.random() < 0.4) this.plan.back = true;
    else if (Math.random() < p.aggression) {
      let pick;
      if (gap > 1.3 || Math.random() < p.kicks) pick = Math.random() < 0.6 ? 'roundhouse' : 'frontkick';
      else if (Math.random() < p.power) pick = Math.random() < 0.5 ? 'hook' : 'uppercut';
      else pick = Math.random() < 0.6 ? 'jab' : 'cross';
      me.attack(pick);
    } else if (Math.random() < 0.3) this.plan.back = true;
    return this.plan;
  }
}

export class EntryBrain {
  constructor(source) {
    const body = source.replace(/export\s+default\s+function/, 'const __brain = function') + '\nreturn __brain;';
    // The validator already rejects network, DOM and global access; shadow those names as well.
    const shadowed = ['window', 'document', 'globalThis', 'self', 'fetch', 'XMLHttpRequest', 'WebSocket',
      'importScripts', 'localStorage', 'indexedDB', 'navigator', 'location', 'setTimeout', 'setInterval'];
    this.fn = new Function(...shadowed, body)();
    this.memory = {};
    this.wait = 0;
    this.plan = { fwd: false, back: false, block: false };
  }

  input(dt, me, foe) {
    this.wait -= dt;
    if (this.wait > 0) return this.plan;
    this.wait = 0.1;
    const arena = me.arena;
    const view = (f) => ({ x: f.root.position.x, hp: f.hp, maxHp: f.maxHp, state: f.state, facing: -f.side });
    const meIdx = arena.fighters.indexOf(me);
    let out;
    try {
      out = this.fn({
        time: arena.timing.roundTime - arena.timeLeft,
        me: view(me),
        foe: { ...view(foe), move: foe.state === 'attack' ? foe.moveName : null },
        distance: Math.abs(me.root.position.x - foe.root.position.x),
        round: arena.round, roundsWon: arena.wins[meIdx], foeRoundsWon: arena.wins[1 - meIdx],
        memory: this.memory,
      }) ?? {};
    } catch {
      out = {};
    }
    if (out.move === 'taunt') me.taunt();
    else if (out.move && MOVES[out.move]) me.attack(out.move);
    this.plan = { fwd: !!out.fwd, back: !!out.back, block: !!out.block };
    return this.plan;
  }
}
