#!/usr/bin/env node
// The Weigh-In announcer (RULES.md §10): a ring-announcer introduction for each weigh-in card, voiced by Kokoro neural
// text-to-speech running locally (competition/voice.py), with an arena echo from ffmpeg. Falls back to macOS `say`.
//
//   node competition/announce.mjs <card no>   announce one weigh-in (judge_pass.mjs runs this after every weigh-in)
//   node competition/announce.mjs --intro     record the ceremony's opening line
//   node competition/announce.mjs --redo      re-record every existing announcement (after changing the voice)
//
// The voice and speed are in competition/announcer.json.
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
const PYTHON = path.join(ROOT, 'assets', 'tts', '.venv', 'bin', 'python');
const ARENA = 'acompressor=threshold=-18dB:ratio=3:attack=5:release=120,aecho=0.85:0.6:70|140:0.22|0.12,loudnorm=I=-16:TP=-1.5';

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
  const { voice = 'am_michael', speed = 0.95 } = JSON.parse(fs.readFileSync(path.join(HERE, 'announcer.json'), 'utf8'));
  const txt = path.join(OUT, `${name}.txt`);
  const wav = path.join(OUT, `${name}.wav`);
  const m4a = path.join(OUT, `${name}.m4a`);
  fs.writeFileSync(txt, text);
  const tts = spawnSync(PYTHON, [path.join(HERE, 'voice.py'), voice, String(speed), txt, wav], { encoding: 'utf8' });
  if (tts.status !== 0) spawnSync('say', ['-v', 'Daniel (Enhanced)', '-r', '178', '--file-format=WAVE', '--data-format=LEI16@24000', '-o', wav, text]);
  spawnSync('ffmpeg', ['-loglevel', 'error', '-y', '-i', wav, '-af', ARENA, '-c:a', 'aac', '-b:a', '128k', m4a]);
  fs.rmSync(txt, { force: true });
  fs.rmSync(wav, { force: true });
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
  if (arg === '--redo') {
    // Same words, new voice: re-record the intro and every saved announcement.
    for (const f of fs.readdirSync(OUT).filter((x) => x.endsWith('.json'))) {
      const file = path.join(OUT, f);
      const a = JSON.parse(fs.readFileSync(file, 'utf8'));
      Object.assign(a, record(f.replace(/\.json$/, ''), a.text));
      fs.writeFileSync(file, `${JSON.stringify(a, null, 2)}\n`);
      console.log(f, a.seconds, 's');
    }
  } else if (arg === '--intro') {
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
