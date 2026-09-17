"""
Backfill the card webps for research thumbnails that were published before they existed.

`just publish` builds and uploads the card variants (card_thumbnails.py) from now on.
This covers the reports already live: for every content/{T}/ with a {T}_thumbnail.png
and no card webps, it downloads the PNG, writes the variants and uploads them beside it.
Nothing is republished and no existing object is touched; the variants are new keys, so
no CDN invalidation is needed. Archived versions are skipped: the portal's cards only
show a company's latest report.

Dry run by default. After an --apply, run `just reindex` so the catalog carries the new
asset fields.

Usage:
    uv run python tools/backfill_card_thumbnails.py            # plan only
    uv run python tools/backfill_card_thumbnails.py --apply    # write to S3
    uv run python tools/backfill_card_thumbnails.py --apply --tickers MSFT SBUX
"""

import argparse
import os
import subprocess
import tempfile

import card_thumbnails
import reindex
from helpers import require_env


def card_names(ticker):
  return [
    os.path.basename(card_thumbnails.card_path(f"{ticker}_thumbnail.png", w))
    for w in card_thumbnails.CARD_WIDTHS
  ]


def plan(bucket, tickers=None):
  """[(ticker, missing card names)] for every published thumbnail missing a card."""
  todo = []
  for t in sorted(tickers or reindex.s3_ls_dirs(bucket, "content/")):
    names = {n for n, _ in reindex.s3_ls(bucket, f"content/{t}/")}
    if f"{t}_thumbnail.png" not in names:
      continue
    missing = [n for n in card_names(t) if n not in names]
    if missing:
      todo.append((t, missing))
  return todo


def backfill(bucket, ticker, workdir):
  prefix = f"s3://{bucket}/content/{ticker}/"
  png = os.path.join(workdir, f"{ticker}_thumbnail.png")
  subprocess.run(
    ["aws", "s3", "cp", f"{prefix}{ticker}_thumbnail.png", png, "--only-show-errors"],
    check=True,
  )
  for out in card_thumbnails.write_card_webps(png):
    subprocess.run(
      [
        "aws",
        "s3",
        "cp",
        out,
        f"{prefix}{os.path.basename(out)}",
        "--content-type",
        "image/webp",
        "--only-show-errors",
      ],
      check=True,
    )
    print(f"  {ticker}: {os.path.basename(out)}  ({os.path.getsize(out) / 1e3:.0f} KB)")


def main():
  ap = argparse.ArgumentParser(description="Backfill research card webps in S3")
  ap.add_argument("--apply", action="store_true", help="Write to S3 (default: plan)")
  ap.add_argument("--tickers", nargs="*", help="Limit to these tickers")
  args = ap.parse_args()

  bucket = require_env("AWS_S3_BUCKET")
  todo = plan(bucket, args.tickers)
  print(f"{len(todo)} published thumbnail(s) missing card webps")
  for t, missing in todo:
    print(f"  {t}: {', '.join(missing)}")

  if not args.apply:
    print("\nDry run. Re-run with --apply to write, then `just reindex`.")
    return

  failed = []
  with tempfile.TemporaryDirectory() as workdir:
    for t, _ in todo:
      try:
        backfill(bucket, t, workdir)
      except subprocess.CalledProcessError as e:
        failed.append(t)
        print(f"  {t}: FAILED ({e})")

  print(f"\n{len(todo) - len(failed)} backfilled, {len(failed)} failed")
  if failed:
    raise SystemExit(f"Re-run for: {' '.join(failed)}")
  print("Next: `just reindex` so the catalog carries thumbnail_card_800/1200.")


if __name__ == "__main__":
  main()
