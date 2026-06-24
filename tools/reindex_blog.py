"""
Build the blog catalog (blog/index.json) the app's /blog routes read.

Mirrors tools/reindex.py but blog-shaped (slug/author/tag, no ticker/version). Scans the
published S3 blog/ prefix, reads each post's metadata from the local git-versioned
blog/<slug>/post.md (the source of truth; falls back to S3 meta.json), and emits ONE
blog/index.json. A post is included once its post.md is published to s3://…/blog/<slug>/.

Asset URLs are absolute (via helpers.asset_url) — same as the research catalog — so the app's
shared catalog layer fetches blog + research bodies through one code path, and the CDN cutover
(AWS_CDN_DOMAIN_URL) flips both at once.

Usage:
    uv run python tools/reindex_blog.py
"""

import argparse
import datetime
import json
import os

import blog_common as bc
from helpers import asset_url, require_env
from reindex import s3_get_json, s3_ls, s3_ls_dirs, s3_put_json


def build_item(bucket, slug, present_names):
    """One catalog item for a published post. present_names = files under blog/<slug>/."""
    prefix = f"blog/{slug}/"
    try:
        meta, body = bc.parse_post(slug)          # local source of truth
    except FileNotFoundError:
        meta, body = (s3_get_json(bucket, f"{prefix}meta.json") or {}), ""

    assets = {}
    if "post.md" in present_names:
        assets["body"] = asset_url(f"{prefix}post.md")
    if "cover.png" in present_names:
        assets["cover"] = asset_url(f"{prefix}cover.png")
    if f"{slug}_narration.mp3" in present_names:
        assets["narration_mp3"] = asset_url(f"{prefix}{slug}_narration.mp3")

    return {
        "slug": slug,
        "title": str(meta.get("title") or slug).strip(),
        "date": bc.normalize_date(meta.get("date") or datetime.date.today().isoformat()),
        "author": meta.get("author") or "RoboSystems",
        "excerpt": bc.excerpt_fallback(meta, body),
        "metaDescription": meta.get("metaDescription") or None,
        "tags": meta.get("tags") or [],
        "keywords": meta.get("keywords") or [],
        "reading_time_minutes": bc.reading_time_minutes(body) if body else None,
        "canonical_url": meta.get("canonicalUrl") or None,
        "assets": assets,
    }


def run():
    bucket = require_env("AWS_S3_BUCKET")
    posts = []
    for slug in sorted(s3_ls_dirs(bucket, "blog/")):
        names = {n for n, _ in s3_ls(bucket, f"blog/{slug}/")}
        if "post.md" not in names:
            continue  # a folder without a body isn't a publishable post
        posts.append(build_item(bucket, slug, names))

    # newest first
    posts.sort(key=lambda p: p["date"], reverse=True)

    index = {
        "version": 1,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(posts),
        "posts": posts,
    }
    s3_put_json(bucket, "blog/index.json", index)

    local_copy = os.path.join(bc.ROOT, "local", "blog_index.json")
    os.makedirs(os.path.dirname(local_copy), exist_ok=True)
    with open(local_copy, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

    print(f"Blog catalog: {len(posts)} post(s) -> s3://{bucket}/blog/index.json")
    for p in posts:
        flags = [f for f, on in (("narrated", "narration_mp3" in p["assets"]),
                                 ("cover", "cover" in p["assets"])) if on]
        extra = f"  [{', '.join(flags)}]" if flags else ""
        print(f"  {p['date']}  {p['slug']}{extra}")
    print(f"Local copy: {local_copy}")
    return index


def main():
    argparse.ArgumentParser(description="Rebuild the blog catalog (blog/index.json)").parse_args()
    run()


if __name__ == "__main__":
    main()
