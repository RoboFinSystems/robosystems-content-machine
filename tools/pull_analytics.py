#!/usr/bin/env python3
"""Pull X + YouTube performance into each project so the pipeline (and Claude) can SEE reach.

Closes the analytics feedback loop. The human has always had the platform dashboards; this
gives the machine the same numbers next to each post/video, so optimization stops being blind.

Reads the IDs each publish step already stamps:
  videos/{T}_x.json             tweet_id   - the long-form native-video X post
  social/{T}_x_article.json     post_id    - the published X Article (only after --publish)
  videos/{T}_youtube.json       video_id   - the long-form YouTube upload
  videos/{T}_short_x.json       tweet_id   - the 9:16 short's X post
  videos/{T}_short_youtube.json video_id   - the 9:16 short's YouTube Short
(the short is reported on its own `T·s` row so its reach/retention stays separate.)

Queries:
  X API v2  GET /2/tweets ...public_metrics
      -> impressions, likes, reposts, replies, quotes, bookmarks   (OAuth1 user token, ~$0.001/post)
  YouTube Analytics API v2  reports.query
      -> views, avg-view-% (retention), watch time, likes/comments/shares, subscribers gained
         (thumbnail impressions + CTR are NOT in the query API - Studio / Reporting API only)

Writes a timestamped snapshot to projects/{T}/analytics.json (a LIST - repeated runs build a
trend), and prints a rollup table. Re-run any time; each run appends a fresh snapshot.

YouTube needs the yt-analytics.readonly scope. It was added to upload_youtube.py's SCOPES on
2026-07-20, so if your YT_REFRESH_TOKEN predates that, run `just yt-auth` once to re-consent -
the tool says exactly that if the scope is missing.

Usage:
  just analytics                 # every project with at least one stamped id
  just analytics NFLX GE         # specific tickers
  uv run python tools/pull_analytics.py NFLX --json
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PROJECTS = REPO / "projects"


def load_env(path=REPO / ".env"):
    """Populate os.environ from .env for direct runs (just/uv already loads it)."""
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


# ---------------- id collection ----------------

def read_json(p: Path):
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def project_ids(ticker: str):
    """Per-ticker ids across surfaces. The 9:16 short posts to X + YT Shorts under its own
    sidecars ({T}_short_x.json / {T}_short_youtube.json), tracked separately from the long-form."""
    proj = PROJECTS / ticker
    ids = {"x_post": None, "x_article": None, "youtube": None,
           "x_short": None, "youtube_short": None}
    xp = read_json(proj / "videos" / f"{ticker}_x.json")
    if xp:
        ids["x_post"] = xp.get("tweet_id")
    art = read_json(proj / "social" / f"{ticker}_x_article.json")
    if art and art.get("status") == "published" and art.get("post_id"):
        ids["x_article"] = art["post_id"]
    yt = read_json(proj / "videos" / f"{ticker}_youtube.json")
    if yt:
        ids["youtube"] = yt.get("video_id")
    xs = read_json(proj / "videos" / f"{ticker}_short_x.json")
    if xs:
        ids["x_short"] = xs.get("tweet_id")
    yts = read_json(proj / "videos" / f"{ticker}_short_youtube.json")
    if yts:
        ids["youtube_short"] = yts.get("video_id")
    return ids


def all_tickers():
    if not PROJECTS.exists():
        return []
    out = []
    for d in sorted(PROJECTS.iterdir()):
        if not d.is_dir() or d.name == "archive":
            continue
        ids = project_ids(d.name)
        if any(ids.values()):
            out.append(d.name)
    return out


# ---------------- X ----------------

def x_session():
    from requests_oauthlib import OAuth1Session
    ck = os.environ.get("X_CONSUMER_KEY", "").strip()
    cs = os.environ.get("X_SECRET_KEY", "").strip()
    at = os.environ.get("X_ACCESS_TOKEN", "").strip()
    ats = os.environ.get("X_ACCESS_SECRET", "").strip()
    if not (ck and cs and at and ats):
        print("  X credentials missing from .env - skipping X metrics", file=sys.stderr)
        return None
    return OAuth1Session(ck, client_secret=cs, resource_owner_key=at, resource_owner_secret=ats)


def pull_x(session, ids):
    """ids: iterable of tweet/post ids. Returns {id: metrics}. One batched call (<=100)."""
    ids = [i for i in ids if i]
    if not session or not ids:
        return {}
    r = session.get("https://api.x.com/2/tweets",
                    params={"ids": ",".join(ids[:100]),
                            "tweet.fields": "public_metrics,created_at"})
    if r.status_code >= 300:
        print(f"  X read failed: HTTP {r.status_code} {r.text[:200]}", file=sys.stderr)
        return {}
    out = {}
    for t in r.json().get("data", []):
        pm = t.get("public_metrics", {})
        imp = pm.get("impression_count") or 0
        eng = sum(pm.get(k, 0) for k in
                  ("like_count", "retweet_count", "reply_count", "quote_count", "bookmark_count"))
        out[t["id"]] = {
            "impressions": pm.get("impression_count"),
            "likes": pm.get("like_count"),
            "reposts": pm.get("retweet_count"),
            "replies": pm.get("reply_count"),
            "quotes": pm.get("quote_count"),
            "bookmarks": pm.get("bookmark_count"),
            "engagement_rate": round(eng / imp, 4) if imp else None,
            "created_at": t.get("created_at"),
        }
    return out


# ---------------- YouTube ----------------

# videoThumbnailImpressions / ...ClickRate are NOT supported by reports.query (any shape 400s);
# they exist only in the bulk Reporting API / Studio. The core set below is what the query API serves.
YT_CORE = ("views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,"
           "likes,comments,shares,subscribersGained")


def yt_services():
    try:
        sys.path.insert(0, str(REPO / "tools"))
        from upload_youtube import get_creds
        from googleapiclient.discovery import build
    except Exception as e:
        print(f"  YouTube libraries/creds unavailable: {e}", file=sys.stderr)
        return None, None
    try:
        creds = get_creds(interactive=False)
    except SystemExit as e:
        print(f"  YouTube auth: {e}", file=sys.stderr)
        return None, None
    return (build("youtubeAnalytics", "v2", credentials=creds),
            build("youtube", "v3", credentials=creds))


def pull_youtube(ana, data, video_id, scope_ok=[True]):
    if not ana or not video_id or not scope_ok[0]:
        return None
    from googleapiclient.errors import HttpError
    start = "2005-02-14"   # YouTube epoch; Analytics clamps to the video's first day
    try:
        items = data.videos().list(part="snippet,statistics", id=video_id).execute().get("items", [])
        if items:
            start = items[0]["snippet"]["publishedAt"][:10]
    except Exception:
        pass
    today = datetime.now(timezone.utc).date().isoformat()
    row = {"video_id": video_id, "since": start}

    def q(metrics):
        return ana.reports().query(ids="channel==MINE", startDate=start, endDate=today,
                                   metrics=metrics, filters=f"video=={video_id}").execute()

    try:
        res = q(YT_CORE)
        cols = [h["name"] for h in res.get("columnHeaders", [])]
        vals = (res.get("rows") or [[None] * len(cols)])[0]
        row.update(dict(zip(cols, vals)))
    except HttpError as e:
        status = getattr(getattr(e, "resp", None), "status", None)
        if status == 403:
            scope_ok[0] = False
            row["_scope_error"] = ("YouTube Analytics 403 - run `just yt-auth` to re-consent "
                                   "with yt-analytics.readonly AND enable the YouTube Analytics API")
        else:
            row["_error"] = str(e)[:160]
    return row


# ---------------- snapshot + report ----------------

def write_snapshot(ticker, snap):
    p = PROJECTS / ticker / "analytics.json"
    hist = read_json(p) or []
    if not isinstance(hist, list):
        hist = [hist]
    hist.append(snap)
    p.write_text(json.dumps(hist, indent=2) + "\n")


def fmt(v, pct=False):
    if v is None:
        return "-"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if pct:
        return f"{f:.1f}%"
    return f"{int(f):,}" if f >= 100 else f"{f:g}"


def main():
    load_env()
    ap = argparse.ArgumentParser(description="Pull X + YouTube reach/retention into each project")
    ap.add_argument("tickers", nargs="*", help="tickers (default: every project with a stamped id)")
    ap.add_argument("--json", action="store_true", help="print the raw snapshots as JSON")
    args = ap.parse_args()

    tickers = [t.upper() for t in args.tickers] or all_tickers()
    if not tickers:
        print("No projects with a stamped X/YouTube id yet. Post something first, then "
              "re-run - future runs stamp the ids automatically (videos/{T}_x.json, "
              "videos/{T}_youtube.json, social/{T}_x_article.json).")
        return

    ids_by_ticker = {t: project_ids(t) for t in tickers}

    # X: one batched read across every id
    xs = x_session()
    xid_owner = {}
    for t, ids in ids_by_ticker.items():
        for kind in ("x_post", "x_article", "x_short"):
            if ids[kind]:
                xid_owner[ids[kind]] = (t, kind)
    xmetrics = pull_x(xs, xid_owner.keys())

    # YouTube: one query per video (only touch Google auth if there's a video to query)
    needs_yt = any(ids["youtube"] or ids["youtube_short"] for ids in ids_by_ticker.values())
    ana, data = yt_services() if needs_yt else (None, None)

    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    snapshots = {}
    for t in tickers:
        ids = ids_by_ticker[t]
        snap = {"ts": ts, "ids": ids,
                "x_post": xmetrics.get(ids["x_post"]) if ids["x_post"] else None,
                "x_article": xmetrics.get(ids["x_article"]) if ids["x_article"] else None,
                "x_short": xmetrics.get(ids["x_short"]) if ids["x_short"] else None,
                "youtube": pull_youtube(ana, data, ids["youtube"]) if ids["youtube"] else None,
                "youtube_short": pull_youtube(ana, data, ids["youtube_short"]) if ids["youtube_short"] else None}
        snapshots[t] = snap
        write_snapshot(t, snap)

    if args.json:
        print(json.dumps(snapshots, indent=2))
        return

    # rollup table
    scope_warned = False
    print(f"\nAnalytics snapshot  {ts}\n" + "=" * 74)
    hdr = (f"{'':7}{'X impr':>9}{'X eng%':>8}{'X bkmk':>7}{'  ':2}"
           f"{'YT views':>9}{'YT AVD%':>8}{'YT min':>9}{'subs':>6}")
    print(hdr)
    print("-" * 75)

    def row(label, xp, yt):
        er = xp.get("engagement_rate")
        er = f"{er*100:.1f}%" if er is not None else "-"
        return (f"{label:7}{fmt(xp.get('impressions')):>9}{er:>8}{fmt(xp.get('bookmarks')):>7}{'  ':2}"
                f"{fmt(yt.get('views')):>9}{fmt(yt.get('averageViewPercentage'), pct=True):>8}"
                f"{fmt(yt.get('estimatedMinutesWatched')):>9}{fmt(yt.get('subscribersGained')):>6}")

    for t in tickers:
        s = snapshots[t]
        for r in (s["x_post"], s["youtube"], s.get("x_short"), s.get("youtube_short")):
            if r and r.get("_scope_error"):
                scope_warned = True
        print(row(t, s["x_post"] or {}, s["youtube"] or {}))
        if s.get("x_short") or s.get("youtube_short"):   # short = its own line (label T·s)
            print(row(f"{t[:5]}·s", s["x_short"] or {}, s["youtube_short"] or {}))
    print("-" * 75)
    print(f"Snapshots appended to projects/*/analytics.json  ({len(tickers)} project(s))  ·  T·s = 9:16 short")
    if scope_warned:
        print("\n  NOTE: YouTube Analytics 403. Run `just yt-auth` to re-consent with "
              "yt-analytics.readonly, and enable the YouTube Analytics API in the GCP project.")


if __name__ == "__main__":
    main()
