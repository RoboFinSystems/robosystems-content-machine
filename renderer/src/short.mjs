/*
 * short — render a 9:16 motion spec to a silent mp4 by mounting the real
 * design-system components in a headless browser and shooting one screenshot
 * per frame. Frame-accurate and deterministic: the page exposes
 * window.__renderFrame(i) and we drive it frame-by-frame (no wall-clock), so
 * the same spec always yields the identical video. Audio (VO/music) is muxed
 * downstream by the Python pipeline.
 *
 * Two brands of scene:
 *   - research (spec.brand === 'research') — the footage-free teaser short
 *     (navy+teal ground, persistent wordmark chrome). Archetypes mirror the
 *     retired Pillow renderer: bignum / statpair / identity / cta / alert /
 *     hook / headline / question. Python classifies card text → these.
 *   - showcase (default) — the demo series: DS-token `hero` / `metrics` scenes
 *     mounting the real MetricCard component.
 */
import { chromium } from 'playwright';
import { readFile, mkdir, rm, readdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { serve } from './server.mjs';
import { framesToMp4 } from './ffmpeg.mjs';

const rendererRoot = fileURLToPath(new URL('..', import.meta.url)); // renderer/
const dsDir = path.join(rendererRoot, '..', 'design-system');
const brandDir = path.join(rendererRoot, '..', 'assets', 'brand');

// The in-page timeline + scene renderers. Each scene animates its entrance over
// the first `entranceMs` (default 550) then holds — matching the Pillow model —
// and the first scene opens ~75% settled so the feed poster frame reads.
const IN_PAGE = /* js */ `
const SPEC = __SPEC__;
const NS = window.RoboSystemsContentDesignSystem_746ae7 || {};
const h = React.createElement;
const container = document.getElementById('root');
const RESEARCH = SPEC.brand === 'research';

const clamp01 = (x) => Math.max(0, Math.min(1, x));
const lerp = (a, b, t) => a + (b - a) * t;
const eo = (t) => 1 - Math.pow(1 - clamp01(t), 3);           // ease-out cubic
const eob = (t) => { t = clamp01(t); const c1 = 1.70158, c3 = 2.70158; return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2); };

const P = {
  teal: '#00D1B2', alert: '#EE6C4D', white: '#FFFFFF', muted: '#96AACA', chrome: '#788CB0',
};

function parseNum(str) {
  const s = String(str).replace('−', '-');
  const m = s.match(/-?\\d[\\d,]*(?:\\.\\d+)?/);
  if (!m) return { prefix: s, value: 0, suffix: '', decimals: 0, comma: false, ok: false };
  const core = m[0];
  return { prefix: s.slice(0, m.index), value: parseFloat(core.replace(/,/g, '')),
    suffix: s.slice(m.index + core.length), decimals: core.includes('.') ? core.split('.')[1].length : 0,
    comma: core.includes(','), ok: true };
}
function fmtNum(p, v, s, dec, comma) {
  const body = (comma || v >= 1000) ? v.toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec }) : v.toFixed(dec);
  return p + body + s;
}
// tint any whitespace token containing a digit with the accent (the data is the hero)
function emph(text, base, accent) {
  return String(text).split(' ').map((tok, i) =>
    h('span', { key: i, style: { color: /\\d/.test(tok) ? accent : base } }, (i ? ' ' : '') + tok));
}
// crude fit: shrink font as text gets longer so long lines don't overflow the 1080 stage
const fit = (text, big, mid, small) => (String(text).length > 30 ? small : String(text).length > 16 ? mid : big);

const stage = { position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column',
  alignItems: 'center', justifyContent: 'center', gap: '30px', padding: '0 90px', textAlign: 'center' };
const bar = (color) => h('div', { style: { width: '150px', height: '10px', borderRadius: '5px', background: color, margin: '0 auto' } });
const eyebrow = (txt, color) => h('div', { style: { fontFamily: '"Space Grotesk"', fontSize: '52px', fontWeight: 500, letterSpacing: '0.06em', textTransform: 'uppercase', color } }, txt);

function slam(te) { const e = eob(te); return { transform: 'scale(' + lerp(1.10, 1.0, e) + ')', opacity: clamp01(te * 1.7) }; }
function rise(te) { const e = eo(te); return { transform: 'translateY(' + lerp(70, 0, e) + 'px)', opacity: clamp01(te * 1.6) }; }

// ---- research archetypes ----
function Bignum(s, te) {
  const n = parseNum(s.number);
  const shown = fmtNum(n.prefix, n.value * eo(clamp01(te / 0.8)), n.suffix, n.decimals, n.comma);
  const wipe = eo(clamp01((te - 0.45) / 0.55));
  return h('div', { style: stage },
    h('div', { style: { fontFamily: '"Space Grotesk"', fontWeight: 700, fontSize: '230px', lineHeight: 1, color: P.white } }, shown),
    h('div', { style: { width: (60 + 300 * wipe) + 'px', height: '14px', borderRadius: '7px', background: P.teal, opacity: te > 0.35 ? 1 : 0 } }),
    s.label && h('div', { style: { fontFamily: '"Space Grotesk"', fontSize: '56px', fontWeight: 500, letterSpacing: '0.05em', textTransform: 'uppercase', color: P.muted, opacity: clamp01((te - 0.35) / 0.4) } }, s.label));
}
function Statpair(s, te) {
  const a = clamp01(te / 0.55), b = clamp01((te - 0.35) / 0.55);
  const line = (txt) => h('div', { style: { fontFamily: '"Space Grotesk"', fontWeight: 700, fontSize: fit(txt, 96, 84, 68) + 'px', lineHeight: 1.05, color: P.white } }, emph(txt.toUpperCase(), P.white, P.teal));
  return h('div', { style: stage },
    h('div', { style: { opacity: a } }, line(s.a)),
    h('div', { style: { width: '16px', height: '16px', borderRadius: '50%', background: P.teal, opacity: b } }),
    h('div', { style: { opacity: b } }, line(s.b)));
}
function Identity(s, te) {
  const ca = clamp01((te - 0.4) / 0.5);
  return h('div', { style: { ...stage, ...rise(te) } },
    h('div', { style: { fontFamily: '"Orbitron"', fontWeight: 700, fontSize: fit(s.company, 104, 84, 60) + 'px', lineHeight: 1.05, letterSpacing: '0.02em', color: P.white } }, s.company.toUpperCase()),
    h('div', { style: { fontFamily: '"Space Grotesk"', fontWeight: 600, fontSize: '56px', color: P.white, border: '4px solid ' + P.teal, borderRadius: '18px', padding: '22px 44px', opacity: ca } }, s.exchange + ': ' + s.ticker));
}
function Cta(s, te) {
  return h('div', { style: { ...stage, ...rise(te) } },
    h('div', { style: { fontFamily: '"Space Grotesk"', fontWeight: 700, fontSize: fit(s.line, 100, 84, 62) + 'px', lineHeight: 1.06, color: P.white } }, emph(s.line.toUpperCase(), P.white, P.teal)),
    bar(P.teal),
    s.secondary && h('div', { style: { fontFamily: '"Space Grotesk"', fontSize: '44px', color: P.muted } }, s.secondary),
    s.handle && h('div', { style: { fontFamily: '"Orbitron"', fontWeight: 700, fontSize: '40px', letterSpacing: '0.08em', color: P.teal } }, s.handle));
}
function Alert(s, te) {
  const txt = String(s.text).toUpperCase().replace(/^[\\u2026. ]+/, '');
  return h('div', { style: { ...stage, ...slam(te) } },
    bar(P.alert),
    h('div', { style: { fontFamily: '"Space Grotesk"', fontWeight: 700, fontSize: fit(txt, 100, 84, 64) + 'px', lineHeight: 1.06, color: P.alert } }, txt));
}
function BoldText(s, te, entrance) {
  const txt = String(s.text).toUpperCase();
  const claude = /CLAUDE/.test(txt);
  return h('div', { style: { ...stage, ...entrance(te) } },
    claude && h('img', { src: '/brand/claude.png', style: { height: '170px', objectFit: 'contain' } }),
    entrance === slam && !claude && bar(P.teal),
    h('div', { style: { fontFamily: '"Space Grotesk"', fontWeight: 700, fontSize: fit(txt, 100, 84, 64) + 'px', lineHeight: 1.06, color: P.white } }, emph(txt, P.white, P.teal)));
}

// ---- showcase (DS tokens) ----
const cCenter = { position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '30px', padding: '0 90px', textAlign: 'center' };
const dsEyebrow = { fontFamily: 'var(--font-display,"Orbitron")', fontSize: '26px', letterSpacing: '0.22em', textTransform: 'uppercase', color: 'var(--text-muted,#9aa4bf)', fontWeight: 700 };
const dsTone = (t) => ({ positive: 'var(--data-positive,#3fd08a)', negative: 'var(--data-negative,#ff6b6b)', warning: 'var(--data-warning,#ffb454)', accent: 'var(--accent,#7c5cff)' }[t] || 'var(--text-primary,#fff)');
function FallbackCard({ label, value, change, changeTone = 'positive', highlight }) {
  return h('div', { style: { background: 'var(--surface-card,#141a2e)', border: '1px solid ' + (highlight ? 'var(--accent,#7c5cff)' : 'var(--border-hairline,#232a42)'), borderRadius: 'var(--radius-lg,18px)', padding: '34px', display: 'flex', flexDirection: 'column', gap: '10px' } },
    h('span', { style: { fontFamily: 'var(--font-body)', fontSize: '26px', color: 'var(--text-muted,#9aa4bf)', fontWeight: 500 } }, label),
    h('span', { style: { fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: '72px', lineHeight: 1, color: highlight ? 'var(--accent,#7c5cff)' : 'var(--text-primary,#fff)' } }, value),
    change != null && h('span', { style: { fontFamily: 'var(--font-mono)', fontSize: '26px', color: dsTone(changeTone), fontWeight: 500 } }, change));
}
const Card = NS.MetricCard || FallbackCard;
function ShowcaseHero(s, te) {
  let disp = null;
  if (s.value != null) {
    const v = s.value * eo(clamp01(te));
    disp = s.format === 'currency'
      ? new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(v)
      : new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(v);
    disp = (s.prefix || '') + disp + (s.suffix || '');
  }
  return h('div', { style: { ...cCenter, ...rise(te) } },
    s.eyebrow && h('div', { style: dsEyebrow }, s.eyebrow),
    disp != null ? h('div', { style: { fontFamily: 'var(--font-display,"Orbitron")', fontWeight: 800, fontSize: '150px', lineHeight: 1, color: dsTone(s.tone) } }, disp)
      : h('div', { style: { fontFamily: 'var(--font-display,"Orbitron")', fontWeight: 800, fontSize: '92px', lineHeight: 1.04, color: 'var(--text-primary,#fff)' } }, s.title),
    s.subline && h('div', { style: { fontFamily: 'var(--font-body,"Space Grotesk")', fontSize: '34px', color: 'var(--text-muted,#9aa4bf)', fontWeight: 500, maxWidth: '840px' } }, s.subline));
}
function ShowcaseMetrics(s, te) {
  return h('div', { style: { ...cCenter, gap: '36px' } },
    s.heading && h('div', { style: dsEyebrow }, s.heading),
    h('div', { style: { display: 'flex', flexDirection: 'column', gap: '26px', width: '100%' } },
      (s.cards || []).map((c, i) => {
        const e = eo(clamp01((te - i * 0.12) / 0.5));
        return h('div', { key: i, style: { opacity: e, transform: 'translateY(' + (1 - e) * 22 + 'px)' } },
          h(Card, { label: c.label, value: c.value, change: c.change, changeTone: c.changeTone, highlight: c.highlight }));
      })));
}

// A full-bleed UI capture (from the capture mode) with a slow Ken-Burns zoom
// and an optional lower-third caption — the hybrid demo cutaway. Uses tp
// (whole-scene progress) for the drift, te (entrance) for the fade.
function ImageScene(s, te, tp) {
  const scale = 1.02 + 0.06 * tp;
  return h('div', { style: { position: 'absolute', inset: 0, overflow: 'hidden', opacity: clamp01(te * 1.6) } },
    h('img', { src: s.src, style: { position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover', transform: 'scale(' + scale + ')', transformOrigin: '50% 42%' } }),
    h('div', { style: { position: 'absolute', inset: 0, background: 'linear-gradient(rgba(6,16,38,0) 55%, rgba(6,16,38,0.85))' } }),
    s.caption && h('div', { style: { position: 'absolute', left: 0, right: 0, bottom: '80px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px', ...rise(te) } },
      h('div', { style: { width: '110px', height: '8px', borderRadius: '4px', background: P.teal } }),
      h('div', { style: { fontFamily: '"Space Grotesk"', fontWeight: 600, fontSize: '46px', color: P.white, textAlign: 'center', padding: '0 90px' } }, s.caption)));
}

function renderScene(sc, te, tp) {
  switch (sc.kind) {
    case 'image': return ImageScene(sc, te, tp);
    case 'bignum': return Bignum(sc, te);
    case 'statpair': return Statpair(sc, te);
    case 'identity': return Identity(sc, te);
    case 'cta': return Cta(sc, te);
    case 'alert': return Alert(sc, te);
    case 'question': return BoldText(sc, te, rise);
    case 'headline': return BoldText(sc, te, slam);
    case 'hook': return BoldText(sc, te, slam);
    case 'metrics': return ShowcaseMetrics(sc, te);
    case 'hero': return ShowcaseHero(sc, te);
    default: return BoldText(sc, te, slam);
  }
}

const FPS = SPEC.fps || 30;
let acc = 0;
const scenes = (SPEC.scenes || []).map((s, i) => {
  const frames = Math.max(1, Math.round(((s.durationMs || 2000) / 1000) * FPS));
  const entF = Math.max(1, Math.round(((s.entranceMs || 550) / 1000) * FPS));
  const start = acc; acc += frames;
  return { ...s, _i: i, _start: start, _frames: frames, _end: acc, _entF: entF };
});
window.__total = acc;
window.__renderFrame = (i) => {
  const sc = scenes.find((s) => i >= s._start && i < s._end) || scenes[scenes.length - 1];
  const local = i - sc._start;
  const offset = sc._i === 0 ? 0.75 * sc._entF : 0; // first scene opens settled (poster frame)
  const te = clamp01((local + offset) / sc._entF);
  const tp = sc._frames <= 1 ? 1 : clamp01(local / (sc._frames - 1)); // whole-scene progress (Ken Burns)
  const ch = document.getElementById('chrome'); // hide wordmark over full-bleed UI shots
  if (ch) ch.style.opacity = sc.kind === 'image' ? '0' : '1';
  ReactDOM.render(renderScene(sc, te, tp), container);
};
window.__renderFrame(0);
`;

function buildHtml(spec) {
  const [W, H] = [spec.width || 1080, spec.height || 1920];
  const research = spec.brand === 'research';
  const bg = research
    ? 'background:radial-gradient(1120px 900px at 50% 46%, rgba(0,209,178,0.10), rgba(0,0,0,0) 60%), linear-gradient(#112B5C, #061026);'
    : 'background:var(--surface-base,#0a0e18);';
  const chrome = research
    ? `<div id="chrome" style="position:absolute;top:30px;left:0;right:0;display:flex;flex-direction:column;align-items:center;gap:14px;z-index:2;transition:none">
         <img src="/brand/robosystems_mark.png" style="height:58px;opacity:.6"/>
         <div style="font-family:'Orbitron';font-weight:700;font-size:26px;letter-spacing:.35em;color:#788CB0">ROBOSYSTEMS</div>
       </div>` : '';
  return `<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="/ds/tokens/colors.css">
<link rel="stylesheet" href="/ds/tokens/semantic.css">
<link rel="stylesheet" href="/ds/tokens/typography.css">
<link rel="stylesheet" href="/ds/tokens/spacing.css">
<link rel="stylesheet" href="/ds/tokens/effects.css">
<link rel="stylesheet" href="/ds/fonts.css">
<style>
  html,body{margin:0;padding:0;background:#000}*{box-sizing:border-box}
  #stage{position:relative;width:${W}px;height:${H}px;overflow:hidden;${bg}color:var(--text-primary,#fff)}
  #root{position:absolute;inset:0;z-index:1}
</style></head><body>
<div id="stage">${chrome}<div id="root"></div></div>
<script src="/react/react.production.min.js"></script>
<script src="/react-dom/react-dom.production.min.js"></script>
<script src="/ds/_ds_bundle.js"></script>
<script>${IN_PAGE.replace('__SPEC__', JSON.stringify(spec))}</script>
</body></html>`;
}

export async function short(args) {
  if (!args.spec) throw new Error('short requires --spec <file.json>');
  const spec = JSON.parse(await readFile(path.resolve(args.spec), 'utf8'));
  const W = spec.width || 1080;
  const H = spec.height || 1920;
  const fps = spec.fps || 30;

  const outDir = args.out ? path.resolve(args.out) : path.join(rendererRoot, 'out');
  const framesDir = path.join(outDir, 'frames');
  const outFile = path.join(outDir, `${spec.slug || 'short'}.mp4`);
  await rm(framesDir, { recursive: true, force: true });
  await mkdir(framesDir, { recursive: true });

  const server = await serve({
    html: buildHtml(spec),
    mounts: {
      '/ds/': dsDir,
      '/brand/': brandDir,
      '/cap/': path.join(rendererRoot, 'out', 'capture'), // UI capture stills for `image` scenes
      '/react/': path.join(rendererRoot, 'node_modules/react/umd'),
      '/react-dom/': path.join(rendererRoot, 'node_modules/react-dom/umd'),
    },
  });

  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
    await page.goto(server.url, { waitUntil: 'networkidle' });
    await page.evaluate(() => document.fonts.ready);

    const usingReal = await page.evaluate(
      () => typeof (window.RoboSystemsContentDesignSystem_746ae7 || {}).MetricCard === 'function'
    );
    console.log(`  brand: ${spec.brand || 'showcase'}${spec.brand === 'research' ? '' : `, MetricCard: ${usingReal ? 'real DS' : 'fallback'}`}`);

    const total = await page.evaluate(() => window.__total);
    console.log(`  rendering ${total} frames @ ${fps}fps (${W}x${H}) ≈ ${(total / fps).toFixed(1)}s`);
    for (let i = 0; i < total; i++) {
      await page.evaluate(
        (n) => new Promise((r) => { window.__renderFrame(n); requestAnimationFrame(() => requestAnimationFrame(r)); }),
        i
      );
      await page.screenshot({ path: path.join(framesDir, `frame-${String(i).padStart(5, '0')}.png`) });
    }

    await framesToMp4({ framePattern: path.join(framesDir, 'frame-%05d.png'), fps, out: outFile });
    console.log(`\n✓ ${path.relative(process.cwd(), outFile)}  (silent visual track — mux VO/music in the Python pipeline)`);

    if (!args['keep-frames']) await rm(framesDir, { recursive: true, force: true });
    else console.log(`  frames kept → ${path.relative(process.cwd(), framesDir)}/ (${(await readdir(framesDir)).length})`);
  } finally {
    await browser.close();
    await server.close();
  }
}
