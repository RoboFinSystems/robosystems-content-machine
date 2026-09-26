/*
 * The motion "slide": one idea per shot, centred, built in front of the viewer,
 * with a slow push underneath (a slide that never moves is the slop this avoids).
 * The words come from data, so every slide says what the narration says.
 *
 * data.kind:
 *   title    { eyebrow?, headline, sub? }
 *   number   { eyebrow?, value, prefix?, suffix?, decimals?, label, from?: { value, label } }
 *   compare  { eyebrow?, left: { title, items[] }, right: { title, items[] } }
 *   flow     { eyebrow?, nodes[], caption? }
 * plus duration? (seconds, default 4.5)
 */
import { blurIn, eio, eo, rise, seg } from '/demos/kit.js'
import { BACKDROP, BRAND_CSS, envelope, H, W, words } from './brand.js'

const fmt = (v, d, prefix = '', suffix = '') =>
  prefix +
  v.toLocaleString('en-US', { minimumFractionDigits: d || 0, maximumFractionDigits: d || 0 }) +
  suffix

function title(data) {
  const n = data.headline.split(' ').length
  return {
    html: `
  ${data.eyebrow ? `<div class="eyebrow" id="eb">${data.eyebrow}</div>` : ''}
  <div class="headline" style="margin-top:${data.eyebrow ? 30 : 0}px">${words(data.headline, 'w')}</div>
  ${data.sub ? `<div class="sub" id="sub" style="margin-top:40px">${data.sub}</div>` : ''}`,
    css: '',
    pose($, t) {
      if (data.eyebrow) blurIn($('eb'), seg(t, 0.15, 0.7), 12)
      for (let i = 0; i < n; i++) blurIn($('w' + i), seg(t, 0.35 + i * 0.08, 1.0 + i * 0.08))
      if (data.sub) blurIn($('sub'), seg(t, 0.9 + n * 0.08, 1.5 + n * 0.08), 12)
    },
  }
}

function number(data) {
  const d = data.decimals || 0
  return {
    html: `
  ${data.eyebrow ? `<div class="eyebrow" id="eb">${data.eyebrow}</div>` : ''}
  ${data.from ? `<div class="from" id="from"><b>${fmt(data.from.value, d, data.prefix, data.suffix)}</b> ${data.from.label}</div>` : ''}
  <div class="big grad" id="num"></div>
  <div class="rule" id="rule" style="width:260px;margin-top:30px"></div>
  <div class="sub" id="lbl" style="margin-top:34px">${data.label}</div>`,
    css: `
.big { font: 800 210px/1 var(--display); margin-top: 26px; font-variant-numeric: tabular-nums; }
.from { margin-top: 34px; font-size: 34px; color: var(--muted); }
.from b { font-family: var(--mono); font-weight: 600; color: #cfcbdc; }`,
    pose($, t) {
      if (data.eyebrow) blurIn($('eb'), seg(t, 0.15, 0.7), 12)
      if (data.from) blurIn($('from'), seg(t, 0.4, 0.9), 12)
      const start = data.from ? data.from.value : 0
      const p = eo(seg(t, 0.6, 2.0))
      $('num').textContent = fmt(start + (data.value - start) * p, d, data.prefix, data.suffix)
      rise($('num'), eo(seg(t, 0.5, 0.9)), 30)
      $('rule').style.transform = `scaleX(${eio(seg(t, 1.6, 2.2))})`
      blurIn($('lbl'), seg(t, 1.8, 2.4), 12)
    },
  }
}

function compare(data) {
  const L = data.left.items
  const R = data.right.items
  const col = (side, c, items) => `
    <div class="col ${side}" id="${side}">
      <div class="ch">${c.title}</div>
      ${items.map((it, i) => `<div class="it" id="${side}${i}"><span>${it}</span><i id="${side}s${i}"></i></div>`).join('')}
    </div>`
  return {
    html: `
  ${data.eyebrow ? `<div class="eyebrow" id="eb">${data.eyebrow}</div>` : ''}
  <div class="cmp" style="margin-top:${data.eyebrow ? 50 : 0}px">
    ${col('l', data.left, L)}
    <div class="vs" id="vs"></div>
    ${col('r', data.right, R)}
  </div>`,
    css: `
.cmp { display: flex; align-items: stretch; gap: 60px; text-align: left; }
.col { width: 760px; padding: 40px 46px; border-radius: 22px; border: 1px solid var(--line); background: rgba(20,19,25,.8); }
.col.r { border-color: var(--v500); }
.ch { font: 700 42px var(--display); margin-bottom: 22px; }
.col.l .ch { color: #b9b5c8; }
.col.r .ch { color: var(--v300); }
.it { position: relative; font-size: 40px; line-height: 1.3; padding: 20px 0; border-top: 1px solid var(--line); }
.col.l .it { color: #9b97ad; }
.it i { position: absolute; left: 0; top: 50%; height: 3px; width: 100%; background: var(--bad); transform-origin: left; transform: scaleX(0); }
.vs { width: 3px; border-radius: 2px; background: linear-gradient(180deg, var(--v500), var(--f500)); transform-origin: top; }`,
    pose($, t) {
      if (data.eyebrow) blurIn($('eb'), seg(t, 0.1, 0.6), 12)
      rise($('l'), eo(seg(t, 0.2, 0.7)), 24)
      L.forEach((_, i) => rise($('l' + i), eo(seg(t, 0.5 + i * 0.25, 0.9 + i * 0.25)), 10))
      const r0 = 0.9 + L.length * 0.25
      $('vs').style.transform = `scaleY(${eio(seg(t, r0 - 0.3, r0 + 0.3))})`
      rise($('r'), eo(seg(t, r0, r0 + 0.5)), 24)
      R.forEach((_, i) => rise($('r' + i), eo(seg(t, r0 + 0.3 + i * 0.3, r0 + 0.7 + i * 0.3)), 10))
      // once the right side has landed, the old way is struck through, line by line
      const s0 = r0 + 0.5 + R.length * 0.3
      L.forEach((_, i) => {
        $('ls' + i).style.transform = `scaleX(${eio(seg(t, s0 + i * 0.15, s0 + 0.4 + i * 0.15))})`
      })
    },
  }
}

function flow(data) {
  const N = data.nodes
  return {
    html: `
  ${data.eyebrow ? `<div class="eyebrow" id="eb">${data.eyebrow}</div>` : ''}
  <div class="flow" style="margin-top:${data.eyebrow ? 60 : 0}px">
    ${N.map((n, i) => `${i ? `<div class="wire" id="wr${i}"></div>` : ''}<div class="node" id="n${i}">${n}</div>`).join('')}
  </div>
  ${data.caption ? `<div class="sub" id="cap" style="margin-top:60px">${data.caption}</div>` : ''}`,
    css: `
.flow { display: flex; align-items: center; }
.node { padding: 34px 48px; border-radius: 24px; border: 1px solid var(--line); background: var(--card); font-size: 46px; font-weight: 600; }
.node:last-child { border-color: var(--v500); }
.wire { width: 140px; height: 3px; background: linear-gradient(90deg, var(--v500), var(--f500)); transform-origin: left; }`,
    pose($, t) {
      if (data.eyebrow) blurIn($('eb'), seg(t, 0.1, 0.6), 12)
      N.forEach((_, i) => {
        const at = 0.4 + i * 0.55
        rise($('n' + i), eo(seg(t, at, at + 0.45)), 20)
        if (i) $('wr' + i).style.transform = `scaleX(${eio(seg(t, at - 0.3, at + 0.05))})`
      })
      if (data.caption) blurIn($('cap'), seg(t, 0.6 + N.length * 0.55, 1.2 + N.length * 0.55), 12)
    },
  }
}

const KINDS = { title, number, compare, flow }

export default function slide(data) {
  const kind = KINDS[data.kind]
  if (!kind) throw new Error(`unknown slide kind "${data.kind}"; expected ${Object.keys(KINDS).join(', ')}`)
  const k = kind(data)
  const total = data.duration || 4.5
  return {
    width: W,
    height: H,
    total,
    poster: 0.7 * total,
    css: BRAND_CSS + k.css,
    html: `${BACKDROP}<div class="frame" id="content">${k.html}</div>`,
    setup(ctx) {
      const { $ } = ctx
      return (t) => {
        envelope($('content'), t, total)
        k.pose($, t)
      }
    },
  }
}
