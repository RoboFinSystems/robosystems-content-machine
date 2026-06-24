"""
Assemble a paste-ready distribution pack for a blog post -> blog/<slug>/<slug>_postpack.md.

Like tools/build_postpack.py for research: it STITCHES (does not LLM-generate) the post's own
metadata + a hand/Cowork-authored blog/<slug>/<slug>_x_post.txt (if present) into per-channel
copy you paste natively. With no x_post.txt it falls back to a starter built from the
title/excerpt/URL + tag hashtags.

Usage:
    uv run python tools/build_blog_postpack.py financial-knowledge-graph-manifesto
"""

import argparse
import os
import sys

import blog_common as bc
from helpers import asset_url

CANONICAL = "https://robosystems.ai/blog/{slug}"


def hashtags(tags):
    out = []
    for t in tags or []:
        out.append("#" + "".join(w.capitalize() for w in str(t).replace("_", "-").split("-")))
    return " ".join(out)


def build(slug):
    if not bc.is_valid_slug(slug):
        sys.exit(f"Error: invalid slug '{slug}' (kebab-case expected).")
    post_dir = bc.blog_dir(slug)
    meta, body = bc.parse_post(slug)

    title = str(meta.get("title") or slug).strip()
    excerpt = bc.excerpt_fallback(meta, body)
    url = (meta.get("canonicalUrl") or CANONICAL.format(slug=slug)).strip()
    tags = meta.get("tags") or []

    x_path = os.path.join(post_dir, f"{slug}_x_post.txt")
    if os.path.exists(x_path):
        with open(x_path, encoding="utf-8") as f:
            x_post = f.read().strip()
    else:
        x_post = f"{title}\n\n{excerpt}\n\n{url}\n\n{hashtags(tags)}".strip()

    has_narration = os.path.exists(os.path.join(post_dir, f"{slug}_narration.mp3"))
    has_cover = os.path.exists(os.path.join(post_dir, "cover.png"))

    lines = [
        f"# Distribution pack — {title}",
        "",
        f"- **Post URL:** {url}",
        f"- **Reading time:** {bc.reading_time_minutes(body)} min",
        f"- **Tags:** {', '.join(map(str, tags)) or '—'}",
        f"- **Narration:** {'yes — ' + asset_url(f'blog/{slug}/{slug}_narration.mp3') if has_narration else 'none'}",
        f"- **Cover:** {'yes' if has_cover else 'none'}",
        "",
        "## X",
        "",
        x_post,
        "",
        "## LinkedIn",
        "",
        f"{title}",
        "",
        excerpt,
        "",
        url,
        "",
    ]
    out_path = os.path.join(post_dir, f"{slug}_postpack.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {out_path}")
    print(f"  X copy source: {'authored ' + x_path if os.path.exists(x_path) else 'auto-generated starter'}")


def main():
    ap = argparse.ArgumentParser(description="Build a paste-ready distribution pack for a blog post")
    ap.add_argument("slug", help="Post slug (the blog/<slug>/ folder name)")
    build(ap.parse_args().slug)


if __name__ == "__main__":
    main()
