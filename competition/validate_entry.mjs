#!/usr/bin/env node
// Dojo Invitational entry validator. No dependencies.
// Usage:
//   node validate_entry.mjs <entry-id>          check competition/entries/<entry-id>/
//   node validate_entry.mjs --glb <file.glb>    check just a model against the fighter.glb rules

import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const PROJECT = path.resolve(HERE, '..');
const REFERENCE_GLB = path.join(PROJECT, 'dojo', 'public', 'fighters', 'me.glb');

const CLIPS = ['block', 'block_high', 'cross', 'crouch', 'fighting_idle', 'front_kick', 'getting_up',
  'hit_by_uppercut', 'hit_head_big', 'hit_head_light', 'hit_reaction', 'hook', 'jab', 'jab_cross', 'jump',
  'knocked_out', 'punch_combo', 'roundhouse_kick', 'side_kick', 'side_step_left', 'side_step_right',
  'step_backward', 'step_forward', 'taunt', 'throw', 'thrown', 'uppercut', 'victory', 'walk_backward', 'walk_forward'];
const BONES = ['Hips', 'Spine', 'Spine1', 'Spine2', 'Neck', 'Head',
  ...['Left', 'Right'].flatMap((s) => ['Shoulder', 'Arm', 'ForeArm', 'Hand', 'UpLeg', 'Leg', 'Foot', 'ToeBase']
    .map((b) => `${s}${b}`))].map((b) => `mixamorig:${b}`);
const ALLOWED_EXT = /^(KHR_materials_[a-z_]+|KHR_texture_transform|KHR_mesh_quantization|EXT_texture_webp)$/;
const MOVES = ['jab', 'cross', 'hook', 'uppercut', 'roundhouse', 'frontkick', 'throw', 'sidekick', 'onetwo', 'combo',
  'dodge', 'slip', 'sweep', 'takedown', 'lowkick', 'knee', 'spinkick', 'taunt'];
const LIMITS = { fileMB: 80, triangles: 250_000, texturePx: 4096, textures: 40, minHeight: 1.55, maxHeight: 2.05 };

const results = [];
const pass = (msg) => results.push(['PASS', msg]);
const fail = (msg) => results.push(['FAIL', msg]);
const warn = (msg) => results.push(['WARN', msg]);

// ---------- GLB parsing ----------
function readGlb(file) {
  const buf = fs.readFileSync(file);
  if (buf.readUInt32LE(0) !== 0x46546c67) throw new Error('not a GLB file (bad magic)');
  let offset = 12;
  let json = null;
  let bin = null;
  while (offset < buf.length) {
    const len = buf.readUInt32LE(offset);
    const type = buf.readUInt32LE(offset + 4);
    const data = buf.subarray(offset + 8, offset + 8 + len);
    if (type === 0x4e4f534a) json = JSON.parse(data.toString('utf8'));
    if (type === 0x004e4942) bin = data;
    offset += 8 + len;
  }
  return { json, bin, size: buf.length };
}

function imageSize(bytes) {
  if (bytes[0] === 0x89 && bytes[1] === 0x50) return [bytes.readUInt32BE(16), bytes.readUInt32BE(20)];
  if (bytes[0] === 0xff && bytes[1] === 0xd8) {
    let i = 2;
    while (i < bytes.length) {
      if (bytes[i] !== 0xff) { i++; continue; }
      const marker = bytes[i + 1];
      const len = bytes.readUInt16BE(i + 2);
      if (marker >= 0xc0 && marker <= 0xcf && ![0xc4, 0xc8, 0xcc].includes(marker)) {
        return [bytes.readUInt16BE(i + 7), bytes.readUInt16BE(i + 5)];
      }
      i += 2 + len;
    }
  }
  if (bytes.toString('ascii', 0, 4) === 'RIFF' && bytes.toString('ascii', 8, 12) === 'WEBP') {
    const kind = bytes.toString('ascii', 12, 16);
    if (kind === 'VP8X') return [1 + bytes.readUIntLE(24, 3), 1 + bytes.readUIntLE(27, 3)];
    if (kind === 'VP8 ') return [bytes.readUInt16LE(26) & 0x3fff, bytes.readUInt16LE(28) & 0x3fff];
    if (kind === 'VP8L') {
      const b = bytes.readUInt32LE(21);
      return [1 + (b & 0x3fff), 1 + ((b >> 14) & 0x3fff)];
    }
  }
  return null;
}

// Minimal 4x4 matrix helpers (column-major, like glTF).
function compose(t = [0, 0, 0], r = [0, 0, 0, 1], s = [1, 1, 1]) {
  const [x, y, z, w] = r;
  const [sx, sy, sz] = s;
  return [
    (1 - 2 * (y * y + z * z)) * sx, 2 * (x * y + z * w) * sx, 2 * (x * z - y * w) * sx, 0,
    2 * (x * y - z * w) * sy, (1 - 2 * (x * x + z * z)) * sy, 2 * (y * z + x * w) * sy, 0,
    2 * (x * z + y * w) * sz, 2 * (y * z - x * w) * sz, (1 - 2 * (x * x + y * y)) * sz, 0,
    t[0], t[1], t[2], 1,
  ];
}
function multiply(a, b) {
  const out = new Array(16).fill(0);
  for (let c = 0; c < 4; c++) for (let r = 0; r < 4; r++) for (let k = 0; k < 4; k++) out[c * 4 + r] += a[k * 4 + r] * b[c * 4 + k];
  return out;
}
const apply = (m, [x, y, z]) => [0, 1, 2].map((i) => m[i] * x + m[4 + i] * y + m[8 + i] * z + m[12 + i]);

/** Checks shared by fighters and dojos. Returns world matrices for every node. */
function checkModelBasics({ json, bin, size }, limits) {
  const mb = size / 1e6;
  (mb <= limits.fileMB ? pass : fail)(`file size ${mb.toFixed(1)} MB (limit ${limits.fileMB} MB)`);

  const used = json.extensionsUsed ?? [];
  const bad = used.filter((e) => !ALLOWED_EXT.test(e));
  (bad.length ? fail : pass)(`extensions: ${used.join(', ') || 'none'}${bad.length ? ` (not allowed: ${bad.join(', ')})` : ''}`);

  const externalBuffers = (json.buffers ?? []).filter((b) => b.uri);
  const externalImages = (json.images ?? []).filter((im) => im.uri);
  (externalBuffers.length || externalImages.length ? fail : pass)('self-contained (no external URIs)');

  // Textures
  const sizes = [];
  for (const im of json.images ?? []) {
    if (im.bufferView === undefined || !bin) continue;
    const bv = json.bufferViews[im.bufferView];
    const bytes = bin.subarray(bv.byteOffset ?? 0, (bv.byteOffset ?? 0) + bv.byteLength);
    sizes.push(imageSize(Buffer.from(bytes)) ?? [0, 0]);
  }
  const biggest = sizes.reduce((m, [w, h]) => Math.max(m, w, h), 0);
  ((json.images ?? []).length <= limits.textures ? pass : fail)(`${(json.images ?? []).length} textures (limit ${limits.textures})`);
  (biggest <= limits.texturePx ? pass : fail)(`largest texture ${biggest} px (limit ${limits.texturePx})`);

  // Triangles (each mesh counted once per node that uses it)
  let tris = 0;
  for (const node of json.nodes ?? []) {
    if (node.mesh === undefined) continue;
    for (const prim of json.meshes[node.mesh].primitives) {
      const mode = prim.mode ?? 4;
      if (mode !== 4) continue;
      const count = prim.indices !== undefined ? json.accessors[prim.indices].count : json.accessors[prim.attributes.POSITION].count;
      tris += count / 3;
    }
  }
  (tris <= limits.triangles ? pass : fail)(`${Math.round(tris).toLocaleString()} triangles (limit ${limits.triangles.toLocaleString()})`);

  const world = new Array(json.nodes?.length ?? 0);
  const visit = (i, parent) => {
    const n = json.nodes[i];
    const local = n.matrix ?? compose(n.translation, n.rotation, n.scale);
    world[i] = parent ? multiply(parent, local) : local;
    for (const c of n.children ?? []) visit(c, world[i]);
  };
  (json.scenes?.[json.scene ?? 0]?.nodes ?? []).forEach((r) => visit(r, null));
  return world;
}

/** World-space bounding box of one primitive (bind pose for skinned meshes). */
function primitiveBox(json, node, world, prim) {
  const acc = json.accessors[prim.attributes.POSITION];
  if (!acc.min || !acc.max) return null;
  const m = node.skin !== undefined ? compose() : world;
  const min = [Infinity, Infinity, Infinity];
  const max = [-Infinity, -Infinity, -Infinity];
  for (const x of [acc.min[0], acc.max[0]]) for (const y of [acc.min[1], acc.max[1]]) for (const z of [acc.min[2], acc.max[2]]) {
    const p = apply(m, [x, y, z]);
    for (let k = 0; k < 3; k++) { min[k] = Math.min(min[k], p[k]); max[k] = Math.max(max[k], p[k]); }
  }
  return { min, max };
}

function checkGlb(file, label = 'fighter.glb') {
  if (!fs.existsSync(file)) return fail(`${label} is missing`);
  let glb;
  try { glb = readGlb(file); } catch (err) { return fail(`${label} cannot be parsed: ${err.message}`); }
  const { json } = glb;
  const world = checkModelBasics(glb, LIMITS);

  // Skeleton
  const skins = json.skins ?? [];
  if (!skins.length) fail('no skin / skeleton');
  else {
    const jointNames = new Set(skins.flatMap((s) => s.joints.map((j) => json.nodes[j].name)));
    const missing = BONES.filter((b) => !jointNames.has(b));
    (missing.length ? fail : pass)(`Mixamo skeleton${missing.length ? ` — missing: ${missing.join(', ')}` : ' (all required mixamorig: bones present)'}`);
  }

  // Animations and lengths compared with the reference fighter
  const anims = Object.fromEntries((json.animations ?? []).map((a) => [a.name, a]));
  const missingClips = CLIPS.filter((c) => !anims[c]);
  (missingClips.length ? fail : pass)(`animations: ${CLIPS.length - missingClips.length}/${CLIPS.length}${missingClips.length ? ` — missing: ${missingClips.join(', ')}` : ''}`);
  const duration = (j, a) => Math.max(...a.samplers.map((s) => j.accessors[s.input].max?.[0] ?? 0));
  if (fs.existsSync(REFERENCE_GLB) && path.resolve(file) !== path.resolve(REFERENCE_GLB)) {
    const ref = readGlb(REFERENCE_GLB).json;
    const refAnims = Object.fromEntries(ref.animations.map((a) => [a.name, duration(ref, a)]));
    const off = CLIPS.filter((c) => anims[c] && refAnims[c])
      .filter((c) => Math.abs(duration(json, anims[c]) - refAnims[c]) > refAnims[c] * 0.1);
    (off.length ? fail : pass)(`clip lengths within ±10 % of reference${off.length ? ` — off: ${off.join(', ')}` : ''}`);
  }

  // Height, from the bind-pose bounding box of the meshes in world space.
  let minY = Infinity, maxY = -Infinity;
  json.nodes.forEach((n, i) => {
    if (n.mesh === undefined || !world[i]) return;
    for (const prim of json.meshes[n.mesh].primitives) {
      const box = primitiveBox(json, n, world[i], prim);
      if (!box) continue;
      minY = Math.min(minY, box.min[1]);
      maxY = Math.max(maxY, box.max[1]);
    }
  });
  const height = maxY - minY;
  if (Number.isFinite(height)) {
    (height >= LIMITS.minHeight && height <= LIMITS.maxHeight ? pass : warn)(
      `bind-pose mesh height ≈ ${height.toFixed(2)} m (expected ${LIMITS.minHeight}–${LIMITS.maxHeight} m; check scale if far off)`);
  }
}

// ---------- Brain ----------
function checkBrain(file) {
  if (!fs.existsSync(file)) return fail('brain.js is missing');
  const raw = fs.readFileSync(file, 'utf8');
  // Only code counts: comments and string contents (e.g. "active window") are ignored by the checks below.
  const src = raw
    .replace(/\/\*[\s\S]*?\*\//g, ' ')
    .replace(/(^|[^:\\])\/\/.*$/gm, '$1')
    .replace(/(['"`])(?:\\.|(?!\1)[^\\\n])*\1/g, '""');
  const banned = [/\bimport\s*\(/, /^\s*import\s/m, /\brequire\s*\(/, /\bfetch\s*\(/, /\beval\s*\(/, /\bFunction\s*\(/,
    /\bglobalThis\b/, /\bwindow\b/, /\bprocess\b/, /\bdocument\b/, /\bsetTimeout\b|\bsetInterval\b/, /\bXMLHttpRequest\b|\bWebSocket\b/];
  const hits = banned.filter((re) => re.test(src));
  if (hits.length) return fail(`brain.js uses forbidden features: ${hits.map(String).join(' ')}`);
  if (!/export\s+default\s+function/.test(src)) return fail('brain.js must `export default function brain(state)`');

  const code = raw.replace(/export\s+default\s+function/, 'globalThis.__brain = function');
  const context = vm.createContext({ Math });
  try {
    vm.runInContext(code, context, { timeout: 500 });
  } catch (err) {
    return fail(`brain.js failed to load: ${err.message}`);
  }
  const brain = context.__brain;
  if (typeof brain !== 'function') return fail('brain.js did not produce a function');

  const memory = {};
  const states = ['idle', 'walk_f', 'walk_b', 'block', 'attack', 'hit', 'ko', 'victory', 'taunt'];
  let bad = null;
  const t0 = process.hrtime.bigint();
  const N = 500;
  for (let i = 0; i < N; i++) {
    const s = {
      time: i / 10,
      me: { x: -1, hp: 100 - (i % 100), maxHp: 100, state: states[i % states.length], facing: 1 },
      foe: { x: 1, hp: 100 - ((i * 7) % 100), maxHp: 100, state: states[(i * 3) % states.length], facing: -1,
             move: i % 4 === 0 ? 'jab' : null },
      distance: 0.8 + (i % 30) / 10, round: 1 + (i % 3), roundsWon: i % 2, foeRoundsWon: (i + 1) % 2, memory,
    };
    let out;
    try { out = vm.runInContext('__brain(__s)', Object.assign(context, { __s: s }), { timeout: 50 }); } catch (err) {
      bad = `threw: ${err.message}`;
      break;
    }
    if (!out || typeof out !== 'object') { bad = 'returned a non-object'; break; }
    if (out.move !== null && out.move !== undefined && !MOVES.includes(out.move)) { bad = `invalid move "${out.move}"`; break; }
    for (const k of ['fwd', 'back', 'block']) if (out[k] !== undefined && typeof out[k] !== 'boolean') { bad = `${k} is not boolean`; break; }
    if (bad) break;
  }
  if (bad) return fail(`brain.js ${bad}`);
  const avgMs = Number(process.hrtime.bigint() - t0) / 1e6 / N;
  (avgMs <= 2 ? pass : fail)(`brain.js runs in the sandbox, valid outputs, ${avgMs.toFixed(3)} ms average (limit 2 ms)`);
}

// ---------- Entry ----------
function checkEntry(id) {
  const dir = path.join(HERE, 'entries', id);
  if (!fs.existsSync(dir)) { fail(`entry folder ${dir} does not exist`); return; }
  const manifestPath = path.join(dir, 'manifest.json');
  let manifest = null;
  if (!fs.existsSync(manifestPath)) fail('manifest.json is missing');
  else {
    try {
      manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
      const missing = ['id', 'displayName', 'agent', 'category', 'fighter', 'brain', 'style', 'claims'].filter((k) => !(k in manifest));
      (missing.length ? fail : pass)(`manifest.json${missing.length ? ` — missing fields: ${missing.join(', ')}` : ' has all fields'}`);
      if (manifest.id !== id) fail(`manifest id "${manifest.id}" does not match folder "${id}"`);
      if (!['A', 'B', 'O'].includes(manifest.category)) fail('manifest category must be "A", "B" or "O"');
      // Category O is the owner's own entry (RULES.md §12), and only that one.
      if ((manifest.category === 'O') !== (id === 'me')) fail('category "O" is only for entry "me", and entry "me" must be category "O"');
    } catch (err) { fail(`manifest.json is not valid JSON: ${err.message}`); }
  }
  checkGlb(path.join(dir, manifest?.fighter ?? 'fighter.glb'));
  checkBrain(path.join(dir, manifest?.brain ?? 'brain.js'));
  for (const r of ['front', 'three_quarter', 'profile', 'closeup']) {
    const p = path.join(dir, 'renders', `${r}.png`);
    if (!fs.existsSync(p)) { fail(`renders/${r}.png is missing`); continue; }
    const dims = imageSize(fs.readFileSync(p));
    if (!dims) fail(`renders/${r}.png is not a readable PNG`);
    else (Math.max(...dims) >= 1920 ? pass : fail)(`renders/${r}.png ${dims[0]}×${dims[1]} (long side ≥ 1920)`);
  }
  for (const doc of ['NOTES.md', 'LICENSES.md']) {
    const p = path.join(dir, doc);
    (fs.existsSync(p) && fs.statSync(p).size > 200 ? pass : fail)(`${doc} present and filled in`);
  }
}

// ---------- Dojo (RULES.md §9) ----------
const DOJO_LIMITS = { fileMB: 150, triangles: 1_500_000, texturePx: 4096, textures: 80 };
const LANE = { min: [-4.5, 0, -1.2], max: [4.5, 2.6, 1.2] };

function checkDojo(dirArg) {
  const dir = path.resolve(dirArg);
  if (!fs.existsSync(dir)) { fail(`dojo folder ${dir} does not exist`); return; }
  let manifest = null;
  try {
    manifest = JSON.parse(fs.readFileSync(path.join(dir, 'manifest.json'), 'utf8'));
    const missing = ['name', 'author', 'season', 'dojo', 'claims'].filter((k) => !(k in manifest));
    (missing.length ? fail : pass)(`manifest.json${missing.length ? ` — missing fields: ${missing.join(', ')}` : ' has the required fields'}`);
  } catch (err) {
    fail(`manifest.json missing or invalid: ${err.message}`);
  }
  const file = path.join(dir, manifest?.dojo ?? 'dojo.glb');
  if (!fs.existsSync(file)) fail(`${manifest?.dojo ?? 'dojo.glb'} is missing`);
  else {
    let glb = null;
    try { glb = readGlb(file); } catch (err) { fail(`dojo.glb cannot be parsed: ${err.message}`); }
    if (glb) {
      const world = checkModelBasics(glb, DOJO_LIMITS);
      const { json } = glb;
      // Fight lane: only the floor (top at y ≈ 0) may reach into it.
      const intruders = [];
      let floorTop = null;
      json.nodes.forEach((n, i) => {
        if (n.mesh === undefined || !world[i]) return;
        json.meshes[n.mesh].primitives.forEach((prim) => {
          const b = primitiveBox(json, n, world[i], prim);
          if (!b) return;
          const overlapsXZ = b.max[0] > LANE.min[0] && b.min[0] < LANE.max[0] && b.max[2] > LANE.min[2] && b.min[2] < LANE.max[2];
          if (!overlapsXZ) return;
          if (b.max[1] <= 0.02) { floorTop = Math.max(floorTop ?? -Infinity, b.max[1]); return; }
          if (b.min[1] < LANE.max[1] && b.max[1] > LANE.min[1]) intruders.push(n.name ?? `node ${i}`);
        });
      });
      (floorTop !== null && Math.abs(floorTop) <= 0.02 ? pass : fail)(
        `floor under the fight lane with its top at y = 0${floorTop === null ? ' — none found' : ` (top ${floorTop.toFixed(3)} m)`}`);
      // A single big room mesh can wrap the lane without blocking it, so this is a warning for the judge to inspect.
      (intruders.length ? warn : pass)(`fight lane clear${intruders.length ? ` — bounding boxes reaching into it: ${[...new Set(intruders)].slice(0, 8).join(', ')}` : ''}`);
    }
  }
  if (manifest?.environment) {
    const hdr = path.join(dir, manifest.environment);
    if (!fs.existsSync(hdr)) fail(`environment ${manifest.environment} is missing`);
    else {
      const mb = fs.statSync(hdr).size / 1e6;
      (mb <= 40 ? pass : fail)(`environment HDR ${mb.toFixed(1)} MB (limit 40 MB)`);
    }
  }
  for (const r of ['wide', 'detail']) {
    const p = path.join(dir, 'renders', `${r}.png`);
    if (!fs.existsSync(p)) { fail(`renders/${r}.png is missing`); continue; }
    const dims = imageSize(fs.readFileSync(p));
    (dims && Math.max(...dims) >= 1920 ? pass : fail)(`renders/${r}.png ${dims ? `${dims[0]}×${dims[1]}` : 'unreadable'} (long side ≥ 1920)`);
  }
  for (const doc of ['NOTES.md', 'LICENSES.md']) {
    const p = path.join(dir, doc);
    (fs.existsSync(p) && fs.statSync(p).size > 200 ? pass : fail)(`${doc} present and filled in`);
  }
}

const args = process.argv.slice(2);
if (args[0] === '--glb' && args[1]) checkGlb(path.resolve(args[1]), path.basename(args[1]));
else if (args[0] === '--dojo' && args[1]) checkDojo(args[1]);
else if (args[0]) checkEntry(args[0]);
else {
  console.log('Usage: node validate_entry.mjs <entry-id> | --glb <file.glb> | --dojo <folder>');
  process.exit(2);
}

for (const [level, msg] of results) console.log(`${level}  ${msg}`);
const failed = results.filter(([l]) => l === 'FAIL').length;
console.log(failed ? `\n${failed} check(s) failed.` : '\nAll checks passed.');
process.exit(failed ? 1 : 0);
