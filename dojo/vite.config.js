import { defineConfig } from 'vite';
import { execFile } from 'node:child_process';
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
const COMMISSION_TEMPLATE = path.join(COMPETITION, 'prompts', 'dojo_commission_template.md');
const BUILDERS = new Set(['gemini', 'grok', 'hermes', 'muse', 'aaron']);
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
function arenaApi() {
  return {
    name: 'dojo-arena-api',
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        const url = new URL(req.url, 'http://localhost');
        try {
          if (url.pathname === '/api/entries' && req.method === 'GET') {
            const ids = fs.existsSync(ENTRIES)
              ? fs.readdirSync(ENTRIES).filter((d) => !d.startsWith('_') && fs.existsSync(path.join(ENTRIES, d, 'manifest.json')))
              : [];
            const entries = [];
            for (const id of ids) {
              if (!fs.existsSync(path.join(ENTRIES, id, 'fighter.glb'))) continue;
              if (!(await validate(id))) continue;
              const manifest = JSON.parse(fs.readFileSync(path.join(ENTRIES, id, 'manifest.json'), 'utf8'));
              if (manifest.category !== 'A') continue;
              entries.push({ id, name: manifest.displayName ?? id, agent: manifest.agent ?? id, style: manifest.style ?? '' });
            }
            return json(res, entries);
          }
          const fileMatch = url.pathname.match(/^\/entries\/([a-z0-9_-]+)\/([a-z._]+)$/i);
          if (fileMatch && req.method === 'GET') {
            const [, id, file] = fileMatch;
            const full = path.join(ENTRIES, id, file);
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
            if (BUILDERS.has(builderId)) {
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
            return json(res, { ok: true });
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
