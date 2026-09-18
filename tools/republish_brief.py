"""
Republish a corrected brief in place: the brief file, its CDN copy, and the catalog.

For a correction to a report that is already live - a wrong figure, a lost unit, a typo.
`just publish` is the wrong tool for that: it rewrites meta.json with today's date, so the
page would claim it was first published on the day of the fix, and it re-uploads every
artifact. This uploads the one file the correction touched, with the transforms publish
applies to it, and leaves meta.json, the video, the thumbnails and the narration alone.

The narration is a read of the brief and is NOT regenerated. A fix that changes what a
listener hears needs `just narrate {T} --force` and a full `just publish` instead. A fix
that only restores a "$" or a "%" does not: the spoken form already said "dollars".

Usage:
    uv run python tools/republish_brief.py TRLV
"""

import argparse
import os
import subprocess

import reindex
from helpers import (
  apply_promo_code,
  get_project_dir,
  invalidate_cdn,
  require_env,
  resolve_promo_code,
  strip_angle_brackets,
)

BRIEF_CONTENT_TYPE = "text/markdown; charset=utf-8"  # as publish_artifacts.ARTIFACTS


def republish_brief(ticker):
  bucket = require_env("AWS_S3_BUCKET")
  local = os.path.join(get_project_dir(ticker), "reports", f"{ticker}_brief.md")
  name = f"{ticker}_brief.md"
  key = f"content/{ticker}/{name}"

  # A first publish writes meta.json, and without it the page has no date or title
  # metadata. That is `just publish`'s job, so refuse rather than half-publish.
  if name not in {n for n, _ in reindex.s3_ls(bucket, f"content/{ticker}/")}:
    raise SystemExit(
      f"{ticker} has no published brief to correct. Use `just publish {ticker}`."
    )

  promo = resolve_promo_code((reindex.project_meta(ticker) or {}).get("campaign"))
  with open(local, encoding="utf-8") as fh:
    body = strip_angle_brackets(apply_promo_code(fh.read(), promo))
  subprocess.run(
    [
      "aws",
      "s3",
      "cp",
      "-",
      f"s3://{bucket}/{key}",
      "--content-type",
      BRIEF_CONTENT_TYPE,
      "--only-show-errors",
    ],
    input=body,
    text=True,
    check=True,
  )
  print(f"  {key} ({len(body.encode('utf-8')):,} bytes)")
  invalidate_cdn([key])


def main():
  ap = argparse.ArgumentParser(
    description="Republish a corrected brief without touching the page's date"
  )
  ap.add_argument("tickers", nargs="+", help="Project name(s) / ticker(s)")
  args = ap.parse_args()
  for ticker in args.tickers:
    republish_brief(ticker)
  # The catalog carries the description read off the brief, so rebuild it once.
  reindex.run()


if __name__ == "__main__":
  main()
