#!/usr/bin/env python3
"""Generate the branded X Article cover (5:2, 2000x800) for a project or a blog post.

A deterministic, local render: assets/backgrounds/background2.png (logo right,
open field left) + ticker / company / filing line typeset from the design
system, snapped via headless Chrome. Replaces the gpt-image 5:2 x-thumbnail as
the Article cover so the timeline shows a consistent research masthead above
the per-ticker video thumbnail instead of two similar covers stacked.

Blog mode swaps the ticker lettering for the post title, since a headline will
not fit the 150px Orbitron treatment a 4-letter ticker is built for.

Usage: gen_article_cover.py TICKER [--force]
       gen_article_cover.py <slug> --blog [--force]
Output: projects/{T}/charts/png/{T}_article_cover.png
        blog/<slug>/<slug>_article_cover.png
"""

import argparse
import datetime
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import blog_common

REPO = Path(__file__).resolve().parent.parent
BACKGROUND = REPO / "assets" / "backgrounds" / "background2.png"
FONTS = REPO / "design-system" / "fonts"
SNAP = REPO / "tools" / "webdeck" / "snap.mjs"
W, H = 2000, 800

PAGE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
@font-face {{ font-family: Orbitron; src: url("{fonts}/Orbitron-Bold.ttf"); font-weight: 700; }}
@font-face {{ font-family: "Space Grotesk"; src: url("{fonts}/SpaceGrotesk-Regular.ttf"); font-weight: 400; }}
@font-face {{ font-family: "Space Grotesk"; src: url("{fonts}/SpaceGrotesk-Medium.ttf"); font-weight: 500; }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ width: {w}px; height: {h}px; overflow: hidden; }}
.stage {{
  width: {w}px; height: {h}px; position: relative; background: #06103a;
  background-image: url("{bg}"); background-size: cover; background-position: center 38%;
}}
.text {{ position: absolute; left: 110px; top: 50%; transform: translateY(-50%); max-width: 1050px; }}
.eyebrow {{
  font: 500 34px "Space Grotesk"; letter-spacing: 0.34em; text-transform: uppercase;
  color: #9db9f7; margin-bottom: 34px;
}}
.eyebrow::after {{
  content: ""; display: block; width: 96px; height: 4px; background: #3b7af5;
  margin-top: 26px; border-radius: 2px;
}}
.ticker {{
  font: 700 150px Orbitron; color: #ffffff; letter-spacing: 0.02em; line-height: 1;
  text-shadow: 0 0 60px rgba(59, 122, 245, 0.55);
}}
.company {{ font: 500 52px "Space Grotesk"; color: #dbe6ff; margin-top: 30px; }}
.meta {{ font: 400 36px "Space Grotesk"; color: #8fa3cf; margin-top: 16px; }}
</style></head><body>
<div class="stage"><div class="text">
  <div class="eyebrow">RoboSystems Research</div>
  <div class="ticker">${ticker}</div>
  <div class="company">{company}</div>
  <div class="meta">{meta}</div>
</div></div>
</body></html>
"""


BLOG_PAGE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
@font-face {{ font-family: Orbitron; src: url("{fonts}/Orbitron-Bold.ttf"); font-weight: 700; }}
@font-face {{ font-family: "Space Grotesk"; src: url("{fonts}/SpaceGrotesk-Regular.ttf"); font-weight: 400; }}
@font-face {{ font-family: "Space Grotesk"; src: url("{fonts}/SpaceGrotesk-Medium.ttf"); font-weight: 500; }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ width: {w}px; height: {h}px; overflow: hidden; }}
.stage {{
  width: {w}px; height: {h}px; position: relative; background: #06103a;
  background-image: url("{bg}"); background-size: cover; background-position: center 38%;
}}
/* Narrower than the canvas suggests: the logo occupies the right ~40% of the
   background, so a wider block runs the headline into the mark. */
.text {{ position: absolute; left: 110px; top: 50%; transform: translateY(-50%); max-width: 1030px; }}
.eyebrow {{
  font: 500 30px "Space Grotesk"; letter-spacing: 0.34em; text-transform: uppercase;
  color: #9db9f7; margin-bottom: 30px;
}}
.eyebrow::after {{
  content: ""; display: block; width: 96px; height: 4px; background: #3b7af5;
  margin-top: 24px; border-radius: 2px;
}}
.title {{
  font: 700 {size}px Orbitron; color: #ffffff; letter-spacing: 0.01em; line-height: 1.16;
  text-shadow: 0 0 60px rgba(59, 122, 245, 0.55);
}}
.meta {{ font: 400 32px "Space Grotesk"; color: #8fa3cf; margin-top: 30px; }}
</style></head><body>
<div class="stage"><div class="text">
  <div class="eyebrow">RoboSystems</div>
  <div class="title">{title}</div>
  <div class="meta">{meta}</div>
</div></div>
</body></html>
"""


def title_size(title: str) -> int:
    """Orbitron is wide; step the headline down so long titles stay inside the 800px
    canvas instead of overflowing it. Deterministic, and close enough by inspection."""
    n = len(title)
    return 92 if n <= 28 else 74 if n <= 48 else 60 if n <= 72 else 50 if n <= 100 else 42


def _snap(html: str, out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
        f.write(html)
        tmp = f.name
    subprocess.run(["node", str(SNAP), "--html", tmp, "--out", str(out),
                    "--width", str(W), "--height", str(H)],
                   check=True, cwd=SNAP.parent)
    print(f"cover: {out} ({out.stat().st_size // 1024}KB)")
    return out


def build_blog(slug: str, force: bool) -> Path:
    d = REPO / "blog" / slug
    if not d.is_dir():
        sys.exit(f"no blog post at blog/{slug}/")
    out = d / f"{slug}_article_cover.png"
    if out.exists() and not force:
        print(f"exists: {out} (use --force to regenerate)")
        return out

    meta, body = blog_common.parse_post(slug)
    title = (meta.get("title") or slug.replace("-", " ")).strip()
    try:
        d_iso = blog_common.normalize_date(meta.get("date", ""))
        when = datetime.date.fromisoformat(d_iso).strftime("%B %Y")
    except ValueError:
        when = datetime.date.today().strftime("%B %Y")
    meta_line = f"{when} · {blog_common.reading_time_minutes(body)} min read"

    html = BLOG_PAGE.format(fonts=FONTS.as_uri(), bg=BACKGROUND.as_uri(), w=W, h=H,
                            size=title_size(title), title=html_escape(title), meta=meta_line)
    return _snap(html, out)


def html_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build(ticker: str, force: bool) -> Path:
    proj = REPO / "projects" / ticker
    out = proj / "charts" / "png" / f"{ticker}_article_cover.png"
    if out.exists() and not force:
        print(f"exists: {out} (use --force to regenerate)")
        return out

    meta = json.loads((proj / "scripts" / f"{ticker}_script.json").read_text())["metadata"]
    company = meta.get("company", ticker)
    filing = meta.get("filing_type", "")
    try:
        d = datetime.date.fromisoformat(meta.get("filing_date", ""))
        when = d.strftime("%B %Y")
    except ValueError:
        when = datetime.date.today().strftime("%B %Y")
    meta_line = f"{filing} Analysis · {when}" if filing else when

    html = PAGE.format(fonts=FONTS.as_uri(), bg=BACKGROUND.as_uri(),
                       w=W, h=H, ticker=ticker, company=company, meta=meta_line)
    return _snap(html, out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="TICKER, or a blog slug with --blog")
    ap.add_argument("--blog", action="store_true", help="target is a blog slug")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    if args.blog:
        build_blog(args.target, args.force)
    else:
        build(args.target.upper(), args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
