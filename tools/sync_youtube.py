"""
Capture YouTube URLs into the research catalog by title-matching the channel's uploads,
read through the YouTube Data API. After you upload to YouTube, run this; it matches each
ticker's titles (youtube_title / short_title / short_qa_title from
publish.json) against the feed and writes youtube_url / short_youtube_url / short_qa_youtube_url
into the LATEST version's S3 meta.json (content/{T}/meta.json), then reindexes so the portal can
embed YouTube instead of streaming the S3 MP4.

Reads the FULL uploads playlist (paginated), not just recent ones, so it also backfills
titles uploaded long ago or through YouTube Studio.

Was RSS (youtube.com/feeds/videos.xml) until 2026-09-14, when that endpoint began returning
404 for this channel while still serving others. It also only ever exposed the ~15 newest
uploads, so it could never match the older cohort. Auth reuses $YT_REFRESH_TOKEN via
upload_youtube.get_creds - run `just yt-auth` if it has expired.

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
import reindex
from helpers import get_project_dir, require_env


def fetch_feed(cid):
    """[(normalized_title, video_url)] for EVERY upload on the channel.

    cid is accepted for signature compatibility and cross-checked against the
    authenticated channel, so a stale $YT_CHANNEL_ID surfaces as an error rather
    than a silent zero-match run.
    """
    import upload_youtube
    from googleapiclient.discovery import build

    yt = build("youtube", "v3", credentials=upload_youtube.get_creds(interactive=False))
    chan = yt.channels().list(part="contentDetails", mine=True).execute().get("items") or []
    if not chan:
        sys.exit("YouTube API returned no channel for these credentials - run `just yt-auth`")
    if cid and chan[0]["id"] != cid:
        sys.exit(f"$YT_CHANNEL_ID is {cid} but the authenticated channel is {chan[0]['id']}")
    uploads = chan[0]["contentDetails"]["relatedPlaylists"]["uploads"]

    out, page = [], None
    while True:
        r = yt.playlistItems().list(part="snippet", playlistId=uploads,
                                    maxResults=50, pageToken=page).execute()
        for it in r.get("items", []):
            sn = it["snippet"]
            out.append((_norm(sn["title"]), f"https://youtu.be/{sn['resourceId']['videoId']}"))
        page = r.get("nextPageToken")
        if not page:
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
    ("short_qa_title", "short_qa_youtube_url", "short-qa"),
]

# `just yt-upload` already records the exact video it created. Rediscovering that by
# title-matching an RSS feed is strictly worse: the feed holds only ~15 uploads and lags
# by minutes, so SAM and IMAX both reported no match right after going public even though
# their ids were sitting on disk. Prefer the sidecar; RSS stays the fallback for videos
# uploaded outside this pipeline.
SIDECARS = {
    "youtube_url": "{t}_youtube.json",
    "short_youtube_url": "{t}_short_youtube.json",
}


def sidecar_url(ticker, url_key):
    """URL recorded by the upload step, if it exists and the video is public."""
    name = SIDECARS.get(url_key)
    if not name:
        return None
    path = os.path.join(get_project_dir(ticker), "videos", name.format(t=ticker))
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    vid = data.get("video_id")
    return f"https://youtu.be/{vid}" if vid else None


def sync(tickers, report_only=False):
    bucket = require_env("AWS_S3_BUCKET")
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
            if (url := sidecar_url(t, url_key)):
                hits[url_key] = url
                cells.append(f"{label} ✓id")      # from the upload sidecar, not the feed
                n_matched += 1
            elif not title:
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
                         if os.path.isdir(os.path.join(projects, d))
                         and not d.startswith(".") and d != "archive")  # archive/ = retired tickers
    sync(tickers, report_only=args.report)


if __name__ == "__main__":
    main()
