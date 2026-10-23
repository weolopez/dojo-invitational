#!/usr/bin/env node
// The Bell (RULES.md §10): after each tournament, wake the agents that have a command line and ask for an update.
//
//   node competition/bell.mjs            ring for the current call (competition/calls/current.json)
//   node competition/bell.mjs --dry-run  print what would run
//
// Each agent runs headless in the project folder with full tool access (the owner chose this), works only in its
// own entry folder per the rules, and finishes by writing competition/entries/<id>/READY.json.
// Grok Bot, Muse and Aaron have no command line here; they run their own routines (prompts/routine.md).
// Caps: one run per agent per call, at most one run per agent per hour, 75 minutes per run.

import { spawn, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');
const STATE_DIR = path.join(HERE, '.bell');
const STATE_FILE = path.join(STATE_DIR, 'state.json');
const CALL_FILE = path.join(HERE, 'calls', 'current.json');
const RUN_LIMIT_MS = 75 * 60 * 1000;
const MIN_GAP_MS = 60 * 60 * 1000;

const AGENTS = {
  // Google retired the Gemini CLI's free tier in favour of Antigravity, so Gemini runs through `agy`.
  gemini: { name: 'Gemini', cmd: process.env.HOME + '/.local/bin/agy', args: (p) => ['-p', p, '--dangerously-skip-permissions', '--add-dir', ROOT] },
  hermes: { name: 'Hermes', cmd: process.env.HOME + '/.local/bin/hermes', args: (p) => ['-z', p, '--yolo', '--in', ROOT] },
  claude: { name: 'Claude', cmd: 'claude', args: (p) => ['-p', p, '--dangerously-skip-permissions'] },
};

/** The environment without variables inherited from the Claude session that runs the dev server, so each CLI
 *  uses its own login. */
export function cleanEnv() {
  return Object.fromEntries(Object.entries(process.env).filter(([k]) => !/^(ANTHROPIC_|CLAUDE_CODE_|CLAUDECODE)/.test(k)));
}

const readJson = (f, fallback) => { try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch { return fallback; } };

export function prompt(id, name, call) {
  const competitorNote = id === 'claude'
    ? '\nYou are Claude the COMPETITOR in this run, not the judge: never edit competition/scores.json, approved.json, weighins.json or any other entry.'
    : '';
  return `You are ${name}, competitor id "${id}" in The Dojo Invitational, a contest to build the most hyper-realistic 3D fighter.
Project: ${ROOT}. This is an automatic update round after tournament ${call.tournament}.${competitorNote}

1. Read competition/AGENTS.md (one page), then competition/calls/${id}.md: the judge's notes on exactly what holds your fighter back.
2. Improve your fighter's realism (and your fight brain if you like), working ONLY in competition/entries/${id}/. Bulky scratch goes in .work/ inside it.
3. Check it in Three.js if you can: with the dev server running, http://localhost:5173/judge.html?id=${id} saves renders to competition/judging/${id}/.
4. Run: node competition/validate_entry.mjs ${id}  until it prints "All checks passed". Paste the output at the end of NOTES.md.
5. Finish by writing competition/entries/${id}/READY.json as {"call": ${call.call}, "at": "<ISO time>", "summary": "<what you changed, honestly>"}.

Rules: don't touch other folders, don't commit or push, never ask for passwords or payments, and be honest in NOTES.md (each false claim costs 10 points).
If you can't make an improvement this round, say so in READY.json's summary instead of faking one.`;
}

/** Commit and push the call, so agents on other machines (Aaron) see it with a git pull. */
function publishCall(call) {
  const git = (...a) => spawnSync('git', a, { cwd: ROOT, encoding: 'utf8' });
  git('add', '--', 'competition/calls');
  if (git('diff', '--cached', '--quiet').status === 0) return;
  git('commit', '-q', '-m', `Call for updates #${call.call} after tournament ${call.tournament}\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`);
  const push = git('-c', 'credential.helper=', '-c', 'credential.helper=!gh auth git-credential', 'push', '-q', 'origin', 'main');
  console.log(`[bell] call #${call.call} ${push.status === 0 ? 'pushed' : 'committed (push failed)'}`);
}

function ring(dryRun) {
  const call = readJson(CALL_FILE, null);
  if (!call) { console.log('[bell] no call yet (competition/calls/current.json)'); return; }
  if (!dryRun) publishCall(call);
  fs.mkdirSync(path.join(STATE_DIR, 'logs'), { recursive: true });
  const state = readJson(STATE_FILE, { runs: {} });
  for (const [id, agent] of Object.entries(AGENTS)) {
    const entryDir = path.join(HERE, 'entries', id);
    const ready = readJson(path.join(entryDir, 'READY.json'), null);
    const last = state.runs[id] ?? {};
    const why = !fs.existsSync(path.join(entryDir, 'manifest.json')) ? 'no entry yet'
      : ready?.call >= call.call ? 'already READY for this call'
        : last.call === call.call && last.tries >= 3 ? 'three tries used for this call'
          : last.running && Date.now() - last.startedAt < RUN_LIMIT_MS ? 'still running'
            : last.startedAt && Date.now() - last.startedAt < MIN_GAP_MS ? 'ran less than an hour ago'
              : null;
    if (why) { console.log(`[bell] ${id}: skip (${why})`); continue; }
    const p = prompt(id, agent.name, call);
    if (dryRun) { console.log(`[bell] ${id}: would run ${agent.cmd}`); continue; }
    const log = fs.openSync(path.join(STATE_DIR, 'logs', `${id}-call${call.call}.log`), 'a');
    const child = spawn(agent.cmd, agent.args(p), { cwd: ROOT, stdio: ['ignore', log, log], detached: true, env: cleanEnv() });
    const tries = last.call === call.call ? (last.tries ?? 0) + 1 : 1;
    state.runs[id] = { call: call.call, startedAt: Date.now(), running: true, pid: child.pid, tries };
    child.on('error', (err) => fs.appendFileSync(path.join(STATE_DIR, 'logs', `${id}-call${call.call}.log`), `\n[bell] failed to start: ${err.message}\n`));
    const timer = setTimeout(() => { try { process.kill(-child.pid); } catch { /* already gone */ } }, RUN_LIMIT_MS);
    child.on('exit', (code) => {
      clearTimeout(timer);
      const s = readJson(STATE_FILE, { runs: {} });
      s.runs[id] = { ...s.runs[id], running: false, exitCode: code, endedAt: Date.now() };
      fs.writeFileSync(STATE_FILE, JSON.stringify(s, null, 2));
      console.log(`[bell] ${id}: finished with code ${code}`);
    });
    console.log(`[bell] ${id}: started (${agent.cmd}, try ${tries}, pid ${child.pid})`);
  }
  fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2));
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  ring(process.argv.includes('--dry-run'));
}
