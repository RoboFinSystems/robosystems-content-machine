#!/usr/bin/env python3
"""Channel/account-level reach analytics - the weekly bird's-eye view.

Complements `just analytics` (per-POST rollup, needs stamped post ids). This pulls the
whole-CHANNEL and whole-ACCOUNT picture that the APIs expose today, independent of any
sidecar: YouTube traffic sources + per-video retention + the impression count on every X
post already published. Feeds the `/insights` skill, which reads this output and interprets it.

  YouTube Analytics API  -> totals (28/90/365d), traffic sources, top videos by views + AVD%,
                            daily trend  (needs the yt-analytics.readonly scope; see pull_analytics.py)
  X API v2               -> the account's recent original posts with public_metrics
                            (impressions/engagement), text-post vs link-only split

Usage:
  just insights                 # everything
  uv run python tools/pull_insights.py --days 180 --posts 100
"""

import argparse
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def load_env(path=REPO / ".env"):
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def iso_dur(d):
    """PT8M6S -> 8:06, PT45S -> 0:45."""
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", d or "")
    if not m:
        return d or "?"
    h, mi, s = (int(x) if x else 0 for x in m.groups())
    mi += h * 60
    return f"{mi}:{s:02d}"


def yt_section(days_list, top_n):
    try:
        sys.path.insert(0, str(REPO / "tools"))
        from upload_youtube import get_creds
        from googleapiclient.discovery import build
    except Exception as e:
        print(f"YouTube libs/creds unavailable: {e}")
        return
    creds = get_creds(interactive=False)
    ana = build("youtubeAnalytics", "v2", credentials=creds)
    data = build("youtube", "v3", credentials=creds)
    today = datetime.now(timezone.utc).date()

    def q(metrics, days, **kw):
        s = (today - timedelta(days=days)).isoformat()
        r = ana.reports().query(ids="channel==MINE", startDate=s, endDate=today.isoformat(),
                                metrics=metrics, **kw).execute()
        return [h["name"] for h in r.get("columnHeaders", [])], r.get("rows", [])

    print("=" * 74 + "\nYOUTUBE (channel)\n" + "=" * 74)
    try:
        ch = data.channels().list(part="statistics,snippet", mine=True).execute()["items"][0]
        st = ch["statistics"]
        print(f"{ch['snippet']['title']}  -  subs {st.get('subscriberCount')}, "
              f"{st.get('viewCount')} lifetime views, {st.get('videoCount')} videos")
    except Exception as e:
        print(f"channel stats error: {e}")

    CORE = "views,estimatedMinutesWatched,averageViewPercentage,subscribersGained,likes,shares"
    for d in days_list:
        try:
            cols, rows = q(CORE, d)
            v = dict(zip(cols, (rows or [[0] * len(cols)])[0]))
            print(f"  {d:>4}d: {v.get('views')} views, {v.get('estimatedMinutesWatched')} watch-min, "
                  f"{v.get('averageViewPercentage')}% avg-view, +{v.get('subscribersGained')} subs")
        except Exception as e:
            print(f"  {d}d: error {e}")

    print("\nTraffic sources (365d, where discovery comes from):")
    try:
        cols, rows = q("views,estimatedMinutesWatched", 365, dimensions="insightTrafficSourceType", sort="-views")
        tot = sum(r[1] for r in rows) or 1
        for r in rows:
            print(f"  {r[0]:22} {r[1]:>5} views ({r[1]/tot*100:>4.0f}%)  {r[2]} watch-min")
    except Exception as e:
        print(f"  error {e}")

    print(f"\nTop {top_n} videos by views (365d):")
    try:
        cols, rows = q("views,averageViewPercentage,estimatedMinutesWatched,subscribersGained",
                       365, dimensions="video", sort="-views", maxResults=top_n)
        titles = {}
        vids = [r[0] for r in rows]
        for i in range(0, len(vids), 50):
            for it in data.videos().list(part="snippet,contentDetails",
                                         id=",".join(vids[i:i + 50])).execute().get("items", []):
                titles[it["id"]] = (it["snippet"]["title"], iso_dur(it["contentDetails"]["duration"]))
        for r in rows:
            t, dur = titles.get(r[0], ("?", "?"))
            print(f"  {r[1]:>4} views  {float(r[2]):>5.1f}% AVD  {dur:>5}  +{r[4]} subs   {t[:56]}")
    except Exception as e:
        print(f"  error {e}")

    print("\nDaily views (last 45d, nonzero):")
    try:
        cols, rows = q("views", 45, dimensions="day", sort="day")
        nz = [(r[0][5:], r[1]) for r in rows if r[1]]
        print("  " + "  ".join(f"{d}:{v}" for d, v in nz) if nz else "  (none)")
    except Exception as e:
        print(f"  error {e}")


def x_section(n_posts):
    print("\n" + "=" * 74 + "\nX / TWITTER (account)\n" + "=" * 74)
    try:
        from requests_oauthlib import OAuth1Session
    except Exception as e:
        print(f"requests_oauthlib unavailable: {e}")
        return
    try:
        s = OAuth1Session(os.environ["X_CONSUMER_KEY"], client_secret=os.environ["X_SECRET_KEY"],
                          resource_owner_key=os.environ["X_ACCESS_TOKEN"],
                          resource_owner_secret=os.environ["X_ACCESS_SECRET"])
        me = s.get("https://api.x.com/2/users/me").json()["data"]
        uid = me["id"]
    except Exception as e:
        print(f"X auth error: {e}")
        return
    posts, token = [], None
    while len(posts) < n_posts:
        params = {"max_results": min(100, n_posts - len(posts)), "exclude": "retweets,replies",
                  "tweet.fields": "public_metrics,created_at"}
        if token:
            params["pagination_token"] = token
        r = s.get(f"https://api.x.com/2/users/{uid}/tweets", params=params).json()
        posts += r.get("data", [])
        token = r.get("meta", {}).get("next_token")
        if not token:
            break
    print(f"@{me['username']}  -  {len(posts)} recent original posts\n")

    rows = []
    for p in posts:
        m = p["public_metrics"]
        imp = m.get("impression_count", 0)
        eng = (m["like_count"] + m["retweet_count"] + m["reply_count"]
               + m["quote_count"] + m.get("bookmark_count", 0))
        text = p["text"]
        stripped = re.sub(r"https://t\.co/\S+", "", text).strip()
        kind = "link" if len(stripped) < 15 else "text"
        rows.append({"date": p["created_at"][:10], "imp": imp, "eng": eng,
                     "er": eng / imp * 100 if imp else 0, "likes": m["like_count"],
                     "bkmk": m.get("bookmark_count", 0), "kind": kind,
                     "text": (stripped or text)[:46].replace("\n", " ")})
    rows.sort(key=lambda x: -x["imp"])
    print(f"{'date':11}{'impr':>7}{'eng':>5}{'eng%':>6}{'bkmk':>5} kind  text")
    for r in rows:
        print(f"{r['date']:11}{r['imp']:>7}{r['eng']:>5}{r['er']:>5.1f}%{r['bkmk']:>5} {r['kind']:5} {r['text']}")

    def med(xs):
        xs = sorted(xs)
        return xs[len(xs) // 2] if xs else 0
    if rows:
        allimp = [r["imp"] for r in rows]
        txt = [r["imp"] for r in rows if r["kind"] == "text"]
        lnk = [r["imp"] for r in rows if r["kind"] == "link"]
        ers = [r["er"] for r in rows if r["imp"]]
        print(f"\nSUMMARY: {len(rows)} posts | impressions median {med(allimp)}, max {max(allimp)}, "
              f"total {sum(allimp)}")
        print(f"  text posts (n={len(txt)}): median {med(txt)} impr   |   "
              f"link-only (n={len(lnk)}): median {med(lnk)} impr")
        print(f"  engagement rate: median {med(ers):.1f}%  (small-account benchmark ~4%)")


def main():
    load_env()
    ap = argparse.ArgumentParser(description="Channel/account-level reach analytics")
    ap.add_argument("--days", type=int, default=365, help="(reserved) primary lookback")
    ap.add_argument("--posts", type=int, default=100, help="how many recent X posts to pull")
    ap.add_argument("--top", type=int, default=15, help="top-N YouTube videos")
    ap.add_argument("--no-youtube", action="store_true")
    ap.add_argument("--no-x", action="store_true")
    args = ap.parse_args()
    if not args.no_youtube:
        try:
            yt_section([28, 90, 365], args.top)
        except Exception as e:
            print(f"YouTube section failed: {e}")
    if not args.no_x:
        x_section(args.posts)


if __name__ == "__main__":
    main()
