/*
 * post - social stills and carousels from a spec: one PNG per slide at post size
 * (1080x1350 by default, LinkedIn's 4:5 portrait) and, for more than one slide, a
 * PDF carousel of the same pages (LinkedIn's document post).
 *
 *   rs-render post --spec drafts/posts/<slug>.post.json [--out DIR] [--dsf 2] [--no-pdf]
 *
 * A slide is a native card (type sized for a phone feed) built here, so the video
 * templates keep their 16:9 layout. A chart or product shot inside a card is a
 * `visual`: a motion template (motion/: research bars, counters, board, flow; slide
 * number, compare, still) posed at its finished frame and cropped to its content,
 * or an image file (a product capture from `capture`). Every word and number comes
 * from the spec; nothing is generated. Spec shape: renderer/README.md, "post".
 */
import { chromium } from 'playwright';
import { mkdir, readFile, rm } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { serve } from './server.mjs';

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const HOME = process.env.HOME || '';

const PUBLIC = {
  robosystems: process.env.ROBOSYSTEMS_PUBLIC || path.join(HOME, 'Projects/robosystems-app/public'),
  roboledger: process.env.ROBOLEDGER_PUBLIC || path.join(HOME, 'Projects/roboledger-app/public'),
};

// Post-sized type for the research kinds: the video layout is 1920 wide and reads
// small once a 4:5 card scales it down, so a chart in a post gets a narrower body and
// bigger labels. Only the card's copy of the shot changes; the video templates don't.
// A spec's visual.css is appended after these, for one-off fixes.
const POST_CSS = {
  bars: `.bars { width: 1000px; gap: 40px; } .lb { font-size: 46px; } .lb small { font-size: 32px; }
    .tk { height: 70px; margin-top: 14px; } .vl { font: 700 50px/70px var(--mono); margin-top: -35px; }
    .tg { font-size: 34px; line-height: 64px; margin-top: -32px; }`,
  counters: `.ct { width: 420px; } .cn { font-size: 128px; } .cl { font-size: 38px; }`,
  board: `.bd2 { width: 1100px; } .rl { width: 420px; font-size: 42px; } .rt { width: 380px; height: 44px; } .rw b { font-size: 44px; }`,
  flow: `.nt { font-size: 44px; } .ns { font-size: 32px; }`,
};

// The motion template a visual uses decides whose landing kit it mounts.
const TEMPLATE_BRAND = { research: 'robosystems', slide: 'roboledger', intro: 'roboledger', outro: 'roboledger' };

const BRANDS = {
  robosystems: {
    logo: '/images/logos/robosystems.png',
    vars: `--bg:#04070c; --ink:#f3f6fb; --muted:#9aa3b2; --line:#1f2937;
      --a1:#22D3EE; --a2:#6098FA; --a3:#818CF8; --eyebrow:#67E8F9;
      --wash: linear-gradient(135deg, rgba(8,145,178,.20), rgba(37,99,235,.11) 50%, rgba(99,102,241,.17));`,
  },
  roboledger: {
    logo: '/images/logos/roboledger.png',
    vars: `--bg:#07060b; --ink:#f4f2fb; --muted:#9b97ad; --line:#27233a;
      --a1:#A78BFA; --a2:#8B5CF6; --a3:#D946EF; --eyebrow:#C4B5FD;
      --wash: linear-gradient(135deg, rgba(76,29,149,.22), rgba(88,28,135,.14) 50%, rgba(112,26,117,.16));`,
  },
};

const esc = (s) =>
  String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);

function cardCss(brand, W, H) {
  return `
@font-face { font-family: 'Space Grotesk'; src: url('/fonts/SpaceGrotesk/SpaceGrotesk-VariableFont_wght.ttf') format('truetype'); font-weight: 300 700; }
@font-face { font-family: 'Orbitron'; src: url('/fonts/Orbitron/Orbitron-VariableFont_wght.ttf') format('truetype'); font-weight: 400 900; }
:root { ${BRANDS[brand].vars} --display: 'Orbitron', 'Space Grotesk', sans-serif; --body: 'Space Grotesk', system-ui, sans-serif;
  --mono: ui-monospace, SFMono-Regular, Menlo, monospace; }
* { box-sizing: border-box; margin: 0; }
html, body { background: #000; }
.card { position: relative; width: ${W}px; height: ${H}px; overflow: hidden; background: var(--bg); color: var(--ink);
  font-family: var(--body); display: flex; flex-direction: column; padding: 76px 72px 64px; }
.card::before { content: ''; position: absolute; inset: 0; background: var(--wash); }
.card::after { content: ''; position: absolute; inset: 0; opacity: .06;
  background-image: linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px); background-size: 54px 54px; }
.card > * { position: relative; z-index: 1; }
.top { display: flex; align-items: center; justify-content: space-between; min-height: 34px; }
.eyebrow { font: 600 25px var(--display); letter-spacing: .26em; text-transform: uppercase; color: var(--eyebrow); }
.count { font: 500 24px var(--mono); color: var(--muted); }
.title { font: 700 66px/1.08 var(--body); letter-spacing: -.01em; margin-top: 34px; }
.cover .title { font-size: 92px; margin-top: auto; }
.sub { font-size: 38px; line-height: 1.3; color: #cfd5df; margin-top: 30px; }
.rule { height: 5px; width: 220px; border-radius: 3px; margin-top: 40px; background: linear-gradient(90deg, var(--a1), var(--a3)); }
.visual { flex: 1; min-height: 0; margin-top: 40px; display: flex; align-items: center; justify-content: center; }
.visual img { max-width: 100%; max-height: 100%; object-fit: contain; display: block; }
.visual.shot img { width: 100%; height: auto; border-radius: 14px; border: 1px solid var(--line); box-shadow: 0 24px 60px rgba(0,0,0,.5); }
.caption { font-size: 32px; line-height: 1.3; color: #d6dbe4; margin-top: 30px; }
.big { font: 800 196px/1 var(--display); margin-top: auto; font-variant-numeric: tabular-nums;
  background: linear-gradient(90deg, var(--a1), var(--a2) 50%, var(--a3)); -webkit-background-clip: text; background-clip: text; color: transparent; }
.label { font: 600 46px/1.2 var(--body); margin-top: 34px; }
.text { font: 500 50px/1.3 var(--body); margin-top: auto; }
.url { font: 600 40px var(--mono); margin-top: 40px; color: var(--a1); }
.foot { display: flex; align-items: center; justify-content: space-between; gap: 30px; margin-top: auto; padding-top: 34px; }
.cover .foot { margin-top: 64px; }
.number .foot, .end .foot, .text-card .foot { margin-top: auto; }
.visual-card .foot, .shot-card .foot { margin-top: 0; }
.source { font-size: 22px; line-height: 1.35; color: var(--muted); max-width: 780px; }
.brand { display: flex; align-items: center; gap: 16px; font-size: 24px; color: var(--muted); white-space: nowrap; }
.brand img { height: 44px; width: auto; }
`;
}

// crop: [x, y, w, h] in the image's own pixels, to zoom a wide UI capture onto the part
// that carries the claim (a 16:9 screen is unreadable whole on a 4:5 card).
export const cropStyle = (c) =>
  Array.isArray(c) && c.length === 4
    ? ` style="object-view-box: xywh(${c[0]}px ${c[1]}px ${c[2]}px ${c[3]}px); aspect-ratio: ${c[2]} / ${c[3]}"`
    : '';

export function slideHtml(s, i, n, spec, visualUrl) {
  const kind = s.kind || (s.visual || s.image ? 'visual' : 'text');
  const count = n > 1 && spec.count !== false ? `<div class="count">${String(i + 1).padStart(2, '0')} / ${String(n).padStart(2, '0')}</div>` : '';
  const top = `<div class="top"><div class="eyebrow">${esc(s.eyebrow)}</div>${count}</div>`;
  const brandLine = spec.footer === false ? '' : esc(s.footer ?? spec.footer ?? '');
  const foot = `<div class="foot"><div class="source">${esc(s.source)}</div>
    <div class="brand">${brandLine ? `<span>${brandLine}</span>` : ''}<img src="${BRANDS[spec.brand].logo}" alt=""></div></div>`;
  switch (kind) {
    case 'cover':
      return `<div class="card cover">${top}<div class="title" data-fit="560">${esc(s.title)}</div>
        ${s.sub ? `<div class="sub" data-fit="300">${esc(s.sub)}</div>` : ''}<div class="rule"></div>${foot}</div>`;
    case 'number':
      return `<div class="card number">${top}<div class="big" data-fit="230">${esc(s.value)}</div>
        <div class="label" data-fit="200">${esc(s.label)}</div>${s.sub ? `<div class="sub" data-fit="320">${esc(s.sub)}</div>` : ''}${foot}</div>`;
    case 'end':
      return `<div class="card end">${top}<div class="title" style="margin-top:auto" data-fit="420">${esc(s.title)}</div>
        ${s.line ? `<div class="sub" data-fit="300">${esc(s.line)}</div>` : ''}${s.url ? `<div class="url">${esc(s.url)}</div>` : ''}${foot}</div>`;
    case 'visual': {
      const shot = !!s.image;
      return `<div class="card ${shot ? 'shot-card' : 'visual-card'}">${top}
        ${s.title ? `<div class="title" data-fit="300">${esc(s.title)}</div>` : ''}
        <div class="visual${shot ? ' shot' : ''}"><img src="${visualUrl}" alt=""${cropStyle(s.crop)}></div>
        ${s.caption ? `<div class="caption" data-fit="180">${esc(s.caption)}</div>` : ''}${foot}</div>`;
    }
    case 'text':
      return `<div class="card text-card">${top}<div class="text" data-fit="820">${esc(s.text)}</div>${foot}</div>`;
    default:
      throw new Error(`slide ${i + 1}: unknown kind "${kind}"; expected cover, visual, number, text, end`);
  }
}

function pageHtml(body, brand, W, H) {
  // data-fit="N": shrink the element's font until it is at most N px tall, so a long
  // line never overruns the card; the spec's words are never cut.
  return `<!doctype html><html><head><meta charset="utf-8"><style>${cardCss(brand, W, H)}</style></head>
<body>${body}<script>
window.__fit = async () => {
  await Promise.all(['700 40px "Space Grotesk"', '600 40px Orbitron', '800 40px Orbitron'].map((f) => document.fonts.load(f)));
  await document.fonts.ready;
  await Promise.all([...document.images].map((im) => im.complete ? 0 : new Promise((r) => { im.onload = im.onerror = r; })));
  for (const el of document.querySelectorAll('[data-fit]')) {
    const max = Number(el.dataset.fit);
    let size = parseFloat(getComputedStyle(el).fontSize);
    while (el.scrollHeight > max && size > 18) { size -= 2; el.style.fontSize = size + 'px'; }
  }
  return true;
};
</script></body></html>`;
}

/* Pose a motion template at its finished frame and crop to what it drew. */
async function renderVisual(browser, visual, file) {
  const template = visual.template || 'research';
  const pub = PUBLIC[visual.public || TEMPLATE_BRAND[template] || 'robosystems'];
  if (!existsSync(pub)) throw new Error(`no app public/ for template "${template}": ${pub} (set ROBOSYSTEMS_PUBLIC / ROBOLEDGER_PUBLIC)`);
  const mounts = {
    '/demos/': path.join(pub, 'demos'),
    '/fonts/': path.join(pub, 'fonts'),
    '/images/': path.join(pub, 'images'),
    ...(visual.stillsDir ? { '/stills/': visual.stillsDir } : {}),
    '/': path.join(REPO, 'motion'),
  };
  const server = await serve({ html: '', mounts });
  try {
    const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 2 });
    const q = `t=${encodeURIComponent(template)}&data=${encodeURIComponent(JSON.stringify(visual.data || {}))}`;
    await page.goto(`${server.url}/render.html?${q}`, { waitUntil: 'load' });
    await page.waitForFunction(() => typeof window.__init === 'function');
    await page.evaluate(() => window.__init());
    await page.waitForFunction(() => window.__READY === true);
    const total = await page.evaluate(() => window.__total());
    const at = visual.at != null ? Math.min(visual.at, total) : Math.max(0, total - 0.6);
    await page.evaluate((t) => new Promise((r) => { window.__seek(t); requestAnimationFrame(() => requestAnimationFrame(r)); }), at);
    // The template draws into a shadow root on #host. Drop its backdrop (wash, grid,
    // stage fill) so the chart lands on the card's own background, not in a box.
    const extra = (visual.postCss === false ? '' : POST_CSS[visual.data?.kind] || '') + (visual.css || '');
    await page.evaluate((extra) => {
      const sr = document.getElementById('host')?.shadowRoot;
      const st = document.createElement('style');
      st.textContent = '.bg, .gridbg { display: none !important; } .stage { background: transparent !important; }' + extra;
      (sr || document.head).appendChild(st);
      for (const el of [document.documentElement, document.body, document.getElementById('host')]) if (el) el.style.background = 'transparent';
    }, extra);
    // Re-pose after the CSS change so anything measured from layout lands again.
    await page.evaluate((t) => new Promise((r) => { window.__seek(t); requestAnimationFrame(() => requestAnimationFrame(r)); }), at);
    const box = await page.evaluate((pad) => {
      const sr = document.getElementById('host')?.shadowRoot;
      const root = sr?.getElementById('content') || document.getElementById('content');
      if (!root) return null;
      let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
      for (const el of root.querySelectorAll('*')) {
        const r = el.getBoundingClientRect();
        const cs = getComputedStyle(el);
        if (!r.width || !r.height || cs.visibility === 'hidden' || Number(cs.opacity) === 0) continue;
        // Only what paints counts: own text, a fill, a border or an image. A pure layout
        // box (a full-width eyebrow row with no text) would widen the crop to the frame.
        const text = [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
        const fill = cs.backgroundImage !== 'none' || !/rgba\(0, 0, 0, 0\)|transparent/.test(cs.backgroundColor);
        const edge = ['Top', 'Right', 'Bottom', 'Left'].some((d) => parseFloat(cs['border' + d + 'Width']) > 0);
        if (!(text || fill || edge || /^(IMG|SVG|CANVAS|svg)$/.test(el.tagName))) continue;
        x0 = Math.min(x0, r.left); y0 = Math.min(y0, r.top); x1 = Math.max(x1, r.right); y1 = Math.max(y1, r.bottom);
      }
      if (!isFinite(x0)) return null;
      const W = innerWidth, H = innerHeight;
      const x = Math.max(0, x0 - pad), y = Math.max(0, y0 - pad);
      return { x, y, width: Math.min(W, x1 + pad) - x, height: Math.min(H, y1 + pad) - y };
    }, visual.pad ?? 24);
    if (!box) throw new Error(`visual "${template}": found no #content to crop`);
    await page.screenshot({ path: file, clip: box, omitBackground: true });
    await page.close();
  } finally {
    await server.close();
  }
}

export async function post(args) {
  if (!args.spec) throw new Error('post requires --spec <file.post.json>');
  const specPath = path.resolve(args.spec);
  const spec = JSON.parse(await readFile(specPath, 'utf8'));
  const specDir = path.dirname(specPath);
  const name = args.name || spec.name || path.basename(specPath).replace(/\.post\.json$|\.json$/, '');
  const outDir = args.out ? path.resolve(args.out) : path.join(specDir, 'renders');
  spec.brand = spec.brand || 'robosystems';
  if (!BRANDS[spec.brand]) throw new Error(`unknown brand "${spec.brand}"; expected ${Object.keys(BRANDS).join(', ')}`);
  const [W, H] = spec.size || [1080, 1350];
  const dsf = Number(args.dsf || spec.dsf || 1);
  const slides = spec.slides || [];
  if (!slides.length) throw new Error('spec has no slides');
  const pub = PUBLIC[spec.brand];
  if (!existsSync(pub)) throw new Error(`no app public/ for brand "${spec.brand}": ${pub}`);

  await mkdir(outDir, { recursive: true });
  const work = path.join(outDir, `.${name}-visuals`);
  await rm(work, { recursive: true, force: true });
  await mkdir(work, { recursive: true });

  const browser = await chromium.launch({ headless: true, args: ['--force-color-profile=srgb', '--hide-scrollbars'] });
  const server = await serve({
    html: '',
    mounts: { '/fonts/': path.join(pub, 'fonts'), '/images/': path.join(pub, 'images'), '/work/': work, '/spec/': specDir, '/out/': outDir },
  });
  const pngs = [];
  try {
    // 1. The visuals: posed motion templates, cropped; image files are used as they are.
    const visualUrls = [];
    for (const [i, s] of slides.entries()) {
      if (s.visual) {
        const file = path.join(work, `v${i + 1}.png`);
        const v = { ...s.visual };
        if (v.stillsDir) v.stillsDir = path.resolve(specDir, v.stillsDir);
        await renderVisual(browser, v, file);
        visualUrls.push(`/work/v${i + 1}.png`);
      } else if (s.image) {
        const abs = path.resolve(specDir, s.image);
        if (!existsSync(abs)) throw new Error(`slide ${i + 1}: no such image ${abs}`);
        visualUrls.push(`/spec/${path.relative(specDir, abs).split(path.sep).join('/')}`);
      } else visualUrls.push('');
    }

    // 2. The cards, one PNG per slide.
    const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: dsf });
    for (const [i, s] of slides.entries()) {
      await page.goto(server.url + '/', { waitUntil: 'load' });
      await page.setContent(pageHtml(slideHtml(s, i, slides.length, spec, visualUrls[i]), spec.brand, W, H), { waitUntil: 'load' });
      await page.evaluate(() => window.__fit());
      const file = path.join(outDir, slides.length > 1 ? `${name}-${String(i + 1).padStart(2, '0')}.png` : `${name}.png`);
      await page.screenshot({ path: file, clip: { x: 0, y: 0, width: W, height: H } });
      pngs.push(file);
      console.log(`  slide ${i + 1}/${slides.length} -> ${path.relative(process.cwd(), file)}`);
    }

    // 3. The carousel: the same pages as one PDF, one page per slide.
    if (slides.length > 1 && !args['no-pdf']) {
      const pdfPage = await browser.newPage({ viewport: { width: W, height: H } });
      const imgs = pngs.map((f) => `<img src="/out/${path.basename(f)}">`).join('');
      await pdfPage.goto(server.url + '/', { waitUntil: 'load' });
      await pdfPage.setContent(`<!doctype html><html><head><style>
        @page { size: ${W}px ${H}px; margin: 0; } html, body { margin: 0; background: #000; }
        img { display: block; width: ${W}px; height: ${H}px; page-break-after: always; }</style></head><body>${imgs}</body></html>`, { waitUntil: 'load' });
      const pdf = path.join(outDir, `${name}.pdf`);
      await pdfPage.pdf({ path: pdf, width: `${W}px`, height: `${H}px`, printBackground: true });
      console.log(`✓ ${path.relative(process.cwd(), pdf)}  (${slides.length} pages)`);
    }
    console.log(`✓ ${pngs.length} PNG${pngs.length > 1 ? 's' : ''} at ${W * dsf}x${H * dsf} in ${path.relative(process.cwd(), outDir) || '.'}`);
  } finally {
    await browser.close();
    await server.close();
    if (!args['keep-visuals']) await rm(work, { recursive: true, force: true });
  }
}
