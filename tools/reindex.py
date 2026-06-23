"""
Build the research catalog (content/index.json) that the /research portal reads.

Scans local projects/, includes those whose deliverables are actually published to
s3://{S3_BUCKET}/content/{TICKER}/, and emits ONE content/index.json. No database —
this flat file is the catalog; the portal fetches it to discover everything.

Versioning: the company is the durable entity; each run is a dated report version.
Each catalog item is the LATEST report (flat content/{T}/ URLs) plus a `history` of
prior dated versions (content/{T}/archive/{VERSION}/ URLs). Prior versions are
snapshotted to archive/ by the publish step when a ticker is re-covered, and this
script rolls the previous "latest" into `history` (merging the prior index so older
history is never lost).

Usage:
    uv run python tools/reindex.py
"""

import argparse
import datetime
import json
import os
import subprocess

from helpers import require_env

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECTS = os.path.join(ROOT, "projects")

# catalog asset key -> published filename (templated on ticker)
ASSETS = {
    "video":       "{t}_final.mp4",
    "short":       "{t}_short.mp4",
    "podcast_mp3": "{t}_qa_podcast.mp3",
    "podcast_mp4": "{t}_qa_podcast.mp4",
    "brief":       "{t}_brief.md",
    "thumbnail":   "{t}_thumbnail.png",
}


def s3_ls(bucket, prefix):
    """[(name, date)] for objects directly under prefix; skips 'PRE <dir>/' rows."""
    r = subprocess.run(["aws", "s3", "ls", f"s3://{bucket}/{prefix}"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return []
    rows = []
    for line in r.stdout.splitlines():
        p = line.split()
        if not p or p[0] == "PRE":
            continue
        rows.append((p[-1], p[0]))   # (name, "YYYY-MM-DD")
    return rows


def s3_get_json(bucket, key):
    r = subprocess.run(["aws", "s3", "cp", f"s3://{bucket}/{key}", "-"],
                       capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        return None
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return None


def s3_put_json(bucket, key, obj):
    data = json.dumps(obj, indent=2, ensure_ascii=False)
    subprocess.run(
        ["aws", "s3", "cp", "-", f"s3://{bucket}/{key}",
         "--content-type", "application/json; charset=utf-8", "--only-show-errors"],
        input=data, text=True, check=True,
    )


def _load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def project_meta(ticker):
    """Rich metadata from the local project (title, summary, tags, company, campaign)."""
    pdir = os.path.join(PROJECTS, ticker)
    meta = (_load(os.path.join(pdir, "scripts", f"{ticker}_script.json")) or {}).get("metadata", {})
    pub = _load(os.path.join(pdir, "social", f"{ticker}_publish.json"))
    campaign = meta.get("campaign")
    return {
        "company": meta.get("company") or ticker,
        "title": (pub.get("youtube_title") or meta.get("video_title") or ticker).strip(),
        "summary": (meta.get("video_description") or "").strip(),
        "tags": meta.get("tags") or [],
        "campaign": campaign,
        "campaign_slug": "cannabis_coverage" if "cannabis" in (campaign or "").lower() else None,
    }


def asset_urls(bucket, ticker, present, prefix):
    out = {}
    for key, fn in ASSETS.items():
        name = fn.format(t=ticker)
        if name in present:
            out[key] = f"https://{bucket}.s3.amazonaws.com/{prefix}{name}"
    return out


def run():
    bucket = require_env("S3_BUCKET")
    prior_by_ticker = {it["ticker"]: it
                       for it in (s3_get_json(bucket, "content/index.json") or {}).get("items", [])}

    tickers = sorted(d for d in os.listdir(PROJECTS)
                     if os.path.isdir(os.path.join(PROJECTS, d)) and not d.startswith("."))

    items = []
    for t in tickers:
        listing = s3_ls(bucket, f"content/{t}/")
        present = {n for n, _ in listing}
        if f"{t}_final.mp4" not in present:
            continue  # not published — skip
        date = next((d for n, d in listing if n == f"{t}_final.mp4"), None) \
            or datetime.date.today().isoformat()
        version = date[:7]  # YYYY-MM

        item = {
            "ticker": t,
            **project_meta(t),
            "date": date,
            "version": version,
            "assets": asset_urls(bucket, t, present, f"content/{t}/"),
        }

        # roll the prior "latest" into history if it was a different version
        prev = prior_by_ticker.get(t)
        history = list(prev.get("history", [])) if prev else []
        if prev and prev.get("version") and prev["version"] != version:
            arch = f"content/{t}/archive/{prev['version']}/"
            history = [{
                "version": prev["version"],
                "date": prev.get("date"),
                "title": prev.get("title"),
                "assets": {k: f"https://{bucket}.s3.amazonaws.com/{arch}{os.path.basename(u)}"
                           for k, u in (prev.get("assets") or {}).items()},
            }] + history
        item["history"] = history
        items.append(item)

    index = {
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "count": len(items),
        "items": sorted(items, key=lambda x: x["date"], reverse=True),
    }
    s3_put_json(bucket, "content/index.json", index)

    local_copy = os.path.join(ROOT, "local", "content_index.json")
    os.makedirs(os.path.dirname(local_copy), exist_ok=True)
    with open(local_copy, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

    print(f"Catalog: {len(items)} item(s) -> s3://{bucket}/content/index.json")
    for it in index["items"]:
        extra = f"  (+{len(it['history'])} archived)" if it["history"] else ""
        print(f"  {it['ticker']:6} {it['version']}  {len(it['assets'])} assets{extra}  {it['title'][:46]}")
    print(f"Local copy: {local_copy}")
    return index


def main():
    argparse.ArgumentParser(description="Rebuild the research catalog (content/index.json)").parse_args()
    run()


if __name__ == "__main__":
    main()
