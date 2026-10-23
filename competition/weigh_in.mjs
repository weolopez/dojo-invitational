#!/usr/bin/env node
// The Weigh-In: how a competitor's work gets into a tournament (RULES.md §11).
//
//   node competition/weigh_in.mjs                      list every entry and whether it changed since its last approval
//   node competition/weigh_in.mjs approve <id> "<verdict>"   validate, snapshot to branch entry/<id>, merge to main, lock files
//   node competition/weigh_in.mjs reject <id> "<verdict>"    snapshot to entry/<id> and record the verdict; nothing goes live
//
// Agents never need git: their folder is snapshotted onto their own branch at weigh-in. Agents that do use git
// (e.g. on another machine) push commits to entry/<id>, and the judge pulls them into the folder before weighing in.
// Only a fixed allowlist of small text and image files is committed; fighter.glb is locked by sha256 instead.

import { execFileSync, spawnSync } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');
const COMPETITORS = ['claude', 'gemini', 'grok', 'hermes', 'muse', 'aaron'];
const APPROVED_FILE = path.join(HERE, 'approved.json');
const WEIGHINS_FILE = path.join(HERE, 'weighins.json');
const SCORES_FILE = path.join(HERE, 'scores.json');
const LOCKED = ['manifest.json', 'fighter.glb', 'brain.js'];
const MAX_COMMIT_FILE = 2_000_000; // bytes; bigger files belong in .work/
const MAX_RENDER_FILE = 8_000_000;
const TRAILER = '\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>';

const git = (...args) => execFileSync('git', args, { cwd: ROOT, encoding: 'utf8' }).trim();
const gitEnv = (env, ...args) => execFileSync('git', args, { cwd: ROOT, encoding: 'utf8', env: { ...process.env, ...env } }).trim();
const readJson = (f, fallback) => { try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch { return fallback; } };
const sha = (f) => (fs.existsSync(f) ? crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex') : null);
const entryDir = (id) => path.join(HERE, 'entries', id);

/** Files from an entry that are committed: manifest, brain, docs, renders and small source files. */
function committable(id) {
  const dir = entryDir(id);
  const out = [];
  const take = (rel) => {
    const full = path.join(dir, rel);
    const cap = rel.startsWith('renders') ? MAX_RENDER_FILE : MAX_COMMIT_FILE;
    if (fs.existsSync(full) && fs.statSync(full).isFile() && fs.statSync(full).size <= cap) out.push(rel);
  };
  ['manifest.json', 'brain.js', 'NOTES.md', 'LICENSES.md', 'FEEDBACK.md'].forEach(take);
  for (const sub of ['renders', 'source']) {
    const base = path.join(dir, sub);
    if (!fs.existsSync(base)) continue;
    const walk = (rel) => {
      for (const name of fs.readdirSync(path.join(dir, rel))) {
        const r = path.join(rel, name);
        if (fs.statSync(path.join(dir, r)).isDirectory()) walk(r);
        else if (sub === 'renders' ? /\.(png|jpe?g|webp)$/i.test(name) : /\.(py|js|mjs|json|md|txt|sh)$/i.test(name)) take(r);
      }
    };
    walk(sub);
  }
  return out.map((r) => path.join('competition', 'entries', id, r));
}

function fingerprint(id) {
  return Object.fromEntries(LOCKED.map((f) => [f, sha(path.join(entryDir(id), f))]));
}

function validate(id) {
  const r = spawnSync(process.execPath, [path.join(HERE, 'validate_entry.mjs'), id], { encoding: 'utf8' });
  const out = r.stdout ?? '';
  const pick = (re) => out.match(re)?.[1];
  return {
    ok: r.status === 0,
    output: out.trim(),
    tape: {
      sizeMB: Number(pick(/file size ([\d.]+) MB/)) || null,
      triangles: Number((pick(/([\d,]+) triangles/) ?? '').replace(/,/g, '')) || null,
      textures: Number(pick(/(\d+) textures/)) || null,
      largestTexture: Number(pick(/largest texture (\d+) px/)) || null,
      heightM: Number(pick(/height ≈ ([\d.]+) m/)) || null,
      extensions: pick(/extensions: (.*)/) ?? '',
    },
  };
}

/** Commit the entry's allowlisted files onto branch entry/<id> without touching the working tree. */
function snapshotToBranch(id, message) {
  const branch = `entry/${id}`;
  const exists = spawnSync('git', ['rev-parse', '--verify', '-q', `refs/heads/${branch}`], { cwd: ROOT }).status === 0;
  const parent = exists ? branch : 'main';
  const indexFile = path.join(ROOT, '.git', `weighin-${id}.index`);
  const env = { GIT_INDEX_FILE: indexFile };
  try {
    gitEnv(env, 'read-tree', parent);
    gitEnv(env, 'rm', '-r', '-q', '--cached', '--ignore-unmatch', `competition/entries/${id}`);
    const files = committable(id);
    if (files.length) gitEnv(env, 'add', '-f', '--', ...files);
    const tree = gitEnv(env, 'write-tree');
    const parentTree = git('rev-parse', `${parent}^{tree}`);
    if (tree === parentTree && exists) return { commit: git('rev-parse', branch), files, changed: false };
    const commit = gitEnv(env, 'commit-tree', tree, '-p', parent, '-m', message);
    git('update-ref', `refs/heads/${branch}`, commit);
    return { commit, files, changed: true };
  } finally {
    fs.rmSync(indexFile, { force: true });
  }
}

/** Merge the branch snapshot into main (the working tree already holds the same files). */
function mergeToMain(id, branchCommit, files, message) {
  if (git('rev-parse', '--abbrev-ref', 'HEAD') !== 'main') throw new Error('check out main before approving');
  git('rm', '-r', '-q', '--cached', '--ignore-unmatch', `competition/entries/${id}`);
  if (files.length) git('add', '-f', '--', ...files);
  git('add', '--', path.relative(ROOT, APPROVED_FILE), path.relative(ROOT, WEIGHINS_FILE));
  const tree = git('write-tree');
  const commit = git('commit-tree', tree, '-p', 'HEAD', '-p', branchCommit, '-m', message);
  git('update-ref', 'refs/heads/main', commit);
  return commit;
}

function list() {
  const approved = readJson(APPROVED_FILE, {});
  const scores = readJson(SCORES_FILE, {}).scores ?? {};
  console.log('THE WEIGH-IN · entries waiting for the judge\n');
  for (const id of COMPETITORS) {
    const dir = entryDir(id);
    const has = fs.existsSync(path.join(dir, 'manifest.json'));
    const fp = fingerprint(id);
    const a = approved[id];
    const status = !has ? 'no entry yet'
      : !a ? 'NEW — never weighed in'
        : LOCKED.every((f) => a.locked?.[f] === fp[f]) ? 'approved, unchanged' : 'CHANGED since approval';
    const score = scores[`entry:${id}`]?.total;
    console.log(`${id.padEnd(7)} ${status}${score !== undefined ? ` · realism ${score}/100` : ''}`);
    if (has && status !== 'approved, unchanged') {
      const v = validate(id);
      const t = v.tape;
      console.log(`        validator ${v.ok ? 'PASS' : 'FAIL'} · ${t.sizeMB ?? '?'} MB · ${t.triangles?.toLocaleString() ?? '?'} tris · ${t.textures ?? '?'} textures ≤ ${t.largestTexture ?? '?'} px · ${t.heightM ?? '?'} m`);
      if (!v.ok) v.output.split('\n').filter((l) => l.startsWith('FAIL')).forEach((l) => console.log(`        ${l}`));
    }
  }
  console.log('\nApprove: node competition/weigh_in.mjs approve <id> "<verdict>"');
}

function decide(kind, id, verdict) {
  if (!COMPETITORS.includes(id)) throw new Error(`unknown competitor "${id}"`);
  if (!verdict) throw new Error('a verdict is required, e.g. "Real pores, needs planted feet"');
  const dir = entryDir(id);
  const manifest = readJson(path.join(dir, 'manifest.json'), null);
  if (!manifest) throw new Error(`no manifest.json in ${dir}`);
  const v = validate(id);
  if (kind === 'approve' && !v.ok) {
    console.log(v.output);
    throw new Error('validator failed: fix the FAILs before approval (or reject with a verdict)');
  }
  const weighins = readJson(WEIGHINS_FILE, []);
  const approved = readJson(APPROVED_FILE, {});
  const scores = readJson(SCORES_FILE, {}).scores ?? {};
  const no = weighins.length + 1;
  const snap = snapshotToBranch(id, `Weigh-in #${no} snapshot: ${id}\n\n${verdict}${TRAILER}`);
  const prev = approved[id]?.branchCommit;
  const changedFiles = prev ? git('diff', '--name-only', prev, snap.commit, '--', `competition/entries/${id}`).split('\n').filter(Boolean) : snap.files;
  const card = {
    no, at: new Date().toISOString(), id, name: manifest.displayName ?? id, agent: manifest.agent ?? id,
    decision: kind === 'approve' ? 'approved' : 'sent back', verdict, style: manifest.style ?? '',
    tape: v.tape, realism: scores[`entry:${id}`]?.total ?? null, realismBefore: approved[id]?.realism ?? null,
    changedFiles: changedFiles.map((f) => f.replace(`competition/entries/${id}/`, '')).slice(0, 12),
    fighterChanged: approved[id]?.locked?.['fighter.glb'] !== sha(path.join(dir, 'fighter.glb')),
    branch: `entry/${id}`, branchCommit: snap.commit,
  };
  weighins.push(card);
  if (kind === 'approve') {
    const lockDir = path.join(HERE, '.approved', id);
    fs.rmSync(lockDir, { recursive: true, force: true });
    fs.mkdirSync(lockDir, { recursive: true });
    for (const f of LOCKED) fs.copyFileSync(path.join(dir, f), path.join(lockDir, f));
    approved[id] = { approvedAt: card.at, weighIn: no, verdict, branchCommit: snap.commit, realism: card.realism,
      locked: fingerprint(id) };
    fs.writeFileSync(APPROVED_FILE, `${JSON.stringify(approved, null, 2)}\n`);
  }
  fs.writeFileSync(WEIGHINS_FILE, `${JSON.stringify(weighins, null, 2)}\n`);
  const title = kind === 'approve' ? `Weigh-in #${no}: ${card.name} approved` : `Weigh-in #${no}: ${card.name} sent back`;
  const commit = kind === 'approve'
    ? mergeToMain(id, snap.commit, snap.files, `${title}\n\n${verdict}${TRAILER}`)
    : (() => {
      git('add', '--', path.relative(ROOT, WEIGHINS_FILE));
      git('commit', '-q', '-m', `${title}\n\n${verdict}${TRAILER}`);
      return git('rev-parse', 'HEAD');
    })();
  console.log(`${title}\n  branch entry/${id} @ ${snap.commit.slice(0, 8)} · main @ ${commit.slice(0, 8)}`);
  console.log(`  ${card.changedFiles.length} file(s) changed${card.fighterChanged ? ', new fighter.glb' : ''} · verdict: ${verdict}`);
}

const [cmd, id, ...rest] = process.argv.slice(2);
try {
  if (!cmd || cmd === 'list') list();
  else if (cmd === 'approve' || cmd === 'reject') decide(cmd, id, rest.join(' '));
  else { console.log('Usage: weigh_in.mjs [list | approve <id> "<verdict>" | reject <id> "<verdict>"]'); process.exit(2); }
} catch (err) {
  console.error(`Weigh-in error: ${err.message}`);
  process.exit(1);
}
