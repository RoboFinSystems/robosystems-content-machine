/*
 * The standard end card: the mark, roboledger.ai, the promise, and the client
 * line, arriving in order and holding. Matches the landing hero's close.
 *
 * data: { line?, cta?, note?, duration? }
 */
import { blurIn, seg, tile } from '/demos/kit.js'
import { BACKDROP, BRAND_CSS, envelope, H, W } from './brand.js'

export default function outro(data = {}) {
  const total = data.duration || 5.5
  const html = `${BACKDROP}
<div class="frame" id="content">
  <div id="mark">${tile(120, 28)}</div>
  <div class="url grad" id="url">roboledger.ai</div>
  <div class="sub" id="line" style="margin-top:34px;color:var(--ink);font-weight:600">${data.line || 'Nothing writes back until you post an entry.'}</div>
  <div class="client" id="client">Works with Claude, ChatGPT, or any MCP client</div>
  ${data.cta ? `<div class="cta" id="cta">${data.cta}</div>` : ''}
  ${data.note ? `<div class="note" id="note">${data.note}</div>` : ''}
</div>`
  const css = `${BRAND_CSS}
.url { font: 800 124px var(--display); margin-top: 40px; }
.client { font-size: 30px; color: var(--muted); margin-top: 26px; }
.cta { margin-top: 46px; padding: 18px 36px; border-radius: 14px; font-size: 30px; font-weight: 600;
  background: linear-gradient(90deg, var(--v600), var(--p500)); color: #fff; }
.note { position: absolute; bottom: 48px; left: 0; right: 0; font-size: 20px; color: var(--dim); }
`
  return {
    width: W,
    height: H,
    total,
    poster: 3.4,
    css,
    html,
    setup(ctx) {
      const { $ } = ctx
      return (t) => {
        envelope($('content'), t, total, { push: 0.02 })
        blurIn($('mark'), seg(t, 0.1, 0.6), 16)
        blurIn($('url'), seg(t, 0.35, 1.05), 28)
        blurIn($('line'), seg(t, 1.0, 1.55), 14)
        blurIn($('client'), seg(t, 1.4, 1.95), 12)
        if (data.cta) blurIn($('cta'), seg(t, 1.9, 2.45), 12)
        if (data.note) $('note').style.opacity = seg(t, 2.2, 2.7)
      }
    },
  }
}
