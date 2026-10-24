// Single-elimination tournaments. At most SCHEDULE.maxConcurrentFights bouts run at once (default 1: one after another in one dojo).
// Fights are the show; the champion is the most realistic fighter by the judge's scores
// (competition/scores.json, RULES.md §6), and the champion earns the right to build the next dojo (§9).
import { DOJO_BUILDERS, ENTRY_COLORS, EQUAL_STATS, PERSONALITIES, ROSTER, SCHEDULE } from './config.js';
const MAX_FIGHTS = Math.max(1, SCHEDULE.maxConcurrentFights ?? 1);
import { CpuBrain, EntryBrain } from './brains.js';
import { DOJO_PRESETS, championPreset } from './dojos.js';

// ?watch: a spectator copy (say, on a phone) that runs its own fights but never writes results or state.
export const WATCH = new URLSearchParams(location.search).has('watch');
const post = (url, value) => WATCH ? Promise.resolve() : fetch(url, {
  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(value),
}).catch(() => {});
const brainFor = (def) => (def.brainSrc ? new EntryBrain(def.brainSrc) : new CpuBrain(PERSONALITIES[def.id] ?? PERSONALITIES.default));
const shuffle = (xs) => xs.map((x) => [Math.random(), x]).sort((p, q) => p[0] - q[0]).map((p) => p[1]);

export class Tournament {
  constructor(arenas, ui) {
    this.arenas = arenas;
    this.ui = ui;
    this.listeners = [];
  }

  async init() {
    const entries = await fetch('/api/entries').then((r) => r.json()).catch(() => []);
    if (entries.length >= 2) {
      this.league = 'Dojo Invitational';
      this.defs = await Promise.all(entries.map(async (e, i) => ({
        id: `entry:${e.id}`, name: e.name, tag: e.agent, style: e.style, color: ENTRY_COLORS[i % ENTRY_COLORS.length],
        tint: 0, url: `/entries/${e.id}/fighter.glb`, stats: EQUAL_STATS,
        brainSrc: await fetch(`/entries/${e.id}/brain.js`).then((r) => r.text()),
      })));
    } else {
      this.league = 'Exhibition League';
      this.defs = ROSTER.map((d) => ({ ...d, stats: EQUAL_STATS }));
    }
    this.byId = Object.fromEntries(this.defs.map((d) => [d.id, d]));
    // Benched fighters still spar, but sit out the bracket, the update gate and the title.
    this.sparDefs = this.defs;
    // The league's history survives new entrants joining: the key is the league, and newcomers get a blank row.
    this.key = `bracket-v1|${this.league}`;
    const saved = await fetch('/api/tournament').then((r) => r.json()).catch(() => null);
    const sameLeague = saved && (saved.key === this.key || saved.key?.startsWith(`${this.key}|`));
    this.data = sameLeague ? saved.data : this.freshData();
    const blank = this.freshData().standings;
    for (const d of this.defs) this.data.standings[d.id] ??= blank[d.id];
    // Leagues saved before the update rule: count every weigh-in already introduced as "used".
    this.data.lastStartWeighIn ??= this.data.lastWeighIn ?? 0;
    const bench = await fetch('/api/bench').then((r) => r.json()).catch(() => ({}));
    const next = this.data.tournamentNo + 1;
    this.benched = this.defs.filter((d) => bench[d.id.replace(/^entry:/, '')]?.tournaments?.includes(next));
    this.defs = this.defs.filter((d) => !this.benched.includes(d));
    await this.refreshScores();
    await this.refreshDojos();
  }

  freshData() {
    const blank = () => ({ played: 0, w: 0, l: 0, rw: 0, rl: 0, kos: 0, dmg: 0, taken: 0, hits: 0, thrown: 0,
      blocks: 0, bestCombo: 0, streak: 0, bestStreak: 0, titles: 0, bracketWins: 0, moves: {} });
    return {
      startedAt: new Date().toISOString(), tournamentNo: 0, matchNo: 0,
      standings: Object.fromEntries(this.defs.map((d) => [d.id, blank()])),
      records: { fastestKO: null, biggestCombo: null, mostDamage: null, longestStreak: null, comeback: null },
      totals: { matches: 0, rounds: 0, kos: 0, timeouts: 0, hits: 0, thrown: 0, damage: 0, blocks: 0 },
      h2h: {}, moveTotals: {}, recent: [], champions: [],
    };
  }

  async refreshScores() {
    const file = await fetch('/api/scores').then((r) => r.json()).catch(() => null);
    this.scores = file?.scores ?? {};
    this.scoreMethod = file?.method ?? null;
  }

  async refreshDojos() {
    const champs = await fetch('/api/dojos').then((r) => r.json()).catch(() => []);
    this.dojos = [...champs.map(championPreset), ...DOJO_PRESETS];
  }

  name(id) { return this.byId[id]?.name ?? id; }
  realism(id) { return this.scores[id]?.total ?? null; }

  /** Seed by all-time win rate (realism score breaks ties), then pair 1v8, 4v5, 3v6, 2v7 with byes. */
  buildBracket() {
    const rate = (id) => { const s = this.data.standings[id]; return s.played ? s.w / s.played : 0.5; };
    const seeds = this.defs.map((d) => d.id)
      .map((id) => ({ id, k: rate(id) + (this.realism(id) ?? 0) / 1000 + Math.random() / 1e4 }))
      .sort((a, b) => b.k - a.k).map((s) => s.id);
    const size = 2 ** Math.ceil(Math.log2(Math.max(2, seeds.length)));
    const order = size === 8 ? [1, 8, 4, 5, 3, 6, 2, 7] : size === 4 ? [1, 4, 2, 3] : [1, 2];
    const slots = order.map((s) => seeds[s - 1] ?? null);
    const rounds = [];
    let current = [];
    for (let i = 0; i < slots.length; i += 2) current.push({ a: slots[i], b: slots[i + 1], winner: null, score: '' });
    rounds.push(current);
    while (current.length > 1) {
      current = Array.from({ length: current.length / 2 }, () => ({ a: null, b: null, winner: null, score: '' }));
      rounds.push(current);
    }
    this.seeds = seeds;
    return rounds;
  }

  roundName(i) {
    const left = this.bracket.length - i;
    return left === 1 ? 'Final' : left === 2 ? 'Semifinals' : left === 3 ? 'Quarterfinals' : `Round ${i + 1}`;
  }

  /**
   * RULES.md §8: in the Invitational a new tournament starts only when every fighter in the league has weighed in
   * an updated version (an approval that changed files) since the previous tournament started.
   */
  async readiness() {
    const cards = await fetch('/api/weighins').then((r) => r.json()).catch(() => []);
    const mark = this.data.lastStartWeighIn ?? 0;
    const fighters = this.defs.map((d) => {
      const update = cards.filter((c) => `entry:${c.id}` === d.id && c.no > mark && c.decision === 'approved'
        && (c.fighterChanged || c.changedFiles?.length)).pop();
      return { id: d.id, name: d.name, updated: !!update, weighIn: update?.no ?? null };
    });
    const gated = this.league === 'Dojo Invitational';
    const override = await fetch('/api/start-now').then((r) => r.json()).catch(() => null);
    // No deadlocks: 6 hours after the call for updates, the tournament starts with whoever is ready.
    const call = await fetch('/api/call').then((r) => r.json()).catch(() => null);
    const timedOut = !!call && Date.now() - Date.parse(call.at) > 6 * 3600 * 1000;
    // Never a tournament of one: with fewer than two fighters (after the bench), keep waiting.
    const enough = this.defs.length >= 2;
    return { ready: enough && (!gated || fighters.every((f) => f.updated) || !!override || timedOut), enough, gated, fighters, override,
      timedOut, latest: cards.at(-1)?.no ?? 0 };
  }

  async start() {
    await this.init();
    const r = await this.readiness();
    if (!r.ready) {
      this.waiting = r;
      // Keep the dojos busy with sparring while waiting.
      this.arenas.forEach((a) => { if (!a.sparring) a.clear(); });
      if (this.arenas.some((a) => !a.preset)) {
        await Promise.all(this.arenas.map((a, i) => a.setDojo(this.dojos[i % this.dojos.length])));
      }
      this.fillSparring();
      this.ui.waiting(r, this);
      clearTimeout(this.retry);
      this.retry = setTimeout(() => this.start(), 30000);
      return;
    }
    this.waiting = null;
    this.ui.waiting(null, this);
    if (r.timedOut && !r.override && !r.fighters.every((f) => f.updated)) {
      const late = r.fighters.filter((f) => !f.updated).map((f) => f.name).join(', ');
      this.ui.flash(`Six hours are up: starting without updates from ${late}`);
    }
    if (r.override) {
      if (!WATCH) await fetch('/api/start-now', { method: 'DELETE' }).catch(() => {});
const brainFor = (def) => (def.brainSrc ? new EntryBrain(def.brainSrc) : new CpuBrain(PERSONALITIES[def.id] ?? PERSONALITIES.default));
const shuffle = (xs) => xs.map((x) => [Math.random(), x]).sort((p, q) => p[0] - q[0]).map((p) => p[1]);
      const waitingOn = r.fighters.filter((f) => !f.updated).map((f) => f.name).join(', ');
      this.ui.flash(`Owner's call: starting now${waitingOn ? ` without updates from ${waitingOn}` : ''}`);
    }
    this.arenas.forEach((a) => { a.sparring = false; a.clear(); });
    this.data.lastStartWeighIn = r.latest;
    this.data.tournamentNo++;
    await this.refreshScores();
    await this.refreshDojos();
    this.bracket = this.buildBracket();
    this.roundIdx = 0;
    // Give every arena a different dojo; rotate each tournament so the dojos take turns hosting the main event.
    const offset = (this.data.tournamentNo - 1) % this.dojos.length;
    await Promise.all(this.arenas.map((a, i) => a.setDojo(this.dojos[(offset + i) % this.dojos.length])));
    this.emit();
    await this.weighInCeremony();
    await this.playRound();
  }

  /** Owner controls: re-check now instead of at the next 30-second check (only while waiting between tournaments). */
  startNow() {
    if (!this.waiting) return false;
    clearTimeout(this.retry);
    this.start();
    return true;
  }

  /** Introduce every entry approved or sent back since the last tournament (RULES.md §11). */
  async weighInCeremony() {
    const cards = (await fetch('/api/weighins').then((r) => r.json()).catch(() => []))
      .filter((c) => c.no > (this.data.lastWeighIn ?? 0));
    if (!cards.length) return;
    const stage = this.arenas[0];
    stage.sparring = false;
    stage.clear();
    stage.reserved = true;
    this.fillSparring();
    this.ui.flash(`The Weigh-In · ${cards.length} ${cards.length === 1 ? 'entry' : 'entries'} before tournament ${this.data.tournamentNo}`);
    // The ring announcer's recorded lines (competition/announce.mjs), where they exist.
    const line = (name) => fetch(`/announcements/${name}.json`).then((r) => (r.ok ? r.json() : null)).catch(() => null);
    const intro = await line('intro');
    if (intro) await this.ui.announce(intro, `THE WEIGH-IN · TOURNAMENT ${this.data.tournamentNo}`);
    for (const card of cards) {
      const def = this.byId[`entry:${card.id}`];
      if (def && card.decision === 'approved') await stage.startShowcase(def).catch(() => stage.clear());
      else stage.clear();
      const said = await line(card.no);
      this.ui.weighIn(card, def, said);
      await (said ? this.ui.speak(said) : new Promise((r) => setTimeout(r, 7500)));
      this.data.lastWeighIn = card.no;
    }
    this.ui.weighIn(null);
    stage.reserved = false;
    stage.clear();
    this.save();
  }

  async playRound() {
    const round = this.bracket[this.roundIdx];
    // Byes advance straight away.
    for (const m of round) {
      if (m.a && !m.b) { m.winner = m.a; m.score = 'bye'; }
      if (m.b && !m.a) { m.winner = m.b; m.score = 'bye'; }
    }
    const live = round.filter((m) => m.a && m.b && !m.winner);
    this.arenas.forEach((a) => { a.clear(); a.match = null; a.sparring = false; });
    this.ui.flash(`${this.roundName(this.roundIdx)} · Tournament ${this.data.tournamentNo}`);
    const startBout = async (arena, m) => {
      arena.match = m;
      arena.comebackLow = [100, 100];
      arena.onRoundEnd = (ar, winner, timeUp) => this.onRoundEnd(ar, winner, timeUp);
      arena.onMatchEnd = (ar, winner) => this.onMatchEnd(ar, winner);
      const da = this.byId[m.a];
      const db = this.byId[m.b];
      await arena.startMatch(da, db, [brainFor(da), brainFor(db)]);
    };
    this.startBout = startBout;
    // Up to MAX_FIGHTS bouts at once; the rest wait in a queue and take over the first arena that frees up.
    this.queue = live.slice(Math.min(MAX_FIGHTS, this.arenas.length));
    const starting = Promise.all(live.slice(0, Math.min(MAX_FIGHTS, this.arenas.length)).map((m, i) => startBout(this.arenas[i], m)));
    // Dojos without a bout this round host sparring between the fighters who aren't fighting.
    this.fillSparring();
    await starting;
    this.data.matchNo += live.length;
    this.emit();
    if (!live.length) this.afterRound();
  }

  /**
   * Sparring (RULES.md §8): a friendly in every dojo with no tournament bout, between fighters who aren't in one,
   * topped up with house fighters. It never counts toward standings, records, seeding or titles.
   */
  fillSparring() {
    // One-fight-at-a-time cap: tournament bouts, the weigh-in stage and sparring all count toward MAX_FIGHTS,
    // and no sparring starts while bracket bouts are still queued.
    if (this.queue?.length) return;
    let fights = this.arenas.filter((a) => a.lineup.length || a.reserved).length;
    const busy = new Set(this.arenas.flatMap((a) => a.lineup));
    // The house "You" is the same person as the owner's entry, so it stays out once entry:me is in.
    const house = ROSTER.filter((d) => !(d.id === 'me' && this.byId['entry:me'])).map((d) => ({ ...d, stats: EQUAL_STATS }));
    const pool = [...shuffle(this.sparDefs), ...shuffle(house)]
      .filter((d, i, all) => !busy.has(d.id) && all.findIndex((x) => x.id === d.id) === i);
    for (const arena of this.arenas) {
      if (arena.lineup.length || arena.reserved || pool.length < 2) continue;
      if (fights >= MAX_FIGHTS) break;
      fights++;
      this.spar(arena, pool.shift(), pool.shift());
    }
  }

  spar(arena, a, b) {
    const gen = (arena.sparGen ?? 0) + 1;
    Object.assign(arena, { sparGen: gen, sparring: true, match: null, comebackLow: null, onRoundEnd: null });
    arena.onMatchEnd = (ar, winner) => this.onSparEnd(ar, winner, gen);
    arena.startMatch(a, b, [brainFor(a), brainFor(b)]).catch(() => arena.clear());
  }

  onSparEnd(arena, winner, gen) {
    const s = (this.data.sparring ??= { matches: 0, kos: 0 });
    s.matches++;
    s.kos += arena.fighters.reduce((n, f) => n + f.tally.kos, 0);
    const loser = arena.fighters.find((f) => f !== winner);
    const wi = arena.fighters.indexOf(winner);
    s.last = { winner: winner.def.name, loser: loser.def.name, score: `${arena.wins[wi]}-${arena.wins[1 - wi]}` };
    this.save();
    // A short look at the result, then a fresh pairing.
    setTimeout(() => {
      if (arena.sparGen !== gen || !arena.sparring) return;
      arena.sparring = false;
      arena.clear();
      this.fillSparring();
    }, 4000);
  }

  tick() {
    for (const a of this.arenas) {
      if (!a.active || !a.comebackLow) continue;
      a.fighters.forEach((f, i) => { a.comebackLow[i] = Math.min(a.comebackLow[i], Math.round((f.hp / f.maxHp) * 100)); });
    }
  }

  onRoundEnd(arena, winner, timeUp) {
    const t = this.data.totals;
    t.rounds++;
    const lows = arena.comebackLow;
    arena.comebackLow = [100, 100];
    if (!winner) return;
    if (timeUp) { t.timeouts++; return; }
    t.kos++;
    const r = this.data.records;
    const elapsed = arena.timing.roundTime - arena.timeLeft;
    const loser = arena.fighters.find((f) => f !== winner);
    if (!r.fastestKO || elapsed < r.fastestKO.seconds) {
      r.fastestKO = { seconds: +elapsed.toFixed(1), who: winner.def.id, vs: loser.def.id };
      this.ui.flash(`NEW RECORD · Fastest KO ${elapsed.toFixed(1)}s · ${winner.def.name}`);
    }
    const low = lows[arena.fighters.indexOf(winner)];
    if (low <= 20 && (!r.comeback || low < r.comeback.hpPct)) {
      r.comeback = { hpPct: low, who: winner.def.id, vs: loser.def.id };
      this.ui.flash(`NEW RECORD · ${winner.def.name} comes back from ${low}% health`);
    }
  }

  onMatchEnd(arena, winner) {
    const d = this.data;
    const [f1, f2] = arena.fighters;
    const loser = winner === f1 ? f2 : f1;
    const wi = arena.fighters.indexOf(winner);
    const m = arena.match;
    m.winner = winner.def.id;
    m.score = `${arena.wins[wi]}-${arena.wins[1 - wi]}`;
    for (const f of [f1, f2]) {
      const s = d.standings[f.def.id];
      const opp = f === f1 ? f2 : f1;
      s.played++;
      s.rw += arena.wins[arena.fighters.indexOf(f)];
      s.rl += arena.wins[arena.fighters.indexOf(opp)];
      s.kos += f.tally.kos;
      s.dmg += f.tally.damage;
      s.taken += opp.tally.damage;
      s.hits += f.tally.hits;
      s.thrown += f.tally.thrown;
      s.blocks += f.tally.blocks;
      s.bestCombo = Math.max(s.bestCombo, f.tally.bestCombo);
      for (const [mv, n] of Object.entries(f.tally.moves)) {
        s.moves[mv] = (s.moves[mv] ?? 0) + n;
        d.moveTotals[mv] = (d.moveTotals[mv] ?? 0) + n;
      }
      d.totals.hits += f.tally.hits;
      d.totals.thrown += f.tally.thrown;
      d.totals.damage += f.tally.damage;
      d.totals.blocks += f.tally.blocks;
    }
    const ws = d.standings[winner.def.id];
    const ls = d.standings[loser.def.id];
    ws.w++;
    ls.l++;
    ws.streak++;
    ls.streak = 0;
    ws.bestStreak = Math.max(ws.bestStreak, ws.streak);
    d.totals.matches++;

    const r = d.records;
    const best = [f1, f2].reduce((a, b) => (b.tally.bestCombo > a.tally.bestCombo ? b : a));
    if (!r.biggestCombo || best.tally.bestCombo > r.biggestCombo.hits) r.biggestCombo = { hits: best.tally.bestCombo, who: best.def.id };
    const heavy = [f1, f2].reduce((a, b) => (b.tally.damage > a.tally.damage ? b : a));
    if (!r.mostDamage || heavy.tally.damage > r.mostDamage.damage) r.mostDamage = { damage: heavy.tally.damage, who: heavy.def.id };
    if (!r.longestStreak || ws.streak > r.longestStreak.streak) {
      r.longestStreak = { streak: ws.streak, who: winner.def.id };
      if (ws.streak >= 3) this.ui.flash(`${winner.def.name} has won ${ws.streak} matches in a row`);
    }
    const pair = [f1.def.id, f2.def.id].sort().join('|');
    d.h2h[pair] ??= {};
    d.h2h[pair][winner.def.id] = (d.h2h[pair][winner.def.id] ?? 0) + 1;

    const result = {
      at: new Date().toISOString(), league: this.league, tournament: d.tournamentNo, stage: this.roundName(this.roundIdx),
      left: f1.def.id, right: f2.def.id, winner: winner.def.id, score: m.score, rounds: arena.round,
      decidedBy: arena.decidedByTime ? 'time' : 'ko', dojo: arena.preset?.name,
      stats: Object.fromEntries([f1, f2].map((f) => [f.def.id, { ...f.tally, moves: { ...f.tally.moves } }])),
    };
    d.recent.unshift(result);
    d.recent = d.recent.slice(0, 12);
    post('/api/result', result);
    this.save();
    this.emit();
    const round = this.bracket[this.roundIdx];
    if (round.every((x) => x.winner || !(x.a && x.b))) {
      setTimeout(() => this.afterRound(), 3500);
    } else if (this.queue?.length) {
      // Next queued bout of this round, in the same dojo, after a short look at the result.
      const next = this.queue.shift();
      setTimeout(() => { arena.clear(); this.startBout(arena, next).then(() => this.emit()); }, 3500);
    }
  }

  afterRound() {
    const round = this.bracket[this.roundIdx];
    if (this.roundIdx === this.bracket.length - 1) {
      this.finishTournament(round[0].winner);
      return;
    }
    const next = this.bracket[this.roundIdx + 1];
    round.forEach((m, i) => {
      const slot = next[Math.floor(i / 2)];
      if (i % 2 === 0) slot.a = m.winner; else slot.b = m.winner;
    });
    this.roundIdx++;
    this.playRound();
  }

  /** Crown the realism champion (not the bracket winner) and commission the next dojo. */
  async finishTournament(bracketWinner) {
    const d = this.data;
    d.standings[bracketWinner].bracketWins++;
    await this.refreshScores();
    const ranked = this.defs.map((def) => ({ id: def.id, score: this.realism(def.id) }))
      .filter((x) => x.score !== null).sort((a, b) => b.score - a.score);
    const baseId = (id) => id.replace(/^entry:/, '');
    const champion = ranked[0] ?? null;
    const builder = ranked.find((x) => DOJO_BUILDERS.includes(baseId(x.id))) ?? null;
    const entry = {
      tournament: d.tournamentNo, at: new Date().toISOString(), bracketWinner,
      champion: champion?.id ?? null, championScore: champion?.score ?? null, builder: builder?.id ?? null,
    };
    d.champions.unshift(entry);
    if (champion) d.standings[champion.id].titles++;

    const table = ['| # | Fighter | Realism score | Tournament result |', '|---|---|---|---|',
      ...ranked.map((x, i) => `| ${i + 1} | ${this.name(x.id)} | ${x.score} / 100 | ${x.id === bracketWinner ? 'won the bracket' : ''} |`)].join('\n');
    const reason = !builder ? '' : builder.id === champion.id
      ? `${this.name(champion.id)} is the most realistic fighter in tournament ${d.tournamentNo} of the ${this.league}, with a judge's realism score of ${champion.score}/100. (${this.name(bracketWinner)} won the bracket, but the title goes to realism, not wins.)`
      : `${this.name(champion.id)} scored highest for realism (${champion.score}/100) in tournament ${d.tournamentNo}, but isn't a competitor that builds dojos, so the commission goes to the most realistic competitor: you, at ${builder.score}/100.`;
    await post('/api/season-end', {
      league: this.league, season: d.tournamentNo, record: champion ? `${champion.score}/100 realism` : 'unscored',
      reason, standings: table,
      champion: champion ? { id: champion.id, name: this.name(champion.id) } : null,
      builder: builder ? { id: baseId(builder.id), name: this.name(builder.id) } : null,
    });
    this.save();
    this.emit();
    this.ui.champion(entry, this);
    setTimeout(() => this.start(), 9000);
  }

  save() {
    post('/api/tournament', { key: this.key, league: this.league, savedAt: new Date().toISOString(), data: this.data });
  }

  onChange(fn) { this.listeners.push(fn); }
  emit() { this.listeners.forEach((fn) => fn(this)); }
}
