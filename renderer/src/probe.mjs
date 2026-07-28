/*
 * probe — dump the anchors a walkthrough can actually aim at.
 *
 * The app's data-testid vocabulary is thin and most of the names that look like
 * anchors live only in its test files, so writing zoom and click targets from
 * the source is guesswork. This logs in, visits each route, and reports the
 * selectors that exist at runtime along with their on-screen size, which is what
 * decides whether a component is worth zooming into at all.
 *
 *   just demo-probe <config> /ledger/close,/reports,/plan
 */
import { chromium } from 'playwright';
import { writeFile, mkdir } from 'node:fs/promises';
import path from 'node:path';
import { resolveCreds, newThemedContext, login, switchEntity, settle } from './session.mjs';

// Runs in the page. Returns candidate anchors, largest first, with a selector
// that Playwright can consume verbatim.
function collect() {
  const seen = new Map();
  const vw = window.innerWidth;
  const vh = window.innerHeight;

  const push = (selector, kind, text, el) => {
    const r = el.getBoundingClientRect();
    if (r.width < 40 || r.height < 18) return;            // too small to aim at
    if (r.bottom < 0 || r.top > vh * 3) return;           // far off screen
    if (seen.has(selector)) return;
    seen.set(selector, {
      selector, kind,
      text: (text || '').replace(/\s+/g, ' ').trim().slice(0, 70),
      x: Math.round(r.x), y: Math.round(r.y),
      w: Math.round(r.width), h: Math.round(r.height),
      // How far a zoom could push before the renderer's 2x cap bites.
      fit: +Math.min(vw / (r.width * 1.28), vh / (r.height * 1.28)).toFixed(2),
      inView: r.top < vh && r.bottom > 0,
    });
  };

  for (const el of document.querySelectorAll('[data-testid]')) {
    const id = el.getAttribute('data-testid');
    if (document.querySelectorAll(`[data-testid="${id}"]`).length === 1) {
      push(`[data-testid="${id}"]`, 'testid', el.innerText, el);
    }
  }
  for (const el of document.querySelectorAll('h1,h2,h3,h4')) {
    const t = (el.innerText || '').trim();
    if (t) push(`${el.tagName.toLowerCase()}:has-text(${JSON.stringify(t.slice(0, 40))})`, 'heading', t, el);
  }
  for (const el of document.querySelectorAll('button,a[role="button"],[role="tab"]')) {
    const t = (el.innerText || '').trim();
    if (t && t.length < 40) push(`button:has-text(${JSON.stringify(t)})`, 'button', t, el);
  }
  for (const el of document.querySelectorAll('table')) {
    const near = el.closest('section,div[class*="card"],div[class*="panel"]');
    push(`table >> nth=${[...document.querySelectorAll('table')].indexOf(el)}`, 'table',
      (near && near.innerText) || el.innerText, el);
  }
  // Cards and panels: the natural zoom targets. Anything boxed and big enough
  // to hold a number worth showing.
  for (const el of document.querySelectorAll('div,section,article')) {
    const s = getComputedStyle(el);
    const boxed = s.borderRadius !== '0px' && (s.borderTopWidth !== '0px' || s.boxShadow !== 'none');
    if (!boxed) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 180 || r.height < 90 || r.width > vw * 0.98) continue;
    const t = (el.innerText || '').trim();
    if (!t) continue;
    push(`text=${JSON.stringify(t.split('\n')[0].slice(0, 36))} >> xpath=ancestor-or-self::div[1]`, 'panel', t, el);
  }

  return [...seen.values()].sort((a, b) => b.w * b.h - a.w * a.h);
}

export async function probe(args) {
  const baseUrl = (args['base-url'] || 'http://localhost:3001').replace(/\/$/, '');
  const [W, H] = String(args.viewport || '1920x1080').split('x').map(Number);
  const theme = String(args.theme || 'dark');
  const routes = String(args.routes || '/home,/ledger/close,/ledger/statements,/reports,/plan')
    .split(',').map((s) => s.trim()).filter(Boolean);

  const { email, password } = await resolveCreds(args);
  const browser = await chromium.launch({ headless: true });
  const report = {};
  try {
    const context = await newThemedContext(browser, { width: W, height: H, deviceScaleFactor: 1, theme });
    const page = await context.newPage();
    await login(page, baseUrl, { email, password });
    if (args.entity) console.log(`✓ entity → ${await switchEntity(page, args.entity)}`);

    for (const route of routes) {
      await page.goto(`${baseUrl}${route}`, { waitUntil: 'domcontentloaded' });
      await settle(page);
      const anchors = await page.evaluate(collect);
      report[route] = anchors;

      console.log(`\n${route}   (${anchors.length} anchors)`);
      console.log('  ' + 'kind'.padEnd(8) + 'size'.padEnd(12) + 'fit'.padEnd(7) + 'text / selector');
      for (const a of anchors.slice(0, Number(args.top || 18))) {
        console.log(
          '  ' + a.kind.padEnd(8) +
          `${a.w}x${a.h}`.padEnd(12) +
          `${a.fit}x`.padEnd(7) +
          (a.text || '(no text)').slice(0, 44).padEnd(46) +
          a.selector
        );
      }
      if (args.shots) {
        const dir = path.resolve(args.shots);
        await mkdir(dir, { recursive: true });
        await page.screenshot({ path: path.join(dir, route.replace(/\W+/g, '_').replace(/^_/, '') + '.png') });
      }
    }

    if (args.out) {
      await mkdir(path.dirname(path.resolve(args.out)), { recursive: true });
      await writeFile(path.resolve(args.out), JSON.stringify(report, null, 2));
      console.log(`\n✓ ${path.relative(process.cwd(), path.resolve(args.out))}`);
    }
    console.log(
      '\n"fit" is the largest zoom that still frames the element; the renderer caps at 2x.\n' +
      'Anything under ~1.3x is already close to full-frame and is not worth zooming.'
    );
  } finally {
    await browser.close();
  }
}
