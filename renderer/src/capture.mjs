/*
 * capture — drive the live RoboLedger web UI headlessly and screenshot the
 * demo's money screens. This is the committed, deterministic version of the
 * hand-driven Puppeteer proof: login → navigate named scenes → still per scene.
 */
import { chromium } from 'playwright';
import { readFile, mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const rendererRoot = fileURLToPath(new URL('..', import.meta.url)); // renderer/

// The demo beats → routes (mapped from the RoboLedger nav).
const SCENES = {
  home: { path: '/home', label: 'Dashboard' },
  transactions: { path: '/ledger/transactions', label: 'Beat 1 — events / journal entries' },
  agents: { path: '/agents', label: 'Beat 1 — counterparties' },
  close: { path: '/ledger/close', label: 'Beat 2 — the AI close (Closing Book)' },
  statements: { path: '/ledger/statements', label: 'Beat 3 — financial statements' },
  reports: { path: '/reports', label: 'Beat 3 — the materialized report' },
};

async function resolveCreds(args) {
  if (args.email && args.password) return { email: args.email, password: args.password };
  if (args.config) {
    const cfg = JSON.parse(await readFile(args.config, 'utf8'));
    if (!cfg.email || !cfg.password) {
      throw new Error(`--config ${args.config} has no .email/.password`);
    }
    return { email: cfg.email, password: cfg.password };
  }
  throw new Error('Provide --config <robosystems config.json> or --email/--password');
}

// Switch the active entity via the header switcher (persists server-side for
// the session, so subsequent goto navigations reflect it). `target` is a
// case-insensitive name prefix, e.g. "Driftline" or "Cadence".
async function switchEntity(page, target) {
  // The header (and its entity name) loads async after the login redirect —
  // wait for the switcher to actually carry a company name before clicking it.
  await page.waitForFunction(
    () =>
      [...document.querySelectorAll('button')].some(
        (e) => /rounded-lg/.test(e.className || '') && /border/.test(e.className || '') &&
          /(Inc\.|LLC|Roasters|Labs|Group|Co\.|Ltd)/i.test(e.innerText || '')
      ),
    { timeout: 15000 }
  );
  const opened = await page.evaluate(() => {
    const btn = [...document.querySelectorAll('button')].find(
      (e) => /rounded-lg/.test(e.className || '') && /border/.test(e.className || '') &&
        /(Inc\.|LLC|Roasters|Labs|Group|Co\.|Ltd)/i.test(e.innerText || '')
    );
    if (btn) { btn.click(); return true; }
    return false;
  });
  if (!opened) throw new Error('entity switcher button not found in header');
  await page.waitForTimeout(400);
  const picked = await page.evaluate((t) => {
    const opt = [...document.querySelectorAll('button')].find(
      (e) => (e.innerText || '').trim().toLowerCase().startsWith(t.toLowerCase())
    );
    if (opt) { opt.click(); return (opt.innerText || '').trim().split('\n')[0]; }
    return null;
  }, target);
  if (!picked) throw new Error(`entity "${target}" not found in the switcher`);
  await page.waitForTimeout(900); // let the server persist + the app settle
  return picked;
}

export async function capture(args) {
  const baseUrl = (args['base-url'] || 'http://localhost:3001').replace(/\/$/, '');
  const outDir = args.out ? path.resolve(args.out) : path.join(rendererRoot, 'out', 'capture');
  const [w, h] = String(args.viewport || '1600x1000').split('x').map(Number);
  const fullPage = Boolean(args['full-page']);
  const theme = String(args.theme || 'dark'); // on-brand default
  const entity = args.entity ? String(args.entity) : null;
  const keys = String(args.scenes || 'home,transactions,agents,close,statements,reports')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);

  const { email, password } = await resolveCreds(args);
  await mkdir(outDir, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: w, height: h },
    deviceScaleFactor: 2,
    colorScheme: theme === 'light' ? 'light' : theme === 'auto' ? 'no-preference' : 'dark',
  });
  // Force the app's stored theme deterministically — Flowbite reads this on load.
  await context.addInitScript((t) => {
    try { localStorage.setItem('flowbite-theme-mode', t); } catch {}
  }, theme);
  const page = await context.newPage();

  try {
    // --- login ---
    await page.goto(`${baseUrl}/login`, { waitUntil: 'networkidle' });
    await page.fill('#email', email);
    await page.fill('#password', password);
    await Promise.all([
      page.waitForURL((url) => !url.pathname.endsWith('/login'), { timeout: 30000 }),
      page.click('button[type="submit"]'),
    ]);
    console.log(`✓ authenticated → ${page.url()}  (theme: ${theme})`);

    if (entity) {
      const picked = await switchEntity(page, entity);
      console.log(`✓ entity → ${picked}`);
    }

    // --- scenes ---
    const captured = [];
    for (const key of keys) {
      const scene = SCENES[key];
      if (!scene) {
        console.warn(`  ! unknown scene "${key}" — skipping (known: ${Object.keys(SCENES).join(', ')})`);
        continue;
      }
      await page.goto(`${baseUrl}${scene.path}`, { waitUntil: 'networkidle' });
      // settle: fonts + a beat for any client-side data fetch / animation
      await page.evaluate(() => document.fonts && document.fonts.ready);
      await page.waitForTimeout(600);
      const file = path.join(outDir, `${key}.png`);
      await page.screenshot({ path: file, fullPage });
      captured.push({ key, label: scene.label, path: scene.path, file });
      console.log(`  ✓ ${key.padEnd(13)} ${scene.path.padEnd(26)} → ${path.relative(process.cwd(), file)}`);
    }

    console.log(`\nCaptured ${captured.length} scene(s) → ${path.relative(process.cwd(), outDir)}/`);
  } finally {
    await browser.close();
  }
}
