import { defineConfig } from 'vite';
import { execFile, spawn } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

const COMPETITION = path.resolve(__dirname, '..', 'competition');
const ENTRIES = path.join(COMPETITION, 'entries');
const STATE_FILE = path.join(COMPETITION, 'tournament_state.json');
const RESULTS_FILE = path.join(COMPETITION, 'results.jsonl');
const SERVED_FILES = new Set(['fighter.glb', 'brain.js', 'manifest.json']);
const DOJOS = path.join(COMPETITION, 'dojos');
const CHAMPIONS_FILE = path.join(COMPETITION, 'champions.json');
const SCORES_FILE = path.join(COMPETITION, 'scores.json');
const APPROVED_FILE = path.join(COMPETITION, 'approved.json');
const APPROVED_DIR = path.join(COMPETITION, '.approved');
const WEIGHINS_FILE = path.join(COMPETITION, 'weighins.json');
const START_NOW_FILE = path.join(COMPETITION, 'start_now.json');
const sha256 = (f) => { try { return crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex'); } catch { return null; } };
const COMMISSION_TEMPLATE = path.join(COMPETITION, 'prompts', 'dojo_commission_template.md');
const BUILDERS = new Set(['claude', 'gemini', 'grok', 'hermes', 'muse', 'aaron', 'me']);
const DOJO_DIR = /^season-(\d+)-([a-z0-9_-]+)$/;

const dojoChecks = new Map();
function validDojo(folder) {
  const dir = path.join(DOJOS, folder);
  let stamp;
  try {
    const m = JSON.parse(fs.readFileSync(path.join(dir, 'manifest.json'), 'utf8'));
    stamp = [m.dojo, m.environment].filter(Boolean).concat('manifest.json')
      .map((f) => { try { return fs.statSync(path.join(dir, f)).mtimeMs; } catch { return 0; } }).join(':') + `:${validatorStamp()}`;
  } catch {
    return Promise.resolve(false);
  }
  const cached = dojoChecks.get(folder);
  if (cached && cached.stamp === stamp) return Promise.resolve(cached.ok);
  return new Promise((resolve) => {
    execFile(process.execPath, [path.join(COMPETITION, 'validate_entry.mjs'), '--dojo', dir], { timeout: 120_000 }, (err) => {
      dojoChecks.set(folder, { stamp, ok: !err });
      resolve(!err);
    });
  });
}

/** The call for updates after tournament `season`: competition/calls/current.json plus one note per competitor. */
function writeCalls(season, championId) {
  const dir = path.join(COMPETITION, 'calls');
  fs.mkdirSync(dir, { recursive: true });
  const scores = fs.existsSync(SCORES_FILE) ? JSON.parse(fs.readFileSync(SCORES_FILE, 'utf8')).scores ?? {} : {};
  const approved = fs.existsSync(APPROVED_FILE) ? JSON.parse(fs.readFileSync(APPROVED_FILE, 'utf8')) : {};
  const prev = fs.existsSync(path.join(dir, 'current.json')) ? JSON.parse(fs.readFileSync(path.join(dir, 'current.json'), 'utf8')) : null;
  const call = { call: (prev?.call ?? 0) + 1, tournament: season, at: new Date().toISOString(), champion: championId };
  const best = championId ? scores[championId]?.total : null;
  for (const id of BUILDERS) {
    const s = scores[`entry:${id}`];
    const lines = [
      `# Call for updates #${call.call} — after tournament ${season}`,
      '',
      s?.total != null ? `Your realism score: **${s.total}/100**${best != null ? ` (champion: ${best}/100)` : ''}.`
        : s?.scoredBy === 'owner' ? 'Your realism score is set by the owner and is still pending.' : 'You have no realism score yet.',
      '',
      s?.notes ? `**What holds you back (judge's notes):** ${s.notes}` : '',
      approved[id]?.verdict ? `**Last weigh-in verdict:** ${approved[id].verdict}` : '',
      '',
      'Improve your fighter, validate it, and write `READY.json` in your entry folder (see AGENTS.md).',
      'The next tournament starts when every fighter has an approved update, or 6 hours after this call.',
    ];
    fs.writeFileSync(path.join(dir, `${id}.md`), `${lines.filter((l, i, a) => l !== '' || a[i - 1] !== '').join('\n')}\n`);
  }
  fs.writeFileSync(path.join(dir, 'current.json'), JSON.stringify(call, null, 2));
}

/** Run a competition script in the background, detached from the dev server. */
function spawnDetached(script, args = []) {
  const logDir = path.join(COMPETITION, '.bell', 'logs');
  fs.mkdirSync(logDir, { recursive: true });
  const log = fs.openSync(path.join(logDir, `${script.replace('.mjs', '')}.log`), 'a');
  const child = spawn(process.execPath, [path.join(COMPETITION, script), ...args],
    { cwd: path.resolve(COMPETITION, '..'), detached: true, stdio: ['ignore', log, log] });
  child.unref();
}

/** Every champion-built dojo that passes the validator, newest first. */
async function allDojos() {
  if (!fs.existsSync(DOJOS)) return [];
  const folders = fs.readdirSync(DOJOS).filter((f) => DOJO_DIR.test(f))
    .sort((a, b) => Number(b.match(DOJO_DIR)[1]) - Number(a.match(DOJO_DIR)[1]));
  const out = [];
  for (const folder of folders) {
    if (!(await validDojo(folder))) continue;
    const m = JSON.parse(fs.readFileSync(path.join(DOJOS, folder, 'manifest.json'), 'utf8'));
    out.push({
      folder, name: m.name, author: m.author, season: Number(folder.match(DOJO_DIR)[1]),
      dojo: `/dojos/${folder}/${m.dojo}`, environment: m.environment ? `/dojos/${folder}/${m.environment}` : null,
      background: !!m.background, sun: m.sun ?? null,
    });
  }
  return out;
}

/** The newest dojo that passes the validator, or null for the built-in one. */
async function currentDojo() {
  return (await allDojos())[0] ?? null;
}

// Validation results, cached until an entry's files change.
const validated = new Map();

const validatorStamp = () => { try { return fs.statSync(path.join(COMPETITION, 'validate_entry.mjs')).mtimeMs; } catch { return 0; } };

function entryStamp(dir) {
  return ['manifest.json', 'fighter.glb', 'brain.js']
    .map((f) => { try { return fs.statSync(path.join(dir, f)).mtimeMs; } catch { return 0; } }).join(':') + `:${validatorStamp()}`;
}

function validate(id) {
  const dir = path.join(ENTRIES, id);
  const stamp = entryStamp(dir);
  const cached = validated.get(id);
  if (cached && cached.stamp === stamp) return Promise.resolve(cached.ok);
  return new Promise((resolve) => {
    execFile(process.execPath, [path.join(COMPETITION, 'validate_entry.mjs'), id], { timeout: 60_000 }, (err) => {
      validated.set(id, { stamp, ok: !err });
      resolve(!err);
    });
  });
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let data = '';
    req.on('data', (chunk) => { data += chunk; if (data.length > 5e6) reject(new Error('too large')); });
    req.on('end', () => resolve(data));
    req.on('error', reject);
  });
}

const json = (res, value, status = 200) => {
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json');
  res.end(JSON.stringify(value));
};

/** Dev-server endpoints for the competition arena: entry discovery, entry files, and the tournament log. */
let broadcastSeen = 0;
// The owner's link for other devices: http://<mac>:5173/?tournament&watch#owner=<token>. The token never leaves the
// Mac except in that link (the part after # isn't sent to servers or kept in their logs).
const OWNER_TOKEN_FILE = path.join(COMPETITION, '.bell', 'owner_token');
function ownerToken() {
  if (!fs.existsSync(OWNER_TOKEN_FILE)) {
    fs.mkdirSync(path.dirname(OWNER_TOKEN_FILE), { recursive: true });
    fs.writeFileSync(OWNER_TOKEN_FILE, crypto.randomBytes(18).toString('base64url'), { mode: 0o600 });
  }
  return fs.readFileSync(OWNER_TOKEN_FILE, 'utf8').trim();
}

function arenaApi() {
  return {
    name: 'dojo-arena-api',
    configureServer(server) {
      // Every 5 minutes, weigh in any entry that wrote READY.json for the current call (judge_pass.mjs).
      // The Bell rings again on the same beat so failed or interrupted agents retry (it enforces its own caps).
      setInterval(() => {
        spawnDetached('judge_pass.mjs', ['--pending']);
        spawnDetached('bell.mjs');
      }, 5 * 60 * 1000);
      server.middlewares.use(async (req, res, next) => {
        const url = new URL(req.url, 'http://localhost');
        // Other devices on the network (a phone watching with ?watch) may read but never write, except the owner's
        // controls (/api/bench, /api/start-now) sent with the owner's token.
        const local = ['127.0.0.1', '::1', '::ffff:127.0.0.1'].includes(req.socket.remoteAddress);
        const owner = ['/api/bench', '/api/start-now'].includes(url.pathname) && req.headers['x-owner-token'] === ownerToken();
        if (!local && !owner && req.method !== 'GET' && req.method !== 'HEAD' && url.pathname.startsWith('/api/')) {
          res.statusCode = 403;
          return res.end('Read-only from other devices');
        }
        try {
          // Only entries approved at a weigh-in fight, and only the locked (approved) copy of their files.
          if (url.pathname === '/api/entries' && req.method === 'GET') {
            const approved = fs.existsSync(APPROVED_FILE) ? JSON.parse(fs.readFileSync(APPROVED_FILE, 'utf8')) : {};
            const entries = [];
            for (const [id, a] of Object.entries(approved)) {
              const dir = path.join(APPROVED_DIR, id);
              const intact = [...SERVED_FILES].every((f) => sha256(path.join(dir, f)) === a.locked?.[f]);
              if (!intact) continue;
              const manifest = JSON.parse(fs.readFileSync(path.join(dir, 'manifest.json'), 'utf8'));
              if (manifest.category !== 'A' && !(id === 'me' && manifest.category === 'O')) continue;
              entries.push({ id, name: manifest.displayName ?? id, agent: manifest.agent ?? id, style: manifest.style ?? '',
                weighIn: a.weighIn });
            }
            return json(res, entries);
          }
          if (url.pathname === '/api/weighins' && req.method === 'GET') {
            return json(res, fs.existsSync(WEIGHINS_FILE) ? JSON.parse(fs.readFileSync(WEIGHINS_FILE, 'utf8')) : []);
          }
          const fileMatch = url.pathname.match(/^\/entries\/([a-z0-9_-]+)\/([a-z._]+)$/i);
          if (fileMatch && req.method === 'GET') {
            const [, id, file] = fileMatch;
            const full = path.join(APPROVED_DIR, id, file);
            if (!SERVED_FILES.has(file) || id.startsWith('_') || !fs.existsSync(full)) return json(res, { error: 'not found' }, 404);
            res.setHeader('Content-Type', file.endsWith('.glb') ? 'model/gltf-binary' : file.endsWith('.js') ? 'text/plain' : 'application/json');
            return fs.createReadStream(full).pipe(res);
          }
          if (url.pathname === '/api/tournament') {
            if (req.method === 'GET') {
              return json(res, fs.existsSync(STATE_FILE) ? JSON.parse(fs.readFileSync(STATE_FILE, 'utf8')) : null);
            }
            if (req.method === 'POST') {
              const body = JSON.parse(await readBody(req));
              fs.writeFileSync(STATE_FILE, JSON.stringify(body, null, 2));
              return json(res, { ok: true });
            }
          }
          if (url.pathname === '/api/dojo' && req.method === 'GET') {
            return json(res, await currentDojo());
          }
          if (url.pathname === '/api/dojos' && req.method === 'GET') {
            return json(res, await allDojos());
          }
          // Judging harness (judge.html): read any entry's current fighter.glb, and save standardised renders.
          const judgeFile = url.pathname.match(/^\/judge-file\/([a-z0-9_-]+)\/fighter\.glb$/);
          if (judgeFile && req.method === 'GET') {
            const full = path.join(ENTRIES, judgeFile[1], 'fighter.glb');
            if (!fs.existsSync(full)) return json(res, { error: 'not found' }, 404);
            res.setHeader('Content-Type', 'model/gltf-binary');
            return fs.createReadStream(full).pipe(res);
          }
          if (url.pathname === '/api/judge-render' && req.method === 'POST') {
            const id = url.searchParams.get('id') ?? '';
            const view = url.searchParams.get('view') ?? '';
            if (!/^[a-z0-9_-]+$/.test(id) || !/^[a-z_]+$/.test(view)) return json(res, { error: 'bad id or view' }, 400);
            const chunks = [];
            for await (const c of req) chunks.push(c);
            const dir = path.join(COMPETITION, 'judging', id);
            fs.mkdirSync(dir, { recursive: true });
            fs.writeFileSync(path.join(dir, `${view}.png`), Buffer.concat(chunks));
            return json(res, { ok: true });
          }
          // Owner override (RULES.md §8): competition/start_now.json starts the next tournament without waiting
          // for every fighter to update. The arena deletes the file when it uses it.
          if (url.pathname === '/api/start-now') {
            if (req.method === 'GET') return json(res, fs.existsSync(START_NOW_FILE) ? JSON.parse(fs.readFileSync(START_NOW_FILE, 'utf8')) : null);
            if (req.method === 'DELETE') { fs.rmSync(START_NOW_FILE, { force: true }); return json(res, { ok: true }); }
            if (req.method === 'POST') {
              const b = JSON.parse((await readBody(req)) || '{}');
              const value = { by: 'owner', at: new Date().toISOString(), via: 'owner controls', note: String(b.note ?? '').slice(0, 200) };
              fs.writeFileSync(START_NOW_FILE, `${JSON.stringify(value, null, 2)}\n`);
              return json(res, value);
            }
          }
          // The broadcast page checks in every 20 s, so the owner controls can tell whether a broadcast is running.
          if (url.pathname === '/api/heartbeat' && req.method === 'GET') {
            broadcastSeen = Date.now();
            return json(res, { ok: true });
          }
          if (url.pathname === '/api/broadcast' && req.method === 'GET') {
            return json(res, { secondsAgo: broadcastSeen ? Math.round((Date.now() - broadcastSeen) / 1000) : null });
          }
          if (url.pathname === '/api/scores' && req.method === 'GET') {
            return json(res, fs.existsSync(SCORES_FILE) ? JSON.parse(fs.readFileSync(SCORES_FILE, 'utf8')) : null);
          }
          const dojoFile = url.pathname.match(/^\/dojos\/(season-\d+-[a-z0-9_-]+)\/([A-Za-z0-9._-]+)$/);
          if (dojoFile && req.method === 'GET') {
            const [, folder, file] = dojoFile;
            const dir = path.join(DOJOS, folder);
            let allowed = [];
            try {
              const m = JSON.parse(fs.readFileSync(path.join(dir, 'manifest.json'), 'utf8'));
              allowed = [m.dojo, m.environment].filter(Boolean);
            } catch { /* no manifest: nothing is served */ }
            if (!allowed.includes(file) || !(await validDojo(folder))) return json(res, { error: 'not found' }, 404);
            res.setHeader('Content-Type', file.endsWith('.glb') ? 'model/gltf-binary' : 'application/octet-stream');
            return fs.createReadStream(path.join(dir, file)).pipe(res);
          }
          if (url.pathname === '/api/season-end' && req.method === 'POST') {
            const b = JSON.parse(await readBody(req));
            const season = Number(b.season);
            const builderId = String(b.builder?.id ?? '');
            if (!Number.isInteger(season) || season < 1) return json(res, { error: 'bad season' }, 400);
            const champions = fs.existsSync(CHAMPIONS_FILE) ? JSON.parse(fs.readFileSync(CHAMPIONS_FILE, 'utf8')) : [];
            if (!champions.some((c) => c.league === b.league && c.season === season)) {
              champions.push({ at: new Date().toISOString(), league: b.league, season, champion: b.champion,
                builder: BUILDERS.has(builderId) ? b.builder : null, record: b.record });
              fs.writeFileSync(CHAMPIONS_FILE, JSON.stringify(champions, null, 2));
            }
            // One open commission per builder: no new one until that builder has delivered a dojo folder for it.
            const openCommission = fs.existsSync(DOJOS) && fs.readdirSync(DOJOS).some((f) => {
              const m = f.match(/^COMMISSION-season-(\d+)\.md$/);
              if (!m) return false;
              const text = fs.readFileSync(path.join(DOJOS, f), 'utf8');
              return text.includes(`competitor id \`${builderId}\``) && !fs.existsSync(path.join(DOJOS, `season-${m[1]}-${builderId}`));
            });
            if (BUILDERS.has(builderId) && !openCommission) {
              fs.mkdirSync(DOJOS, { recursive: true });
              const next = season + 1;
              const text = fs.readFileSync(COMMISSION_TEMPLATE, 'utf8')
                .replaceAll('{{SEASON}}', String(season))
                .replaceAll('{{SEASON_NEXT}}', String(next))
                .replaceAll('{{BUILDER_ID}}', builderId)
                .replaceAll('{{BUILDER_NAME}}', String(b.builder.name).replace(/[^\w .-]/g, ''))
                .replaceAll('{{REASON}}', String(b.reason ?? '').slice(0, 600))
                .replaceAll('{{STANDINGS}}', String(b.standings ?? '').slice(0, 4000));
              fs.writeFileSync(path.join(DOJOS, `COMMISSION-season-${next}.md`), text);
            }
            writeCalls(season, b.champion?.id ?? null);
            spawnDetached('bell.mjs');
            return json(res, { ok: true });
          }
          if (url.pathname === '/api/ring-bell' && req.method === 'POST') {
            // Ring by hand (e.g. the first call): uses the last recorded tournament and champion.
            const champs = fs.existsSync(CHAMPIONS_FILE) ? JSON.parse(fs.readFileSync(CHAMPIONS_FILE, 'utf8')) : [];
            const last = champs.at(-1);
            writeCalls(last?.season ?? 0, last?.champion?.id ?? null);
            spawnDetached('bell.mjs');
            return json(res, JSON.parse(fs.readFileSync(path.join(COMPETITION, 'calls', 'current.json'), 'utf8')));
          }
          // The Weigh-In announcer's lines and recordings (competition/announce.mjs).
          const line = url.pathname.match(/^\/announcements\/(intro|\d+)\.(json|m4a)$/);
          if (line && req.method === 'GET') {
            const f = path.join(COMPETITION, 'announcements', `${line[1]}.${line[2]}`);
            if (!fs.existsSync(f)) return json(res, { error: 'not found' }, 404);
            res.setHeader('Content-Type', line[2] === 'm4a' ? 'audio/mp4' : 'application/json');
            return fs.createReadStream(f).pipe(res);
          }
          // Owner's bench (RULES.md §8): { "<id>": { "tournaments": [7] } } keeps a fighter out of those tournaments.
          if (url.pathname === '/api/bench' && req.method === 'GET') {
            const f = path.join(COMPETITION, 'bench.json');
            return json(res, fs.existsSync(f) ? JSON.parse(fs.readFileSync(f, 'utf8')) : {});
          }
          // Owner controls: { tournament, benched: [ids] } sets who sits out that tournament.
          if (url.pathname === '/api/bench' && req.method === 'POST') {
            const f = path.join(COMPETITION, 'bench.json');
            const bench = fs.existsSync(f) ? JSON.parse(fs.readFileSync(f, 'utf8')) : {};
            const b = JSON.parse(await readBody(req));
            const no = Number(b.tournament);
            const out = new Set((b.benched ?? []).map(String).filter((id) => /^[a-z0-9_-]+$/.test(id)));
            for (const id of new Set([...Object.keys(bench), ...out])) {
              const row = bench[id] ?? { tournaments: [], by: 'owner' };
              row.tournaments = row.tournaments.filter((t) => t !== no);
              if (out.has(id)) { row.tournaments.push(no); row.reason = 'Benched with the owner controls.'; }
              if (row.tournaments.length) bench[id] = row; else delete bench[id];
            }
            fs.writeFileSync(f, `${JSON.stringify(bench, null, 2)}\n`);
            return json(res, bench);
          }
          if (url.pathname === '/api/call' && req.method === 'GET') {
            const f = path.join(COMPETITION, 'calls', 'current.json');
            return json(res, fs.existsSync(f) ? JSON.parse(fs.readFileSync(f, 'utf8')) : null);
          }
          if (url.pathname === '/api/result' && req.method === 'POST') {
            const body = JSON.parse(await readBody(req));
            fs.appendFileSync(RESULTS_FILE, `${JSON.stringify(body)}\n`);
            return json(res, { ok: true });
          }
        } catch (err) {
          return json(res, { error: err.message }, 500);
        }
        next();
      });
    },
  };
}

export default defineConfig({
  plugins: [arenaApi()],
});
