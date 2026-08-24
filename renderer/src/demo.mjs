/*
 * demo — record a scripted walkthrough of the live RoboLedger UI.
 *
 * The difference from `capture` (stills + a Ken Burns drift bolted on later) is
 * that this drives the real product: a pointer travels, hovers, clicks, scrolls
 * and the app responds, because the drawn cursor and the real mouse are the same
 * mouse. Zoom is a camera over the live page, not a crop of a PNG.
 *
 * Two rules make it hold together:
 *
 *   1. VO owns the clock. Each beat's frame budget comes from the length of its
 *      narration mp3 (written into the spec by tools/demo_narrate.py), and the
 *      beat's actions are fitted into exactly that many frames. Audio and video
 *      cannot drift.
 *
 *   2. Waiting happens off camera. Navigations, network settles and entrance
 *      animations run to completion between frames, never during them. A frame
 *      is only ever shot of a settled UI, so the recording has no dead air and
 *      the product looks as fast as it actually is.
 *
 * Zoom stays sharp because the browser, not an upscaler, does the work: the page
 * is rendered at deviceScaleFactor 2 and each frame is a screenshot `clip` of
 * the camera rect, downsampled to the output size. At 1x that is a supersampled
 * 1080p frame; at the 2x cap it is pixel-for-pixel. Nothing is ever upsampled.
 */
import { chromium } from 'playwright';
import sharp from 'sharp';
import { readFile, mkdir, rm, readdir } from 'node:fs/promises';
import path from 'node:path';
import { framesToMp4 } from './ffmpeg.mjs';
import { installCursor } from './cursor.mjs';
import { resolveCreds, newThemedContext, login, switchEntity, settle } from './session.mjs';

const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
const clamp01 = (t) => clamp(t, 0, 1);
const lerp = (a, b, t) => a + (b - a) * t;
const easeInOut = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const easeOut = (t) => 1 - Math.pow(1 - clamp01(t), 3);

// ---------------------------------------------------------------------------
// Target resolution
//
// A target is a raw Playwright selector string, or [x, y] in CSS pixels, or an
// object { selector, offset: [dx, dy] }. Raw selectors on purpose: the app has
// only a thin data-testid vocabulary, so specs need text=, role= and :has-text()
// as first-class options rather than a bespoke targeting DSL.
// ---------------------------------------------------------------------------

function targetSpec(t) {
  if (Array.isArray(t)) return { point: { x: t[0], y: t[1] } };
  if (typeof t === 'string') return { selector: t, offset: [0, 0] };
  return { selector: t.selector, offset: t.offset || [0, 0], nth: t.nth, timeout: t.timeout };
}

/*
 * When a target misses, say what the page actually offers. Specs are written
 * against a live app that only exists while the stack is up, so a bare "not
 * found" costs a whole restart to diagnose.
 */
async function suggestTargets(page, selector) {
  const want = String(selector).toLowerCase().replace(/[^a-z0-9]+/g, '');
  const found = await page.evaluate(() => {
    const out = [];
    for (const el of document.querySelectorAll('[data-testid]')) {
      out.push({ sel: `[data-testid="${el.getAttribute('data-testid')}"]`, txt: (el.innerText || '').slice(0, 40) });
    }
    for (const el of document.querySelectorAll('h1,h2,h3,button,[role="tab"]')) {
      const t = (el.innerText || '').trim();
      if (t && t.length < 40) out.push({ sel: `${el.tagName.toLowerCase()}:has-text(${JSON.stringify(t)})`, txt: t });
    }
    return out.slice(0, 400);
  }).catch(() => []);

  const score = (c) => {
    const hay = (c.sel + ' ' + c.txt).toLowerCase().replace(/[^a-z0-9]+/g, '');
    let n = 0;
    for (let i = 0; i + 3 <= want.length; i++) if (hay.includes(want.slice(i, i + 3))) n++;
    return n;
  };
  return found.map((c) => ({ ...c, s: score(c) })).filter((c) => c.s > 0)
    .sort((a, b) => b.s - a.s).slice(0, 6).map((c) => `      ${c.sel}`);
}

async function resolveBox(page, target) {
  const t = targetSpec(target);
  if (t.point) return { x: t.point.x - 1, y: t.point.y - 1, width: 2, height: 2, point: t.point };
  let loc = page.locator(t.selector);
  if (t.nth != null) loc = loc.nth(t.nth);
  else loc = loc.first();
  // Every action settles the page first, so a target that is not there within a
  // few seconds is a spec bug, not a slow app. The default 30s wait would turn
  // one typo into half a minute of silence per beat.
  const box = await loc.boundingBox({ timeout: t.timeout ?? 4000 }).catch(() => null);
  if (!box) {
    const hints = await suggestTargets(page, t.selector);
    throw new Error(
      `target not found or not visible on ${new URL(page.url()).pathname}: ${t.selector}` +
      (hints.length ? `\n    closest anchors on the page:\n${hints.join('\n')}` : '') +
      `\n    full list: just demo-probe <config> "" "${new URL(page.url()).pathname}"`
    );
  }
  return {
    ...box,
    point: {
      x: box.x + box.width / 2 + (t.offset[0] || 0),
      y: box.y + box.height / 2 + (t.offset[1] || 0),
    },
    locator: loc,
  };
}

// ---------------------------------------------------------------------------
// Recorder — owns the camera, the cursor, and the frame counter
// ---------------------------------------------------------------------------

class Recorder {
  constructor(page, { W, H, fps, dsf, maxZoom, framesDir, stills = false }) {
    Object.assign(this, { page, W, H, fps, dsf, maxZoom, framesDir, stills });
    this.cam = { cx: W / 2, cy: H / 2, z: 1 };
    this.cursor = { x: W * 0.5, y: H * 0.62 };
    this.frame = 0;
    this.moveIndex = 0;
    this.pending = [];
  }

  msToFrames(ms) {
    return Math.max(1, Math.round((ms / 1000) * this.fps));
  }

  /* The camera rect in CSS pixels, clamped so it never leaves the viewport. */
  clip() {
    const { W, H, maxZoom } = this;
    const z = clamp(this.cam.z, 1, maxZoom);
    const w = W / z;
    const h = H / z;
    const x = clamp(this.cam.cx - w / 2, 0, W - w);
    const y = clamp(this.cam.cy - h / 2, 0, H - h);
    return {
      x: Math.round(x),
      y: Math.round(y),
      width: Math.max(2, Math.round(w)),
      height: Math.max(2, Math.round(h)),
    };
  }

  async syncCursor() {
    const { x, y } = this.cursor;
    await this.page.mouse.move(x, y);
    const ok = await this.page.evaluate(([cx, cy]) => {
      if (!window.__rsCursor) return false;
      window.__rsCursor.set(cx, cy);
      return window.__rsCursor.ensure();
    }, [x, y]);
    // An init script that throws fails silently, so a missing pointer would
    // otherwise only surface after a full render.
    if (!ok && !this.cursorWarned) {
      this.cursorWarned = true;
      console.warn('  ! the pointer overlay is not mounted - recording without a visible cursor');
    }
    return ok;
  }

  /*
   * Shoot one frame. The screenshot is taken at the camera rect and downsampled
   * to the output size; sharp runs off the critical path so the browser can
   * paint the next frame while the previous one is still being written.
   */
  async shoot() {
    // Fit-check mode walks the whole choreography but only writes one frame per
    // beat, so a zoom aimed at the wrong element costs ten seconds to catch
    // instead of a full render.
    if (this.stills) { this.frame++; return; }
    const buf = await this.page.screenshot({ clip: this.clip(), animations: 'allow' });
    const file = path.join(this.framesDir, `frame-${String(this.frame++).padStart(5, '0')}.png`);
    this.pending.push(
      sharp(buf).resize(this.W, this.H, { fit: 'fill' }).png({ compressionLevel: 3 }).toFile(file)
    );
    if (this.pending.length >= 8) {
      await Promise.all(this.pending);
      this.pending = [];
    }
  }

  async flush() {
    await Promise.all(this.pending);
    this.pending = [];
  }

  /* Write one framed still, named for the beat it closes. */
  async shootStill(name) {
    const buf = await this.page.screenshot({ clip: this.clip(), animations: 'allow' });
    const file = path.join(this.framesDir, `${name}.png`);
    await sharp(buf).resize(this.W, this.H, { fit: 'fill' }).png({ compressionLevel: 6 }).toFile(file);
    return file;
  }

  /* Hold the current state for n frames. */
  async hold(n) {
    for (let i = 0; i < n; i++) await this.shoot();
  }

  /*
   * Move the pointer along a gently bowed path. A straight line between two
   * points is the tell that a machine is driving; real hands arc, and alternate
   * which way they arc.
   */
  async move(to, frames) {
    const from = { ...this.cursor };
    const dx = to.x - from.x;
    const dy = to.y - from.y;
    const dist = Math.hypot(dx, dy);
    const bow = Math.min(0.14 * dist, 46) * (this.moveIndex++ % 2 ? -1 : 1);
    const nx = dist ? -dy / dist : 0;
    const ny = dist ? dx / dist : 0;

    for (let i = 0; i < frames; i++) {
      const t = frames === 1 ? 1 : easeInOut(i / (frames - 1));
      const arc = Math.sin(Math.PI * (frames === 1 ? 1 : i / (frames - 1))) * bow;
      this.cursor = { x: lerp(from.x, to.x, t) + nx * arc, y: lerp(from.y, to.y, t) + ny * arc };
      await this.syncCursor();
      await this.shoot();
    }
    this.cursor = { ...to };
  }

  /* Animate the camera toward a rect (or back to the full frame). */
  async zoomTo(target, frames, padding = 0.14, box = undefined) {
    const from = { ...this.cam };
    let to;
    if (target === 'reset' || target == null) {
      to = { cx: this.W / 2, cy: this.H / 2, z: 1 };
    } else {
      box = box || (await resolveBox(this.page, target));
      const fit = Math.min(
        this.W / (box.width * (1 + padding * 2)),
        this.H / (box.height * (1 + padding * 2))
      );
      to = {
        cx: box.x + box.width / 2,
        cy: box.y + box.height / 2,
        z: clamp(fit, 1, this.maxZoom),
      };
    }
    for (let i = 0; i < frames; i++) {
      const t = frames === 1 ? 1 : easeInOut(i / (frames - 1));
      this.cam = {
        cx: lerp(from.cx, to.cx, t),
        cy: lerp(from.cy, to.cy, t),
        // Interpolate zoom geometrically - linear interpolation of scale reads
        // as a lurch that decelerates too early.
        z: from.z * Math.pow(to.z / from.z, t),
      };
      await this.syncCursor();
      await this.shoot();
    }
    this.cam = to;
  }

  /* Press, click for real, then ride the ripple out. */
  async click(frames, { button = 'left' } = {}) {
    const pressF = Math.max(1, Math.min(Math.round(frames * 0.28), frames - 1));
    const rippleF = frames - pressF;
    const { x, y } = this.cursor;

    await this.page.mouse.move(x, y);
    await this.page.mouse.down({ button });
    for (let i = 0; i < pressF; i++) {
      await this.page.evaluate((t) => window.__rsCursor && window.__rsCursor.press(t), (i + 1) / pressF);
      await this.shoot();
    }
    await this.page.mouse.up({ button });
    await this.page.evaluate(() => window.__rsCursor && window.__rsCursor.press(0));

    for (let i = 0; i < rippleF; i++) {
      const t = (i + 1) / rippleF;
      await this.page.evaluate(
        ([tt, cx, cy]) => {
          window.__rsCursor && window.__rsCursor.set(cx, cy);
          window.__rsCursor && window.__rsCursor.ripple(tt);
        },
        [t, x, y]
      );
      await this.shoot();
    }
    await this.page.evaluate(() => window.__rsCursor && window.__rsCursor.ripple(0));
  }

  /*
   * Smooth-scroll the element's own scroll container so the element lands in
   * view. Panels here scroll independently of the document, so the container is
   * discovered rather than assumed.
   */
  async scrollTo(target, frames, block = 'center') {
    const t = targetSpec(target);
    if (!t.selector) return this.hold(frames);

    // Playwright understands :has-text() / nth; querySelector does not.
    // Tag the resolved node, then animate its scroll container.
    let loc = this.page.locator(t.selector);
    if (t.nth != null) loc = loc.nth(t.nth);
    else loc = loc.first();
    const handle = await loc.elementHandle({ timeout: t.timeout ?? 4000 }).catch(() => null);
    if (!handle) return this.hold(frames);
    await this.page.evaluate((el) => {
      document.querySelectorAll('[data-rsdemo-scroll-target]').forEach((n) => n.removeAttribute('data-rsdemo-scroll-target'));
      el.setAttribute('data-rsdemo-scroll-target', '1');
    }, handle);

    const plan = await this.page.evaluate(
      ([sel, blk]) => {
        const el = document.querySelector('[data-rsdemo-scroll-target]') || document.querySelector(sel);
        if (!el) return null;
        const scroller = (() => {
          let n = el.parentElement;
          while (n && n !== document.body) {
            const s = getComputedStyle(n);
            if (/(auto|scroll)/.test(s.overflowY) && n.scrollHeight > n.clientHeight + 4) return n;
            n = n.parentElement;
          }
          return document.scrollingElement || document.documentElement;
        })();
        const isDoc = scroller === (document.scrollingElement || document.documentElement);
        const cRect = isDoc
          ? { top: 0, height: window.innerHeight }
          : scroller.getBoundingClientRect();
        const eRect = el.getBoundingClientRect();
        const want =
          blk === 'start'
            ? eRect.top - cRect.top
            : eRect.top - cRect.top - (cRect.height - eRect.height) / 2;
        const from = scroller.scrollTop;
        const to = Math.max(0, Math.min(from + want, scroller.scrollHeight - scroller.clientHeight));
        scroller.setAttribute('data-rsdemo-scroller', '1');
        return { from, to, isDoc };
      },
      [t.selector, block]
    );
    if (!plan || Math.abs(plan.to - plan.from) < 2) return this.hold(frames);

    for (let i = 0; i < frames; i++) {
      const p = frames === 1 ? 1 : easeInOut(i / (frames - 1));
      await this.page.evaluate((v) => {
        const s = document.querySelector('[data-rsdemo-scroller]');
        if (s) s.scrollTop = v;
      }, lerp(plan.from, plan.to, p));
      await this.syncCursor();
      await this.shoot();
    }
    await this.page.evaluate(() => {
      const s = document.querySelector('[data-rsdemo-scroller]');
      if (s) s.removeAttribute('data-rsdemo-scroller');
      document.querySelectorAll('[data-rsdemo-scroll-target]').forEach((n) => n.removeAttribute('data-rsdemo-scroll-target'));
    });
  }

  /* Type with a human-ish cadence, one frame per few characters. */
  async type(text, frames) {
    const per = Math.max(1, Math.ceil(text.length / frames));
    let i = 0;
    for (let f = 0; f < frames; f++) {
      const next = Math.min(text.length, i + per);
      if (next > i) {
        await this.page.keyboard.type(text.slice(i, next), { delay: 0 });
        i = next;
      }
      await this.shoot();
    }
    if (i < text.length) await this.page.keyboard.type(text.slice(i), { delay: 0 });
  }
}

// ---------------------------------------------------------------------------
// Timeline planning
//
// Every beat is fitted to its narration exactly. Actions declaring `ms` are
// fixed; `dwell` actions without `ms` are elastic and soak up whatever is left.
// If the fixed actions overflow the narration they are scaled down together and
// the spec author is told, because that means the beat is over-choreographed
// rather than that the timing is wrong.
// ---------------------------------------------------------------------------

const DEFAULT_MS = {
  goto: 500, move: 900, hover: 900, click: 460, zoom: 1100,
  scroll: 1000, dwell: 800, type: 900, wait: 0, key: 240, api: 0, select: 900,
  overlay: 1600, 'overlay-clear': 200,
};

function planBeat(beat, fps, warn, stills = false) {
  const actions = beat.actions || [];
  // Fit-check mode collapses every action to its settled end state.
  if (stills) return actions.map((a) => ({ ...a, frames: (a.kind === 'wait' || a.kind === 'api') ? 0 : 1 }));
  const total = Math.max(1, Math.round(((beat.durationMs || 3000) / 1000) * fps));
  const f = (ms) => Math.max(1, Math.round((ms / 1000) * fps));

  const elastic = [];
  let fixed = 0;
  const planned = actions.map((a, i) => {
    if (a.kind === 'wait' || a.kind === 'api') return { ...a, frames: 0 };
    if (a.kind === 'dwell' && a.ms == null) {
      elastic.push(i);
      return { ...a, frames: 0 };
    }
    const n = f(a.ms ?? DEFAULT_MS[a.kind] ?? 700);
    fixed += n;
    return { ...a, frames: n };
  });

  let slack = total - fixed;
  if (slack < 0) {
    const scale = total / fixed;
    let acc = 0;
    for (const p of planned) {
      if (p.frames > 0) {
        p.frames = Math.max(1, Math.floor(p.frames * scale));
        acc += p.frames;
      }
    }
    warn(
      `beat "${beat.id}": choreography needs ${(fixed / fps).toFixed(1)}s but narration is ` +
        `${(total / fps).toFixed(1)}s - actions compressed ${(scale * 100).toFixed(0)}%. ` +
        `Trim actions or lengthen the narration.`
    );
    slack = total - acc;
  }

  if (elastic.length) {
    const each = Math.floor(slack / elastic.length);
    elastic.forEach((i, n) => {
      planned[i].frames = Math.max(1, each + (n === 0 ? slack - each * elastic.length : 0));
    });
  } else if (slack > 0) {
    planned.push({ kind: 'dwell', frames: slack });
  }

  return planned;
}

// ---------------------------------------------------------------------------

/*
 * An action marked `optional` degrades to a hold instead of killing the run.
 * Specs are written against a UI that changes under them, and losing a
 * twenty-minute render to one renamed panel is the wrong trade - the warning
 * plus the fit-check stills catch it just as well.
 */
async function tryResolve(rec, page, a, warn) {
  try {
    return await resolveBox(page, a.target);
  } catch (e) {
    if (!a.optional) throw e;
    warn(`optional ${a.kind} skipped - ${String(e.message).split('\n')[0]}`);
    return null;
  }
}

/*
 * `api` support: off-camera calls to the product while the camera holds.
 *
 * The transport is general to RoboLedger. Everything episode-specific (which
 * tenant, which forecast block, which concept, what number) comes from the
 * spec, and there are no defaults for any of it. A default would not fail the
 * render; it would quietly drive one company while filming another, or put a
 * number on camera that nobody authored, in a demo whose entire claim is that
 * the numbers are right.
 */
async function apiSession(ctx) {
  if (ctx._api) return ctx._api;
  if (!ctx.configPath) throw new Error('api action needs --config (no configPath in ctx)');
  const cfg = JSON.parse(await readFile(ctx.configPath, 'utf8'));
  const baseUrl = String(cfg.base_url || ctx.apiBaseUrl || 'http://localhost:8000').replace(/\/$/, '');
  ctx._api = { cfg, baseUrl, configPath: ctx.configPath, auth: null };
  return ctx._api;
}

// Cached on the session: a walkthrough with three api actions should log in once.
async function apiAuth(sess) {
  if (sess.auth) return sess.auth;
  const { cfg } = sess;
  if (cfg.api_key) return (sess.auth = { kind: 'key', value: cfg.api_key });
  if (!cfg.email || !cfg.password) {
    throw new Error(`api needs api_key or email/password in ${sess.configPath}`);
  }
  const res = await fetch(`${sess.baseUrl}/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: cfg.email, password: cfg.password }),
  });
  if (!res.ok) throw new Error(`api login failed: HTTP ${res.status} ${await res.text()}`);
  const body = await res.json();
  const token = body.token || body.access_token || body.accessToken;
  if (!token) throw new Error('api login response missing token');
  return (sess.auth = { kind: 'bearer', value: token });
}

function apiHeaders(auth) {
  const h = { 'Content-Type': 'application/json' };
  if (auth.kind === 'key') h['X-API-Key'] = auth.value;
  else h.Authorization = `Bearer ${auth.value}`;
  return h;
}

/*
 * Which tenant the off-camera calls hit.
 *
 * No default and no first-graph fallback, on purpose. The camera picks its
 * tenant by entity name and the API picks its own by graph id: those are two
 * independent handles on the same thing, and a guess makes them disagree
 * silently. Every spec that uses `api` names its graph.
 */
function apiGraphId(a, ctx, sess) {
  const explicit = a.graph_id || ctx.graphId;
  if (explicit) return explicit;
  const graphs = sess.cfg.graphs || {};
  const keys = Object.keys(graphs).join(', ') || 'none';
  const key = a.graph || ctx.graphKey;
  if (!key) {
    throw new Error(
      'api action needs a graph: set "graph": "<key>" on the spec (or on the action), '
      + `or "graphId" for a literal id. Keys in ${sess.configPath}: ${keys}`
    );
  }
  const id = graphs[key]?.graph_id;
  if (!id) throw new Error(`no graphs.${key}.graph_id in ${sess.configPath} (have: ${keys})`);
  return id;
}

async function apiCall(sess, auth, graphId, { path, method = 'POST', body, label }) {
  const url = `${sess.baseUrl}${path.replace('{graphId}', graphId)}`;
  const res = await fetch(url, {
    method,
    headers: apiHeaders(auth),
    body: body == null ? undefined : JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${label} failed: HTTP ${res.status} ${await res.text()}`);
  return res;
}

/*
 * Resolve a forecast Information Block by exact name, and remember it so a
 * later beat's compute-forecast reuses it instead of asking again.
 *
 * Exact match only: fuzzy matching here would compute a different block than
 * the one just asserted into, and the render would succeed while showing the
 * wrong forecast.
 */
async function apiForecastStructureId(sess, auth, graphId, a, ctx) {
  if (a.structure_id) return a.structure_id;
  const want = a.structure_name;
  const cache = (ctx.forecastStructureIds ||= {});
  if (!want) {
    const only = Object.values(cache);
    if (only.length === 1) return only[0];
    throw new Error('forecast api op needs "structure_name" (or "structure_id") on the action');
  }
  const key = `${graphId}:${want.toLowerCase()}`;
  if (cache[key]) return cache[key];

  const res = await apiCall(sess, auth, graphId, {
    path: '/extensions/{graphId}/graphql',
    body: { query: 'query { informationBlocks(blockType: "forecast") { id name blockType } }' },
    label: 'forecast structure lookup',
  });
  const blocks = (await res.json())?.data?.informationBlocks || [];
  const hit = blocks.find((b) => String(b.name || '').toLowerCase() === want.toLowerCase());
  if (!hit?.id) {
    const found = blocks.map((b) => JSON.stringify(b.name)).join(', ') || 'none';
    throw new Error(`no forecast block named ${JSON.stringify(want)} in graph ${graphId} (found: ${found})`);
  }
  return (cache[key] = hit.id);
}

// Some ops change data the current page already rendered; Refresh re-reads it
// on camera. Never fatal: the beat can still be shot from the stale view.
async function apiClickRefresh(page, warn) {
  for (const loc of [
    page.getByRole('button', { name: /^Refresh$/i }).first(),
    page.locator('button:has-text("Refresh")').first(),
  ]) {
    if (!(await loc.count().catch(() => 0))) continue;
    try {
      await loc.click({ timeout: 3000 });
      await settle(page);
      return;
    } catch (e) {
      warn(`api refresh click skipped - ${String(e.message).split('\n')[0]}`);
      return;
    }
  }
}

/*
 * Dispatch one `api` action. Named ops carry the behaviour worth reusing
 * (structure lookup, refresh-after); `path` is the escape hatch for everything
 * this tool has not been taught yet.
 */
async function runApiAction(page, a, ctx, warn) {
  // Off-camera product ops. Zero frames, because waiting is already off camera.
  const sess = await apiSession(ctx);
  const auth = await apiAuth(sess);
  const graphId = apiGraphId(a, ctx, sess);
  const op = a.op || a.name;
  const where = `graph ${graphId}`;

  if (op === 'promote-obligations') {
    await apiCall(sess, auth, graphId, {
      path: '/extensions/roboledger/{graphId}/operations/promote-obligations',
      body: { dispatch_handlers: true },
      label: op,
    });
    console.log(`  · api promote-obligations ok (${where})`);
    if (a.refresh !== false) await apiClickRefresh(page, warn);
    return;
  }

  if (op === 'update-forecast-assert' || op === 'update-information-block') {
    const structureId = await apiForecastStructureId(sess, auth, graphId, a, ctx);
    const lineAssertions =
      a.line_assertions
      || (a.qname != null && a.value != null ? [{ qname: a.qname, value: Number(a.value) }] : null);
    if (!lineAssertions?.length) {
      throw new Error(`${op} needs "line_assertions", or "qname" + "value", on the action`);
    }
    const payload = { structure_id: structureId, line_assertions: lineAssertions };
    if (a.levers) payload.levers = a.levers;  // full lever replace when the beat supplies it
    await apiCall(sess, auth, graphId, {
      path: '/extensions/roboledger/{graphId}/operations/update-information-block',
      body: { block_type: 'forecast', payload },
      label: op,
    });
    const shown = lineAssertions.map((l) => `${l.qname}=${l.value}`).join(' ');
    console.log(`  · api ${op} ok (${where} ${structureId} ${shown})`);
    if (a.refresh) await apiClickRefresh(page, warn);
    return;
  }

  if (op === 'compute-forecast') {
    const structureId = await apiForecastStructureId(sess, auth, graphId, a, ctx);
    await apiCall(sess, auth, graphId, {
      path: '/extensions/roboledger/{graphId}/operations/compute-forecast',
      body: { structure_id: structureId },
      label: op,
    });
    console.log(`  · api compute-forecast ok (${where} ${structureId})`);
    if (a.refresh) await apiClickRefresh(page, warn);
    return;
  }

  // Escape hatch: a raw call, so the next capability demo can reach a new
  // operation without a change to this tool. `{graphId}` interpolates.
  if (a.path) {
    await apiCall(sess, auth, graphId, {
      path: a.path,
      method: a.method || 'POST',
      body: a.body,
      label: op || `${a.method || 'POST'} ${a.path}`,
    });
    console.log(`  · api ${a.method || 'POST'} ${a.path} ok (${where})`);
    if (a.refresh) await apiClickRefresh(page, warn);
    return;
  }

  throw new Error(
    `unknown api op ${JSON.stringify(op)}. Known: promote-obligations, `
    + 'update-forecast-assert, compute-forecast. Or give "path" for a raw call.'
  );
}

async function runAction(rec, page, baseUrl, a, warn, ctx = {}) {
  switch (a.kind) {
    case 'goto': {
      await page.goto(`${baseUrl}${a.route}`, { waitUntil: 'domcontentloaded' });
      await settle(page);
      // A camera rect from the previous page points at nothing on this one, so
      // navigation returns to the full frame unless the spec insists otherwise.
      if (!a.keepZoom) rec.cam = { cx: rec.W / 2, cy: rec.H / 2, z: 1 };
      await rec.syncCursor();
      await rec.hold(a.frames);
      break;
    }
    case 'wait': {
      if (a.selector) await page.waitForSelector(a.selector, { timeout: a.timeout || 20000 });
      await settle(page);
      break;
    }
    case 'move':
    case 'hover': {
      const box = await tryResolve(rec, page, a, warn);
      if (!box) return rec.hold(a.frames);
      if (box.locator) {
        await box.locator.scrollIntoViewIfNeeded().catch(() => {});
        const fresh = await box.locator.boundingBox().catch(() => null);
        if (fresh) {
          const off = (targetSpec(a.target).offset || [0, 0]);
          box.point = { x: fresh.x + fresh.width / 2 + (off[0] || 0), y: fresh.y + fresh.height / 2 + (off[1] || 0) };
        }
      }
      await rec.move(box.point, a.frames);
      if (a.kind === 'hover') await settle(page, { quietMs: 0, timeout: 2000 });
      break;
    }
    case 'click': {
      if (a.target) {
        const box = await tryResolve(rec, page, a, warn);
        if (!box) return rec.hold(a.frames);
        // Off-screen controls (e.g. Close Period under Draft review) must be
        // brought into the viewport or the drawn cursor clicks empty space.
        if (box.locator) {
          await box.locator.scrollIntoViewIfNeeded().catch(() => {});
          const fresh = await box.locator.boundingBox().catch(() => null);
          if (fresh) {
            box.point = {
              x: fresh.x + fresh.width / 2 + ((targetSpec(a.target).offset || [0, 0])[0] || 0),
              y: fresh.y + fresh.height / 2 + ((targetSpec(a.target).offset || [0, 0])[1] || 0),
            };
          }
        }
        const moveF = Math.max(1, Math.round(a.frames * 0.45));
        await rec.move(box.point, moveF);
        await rec.click(a.frames - moveF, { button: a.button });
      } else {
        await rec.click(a.frames, { button: a.button });
      }
      // The consequence of the click settles between frames, so the cut lands
      // on a finished UI rather than a spinner.
      await settle(page);
      await rec.syncCursor();
      break;
    }
    case 'scroll': {
      try {
        await rec.scrollTo(a.target, a.frames, a.block || 'center');
      } catch (e) {
        if (!a.optional) throw e;
        warn(`optional scroll skipped - ${String(e.message).split('\n')[0]}`);
        await rec.hold(a.frames);
      }
      break;
    }
    case 'zoom': {
      if (a.target == null) { await rec.zoomTo('reset', a.frames, a.padding); break; }
      const box = await tryResolve(rec, page, a, warn);
      if (!box) return rec.hold(a.frames);
      await rec.zoomTo(a.target, a.frames, a.padding, box);
      break;
    }
    case 'type':
      await rec.type(a.text || '', a.frames);
      break;
    case 'key':
      await page.keyboard.press(a.key);
      await settle(page);
      await rec.hold(a.frames);
      break;
    case 'dwell':
      await rec.hold(a.frames);
      break;
    case 'select': {
      // Native <select> by label/value. Visible move + settle so the grid change
      // lands on camera after the option flips.
      const box = await tryResolve(rec, page, a, warn);
      if (!box) return rec.hold(a.frames);
      const moveF = Math.max(1, Math.min(Math.round(a.frames * 0.35), Math.max(1, a.frames - 1)));
      await rec.move(box.point, moveF);
      const t = targetSpec(a.target);
      let loc = page.locator(t.selector);
      if (t.nth != null) loc = loc.nth(t.nth);
      else loc = loc.first();
      const opt = a.value ?? a.label ?? a.option;
      if (opt == null) throw new Error('select action requires value, label, or option');
      try {
        if (a.label != null || (a.value == null && a.option != null)) {
          await loc.selectOption({ label: String(a.label ?? a.option) });
        } else {
          await loc.selectOption(String(opt));
        }
      } catch (e) {
        if (!a.optional) throw e;
        warn(`optional select skipped - ${String(e.message).split('\n')[0]}`);
      }
      await settle(page);
      await rec.syncCursor();
      await rec.hold(Math.max(0, a.frames - moveF));
      break;
    }
    case 'overlay': {
      // Fixed bottom-right chat bubble (human ask / agent reply) — must land in frames.
      const role = String(a.role || 'human').toLowerCase();
      const label = role === 'agent' ? 'Agent' : 'You';
      const accent = role === 'agent' ? '#00D1B2' : '#8B5CF6';
      const text = String(a.text || '');
      await page.evaluate(({ label, accent, text, role }) => {
        let root = document.getElementById('rs-demo-chat-overlay');
        if (!root) {
          root = document.createElement('div');
          root.id = 'rs-demo-chat-overlay';
          root.style.cssText = [
            'position:fixed', 'right:28px', 'bottom:28px', 'z-index:2147483646',
            'max-width:420px', 'pointer-events:none', 'font-family:Inter,system-ui,sans-serif',
          ].join(';');
          document.documentElement.appendChild(root);
        }
        root.innerHTML = '';
        const bubble = document.createElement('div');
        bubble.setAttribute('data-rs-overlay-role', role);
        bubble.style.cssText = [
          'background:rgba(17,24,39,0.94)', 'color:#F9FAFB', 'border:1px solid rgba(255,255,255,0.12)',
          'border-radius:14px', 'padding:14px 16px', 'box-shadow:0 12px 40px rgba(0,0,0,0.45)',
          'backdrop-filter:blur(8px)',
        ].join(';');
        const head = document.createElement('div');
        head.style.cssText = `font-size:11px;font-weight:600;letter-spacing:0.04em;text-transform:uppercase;color:${accent};margin-bottom:6px`;
        head.textContent = label;
        const body = document.createElement('div');
        body.style.cssText = 'font-size:15px;line-height:1.45;color:#E5E7EB';
        body.textContent = text;
        bubble.appendChild(head);
        bubble.appendChild(body);
        root.appendChild(bubble);
      }, { label, accent, text, role });
      await rec.syncCursor();
      await rec.hold(a.frames);
      break;
    }
    case 'overlay-clear': {
      await page.evaluate(() => {
        const root = document.getElementById('rs-demo-chat-overlay');
        if (root) root.remove();
      });
      await rec.hold(a.frames);
      break;
    }
    case 'api': {
      try {
        await runApiAction(page, a, ctx, warn);
      } catch (e) {
        if (!a.optional) throw e;
        warn(`optional api ${a.op || a.name || a.path} skipped - ${String(e.message).split('\n')[0]}`);
      }
      break;
    }
    default:
      warn(`unknown action kind "${a.kind}" - held for ${a.frames} frames`);
      await rec.hold(a.frames);
  }
}

export async function demo(args) {
  if (!args.spec) throw new Error('demo requires --spec <file.json>');
  const specPath = path.resolve(args.spec);
  const spec = JSON.parse(await readFile(specPath, 'utf8'));
  const specDir = path.dirname(specPath);

  const W = spec.width || 1920;
  const H = spec.height || 1080;
  const fps = spec.fps || 30;
  const dsf = Number(args.dsf || spec.deviceScaleFactor || 2);
  // Beyond the device scale factor a zoom would be upsampled, which is exactly
  // the softness this renderer exists to avoid.
  const maxZoom = Math.min(Number(args['max-zoom'] || spec.maxZoom || 2), dsf);
  const baseUrl = (args['base-url'] || spec.baseUrl || 'http://localhost:3001').replace(/\/$/, '');
  const theme = String(args.theme || spec.theme || 'dark');
  const entity = args.entity || spec.entity || null;

  const stills = Boolean(args.stills);
  const outDir = args.out ? path.resolve(args.out) : path.join(specDir, 'renders');
  const framesDir = stills
    ? path.join(outDir, `stills_${spec.slug || 'demo'}`)
    : path.join(outDir, `frames_${spec.slug || 'demo'}`);
  const outFile = path.join(outDir, `${spec.slug || 'demo'}.mp4`);
  await rm(framesDir, { recursive: true, force: true });
  await mkdir(framesDir, { recursive: true });

  const warnings = [];
  const warn = (m) => { warnings.push(m); console.warn(`  ! ${m}`); };

  const beats = spec.beats || [];
  if (!beats.length) throw new Error(`${path.basename(specPath)} has no beats`);
  const untimed = beats.filter((b) => !b.durationMs);
  if (untimed.length && !stills) {
    warn(
      `${untimed.length}/${beats.length} beats have no durationMs - falling back to 3s each. ` +
        `Run "just demo-narrate ${path.relative(process.cwd(), specPath)}" first so voiceover owns the clock.`
    );
  }

  const { email, password } = await resolveCreds({ ...args, config: args.config || spec.config });
  const browser = await chromium.launch({ headless: !args.headed });
  try {
    const context = await newThemedContext(browser, { width: W, height: H, deviceScaleFactor: dsf, theme });
    await context.addInitScript(installCursor, { size: spec.cursorSize || 30, accent: spec.accent || '#00D1B2' });
    const page = await context.newPage();

    await login(page, baseUrl, { email, password });
    console.log(`✓ authenticated  (theme: ${theme}, ${W}x${H}@${dsf}x, zoom cap ${maxZoom}x)`);
    if (entity) console.log(`✓ entity → ${await switchEntity(page, entity)}`);

    const rec = new Recorder(page, { W, H, fps, dsf, maxZoom, framesDir, stills });

    if (stills) {
      console.log(`  fit-check: ${beats.length} beats, one still each\n`);
    } else {
      const totalSec = beats.reduce((s, b) => s + (b.durationMs || 3000), 0) / 1000;
      console.log(`  ${beats.length} beats ≈ ${totalSec.toFixed(1)}s @ ${fps}fps\n`);
    }

    // One ctx for the whole run, not one per beat. `api` actions hand state to
    // each other through it: a resolved forecast structure id, and the login.
    // The shipping spec happens to keep both forecast ops inside one beat, so
    // per-beat rebuilding worked by luck; a spec that splits them across beats
    // would re-login and re-resolve every time.
    const actionCtx = {
      configPath: args.config || spec.config || null,
      apiBaseUrl: args['api-base'] || spec.apiBaseUrl || null,
      // Which tenant `api` actions drive. Named per spec, never guessed.
      graphKey: args.graph || spec.graph || null,
      graphId: args['graph-id'] || spec.graphId || null,
      entity,
    };

    for (const [i, beat] of beats.entries()) {
      const planned = planBeat(beat, fps, warn, stills);
      const at = rec.frame;
      for (const a of planned) await runAction(rec, page, baseUrl, a, warn, actionCtx);

      if (stills) {
        const name = `${String(i).padStart(2, '0')}_${String(beat.id || 'beat').replace(/\W+/g, '-')}`;
        await rec.shootStill(name);
        console.log(`  ✓ ${name.padEnd(26)} zoom ${rec.cam.z.toFixed(2)}x  ${planned.length} actions`);
        continue;
      }

      const got = rec.frame - at;
      const want = Math.max(1, Math.round(((beat.durationMs || 3000) / 1000) * fps));
      // Trailing pad keeps every beat on its narration to the frame.
      if (got < want) await rec.hold(want - got);
      console.log(
        `  ✓ ${String(beat.id).padEnd(18)} ${(want / fps).toFixed(1)}s  ` +
          `${planned.length} actions${got !== want ? `  (padded ${want - got}f)` : ''}`
      );
    }

    await rec.flush();

    if (stills) {
      console.log(`\n✓ ${path.relative(process.cwd(), framesDir)}/  (${(await readdir(framesDir)).length} stills)`);
      console.log('  Check every zoom actually frames what the narration talks about, then render.');
    } else {
      await framesToMp4({ framePattern: path.join(framesDir, 'frame-%05d.png'), fps, out: outFile });
      console.log(`\n✓ ${path.relative(process.cwd(), outFile)}  (${(rec.frame / fps).toFixed(1)}s silent)`);
      console.log(`  mux the voiceover:  just demo-mux ${path.relative(process.cwd(), specPath)}`);
      if (!args['keep-frames']) await rm(framesDir, { recursive: true, force: true });
      else console.log(`  frames kept → ${path.relative(process.cwd(), framesDir)}/ (${(await readdir(framesDir)).length})`);
    }
    if (warnings.length) console.log(`\n  ${warnings.length} warning(s) above.`);
  } finally {
    await browser.close();
  }
}
