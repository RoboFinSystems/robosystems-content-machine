"""
Capture YouTube URLs into the research catalog by title-matching the channel's public
RSS feed — no API key, no OAuth. After you upload to YouTube, run this; it matches each
ticker's titles (youtube_title / short_title / podcast_episode_title from publish.json)
against the feed and writes youtube_url / short_youtube_url / podcast_youtube_url into the
LATEST version's S3 meta.json (content/{T}/meta.json), then reindexes so the portal can
embed YouTube instead of streaming the S3 MP4.

The feed only holds the ~15 most-recent uploads, so run it within a few uploads of posting.
Channel id from $YT_CHANNEL_ID (e.g. UChqVvHIxAs_tAZedlV1UVLQ for @robosystems).

Usage:
    uv run python tools/sync_youtube.py            # all published tickers
    uv run python tools/sync_youtube.py TRLV GTBIF # specific ones
"""

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request

import reindex
from helpers import get_project_dir, require_env

FEED = "https://www.youtube.com/feeds/videos.xml?channel_id={cid}"


def fetch_feed(cid):
    """[(title, video_url)] for the channel's recent uploads."""
    req = urllib.request.Request(FEED.format(cid=cid), headers={"User-Agent": "Mozilla/5.0"})
    xml = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    out = []
    for entry in xml.split("<entry>")[1:]:
        vid = re.search(r"<yt:videoId>([^<]+)", entry)
        title = re.search(r"<title>([^<]+)", entry)
        if vid and title:
            out.append((_norm(title.group(1)), f"https://youtu.be/{vid.group(1)}"))
    return out


def _norm(s):
    """Normalize a title for matching (unescape, collapse whitespace, casefold)."""
    s = (s or "").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'").replace("&quot;", '"')
    return re.sub(r"\s+", " ", s).strip().casefold()


def _match(title, feed):
    if not title:
        return None
    want = _norm(title)
    for ft, url in feed:
        if ft == want:
            return url
    return None


# (publish.json title field, meta.json url field, short label)
FIELDS = [
    ("youtube_title", "youtube_url", "long"),
    ("short_title", "short_youtube_url", "short"),
    ("podcast_episode_title", "podcast_youtube_url", "podcast"),
]


def sync(tickers, report_only=False):
    bucket = require_env("S3_BUCKET")
    cid = require_env("YT_CHANNEL_ID")
    feed = fetch_feed(cid)
    print(f"Feed: {len(feed)} recent uploads on channel {cid}")
    print("  ✓ matched · ✗ title authored but no feed match · — no title\n")

    n_matched = n_missed = 0
    wrote = False
    for t in tickers:
        pj = os.path.join(get_project_dir(t), "social", f"{t}_publish.json")
        pub = {}
        if os.path.exists(pj):
            with open(pj, encoding="utf-8") as f:
                pub = json.load(f)

        meta = reindex.s3_get_json(bucket, f"content/{t}/meta.json")
        if meta is None:
            print(f"  {t:6} — not published (no content/{t}/meta.json)")
            continue

        cells, hits = [], {}
        for title_key, url_key, label in FIELDS:
            title = pub.get(title_key)
            if not title:
                cells.append(f"{label} —")
            elif (url := _match(title, feed)):
                hits[url_key] = url
                cells.append(f"{label} ✓")
                n_matched += 1
            else:
                cells.append(f"{label} ✗")
                n_missed += 1

        if hits and not report_only:
            meta.update(hits)
            reindex.s3_put_json(bucket, f"content/{t}/meta.json", meta)
            wrote = True

        ids = " ".join(v.rsplit("/", 1)[-1] for v in hits.values())
        print(f"  {t:6} {'  '.join(cells):28} {ids}")

    print(f"\n{n_matched} matched, {n_missed} missed")
    if report_only:
        print("(--report: dry run — nothing written)")
    elif wrote:
        print()
        reindex.run()
    else:
        print("(no new matches to write)")


def main():
    ap = argparse.ArgumentParser(description="Capture YouTube URLs into the catalog via the channel RSS feed")
    ap.add_argument("tickers", nargs="*", help="Tickers (default: all published)")
    ap.add_argument("--report", action="store_true",
                    help="Dry run: show the match table without writing")
    args = ap.parse_args()

    tickers = args.tickers
    if not tickers:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        projects = os.path.join(root, "projects")
        tickers = sorted(d for d in os.listdir(projects)
                         if os.path.isdir(os.path.join(projects, d)) and not d.startswith("."))
    sync(tickers, report_only=args.report)


if __name__ == "__main__":
    main()
