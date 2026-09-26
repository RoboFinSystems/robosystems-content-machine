/*
 * The standard video open: the RoboLedger mark, a kicker, and the episode
 * title blurring in word by word over the brand backdrop.
 *
 * data: { kicker, title, sub?, duration? }
 */
import { blurIn, eio, seg, tile } from '/demos/kit.js'
import { BACKDROP, BRAND_CSS, envelope, H, W, words } from './brand.js'

export default function intro(data) {
  const title = data.title || 'Connect your books. Ask your AI.'
  const n = title.split(' ').length
  const total = data.duration || 4.8
  const html = `${BACKDROP}
<div class="frame" id="content">
  <div class="mark" id="mark">${tile(96, 24)}<span class="wm">RoboLedger</span></div>
  <div class="eyebrow" id="kick" style="margin-top:56px">${data.kicker || 'For finance leads'}</div>
  <div class="headline" style="margin-top:28px">${words(title, 'w')}</div>
  <div class="rule" id="rule" style="width:220px;margin-top:44px"></div>
  ${data.sub ? `<div class="sub" id="sub" style="margin-top:36px">${data.sub}</div>` : ''}
</div>`
  const css = `${BRAND_CSS}
.mark { display: flex; align-items: center; gap: 22px; }
.mark .wm { font: 700 52px var(--display); }
`
  return {
    width: W,
    height: H,
    total,
    poster: 2.6,
    css,
    html,
    setup(ctx) {
      const { $ } = ctx
      return (t) => {
        envelope($('content'), t, total)
        blurIn($('mark'), seg(t, 0.1, 0.7), 16)
        blurIn($('kick'), seg(t, 0.45, 1.0), 12)
        for (let i = 0; i < n; i++) blurIn($('w' + i), seg(t, 0.7 + i * 0.08, 1.35 + i * 0.08))
        $('rule').style.transform = `scaleX(${eio(seg(t, 1.2 + n * 0.08, 1.9 + n * 0.08))})`
        if (data.sub) blurIn($('sub'), seg(t, 1.6 + n * 0.08, 2.2 + n * 0.08), 12)
      }
    },
  }
}
