#!/usr/bin/env node
// Automatic weigh-in (RULES.md §10). Run every 5 minutes by the dev server, or by hand:
//
//   node competition/judge_pass.mjs --pending   judge every entry whose READY.json answers the current call
//   node competition/judge_pass.mjs <id>        judge one entry now
//
// For each entry: validate → (fail: send back with the FAIL lines) → render in the Three.js harness with headless
// Chrome → a headless Claude judge scores realism into scores.json and approves or sends back with a verdict.
// Claude's own entry is never scored here (the owner scores it); it's approved on the automated checks alone.
// Finally the result is committed and pushed.

import { execFileSync, spawn, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { cleanEnv } from './bell.mjs';
import { announce } from './announce.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');
const STATE_DIR = path.join(HERE, '.bell');
const STATE_FILE = path.join(STATE_DIR, 'judged.json');
const LOCK = path.join(STATE_DIR, 'judge.lock');
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const COMPETITORS = ['claude', 'gemini', 'grok', 'hermes', 'muse', 'aaron', 'me'];

const readJson = (f, fallback) => { try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch { return fallback; } };
const log = (...a) => console.log(new Date().toISOString(), '[judge]', ...a);

function weighIn(kind, id, verdict) {
  const r = spawnSync(process.execPath, [path.join(HERE, 'weigh_in.mjs'), kind, id, verdict], { cwd: ROOT, encoding: 'utf8' });
  log(id, kind, r.status === 0 ? 'ok' : `failed: ${r.stderr.trim()}`);
  return r.status === 0;
}

/** Standardised renders via the harness page in headless Chrome (needs the dev server on :5173). */
function harness(id) {
  const out = path.join(HERE, 'judging', id);
  const last = path.join(out, 'action_roundhouse.png'); // the harness saves this view last
  const mtime = () => (fs.existsSync(last) ? fs.statSync(last).mtimeMs : 0);
  const before = mtime();
  // Real-time headless Chrome (virtual time skips ahead before the model finishes loading); stop once saved.
  const chrome = spawn(CHROME, ['--headless=new', '--enable-unsafe-swiftshader', '--use-angle=swiftshader',
    '--window-size=1920,1080', `--user-data-dir=${path.join(STATE_DIR, 'chrome-judge')}`, '--remote-debugging-port=0',
    `http://localhost:5173/judge.html?id=${id}`], { stdio: 'ignore' });
  const sleep = (ms) => Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
  for (let waited = 0; waited < 180000 && mtime() <= before; waited += 2000) sleep(2000);
  sleep(1500);
  chrome.kill();
  return mtime() > before;
}

function judgePrompt(id, ready, rendered) {
  return `You are Claude, the JUDGE of The Dojo Invitational (project ${ROOT}). Judge entry "${id}" for its automatic weigh-in.

Read competition/RULES.md sections 6-7 (the Realism Score rubric), competition/entries/${id}/manifest.json, NOTES.md and READY.json
(the entrant says: ${JSON.stringify(ready?.summary ?? '')}), and look at the images in ${rendered ? `competition/judging/${id}/ (standardised Three.js harness renders)` : `competition/entries/${id}/renders/ (the harness renders could not be made this time; say so in your notes)`}.
Compare with the current scorecard in competition/scores.json.

Then do exactly two things, and nothing else:
1. Update ONLY the "entry:${id}" record in competition/scores.json with the rubric breakdown
   {"fighter": {"skin","face","hair","clothing","overall"}, "fight": {"motion","contact","grounding"}, "total", "notes", "method": "harness"},
   where notes is one or two plain sentences on what holds the fighter back. Apply the honesty penalties if a claim is false.
2. Run: node competition/weigh_in.mjs approve ${id} "<one-sentence verdict>"   (or "reject" if the entry is broken, unusable
   or breaks a rule, with the verdict saying what to fix).

Don't edit any other file. Don't run any git command (no checkout, commit or push): the weigh-in script does the git work.
Be fair: the same rubric for everyone.`;
}

/** The ring announcer's introduction for the card this pass just made (announce.mjs). */
function announceNew(id, cardsBefore) {
  const cards = readJson(path.join(HERE, 'weighins.json'), []);
  const card = cards.slice(cardsBefore).filter((c) => c.id === id).pop();
  if (!card) return;
  try { log(id, 'announced:', announce(card.no).text.slice(0, 80)); } catch (err) { log(id, 'announcer failed:', err.message); }
}

function judge(id) {
  const cardsBefore = readJson(path.join(HERE, 'weighins.json'), []).length;
  const dir = path.join(HERE, 'entries', id);
  const ready = readJson(path.join(dir, 'READY.json'), null);
  const v = spawnSync(process.execPath, [path.join(HERE, 'validate_entry.mjs'), id], { encoding: 'utf8' });
  if (v.status !== 0) {
    const fails = v.stdout.split('\n').filter((l) => l.startsWith('FAIL')).map((l) => l.slice(6)).join('; ');
    weighIn('reject', id, `Validator failed: ${fails.slice(0, 300)}. Fix these and write READY.json again.`);
    announceNew(id, cardsBefore);
    return;
  }
  const rendered = harness(id);
  log(id, rendered ? 'harness renders made' : 'harness renders not made (is the dev server up?)');
  if (id === 'claude') {
    weighIn('approve', id, `Self-submitted: passes every automated check. Realism awaits the owner's score. Entrant's note: ${(ready?.summary ?? '').slice(0, 200)}`);
  } else {
    const r = spawnSync('claude', ['-p', judgePrompt(id, ready, rendered), '--dangerously-skip-permissions'],
      { cwd: ROOT, encoding: 'utf8', timeout: 20 * 60 * 1000, env: cleanEnv() });
    log(id, 'judge run exit', r.status, (r.stdout ?? '').trim().split('\n').slice(-2).join(' | '));
    // The weigh-in merges into main; a judge that switched branches would strand it (it happened once, with entry/me).
    const head = execFileSync('git', ['rev-parse', '--abbrev-ref', 'HEAD'], { cwd: ROOT, encoding: 'utf8' }).trim();
    if (head !== 'main') {
      log(id, `judge left the checkout on ${head}; switching back to main`);
      execFileSync('git', ['checkout', '-q', 'main'], { cwd: ROOT });
    }
  }
  announceNew(id, cardsBefore);
  const git = (...a) => execFileSync('git', a, { cwd: ROOT, encoding: 'utf8' }).trim();
  try {
    // The owner's renders show a real face: they stay on the Mac (competition/judging/me is git-ignored).
    git('add', '--', 'competition/scores.json', ...(id === 'me' ? [] : [`competition/judging/${id}`]), 'competition/announcements');
    if (git('diff', '--cached', '--name-only')) git('commit', '-q', '-m', `Judge's scorecard: ${id}\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`);
    git('-c', 'credential.helper=', '-c', 'credential.helper=!gh auth git-credential', 'push', '-q', 'origin', 'main', `entry/${id}`);
    log(id, 'pushed');
  } catch (err) {
    log(id, 'git step failed:', err.message.split('\n')[0]);
  }
}

function main() {
  fs.mkdirSync(STATE_DIR, { recursive: true });
  const args = process.argv.slice(2);
  if (fs.existsSync(LOCK) && Date.now() - fs.statSync(LOCK).mtimeMs < 60 * 60 * 1000) return; // a pass is running
  fs.writeFileSync(LOCK, String(process.pid));
  try {
    if (args[0] && args[0] !== '--pending') { judge(args[0]); return; }
    const call = readJson(path.join(HERE, 'calls', 'current.json'), null);
    if (!call) return;
    const judged = readJson(STATE_FILE, {});
    for (const id of COMPETITORS) {
      const ready = readJson(path.join(HERE, 'entries', id, 'READY.json'), null);
      if (!ready || ready.call < call.call) continue;
      const stamp = `${ready.call}:${ready.at}`;
      if (judged[id] === stamp) continue;
      log(id, `READY for call ${ready.call}: judging`);
      judge(id);
      judged[id] = stamp;
      fs.writeFileSync(STATE_FILE, JSON.stringify(judged, null, 2));
    }
  } finally {
    fs.rmSync(LOCK, { force: true });
  }
}

main();
