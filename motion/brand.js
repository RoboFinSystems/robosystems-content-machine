/*
 * The RoboLedger video look, shared by the intro, the end card and the slides:
 * the landing hero's backdrop (flat brand gradient over the site's grid) and
 * the type the landing demos use. The runtime and helpers come from the landing
 * kit (roboledger-app/public/demos/kit.js), mounted at /demos/ by the renderer.
 */
import { eio, seg } from '/demos/kit.js'

export const W = 1920
export const H = 1080

export const BACKDROP = `<div class="bg"></div><div class="gridbg"></div>`

export const BRAND_CSS = `
.stage { background: var(--bg); }
.bg { position: absolute; inset: 0;
  background: linear-gradient(135deg, rgba(76,29,149,.22), rgba(88,28,135,.14) 50%, rgba(112,26,117,.16)); }
.gridbg { position: absolute; inset: 0; opacity: .07;
  background-image: linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px);
  background-size: 64px 64px; }
.frame { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; padding: 0 160px; }
.eyebrow { font: 600 24px var(--display); letter-spacing: .32em; color: var(--v300); text-transform: uppercase; }
.headline { font: 800 104px/1.06 var(--display); letter-spacing: -.01em; }
.sub { font-size: 40px; font-weight: 500; color: #cfcbdc; line-height: 1.3; max-width: 1300px; }
.wd { display: inline-block; }
.rule { height: 4px; border-radius: 2px; background: linear-gradient(90deg, var(--v500), var(--f500)); transform-origin: center; }
`

/* Split a line into word spans for a blur-in, keeping spaces between them. */
export const words = (text, idPrefix, cls = '') =>
  text
    .split(' ')
    .map((w, i) => `<span class="wd${cls ? ' ' + cls : ''}" id="${idPrefix}${i}">${w}</span>`)
    .join(' ')

/*
 * The shared envelope of a template: content fades in from the backdrop at the
 * start and back into it at the end, and a slow push runs underneath, so every
 * cut between templates and live footage lands on the same backdrop.
 */
export function envelope(el, t, total, { push = 0.03 } = {}) {
  const f = Math.min(eio(seg(t, 0, 0.35)), 1 - eio(seg(t, total - 0.45, total)))
  el.style.opacity = f
  el.style.transform = `scale(${1 + push * eio(seg(t, 0, total))})`
}
