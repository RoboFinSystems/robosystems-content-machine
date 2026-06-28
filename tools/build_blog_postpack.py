"""
Assemble a paste-ready distribution pack for a blog post -> blog/<slug>/<slug>_postpack.md.

Like tools/build_postpack.py for research: it STITCHES (does not LLM-generate, does not post) the
post's own metadata + hand/Cowork-authored per-platform cuts into one paste-ready doc. Companion cuts
(all optional): blog/<slug>/<slug>_medium.md (syndicated essay), _linkedin.md (native), _x_post.txt.
Missing cuts fall back to a starter. Medium section carries the canonical-back-to-blog reminder so
syndication never cannibalizes the blog's SEO; the URL goes in LinkedIn's first comment, not the body.

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

    def companion(suffix):
        """Read a hand/Cowork-authored per-platform cut blog/<slug>/<slug>_<suffix>, or None."""
        p = os.path.join(post_dir, f"{slug}_{suffix}")
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                return f.read().strip()
        return None

    # Per-platform copy: authored companion if present, else a starter. No link in X/LinkedIn body
    # (links throttle reach — the URL goes in LinkedIn's first comment). Medium is a SYNDICATED copy of
    # the full essay; its canonical must point back to the blog so we don't cannibalize our own SEO.
    x_post = companion("x_post.txt") or f"{title}\n\n{excerpt}\n\n{hashtags(tags)}".strip()
    linkedin = companion("linkedin.md") or f"{title}\n\n{excerpt}\n\nWhat's your take?"
    medium = companion("medium.md") or body

    has_narration = os.path.exists(os.path.join(post_dir, f"{slug}_narration.mp3"))
    cover_url = asset_url(f"blog/{slug}/cover.png") if os.path.exists(os.path.join(post_dir, "cover.png")) else None

    lines = [
        f"# Distribution pack — {title}",
        "",
        f"- **Canonical (blog):** {url}",
        f"- **Reading time:** {bc.reading_time_minutes(body)} min",
        f"- **Tags:** {', '.join(map(str, tags)) or '—'}",
        f"- **Narration:** {'yes — ' + asset_url(f'blog/{slug}/{slug}_narration.mp3') if has_narration else 'none'}",
        f"- **Cover:** {cover_url or 'none'}",
        "",
        "## ☐ Pre-publish checklist",
        "",
        "- [ ] Blog published (canonical live at the URL above)",
        "- [ ] Medium: import/paste, then **set the canonical URL to the blog post** (Story → ⋯ → Advanced settings → Canonical link) — protects SEO",
        "- [ ] LinkedIn: post native; link goes in the **first comment**, not the body",
        "- [ ] Cover uploaded where supported",
        "",
        "## Medium  (syndicated — set canonical → blog on import)",
        "",
        f"_Canonical URL to set: {url}_",
        "",
        medium,
        "",
        "## LinkedIn  (native — no link in body)",
        "",
        linkedin,
        "",
        f"**First comment:** Full piece → {url}",
        "",
        "## X  (native post/thread)",
        "",
        x_post,
        "",
    ]
    out_path = os.path.join(post_dir, f"{slug}_postpack.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {out_path}")
    for s in ("medium.md", "linkedin.md", "x_post.txt"):
        print(f"  {s:13} {'authored' if os.path.exists(os.path.join(post_dir, f'{slug}_{s}')) else 'auto-starter'}")


def main():
    ap = argparse.ArgumentParser(description="Build a paste-ready distribution pack for a blog post")
    ap.add_argument("slug", help="Post slug (the blog/<slug>/ folder name)")
    build(ap.parse_args().slug)


if __name__ == "__main__":
    main()
