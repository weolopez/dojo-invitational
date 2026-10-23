// One arena: its own scene, camera, dojo, two fighters and the match rules (rounds, timer, KO).
// Several arenas can run at once; the page renders each into its own viewport.
import * as THREE from 'three';
import { ARENA_HALF, MIN_GAP, ROUNDS_TO_WIN } from './config.js';
import { Effects } from './effects.js';
import { Fighter } from './fighter.js';
import { loadFighterAsset, playSound } from './assets.js';
import { applyPreset } from './dojos.js';

const IDLE_INPUT = { fwd: false, back: false, block: false };

export class Arena {
  constructor({ timing, shadowSize = 2048, sound = false, humanInput = null }) {
    this.timing = timing;
    this.soundOn = sound;
    this.humanInput = humanInput; // (playerIndex) => {fwd, back, block}
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(38, 16 / 9, 0.1, 60);
    this.camera.position.set(0, 1.6, 6.2);
    this.sun = new THREE.DirectionalLight(0xfff1dd, 2.2);
    this.sun.castShadow = true;
    this.sun.shadow.mapSize.set(shadowSize, shadowSize);
    Object.assign(this.sun.shadow.camera, { left: -6, right: 6, top: 6, bottom: -2, near: 1, far: 20 });
    this.scene.add(this.sun);
    this.fill = new THREE.HemisphereLight(0xffe8cc, 0x3a2a1c, 0.6);
    this.scene.add(this.fill);
    this.effects = new Effects(this.scene);

    this.fighters = [];
    this.brains = [null, null];
    this.clock = 0;
    this.timers = [];
    this.token = 0;
    this.wins = [0, 0];
    this.round = 1;
    this.timeLeft = timing.roundTime;
    this.over = false;
    this.matchOver = false;
    this.active = false; // a match is loaded
    this.banner = { text: '', until: 0 };
    this.roundLabel = '';
    this.idleAngle = Math.random() * Math.PI * 2;
    this.onRoundEnd = null; // (arena, winner, timeUp)
    this.onMatchEnd = null; // (arena, winner)
  }

  setDojo(preset) {
    return applyPreset(this, preset);
  }

  sound(kind, volume) {
    if (this.soundOn) playSound(kind, volume);
  }

  showBanner(text, seconds) {
    this.banner = { text, until: performance.now() + seconds * 1000 };
  }

  /** Run fn after `seconds` of this arena's game time, unless the round changes first. */
  schedule(seconds, fn) {
    this.timers.push({ at: this.clock + seconds, fn, token: this.token });
  }

  clear() {
    this.fighters.forEach((f) => f.dispose());
    this.fighters = [];
    this.active = false;
    this.token++;
    this.timers = [];
    this.banner = { text: '', until: 0 };
  }

  async startMatch(def1, def2, brains = [null, null]) {
    const [g1, g2] = await Promise.all([loadFighterAsset(def1.id, def1.url), loadFighterAsset(def2.id, def2.url)]);
    this.clear();
    this.fighters = [new Fighter(this, def1, g1, -1), new Fighter(this, def2, g2, 1)];
    this.brains = brains;
    this.active = true;
    this.newMatch();
  }

  newMatch() {
    this.wins = [0, 0];
    this.round = 1;
    this.matchOver = false;
    this.fighters.forEach((f) => { f.tally = { ...f.tally, thrown: 0, hits: 0, damage: 0, blocks: 0, bestCombo: 0, kos: 0, moves: {} }; });
    this.newRound();
  }

  newRound() {
    this.token++;
    this.fighters.forEach((f) => f.reset());
    this.timeLeft = this.timing.roundTime;
    this.over = false;
    this.effects.reset();
    const final = this.wins[0] === ROUNDS_TO_WIN - 1 && this.wins[1] === ROUNDS_TO_WIN - 1;
    this.roundLabel = final ? 'FINAL ROUND' : `ROUND ${this.round}`;
    this.showBanner(this.roundLabel, this.timing.roundIntro);
    this.schedule(this.timing.roundIntro, () => this.showBanner('FIGHT!', 0.7));
  }

  endRound(winner, timeUp) {
    if (this.over) return;
    this.over = true;
    if (winner) {
      this.wins[this.fighters.indexOf(winner)]++;
      this.schedule(timeUp ? 0 : this.timing.victoryDelay, () => winner.win());
    }
    this.onRoundEnd?.(this, winner, timeUp);
    // A match that keeps drawing is decided on total damage after five rounds.
    if (!winner && this.round >= 5) {
      const [a, b] = this.fighters;
      winner = a.tally.damage >= b.tally.damage ? a : b;
      this.wins[this.fighters.indexOf(winner)] = ROUNDS_TO_WIN;
    }
    if (winner && this.wins[this.fighters.indexOf(winner)] >= ROUNDS_TO_WIN) {
      this.matchOver = true;
      this.winner = winner;
      this.decidedByTime = !!timeUp;
      this.showBanner(winner.def.id === 'me' ? 'YOU WIN!' : `${winner.def.name.toUpperCase()} WINS!`, 999);
      this.roundLabel = 'MATCH OVER';
      this.onMatchEnd?.(this, winner);
      return;
    }
    this.showBanner(winner ? (timeUp ? 'TIME!' : 'K.O.!') : 'DRAW', this.timing.roundBreak * 0.6);
    this.schedule(this.timing.roundBreak, () => {
      this.round++;
      this.newRound();
    });
  }

  update(realDt) {
    this.clock += realDt;
    const due = this.timers.filter((t) => t.at <= this.clock);
    this.timers = this.timers.filter((t) => t.at > this.clock);
    for (const t of due) if (t.token === this.token) t.fn();

    if (!this.active) {
      this.effects.update(realDt);
      this.idleAngle += realDt * 0.12;
      this.camera.position.set(Math.sin(this.idleAngle) * 5, 2.2, Math.cos(this.idleAngle) * 5);
      this.camera.lookAt(0, 1.2, 0);
      return;
    }

    const [p1, p2] = this.fighters;
    const dt = realDt * this.effects.update(realDt);
    const input = (i, me, foe) => {
      if (this.over) return IDLE_INPUT;
      if (this.brains[i]) return this.brains[i].input(dt, me, foe);
      return this.humanInput ? this.humanInput(i) : IDLE_INPUT;
    };
    const in1 = input(0, p1, p2);
    const in2 = input(1, p2, p1);
    p1.update(dt, in1, p2);
    p2.update(dt, in2, p1);

    // Keep fighters apart and inside the mat.
    for (const f of this.fighters) f.root.position.x = THREE.MathUtils.clamp(f.root.position.x, -ARENA_HALF, ARENA_HALF);
    const gap = p2.root.position.x - p1.root.position.x;
    if (gap < MIN_GAP) {
      const push = (MIN_GAP - gap) / 2;
      p1.root.position.x -= push;
      p2.root.position.x += push;
    }

    if (!this.over) {
      this.timeLeft = Math.max(0, this.timeLeft - dt);
      if (p1.hp === 0) this.endRound(p2);
      else if (p2.hp === 0) this.endRound(p1);
      else if (this.timeLeft === 0) {
        const r1 = p1.hp / p1.maxHp;
        const r2 = p2.hp / p2.maxHp;
        this.endRound(r1 === r2 ? null : (r1 > r2 ? p1 : p2), true);
      }
    }

    // Side-on camera that tracks the midpoint and pulls back as fighters separate.
    const mid = (p1.root.position.x + p2.root.position.x) / 2;
    const target = new THREE.Vector3(mid, 1.6, 4.2 + Math.abs(gap) * 0.75);
    this.camera.position.lerp(target, 1 - Math.exp(-realDt * 4));
    this.camera.lookAt(mid, 1.05, 0);
    this.effects.applyShake(this.camera);
  }

  /** Render into a rectangle of the canvas, in CSS pixels from the top-left. */
  render(renderer, rect) {
    const h = renderer.domElement.clientHeight;
    this.camera.aspect = rect.w / rect.h;
    this.camera.updateProjectionMatrix();
    renderer.setViewport(rect.x, h - rect.y - rect.h, rect.w, rect.h);
    renderer.setScissor(rect.x, h - rect.y - rect.h, rect.w, rect.h);
    renderer.render(this.scene, this.camera);
  }
}
