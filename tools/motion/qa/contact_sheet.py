#!/usr/bin/env python3
"""contact_sheet.py: tile frames of a render into labelled contact sheets, for reviewing motion on paper.

The principle: you cannot judge motion from the frames you remember. Scrubbing a player skips the
frames that matter, and a pop, a double exposure or a late element only shows up when frames sit
side by side. Review a render as a sheet: every N seconds for pacing and composition, or densely
(every 0.1 to 0.3 s, or every frame) around a cut or a hit to see exactly what happens there.

Usage:
  python3 contact_sheet.py render.mp4 --every 2                      # one frame every 2 s
  python3 contact_sheet.py render.mp4 --around 3.2,7.9 [--span 0.3] [--step 0.1]
                                                                     # dense frames around moments
  python3 contact_sheet.py render.mp4 --around 3.2 --span 0.1 --step frame   # every frame near 3.2 s
  python3 contact_sheet.py render.mp4 --times 1.0,2.5,4.0
  options: [--out sheet.png] [--cols 6] [--width 320] [--per-sheet 48] [--font /path/font.ttf]

Each tile is labelled with its time, frame number and, around a moment, the offset from it. Frames
are exact: a time snaps to the frame showing at that time. More tiles than --per-sheet split into
numbered sheets (sheet-01.png, sheet-02.png). With --around, each moment starts a new row.
Labels need ffmpeg built with drawtext (libfreetype); without it the sheet is written unlabelled.

Requirements: ffmpeg and ffprobe on PATH. Python 3.8+, no packages.
"""

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile


def probe(path):
  out = subprocess.run(
    [
      "ffprobe",
      "-v",
      "error",
      "-select_streams",
      "v:0",
      "-show_entries",
      "stream=width,height,r_frame_rate,nb_frames:format=duration,start_time",
      "-of",
      "json",
      path,
    ],
    check=True,
    capture_output=True,
    text=True,
  ).stdout
  j = json.loads(out)
  st = j["streams"][0]
  num, den = st["r_frame_rate"].split("/")
  return {
    "width": int(st["width"]),
    "height": int(st["height"]),
    "fps": float(num) / float(den),
    "duration": float(j["format"]["duration"]),
    "start": float(j["format"].get("start_time", 0) or 0),
  }


def frame_index(t, fps):
  return max(0, int(math.floor(t * fps + 1e-6)))


_drawtext = None


def has_drawtext():
  global _drawtext
  if _drawtext is None:
    out = subprocess.run(
      ["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True
    ).stdout
    _drawtext = " drawtext " in out
  return _drawtext


def extract(video, info, n, label, width, dest, font=None, highlight=False):
  """Write frame n of video to dest (PNG), scaled to width, with a label bar at the bottom."""
  fps = info["fps"]
  # an accurate seek drops every frame whose timestamp is before t, so aim just before frame n
  t = info.get("start", 0.0) + max(0.0, (n - 0.25) / fps)
  height = int(round(info["height"] * width / info["width"] / 2) * 2)
  vf = [f"scale={width}:{height}"]
  if label and has_drawtext():
    tf = dest + ".txt"
    with open(tf, "w") as f:
      f.write(label)
    size = max(10, width // 22)
    color = "yellow" if highlight else "white"
    opts = [
      f"textfile='{tf}'",
      f"fontsize={size}",
      f"fontcolor={color}",
      "box=1",
      "boxcolor=black@0.65",
      "boxborderw=4",
      "x=6",
      "y=h-th-8",
    ]
    if font:
      opts.append(f"fontfile='{font}'")
    vf.append("drawtext=" + ":".join(opts))
  cmd = [
    "ffmpeg",
    "-v",
    "error",
    "-y",
    "-ss",
    f"{t:.6f}",
    "-i",
    video,
    "-frames:v",
    "1",
    "-vf",
    ",".join(vf),
    dest,
  ]
  subprocess.run(cmd, check=True)


def tile(frames_dir, count, cols, out):
  rows = max(1, math.ceil(count / cols))
  cmd = [
    "ffmpeg",
    "-v",
    "error",
    "-y",
    "-framerate",
    "1",
    "-i",
    os.path.join(frames_dir, "%05d.png"),
    "-vf",
    f"tile={cols}x{rows}:padding=4:margin=4:color=0x202020",
    "-frames:v",
    "1",
    out,
  ]
  subprocess.run(cmd, check=True)


def build_sheets(video, tiles, out, cols=6, width=320, per_sheet=48, font=None):
  """tiles: list of dicts {n, label, highlight?, row_break?}. Returns the sheet paths written."""
  info = probe(video)
  # lay out: a row_break pads the current row with blanks so the next tile starts a new row
  laid = []
  for tl in tiles:
    if tl.get("row_break") and len(laid) % cols:
      laid += [None] * (cols - len(laid) % cols)
    laid.append(tl)
  pages = [laid[i : i + per_sheet] for i in range(0, len(laid), per_sheet)]
  written = []
  base, ext = os.path.splitext(out)
  ext = ext or ".png"
  tmp = tempfile.mkdtemp(prefix="contact-")
  try:
    for p, page in enumerate(pages, 1):
      d = os.path.join(tmp, f"p{p}")
      os.makedirs(d)
      blank = None
      for k, tl in enumerate(page, 1):
        dest = os.path.join(d, f"{k:05d}.png")
        if tl is None:
          if blank is None:
            blank = dest
            h = int(round(info["height"] * width / info["width"] / 2) * 2)
            subprocess.run(
              [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"color=c=0x202020:s={width}x{h}",
                "-frames:v",
                "1",
                dest,
              ],
              check=True,
            )
          else:
            shutil.copy(blank, dest)
          continue
        extract(
          video,
          info,
          tl["n"],
          tl.get("label", ""),
          width,
          dest,
          font,
          tl.get("highlight", False),
        )
      name = f"{base}-{p:02d}{ext}" if len(pages) > 1 else base + ext
      tile(d, len(page), min(cols, len(page)), name)
      written.append(name)
  finally:
    shutil.rmtree(tmp, ignore_errors=True)
  return written


def label_for(n, fps, extra=""):
  return f"{n / fps:7.3f}s  f{n}" + (f"  {extra}" if extra else "")


def main():
  ap = argparse.ArgumentParser(description="Labelled contact sheets from a video.")
  ap.add_argument("video")
  g = ap.add_mutually_exclusive_group(required=True)
  g.add_argument("--every", type=float, help="one frame every N seconds")
  g.add_argument("--around", help="comma separated times to look at closely")
  g.add_argument("--times", help="comma separated exact times")
  ap.add_argument(
    "--span",
    type=float,
    default=0.3,
    help="--around: seconds before and after (default 0.3)",
  )
  ap.add_argument(
    "--step",
    default="0.1",
    help='--around: seconds between frames, or "frame" (default 0.1)',
  )
  ap.add_argument("--out", help="output image (default <video>-sheet.png)")
  ap.add_argument(
    "--cols",
    type=int,
    help="tiles per row (default 6; with --around, one row per moment up to 12)",
  )
  ap.add_argument("--width", type=int, default=320, help="tile width in pixels")
  ap.add_argument("--per-sheet", type=int, default=48)
  ap.add_argument("--font", help="font file for labels (default: fontconfig's sans)")
  args = ap.parse_args()

  info = probe(args.video)
  fps, dur = info["fps"], info["duration"]
  last = max(0, int(dur * fps) - 1)
  tiles = []
  if args.every:
    t = 0.0
    while t < dur:
      n = min(last, frame_index(t, fps))
      tiles.append({"n": n, "label": label_for(n, fps)})
      t += args.every
  elif args.times:
    for t in (float(x) for x in args.times.split(",")):
      n = min(last, frame_index(t, fps))
      tiles.append({"n": n, "label": label_for(n, fps)})
  else:
    step_frames = (
      1 if args.step == "frame" else max(1, int(round(float(args.step) * fps)))
    )
    per_moment = 2 * (int(round(args.span * fps)) // step_frames) + 1
    if args.cols is None:
      args.cols = min(12, per_moment)
    for c in (float(x) for x in args.around.split(",")):
      nc = min(last, frame_index(c, fps))
      reach = int(round(args.span * fps))
      first = True
      for n in range(
        nc - (reach // step_frames) * step_frames, nc + reach + 1, step_frames
      ):
        if 0 <= n <= last:
          off = (n - nc) / fps
          tiles.append(
            {
              "n": n,
              "label": label_for(n, fps, f"{off:+.2f}" if n != nc else f"@{c:g}"),
              "highlight": n == nc,
              "row_break": first,
            }
          )
          first = False
  if not tiles:
    sys.exit("no frames selected")
  args.cols = args.cols or 6
  out = args.out or os.path.splitext(args.video)[0] + "-sheet.png"
  written = build_sheets(
    args.video, tiles, out, args.cols, args.width, args.per_sheet, args.font
  )
  if not has_drawtext():
    print("! this ffmpeg has no drawtext filter: tiles are unlabelled", file=sys.stderr)
  for w in written:
    print("wrote", w)
  print(f"{len(tiles)} frames, {fps:g} fps, {dur:.2f} s")


if __name__ == "__main__":
  sys.exit(main())
