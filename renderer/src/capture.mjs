/*
 * capture — drive the live RoboLedger web UI headlessly and screenshot the
 * demo's money screens. This is the committed, deterministic version of the
 * hand-driven Puppeteer proof: login → navigate named scenes → still per scene.
 */
import { chromium } from 'playwright';
import { mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { resolveCreds, newThemedContext, login, switchEntity, settle } from './session.mjs';

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
  const context = await newThemedContext(browser, {
    width: w, height: h, deviceScaleFactor: 2, theme,
  });
  const page = await context.newPage();

  try {
    console.log(`✓ authenticated → ${await login(page, baseUrl, { email, password })}  (theme: ${theme})`);

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
      await page.goto(`${baseUrl}${scene.path}`, { waitUntil: 'domcontentloaded' });
      await settle(page, { quietMs: 600 });
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
