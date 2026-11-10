/*
 * Research-lane scenes: findings drawn in front of the viewer, in the RoboSystems
 * look (mount robosystems-app's public/ at /demos/, /fonts/ and /images/; an episode
 * does that with "public" in episode.json). Every number and word comes from data;
 * nothing is computed here but the tween.
 *
 * data.kind:
 *   title     { eyebrow?, headline, sub? }
 *   rungs     { eyebrow?, rungs: [{ label, note?, at? }] }            bottom rung first
 *   counters  { eyebrow?, wide?, items: [{ value | text, label, at? }], lines?: [{ text, at }] }
 *   band      { eyebrow?, dots: [values], band: [lo, hi], bandLabel, bandAt, lines?: [{ text, at }] }
 *   board     { eyebrow?, groups: [{ title, tone?, at, stagger?, summary?: { text, at },
 *               rows: [{ label, v, text?, note?, at? }] }] }          accuracy, 0 to 100;
 *               `text` replaces the figure once the bar lands (a range)
 *   bars      { eyebrow?, eyebrow2?: { text, at }, unit?, max, rows: [{ label, note?, tone?, enter?,
 *               steps: [{ v, at? }], tag?: { text, at } }] }
 *             a bar grows to steps[0].v at `enter`, then moves to each later step at its
 *             `at`, leaving a faint ghost and a tick at the value it started from
 *   flow      { eyebrow?, nodes: [{ title, sub?, main?, at? }], lines?: [{ text, at }] }
 *   grid      { eyebrow?, count, cols, strike: [indexes], strikeAt, stats: [{ big, label, at }] }
 *   tools     { eyebrow?, tools: [names], empty, full, fillAt, chips?: [{ text, at }] }
 *   corpus    { eyebrow?, zoomAt, lines: [{ text, at }] }
 *   end       { title, line, url, client?, repo? }
 * plus duration? (seconds). Times are seconds from the start of the shot; the assembler
 * fills them from the voice ("@cue" values), so the picture follows the words.
 */
import { blurIn, eio, eo, rise, seg, typed } from './runtime.js'
import { tile } from '/demos/kit.js'
import { envelope, H, W, words } from './brand.js'

const CSS = `
.stage { background: var(--bg); }
.bg { position: absolute; inset: 0;
  background: linear-gradient(135deg, rgba(8,145,178,.20), rgba(37,99,235,.11) 50%, rgba(99,102,241,.17)); }
.gridbg { position: absolute; inset: 0; opacity: .06;
  background-image: linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px);
  background-size: 64px 64px; }
.frame { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 0 150px; text-align: center; }
.eyebrow { font: 600 24px var(--display); letter-spacing: .32em; color: var(--c300); text-transform: uppercase; }
.ebs { position: relative; height: 32px; width: 100%; }
.ebs .eyebrow { position: absolute; left: 0; right: 0; top: 0; }
.eyebrow.warn { color: var(--warn); }
.headline { font: 800 104px/1.08 var(--display); letter-spacing: -.01em; }
.sub { font-size: 40px; font-weight: 500; color: #c9d1dd; line-height: 1.3; max-width: 1400px; }
.wd { display: inline-block; }
.ln { font-size: 38px; font-weight: 500; color: #c9d1dd; margin-top: 22px; }
.ln:first-child { margin-top: 0; }
.lns { margin-top: 64px; }
`

const head = (data) => (data.eyebrow ? `<div class="eyebrow" id="eb">${data.eyebrow}</div>` : '')
const headIn = ($, data, t) => data.eyebrow && blurIn($('eb'), seg(t, 0.15, 0.7), 12)
const linesHtml = (lines = []) =>
  lines.length ? `<div class="lns">${lines.map((l, i) => `<div class="ln" id="ln${i}">${l.text}</div>`).join('')}</div>` : ''
const linesIn = ($, lines = [], t) => lines.forEach((l, i) => blurIn($('ln' + i), seg(t, l.at, l.at + 0.6), 12))

function title(data) {
  const n = data.headline.split(' ').length
  return {
    html: `${head(data)}
  <div class="headline" style="margin-top:${data.eyebrow ? 34 : 0}px">${words(data.headline, 'w')}</div>
  ${data.sub ? `<div class="sub" id="sub" style="margin-top:44px">${data.sub}</div>` : ''}`,
    css: '',
    pose($, t) {
      headIn($, data, t)
      for (let i = 0; i < n; i++) blurIn($('w' + i), seg(t, 0.35 + i * 0.1, 1.0 + i * 0.1))
      if (data.sub) blurIn($('sub'), seg(t, 0.9 + n * 0.1, 1.5 + n * 0.1), 12)
    },
  }
}

function rungs(data) {
  const R = data.rungs.map((r, i) => ({ ...r, at: r.at ?? 0.6 + i * 1.1 }))
  const n = R.length
  const gap = 150
  const y = (i) => (n - 1 - i) * gap // bottom rung first
  return {
    html: `${head(data)}
  <div class="ladder" style="height:${(n - 1) * gap + 110}px">
    <div class="rail l" id="rl"></div><div class="rail r" id="rr"></div>
    ${R.map(
      (r, i) => `
    <div class="rung" id="g${i}" style="top:${y(i)}px">
      <b>${i + 1}</b><span>${r.label}</span>${r.note ? `<small>${r.note}</small>` : ''}
      <i id="h${i}"></i>
    </div>`
    ).join('')}
  </div>`,
    css: `
.ladder { position: relative; width: 1320px; margin-top: 70px; text-align: left; }
.rail { position: absolute; top: -40px; bottom: -40px; width: 6px; border-radius: 3px; transform-origin: bottom;
  background: linear-gradient(0deg, var(--i500), var(--b500) 50%, var(--c400)); }
.rail.l { left: 0; } .rail.r { right: 0; }
.rung { position: absolute; left: 6px; right: 6px; height: 110px; display: flex; align-items: center; gap: 30px; padding: 0 44px;
  border: 1px solid var(--line); border-radius: 6px; background: rgba(15,17,22,.86); }
.rung b { font: 700 30px var(--display); color: var(--c400); width: 40px; }
.rung span { font-size: 40px; font-weight: 600; }
.rung small { margin-left: auto; font-size: 26px; color: var(--muted); }
.rung i { position: absolute; inset: -1px; border-radius: 6px; border: 2px solid var(--c400); opacity: 0; }`,
    pose($, t) {
      headIn($, data, t)
      let top = 0
      R.forEach((r, i) => {
        rise($('g' + i), eo(seg(t, r.at, r.at + 0.55)), 26)
        top = Math.max(top, ((i + 1) / n) * eio(seg(t, r.at - 0.25, r.at + 0.45)))
        // the rung being named is lit; it settles when the next one arrives
        const next = R[i + 1]?.at ?? Infinity
        $('h' + i).style.opacity = Math.min(seg(t, r.at + 0.1, r.at + 0.5), 1 - seg(t, next - 0.1, next + 0.4))
      })
      $('rl').style.transform = $('rr').style.transform = `scaleY(${top})`
    },
  }
}

function counters(data) {
  const I = data.items.map((it, i) => ({ ...it, at: it.at ?? 0.5 + i * 0.9 }))
  return {
    html: `${head(data)}
  <div class="cts${data.wide ? ' wide' : ''}">
    ${I.map((it, i) => `<div class="ct" id="c${i}"><div class="cn grad" id="n${i}"></div><div class="cl">${it.label}</div></div>`).join('')}
  </div>
  ${linesHtml(data.lines)}`,
    css: `
.cts { display: flex; gap: 28px; margin-top: 70px; }
.ct { width: 300px; padding: 44px 16px 38px; border-radius: 18px; border: 1px solid var(--line); background: rgba(15,17,22,.86); }
.cn { font: 800 112px/1 var(--display); font-variant-numeric: tabular-nums; }
.cts.wide .ct { width: 500px; }
.cts.wide .cn { font-size: 76px; white-space: nowrap; }
.cts.wide .cl { font-size: 32px; }
.cl { margin-top: 22px; font-size: 28px; font-weight: 500; color: #c9d1dd; line-height: 1.25; }`,
    pose($, t) {
      headIn($, data, t)
      I.forEach((it, i) => {
        rise($('c' + i), eo(seg(t, it.at, it.at + 0.5)), 24)
        $('n' + i).textContent = it.text ?? String(Math.round(it.value * eo(seg(t, it.at + 0.05, it.at + 0.8))))
      })
      linesIn($, data.lines, t)
    },
  }
}

function band(data) {
  const [lo, hi] = data.band
  const lanes = [0, -1, 1, -2, 2]
  const seen = {}
  const D = data.dots.map((v, i) => {
    const k = (seen[v] = (seen[v] ?? -1) + 1)
    return { v, lane: lanes[(i + k) % lanes.length], at: 0.7 + i * 0.22 }
  })
  return {
    html: `${head(data)}
  <div class="ax">
    <div class="bd" id="bd" style="left:${lo}%;width:${hi - lo}%"></div>
    <div class="bl" id="bl" style="left:${(lo + hi) / 2}%">${data.bandLabel}</div>
    <div class="base"></div>
    ${[0, 25, 50, 75, 100].map((v) => `<div class="tk" style="left:${v}%"><i></i><span>${v}%</span></div>`).join('')}
    ${D.map((d, i) => `<div class="dot" id="d${i}" style="top:${170 + d.lane * 34}px"></div>`).join('')}
  </div>
  ${linesHtml(data.lines)}`,
    css: `
.ax { position: relative; width: 1560px; height: 400px; margin-top: 110px; }
.base { position: absolute; left: 0; right: 0; top: 300px; height: 3px; border-radius: 2px; background: #3d4657; }
.tk { position: absolute; top: 300px; width: 0; }
.tk i { position: absolute; left: -1px; top: 0; width: 3px; height: 16px; background: #3d4657; }
.tk span { position: absolute; top: 30px; left: -60px; width: 120px; font: 500 28px var(--mono); color: var(--muted); }
.bd { position: absolute; top: 40px; height: 262px; border-radius: 10px; transform-origin: bottom;
  background: linear-gradient(180deg, rgba(34,211,238,.26), rgba(59,122,245,.10)); border: 1px solid var(--c600); }
.bl { position: absolute; top: -52px; width: 520px; margin-left: -260px; font: 700 54px var(--display); color: var(--c300); }
.dot { position: absolute; width: 30px; height: 30px; margin-left: -15px; border-radius: 50%; background: var(--ink); }`,
    pose($, t) {
      headIn($, data, t)
      D.forEach((d, i) => {
        const p = eo(seg(t, d.at, d.at + 1.1))
        $('d' + i).style.left = d.v * p + '%'
        $('d' + i).style.opacity = seg(t, d.at, d.at + 0.3)
      })
      const b = eio(seg(t, data.bandAt, data.bandAt + 0.7))
      $('bd').style.opacity = b
      $('bd').style.transform = `scaleY(${0.6 + 0.4 * b})`
      blurIn($('bl'), seg(t, data.bandAt + 0.3, data.bandAt + 0.9), 14)
      linesIn($, data.lines, t)
    },
  }
}

function board(data) {
  const G = data.groups
  let k = 0
  const rows = G.flatMap((g, gi) => g.rows.map((r, ri) => ({ ...r, gi, ri, id: k++ })))
  return {
    html: `${head(data)}
  <div class="bd2">
    ${G.map(
      (g, gi) => `
    <div class="grp ${g.tone || ''}" id="gp${gi}">
      <div class="gt">${g.title}</div>
      ${rows
        .filter((r) => r.gi === gi)
        .map((r) => `<div class="rw" id="rw${r.id}"><span class="rl">${r.label}</span><span class="rt"><i id="rf${r.id}"></i></span><b id="rv${r.id}"></b>${r.note ? `<em>${r.note}</em>` : ''}</div>`)
        .join('')}
      ${g.summary ? `<div class="gs" id="gs${gi}">${g.summary.text}</div>` : ''}
    </div>`
    ).join('')}
  </div>`,
    css: `
.bd2 { width: 1640px; margin-top: 44px; display: flex; flex-direction: column; gap: 30px; text-align: left; }
.grp { position: relative; }
.gt { font: 600 21px var(--display); letter-spacing: .24em; text-transform: uppercase; color: var(--muted); margin-bottom: 12px; }
.rw { display: flex; align-items: center; height: 62px; }
.rl { width: 540px; font-size: 34px; font-weight: 600; }
.rt { position: relative; width: 600px; height: 34px; border-radius: 8px; background: rgba(255,255,255,.035); }
.rt i { position: absolute; left: 0; top: 0; bottom: 0; border-radius: 8px; background: #8792a6; }
.grp.low .rt i { background: #4a5364; }
.grp.brand .rt i { background: linear-gradient(90deg, var(--c500), var(--b500) 60%, var(--i500)); }
.rw b { min-width: 120px; padding-left: 22px; white-space: nowrap; font: 700 34px var(--mono); font-variant-numeric: tabular-nums; }
.grp.low .rw b, .grp.low .rl { color: #aab2c0; }
.rw em { font-style: normal; font-size: 26px; color: var(--muted); padding-left: 14px; white-space: nowrap; }
.gs { position: absolute; right: 0; top: 50%; margin-top: -10px; width: 340px; text-align: right; font: 700 50px/1.1 var(--display); color: var(--c300); }
.grp.low .gs { color: #aab2c0; }`,
    pose($, t) {
      headIn($, data, t)
      G.forEach((g, gi) => {
        $('gp' + gi).style.opacity = eo(seg(t, g.at - 0.2, g.at + 0.3))
        if (g.summary) blurIn($('gs' + gi), seg(t, g.summary.at, g.summary.at + 0.6), 12)
      })
      rows.forEach((r) => {
        const at = r.at ?? G[r.gi].at + r.ri * (G[r.gi].stagger ?? 0.5)
        rise($('rw' + r.id), eo(seg(t, at, at + 0.45)), 14)
        const v = r.v * eo(seg(t, at + 0.1, at + 0.95))
        $('rf' + r.id).style.width = v + '%'
        $('rv' + r.id).textContent = r.text && v >= r.v ? r.text : Math.round(v) + '%'
      })
    },
  }
}

function bars(data) {
  const unit = data.unit ?? '¢'
  const rows = data.rows.map((r, i) => ({
    ...r,
    enter: r.enter ?? 0.5 + i * 0.5,
    steps: r.steps.map((s) => ({ v: s.v, at: s.at ?? 0 })),
  }))
  const pct = (v) => (v / data.max) * 100
  const e2 = data.eyebrow2
  return {
    html: `
  <div class="ebs"><div class="eyebrow" id="eb">${data.eyebrow || ''}</div>${e2 ? `<div class="eyebrow warn" id="eb2">${e2.text}</div>` : ''}</div>
  <div class="bars">
    ${rows
      .map(
        (r, i) => `
    <div class="br ${r.tone || ''}" id="r${i}">
      <div class="lb"><span>${r.label}</span>${r.note ? `<small>${r.note}</small>` : ''}</div>
      <div class="tk">
        <div class="gh" id="g${i}" style="width:${pct(r.steps[0].v)}%"></div>
        <div class="fl" id="f${i}"></div>
        <div class="vl" id="v${i}"></div>
        ${r.tag ? `<div class="tg" id="t${i}">${r.tag.text}</div>` : ''}
      </div>
    </div>`
      )
      .join('')}
  </div>`,
    css: `
.bars { width: 1560px; margin-top: 44px; display: flex; flex-direction: column; gap: 22px; text-align: left; }
.lb { display: flex; justify-content: space-between; align-items: baseline; font-size: 34px; font-weight: 600; }
.lb small { font-size: 25px; font-weight: 500; color: var(--muted); }
.tk { position: relative; height: 50px; margin-top: 10px; border-radius: 12px; background: rgba(255,255,255,.035); }
.fl { position: absolute; left: 0; top: 0; bottom: 0; border-radius: 12px;
  background: linear-gradient(90deg, var(--c500), var(--b500) 60%, var(--i500)); }
.br.plain .fl { background: #3d4657; }
.br.warn .fl { background: linear-gradient(90deg, #d97706, var(--warn)); }
.gh { position: absolute; left: 0; top: 0; bottom: 0; border-radius: 12px; background: rgba(255,255,255,.07); border-right: 3px solid rgba(255,255,255,.38); opacity: 0; }
.vl { position: absolute; top: 50%; margin-top: -24px; font: 700 38px/48px var(--mono); font-variant-numeric: tabular-nums; }
.tg { position: absolute; right: 0; top: 50%; margin-top: -24px; padding: 0 20px; border-radius: 24px;
  font: 600 26px/48px var(--body); color: var(--c300); border: 1px solid var(--c600); background: rgba(8,145,178,.14); }
.br.plain .tg { color: #cdd3de; border-color: #4a5364; background: rgba(255,255,255,.05); }`,
    pose($, t) {
      const out = e2 ? eio(seg(t, e2.at - 0.35, e2.at)) : 0
      blurIn($('eb'), seg(t, 0.15, 0.7), 12)
      if (e2) {
        $('eb').style.opacity = Math.min(Number($('eb').style.opacity), 1 - out)
        blurIn($('eb2'), seg(t, e2.at, e2.at + 0.55), 12)
      }
      rows.forEach((r, i) => {
        rise($('r' + i), eo(seg(t, r.enter, r.enter + 0.5)), 22)
        let v = r.steps[0].v * eo(seg(t, r.enter + 0.15, r.enter + 1.0))
        for (let k = 1; k < r.steps.length; k++) {
          v += (r.steps[k].v - r.steps[k - 1].v) * eio(seg(t, r.steps[k].at, r.steps[k].at + 0.9))
        }
        $('f' + i).style.width = pct(v) + '%'
        // a value that lands close to its ghost's tick sits past the tick, not on it
        const s0 = r.steps[0].v
        const near = r.steps.length > 1 && Math.abs(s0 - v) / data.max < 0.12 ? eio(seg(t, r.steps[1].at - 0.1, r.steps[1].at + 0.5)) : 0
        $('v' + i).style.left = `calc(${pct(v + (Math.max(s0, v) - v) * near)}% + 22px)`
        $('v' + i).textContent = v.toFixed(1) + unit
        if (r.steps.length > 1) $('g' + i).style.opacity = seg(t, r.steps[1].at - 0.1, r.steps[1].at + 0.4)
        if (r.tag) blurIn($('t' + i), seg(t, r.tag.at, r.tag.at + 0.5), 10)
      })
    },
  }
}

function flow(data) {
  const N = data.nodes.map((n, i) => ({ ...n, at: n.at ?? 0.5 + i * 0.7 }))
  return {
    html: `${head(data)}
  <div class="fw">
    ${N.map((n, i) => `${i ? `<div class="wire" id="wr${i}"></div>` : ''}<div class="nd${n.main ? ' main' : ''}" id="nd${i}"><div class="nt">${n.title}</div>${n.sub ? `<div class="ns">${n.sub}</div>` : ''}</div>`).join('')}
  </div>
  ${linesHtml(data.lines)}`,
    css: `
.fw { display: flex; align-items: center; margin-top: 80px; }
.nd { width: 440px; padding: 44px 30px; border-radius: 22px; border: 1px solid var(--line); background: rgba(15,17,22,.88); }
.nd.main { width: 520px; border: 2px solid var(--c400); background: linear-gradient(135deg, rgba(34,211,238,.20), rgba(99,102,241,.16)); }
.nt { font: 700 40px/1.15 var(--display); }
.ns { margin-top: 18px; font-size: 28px; color: #c9d1dd; line-height: 1.3; }
.wire { width: 110px; height: 4px; background: linear-gradient(90deg, var(--c400), var(--i500)); transform-origin: left; }`,
    pose($, t) {
      headIn($, data, t)
      N.forEach((n, i) => {
        rise($('nd' + i), eo(seg(t, n.at, n.at + 0.5)), 22)
        if (i) $('wr' + i).style.transform = `scaleX(${eio(seg(t, n.at - 0.35, n.at + 0.05))})`
      })
      linesIn($, data.lines, t)
    },
  }
}

function grid(data) {
  const S = data.stats
  const struck = new Set(data.strike)
  const idx = [...Array(data.count).keys()]
  return {
    html: `${head(data)}
  <div class="gq">
    <div class="qs" style="grid-template-columns:repeat(${data.cols},1fr)">
      ${idx.map((i) => `<div class="q" id="q${i}"><u id="x${i}"></u></div>`).join('')}
    </div>
    <div class="sts">
      ${S.map((s, i) => `<div class="st" id="s${i}"><div class="sb grad">${s.big}</div><div class="sl">${s.label}</div></div>`).join('')}
    </div>
  </div>`,
    css: `
.gq { display: flex; align-items: center; gap: 110px; margin-top: 80px; }
.qs { display: grid; gap: 22px; }
.q { position: relative; width: 104px; height: 104px; border-radius: 16px; border: 1px solid var(--c600);
  background: linear-gradient(135deg, rgba(34,211,238,.30), rgba(99,102,241,.22)); }
.q u { position: absolute; left: 14px; right: 14px; top: 50%; height: 5px; margin-top: -2px; border-radius: 3px;
  background: var(--bad); transform: rotate(-45deg) scaleX(0); }
.sts { position: relative; width: 800px; height: 330px; text-align: left; }
.st { position: absolute; left: 0; top: 0; right: 0; }
.sb { font: 800 100px/1 var(--display); white-space: nowrap; display: inline-block; }
.sl { margin-top: 30px; font-size: 40px; font-weight: 500; color: #c9d1dd; line-height: 1.25; }`,
    pose($, t) {
      headIn($, data, t)
      idx.forEach((i) => {
        const el = $('q' + i)
        rise(el, eo(seg(t, 0.4 + i * 0.05, 0.85 + i * 0.05)), 16)
        if (struck.has(i)) {
          const k = [...struck].indexOf(i)
          const p = eio(seg(t, data.strikeAt + k * 0.22, data.strikeAt + 0.5 + k * 0.22))
          el.style.opacity = Math.min(Number(el.style.opacity), 1 - 0.62 * p)
          $('x' + i).style.transform = `rotate(-45deg) scaleX(${p})`
        }
      })
      S.forEach((s, i) => {
        const next = S[i + 1]?.at ?? Infinity
        blurIn($('s' + i), seg(t, s.at, s.at + 0.6), 16)
        $('s' + i).style.opacity = Math.min(Number($('s' + i).style.opacity), 1 - eio(seg(t, next - 0.4, next)))
      })
    },
  }
}

function tools(data) {
  const T = data.tools
  const fill = data.fillAt
  return {
    html: `${head(data)}
  <div class="tls">
    ${T.map(
      (name, i) => `
    <div class="tl" id="tl${i}"><i id="ok${i}"></i>
      <div class="tn">${name}</div>
      <div class="td">description <b>sent</b></div>
      <div class="ts">inputSchema</div>
      <pre class="sc" id="sc${i}"></pre>
    </div>`
    ).join('')}
  </div>
  <div class="chips">${(data.chips || []).map((c, i) => `<div class="chip" id="ch${i}">${c.text}</div>`).join('')}</div>`,
    css: `
.tls { display: flex; gap: 34px; margin-top: 70px; text-align: left; }
.tl { position: relative; width: 500px; padding: 34px 36px; border-radius: 18px; border: 2px solid var(--warn); background: rgba(15,17,22,.9); }
.tl i { position: absolute; inset: -2px; border-radius: 18px; border: 2px solid var(--c400); opacity: 0; }
.tn { font: 600 36px var(--mono); color: var(--c300); }
.td { margin-top: 14px; font-size: 26px; color: var(--muted); }
.td b { color: var(--good); font-weight: 600; }
.ts { margin-top: 26px; font: 500 22px var(--mono); color: var(--muted); letter-spacing: .04em; }
.sc { margin-top: 10px; height: 190px; padding: 18px 20px; border-radius: 12px; background: #030712; border: 1px solid var(--line);
  font: 500 25px/1.42 var(--mono); color: var(--ink); white-space: pre; }
.chips { display: flex; gap: 26px; margin-top: 56px; height: 72px; }
.chip { padding: 0 34px; border-radius: 36px; font: 600 32px/70px var(--body); border: 1px solid var(--line); background: rgba(15,17,22,.86); color: #dfe5ee; }`,
    pose($, t) {
      headIn($, data, t)
      T.forEach((_, i) => {
        rise($('tl' + i), eo(seg(t, 0.4 + i * 0.25, 0.9 + i * 0.25)), 24)
        const at = fill + i * 0.3
        // the schema box empties through a dip, then the real schema types in
        const sc = $('sc' + i)
        sc.textContent = t < at ? data.empty : typed(data.full, t, at, 60)
        sc.style.opacity = Math.min(1, 0.15 + 0.85 * (Math.abs(t - at) / 0.15))
        $('ok' + i).style.opacity = eio(seg(t, at + 0.2, at + 0.9))
      })
      ;(data.chips || []).forEach((c, i) => blurIn($('ch' + i), seg(t, c.at, c.at + 0.55), 12))
    },
  }
}

function corpus(data) {
  const cols = 27
  const rowsN = 9
  const mid = Math.floor(rowsN / 2) * cols + Math.floor(cols / 2)
  const cells = [...Array(cols * rowsN).keys()]
  const dist = (i) => Math.hypot((i % cols) - Math.floor(cols / 2), (Math.floor(i / cols) - Math.floor(rowsN / 2)) * 1.3)
  const z = data.zoomAt
  return {
    html: `${head(data)}
  <div class="fld" id="fld">
    ${cells.map((i) => `<div class="dc${i === mid ? ' one' : ''}" id="k${i}"><s></s><s></s><s></s></div>`).join('')}
  </div>
  ${linesHtml(data.lines)}`,
    css: `
.fld { display: grid; grid-template-columns: repeat(${cols}, 44px); gap: 14px; margin-top: 60px; transform-origin: 50% 50%; }
.dc { width: 44px; height: 56px; border-radius: 6px; border: 1px solid #2c3646; background: rgba(15,17,22,.9); padding: 9px 7px; }
.dc s { display: block; height: 3px; margin-bottom: 6px; border-radius: 2px; background: #2c3646; }
.dc s:last-child { width: 60%; }
.dc.one { border-color: var(--c400); background: linear-gradient(135deg, rgba(34,211,238,.34), rgba(99,102,241,.26)); }
.dc.one s { background: var(--c300); }`,
    pose($, t) {
      headIn($, data, t)
      const p = eio(seg(t, z, z + 2.2))
      $('fld').style.transform = `scale(${6 - 5 * p})`
      cells.forEach((i) => {
        const el = $('k' + i)
        if (i === mid) el.style.opacity = seg(t, 0.4, 0.9)
        else el.style.opacity = eo(seg(t, z + 0.2 + dist(i) * 0.09, z + 0.8 + dist(i) * 0.09))
      })
      linesIn($, data.lines, t)
    },
  }
}

function end(data) {
  return {
    html: `
  <div id="mark">${tile(120, 28)}</div>
  <div class="et grad" id="et">${data.title}</div>
  <div class="sub" id="el" style="margin-top:34px;color:var(--ink);font-weight:600">${data.line}</div>
  ${data.repo ? `<div class="er" id="er">${data.repo}</div>` : ''}
  <div class="eu" id="eu">${data.url}</div>
  ${data.client ? `<div class="ec" id="ec">${data.client}</div>` : ''}`,
    css: `
.et { font: 800 112px var(--display); margin-top: 44px; display: inline-block; }
.er { margin-top: 40px; font: 500 30px var(--mono); color: var(--c300); }
.eu { margin-top: 22px; font: 700 40px var(--display); }
.ec { margin-top: 22px; font-size: 28px; color: var(--muted); }`,
    pose($, t) {
      blurIn($('mark'), seg(t, 0.1, 0.6), 16)
      blurIn($('et'), seg(t, 0.35, 1.05), 28)
      blurIn($('el'), seg(t, 1.0, 1.55), 14)
      if (data.repo) blurIn($('er'), seg(t, 1.5, 2.05), 12)
      blurIn($('eu'), seg(t, 1.8, 2.35), 12)
      if (data.client) blurIn($('ec'), seg(t, 2.1, 2.65), 12)
    },
  }
}

const KINDS = { title, rungs, counters, band, board, bars, flow, grid, tools, corpus, end }

export default function research(data) {
  const kind = KINDS[data.kind]
  if (!kind) throw new Error(`unknown research kind "${data.kind}"; expected ${Object.keys(KINDS).join(', ')}`)
  const k = kind(data)
  const total = data.duration || 8
  return {
    width: W,
    height: H,
    total,
    poster: 0.8 * total,
    css: CSS + k.css,
    html: `<div class="bg"></div><div class="gridbg"></div><div class="frame" id="content">${k.html}</div>`,
    setup(ctx) {
      const { $ } = ctx
      return (t) => {
        envelope($('content'), t, total, { push: 0.025 })
        k.pose($, t)
      }
    },
  }
}
