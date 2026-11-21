"""
Emit the prior-coverage card for a company we have covered before.

On a re-cover, `just recover` archives the prior outputs to projects/{T}/.history/{ver}/
then calls this to write projects/{T}/sources/_prior_coverage.md: three facts (when, on
what filing, the one claim). The author drafts the new brief from the current filing
first and opens the card only afterwards, so the new brief is not a sequel to the old.

Usage:
    uv run python tools/prior_coverage.py TICKER .history/2026-Q2 2026-Q2
    (paths are relative to projects/{TICKER}/)
"""

import argparse
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
  ap = argparse.ArgumentParser(
    description="Write sources/_prior_coverage.md from an archived version"
  )
  ap.add_argument("ticker")
  ap.add_argument(
    "prior_rel",
    help="prior version dir relative to the project (e.g. .history/2026-Q2)",
  )
  ap.add_argument("version", help="prior version label (e.g. 2026-Q2)")
  args = ap.parse_args()

  pdir = os.path.join(ROOT, "projects", args.ticker)
  prior = os.path.join(pdir, args.prior_rel)
  t = args.ticker

  meta = {}
  sp = os.path.join(prior, "scripts", f"{t}_script.json")
  if os.path.exists(sp):
    with open(sp, encoding="utf-8") as f:
      meta = (json.load(f) or {}).get("metadata", {})

  brief_path = os.path.join(prior, "reports", f"{t}_brief.md")
  brief = ""
  if os.path.exists(brief_path):
    with open(brief_path, encoding="utf-8") as f:
      brief = f.read()

  h1 = next(
    (line[2:].strip() for line in brief.splitlines() if line.startswith("# ")), t
  )
  label = meta.get("coverage_label")
  head = f"# Prior coverage — {args.version}" + (f" · {label}" if label else "")
  sub = " · ".join(x for x in [meta.get("filing_type"), meta.get("filing_date")] if x)

  # Three facts only: when, on what filing, and the one claim. The hook and bottom
  # line are left out on purpose, so the next brief cannot be rebuilt from the last.
  out = [head]
  if sub:
    out.append(f"_{sub}_")
  out += [
    "",
    f"**Last report:** {meta.get('video_title') or h1}",
  ]
  if meta.get("video_description"):
    out.append(f"**Then, in one line:** {meta['video_description']}")
  out += [
    "",
    "---",
    "_Prior coverage exists. **Open this card only after the new brief is drafted** from the current "
    'filing. Use it for one short "since we last covered this" passage and to check for contradictions; '
    "do not rebuild the old angle. "
    'Set `metadata.coverage_label` (e.g. "Q2 FY2026 update") in the script._',
  ]

  dest = os.path.join(pdir, "sources", "_prior_coverage.md")
  os.makedirs(os.path.dirname(dest), exist_ok=True)
  with open(dest, "w", encoding="utf-8") as f:
    f.write("\n".join(out) + "\n")
  print(f"Wrote {dest}  (prior {args.version})")


if __name__ == "__main__":
  main()
