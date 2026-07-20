#!/usr/bin/env python3
"""Mux webdeck audio onto the silent render.

Variant A ({T}_webpilot.mp4): narration only, placed at exact timeline offsets.
Variant B ({T}_webpilot_music.mp4): + music bed with sidechain ducking under VO.

Usage:
  python3 tools/webdeck/mux_webdeck.py TICKER [--music assets/music/tech_corporate.mp3]
          [--music-gain -20] [--silent projects/T/webdeck/render/silent.mp4]
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent


def run(cmd):
    print("+", " ".join(str(c) for c in cmd[:12]), "...")
    subprocess.run([str(c) for c in cmd], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker")
    ap.add_argument("--music", default="assets/music/tech_corporate.mp3")
    ap.add_argument("--music-gain", type=float, default=-20.0,
                    help="music bed gain in dB before ducking")
    ap.add_argument("--silent", default=None)
    ap.add_argument("--skip-music", action="store_true")
    args = ap.parse_args()
    t = args.ticker.upper()

    wd = REPO / "projects" / t / "webdeck"
    manifest = json.loads((wd / f"{t}_mux_manifest.json").read_text())
    silent = Path(args.silent) if args.silent else wd / "render" / "silent.mp4"
    if not silent.exists():
        print(f"ERROR: {silent} not found (render first)", file=sys.stderr)
        return 1

    total = manifest["total"]
    segs = manifest["segments"]

    # ---- narration mix: delay each segment to its timeline offset ----
    inputs = ["-i", silent]
    for s in segs:
        inputs += ["-i", s["file"]]
    parts, labels = [], []
    for n, s in enumerate(segs):
        ms = round(s["audioStart"] * 1000)
        parts.append(f"[{n+1}:a]aresample=48000,adelay={ms}|{ms}[a{n}]")
        labels.append(f"[a{n}]")
    vo_mix = (";".join(parts) +
              f";{''.join(labels)}amix=inputs={len(segs)}:normalize=0[vo]")

    out_a = wd / f"{t}_webpilot.mp4"
    run(["ffmpeg", "-y", *inputs,
         "-filter_complex", vo_mix + ";[vo]apad[aout]",
         "-map", "0:v", "-map", "[aout]",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-t", f"{total}", out_a])
    print(f"A (VO only):   {out_a}")

    if args.skip_music:
        return 0

    # ---- music variant: bed + sidechain duck keyed by narration ----
    music = REPO / args.music if not Path(args.music).is_absolute() else Path(args.music)
    fade_out_start = max(0.0, total - 4.0)
    fc = (vo_mix +
          ";[vo]asplit=2[voref][vomain]" +
          f";[{len(segs)+1}:a]aresample=48000,atrim=0:{total}," +
          f"afade=t=in:st=0:d=2,afade=t=out:st={fade_out_start}:d=4," +
          f"volume={args.music_gain}dB[mus]" +
          ";[mus][voref]sidechaincompress=threshold=0.02:ratio=8:attack=180:release=1000[musd]" +
          ";[vomain][musd]amix=inputs=2:normalize=0,apad[aout]")
    out_b = wd / f"{t}_webpilot_music.mp4"
    run(["ffmpeg", "-y", *inputs, "-i", music,
         "-filter_complex", fc,
         "-map", "0:v", "-map", "[aout]",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-t", f"{total}", out_b])
    print(f"B (VO+music):  {out_b}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
