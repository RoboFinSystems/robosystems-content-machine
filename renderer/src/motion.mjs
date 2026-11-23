/*
 * motion - render a self-contained HTML composition to a silent mp4.
 *
 * The page owns its own timeline and follows the webdeck contract:
 *   window.__init()   async setup (fonts, DOM), then sets window.__READY = true
 *   window.__total()  duration in seconds
 *   window.__seek(t)  pose the stage at time t (a pure function of t)
 *
 * Every frame is posed with __seek and screenshotted, so the render is
 * deterministic. Outputs land next to the HTML (renders/<name>.mp4) unless
 * --out is given. --stills "1.5,12,30" writes QA PNGs instead of a video.
 *
 * --root DIR serves DIR over http and opens the page from there, for pages
 * that load ES modules or absolute /paths (file:// can't). --query appends a
 * query string, e.g. the roboledger-app landing demos:
 *   --root ~/Projects/roboledger-app/public --html .../public/demos/render.html --query demo=hero --name hero
 * --mount "/demos/=DIR,/fonts/=DIR" adds more url prefixes to that server, so a
 * page under --root can import files from another folder (templates/ imports the
 * landing kit from roboledger-app this way).
 */
import { chromium } from 'playwright';
import { mkdir, rm, readdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import path from 'node:path';
import { framesToMp4 } from './ffmpeg.mjs';
import { serve } from './server.mjs';

export async function motion(args) {
  if (!args.html) throw new Error('motion requires --html <file.html>');
  const htmlPath = path.resolve(args.html);
  if (!existsSync(htmlPath)) throw new Error(`no such html: ${htmlPath}`);
  const name = args.name || path.basename(htmlPath, '.html');
  const outDir = args.out ? path.resolve(args.out) : path.join(path.dirname(htmlPath), 'renders');
  const W = Number(args.width || 1920);
  const H = Number(args.height || 1080);
  const fps = Number(args.fps || 30);
  await mkdir(outDir, { recursive: true });

  const browser = await chromium.launch({
    headless: true,
    args: ['--force-color-profile=srgb', '--hide-scrollbars', '--allow-file-access-from-files'],
  });
  const mounts = {};
  for (const m of String(args.mount || '').split(',').filter(Boolean)) {
    const [prefix, dir] = m.split('=');
    mounts[prefix] = path.resolve(dir.replace(/^~/, process.env.HOME));
  }
  if (args.root) mounts['/'] = path.resolve(args.root); // last: '/' matches everything
  const server = args.root ? await serve({ html: '', mounts }) : null;
  try {
    const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
    const q = args.query ? `?${args.query}` : '';
    const url = server
      ? `${server.url}/${path.relative(path.resolve(args.root), htmlPath).split(path.sep).join('/')}${q}`
      : pathToFileURL(htmlPath).href + q;
    await page.goto(url, { waitUntil: 'load' });
    await page.waitForFunction(() => typeof window.__init === 'function');
    await page.evaluate(() => window.__init());
    await page.waitForFunction(() => window.__READY === true);
    const total = await page.evaluate(() => window.__total());
    const pose = (t) =>
      page.evaluate(
        (s) => new Promise((r) => { window.__seek(s); requestAnimationFrame(() => requestAnimationFrame(r)); }),
        t
      );

    if (args.stills) {
      const times = String(args.stills).split(',').map(Number).filter((t) => !Number.isNaN(t));
      for (const t of times) {
        await pose(Math.min(t, total));
        const file = path.join(outDir, `${name}-${t.toFixed(2)}s.png`);
        await page.screenshot({ path: file });
        console.log(`  still ${t}s -> ${path.relative(process.cwd(), file)}`);
      }
      return;
    }

    const framesDir = path.join(outDir, `${name}-frames`);
    await rm(framesDir, { recursive: true, force: true });
    await mkdir(framesDir, { recursive: true });
    // --from/--to (seconds) render part of the film: frame files are numbered from 0 at --from
    const first = Math.max(0, Math.round(Number(args.from || 0) * fps));
    const last = Math.min(Math.round(total * fps), args.to ? Math.round(Number(args.to) * fps) : Infinity);
    const count = last - first;
    const workers = Math.max(1, Math.min(Number(args.workers || 1), count));
    console.log(`  rendering ${count} frames @ ${fps}fps (${W}x${H}) = ${(count / fps).toFixed(1)}s${workers > 1 ? `, ${workers} pages` : ''}`);
    // a frame is a pure function of its time, so pages can share the work: each takes every
    // workers-th frame, which keeps heavy and light stretches spread evenly between them
    const shoot = async (pg, k) => {
      const poseOn = (t) => pg.evaluate((s) => new Promise((r) => { window.__seek(s); requestAnimationFrame(() => requestAnimationFrame(r)); }), t);
      for (let i = first + k; i < last; i += workers) {
        await poseOn(i / fps);
        await pg.screenshot({ path: path.join(framesDir, `frame-${String(i - first).padStart(5, '0')}.png`) });
        if (k === 0 && (i - first) % (fps * 5) < workers) process.stdout.write(`\r  ${Math.round(((i - first) / count) * 100)}%`);
      }
    };
    const pages = [page];
    for (let k = 1; k < workers; k++) {
      const pg = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
      await pg.goto(url, { waitUntil: 'load' });
      await pg.waitForFunction(() => typeof window.__init === 'function');
      await pg.evaluate(() => window.__init());
      await pg.waitForFunction(() => window.__READY === true);
      pages.push(pg);
    }
    await Promise.all(pages.map((pg, k) => shoot(pg, k)));
    const outFile = path.join(outDir, `${name}.mp4`);
    await framesToMp4({ framePattern: path.join(framesDir, 'frame-%05d.png'), fps, out: outFile });
    console.log(`\n✓ ${path.relative(process.cwd(), outFile)}  (silent)`);
    if (!args['keep-frames']) await rm(framesDir, { recursive: true, force: true });
    else console.log(`  frames kept -> ${framesDir} (${(await readdir(framesDir)).length})`);
  } finally {
    await browser.close();
    if (server) await server.close();
  }
}
