// Phone controls for mobile.html: on-screen buttons that drive play mode exactly like the keyboard does.
// Movement and block are held keys (synthetic keydown/keyup on window, read by main.js); the strikes call the
// player's fighter directly through the dev-server hook (window.__dojo), so every move in MOVES has a button,
// and fall back to the keyboard map for the seven moves it has.
import { KEYMAP } from './config.js';

const touch = document.getElementById('touch');
const hud = document.getElementById('hud');
const KEY_FOR = Object.fromEntries(Object.entries(KEYMAP.p1.moves).map(([code, move]) => [move, code]));

const key = (type, code) => window.dispatchEvent(new KeyboardEvent(type, { code, bubbles: true }));

function strike(move) {
  const arena = window.__dojo;
  if (arena) {
    if (!arena.active || arena.over) return;
    const me = arena.fighters[0];
    if (move === 'taunt') me.taunt();
    else me.attack(move);
    return;
  }
  const code = move === 'taunt' ? KEYMAP.p1.taunt : KEY_FOR[move];
  if (code) { key('keydown', code); key('keyup', code); }
}

// Held buttons: pressed while any finger is on them, released when it lifts or slides off.
for (const el of touch.querySelectorAll('[data-hold]')) {
  const code = el.dataset.hold;
  const down = (e) => {
    e.preventDefault();
    el.classList.add('down');
    key('keydown', code);
    try { el.setPointerCapture(e.pointerId); } catch { /* not a live pointer */ }
  };
  const up = (e) => { e.preventDefault(); el.classList.remove('down'); key('keyup', code); };
  el.addEventListener('pointerdown', down);
  el.addEventListener('pointerup', up);
  el.addEventListener('pointercancel', up);
  el.addEventListener('lostpointercapture', up);
}

// Tapped buttons.
for (const el of touch.querySelectorAll('[data-move], [data-key]')) {
  el.addEventListener('pointerdown', (e) => {
    e.preventDefault();
    el.classList.add('down');
    if (el.dataset.move) strike(el.dataset.move);
    else { key('keydown', el.dataset.key); key('keyup', el.dataset.key); }
  });
  const up = () => el.classList.remove('down');
  el.addEventListener('pointerup', up);
  el.addEventListener('pointercancel', up);
}

// Move sets: punches, kicks, grappling and footwork.
for (const tab of touch.querySelectorAll('.tab')) {
  tab.addEventListener('pointerdown', (e) => {
    e.preventDefault();
    touch.querySelectorAll('.tab').forEach((t) => t.classList.toggle('on', t === tab));
    touch.querySelectorAll('.set').forEach((s) => s.classList.toggle('hidden', s.dataset.set !== tab.dataset.set));
  });
}

// Show the pad only while a match is on screen (main.js shows and hides the HUD).
const sync = () => touch.classList.toggle('hidden', hud.classList.contains('hidden'));
new MutationObserver(sync).observe(hud, { attributes: true, attributeFilter: ['class'] });
sync();

// No pinch-zoom, double-tap zoom or page bounce during a fight.
document.addEventListener('gesturestart', (e) => e.preventDefault());
document.addEventListener('dblclick', (e) => e.preventDefault());
document.addEventListener('touchmove', (e) => { if (e.target.closest('#touch, #stage')) e.preventDefault(); }, { passive: false });
