// A fighter in one arena: model, animation, moves, hit handling and per-match stats.
import * as THREE from 'three';
import * as SkeletonUtils from 'three/addons/utils/SkeletonUtils.js';
import { MOVES } from './config.js';

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
    for (const clip of gltf.animations) this.actions[clip.name] = this.mixer.clipAction(clip);
    this.mixer.addEventListener('finished', () => this.onClipFinished());

    this.stats = def.stats;
    this.maxHp = def.stats.hp;
    this.tally = newTally();
    this.bones = {};
    this.model.traverse((o) => {
      if (!o.isBone) return;
      if (/Head$/.test(o.name)) this.bones.head = o;
      if (/Spine2$/.test(o.name)) this.bones.chest = o;
    });
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
    this.cooldown = 0;
    this.combo = 0;
    this.root.position.set(this.side * 1.4, 0, 0);
    this.root.rotation.y = this.side < 0 ? Math.PI / 2 : -Math.PI / 2;
    this.mixer.stopAllAction();
    this.current = null;
    this.playLoop('fighting_idle');
  }

  dispose() {
    this.arena.scene.remove(this.root);
  }

  fade(name, once) {
    const next = this.actions[name];
    if (!next) return null;
    next.reset();
    next.setLoop(once ? THREE.LoopOnce : THREE.LoopRepeat, Infinity);
    next.clampWhenFinished = !!once;
    if (this.current && this.current !== next) next.crossFadeFrom(this.current, 0.12, false);
    next.play();
    this.current = next;
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
    const base = MOVES[moveName];
    this.move = { ...base, dmg: Math.round(base.dmg * this.stats.power), reach: base.reach * this.stats.reach,
                  heavy: base.dmg >= 12, high: base.react !== 'hit_reaction', grab: !!base.grab };
    this.hitLanded = false;
    const action = this.fade(this.move.clip, true);
    if (action) action.timeScale = (0.85 + 0.25 * this.stats.speed) * (base.timeScale ?? 1);
    this.arena.sound('swing', 0.35);
  }

  taunt() {
    if (this.busy) return;
    this.state = 'taunt';
    this.fade('taunt', true);
  }

  takeHit(move, blocked) {
    if (this.state === 'ko') return;
    const fx = this.arena.effects;
    const dmg = blocked ? Math.ceil(move.dmg * 0.15) : move.dmg;
    this.hp = Math.max(0, this.hp - dmg);
    const where = this.hitPoint(move.high);
    if (this.hp === 0) {
      this.state = 'ko';
      this.fade('knocked_out', true);
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
    this.fade(move.react, true);
    if (move.grab) {
      // Thrown: knockdown, then get up (chained in onClipFinished). Pushed further than a strike.
      this.downed = true;
      this.root.position.x += this.side * 0.45;
      this.arena.sound('heavy', 0.9);
      fx.sparks(where, 0xffb347, 30, 2.2);
      fx.shake(0.12);
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
    if (this.state === 'hit' && this.downed) {
      this.downed = false;
      this.fade('getting_up', true);
      return;
    }
    if (['attack', 'hit', 'taunt'].includes(this.state)) {
      this.state = 'idle';
      this.cooldown = 0.12;
      this.playLoop('fighting_idle');
    }
  }

  /** input: {fwd, back, block} booleans. */
  update(dt, input, opponent) {
    this.cooldown = Math.max(0, this.cooldown - dt);
    if (!this.busy) {
      const facing = -this.side; // +1 when facing +x
      if (input.block) {
        this.state = 'block';
        this.playLoop('block');
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

    // Hit check during the move's active window.
    if (this.state === 'attack' && !this.hitLanded && this.current) {
      const t = this.current.time / this.current.getClip().duration;
      const gap = Math.abs(this.root.position.x - opponent.root.position.x);
      if (t >= this.move.from && t <= this.move.to && gap <= this.move.reach && opponent.state !== 'ko') {
        this.hitLanded = true;
        // Throws can't be blocked, but a foe who is mid-strike (or already down) slips the grab.
        if (this.move.grab && (opponent.state === 'attack' || opponent.downed)) {
          this.arena.sound('swing', 0.2);
          this.mixer.update(dt);
          return;
        }
        const blocked = !this.move.grab && opponent.state === 'block';
        const hpBefore = opponent.hp;
        opponent.takeHit(this.move, blocked);
        this.tally.damage += hpBefore - opponent.hp;
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
    this.mixer.update(dt);
  }
}
