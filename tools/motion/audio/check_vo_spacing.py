#!/usr/bin/env python3
"""check_vo_spacing.py: check that voice pieces cut from one take are placed at their recorded spacing.

The principle: an act is recorded as one continuous take so its lines share a breath, a pitch contour
and a pace. split_takes.py then cuts it into pieces so pictures and captions can hang off each line.
The moment a timing plan moves one of those pieces by even a few hundred milliseconds, the pause
between them stops being the narrator's pause and the delivery sounds stitched. Pieces that belong to
one breath group must keep the gap they were recorded with; pieces from the same take that are not
grouped may be respaced on purpose, and this script reports by how much.

What it checks, per voice line in the plan:
  - breath groups (pieces sharing a "breath" name in vo.json): the gap between consecutive speech
    onsets in the plan must equal the recorded gap, within --tol seconds. Otherwise: ERROR, with the
    onset that restores the recorded spacing;
  - pieces of one take must play in take order, and no line may start before the previous line's
    speech has ended (overlapping voice). Both are ERRORs;
  - other neighbours from the same take: the respacing is reported (INFO). --strict turns every
    same-take neighbour into a breath group.

Usage:
  python3 check_vo_spacing.py plan.json vo.json [--voice narrator] [--tol 0.02] [--strict] [--json out.json]

plan.json: the timing table, either PLAN-shaped  {"vo": [["l01", 0.4, {...}], ["l02", 2.3], ...]}
           or the film data render.ts extracts    {"vo": [{"id": "l01", "onset": 0.4}, ...]}.
           An onset is where the line's SPEECH starts on the film timeline.
vo.json:   the file split_takes.py writes: {"<id>": {source, source_offset, on, off, take_order, breath?}}.
           A vo-data style object keyed by voice ({"narrator": {"<id>": {...}}}) works with --voice.

Exit status 1 if any ERROR. Requirements: Python 3.8+, no packages.
"""

import argparse
import json
import sys


def load_plan(path):
  plan = json.load(open(path))
  rows = plan.get("vo", []) if isinstance(plan, dict) else plan
  onsets = {}
  for row in rows:
    if isinstance(row, (list, tuple)):
      onsets[str(row[0])] = float(row[1])
    elif isinstance(row, dict) and "id" in row:
      onsets[str(row["id"])] = float(row.get("onset", row.get("at")))
  return onsets


def load_vo(path, voice):
  vo = json.load(open(path))
  if voice:
    vo = vo[voice]
  elif vo and all(
    isinstance(v, dict) and "on" not in v and "file" not in v for v in vo.values()
  ):
    if len(vo) == 1:
      vo = next(iter(vo.values()))
    else:
      sys.exit(f"{path} holds several voices ({', '.join(vo)}): pass --voice")
  return vo


def check(onsets, vo, tol, strict):
  """Return (rows, errors). Each row describes one pair of neighbouring pieces from the same take."""
  rows, errors = [], []
  placed = [(onsets[i], i) for i in onsets if i in vo]
  missing = [i for i in onsets if i not in vo]
  placed.sort()
  # overlap: a line starting before the previous line's speech ends (any source)
  for (ta, a), (tb, b) in zip(placed, placed[1:]):
    end_a = ta + vo[a]["off"] - vo[a]["on"]
    if tb < end_a - tol:
      errors.append(
        f"{b} starts at {tb:.3f} s, before {a} finishes speaking ({end_a:.3f} s): voices overlap"
      )
  by_take = {}
  for t, i in placed:
    src = vo[i].get("source")
    if src is not None and "source_offset" in vo[i]:
      by_take.setdefault(src, []).append(i)
  for src, ids in by_take.items():
    ids.sort(key=lambda i: vo[i].get("take_order", 0))
    for a, b in zip(ids, ids[1:]):
      ea, eb = vo[a], vo[b]
      recorded = (eb["source_offset"] + eb["on"]) - (ea["source_offset"] + ea["on"])
      planned = onsets[b] - onsets[a]
      delta = planned - recorded
      grouped = strict or (
        ea.get("breath") is not None and ea.get("breath") == eb.get("breath")
      )
      row = {
        "take": src,
        "a": a,
        "b": b,
        "recorded_gap": round(recorded, 3),
        "planned_gap": round(planned, 3),
        "delta": round(delta, 3),
        "breath": ea.get("breath") if grouped else None,
        "status": "ok",
      }
      if planned <= 0:
        row["status"] = "ERROR"
        errors.append(f"{b} is placed before {a}, but {a} comes first in take {src}")
      elif grouped and abs(delta) > tol:
        row["status"] = "ERROR"
        row["fix"] = round(onsets[a] + recorded, 3)
        errors.append(
          f"{a} -> {b} (breath {row['breath'] or 'strict'}): planned gap {planned:.3f} s, recorded "
          f"{recorded:.3f} s ({delta:+.3f} s). Put {b} at {row['fix']:.3f} s to keep the one-breath delivery"
        )
      elif abs(delta) > tol:
        row["status"] = "respaced"
      rows.append(row)
  return rows, errors, missing


def main():
  ap = argparse.ArgumentParser(
    description="Check voice pieces from one take keep their recorded spacing."
  )
  ap.add_argument("plan", help="plan.json (PLAN.vo rows or film data vo list)")
  ap.add_argument("vo", help="vo.json written by split_takes.py")
  ap.add_argument("--voice", help="voice key when vo.json is keyed by voice")
  ap.add_argument(
    "--tol",
    type=float,
    default=0.02,
    help="allowed gap difference in seconds (default 0.02)",
  )
  ap.add_argument(
    "--strict",
    action="store_true",
    help="treat every same-take neighbour as one breath group",
  )
  ap.add_argument("--json", help="also write the result as JSON")
  args = ap.parse_args()

  onsets = load_plan(args.plan)
  vo = load_vo(args.vo, args.voice)
  rows, errors, missing = check(onsets, vo, args.tol, args.strict)

  print("| take | pair | breath | recorded gap | planned gap | delta | status |")
  print("|---|---|---|---:|---:|---:|---|")
  for r in rows:
    print(
      f"| {r['take']} | {r['a']} > {r['b']} | {r['breath'] or ''} | {r['recorded_gap']:.3f} | "
      f"{r['planned_gap']:.3f} | {r['delta']:+.3f} | {r['status']} |"
    )
  for m in missing:
    print(f"INFO  {m} is in the plan but not in {args.vo} (not a split piece, skipped)")
  for r in rows:
    if r["status"] == "respaced":
      print(
        f"INFO  {r['a']} -> {r['b']} respaced by {r['delta']:+.3f} s (not a breath group, allowed)"
      )
  for e in errors:
    print("ERROR", e)
  if args.json:
    json.dump(
      {"pairs": rows, "errors": errors, "missing": missing},
      open(args.json, "w"),
      indent=1,
    )
  print(f"{len(rows)} same-take pair(s) checked, {len(errors)} error(s)")
  return 1 if errors else 0


if __name__ == "__main__":
  sys.exit(main())
