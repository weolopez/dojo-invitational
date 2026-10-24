import puppeteer from 'puppeteer-core';
import fs from 'node:fs';

const [chromePath, url, outDir] = process.argv.slice(2);
fs.mkdirSync(outDir, { recursive: true });
const browser = await puppeteer.launch({
  executablePath: chromePath, headless: true,
  args: ['--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--window-size=1100,850'],
});
const page = await browser.newPage();
await page.setViewport({ width: 1100, height: 850 });
const errors = [];
page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') errors.push(m.type() + ': ' + m.text().slice(0, 200)); });
page.on('pageerror', (e) => errors.push('pageerror: ' + String(e).slice(0, 300)));

await page.goto(url, { waitUntil: 'load', timeout: 60000 });
await page.waitForFunction(() => window.__demo && document.getElementById('state').textContent.includes('ANIMATED'), { timeout: 60000 });
console.log('READY');
const shot = async (name) => { await page.screenshot({ path: `${outDir}/${name}.png` }); console.log('SHOT', name); };
const waitMode = (m, t = 60000) => page.waitForFunction((mm) => window.__demo.mode() === mm, { timeout: t }, m);

await new Promise((r) => setTimeout(r, 1200));
await shot('1_idle');
await page.evaluate(() => window.__demo.fall('back'));
await new Promise((r) => setTimeout(r, 550));
console.log('PELVIS@fall', JSON.stringify(await page.evaluate(() => window.__demo.pelvis())));
await shot('2_falling');
await page.waitForFunction(() => window.__demo.settled(), { timeout: 30000 });
console.log('SETTLED', JSON.stringify(await page.evaluate(() => window.__demo.pelvis())));
await shot('3_settled');
await page.evaluate(() => window.__demo.getUp());
await new Promise((r) => setTimeout(r, 1100));
await shot('4_recovering');
await waitMode('ANIM');
await new Promise((r) => setTimeout(r, 600));
await shot('5_recovered');
console.log('MODE', await page.evaluate(() => window.__demo.mode()));
await page.evaluate(() => window.__demo.fall('side'));
await new Promise((r) => setTimeout(r, 2000));
await shot('6_side_fall');
console.log('ERRORS:', JSON.stringify(errors.slice(0, 8), null, 1));
await browser.close();
console.log('DONE');
