// Dojo Fighters: play mode (one arena, keyboard) and tournament mode (?tournament: four arenas at once,
// the main event large and the other live fights alongside, single-elimination bracket).
import * as THREE from 'three';
import { KEYMAP, MOVE_LABELS, PERSONALITIES, ROSTER, ROUNDS_TO_WIN, TIMING } from './config.js';
import { Arena } from './arena.js';
import { CpuBrain } from './brains.js';
import { DOJO_PRESETS } from './dojos.js';
import { loadFighterAsset } from './assets.js';
import { Tournament, WATCH } from './tournament.js';

const TOURNAMENT_MODE = new URLSearchParams(location.search).has('tournament');

// ---------- Renderer ----------
const stage = document.getElementById('stage');
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, TOURNAMENT_MODE ? 1.5 : 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.setClearColor(0x0b0c0e);
stage.appendChild(renderer.domElement);
window.addEventListener('resize', () => renderer.setSize(window.innerWidth, window.innerHeight));

// ---------- Input ----------
const keys = new Set();
const humanInput = (i) => {
  const map = i === 0 ? KEYMAP.p1 : KEYMAP.p2;
  return { fwd: keys.has(map.fwd), back: keys.has(map.back), block: keys.has(map.block) };
};

// ---------- UI ----------
const $ = (id) => document.getElementById(id);
const ui = {
  loading: $('loading'), loadingText: $('loading-text'), select: $('select'), prompt: $('select-prompt'),
  roster: $('roster'), hud: $('hud'), banner: $('banner'), timer: $('timer'), round: $('round-label'),
  p2controls: $('p2-controls'),
  names: [$('p1-name'), $('p2-name')], fills: [$('p1-fill'), $('p2-fill')], pips: [$('p1-pips'), $('p2-pips')],
  tournament: $('tournament'), league: $('t-league'), stage: $('t-stage'), dojo: $('t-dojo'), tiles: $('t-tiles'),
  bracket: $('t-bracket'), board: $('t-board'), info: $('t-info'), infoTitle: $('t-info-title'),
  ticker: $('t-ticker'), flash: $('t-flash'),
};
const pct = (a, b) => (b ? Math.round((a / b) * 100) : 0);
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const topKey = (obj) => Object.entries(obj ?? {}).sort((a, b) => b[1] - a[1])[0]?.[0];

const pipsHtml = (w) => Array.from({ length: ROUNDS_TO_WIN }, (_, k) => `<span class="pip${k < w ? ' won' : ''}"></span>`).join('');

/** Update the big HUD (names, health, pips, timer, banner) from an arena. */
function updateHud(arena, nameSuffix = ['', '']) {
  if (!arena.active || arena.fighters.length < 2) return;
  arena.fighters.forEach((f, i) => {
    ui.names[i].textContent = f.def.name + nameSuffix[i];
    const p = (f.hp / f.maxHp) * 100;
    ui.fills[i].style.width = `${p}%`;
    ui.fills[i].style.background = p < 30 ? 'var(--hp-low)' : 'var(--hp)';
    const html = pipsHtml(arena.wins[i]);
    if (ui.pips[i].innerHTML !== html) ui.pips[i].innerHTML = html;
  });
  ui.timer.textContent = Math.ceil(arena.timeLeft);
  ui.round.textContent = arena.roundLabel;
  ui.banner.textContent = arena.banner.text;
  ui.banner.style.opacity = performance.now() < arena.banner.until ? 1 : 0;
}

function flash(text) {
  ui.flash.textContent = text;
  ui.flash.classList.remove('show');
  void ui.flash.offsetWidth;
  ui.flash.classList.add('show');
}

// ---------- Play mode ----------
let playArena = null;
let pick1 = null;
let pvp = false;

function buildRosterCards() {
  for (const def of ROSTER) {
    const card = document.createElement('button');
    card.className = 'card';
    card.style.setProperty('--accent', def.color);
    const s = def.stats;
    const bar = (label, v, lo, hi) =>
      `<div class="stat"><span>${label}</span><i style="width:${Math.round(((v - lo) / (hi - lo)) * 100)}%"></i></div>`;
    card.innerHTML = `<div class="swatch">${def.name[0]}</div><div class="cname">${def.name}</div>`
      + `<div class="ctag">${def.tag}</div><div class="cstyle">${def.style}</div>`
      + `<div class="stats">${bar('PWR', s.power, 0.7, 1.3)}${bar('SPD', s.speed, 0.7, 1.35)}`
      + `${bar('RCH', s.reach, 0.8, 1.2)}${bar('HP', s.hp, 70, 120)}</div>`;
    card.addEventListener('click', () => choose(def, card));
    ui.roster.appendChild(card);
  }
}

function choose(def, card) {
  pvp = document.querySelector('input[name=mode]:checked').value === 'pvp';
  if (!pick1) {
    pick1 = def;
    card.classList.add('p1');
    ui.prompt.textContent = pvp ? 'Player 2 — choose your fighter' : 'Choose your opponent';
    return;
  }
  startPlay(pick1, def);
}

async function startPlay(def1, def2) {
  ui.select.classList.add('hidden');
  ui.loading.classList.remove('hidden');
  ui.loadingText.textContent = `Loading ${def1.name} vs ${def2.name}…`;
  const brains = [null, pvp ? null : new CpuBrain()];
  await playArena.startMatch(def1, def2, brains);
  ui.p2controls.classList.toggle('hidden', !pvp);
  ui.loading.classList.add('hidden');
  ui.hud.classList.remove('hidden');
}

function backToSelect() {
  playArena.clear();
  pick1 = null;
  document.querySelectorAll('.card').forEach((c) => c.classList.remove('p1'));
  ui.prompt.textContent = 'Player 1 — choose your fighter';
  ui.hud.classList.add('hidden');
  ui.select.classList.remove('hidden');
}

window.addEventListener('keydown', (e) => {
  keys.add(e.code);
  if (TOURNAMENT_MODE || !playArena?.active) return;
  if (e.code === 'Escape') return backToSelect();
  if (e.code === 'KeyR') return playArena.newMatch();
  if (playArena.over) return;
  const [p1, p2] = playArena.fighters;
  if (KEYMAP.p1.moves[e.code]) p1.attack(KEYMAP.p1.moves[e.code]);
  if (e.code === KEYMAP.p1.taunt) p1.taunt();
  if (pvp) {
    if (KEYMAP.p2.moves[e.code]) p2.attack(KEYMAP.p2.moves[e.code]);
    if (e.code === KEYMAP.p2.taunt) p2.taunt();
  }
  if (e.code.startsWith('Arrow')) e.preventDefault();
});
window.addEventListener('keyup', (e) => keys.delete(e.code));

// ---------- Tournament mode ----------
let arenas = [];
let tournament = null;
let mainIdx = 0;
let overSince = null;
let uiWait = 0;
let infoPage = 0;
let infoFlip = 0;
const tileEls = [];

/** Screen rectangles: the main event, then the side tiles. */
function layout() {
  const W = window.innerWidth;
  const H = window.innerHeight;
  const mainW = Math.round(W * 0.7);
  const mainH = Math.round(H * 0.71);
  const tileH = Math.floor(H / 3);
  return {
    main: { x: 0, y: 0, w: mainW, h: mainH },
    tiles: [0, 1, 2].map((i) => ({ x: mainW, y: i * tileH, w: W - mainW, h: i === 2 ? H - 2 * tileH : tileH })),
  };
}

const liveNow = (a) => a.active && !a.matchOver;

/** What the main screen should show: the weigh-in stage, then tournament bouts, then sparring. */
const rank = (a) => (a.showcase ? 3 : !liveNow(a) ? 0 : a.sparring ? 1 : 2);

/** Keep the main event on the best live fight: cut away when it ends, or when a tournament bout starts. */
function pickMain(dt) {
  const main = arenas[mainIdx];
  // Hold a finished tournament bout on screen; leave it only for another tournament bout or the weigh-in.
  const holding = main.active && main.matchOver && !main.sparring;
  if (main.active && main.matchOver) {
    overSince = (overSince ?? 0) + dt;
    if (overSince < 2.5) return;
  } else overSince = null;
  const best = arenas.reduce((b, a, i) => (rank(a) > rank(arenas[b]) ? i : b), mainIdx);
  if (best === mainIdx || rank(arenas[best]) === 0 || (holding && rank(arenas[best]) < 2)) return;
  mainIdx = best;
  overSince = null;
  const next = arenas[best];
  if (!next.showcase) flash(`${next.sparring ? 'Sparring' : 'Cut to'} · ${next.fighters.map((f) => f.def.name).join(' vs ')}`);
}

function tileOrder() {
  return arenas.map((_, i) => i).filter((i) => i !== mainIdx).slice(0, 3);
}

function renderTiles() {
  const order = tileOrder();
  const rects = layout().tiles;
  order.forEach((ai, slot) => {
    const a = arenas[ai];
    const el = tileEls[slot];
    const r = rects[slot];
    el.style.top = `${r.y}px`;
    el.style.height = `${r.h}px`;
    const dojo = a.preset ? `${esc(a.preset.name)}${a.preset.champion ? ` · by ${esc(a.preset.author)}` : ''}` : '';
    if (!a.active) {
      const why = a.showcase ? 'The weigh-in' : a.lineup.length ? 'Fighters warming up…' : 'No fight in this dojo right now';
      el.innerHTML = `<div class="tile-top"><span class="tile-dojo">${dojo}</span><span class="tile-status idle">Waiting</span></div>`
        + `<div class="tile-bars"><div class="tile-row"><span class="tn"></span><span class="mid">${why}</span><span class="tn r"></span></div></div>`;
      return;
    }
    const [f1, f2] = a.fighters;
    const status = a.matchOver ? `<span class="tile-status done">${esc(a.winner.def.name)} wins</span>`
      : a.sparring ? `<span class="tile-status spar">SPARRING · ${Math.ceil(a.timeLeft)}s</span>`
        : `<span class="tile-status">LIVE · ${Math.ceil(a.timeLeft)}s</span>`;
    const bar = (f, right) => `<div class="mini${right ? ' r' : ''}"><i style="width:${(f.hp / f.maxHp) * 100}%"></i></div>`;
    const showBanner = performance.now() < a.banner.until && !a.matchOver;
    el.innerHTML = `<div class="tile-top"><span class="tile-dojo">${dojo}</span>${status}</div>`
      + (showBanner ? `<div class="tile-banner">${esc(a.banner.text)}</div>` : '')
      + `<div class="tile-bars"><div class="tile-row">`
      + `<div><span class="tn">${esc(f1.def.name)}</span>${bar(f1)}</div>`
      + `<span class="mid">${a.wins[0]} – ${a.wins[1]}<br>${esc(a.roundLabel)}</span>`
      + `<div><div class="tn r">${esc(f2.def.name)}</div>${bar(f2, true)}</div></div></div>`;
  });
}

function dot(id) {
  return `<i class="dot" style="background:${tournament.byId[id]?.color ?? '#888'}"></i>`;
}

function renderBracket(t) {
  if (!t.bracket) return;
  const liveIds = new Set(arenas.filter(liveNow).flatMap((a) => a.fighters.map((f) => f.def.id)));
  ui.bracket.innerHTML = t.bracket.map((round, ri) => `<div class="b-round"><h3>${t.roundName(ri)}</h3>`
    + round.map((m) => {
      const live = m.a && m.b && !m.winner && liveIds.has(m.a) && liveIds.has(m.b);
      const line = (id) => (id
        ? `<div class="b-line${m.winner === id ? ' win' : ''}"><span>${dot(id)}${esc(t.name(id))}</span><b>${m.winner === id ? esc(m.score) : ''}</b></div>`
        : `<div class="b-line"><span>${m.score === 'bye' ? '— bye —' : 'TBD'}</span></div>`);
      return `<div class="b-match${live ? ' live' : ''}">${line(m.a)}${line(m.b)}</div>`;
    }).join('') + '</div>').join('');
}

function renderBoard(t) {
  const live = new Set(arenas.filter(liveNow).flatMap((a) => a.fighters.map((f) => f.def.id)));
  const rows = t.defs.map((d) => ({ id: d.id, score: t.realism(d.id), ...t.data.standings[d.id] }))
    .sort((a, b) => (b.score ?? -1) - (a.score ?? -1));
  const method = t.scoreMethod === 'provisional' ? ' · provisional scores' : '';
  document.querySelector('#t-realism-panel h2 small').textContent = `judge's score decides the champion${method}`;
  ui.board.innerHTML = '<tr><th>#</th><th>Fighter</th><th>Realism</th><th>W-L</th><th>KOs</th><th>Titles</th></tr>'
    + rows.map((s, i) => `<tr class="${live.has(s.id) ? 'live' : ''}"><td>${i + 1}</td><td>${dot(s.id)}${esc(t.name(s.id))}</td>`
      + `<td class="score">${s.score ?? '—'}</td><td>${s.w}-${s.l}</td><td>${s.kos}</td><td>${s.titles || ''}</td></tr>`).join('');
}

function renderInfo(t) {
  const main = arenas[mainIdx];
  if (infoPage === 0 && main.active) {
    ui.infoTitle.textContent = 'Main event';
    const [f1, f2] = main.fighters;
    const a = f1.tally;
    const b = f2.tally;
    const line = (label, x, y) => `<tr><td>${x}</td><th>${label}</th><td>${y}</td></tr>`;
    const fav = (x) => MOVE_LABELS[topKey(x.moves)] ?? '—';
    const h = t.data.h2h[[f1.def.id, f2.def.id].sort().join('|')] ?? {};
    ui.info.innerHTML = '<table>'
      + `<tr><td>${dot(f1.def.id)}${esc(f1.def.name)}</td><th></th><td>${esc(f2.def.name)}${dot(f2.def.id)}</td></tr>`
      + line('Landed', `${a.hits}/${a.thrown}`, `${b.hits}/${b.thrown}`)
      + line('Accuracy', `${pct(a.hits, a.thrown)}%`, `${pct(b.hits, b.thrown)}%`)
      + line('Damage', a.damage, b.damage)
      + line('Blocks', a.blocks, b.blocks)
      + line('Best combo', a.bestCombo, b.bestCombo)
      + line('Favourite', fav(a), fav(b))
      + line('All-time H2H', h[f1.def.id] ?? 0, h[f2.def.id] ?? 0)
      + '</table>';
    return;
  }
  ui.infoTitle.textContent = 'League records';
  const d = t.data;
  const r = d.records;
  const rec = (label, value) => `<div class="rec"><span>${label}</span><b>${value}</b></div>`;
  const champ = d.champions[0];
  const fav = topKey(d.moveTotals);
  ui.info.innerHTML = [
    rec('Last realism champion', champ?.champion ? `${dot(champ.champion)}${esc(t.name(champ.champion))} · ${champ.championScore}/100` : '—'),
    rec('Last bracket winner', champ ? `${dot(champ.bracketWinner)}${esc(t.name(champ.bracketWinner))}` : '—'),
    rec('Fastest KO', r.fastestKO ? `${r.fastestKO.seconds}s · ${esc(t.name(r.fastestKO.who))}` : '—'),
    rec('Biggest combo', r.biggestCombo ? `${r.biggestCombo.hits} · ${esc(t.name(r.biggestCombo.who))}` : '—'),
    rec('Most damage, one match', r.mostDamage ? `${r.mostDamage.damage} · ${esc(t.name(r.mostDamage.who))}` : '—'),
    rec('Longest win streak', r.longestStreak ? `${r.longestStreak.streak} · ${esc(t.name(r.longestStreak.who))}` : '—'),
    rec('Greatest comeback', r.comeback ? `from ${r.comeback.hpPct}% · ${esc(t.name(r.comeback.who))}` : '—'),
    rec('Most thrown move', fav ? `${MOVE_LABELS[fav] ?? fav} (${d.moveTotals[fav]})` : '—'),
    rec('Matches · KOs · accuracy', `${d.totals.matches} · ${d.totals.kos} · ${pct(d.totals.hits, d.totals.thrown)}%`),
    rec('Sparring (doesn\'t count)', d.sparring ? `${d.sparring.matches} matches · last: ${esc(d.sparring.last.winner)} def. ${esc(d.sparring.last.loser)} ${d.sparring.last.score}` : '—'),
  ].join('');
}

function renderHeader(t) {
  const main = arenas[mainIdx];
  ui.league.textContent = t.league;
  const stage = t.bracket ? t.roundName(t.roundIdx) : '';
  const what = main.sparring ? 'Sparring · doesn\'t count' : 'Main event';
  ui.stage.textContent = t.waiting ? `Between tournaments · ${main.sparring ? 'Sparring · doesn\'t count' : 'Waiting for updates'}`
    : `Tournament ${t.data.tournamentNo} · ${stage} · ${what}`;
  ui.dojo.textContent = main.preset ? `${main.preset.name}${main.preset.champion ? ` · built by ${main.preset.author}` : ''}` : '';
  ui.ticker.innerHTML = t.data.recent.slice(0, 7).map((m) => {
    const loser = m.winner === m.left ? m.right : m.left;
    return `<span>${dot(m.winner)}<b>${esc(t.name(m.winner))}</b> def. ${esc(t.name(loser))} ${m.score}${m.decidedBy === 'time' ? ' (time)' : ''} · ${esc(m.stage)}</span>`;
  }).join('') || '<span>Tournament under way…</span>';
}

function renderBroadcast(t) {
  renderBracket(t);
  renderBoard(t);
  renderInfo(t);
  renderHeader(t);
}

/** The Weigh-In card: tale of the tape, what changed, realism score and the judge's verdict. */
function showWeighIn(card) {
  const el = $('t-weighin');
  document.body.classList.toggle('weighin', !!card);
  if (!card) { el.classList.add('hidden'); ui.hud.classList.remove('hidden'); return; }
  ui.hud.classList.add('hidden');
  const t = card.tape ?? {};
  const delta = card.realismBefore !== null && card.realism !== null && card.realism !== card.realismBefore
    ? ` <em>(${card.realism > card.realismBefore ? '+' : ''}${card.realism - card.realismBefore})</em>` : '';
  const row = (k, v) => `<div class="rec"><span>${k}</span><b>${v}</b></div>`;
  el.innerHTML = `<div class="w-head">THE WEIGH-IN · #${card.no}</div>`
    + `<div class="w-name">${esc(card.name)}</div><div class="w-agent">${esc(card.agent)} · branch ${esc(card.branch)} @ ${esc(card.branchCommit?.slice(0, 7))}</div>`
    + `<div class="w-stamp ${card.decision === 'approved' ? 'ok' : 'no'}">${card.decision === 'approved' ? 'APPROVED' : 'SENT BACK TO THE GYM'}</div>`
    + `<div class="w-style">${esc(card.style)}</div>`
    + '<div class="w-tape"><h3>Tale of the tape</h3>'
    + row('Realism score', card.realism !== null ? `${card.realism}/100${delta}` : 'not judged yet')
    + row('Height', t.heightM ? `${t.heightM} m` : '—')
    + row('Triangles', t.triangles ? t.triangles.toLocaleString() : '—')
    + row('Textures', t.textures ? `${t.textures} · up to ${t.largestTexture} px` : '—')
    + row('File', t.sizeMB ? `${t.sizeMB} MB` : '—')
    + row('This weigh-in', card.fighterChanged ? 'new fighter model' : 'brain / docs only')
    + `<div class="w-files">${(card.changedFiles ?? []).slice(0, 6).map(esc).join(' · ')}</div></div>`
    + `<blockquote>“${esc(card.verdict)}”<cite>— the Judge</cite></blockquote>`;
  el.classList.remove('hidden');
}

/** Between tournaments: who still has to weigh in an update before the next tournament can start. */
function showWaiting(r, t) {
  const el = $('t-waiting');
  document.body.classList.toggle('waiting', !!r);
  if (!r) { el.classList.add('hidden'); return; }
  const done = r.fighters.filter((f) => f.updated).length;
  el.innerHTML = `<div class="w-head">BETWEEN TOURNAMENTS · ${done} OF ${r.fighters.length} READY</div>`
    + `<p class="w-style">Tournament ${t.data.tournamentNo + 1} starts when every fighter has weighed in an improved version. `
    + `Sparring until then; it doesn't count.</p>`
    + r.fighters.map((f) => `<div class="rec"><span>${dot(f.id)}${esc(f.name)}</span>`
      + `<b class="${f.updated ? 'ok' : 'no'}">${f.updated ? `updated · weigh-in #${f.weighIn}` : 'waiting for a new version'}</b></div>`).join('')
    + `<p class="w-files">Agents write READY.json; the judge weighs them in automatically. Checking every 30 seconds.</p>`;
  el.classList.remove('hidden');
  renderBroadcast(t);
}

function announceChampion(entry, t) {
  const main = arenas[mainIdx];
  if (!entry.champion) {
    main.showBanner('NO REALISM SCORES YET', 6);
    flash(`${t.name(entry.bracketWinner)} won the bracket · the judge hasn't scored realism yet`);
    return;
  }
  main.showBanner(`${t.name(entry.champion).toUpperCase()} · REALISM CHAMPION`, 7);
  flash(entry.builder
    ? `${t.name(entry.builder)} earns the right to build the next dojo · ${t.name(entry.bracketWinner)} won the bracket`
    : `${t.name(entry.bracketWinner)} won the bracket`);
}

async function startTournament() {
  document.body.classList.add('tournament');
  ui.tournament.classList.remove('hidden');
  ui.hud.classList.remove('hidden');
  ui.loadingText.textContent = 'Setting up the arenas…';
  arenas = [0, 1, 2, 3].map((i) => new Arena({ timing: TIMING.tournament, shadowSize: i === 0 && !WATCH ? 2048 : 1024 }));
  for (let i = 0; i < 3; i++) {
    const el = document.createElement('div');
    el.className = 'tile';
    ui.tiles.appendChild(el);
    tileEls.push(el);
  }
  tournament = new Tournament(arenas, { flash, champion: announceChampion, weighIn: showWeighIn, waiting: showWaiting });
  if (import.meta.env.DEV) { window.__tournament = tournament; window.__arenas = arenas; }
  tournament.onChange(renderBroadcast);
  await tournament.init();
  ui.loading.classList.add('hidden');
  await tournament.start();
}

// ---------- Main loop ----------
const clock = new THREE.Clock();
function frame(dt) {
  if (TOURNAMENT_MODE) {
    if (!arenas.length) return;
    pickMain(dt);
    arenas.forEach((a, i) => { a.soundOn = i === mainIdx; a.update(dt); });
    tournament?.tick();
    const rects = layout();
    renderer.setScissorTest(false);
    renderer.clear();
    renderer.setScissorTest(true);
    arenas[mainIdx].render(renderer, rects.main);
    tileOrder().forEach((ai, slot) => arenas[ai].render(renderer, rects.tiles[slot]));
    updateHud(arenas[mainIdx]);
    uiWait -= dt;
    infoFlip += dt;
    if (infoFlip > 9) { infoFlip = 0; infoPage = 1 - infoPage; }
    if (uiWait <= 0 && tournament?.data) {
      uiWait = 0.25;
      renderTiles();
      renderInfo(tournament);
      renderHeader(tournament);
    }
    return;
  }
  if (!playArena) return;
  playArena.update(dt);
  renderer.setScissorTest(false);
  playArena.render(renderer, { x: 0, y: 0, w: window.innerWidth, h: window.innerHeight });
  if (playArena.active) updateHud(playArena, ['', pvp ? '' : ' (CPU)']);
}

function loop() {
  requestAnimationFrame(loop);
  frame(Math.min(clock.getDelta(), 1 / 20));
}

if (import.meta.env.DEV) {
  // Advance everything by hand (the browser throttles rendering in hidden tabs).
  window.__dojoStep = (seconds, fps = 30) => { for (let i = 0; i < seconds * fps; i++) frame(1 / fps); };
}

async function boot() {
  loop();
  if (TOURNAMENT_MODE) {
    await startTournament();
    return;
  }
  playArena = new Arena({ timing: TIMING.play, sound: true, humanInput });
  if (import.meta.env.DEV) window.__dojo = playArena;
  buildRosterCards();
  await playArena.setDojo(DOJO_PRESETS[0]);
  try {
    await loadFighterAsset('me');
  } catch (err) {
    ui.loadingText.textContent = `Could not load fighters: ${err.message}`;
    return;
  }
  ui.loading.classList.add('hidden');
  ui.select.classList.remove('hidden');
}
boot();
