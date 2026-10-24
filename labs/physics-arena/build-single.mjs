// Builds demo.html: a fully self-contained version of the physics demo
// (three.js + Rapier bundled with esbuild, fighter GLB embedded as base64).
// No fetches at runtime — it can be hosted as one static file anywhere.
import { build } from 'esbuild';
import fs from 'node:fs';

const bundle = await build({
  entryPoints: ['src/main.js'],
  bundle: true,
  format: 'esm',
  write: false,
  logLevel: 'silent',
  alias: {
    three: './vendor/three.module.js',
    'three/addons': './vendor/addons',
    rapier: './vendor/rapier.es.js',
  },
});
let js = bundle.outputFiles[0].text.replaceAll('</script', '<\\/script');
const glbB64 = fs.readFileSync(process.argv[2] || 'fighter.glb').toString('base64');
const html = fs.readFileSync('index.html', 'utf8');
const body = html
  .replace(/<script type="importmap">[\s\S]*?<\/script>/, '')
  .replace('<script type="module" src="./src/main.js"></script>',
    `<script>window.__GLB_B64 = "${glbB64}";</script>\n<script type="module">\n${js}\n</script>`);
if (body === html) throw new Error('template replacement failed');
fs.writeFileSync('demo.html', body);
console.log('demo.html written:', (body.length / 1048576).toFixed(1), 'MB');
