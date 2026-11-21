"""
Write one ticker's batch task: projects/{T}/TASK.md from template/BRIEF_TASK.md, and reset
projects/{T}/STATUS.md to `queued`.

`/batch-research` runs this once per ticker after it has looked the filing up in the SEC
graph. A brief already in reports/ means this cohort's run got that far: the tool refuses
unless --redo, which moves the old outputs to .partial/ so the next author never builds on
them (TASK.md tells authors never to open .partial/).

Usage:
    uv run python tools/write_task.py WK --cik 1445305 --accession 0001445305-26-000085 \\
        --form 10-Q --period-end 2026-09-30 --filed 2026-11-05 --company "Workiva Inc."
    uv run python tools/write_task.py MSFT ... --tier deep --redo
"""

import argparse
import datetime
import filecmp
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(ROOT, "template", "BRIEF_TASK.md")
OUTPUTS = ("reports/{t}_brief.md", "social/{t}_x_post.txt", "social/{t}_publish.json")


def main():
  ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
  ap.add_argument("ticker")
  ap.add_argument("--cik", required=True)
  ap.add_argument("--accession", required=True)
  ap.add_argument("--form", required=True)
  ap.add_argument("--period-end", required=True)
  ap.add_argument("--filed", required=True)
  ap.add_argument("--company", required=True)
  ap.add_argument("--tier", choices=("middle", "deep"), default="middle")
  ap.add_argument(
    "--redo", action="store_true", help="move existing outputs to .partial/ first"
  )
  args = ap.parse_args()

  t = args.ticker.upper()
  pdir = os.path.join(ROOT, "projects", t)
  if not os.path.isdir(pdir):
    sys.exit(f"projects/{t} does not exist: scaffold it first (just new {t})")

  existing = [
    rel.format(t=t)
    for rel in OUTPUTS
    if os.path.exists(os.path.join(pdir, rel.format(t=t)))
  ]
  if existing and not args.redo:
    sys.exit(
      f"{t}: outputs already present ({', '.join(existing)}); pass --redo to set them aside"
    )
  if existing:
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    dest = os.path.join(pdir, ".partial", stamp)
    for rel in existing:
      os.makedirs(os.path.join(dest, os.path.dirname(rel)), exist_ok=True)
      shutil.move(os.path.join(pdir, rel), os.path.join(dest, rel))
    print(f"{t}: moved {len(existing)} old output(s) to .partial/{stamp}/")

  # A project scaffolded before the current template carries stale instructions; the
  # campaign ones differ from the base on purpose, so this only warns.
  instr = os.path.join(pdir, "AUTHORING_INSTRUCTIONS.md")
  base = os.path.join(ROOT, "template", "AUTHORING_INSTRUCTIONS.md")
  if not os.path.exists(instr):
    sys.exit(f"{t}: no AUTHORING_INSTRUCTIONS.md")
  if not filecmp.cmp(instr, base, shallow=False):
    print(
      f"{t}: WARNING AUTHORING_INSTRUCTIONS.md differs from the template "
      f"(fine for a campaign project; otherwise copy the template in)"
    )

  prior = os.path.exists(os.path.join(pdir, "sources", "_prior_coverage.md"))
  coverage = (
    "continuing (sources/_prior_coverage.md exists; open it only after drafting)"
    if prior
    else "initiating (no prior coverage card)"
  )
  fields = {
    "TICKER_LOWER": t.lower(),
    "TICKER": t,
    "COMPANY": args.company,
    "CIK": args.cik.lstrip("0") or "0",
    "ACCESSION": args.accession,
    "FORM": args.form,
    "PERIOD_END": args.period_end,
    "FILED": args.filed,
    "TIER": args.tier,
    "COVERAGE": coverage,
    "WRITTEN": datetime.date.today().isoformat(),
  }
  with open(TEMPLATE, encoding="utf-8") as fh:
    text = fh.read()
  for key, val in fields.items():
    text = text.replace("{" + key + "}", val)
  with open(os.path.join(pdir, "TASK.md"), "w", encoding="utf-8") as fh:
    fh.write(text)
  with open(os.path.join(pdir, "STATUS.md"), "w", encoding="utf-8") as fh:
    fh.write(
      f"ticker: {t}\nstage: queued\ntier: {args.tier}\n"
      f"filing: {args.form} {args.period_end} {args.accession}\nblocked_on: none\n"
    )
  print(
    f"{t}: TASK.md written ({args.tier}, {'continuing' if prior else 'initiating'})"
  )


if __name__ == "__main__":
  main()
