#!/usr/bin/env node
/* Deterministic frame renderer for webdeck HTML.
 *
 * Drives headless Chrome (system install, via puppeteer-core) with a virtual
 * clock: for each frame, page.evaluate(__seek(t)) then screenshot. No live
 * recording, no dropped frames. Frames are piped straight into per-worker
 * ffmpeg chunk encodes and concatenated at the end - no 10GB PNG pile.
 *
 * Modes:
 *   full render:  node render_webdeck.mjs --html X.html --out dir [--fps 30] [--workers 6]
 *   QA stills:    node render_webdeck.mjs --html X.html --out dir --stills "1.0,5.5,30"
 */

import { spawn, execSync } from 'node:child_process';
import { mkdirSync, writeFileSync, existsSync } from 'node:fs';
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
const FPS = Number(args.fps || 30);
const WORKERS = Number(args.workers || 6);
const CHROME = args.chrome ||
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

if (!existsSync(HTML)) { console.error(`no such html: ${HTML}`); process.exit(1); }
mkdirSync(OUT, { recursive: true });

async function newReadyPage(browser) {
  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 1 });
  await page.goto(pathToFileURL(HTML).href, { waitUntil: 'load', timeout: 60000 });
  await page.evaluate('window.__init()');
  await page.waitForFunction('window.__READY === true', { timeout: 60000 });
  return page;
}

async function main() {
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: true,
    args: [
      '--force-color-profile=srgb',
      '--hide-scrollbars',
      '--disable-gpu-vsync',
      '--allow-file-access-from-files',
      `--window-size=1920,1080`,
    ],
  });

  try {
    const probe = await newReadyPage(browser);
    const total = await probe.evaluate('window.__total()');

    if (args.stills) {
      const times = String(args.stills).split(',').map(Number);
      for (const t of times) {
        await probe.evaluate(`window.__seek(${t})`);
        const f = path.join(OUT, `still_${t.toFixed(2).replace('.', '_')}.png`);
        await probe.screenshot({ path: f });
        console.log(`still ${t}s -> ${f}`);
      }
      await browser.close();
      return;
    }

    const totalFrames = Math.ceil(total * FPS);
    console.log(`duration ${total}s -> ${totalFrames} frames @ ${FPS}fps, ${WORKERS} workers`);
    await probe.close();

    // contiguous chunks, one ffmpeg encode per chunk
    const per = Math.ceil(totalFrames / WORKERS);
    const chunks = [];
    for (let w = 0; w < WORKERS; w++) {
      const startF = w * per;
      const endF = Math.min(totalFrames, startF + per);
      if (startF >= endF) break;
      chunks.push({ w, startF, endF, file: path.join(OUT, `chunk_${String(w).padStart(2, '0')}.mp4`) });
    }

    const t0 = Date.now();
    let done = 0;
    await Promise.all(chunks.map(async (chunk) => {
      const page = await newReadyPage(browser);
      const ff = spawn('ffmpeg', [
        '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-i', 'pipe:0',
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '17',
        '-pix_fmt', 'yuv420p', chunk.file,
      ], { stdio: ['pipe', 'ignore', 'ignore'] });
      const ffDone = new Promise((res, rej) => {
        ff.on('close', c => c === 0 ? res() : rej(new Error(`ffmpeg chunk ${chunk.w} exit ${c}`)));
        ff.on('error', rej);
      });

      for (let f = chunk.startF; f < chunk.endF; f++) {
        const t = f / FPS;
        await page.evaluate(`window.__seek(${t})`);
        const buf = await page.screenshot({ type: 'png', optimizeForSpeed: true });
        if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
        done++;
        if (done % 250 === 0) {
          const rate = done / ((Date.now() - t0) / 1000);
          const eta = Math.round((totalFrames - done) / rate);
          console.log(`frames ${done}/${totalFrames} (${rate.toFixed(1)} fps, eta ${eta}s)`);
        }
      }
      ff.stdin.end();
      await ffDone;
      await page.close();
      console.log(`chunk ${chunk.w} done (${chunk.endF - chunk.startF} frames)`);
    }));

    const listFile = path.join(OUT, 'chunks.txt');
    writeFileSync(listFile, chunks.map(c => `file '${c.file}'`).join('\n') + '\n');
    const silent = path.join(OUT, 'silent.mp4');
    execSync(`ffmpeg -y -f concat -safe 0 -i "${listFile}" -c copy "${silent}"`, { stdio: 'inherit' });
    console.log(`silent video: ${silent}`);
    console.log(`wall time: ${Math.round((Date.now() - t0) / 1000)}s`);
  } finally {
    await browser.close();
  }
}

main().catch(e => { console.error(e); process.exit(1); });
