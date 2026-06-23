"""
Publish a project's final deliverables to the public S3 artifact store.

Uploads the finished media (+ brief and social copy) to
  s3://{S3_BUCKET}/content/{TICKER}/
with correct content-types, and prints the public URLs.

Public read is granted by a bucket policy scoped to the `content/*` prefix (set once); the
Shotstack staging assets elsewhere in the bucket stay private. This is the separate "S3
artifact" archive — independent of posting to YouTube / Spotify / X.

Usage:
    uv run python tools/publish_artifacts.py TRLV
"""

import argparse
import datetime
import json
import os
import subprocess

import reindex
from helpers import get_project_dir, require_env

# (path under the project dir, content-type). Whatever exists gets published.
ARTIFACTS = [
    ("videos/{t}_final.mp4", "video/mp4"),
    ("videos/{t}_short.mp4", "video/mp4"),
    ("videos/{t}_qa_podcast.mp3", "audio/mpeg"),
    ("videos/{t}_qa_podcast.mp4", "video/mp4"),
    ("charts/png/{t}_thumbnail.png", "image/png"),
    ("reports/{t}_brief.md", "text/markdown; charset=utf-8"),
    ("social/{t}_x_post.txt", "text/plain; charset=utf-8"),
    ("social/{t}_youtube_description.txt", "text/plain; charset=utf-8"),
]


def snapshot_prior_version(bucket, ticker):
    """If a different-month report is already published, copy the current flat files
    into content/{ticker}/archive/{prior_version}/ before we overwrite them — so
    re-covering a ticker preserves the prior version instead of smashing it."""
    r = subprocess.run(["aws", "s3", "ls", f"s3://{bucket}/content/{ticker}/"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return
    prior_date = next((line.split()[0] for line in r.stdout.splitlines()
                       if line.split() and line.split()[-1] == f"{ticker}_final.mp4"), None)
    if not prior_date:
        return  # nothing published yet
    prior_version = reindex.quarter(prior_date)
    if prior_version == reindex.quarter(datetime.date.today().isoformat()):
        return  # same quarter — an in-place refresh, not a new version
    dst = f"s3://{bucket}/content/{ticker}/archive/{prior_version}/"
    print(f"  Archiving prior version {prior_version} -> {dst}")
    subprocess.run(["aws", "s3", "cp", f"s3://{bucket}/content/{ticker}/", dst,
                    "--recursive", "--exclude", "archive/*", "--only-show-errors"])


def publish(project):
    bucket = require_env("S3_BUCKET")
    project_dir = get_project_dir(project)
    ticker = project
    prefix = f"content/{ticker}/"
    print(f"Publishing {ticker} -> s3://{bucket}/{prefix}\n")

    snapshot_prior_version(bucket, ticker)

    urls = []
    for rel_tmpl, ctype in ARTIFACTS:
        rel = rel_tmpl.format(t=ticker)
        local = os.path.join(project_dir, rel)
        if not os.path.exists(local):
            continue
        name = os.path.basename(rel)
        key = prefix + name
        r = subprocess.run(
            ["aws", "s3", "cp", local, f"s3://{bucket}/{key}",
             "--content-type", ctype, "--only-show-errors"],
        )
        if r.returncode != 0:
            print(f"  FAILED: {name}")
            continue
        url = f"https://{bucket}.s3.amazonaws.com/{key}"
        print(f"  {url}  ({os.path.getsize(local) / 1e6:.1f} MB)")
        urls.append(url)

    print(f"\n{len(urls)} artifact(s) published to s3://{bucket}/{prefix}")

    # self-describing version metadata + research catalog refresh (best-effort)
    try:
        today = datetime.date.today().isoformat()
        meta = {"ticker": ticker, **reindex.project_meta(ticker), "date": today, "version": reindex.quarter(today)}
        subprocess.run(
            ["aws", "s3", "cp", "-", f"s3://{bucket}/{prefix}meta.json",
             "--content-type", "application/json; charset=utf-8", "--only-show-errors"],
            input=json.dumps(meta, indent=2, ensure_ascii=False), text=True)
        print()
        reindex.run()
    except Exception as e:  # noqa: BLE001
        print(f"  (meta/catalog refresh skipped: {e})")

    return urls


def main():
    ap = argparse.ArgumentParser(description="Publish final deliverables to the public S3 store")
    ap.add_argument("project", help="Project name / ticker (e.g., TRLV)")
    publish(ap.parse_args().project)


if __name__ == "__main__":
    main()
