#!/usr/bin/env node
/* Generic HTML -> PNG snapshot via headless system Chrome.
 * Usage: node snap.mjs --html page.html --out shot.png [--width 2000] [--height 800]
 */

import { existsSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import path from 'node:path';
import puppeteer from 'puppeteer-core';

const args = {};
for (let i = 2; i < process.argv.length; i++) {
  const a = process.argv[i];
  if (a.startsWith('--')) args[a.slice(2)] = process.argv[i + 1]?.startsWith('--') ? true : process.argv[++i];
}

const HTML = path.resolve(args.html);
const OUT = path.resolve(args.out);
const W = Number(args.width || 2000);
const H = Number(args.height || 800);
const CHROME = args.chrome ||
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

if (!existsSync(HTML)) { console.error(`no such html: ${HTML}`); process.exit(1); }

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: 'new',
  args: ['--force-color-profile=srgb', '--disable-lcd-text', '--hide-scrollbars'],
});
const page = await browser.newPage();
await page.setViewport({ width: W, height: H, deviceScaleFactor: 1 });
await page.goto(pathToFileURL(HTML).href, { waitUntil: 'networkidle0', timeout: 30000 });
await page.evaluate('document.fonts.ready.then(() => true)');
await page.screenshot({ path: OUT, type: 'png' });
await browser.close();
console.log(OUT);
