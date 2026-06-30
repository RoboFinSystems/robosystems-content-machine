"""
short_design.py — design primitives for the footage-free 9:16 Short renderer.

This is the code half of the parked Claude Design template
(local/archive/short_9x16_design_brief.md): a 1080x1920, navy-ground, teal-accent,
Space-Grotesk, *data-forward* system where the hero of every frame is a number or a
thesis — never b-roll. It provides:

  - tokens        brand colours, safe zones, the hero band
  - fonts()       cached Space Grotesk + Orbitron loaders (vendored in assets/fonts)
  - ground()      the static navy gradient + persistent wordmark chrome (rendered once)
  - classify_card()  card text -> (archetype, payload)  [Stage-1 inference, no schema change]
  - render_frame(kind, payload, t)  a full 1080x1920 PIL frame, animated by t in [0,1]

The assembler renders an entrance sequence (t: 0->1) + a settled still (t=1) per beat
and stitches them with ffmpeg. Everything here is pure Pillow — no b-roll, no network.
"""

import os
import re
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = os.path.join(ROOT, "assets", "fonts")
BRAND_DIR = os.path.join(ROOT, "assets", "brand")

W, H = 1080, 1920

# ── brand tokens (RGB) ──
NAVY = (10, 31, 68)        # #0A1F44 ground
TEAL = (0, 209, 178)       # #00D1B2 accent / key number
ALERT = (238, 108, 77)     # #EE6C4D bear / negative beat
WHITE = (255, 255, 255)
MUTED = (150, 170, 202)    # label grey-blue
CHROME = (120, 140, 176)   # persistent wordmark

# ── safe zones (design brief: top 10%, bottom 20%, right 12%) ──
SAFE_TOP = int(H * 0.10)
SAFE_BOTTOM = H - int(H * 0.20)
HERO_TOP = int(H * 0.25)
HERO_BOTTOM = int(H * 0.70)
HERO_MID = (HERO_TOP + HERO_BOTTOM) // 2
MARGIN = 90                      # horizontal text margin
TEXT_W = W - 2 * MARGIN          # usable text width


# ── fonts ────────────────────────────────────────────────────────────────────
@lru_cache(maxsize=128)
def font(family, weight, size):
    """Cached truetype loader. Falls back to the variable font, then default."""
    for name in (f"{family}-{weight}.ttf", f"{family}-VariableFont_wght.ttf"):
        path = os.path.join(FONT_DIR, name)
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


# ── small math / easing ──────────────────────────────────────────────────────
def clamp01(t):
    return 0.0 if t < 0 else (1.0 if t > 1 else t)


def lerp(a, b, t):
    return a + (b - a) * t


def _eo(t):                       # cubic ease-out
    t = clamp01(t)
    return 1 - (1 - t) ** 3


def _eob(t):                      # ease-out-back (slight overshoot, for slams)
    t = clamp01(t)
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


# ── text helpers ─────────────────────────────────────────────────────────────
def line_height(fnt):
    a, d = fnt.getmetrics()
    return a + d


def wrap(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [text]


def fit(draw, text, family, weight, max_w, start, min_size, max_lines):
    """Largest size at which `text` wraps to <= max_lines within max_w."""
    size = start
    while size >= min_size:
        f = font(family, weight, size)
        lines = wrap(draw, text, f, max_w)
        if len(lines) <= max_lines and max(draw.textlength(ln, font=f) for ln in lines) <= max_w:
            return f, lines
        size -= 6
    f = font(family, weight, min_size)
    return f, wrap(draw, text, f, max_w)


def draw_tracked(draw, s, fnt, cx, y, rgb, tracking=0):
    """Draw a single line centred on cx, with optional letter-spacing."""
    widths = [draw.textlength(ch, font=fnt) for ch in s]
    total = sum(widths) + tracking * max(0, len(s) - 1)
    x = cx - total / 2
    for ch, w in zip(s, widths):
        draw.text((x, y), ch, font=fnt, fill=rgb)
        x += w + tracking


def draw_emph(draw, line, fnt, cx, y, base_rgb, num_rgb=TEAL):
    """Centre a line; tint any token containing a digit with num_rgb (the data is the hero)."""
    toks = line.split(" ")
    widths = [draw.textlength(t, font=fnt) for t in toks]
    sp = draw.textlength(" ", font=fnt)
    total = sum(widths) + sp * (len(toks) - 1)
    x = cx - total / 2
    for t, w in zip(toks, widths):
        rgb = num_rgb if re.search(r"\d", t) else base_rgb
        draw.text((x, y), t, font=fnt, fill=rgb + (255,) if len(rgb) == 3 else rgb)
        x += w + sp


def _block(draw, lines, fnt, top, rgb, emph=True, gap_ratio=0.14):
    lh = line_height(fnt)
    gap = int(lh * gap_ratio)
    y = top
    for ln in lines:
        if emph:
            draw_emph(draw, ln, fnt, W / 2, y, rgb)
        else:
            draw_tracked(draw, ln, fnt, W / 2, y, rgb + (255,))
        y += lh + gap
    return y


def _block_height(fnt, n, gap_ratio=0.14):
    lh = line_height(fnt)
    return n * lh + (n - 1) * int(lh * gap_ratio)


# ── number parsing (for count-up) ────────────────────────────────────────────
def parse_num(num):
    num = num.replace("−", "-")
    m = re.search(r"-?\d[\d,]*(?:\.\d+)?", num)
    if not m:
        return ("", 0.0, num, 0, False)
    core = m.group(0)
    prefix, suffix = num[:m.start()], num[m.end():]
    decimals = len(core.split(".")[1]) if "." in core else 0
    return (prefix, float(core.replace(",", "")), suffix, decimals, "," in core)


def fmt_num(prefix, value, suffix, decimals, comma):
    body = f"{value:,.{decimals}f}" if (comma or value >= 1000) else f"{value:.{decimals}f}"
    return f"{prefix}{body}{suffix}"


# ── ground + chrome (static, rendered once) ──────────────────────────────────
@lru_cache(maxsize=1)
def _gradient():
    top, bot = (17, 43, 92), (6, 16, 38)
    col = Image.new("RGB", (1, H))
    px = col.load()
    for y in range(H):
        t = y / (H - 1)
        px[0, y] = (round(lerp(top[0], bot[0], t)),
                    round(lerp(top[1], bot[1], t)),
                    round(lerp(top[2], bot[2], t)))
    return col.resize((W, H))


@lru_cache(maxsize=8)
def _mark(height, color):
    """The RoboSystems mark (assets/brand/robosystems_mark.png — white glyph on transparent),
    scaled to `height` and tinted `color`. None if the asset is missing (chrome degrades to text)."""
    path = os.path.join(BRAND_DIR, "robosystems_mark.png")
    if not os.path.exists(path):
        return None
    m = Image.open(path).convert("RGBA")
    w = max(1, round(height * m.width / m.height))
    m = m.resize((w, height), Image.LANCZOS)
    tint = Image.new("RGBA", m.size, color + (0,))
    tint.putalpha(m.split()[3])
    return tint


@lru_cache(maxsize=4)
def _claude_burst(height):
    """The Claude sunburst (assets/brand/claude.png — orange on transparent), scaled to `height`.
    Co-brand mark for any card whose text names Claude. None if the asset is missing."""
    path = os.path.join(BRAND_DIR, "claude.png")
    if not os.path.exists(path):
        return None
    m = Image.open(path).convert("RGBA")
    w = max(1, round(height * m.width / m.height))
    return m.resize((w, height), Image.LANCZOS)


@lru_cache(maxsize=1)
def ground():
    """Navy gradient + a faint teal hero glow + the persistent brand lockup (mark + wordmark)."""
    img = _gradient().convert("RGBA")
    # faint teal glow behind the hero band (depth, on-brand)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse(
        [W * 0.5 - 560, HERO_MID - 460, W * 0.5 + 560, HERO_MID + 460], fill=TEAL + (22,))
    glow = glow.filter(ImageFilter.GaussianBlur(170))
    img = Image.alpha_composite(img, glow).convert("RGB")
    # top brand lockup: the mark above the wordmark
    mark = _mark(58, CHROME)
    wy = 92
    if mark is not None:
        img.paste(mark, ((W - mark.width) // 2, 30), mark)
        wy = 30 + mark.height + 16
    d = ImageDraw.Draw(img, "RGBA")
    draw_tracked(d, "ROBOSYSTEMS", font("Orbitron", "Bold", 26), W / 2, wy, CHROME + (255,),
                 tracking=9)
    return img


# ── archetype renderers ──────────────────────────────────────────────────────
def _new_layer():
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    return layer, ImageDraw.Draw(layer)


def _paste(base, layer, dy=0, scale=1.0, alpha=1.0):
    if alpha <= 0:
        return base
    if scale != 1.0:
        nw, nh = max(1, round(W * scale)), max(1, round(H * scale))
        layer = layer.resize((nw, nh), Image.LANCZOS)
        ox, oy = (W - nw) // 2, (H - nh) // 2 + dy
    else:
        ox, oy = 0, dy
    if alpha < 1.0:
        r, g, b, a = layer.split()
        a = a.point(lambda v: int(v * alpha))
        layer = Image.merge("RGBA", (r, g, b, a))
    base.paste(layer, (int(ox), int(oy)), layer)
    return base


def _slam(base, layer, t):
    _paste(base, layer, scale=lerp(1.10, 1.0, _eob(t)), alpha=clamp01(t * 1.7))


def _rise(base, layer, t):
    _paste(base, layer, dy=int(lerp(70, 0, _eo(t))), alpha=clamp01(t * 1.6))


def _accent_bar(d, cy, w=150, color=TEAL):
    d.rounded_rectangle([W / 2 - w / 2, cy, W / 2 + w / 2, cy + 10], radius=5, fill=color + (255,))


def _f_hook(base, p, t):
    layer, d = _new_layer()
    f, lines = fit(d, p["text"].upper(), "SpaceGrotesk", "Bold", TEXT_W, 152, 70, 4)
    top = HERO_MID - _block_height(f, len(lines)) // 2
    _accent_bar(d, top - 52)
    _block(d, lines, f, top, WHITE)
    _slam(base, layer, t)


def _f_headline(base, p, t):
    layer, d = _new_layer()
    f, lines = fit(d, p["text"].upper(), "SpaceGrotesk", "Bold", TEXT_W, 140, 64, 4)
    bh = _block_height(f, len(lines))
    burst = _claude_burst(170) if "CLAUDE" in p["text"].upper() else None
    if burst is not None:
        gap = 48
        gtop = HERO_MID - (burst.height + gap + bh) // 2
        layer.paste(burst, ((W - burst.width) // 2, gtop), burst)
        _block(d, lines, f, gtop + burst.height + gap, WHITE)
    else:
        _block(d, lines, f, HERO_MID - bh // 2, WHITE)
    _slam(base, layer, t)


def _f_alert(base, p, t):
    layer, d = _new_layer()
    text = p["text"].upper().lstrip("…. ")
    f, lines = fit(d, text, "SpaceGrotesk", "Bold", TEXT_W, 150, 68, 4)
    top = HERO_MID - _block_height(f, len(lines)) // 2
    _accent_bar(d, top - 52, color=ALERT)
    _block(d, lines, f, top, ALERT, emph=False)
    _slam(base, layer, t)


def _f_hero(base, p, t):
    layer, d = _new_layer()
    prefix, value, suffix, dec, comma = parse_num(p["number"])
    final = fmt_num(prefix, value, suffix, dec, comma)
    nf = font("SpaceGrotesk", "Bold", 300)
    while d.textlength(final, font=nf) > TEXT_W and nf.size > 120:
        nf = font("SpaceGrotesk", "Bold", nf.size - 12)
    fullw = d.textlength(final, font=nf)
    nlh = line_height(nf)
    ny = HERO_MID - nlh // 2 - 30
    # count-up
    shown = fmt_num(prefix, value * _eo(clamp01(t / 0.8)), suffix, dec, comma)
    sw = d.textlength(shown, font=nf)
    d.text((W / 2 - sw / 2, ny), shown, font=nf, fill=WHITE + (255,))
    # teal underline wipe
    wt = _eo(clamp01((t - 0.45) / 0.55))
    uy = ny + nlh + 4
    if wt > 0:
        d.rounded_rectangle([W / 2 - fullw / 2, uy, W / 2 - fullw / 2 + fullw * wt, uy + 14],
                            radius=7, fill=TEAL + (255,))
    # label
    lf = font("SpaceGrotesk", "Medium", 56)
    la = int(255 * clamp01((t - 0.35) / 0.4))
    if la > 0:
        draw_tracked(d, p["label"].upper(), lf, W / 2, uy + 42, MUTED + (la,), tracking=3)
    base.paste(layer, (0, 0), layer)


def _f_stat(base, p, t):
    layer, d = _new_layer()
    fa, la = fit(d, p["a"].upper(), "SpaceGrotesk", "Bold", TEXT_W, 104, 56, 2)
    fb, lb = fit(d, p["b"].upper(), "SpaceGrotesk", "Bold", TEXT_W, 104, 56, 2)
    ha = _block_height(fa, len(la))
    hb = _block_height(fb, len(lb))
    gap = 70
    top = HERO_MID - (ha + gap + hb) // 2
    # fact A (in first), divider, fact B (in second)
    aa = clamp01(t / 0.55)
    ab = clamp01((t - 0.35) / 0.55)
    la_layer, lad = _new_layer()
    _block(lad, la, fa, top, WHITE)
    _paste(base, la_layer, alpha=aa)
    d.ellipse([W / 2 - 7, top + ha + gap / 2 - 7, W / 2 + 7, top + ha + gap / 2 + 7],
              fill=TEAL + (int(255 * ab),))
    lb_layer, lbd = _new_layer()
    _block(lbd, lb, fb, top + ha + gap, WHITE)
    _paste(base, lb_layer, alpha=ab)
    base.paste(layer, (0, 0), layer)


def _f_identity(base, p, t):
    layer, d = _new_layer()
    cf, clines = fit(d, p["company"].upper(), "Orbitron", "Bold", TEXT_W, 116, 44, 2)
    ch = _block_height(cf, len(clines))
    top = HERO_MID - ch // 2 - 40
    _block(d, clines, cf, top, WHITE, emph=False)
    # ticker chip
    chip = f'{p["exchange"]}: {p["ticker"]}'
    chf = font("SpaceGrotesk", "SemiBold", 56)
    cw = d.textlength(chip, font=chf)
    chh = line_height(chf)
    cy = top + ch + 48
    pad_x, pad_y = 44, 22
    box = [W / 2 - cw / 2 - pad_x, cy, W / 2 + cw / 2 + pad_x, cy + chh + 2 * pad_y]
    ca = int(255 * clamp01((t - 0.4) / 0.5))
    d.rounded_rectangle(box, radius=18, outline=TEAL + (ca,), width=4)
    d.text((W / 2 - cw / 2, cy + pad_y), chip, font=chf, fill=WHITE + (ca,))
    _rise(base, layer, t)


def _f_question(base, p, t):
    layer, d = _new_layer()
    f, lines = fit(d, p["text"].upper(), "SpaceGrotesk", "Bold", TEXT_W, 140, 60, 5)
    top = HERO_MID - _block_height(f, len(lines)) // 2
    _block(d, lines, f, top, WHITE)
    _rise(base, layer, t)


def _f_cta(base, p, t):
    layer, d = _new_layer()
    f, lines = fit(d, p["line"].upper(), "SpaceGrotesk", "Bold", TEXT_W, 120, 54, 4)
    top = HERO_MID - _block_height(f, len(lines)) // 2 - 40
    bottom = _block(d, lines, f, top, WHITE)
    _accent_bar(d, bottom + 36)
    sf = font("SpaceGrotesk", "Medium", 44)
    draw_tracked(d, p.get("secondary", ""), sf, W / 2, bottom + 70, MUTED + (255,), tracking=1)
    hf = font("Orbitron", "Bold", 40)
    draw_tracked(d, p.get("handle", "@RoboFinSystems"), hf, W / 2, SAFE_BOTTOM - 30, TEAL + (255,),
                 tracking=4)
    _rise(base, layer, t)


_RENDERERS = {
    "hook": _f_hook, "headline": _f_headline, "alert": _f_alert, "hero": _f_hero,
    "stat": _f_stat, "identity": _f_identity, "question": _f_question, "cta": _f_cta,
}


def render_frame(kind, payload, t):
    """A full 1080x1920 RGB frame for `kind`, with entrance progress t in [0,1]."""
    base = ground().copy()
    _RENDERERS.get(kind, _f_headline)(base, payload, clamp01(t))
    return base


# ── card text -> (archetype, payload)  [Stage-1 inference; no schema change] ──
_EXCH = r"(NYSE AMERICAN|NYSE|NASDAQ|OTCQX|OTCQB|OTCMKTS|OTC|CSE|TSXV|TSX)"


# separators that mean "two facts in tension": ·•  arrows  em/en/hyphen dash  ". "  ", "
_SPLIT = re.compile(r"\s*[·•]\s*|\s*(?:→|⟶|➜|->)\s*|\s+[—–-]\s+|\.\s+|,\s+")


def _two_facts(s):
    parts = [p.strip(" .,") for p in _SPLIT.split(s) if p and p.strip(" .,")]
    if len(parts) == 2 and any(re.search(r"\d", p) for p in parts):
        return {"a": parts[0], "b": parts[1]}
    return None


def _hero_split(s):
    s = s.replace("−", "-")
    toks = list(re.finditer(r"-?\$?\d[\d,]*(?:\.\d+)?\s*(?:%|x|bps|B|M|K)?", s))
    if len(toks) != 1:
        return None
    m = toks[0]
    num = re.sub(r"\s+", "", m.group(0))
    label = (s[:m.start()] + " " + s[m.end():]).strip(" —–-·,.:")
    label = re.sub(r"\s*[—–-]\s*", " ", label).strip(" :")
    label = " ".join(label.split())
    if not label or len(label) > 22:
        return None
    return {"number": num, "label": label}


def classify_card(text, idx, n):
    """Map a caption card to a frame archetype + payload. Everything falls back to a
    full-bleed branded `headline`, so an unmatched card is still on-brand, never broken."""
    s = " ".join(text.split())
    up = s.upper()
    last = idx == n - 1
    cta_extra = {"secondary": "Full breakdown → pinned comment", "handle": "@RoboFinSystems"}

    m = re.search(_EXCH + r"\s*[:\-]?\s*([A-Z][A-Z.]{1,6})", up)
    if m:
        company = re.split(r"[—–-]", s)[0].strip() or s
        return ("identity", {"company": company, "exchange": m.group(1), "ticker": m.group(2)})
    if s.endswith("?"):
        return ("cta" if last else "question", {"line": s, "text": s, **cta_extra})
    if last:
        return ("cta", {"line": s, "text": s, **cta_extra})
    if s.startswith(("…", "...")) or re.search(r"\b(LOSS|BLAME|TRAP|BANKRUPT|DISTRESS|STILL)\b", up):
        return ("alert", {"text": s})
    facts = _two_facts(s)
    if facts:
        return ("stat", facts)
    hero = _hero_split(s)
    if hero:
        return ("hero", hero)
    if idx == 0:
        return ("hook", {"text": s})
    return ("headline", {"text": s})
