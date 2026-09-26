#!/usr/bin/env python3
"""pop-scan.py: find pops, flashes and black dips in a rendered film.

The principle: things on screen should arrive and leave with motion, and the picture should only
change all at once on a planned cut. A card that appears or vanishes within one or two frames reads
as a glitch (usually a missing tween, an element outside its clip window, or a seek that skipped
its entrance). A single dark or white frame between scenes reads as a broken edit. Both are easy
to miss at full speed and obvious to the viewer who replays the film. This scans every frame.

What it flags (per frame, on a 192 x 108 copy of the video):
  pop      part of the frame changes sharply in this frame (block difference over --pop-thr) while
           the same area was still two frames before and is still two frames after. Smooth motion
           and fades change a little every frame, so they do not trigger it.
  cut      most of the frame changes at once (over --cut-area of the blocks), not near an allowed cut.
  flash    mean brightness jumps over --flash-thr above its neighbours, not near an allowed cut.
  black    a frame much darker than its neighbours (a dip to black), not near an allowed cut.
Allowed cuts come from --cuts 3.2,7.9 and/or --plan: a JSON file with "cuts": [...], "scenes":
[[id, start], ...] or "SCENES", or an HTML file containing `window.SCENES = [[id, start], ...]`.
Anything within --cut-tol frames (default 2) of an allowed cut is not flagged, except pops.

Usage:
  python3 pop-scan.py render.mp4 [--cuts 3.2,7.9] [--plan index.html] [--sheet pops.png]
                      [--json pops.json] [--pop-thr 28] [--cut-area 0.6] [--flash-thr 45] [--cut-tol 2]

Output: one line per event (time, frame, kind, size, where on screen), a contact sheet of every
event (the frame before, the frame, the frame after; default <video>-pops.png) and optional JSON.
Exit status 1 if anything was flagged.

Requirements: ffmpeg and ffprobe on PATH, numpy; contact_sheet.py next to this file.
"""

import argparse
import json
import os
import re
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from contact_sheet import build_sheets, probe  # noqa: E402

SW, SH, BLOCK = 192, 108, 12  # analysis size and block size: 16 x 9 blocks


def read_frames(path):
  """Every frame at 192 x 108 RGB. Colour matters: a cut between two scenes of equal brightness
  is invisible in greyscale."""
  cmd = [
    "ffmpeg",
    "-v",
    "error",
    "-i",
    path,
    "-vf",
    f"scale={SW}:{SH}:flags=area,format=rgb24",
    "-f",
    "rawvideo",
    "-pix_fmt",
    "rgb24",
    "-",
  ]
  raw = subprocess.run(cmd, check=True, capture_output=True).stdout
  return np.frombuffer(raw, dtype=np.uint8).reshape(-1, SH, SW, 3)


def allowed_cuts(args):
  cuts = [float(x) for x in args.cuts.split(",") if x.strip()] if args.cuts else []
  if args.plan:
    text = open(args.plan).read()
    if args.plan.endswith((".html", ".htm", ".js")):
      m = re.search(r"SCENES\s*=\s*(\[[\s\S]*?\])\s*;", text)
      if not m:
        sys.exit(f"no window.SCENES = [...] found in {args.plan}")
      scenes = json.loads(re.sub(r",\s*]", "]", m.group(1).replace("'", '"')))
      cuts += [float(s[1]) for s in scenes]
    else:
      j = json.loads(text)
      cuts += [float(c) for c in j.get("cuts", [])]
      for s in j.get("scenes", j.get("SCENES", [])):
        cuts.append(
          float(s[1] if isinstance(s, (list, tuple)) else s.get("start", s.get("t")))
        )
  return sorted(c for c in set(cuts) if c > 0)


def block_diffs(frames):
  """Mean absolute RGB difference to the previous frame per 12 x 12 block: [n_frames, 9, 16]."""
  f = frames.astype(np.int16)
  d = np.abs(np.diff(f, axis=0)).mean(axis=3).astype(np.float32)
  d = np.concatenate([np.zeros((1, SH, SW), np.float32), d])
  return d.reshape(len(f), SH // BLOCK, BLOCK, SW // BLOCK, BLOCK).mean(axis=(2, 4))


def scan(frames, fps, cuts, args):
  n = len(frames)
  B = block_diffs(frames)
  luma = (frames.reshape(n, -1, 3) @ np.array([0.2126, 0.7152, 0.0722])).mean(1)
  near_cut = np.zeros(n, bool)
  for c in cuts:
    k = int(round(c * fps))
    near_cut[max(0, k - args.cut_tol) : min(n, k + args.cut_tol + 1)] = True
  # baseline per block: the change two and three frames before and after
  pad = np.pad(B, ((3, 3), (0, 0), (0, 0)), mode="edge")
  base = np.max(
    np.stack([pad[1 : n + 1], pad[2 : n + 2], pad[4 : n + 4], pad[5 : n + 5]]), axis=0
  )
  spike = (B > args.pop_thr) & (B - base > args.pop_thr * 0.75)
  area = (B > args.pop_thr).mean(axis=(1, 2))
  events = []
  edge = int(args.ignore_edges * fps)
  for t in range(1, n):
    if t < edge or t >= n - edge:
      continue
    lo, hi = max(0, t - 8), min(n, t + 9)
    neigh = np.r_[luma[lo : max(lo, t - 2)], luma[min(hi, t + 3) : hi]]
    ref = float(np.median(neigh)) if len(neigh) else float(luma[t])
    kind = None
    if luma[t] < max(12.0, 0.35 * ref) and ref - luma[t] > 25 and not near_cut[t]:
      kind = "black"
    elif luma[t] - ref > args.flash_thr and not near_cut[t]:
      kind = "flash"
    elif area[t] >= args.cut_area and not near_cut[t]:
      kind = "cut"
    elif spike[t].any() and area[t] < args.cut_area:
      kind = "pop"
    if kind is None:
      continue
    ys, xs = np.nonzero(spike[t] if kind == "pop" else B[t] > args.pop_thr)
    box = None
    if len(xs):
      box = [
        int(xs.min() * BLOCK / SW * 100),
        int(ys.min() * BLOCK / SH * 100),
        int((xs.max() + 1) * BLOCK / SW * 100),
        int((ys.max() + 1) * BLOCK / SH * 100),
      ]
    events.append(
      {
        "frame": t,
        "t": round(t / fps, 3),
        "kind": kind,
        "luma": round(float(luma[t]), 1),
        "area": round(
          float((spike[t] if kind == "pop" else B[t] > args.pop_thr).mean()), 3
        ),
        "max_change": round(float(B[t].max()), 1),
        "box_pct": box,
      }
    )
  # merge: a black or flash frame also produces cut-like changes in the frames around it
  merged = []
  for e in events:
    if merged and e["frame"] - merged[-1]["frame"] <= 2:
      rank = {"black": 0, "flash": 1, "cut": 2, "pop": 3}
      if rank[e["kind"]] < rank[merged[-1]["kind"]]:
        merged[-1] = e
      continue
    merged.append(e)
  return merged


def where(box):
  if not box:
    return ""
  x0, y0, x1, y1 = box
  return f"x {x0}-{x1}%, y {y0}-{y1}% of the frame"


def main():
  ap = argparse.ArgumentParser(
    description="Find pops, flashes and black dips in a render."
  )
  ap.add_argument("video")
  ap.add_argument("--cuts", help="allowed cut times in seconds, comma separated")
  ap.add_argument(
    "--plan", help="JSON with cuts/scenes, or index.html with window.SCENES"
  )
  ap.add_argument(
    "--cut-tol",
    type=int,
    default=2,
    help="frames either side of an allowed cut (default 2)",
  )
  ap.add_argument(
    "--pop-thr",
    type=float,
    default=28.0,
    help="block change (0-255) that counts as sharp",
  )
  ap.add_argument(
    "--cut-area",
    type=float,
    default=0.6,
    help="fraction of the frame that makes a change a cut",
  )
  ap.add_argument(
    "--flash-thr",
    type=float,
    default=45.0,
    help="brightness jump (0-255) that counts as a flash",
  )
  ap.add_argument(
    "--ignore-edges",
    type=float,
    default=0.0,
    help="seconds ignored at the start and end",
  )
  ap.add_argument(
    "--sheet", help='contact sheet path (default <video>-pops.png); "none" to skip'
  )
  ap.add_argument("--json", help="write events as JSON")
  args = ap.parse_args()

  info = probe(args.video)
  fps = info["fps"]
  cuts = allowed_cuts(args)
  frames = read_frames(args.video)
  events = scan(frames, fps, cuts, args)
  print(
    f"{args.video}: {len(frames)} frames at {fps:g} fps, {len(cuts)} allowed cut(s)"
    + (f" ({', '.join(f'{c:g}' for c in cuts)})" if cuts else "")
  )
  for e in events:
    print(
      f"  {e['t']:8.3f} s  f{e['frame']:<6} {e['kind']:6} luma {e['luma']:5.1f}  "
      f"area {e['area'] * 100:4.0f}%  {where(e['box_pct'])}"
    )
  if not events:
    print("  nothing flagged")
  if args.json:
    json.dump(
      {"fps": fps, "cuts": cuts, "events": events}, open(args.json, "w"), indent=1
    )
  if events and args.sheet != "none":
    out = args.sheet or os.path.splitext(args.video)[0] + "-pops.png"
    tiles = []
    last = len(frames) - 1
    for e in events:
      for k, tag in ((-1, "before"), (0, e["kind"].upper()), (1, "after")):
        m = min(last, max(0, e["frame"] + k))
        tiles.append(
          {
            "n": m,
            "label": f"{m / fps:.3f}s f{m} {tag}",
            "highlight": k == 0,
            "row_break": k == -1,
          }
        )
    for w in build_sheets(args.video, tiles, out, cols=3, width=360, per_sheet=36):
      print("wrote", w)
  return 1 if events else 0


if __name__ == "__main__":
  sys.exit(main())
