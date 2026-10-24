// A fighter in one arena: model, animation, moves, hit handling and per-match stats.
import * as THREE from 'three';
import { clipRate, crossFadeFor, getUpRate, hasClipRate, knockdownBelow, knockdownLie } from './realism.js';
import * as SkeletonUtils from 'three/addons/utils/SkeletonUtils.js';
import { JAM, KICKS, KNOCKDOWN, MOVES } from './config.js';
import { Inertializer, LookAt } from './motion.js';
import { Ragdoll } from './physics.js';

// Clips that travel along the floor: switching into or out of them keeps the body where it lies.
const GROUND = new Set(['knocked_out', 'knockdown_front', 'thrown', 'getting_up', 'getup_back', 'getup_front', 'sweep_fall', 'takedown_victim']);
// The clips prepared or lent at load time (lent.js).
const PREPARED = ['throw', 'thrown', 'knockdown_front', 'getup_back', 'getup_front', 'sweep', 'sweep_fall', 'takedown', 'takedown_victim'];

export function newTally() {
  return { thrown: 0, hits: 0, damage: 0, blocks: 0, bestCombo: 0, kos: 0, moves: {} };
}

export class Fighter {
  constructor(arena, def, gltf, side) {
    this.arena = arena;
    this.def = def;
    this.side = side; // -1 = left, +1 = right
    this.root = new THREE.Group();
    this.model = SkeletonUtils.clone(gltf.scene);
    this.root.add(this.model);
    arena.scene.add(this.root);

    const theme = new THREE.Color(def.color);
    this.model.traverse((o) => {
      if (!o.isMesh) return;
      o.castShadow = true;
      o.frustumCulled = false;
      const mats = Array.isArray(o.material) ? o.material : [o.material];
      const tinted = mats.map((m) => {
        const c = m.clone();
        if (def.tint > 0) {
          if (def.dark) c.color.multiplyScalar(0.35);
          c.color.lerp(theme, def.tint);
        }
        return c;
      });
      o.material = Array.isArray(o.material) ? tinted : tinted[0];
    });

    const ring = new THREE.Mesh(new THREE.RingGeometry(0.42, 0.52, 48),
      new THREE.MeshBasicMaterial({ color: theme, transparent: true, opacity: 0.85 }));
    ring.rotation.x = -Math.PI / 2;
    ring.position.y = 0.004;
    this.root.add(ring);

    this.mixer = new THREE.AnimationMixer(this.model);
    this.actions = {};
    for (const clip of gltf.animations) {
      if (!PREPARED.includes(clip.name)) this.actions[clip.name] = this.mixer.clipAction(clip);
    }
    // The throw, falls and get-ups: the fighter's own clips, or Mixamo's lent to it (lent.js, prepared on load).
    const prepared = gltf.userData.fightClips ?? { clips: {}, lent: [] };
    for (const [name, clip] of Object.entries(prepared.clips)) this.actions[name] = this.mixer.clipAction(clip);
    this.lent = prepared.lent;
    this.mixer.addEventListener('finished', () => this.onClipFinished());

    this.stats = def.stats;
    this.maxHp = def.stats.hp;
    this.tally = newTally();
    this.bones = {};
    this.model.traverse((o) => {
      if (!o.isBone) return;
      if (/Head$/.test(o.name)) this.bones.head = o;
      if (/Spine2$/.test(o.name)) this.bones.chest = o;
      if (/Hips$/.test(o.name)) this.bones.hips = o;
    });
    // Measured in the rest pose (model space, facing +Z): which way the hips bone's front points, to tell face up
    // from face down after a fall.
    this.model.updateMatrixWorld(true);
    // Standing hips height, to tell when a falling fighter has reached the mat.
    this.standHips = this.bones.hips ? this.bones.hips.getWorldPosition(new THREE.Vector3()).y : 1;
    if (this.bones.hips) {
      this.hipsFront = new THREE.Vector3(0, 0, 1).applyQuaternion(this.bones.hips.getWorldQuaternion(new THREE.Quaternion()).invert());
    }
    this.inertia = new Inertializer(this.model);
    this.lookAt = new LookAt(this.model);
    // Physics layering (PHYSICS.md): a ragdoll when the arena has a physics world. Visual only.
    this.ragdoll = arena.physics && side !== undefined ? new Ragdoll(arena.physics, this) : null;
    this.reset();
  }

  /** World position of the head or chest, used to place hit sparks. */
  hitPoint(high) {
    const bone = (high ? this.bones.head : this.bones.chest) ?? this.bones.head;
    const p = new THREE.Vector3();
    if (bone) bone.getWorldPosition(p);
    else p.set(this.root.position.x, high ? 1.6 : 1.2, 0);
    return p;
  }

  reset() {
    this.hp = this.maxHp;
    this.state = 'idle';
    this.move = null;
    this.hitLanded = false;
    this.whiffAt = null;
    this.clinch = false;
    this.downed = false;
    this.landedAt = null;
    this.downSince = null;
    this.knockedDown = false; // once per round
    this.cooldown = 0;
    this.combo = 0;
    this.root.position.set(this.side * 1.4, 0, 0);
    this.root.rotation.y = this.side < 0 ? Math.PI / 2 : -Math.PI / 2;
    this.mixer.stopAllAction();
    this.inertia?.forget();
    this.ragdoll?.reset();
    this.current = null;
    this.playLoop('fighting_idle');
  }

  dispose() {
    if (this.ragdoll) this.arena.physics?.remove(this.ragdoll);
    this.arena.scene.remove(this.root);
  }

  fade(name, once) {
    const next = this.actions[name];
    if (!next) return null;
    // Inertial blending (motion.js) instead of a crossfade: cut straight to the new clip, and let the difference fade.
    const was = this.current?.getClip().name;
    if (this.current && this.current !== next) this.current.stop();
    next.reset();
    next.setLoop(once ? THREE.LoopOnce : THREE.LoopRepeat, Infinity);
    next.clampWhenFinished = !!once;
    if (hasClipRate(name)) next.timeScale = clipRate(name);
    next.play();
    this.current = next;
    // The champion's crossfade tuning (realism.js) sets how long the leftover takes to fade.
    this.inertia?.switched(GROUND.has(was) || GROUND.has(name), crossFadeFor(name));
    return next;
  }

  playLoop(name) {
    if (this.current === this.actions[name] && this.current.isRunning()) return;
    this.fade(name, false);
  }

  get busy() {
    return ['attack', 'hit', 'ko', 'victory', 'taunt'].includes(this.state);
  }

  attack(moveName) {
    if (this.busy || this.cooldown > 0) return;
    this.state = 'attack';
    this.moveName = moveName;
    this.tally.thrown++;
    this.tally.moves[moveName] = (this.tally.moves[moveName] ?? 0) + 1;
    // A move whose clip nobody has yet (the sweep and takedown before the library has them) becomes its fallback.
    let def = MOVES[moveName];
    // (The fallback keeps the requested move's reach, so a takedown shot from 1.1 m still connects as a throw.)
    if (def.needs && !this.actions[def.needs]) { const reach = def.reach; moveName = def.fallback; def = { ...MOVES[moveName], reach }; }
    // A move with a paired animation uses it when this fighter has the clip (the throw).
    const base = def.paired && this.actions[def.paired.clip] ? { ...def, ...def.paired } : def;
    const power = this.stats.power;
    const hits = (base.hits ?? (base.footwork ? [] : [{ from: base.from, to: base.to, dmg: base.dmg }]))
      .map((h) => ({ ...h, dmg: Math.round(h.dmg * power) }));
    const top = Math.max(0, ...hits.map((h) => h.dmg));
    this.move = { ...base, name: moveName, hits, dmg: top, reach: (base.reach ?? 0) * this.stats.reach,
                  heavy: top >= Math.round(12 * power), high: base.react !== 'hit_reaction' && !base.knockdown,
                  grab: !!base.grab, paired: ['thrown', 'takedown_victim'].includes(base.react) };
    this.hitsDone = 0;
    this.hitLanded = false;
    this.grabbed = null;
    this.groundDone = 0;
    this.whiffAt = null;
    const action = this.fade(this.move.clip, true);
    if (action) action.timeScale = (0.85 + 0.25 * this.stats.speed) * (base.timeScale ?? 1) * clipRate(this.move.clip);
    this.arena.sound('swing', 0.35);
  }

  taunt() {
    if (this.busy) return;
    this.state = 'taunt';
    this.fade('taunt', true);
  }

  /** In the striking part of an attack: from the first blow's window to the last one's. Grabs miss you here. */
  striking() {
    if (this.state !== 'attack' || !this.move?.hits?.length || !this.current) return false;
    const t = this.current.time / this.current.getClip().duration;
    return t >= this.move.hits[0].from - 0.05 && t <= this.move.hits.at(-1).to;
  }

  /** In the part of a dodge or slip where strikes (and grabs) miss. */
  evading() {
    if (this.state !== 'attack' || !this.move?.evade || !this.current) return false;
    const t = this.current.time / this.current.getClip().duration;
    return t >= this.move.evade[0] && t <= this.move.evade[1];
  }

  /** Ground-and-pound: a blow to a fighter you've taken down. Bypasses the rule that you can't hit a downed fighter. */
  groundHit(dmg, from) {
    if (this.state === 'ko') return 0;
    const before = this.hp;
    this.hp = Math.max(0, this.hp - dmg);
    const fx = this.arena.effects;
    fx.sparks(this.hitPoint(true), 0xffe9a8, 18, 1.6);
    fx.shake(0.04);
    this.arena.sound('hit', 0.8);
    if (this.hp === 0) { this.state = 'ko'; this.lastHitBy = from; }
    return before - this.hp;
  }

  /** Lying face up (belly to the sky) rather than face down. */
  faceUp() {
    if (!this.hipsFront) return true;
    this.root.updateMatrixWorld(true);
    // The clip's hips orientation (physics is visual only and must not change which get-up plays).
    const hips = this.ragdoll?.animHips()?.rot ?? this.bones.hips.getWorldQuaternion(new THREE.Quaternion());
    return this.hipsFront.clone().applyQuaternion(hips).y > 0;
  }

  /** Fall onto your front or your back, depending on what hit you. Returns the clip playing. */
  fall(move) {
    const front = KNOCKDOWN.front.includes(this.lastHitBy ?? move?.name) && this.actions.knockdown_front;
    return this.fade(front ? 'knockdown_front' : 'knocked_out', true);
  }

  takeHit(move, blocked) {
    if (this.state === 'ko' || this.downed) return; // no hitting a fighter who is down
    const fx = this.arena.effects;
    const dmg = blocked ? Math.ceil(move.dmg * 0.15) : move.dmg;
    this.hp = Math.max(0, this.hp - dmg);
    const where = this.hitPoint(move.high);
    if (this.hp === 0) {
      this.state = 'ko';
      // A throw that knocks you out ends the way the throw does: flat on the mat.
      this.lastHitBy = move.name;
      const fall = move.sync && this.actions.thrown ? this.fade('thrown', true) : this.fall(move);
      if (fall && move.sync && this.actions.thrown) { fall.time = move.sync.time; fall.timeScale = move.sync.timeScale; }
      this.arena.sound('heavy', 0.9);
      fx.sparks(where, 0xfff2b0, 60, 3.2);
      fx.shake(0.16);
      fx.slowMo(1.1);
      return;
    }
    if (blocked) {
      this.arena.sound('block', 0.6);
      fx.sparks(where, 0x9fd8ff, 14, 1.4);
      this.root.position.x += this.side * 0.08;
      return;
    }
    this.combo = 0;
    this.state = 'hit';
    // The paired fall plays in step with the thrower's clip; fighters without the clip fall back to the knock-down.
    const react = this.actions[move.react] ? move.react : (move.grab || move.knockdown ? 'knocked_out' : 'hit_reaction');
    const reaction = this.fade(react, true);
    if (reaction && move.sync) { reaction.time = move.sync.time; reaction.timeScale = move.sync.timeScale; }
    if (move.grab || move.knockdown) {
      // Thrown, taken down or swept: on the mat, then get up (see animate). Pushed further than a strike.
      this.downed = true;
      this.lastHitBy = move.name;
      this.root.position.x += this.side * (move.sync ? 0.2 : 0.45);
      this.arena.sound('heavy', 0.9);
      fx.sparks(where, 0xffb347, 30, 2.2);
      fx.shake(0.12);
      return;
    }
    if (KNOCKDOWN.moves.includes(move.name) && !this.knockedDown && this.hp / this.maxHp <= knockdownBelow()) {
      // Knockdown: down on the mat, then up again the way you landed (onClipFinished).
      this.knockedDown = true;
      this.downed = true;
      this.lastHitBy = move.name;
      this.fall(move);
      this.arena.showBanner('KNOCKDOWN!', 1.2);
      this.arena.sound('heavy', 0.9);
      fx.sparks(where, 0xffb347, 40, 2.6);
      fx.shake(0.12);
      fx.hitStop(0.09);
      return;
    }
    this.root.position.x += this.side * (move.heavy ? 0.26 : 0.16);
    this.arena.sound(move.heavy ? 'heavy' : 'hit', 0.8);
    fx.sparks(where, move.heavy ? 0xffb347 : 0xffe9a8, move.heavy ? 36 : 20, move.heavy ? 2.6 : 1.8);
    fx.shake(move.heavy ? 0.09 : 0.035);
    fx.hitStop(move.heavy ? 0.09 : 0.045);
  }

  win() {
    this.state = 'victory';
    this.fade('victory', true);
  }

  onClipFinished() {
    // A fall that ends stays on its last frame: the get-up starts once the fighter has lain long enough (animate).
    if (this.state === 'hit' && this.downed && !this.gettingUp) return;
    if (this.gettingUp) { this.gettingUp = false; this.downed = false; this.landedAt = null; this.downSince = null; }
    if (['attack', 'hit', 'taunt'].includes(this.state)) {
      this.state = 'idle';
      this.cooldown = 0.12;
      this.playLoop('fighting_idle');
    }
  }

  /** Start getting up: the way you're lying; fighters without the get-up clips use their own getting_up. */
  getUp() {
    this.gettingUp = true;
    const clip = this.fade(this.faceUp() ? 'getup_back' : 'getup_front', true) ?? this.fade('getting_up', true);
    if (clip) clip.timeScale = getUpRate();
  }

  /** input: {fwd, back, block} booleans. */
  update(dt, input, opponent) {
    this.cooldown = Math.max(0, this.cooldown - dt);
    if (!this.busy) {
      const facing = -this.side; // +1 when facing +x
      if (input.block) {
        // Guard up for punches and kicks to the head, mid guard for body shots and before anything is thrown.
        this.state = 'block';
        const high = opponent?.state === 'attack' && opponent.move?.high;
        this.playLoop(high && this.actions.block_high ? 'block_high' : 'block');
      } else if (input.fwd || input.back) {
        const dir = input.fwd ? facing : -facing;
        this.root.position.x += dir * (input.fwd ? 1.7 : 1.3) * this.stats.speed * dt;
        this.state = input.fwd ? 'walk_f' : 'walk_b';
        this.playLoop(input.fwd ? 'walk_forward' : 'walk_backward');
      } else {
        this.state = 'idle';
        this.playLoop('fighting_idle');
      }
    }

    // Footwork: move along the way you face during the move's window (the clip plays in place).
    if (this.state === 'attack' && this.move.footwork && this.current) {
      const t = this.current.time / this.current.getClip().duration;
      const [a, b] = this.move.move;
      if (t >= a && t <= b) {
        const rate = this.current.timeScale / (this.current.getClip().duration * (b - a));
        this.root.position.x += -this.side * this.move.shift * rate * dt;
      }
    }

    // Hit check: each blow of the move during its own window.
    if (this.state === 'attack' && this.current && this.hitsDone < this.move.hits.length) {
      const t = this.current.time / this.current.getClip().duration;
      const blow = this.move.hits[this.hitsDone];
      const gap = Math.abs(this.root.position.x - opponent.root.position.x);
      if (t > blow.to) this.hitsDone++; // this blow missed its window
      else if (t >= blow.from && gap <= this.move.reach && opponent.state !== 'ko' && !(opponent.downed && !this.move.grab)) {
        this.hitsDone++;
        this.hitLanded = true;
        // Throws and takedowns can't be blocked, but a foe in the middle of a blow, dodging or already down slips
        // them. A foe winding up or recovering from a strike can be grabbed: that's how a caught kick gets thrown.
        if (this.move.grab && (opponent.striking() || opponent.evading() || opponent.downed)) {
          this.arena.sound('swing', 0.2);
          // A paired grab that catches nothing shouldn't play the whole move on thin air.
          if (this.move.paired) this.whiffAt = this.arena.clock + 0.25;
          this.animate(dt, opponent);
          return;
        }
        if (!this.move.grab && opponent.evading()) {
          this.arena.sound('swing', 0.3); // slipped
        } else {
          const blocked = !this.move.grab && opponent.state === 'block';
          const hpBefore = opponent.hp;
          const sync = this.move.paired ? { time: this.current.time, timeScale: this.current.timeScale } : null;
          // A kick from too close is smothered: half damage, and no knockdown.
          const jammed = KICKS.includes(this.move.name) && gap < JAM;
          const hit = { ...this.move, dmg: jammed ? Math.ceil(blow.dmg / 2) : blow.dmg, ...(jammed ? { name: 'jammed' } : {}) };
          opponent.takeHit({ ...hit, ...(sync ? { sync } : {}) }, blocked);
          if (!blocked && !this.move.grab) opponent.ragdoll?.hit(this, hit, this.move.high);
          this.tally.damage += hpBefore - opponent.hp;
          if (this.move.grab && opponent.downed) {
            this.grabbed = opponent;
            // A takedown ends on top of the opponent: the two may tangle closer than the usual minimum gap.
            if (this.move.ground) this.clinch = true;
          }
          if (blocked) {
            opponent.tally.blocks++;
          } else {
            this.tally.hits++;
            // A combo is a run of clean hits, each within 1.5 s of the last, without getting hit back.
            if (this.arena.clock - (this.lastHitAt ?? -10) > 1.5) this.combo = 0;
            this.lastHitAt = this.arena.clock;
            this.combo++;
            this.tally.bestCombo = Math.max(this.tally.bestCombo, this.combo);
          }
          if (opponent.hp === 0) this.tally.kos++;
        }
      }
    }
    // On top after a takedown: close in to the opponent on the mat.
    if (this.clinch) {
      if (this.state !== 'attack') this.clinch = false;
      else {
        const gap = opponent.root.position.x - this.root.position.x;
        const want = Math.sign(gap) * (Math.abs(gap) - 0.45);
        this.root.position.x += Math.sign(want) * Math.min(Math.abs(want), 1.8 * dt);
      }
    }
    // Ground-and-pound after a takedown: the blows in the clip land on the fighter underneath.
    if (this.state === 'attack' && this.grabbed && this.move.ground && this.current) {
      const t = this.current.time / this.current.getClip().duration;
      const g = this.move.ground[this.groundDone];
      if (g && t >= g.at) {
        this.groundDone++;
        const dealt = this.grabbed.groundHit(Math.round(g.dmg * this.stats.power), this.move.name);
        this.tally.damage += dealt;
        this.tally.hits++;
        if (this.grabbed.hp === 0) this.tally.kos++;
      }
    }
    if (this.state === 'attack' && this.move?.paired && !this.hitLanded && this.whiffAt === null && this.current
      && this.current.time / this.current.getClip().duration > this.move.hits[0].to) this.whiffAt = this.arena.clock;
    if (this.whiffAt !== null && this.arena.clock >= this.whiffAt && this.state === 'attack') {
      this.whiffAt = null;
      this.state = 'idle';
      this.cooldown = 0.3;
      this.playLoop('fighting_idle');
    }
    this.animate(dt, opponent);
  }

  /** Clips, then inertial blending, then the head turning to the opponent. */
  animate(dt, opponent) {
    // Down: get up once the hips have been on the mat for the tuned time (realism.js knockdown.lie).
    if (this.downed && !this.gettingUp && this.state === 'hit' && this.bones.hips) {
      this.downSince ??= this.arena.clock;
      // (The clip's hips, not the physics layer's: physics is visual only.)
      const hipsY = this.ragdoll?.animHips()?.pos.y ?? this.bones.hips.getWorldPosition(new THREE.Vector3()).y;
      const low = hipsY < this.standHips * 0.4;
      // (A fall that never reaches the mat, say a badly lent clip, still ends after 4 s.)
      if (this.landedAt === null && (low || this.arena.clock - this.downSince > 4)) this.landedAt = this.arena.clock;
      if (this.landedAt !== null && this.arena.clock - this.landedAt > knockdownLie()) this.getUp();
    }
    this.mixer.update(dt);
    this.inertia.apply(dt, this.root);
    this.inertia.record(this.root);
    const looking = ['idle', 'walk_f', 'walk_b', 'block', 'attack'].includes(this.state) && !this.downed;
    this.lookAt.apply(dt, looking, opponent?.bones.head?.getWorldPosition(new THREE.Vector3()), this.root);
  }
}
