import puppeteer from 'puppeteer-core';
import fs from 'node:fs';

const [exe, url, outDir, viewsCsv] = process.argv.slice(2);
fs.mkdirSync(outDir, { recursive: true });
const t0 = Date.now();
const browser = await puppeteer.launch({
  executablePath: exe, headless: 'shell',
  args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader',
         '--window-size=1922,1922', '--force-device-scale-factor=1'],
});
const page = await browser.newPage();
await page.setViewport({ width: 1920, height: 1920 });
page.on('pageerror', e => console.log('[pageerror]', String(e).slice(0, 200)));
await page.goto(url, { waitUntil: 'load', timeout: 45000 });
await page.waitForFunction(
  () => { const t = document.getElementById('out')?.textContent || ''; return t.startsWith('READY') || t.startsWith('ERROR'); },
  { timeout: 90000, polling: 500 },
);
console.log('READY at', ((Date.now() - t0) / 1000).toFixed(1) + 's');
for (const n of viewsCsv.split(',')) {
  await page.evaluate(k => window.__view(k), n);
  await new Promise(r => setTimeout(r, 250));
  const p = outDir + '/' + n + '.png';
  await page.screenshot({ path: p });
  console.log('SHOT', n, fs.statSync(p).size, ((Date.now() - t0) / 1000).toFixed(1) + 's');
}
await browser.close();
console.log('ALL DONE');
