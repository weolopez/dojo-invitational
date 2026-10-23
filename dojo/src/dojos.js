// Arena environments: four built-in dojos plus any champion-built dojo (competition/RULES.md §9).
import * as THREE from 'three';
import { gltfLoader, loadHdr, pbr } from './assets.js';
import { ARENA_HALF } from './config.js';

function room(group, { floor, walls, wainscot, beams, beamColor, lineColor }) {
  const f = new THREE.Mesh(new THREE.PlaneGeometry(14, 9), pbr(floor, 7, 4.5));
  f.rotation.x = -Math.PI / 2;
  f.receiveShadow = true;
  group.add(f);

  const wallMat = pbr(walls, 4, 2);
  const back = new THREE.Mesh(new THREE.PlaneGeometry(14, 4.5), wallMat);
  back.position.set(0, 2.25, -4.5);
  back.receiveShadow = true;
  group.add(back);
  for (const side of [-1, 1]) {
    const wall = new THREE.Mesh(new THREE.PlaneGeometry(9, 4.5), wallMat);
    wall.position.set(side * 7, 2.25, 0);
    wall.rotation.y = -side * Math.PI / 2;
    group.add(wall);
  }
  if (wainscot) {
    const w = new THREE.Mesh(new THREE.PlaneGeometry(14, 1.1), pbr(wainscot, 6, 1));
    w.position.set(0, 0.55, -4.49);
    group.add(w);
  }
  if (beams) {
    const beamMat = new THREE.MeshStandardMaterial({ color: beamColor, roughness: 0.7 });
    for (let x = -6; x <= 6; x += 3) {
      const beam = new THREE.Mesh(new THREE.BoxGeometry(0.22, 4.5, 0.22), beamMat);
      beam.position.set(x, 2.25, -4.4);
      beam.castShadow = true;
      group.add(beam);
    }
  }
  const line = new THREE.Mesh(new THREE.PlaneGeometry(ARENA_HALF * 2 + 0.6, 0.05), new THREE.MeshBasicMaterial({ color: lineColor }));
  line.rotation.x = -Math.PI / 2;
  line.position.set(0, 0.003, 0.9);
  group.add(line);
}

function lantern(group, x, y, z) {
  const glow = new THREE.Mesh(new THREE.SphereGeometry(0.16, 16, 12),
    new THREE.MeshStandardMaterial({ color: 0xffb066, emissive: 0xff8a2a, emissiveIntensity: 2.5 }));
  glow.position.set(x, y, z);
  group.add(glow);
  const light = new THREE.PointLight(0xff9a4a, 6, 7, 1.6);
  light.position.set(x, y, z + 0.2);
  group.add(light);
}

// Each preset: name, environment HDR, background, fog, sun and fill settings, and a room builder.
export const DOJO_PRESETS = [
  {
    id: 'house', name: 'The House Dojo', author: 'House',
    hdr: '/hdri/basement_boxing_ring_2k.hdr', background: 0x1a1512, fog: [0x1a1512, 9, 22],
    sun: { position: [-3, 7, 5], intensity: 2.2, color: 0xfff1dd }, fill: [0xffe8cc, 0x3a2a1c, 0.6],
    build: (g) => room(g, { floor: 'tatami_mat', walls: 'white_plaster_rough_01', wainscot: 'japanese_cedar_planks', beams: true, beamColor: 0x3b2716, lineColor: 0x9c2a1c }),
  },
  {
    id: 'bamboo', name: 'Bamboo Dawn Hall', author: 'House',
    hdr: '/hdri/gym_01_2k.hdr', background: 0x3a2a20, fog: [0x3a2a20, 10, 24],
    sun: { position: [-7, 3, 4], intensity: 2.8, color: 0xffc58a }, fill: [0xffd9b0, 0x2a1d12, 0.5],
    build: (g) => room(g, { floor: 'hinoki_planks', walls: 'bamboo_wall', beams: true, beamColor: 0x5a3b1f, lineColor: 0xffffff }),
  },
  {
    id: 'temple', name: 'Stone Lantern Temple', author: 'House',
    hdr: '/hdri/basement_boxing_ring_2k.hdr', background: 0x070a12, fog: [0x070a12, 8, 18], envIntensity: 0.35,
    sun: { position: [4, 8, 3], intensity: 0.9, color: 0x9db8ff }, fill: [0x506080, 0x120c08, 0.35],
    build: (g) => {
      room(g, { floor: 'tatami_mat', walls: 'japanese_stone_wall', beams: false, lineColor: 0xc23b22 });
      lantern(g, -4.5, 2.4, -3.9);
      lantern(g, 0, 2.8, -3.9);
      lantern(g, 4.5, 2.4, -3.9);
    },
  },
  {
    id: 'cedar', name: 'Cedar Fight Hall', author: 'House',
    hdr: '/hdri/wrestling_gym_2k.hdr', background: 0x1c1f24, fog: [0x1c1f24, 10, 24],
    sun: { position: [0, 9, 3], intensity: 2.4, color: 0xf2f6ff }, fill: [0xdfe8ff, 0x2a241c, 0.55],
    build: (g) => room(g, { floor: 'japanese_cedar_planks', walls: 'white_plaster_rough_01', wainscot: 'hinoki_planks', beams: true, beamColor: 0x2a1c10, lineColor: 0x1d4fd6 }),
  },
];

/** Champion dojos from the server, shaped like presets. */
export function championPreset(info) {
  return {
    id: `champion:${info.folder}`, name: info.name, author: info.author, champion: true,
    hdr: info.environment, hdrBackground: info.background, background: 0x111111, fog: null,
    sun: info.sun ? { position: info.sun.direction.map((v) => v * 10), intensity: info.sun.intensity ?? 2.2, color: info.sun.color ?? 0xffffff } : null,
    fill: [0xffffff, 0x222222, 0.4],
    load: async (g) => {
      const gltf = await gltfLoader.loadAsync(info.dojo);
      gltf.scene.traverse((o) => { if (o.isMesh) { o.receiveShadow = true; o.castShadow = true; } });
      g.add(gltf.scene);
    },
  };
}

/** Build a preset into an arena: room geometry, environment, background, fog and lights. */
export async function applyPreset(arena, preset) {
  const { scene } = arena;
  if (arena.dojoGroup) scene.remove(arena.dojoGroup);
  const group = new THREE.Group();
  if (preset.load) await preset.load(group);
  else preset.build(group);
  scene.add(group);
  arena.dojoGroup = group;
  arena.preset = preset;

  scene.background = new THREE.Color(preset.background);
  scene.fog = preset.fog ? new THREE.Fog(...preset.fog) : null;
  scene.environmentIntensity = preset.envIntensity ?? 1;
  if (preset.sun) {
    arena.sun.position.set(...preset.sun.position);
    arena.sun.intensity = preset.sun.intensity;
    arena.sun.color.set(preset.sun.color);
  }
  arena.fill.color.set(preset.fill[0]);
  arena.fill.groundColor.set(preset.fill[1]);
  arena.fill.intensity = preset.fill[2];
  if (preset.hdr) {
    const hdr = await loadHdr(preset.hdr);
    scene.environment = hdr;
    if (preset.hdrBackground) scene.background = hdr;
  }
}
