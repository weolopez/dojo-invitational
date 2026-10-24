// Standardised judging renders (competition/RULES.md §7): every fighter.glb under the same Three.js scene,
// camera positions, lighting (judge HDRI + one key light), ACES tone mapping and 1920×1080 resolution.
// Open /judge.html?id=<entry-id>. Each view is saved to competition/judging/<id>/<view>.png by the dev server.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RGBELoader } from 'three/addons/loaders/RGBELoader.js';

const params = new URLSearchParams(location.search);
const id = params.get('id');
const status = document.getElementById('status');
const W = 1920;
const H = 1080;

const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1);
renderer.setSize(W, H, false);
renderer.domElement.style.width = '100%';
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.shadowMap.enabled = true;
document.body.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(30, W / H, 0.05, 50);
const key = new THREE.DirectionalLight(0xfff1e0, 2.0);
key.position.set(-2.2, 3.2, 3.0);
key.castShadow = true;
scene.add(key);

// Views: azimuth (degrees, 0 = fighter's front), distance (m), camera height and look-at height as fractions
// of the fighter's height (or absolute offsets from the head for the close-up), and the animation frame.
const VIEWS = [
  { name: 'front', az: 0, dist: 5.2, camY: 0.55, lookY: 0.52 },
  { name: 'three_quarter', az: 35, dist: 5.2, camY: 0.58, lookY: 0.52 },
  { name: 'profile', az: 90, dist: 5.2, camY: 0.55, lookY: 0.52 },
  { name: 'closeup', az: 20, dist: 1.0, head: true },
  { name: 'idle_full', az: 25, dist: 5.6, camY: 0.5, lookY: 0.5, clip: 'fighting_idle', at: 0.3 },
  { name: 'action_roundhouse', az: 70, dist: 6.0, camY: 0.5, lookY: 0.5, clip: 'roundhouse_kick', at: 0.45 },
];

async function save(view) {
  const blob = await new Promise((r) => renderer.domElement.toBlob(r, 'image/png'));
  const res = await fetch(`/api/judge-render?id=${encodeURIComponent(id)}&view=${view}`, { method: 'POST', body: blob });
  if (!res.ok) throw new Error(`save failed: ${res.status}`);
}

async function main() {
  if (!/^[a-z0-9_-]+$/.test(id ?? '')) { status.textContent = 'Add ?id=<entry-id>'; return; }
  const hdr = await new RGBELoader().loadAsync('/hdri/basement_boxing_ring_2k.hdr');
  hdr.mapping = THREE.EquirectangularReflectionMapping;
  scene.environment = hdr;
  scene.background = hdr;
  scene.backgroundBlurriness = 0.35;
  const gltf = await new GLTFLoader().loadAsync(`/judge-file/${id}/fighter.glb`);
  const model = gltf.scene;
  model.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.frustumCulled = false; } });
  scene.add(model);
  const mixer = new THREE.AnimationMixer(model);
  // Frame from the skeleton: skinned-mesh bounding boxes are unreliable in Three.js.
  let headBone = null;
  let hipsBone = null;
  model.traverse((o) => {
    if (o.isBone && /Head$/.test(o.name)) headBone = o;
    if (o.isBone && /Hips$/.test(o.name)) hipsBone = o;
  });
  // The rest pose as loaded. (skeleton.pose() ignores a scaled armature above the bones, which Mixamo and Blender
  // exports usually have, and blows such fighters up 100 times with the camera inside them.)
  const rest = [];
  model.traverse((o) => { if (o.isBone) rest.push([o, o.position.clone(), o.quaternion.clone(), o.scale.clone()]); });
  model.updateMatrixWorld(true);
  const headY = headBone ? headBone.getWorldPosition(new THREE.Vector3()).y : 1.6;
  const box = { min: { y: 0 } };
  const height = headY + 0.14;

  for (const v of VIEWS) {
    mixer.stopAllAction();
    if (v.clip) {
      const clip = gltf.animations.find((c) => c.name === v.clip);
      if (clip) {
        const action = mixer.clipAction(clip);
        action.play();
        mixer.setTime(clip.duration * v.at);
      }
    } else {
      // Bind pose for the beauty views, so every fighter is compared in the same neutral stance.
      for (const [bone, p, q, sc] of rest) { bone.position.copy(p); bone.quaternion.copy(q); bone.scale.copy(sc); }
    }
    model.updateMatrixWorld(true);
    const a = THREE.MathUtils.degToRad(v.az);
    let target;
    let camPos;
    if (v.head && headBone) {
      const head = new THREE.Vector3();
      headBone.getWorldPosition(head);
      target = head.clone().add(new THREE.Vector3(0, 0.08, 0));
      camPos = target.clone().add(new THREE.Vector3(Math.sin(a) * v.dist, 0.02, Math.cos(a) * v.dist));
    } else {
      // Frame the fighter where the pose actually puts them (attacks move the hips).
      const c = hipsBone ? hipsBone.getWorldPosition(new THREE.Vector3()) : new THREE.Vector3();
      target = new THREE.Vector3(c.x, box.min.y + height * v.lookY, c.z);
      camPos = new THREE.Vector3(c.x + Math.sin(a) * v.dist, box.min.y + height * v.camY, c.z + Math.cos(a) * v.dist);
    }
    camera.position.copy(camPos);
    camera.lookAt(target);
    renderer.render(scene, camera);
    status.textContent = `Rendering ${v.name}…`;
    await save(v.name);
  }
  status.textContent = `Done: ${VIEWS.length} views saved to competition/judging/${id}/`;
  document.title = 'Judging Harness · done';
}

main().catch((err) => { status.textContent = `Error: ${err.message}`; document.title = 'Judging Harness · error'; });
