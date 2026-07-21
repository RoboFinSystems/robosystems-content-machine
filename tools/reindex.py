"""
Build the research catalog (content/index.json) that the /research portal reads.

Scans local projects/, includes those whose deliverables are actually published to
s3://{AWS_S3_BUCKET}/content/{TICKER}/, and emits ONE content/index.json. No database —
this flat file is the catalog; the portal fetches it to discover everything.

Versioning: the company is the durable entity; each run is a dated report version.
  - LATEST report lives at flat content/{T}/ (stable URL → /research/{T}).
  - prior versions are snapshotted to content/{T}/archive/{YYYY-MM}/ by `just publish`.
Each version folder is SELF-DESCRIBING via a small meta.json (ticker, title, summary,
tags, date, version, ...). This script derives the catalog purely from S3: the latest
from content/{T}/meta.json (falling back to the local project), and `history[]` by
scanning content/{T}/archive/*/ — so backfilling an old version is just "upload it +
reindex". Assets are mapped by filename suffix, so legacy names (e.g. TCNNF_final.mp4
under content/TRLV/archive/) resolve correctly.

Usage:
    uv run python tools/reindex.py
"""

import argparse
import datetime
import json
import os
import subprocess

from helpers import asset_url, require_env

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECTS = os.path.join(ROOT, "projects")

# filename suffix -> catalog asset key
SUFFIX_MAP = [
    ("_final.mp4", "video"),
    ("_short.mp4", "short"),
    ("_brief.md", "brief"),
    ("_thumbnail.png", "thumbnail"),
]


def quarter(date_str):
    """'2026-06-22' -> '2026-Q2' (calendar quarter; coverage cadence is quarterly)."""
    y, m = int(date_str[:4]), int(date_str[5:7])
    return f"{y}-Q{(m - 1) // 3 + 1}"


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


def s3_ls_dirs(bucket, prefix):
    """Sub-'directory' names (the 'PRE x/' rows) directly under prefix."""
    r = subprocess.run(["aws", "s3", "ls", f"s3://{bucket}/{prefix}"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return []
    return [p.split()[-1].rstrip("/") for p in r.stdout.splitlines()
            if p.split() and p.split()[0] == "PRE"]


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
    # Short max-age: this catalog/meta is rewritten on every publish + sync-youtube, so the
    # CDN (CachingOptimized, 24h default) must not serve it stale. Media stays on the long
    # default TTL — it's large, egress-costly, and only changes on a (rare) re-cover.
    subprocess.run(
        ["aws", "s3", "cp", "-", f"s3://{bucket}/{key}",
         "--content-type", "application/json; charset=utf-8",
         "--cache-control", "public, max-age=60", "--only-show-errors"],
        input=json.dumps(obj, indent=2, ensure_ascii=False), text=True, check=True,
    )


def _load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def project_meta(ticker):
    """Rich metadata from the local project (title, summary, tags, company, campaign).
    Used for a freshly-published latest that has no meta.json yet, and by publish."""
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
        "coverage_label": meta.get("coverage_label"),
    }


def map_assets(names, prefix):
    """Map a folder's filenames to {asset_key: public_url} by suffix."""
    out = {}
    for name in sorted(names):
        for suf, key in SUFFIX_MAP:
            if name.endswith(suf) and key not in out:
                out[key] = asset_url(f"{prefix}{name}")
                break
    return out


def run():
    bucket = require_env("AWS_S3_BUCKET")
    tickers = sorted(d for d in os.listdir(PROJECTS)
                     if os.path.isdir(os.path.join(PROJECTS, d))
                     and not d.startswith(".") and d != "archive")  # archive/ = retired tickers, not a ticker

    items = []
    for t in tickers:
        flat = f"content/{t}/"
        listing = s3_ls(bucket, flat)
        present = {n for n, _ in listing}
        if f"{t}_final.mp4" not in present:
            continue  # not published — skip

        meta = s3_get_json(bucket, f"{flat}meta.json")
        if not meta:  # freshly published before meta.json existed — derive from local
            date = next((d for n, d in listing if n == f"{t}_final.mp4"), None) \
                or datetime.date.today().isoformat()
            meta = {**project_meta(t), "date": date, "version": quarter(date)}

        item = {"ticker": t, **meta, "assets": map_assets(present, flat)}

        history = []
        for ver in sorted(s3_ls_dirs(bucket, f"{flat}archive/"), reverse=True):
            aprefix = f"{flat}archive/{ver}/"
            anames = {n for n, _ in s3_ls(bucket, aprefix)}
            ameta = s3_get_json(bucket, f"{aprefix}meta.json") or {"version": ver}
            history.append({**ameta, "version": ameta.get("version", ver),
                            "assets": map_assets(anames, aprefix)})
        item["history"] = history
        items.append(item)

    index = {
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "count": len(items),
        "items": sorted(items, key=lambda x: x.get("date", ""), reverse=True),
    }
    s3_put_json(bucket, "content/index.json", index)

    local_copy = os.path.join(ROOT, "local", "content_index.json")
    os.makedirs(os.path.dirname(local_copy), exist_ok=True)
    with open(local_copy, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

    print(f"Catalog: {len(items)} item(s) -> s3://{bucket}/content/index.json")
    for it in index["items"]:
        extra = f"  (+{len(it['history'])} archived: {', '.join(h['version'] for h in it['history'])})" \
            if it["history"] else ""
        print(f"  {it['ticker']:6} {it.get('version','?')}  {len(it['assets'])} assets{extra}")
    print(f"Local copy: {local_copy}")
    return index


def main():
    argparse.ArgumentParser(description="Rebuild the research catalog (content/index.json)").parse_args()
    run()


if __name__ == "__main__":
    main()
