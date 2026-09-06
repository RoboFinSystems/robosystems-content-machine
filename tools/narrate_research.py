"""
Narrate a research brief: ElevenLabs read of projects/{T}/reports/{T}_brief.md
-> projects/{T}/reports/{T}_narration.mp3.

The audio article. Same single-voice engine as the blog narration (narrate_common), so a
/research page gets the "Listen to this report" affordance every blog post already ships
with. This is what replaced the Q&A podcast (retired 2026-07-21): one voice reading the
written report, not two voices performing a conversation about it.

Brief-specific cleaning on top of the blog's markdown stripping:

  - `[PROMO_CODE]` is resolved (or its sentence dropped) exactly as `just publish` does, so
    the narration never speaks a placeholder the published text would never show.
  - Cashtags lose their `$` — "$STX" is written for X, and read aloud it becomes "dollar
    S T X". Bare "$M" is left alone; it is a table-header unit, and tables are dropped.
  - The `·` separators in a brief's source-note line become sentence breaks, so
    "Initiating coverage · NYSE: CAG · FY2026 10-K" reads as three clauses, not one.

Tables are stripped, like everywhere else — they read terribly aloud. The prose around them
carries the findings, which is how these briefs are written, but it does mean a sentence that
introduces a table ("Here is the table nobody builds:") lands on the next paragraph instead.

Idempotent: skips if the narration already exists (use --force to regenerate — it re-bills TTS).

Usage:
    uv run python tools/narrate_research.py STX
    uv run python tools/narrate_research.py STX --force
"""

import argparse
import os
import re
import subprocess
import sys

import blog_common as bc
import narrate_common
from helpers import apply_promo_code, get_project_dir, resolve_promo_code

CASHTAG_RE = re.compile(r"\$([A-Z]{2,6})\b")


def brief_path(ticker):
    return os.path.join(get_project_dir(ticker), "reports", f"{ticker}_brief.md")


def read_brief(ticker):
    """The brief's markdown: local if the project has it, else the published copy on S3.

    Three of the back catalogue's tickers (PLNH, GTBIF, TRLV) are published but no longer
    have a local brief, and they still deserve narration.
    """
    local = brief_path(ticker)
    if os.path.exists(local):
        with open(local, encoding="utf-8") as fh:
            return fh.read()
    bucket = os.environ.get("AWS_S3_BUCKET", "").strip()
    if not bucket:
        sys.exit(f"Error: {local} not found and AWS_S3_BUCKET is unset — cannot fall back to S3.")
    key = f"s3://{bucket}/content/{ticker}/{ticker}_brief.md"
    print(f"  (no local brief — reading the published copy: {key})")
    r = subprocess.run(["aws", "s3", "cp", key, "-"], capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        sys.exit(f"Error: no brief for {ticker}, locally or at {key}.")
    return r.stdout


def clean_brief_for_tts(markdown, campaign=None):
    """Brief markdown -> spoken prose. Promo placeholder resolved first, on the raw text,
    the way publish_artifacts does it — then the shared markdown stripping."""
    text = apply_promo_code(markdown, resolve_promo_code(campaign))
    text = text.replace(" · ", ". ").replace("·", ",")
    text = CASHTAG_RE.sub(r"\1", text)
    return bc.clean_markdown_for_tts(text)


def narrate(ticker, force=False):
    out_path = os.path.join(get_project_dir(ticker), "reports", f"{ticker}_narration.mp3")
    if narrate_common.already_narrated(out_path, force):
        return out_path

    # Imported lazily: reindex reaches for AWS_S3_BUCKET at import time in some paths, and
    # narration should work on a project that has never been published.
    import reindex
    campaign = (reindex.project_meta(ticker) or {}).get("campaign")

    chunks = bc.chunk_text(clean_brief_for_tts(read_brief(ticker), campaign))
    narrate_common.synthesize(chunks, out_path, f"{ticker} brief")
    mins, secs = divmod(int(narrate_common.duration_seconds(out_path)), 60)
    print(f"  Runtime: {mins}m{secs:02d}s")
    print(f"  Publish with: just publish {ticker}")
    return out_path


def main():
    ap = argparse.ArgumentParser(description="Narrate a research brief via ElevenLabs TTS")
    ap.add_argument("ticker", help="Project name / ticker (e.g., STX)")
    ap.add_argument("--force", action="store_true", help="Regenerate even if narration exists")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print the cleaned text and character count; call no API, bill nothing")
    args = ap.parse_args()
    if args.dry_run:
        import reindex
        campaign = (reindex.project_meta(args.ticker) or {}).get("campaign")
        text = clean_brief_for_tts(read_brief(args.ticker), campaign)
        chunks = bc.chunk_text(text)
        print(text)
        print(f"\n--- {len(text)} chars, {len(chunks)} chunk(s) ---")
        return
    narrate(args.ticker, force=args.force)


if __name__ == "__main__":
    main()
