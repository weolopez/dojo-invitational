// Per-arena hit effects: sparks, camera shake, hit-stop and KO slow motion.
import * as THREE from 'three';

export class Effects {
  constructor(scene) {
    this.scene = scene;
    this.bursts = [];
    this.shakeAmount = 0;
    this.stopTime = 0;
    this.slowTime = 0;
  }

  reset() {
    this.stopTime = this.slowTime = this.shakeAmount = 0;
  }

  sparks(pos, color, count, speed) {
    const positions = new Float32Array(count * 3);
    const velocities = [];
    for (let i = 0; i < count; i++) {
      positions.set([pos.x, pos.y, pos.z], i * 3);
      const dir = new THREE.Vector3(Math.random() - 0.5, Math.random() - 0.3, Math.random() - 0.5).normalize();
      velocities.push(dir.multiplyScalar(speed * (0.4 + Math.random() * 0.8)));
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    const mat = new THREE.PointsMaterial({ color, size: 0.07, transparent: true, opacity: 1,
      blending: THREE.AdditiveBlending, depthWrite: false });
    const points = new THREE.Points(geo, mat);
    this.scene.add(points);
    const flash = new THREE.PointLight(color, 6, 2.5);
    flash.position.copy(pos);
    this.scene.add(flash);
    this.bursts.push({ points, flash, velocities, age: 0, life: 0.4 });
  }

  shake(amount) { this.shakeAmount = Math.max(this.shakeAmount, amount); }
  hitStop(seconds) { this.stopTime = Math.max(this.stopTime, seconds); }
  slowMo(seconds) { this.slowTime = Math.max(this.slowTime, seconds); }

  /** Advances the effects and returns the time scale the fighters should run at this frame. */
  update(dt) {
    for (const b of this.bursts) {
      b.age += dt;
      const pos = b.points.geometry.attributes.position;
      b.velocities.forEach((v, i) => {
        v.y -= 7 * dt;
        pos.setXYZ(i, pos.getX(i) + v.x * dt, pos.getY(i) + v.y * dt, pos.getZ(i) + v.z * dt);
      });
      pos.needsUpdate = true;
      const k = 1 - b.age / b.life;
      b.points.material.opacity = Math.max(0, k);
      b.flash.intensity = Math.max(0, 6 * k * k);
    }
    for (const b of this.bursts.filter((x) => x.age >= x.life)) {
      this.scene.remove(b.points, b.flash);
      b.points.geometry.dispose();
      b.points.material.dispose();
    }
    this.bursts = this.bursts.filter((x) => x.age < x.life);
    this.shakeAmount = Math.max(0, this.shakeAmount - dt * 0.6);

    if (this.stopTime > 0) {
      this.stopTime -= dt;
      return 0.04;
    }
    if (this.slowTime > 0) {
      this.slowTime -= dt;
      return 0.35;
    }
    return 1;
  }

  applyShake(cam) {
    if (this.shakeAmount <= 0) return;
    cam.position.x += (Math.random() - 0.5) * this.shakeAmount;
    cam.position.y += (Math.random() - 0.5) * this.shakeAmount;
  }
}
