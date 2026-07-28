/*
 * cursor — the synthetic pointer drawn into the page.
 *
 * Playwright's screenshots never contain the OS cursor, so a demo driven by
 * page.mouse would show the UI reacting to something invisible. This injects a
 * pointer we draw ourselves and position in lockstep with the real mouse: hover
 * styles, row highlights and focus rings all come from the actual mouse being
 * there, while the arrow in the frame is ours.
 *
 * Installed with addInitScript, so it survives every navigation. That runs at
 * document-start, when documentElement and head are still null - so the API is
 * published immediately and the DOM half mounts lazily on first use. Touching
 * the document eagerly throws, and an init script that throws fails silently:
 * the demo still records, just with no pointer in it.
 */

// Runs in the page. Kept dependency-free and idempotent.
export function installCursor(opts) {
  const ID = '__rsdemo_cursor';
  if (window.__rsCursor) return;

  const SIZE = (opts && opts.size) || 30;
  const ACCENT = (opts && opts.accent) || '#00D1B2';
  // Arrow tip inside the 24x24 viewBox, so the drawn point lands on (x, y).
  const TIP_X = (5.5 / 24) * SIZE;
  const TIP_Y = (3.2 / 24) * SIZE;

  const state = { x: -100, y: -100, press: 0, visible: true };
  let root = null;
  let arrow = null;
  let ripple = null;

  function mount() {
    if (root && root.isConnected) return true;
    const host = document.body || document.documentElement;
    if (!host) return false;

    if (!root) {
      root = document.createElement('div');
      root.id = ID;
      root.setAttribute('aria-hidden', 'true');
      root.style.cssText = [
        'position:fixed', 'left:0', 'top:0', 'width:0', 'height:0',
        'z-index:2147483647', 'pointer-events:none', 'margin:0', 'padding:0',
      ].join(';');

      ripple = document.createElement('div');
      ripple.style.cssText = [
        'position:absolute', 'left:0', 'top:0', 'border-radius:50%',
        'pointer-events:none', 'opacity:0',
        'border:2px solid ' + ACCENT, 'background:' + ACCENT + '22',
      ].join(';');

      arrow = document.createElement('div');
      arrow.style.cssText = [
        'position:absolute', 'left:0', 'top:0',
        'width:' + SIZE + 'px', 'height:' + SIZE + 'px',
        'transform-origin:' + TIP_X + 'px ' + TIP_Y + 'px',
        'filter:drop-shadow(0 2px 4px rgba(0,0,0,.55))',
      ].join(';');
      arrow.innerHTML =
        '<svg viewBox="0 0 24 24" width="' + SIZE + '" height="' + SIZE + '" xmlns="http://www.w3.org/2000/svg">' +
        '<path d="M5.5,3.21V20.8c0,.45.54.67.85.35l4.86-4.86a.5.5,0,0,1,.35-.15h6.87a.5.5,0,0,0,.35-.85L6.35,2.86a.5.5,0,0,0-.85.35Z" ' +
        'fill="#ffffff" stroke="#0b1020" stroke-width="1.4" stroke-linejoin="round"/></svg>';

      root.appendChild(ripple);
      root.appendChild(arrow);
    }
    host.appendChild(root);

    // The driver scrolls frame by frame, so the app's own smooth-scroll would
    // fight it. Scrollbars get a neutral treatment so they do not read as an OS
    // artifact in the frame.
    if (!document.getElementById(ID + '_css')) {
      const css = document.createElement('style');
      css.id = ID + '_css';
      css.textContent =
        'html{scroll-behavior:auto !important}' +
        '*::-webkit-scrollbar{width:10px;height:10px}' +
        '*::-webkit-scrollbar-thumb{background:rgba(140,160,200,.35);border-radius:5px}' +
        '*::-webkit-scrollbar-track{background:transparent}';
      (document.head || host).appendChild(css);
    }
    return true;
  }

  function paint() {
    if (!mount()) return;
    const s = 1 - 0.16 * state.press; // the arrow dips slightly on press
    arrow.style.transform =
      'translate(' + (state.x - TIP_X) + 'px,' + (state.y - TIP_Y) + 'px) scale(' + s + ')';
    root.style.opacity = state.visible ? '1' : '0';
  }

  window.__rsCursor = {
    set(x, y) { state.x = x; state.y = y; paint(); },
    press(t) { state.press = Math.max(0, Math.min(1, t)); paint(); },
    show(v) { state.visible = v !== false; paint(); },
    /*
     * t runs 0..1 across the click. The ring expands and fades, which is the
     * only cue in the frame that a click actually happened.
     */
    ripple(t) {
      if (!mount()) return;
      if (t == null || t <= 0 || t >= 1) { ripple.style.opacity = '0'; return; }
      const e = 1 - Math.pow(1 - t, 3);
      const r = 6 + 40 * e;
      ripple.style.width = r * 2 + 'px';
      ripple.style.height = r * 2 + 'px';
      ripple.style.transform = 'translate(' + (state.x - r) + 'px,' + (state.y - r) + 'px)';
      ripple.style.opacity = String(0.85 * (1 - e));
    },
    // Re-attach after a client-side route change detaches the node, and report
    // whether the pointer is actually on screen so the driver can fail loudly
    // rather than silently recording a cursorless demo.
    ensure() { paint(); return Boolean(root && root.isConnected); },
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', paint, { once: true });
  }
  paint();
}
