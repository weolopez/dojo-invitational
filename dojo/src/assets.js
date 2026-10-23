// Loaders, caches and sound effects shared by every arena.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RGBELoader } from 'three/addons/loaders/RGBELoader.js';

export const gltfLoader = new GLTFLoader();
const rgbeLoader = new RGBELoader();
const texLoader = new THREE.TextureLoader();

const gltfCache = {};
export function loadFighterAsset(id, url = `/fighters/${id}.glb`) {
  return gltfCache[url] ??= gltfLoader.loadAsync(url);
}

const hdrCache = {};
export function loadHdr(url) {
  return hdrCache[url] ??= rgbeLoader.loadAsync(url).then((hdr) => {
    hdr.mapping = THREE.EquirectangularReflectionMapping;
    return hdr;
  });
}

const materialCache = {};
/** A tiling PBR material from the textures in /tex (diff, nor_gl, rough). */
export function pbr(name, repeatX, repeatY) {
  const key = `${name}:${repeatX}:${repeatY}`;
  if (materialCache[key]) return materialCache[key];
  const load = (suffix, srgb) => {
    const t = texLoader.load(`/tex/${name}_${suffix}.jpg`);
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.repeat.set(repeatX, repeatY);
    t.anisotropy = 8;
    if (srgb) t.colorSpace = THREE.SRGBColorSpace;
    return t;
  };
  return materialCache[key] = new THREE.MeshStandardMaterial({
    map: load('diff', true), normalMap: load('nor_gl'), roughnessMap: load('rough'),
  });
}

const SFX = {
  hit: ['impactPunch_medium_000', 'impactPunch_medium_001'],
  heavy: ['impactPunch_heavy_000', 'impactPunch_heavy_001'],
  block: ['impactSoft_heavy_000'],
  swing: ['cloth1', 'cloth2', 'cloth3'],
};
const audioCache = {};
export function playSound(kind, volume = 0.7) {
  const list = SFX[kind];
  const file = list[Math.floor(Math.random() * list.length)];
  const base = audioCache[file] ??= new Audio(`/sfx/${file}.ogg`);
  const a = base.cloneNode();
  a.volume = volume;
  a.play().catch(() => {});
}
