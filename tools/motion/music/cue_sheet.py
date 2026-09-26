#!/usr/bin/env python3
"""cue_sheet.py: check the picture's must-hit moments against the music's real accents.

The principle: a cut or a reveal that lands a tenth of a second off the music reads as sloppy even
when nobody can say why, and a timing table typed by hand drifts from the track as soon as the music
is re-edited. This script measures the music (onsets, beats, downbeats, level) and prints a cue
sheet: for every hit in the plan, the nearest real accent and how far off it is. A hit more than
--max-miss (0.1 s) from both the nearest strong onset and the nearest downbeat is a MISS.

Usage:
  python3 cue_sheet.py plan.json [--music track.wav] [--music-start 0] [--max-miss 0.1]
                       [--all] [--bpb 4] [--bpm 120] [--out cues.md] [--json cues.json]

plan.json may give hits in any of these shapes (times in film seconds):
  {"music": {"file": "assets/audio/score.wav", "hit": 4.3, "settle": 8.2}}   PLAN.music: every number is a hit
  {"hits": [{"t": 4.3, "name": "reveal", "must": true}, {"t": 6.0, "name": "logo", "must": false}]}
  {"hits": [["reveal", 4.3], ["logo", 6.0]]}
The music file comes from --music, or plan.music.file (relative to the plan). --music-start is the
film time at which the music file starts (default 0, or plan.music.start). Hits named "end",
"duration" or "start", and non-numeric fields, are not treated as hits.

Output: a markdown table (time, name, must-hit, energy, nearest onset and delta, nearest downbeat as
bar.beat and delta, nearest beat and delta, status), then the strongest accents in the track that no
hit uses, which are the natural places for cuts. Exit status 1 if any must-hit is a MISS.

Requirements: numpy, scipy, soundfile, librosa (see requirements.txt); ffmpeg for m4a/mp3.
"""

import argparse
import json
import os
import sys

import librosa
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from musiclib import AN_SR, HOP, analyse, load_audio, refine_onset, to_mono  # noqa: E402

NOT_HITS = {
  "file",
  "start",
  "end",
  "duration",
  "gainDb",
  "gain",
  "fadeOut",
  "fade",
  "bpm",
}


def read_hits(plan):
  hits = []
  raw = plan.get("hits") if isinstance(plan, dict) else plan
  if raw:
    for h in raw:
      if isinstance(h, dict):
        hits.append(
          {
            "name": str(h.get("name", h.get("id", ""))),
            "t": float(h.get("t", h.get("time"))),
            "must": bool(h.get("must", True)),
          }
        )
      else:
        hits.append(
          {
            "name": str(h[0]),
            "t": float(h[1]),
            "must": bool(h[2]) if len(h) > 2 else True,
          }
        )
  music = plan.get("music", {}) if isinstance(plan, dict) else {}
  for k, v in (music or {}).items():
    if k in NOT_HITS or isinstance(v, bool) or not isinstance(v, (int, float)):
      continue
    hits.append({"name": k, "t": float(v), "must": True})
  return sorted(hits, key=lambda h: h["t"])


def nearest(arr, t):
  if len(arr) == 0:
    return None, None
  k = int(np.argmin(np.abs(arr - t)))
  return float(arr[k]), k


def main():
  ap = argparse.ArgumentParser(
    description="Cue sheet: must-hits against the music's onsets and downbeats."
  )
  ap.add_argument("plan", help="plan JSON with hits (see the header)")
  ap.add_argument("--music", help="music file (default: plan.music.file)")
  ap.add_argument(
    "--music-start", type=float, help="film time where the music file starts"
  )
  ap.add_argument("--max-miss", type=float, default=0.1, help="seconds (default 0.1)")
  ap.add_argument("--bpb", type=int, default=4)
  ap.add_argument("--bpm", type=float, help="tempo hint for the beat tracker")
  ap.add_argument(
    "--all",
    action="store_true",
    help="also list every downbeat as a row (a full bar map)",
  )
  ap.add_argument(
    "--accents", type=int, default=8, help="strongest unused accents to list"
  )
  ap.add_argument("--out", help="write the markdown here too")
  ap.add_argument("--json", help="write the rows as JSON")
  args = ap.parse_args()

  plan = json.load(open(args.plan))
  music = plan.get("music", {}) if isinstance(plan, dict) else {}
  path = args.music or (music or {}).get("file")
  if not path:
    ap.error("no music file: pass --music or set plan.music.file")
  if not args.music and not os.path.isabs(path):
    path = os.path.join(os.path.dirname(os.path.abspath(args.plan)), path)
  start = (
    args.music_start
    if args.music_start is not None
    else float((music or {}).get("start", 0.0))
  )
  hits = read_hits(plan)
  if not hits:
    ap.error("no hits found in the plan")

  y, sr = load_audio(path)
  an = analyse(y, sr, args.bpb, args.bpm)
  m = librosa.resample(to_mono(y).astype(np.float32), orig_sr=sr, target_sr=AN_SR)
  oenv = librosa.onset.onset_strength(y=m, sr=AN_SR, hop_length=HOP)
  on_frames = librosa.onset.onset_detect(
    onset_envelope=oenv, sr=AN_SR, hop_length=HOP, units="frames"
  )
  strength = oenv[on_frames] / (oenv.max() + 1e-9)
  strong = on_frames[strength >= 0.25]
  onsets = librosa.frames_to_time(strong, sr=AN_SR, hop_length=HOP) + start
  beats, downbeats = an["beats"] + start, an["downbeats"] + start
  rms = librosa.feature.rms(y=m, hop_length=HOP)[0]
  rms_db = 20 * np.log10(rms + 1e-9)
  peak_db = float(np.percentile(rms_db, 99))

  def energy(t):
    f = librosa.time_to_frames(t - start, sr=AN_SR, hop_length=HOP)
    if f < 0 or f >= len(rms_db):
      return None
    return float(rms_db[max(0, f - 4) : f + 5].mean() - peak_db)

  def bar_beat(t):
    _, k = nearest(beats, t)
    rel = k - an["phase"]
    return f"{rel // args.bpb + 1}.{rel % args.bpb + 1}"

  rows = []
  for h in hits:
    t = h["t"]
    o, _ = nearest(onsets, t)
    d, _ = nearest(downbeats, t)
    b, _ = nearest(beats, t)
    # the tracker's grid is frame-quantised; snap to the actual drum hit
    if o is not None:
      o = refine_onset(y, sr, o - start, win=0.03) + start
    if d is not None:
      d = refine_onset(y, sr, d - start) + start
    if b is not None:
      b = refine_onset(y, sr, b - start) + start
    best = min((abs(x - t) for x in (o, d) if x is not None), default=None)
    miss = best is None or best > args.max_miss
    e = energy(t)
    rows.append(
      {
        "name": h["name"],
        "t": round(t, 3),
        "must": h["must"],
        "energy_db": None if e is None else round(e, 1),
        "onset": None if o is None else round(o, 3),
        "onset_delta": None if o is None else round(o - t, 3),
        "downbeat": None if d is None else round(d, 3),
        "downbeat_delta": None if d is None else round(d - t, 3),
        "bar_beat": bar_beat(d) if d is not None else None,
        "beat": None if b is None else round(b, 3),
        "beat_delta": None if b is None else round(b - t, 3),
        "status": ("MISS" if h["must"] else "off") if miss else "ok",
      }
    )

  def fmt(v, sign=False):
    if v is None:
      return "-"
    return f"{v:+.3f}" if sign else f"{v:.3f}"

  md = [
    f"# Cue sheet: {os.path.basename(path)}",
    "",
    f"Tempo {an['tempo']:.1f} BPM, {args.bpb}/4, first downbeat {downbeats[0]:.3f} s (film time), "
    f"music starts at {start:.3f} s. Energy is dB below the track's loud level. MISS = more than "
    f"{args.max_miss:.2f} s from both the nearest strong onset and the nearest downbeat.",
    "",
    "| time | name | must-hit | energy | nearest onset | delta | nearest downbeat (bar.beat) | delta | nearest beat | delta | status |",
    "|---:|---|:-:|---:|---:|---:|---:|---:|---:|---:|---|",
  ]
  for r in rows:
    md.append(
      f"| {r['t']:.3f} | {r['name']} | {'yes' if r['must'] else 'no'} | "
      f"{'-' if r['energy_db'] is None else format(r['energy_db'], '.1f')} | {fmt(r['onset'])} | {fmt(r['onset_delta'], True)} | "
      f"{fmt(r['downbeat'])} ({r['bar_beat']}) | {fmt(r['downbeat_delta'], True)} | {fmt(r['beat'])} | "
      f"{fmt(r['beat_delta'], True)} | {'**MISS**' if r['status'] == 'MISS' else r['status']} |"
    )

  used = [r["t"] for r in rows]
  order = np.argsort(-oenv[strong])
  free = []
  for k in order:
    if len(free) >= args.accents:
      break
    t = float(librosa.frames_to_time(strong[k], sr=AN_SR, hop_length=HOP)) + start
    if all(abs(t - u) > 0.5 for u in used + [f["t"] for f in free]):
      free.append(
        {
          "t": round(t, 3),
          "strength": round(float(oenv[strong[k]] / oenv.max()), 2),
          "bar_beat": bar_beat(t),
          "energy_db": energy(t),
        }
      )
  if free:
    md += [
      "",
      "Strongest accents no hit uses (natural cut points):",
      "",
      "| time | bar.beat | strength | energy |",
      "|---:|---:|---:|---:|",
    ]
    for f in sorted(free, key=lambda f: f["t"]):
      md.append(
        f"| {f['t']:.3f} | {f['bar_beat']} | {f['strength']:.2f} | "
        f"{'-' if f['energy_db'] is None else format(f['energy_db'], '.1f')} |"
      )
  if args.all:
    md += ["", "Bar map:", "", "| bar | downbeat | energy |", "|---:|---:|---:|"]
    for n, d in enumerate(downbeats, 1):
      e = energy(d)
      md.append(f"| {n} | {d:.3f} | {'-' if e is None else format(e, '.1f')} |")
  misses = [r for r in rows if r["status"] == "MISS"]
  md += ["", f"{len(rows)} hit(s), {len(misses)} must-hit miss(es)."]
  text = "\n".join(md) + "\n"
  print(text)
  if args.out:
    open(args.out, "w").write(text)
  if args.json:
    json.dump(
      {
        "tempo": an["tempo"],
        "downbeats": [round(float(x), 3) for x in downbeats],
        "hits": rows,
        "free_accents": free,
      },
      open(args.json, "w"),
      indent=1,
    )
  return 1 if misses else 0


if __name__ == "__main__":
  sys.exit(main())
