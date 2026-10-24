#!/usr/bin/env node
// The Weigh-In announcer (RULES.md §10): a ring-announcer introduction for each weigh-in card, voiced with macOS `say`.
//
//   node competition/announce.mjs <card no>   announce one weigh-in (judge_pass.mjs runs this after every weigh-in)
//   node competition/announce.mjs --intro     record the ceremony's opening line
//
// Writes competition/announcements/<no>.json ({ no, id, text, audio, seconds }) and <no>.m4a. The arena plays them
// at the weigh-in before each tournament, with the text as subtitles.

import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { cleanEnv } from './bell.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');
const OUT = path.join(HERE, 'announcements');
const VOICE = 'Daniel (Enhanced)';
const RATE = '178';

const INTRO = 'Ladies and gentlemen, boys and girls, bots of every model and parameter count! '
  + 'Welcome, to the weigh-in! Tonight, every fighter steps on the scale, and the judge tells you exactly how real they look. '
  + 'No hype. No filters. Just polygons, and the truth. Let us meet the fighters!';

function writeLine(card) {
  const facts = {
    name: card.name, agent: card.agent, decision: card.decision, style: card.style,
    realismScore: card.realism, realismBefore: card.realismBefore, judgeVerdict: card.verdict,
    newFighterModel: card.fighterChanged, changedFiles: card.changedFiles, taleOfTheTape: card.tape,
    selfSubmitted: card.id === 'claude',
  };
  const prompt = `You are the ring announcer at "The Dojo Invitational", a tournament where AI agents build hyper-realistic 3D
fighters. The champion is the most realistic fighter, not the one who wins most. Write the spoken introduction for this
weigh-in card, in the voice of a big, booming boxing announcer: fun, theatrical, a playful nickname, a little gentle
roasting, real warmth.

Rules:
- 60 to 90 words. Plain spoken English only: no emoji, markdown, stage directions or quotation marks.
- Every fact must come from the card below. Never invent numbers, wins or features.
- Say what improved (or what went wrong) and the realism score versus last time, if both exist.
- If decision is "sent back", the fighter didn't make weight: tease them and say what to fix.
- If selfSubmitted is true, this is the announcer's own entry: be self-deprecating, and say its realism is scored
  by the owner, not the judge.
- End by introducing the fighter by name, like a title fight.

Card:
${JSON.stringify(facts, null, 2)}

Reply with the introduction text only.`;
  const r = spawnSync('claude', ['-p', prompt], { cwd: ROOT, encoding: 'utf8', timeout: 5 * 60 * 1000, env: cleanEnv() });
  const text = (r.stdout ?? '').trim().replace(/\s+/g, ' ');
  if (r.status === 0 && text.length > 40) return text;
  // Fallback: a plain introduction from the card itself.
  const score = card.realism !== null ? ` Realism score: ${card.realism} out of 100.` : '';
  return card.decision === 'approved'
    ? `From ${card.agent}, stepping on the scale: ${card.name}!${score} The judge says: ${card.verdict}`
    : `${card.name}, from ${card.agent}, did not make weight tonight. The judge says: ${card.verdict}`;
}

function record(name, text) {
  fs.mkdirSync(OUT, { recursive: true });
  const aiff = path.join(OUT, `${name}.aiff`);
  const m4a = path.join(OUT, `${name}.m4a`);
  spawnSync('say', ['-v', VOICE, '-r', RATE, '-o', aiff, text]);
  spawnSync('afconvert', ['-f', 'm4af', '-d', 'aac', aiff, m4a]);
  fs.rmSync(aiff, { force: true });
  const info = spawnSync('afinfo', [m4a], { encoding: 'utf8' }).stdout ?? '';
  const seconds = Number(info.match(/estimated duration: ([\d.]+)/)?.[1] ?? 0);
  return { audio: `${name}.m4a`, seconds: +seconds.toFixed(1) };
}

export function announce(no) {
  const cards = JSON.parse(fs.readFileSync(path.join(HERE, 'weighins.json'), 'utf8'));
  const card = cards.find((c) => c.no === Number(no));
  if (!card) throw new Error(`no weigh-in card #${no}`);
  const text = writeLine(card);
  const result = { no: card.no, id: card.id, text, ...record(String(card.no), text) };
  fs.writeFileSync(path.join(OUT, `${card.no}.json`), `${JSON.stringify(result, null, 2)}\n`);
  return result;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const arg = process.argv[2];
  if (arg === '--intro') {
    const result = { text: INTRO, ...record('intro', INTRO) };
    fs.writeFileSync(path.join(OUT, 'intro.json'), `${JSON.stringify(result, null, 2)}\n`);
    console.log(result);
  } else if (arg) {
    console.log(announce(arg));
  } else {
    console.error('usage: node competition/announce.mjs <card no> | --intro');
    process.exit(1);
  }
}
