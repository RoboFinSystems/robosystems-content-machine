"""
Publish a blog post to the public S3 content store + refresh the blog catalog.

Narrates the post if it has no audio yet (default-on — every post ships with the "Listen to
this story" feature; pass --no-audio to skip), then uploads whatever exists in blog/<slug>/ to
s3://{AWS_S3_BUCKET}/blog/<slug>/ with correct content-types, writes a self-describing
meta.json, and rebuilds blog/index.json. A post with just post.md publishes cleanly; cover.png
and <slug>_x_post.txt are optional and additive.

The bucket + CloudFront CDN are managed by cloudformation/content.yaml (`just infra-deploy`);
public read covers content/* + blog/*. Public URLs go through AWS_CDN_DOMAIN_URL when set.

Usage:
    uv run python tools/publish_blog.py financial-knowledge-graph-manifesto
"""

import argparse
import datetime
import json
import os
import subprocess
import sys

import blog_common as bc
import narrate_blog
import reindex_blog
from helpers import asset_url, require_env

# (filename template under blog/<slug>/, content-type). Whatever exists gets published.
ARTIFACTS = [
    ("post.md", "text/markdown; charset=utf-8"),
    ("cover.png", "image/png"),
    ("{slug}_narration.mp3", "audio/mpeg"),
    ("{slug}_x_post.txt", "text/plain; charset=utf-8"),
]


def publish(slug, narrate=True):
    if not bc.is_valid_slug(slug):
        sys.exit(f"Error: invalid slug '{slug}' (kebab-case expected).")
    bucket = require_env("AWS_S3_BUCKET")
    post_dir = bc.blog_dir(slug)
    prefix = f"blog/{slug}/"
    if not os.path.exists(os.path.join(post_dir, "post.md")):
        sys.exit(f"Error: {post_dir}/post.md not found — nothing to publish.")

    # Default-on narration: every post ships with the "Listen to this story" audio (pass
    # --no-audio to skip). Resilient — a TTS hiccup logs a warning and still publishes the text.
    if narrate and not os.path.exists(os.path.join(post_dir, f"{slug}_narration.mp3")):
        print("Narrating (default-on; --no-audio to skip)...\n")
        try:
            narrate_blog.narrate(slug)
        except (SystemExit, Exception) as e:  # noqa: BLE001
            print(f"  (narration skipped: {e} — publishing text only; re-run later with `just blog-narrate {slug}`)")
        print()

    print(f"Publishing blog/{slug} -> s3://{bucket}/{prefix}\n")
    urls = []
    for name_tmpl, ctype in ARTIFACTS:
        name = name_tmpl.format(slug=slug)
        local = os.path.join(post_dir, name)
        if not os.path.exists(local):
            continue
        key = prefix + name
        r = subprocess.run(["aws", "s3", "cp", local, f"s3://{bucket}/{key}",
                            "--content-type", ctype, "--only-show-errors"])
        if r.returncode != 0:
            print(f"  FAILED: {name}")
            continue
        url = asset_url(key)
        print(f"  {url}  ({os.path.getsize(local) / 1e6:.2f} MB)")
        urls.append(url)

    # Self-describing post metadata (mirrors research meta.json); reindex prefers the local
    # post.md but this keeps each S3 folder independently describable.
    meta, body = bc.parse_post(slug)
    meta_obj = {
        "slug": slug,
        "title": str(meta.get("title") or slug).strip(),
        "date": bc.normalize_date(meta.get("date") or datetime.date.today().isoformat()),
        "author": meta.get("author") or "RoboSystems",
        "excerpt": bc.excerpt_fallback(meta, body),
        "metaDescription": meta.get("metaDescription") or None,
        "tags": meta.get("tags") or [],
        "keywords": meta.get("keywords") or [],
        "reading_time_minutes": bc.reading_time_minutes(body),
        "canonical_url": meta.get("canonicalUrl") or None,
    }
    subprocess.run(
        ["aws", "s3", "cp", "-", f"s3://{bucket}/{prefix}meta.json",
         "--content-type", "application/json; charset=utf-8",
         "--cache-control", "public, max-age=60", "--only-show-errors"],
        input=json.dumps(meta_obj, indent=2, ensure_ascii=False), text=True, check=True)

    print(f"\n{len(urls)} file(s) published. Refreshing blog catalog...\n")
    reindex_blog.run()
    return urls


def main():
    ap = argparse.ArgumentParser(description="Publish a blog post to S3 + reindex")
    ap.add_argument("slug", help="Post slug (the blog/<slug>/ folder name)")
    ap.add_argument("--no-audio", action="store_true",
                    help="Skip auto-narration; publish text/assets only")
    args = ap.parse_args()
    publish(args.slug, narrate=not args.no_audio)


if __name__ == "__main__":
    main()
