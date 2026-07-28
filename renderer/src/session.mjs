/*
 * session — the shared RoboLedger browser session: credentials, login, and the
 * entity switcher. Extracted from capture.mjs so `capture`, `demo` and `probe`
 * all authenticate the same way against the same app.
 */
import { readFile } from 'node:fs/promises';

export async function resolveCreds(args) {
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

/*
 * A browser context pinned to one theme. Chromium is told both the OS-level
 * preference and the app's own stored Flowbite mode, because the app reads the
 * latter on load and would otherwise flash to its default.
 */
export async function newThemedContext(browser, { width, height, deviceScaleFactor = 2, theme = 'dark' }) {
  const context = await browser.newContext({
    viewport: { width, height },
    deviceScaleFactor,
    colorScheme: theme === 'light' ? 'light' : theme === 'auto' ? 'no-preference' : 'dark',
    reducedMotion: 'no-preference',
  });
  await context.addInitScript((t) => {
    try { localStorage.setItem('flowbite-theme-mode', t); } catch {}
  }, theme);
  return context;
}

export async function login(page, baseUrl, { email, password }) {
  await page.goto(`${baseUrl}/login`, { waitUntil: 'networkidle' });
  await page.fill('#email', email);
  await page.fill('#password', password);
  await Promise.all([
    page.waitForURL((url) => !url.pathname.endsWith('/login'), { timeout: 30000 }),
    page.click('button[type="submit"]'),
  ]);
  return page.url();
}

/*
 * Switch the active entity via the header switcher. The selection persists
 * server-side for the session, so later navigations keep it. `target` is a
 * case-insensitive name prefix, e.g. "Driftline" or "Cadence".
 */
export async function switchEntity(page, target) {
  // The header (and its entity name) loads async after the login redirect - wait
  // for the switcher to actually carry a company name before clicking it.
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

/*
 * Wait for the app to be visually done: network quiet, fonts loaded, no
 * spinners or skeletons on screen, and two consecutive identical layout
 * hashes. The demo driver captures frames far slower than wall-clock, so any
 * in-flight entrance animation would otherwise snap between frames rather than
 * play. Settling off-camera keeps the recorded timeline clean.
 */
export async function settle(page, { timeout = 12000, quietMs = 350 } = {}) {
  try {
    await page.waitForLoadState('networkidle', { timeout });
  } catch {
    /* a long-poll or websocket can keep the network busy forever - keep going */
  }
  await page.evaluate(() => document.fonts && document.fonts.ready).catch(() => {});
  try {
    await page.waitForFunction(
      () => !document.querySelector(
        '[data-testid="spinner"],[data-testid="loading-state"],[role="progressbar"],.animate-pulse,.animate-spin'
      ),
      { timeout }
    );
  } catch {
    /* a permanently animated element is not a reason to abandon the shot */
  }
  await page.waitForTimeout(quietMs);
}
