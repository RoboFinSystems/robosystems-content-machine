#!/usr/bin/env python3
"""join_on_downbeats.py: join music takes, or fit a track to a length, the way a music editor would.

The principle: a score has to feel like one performance. AI music tools hand you an original plus
continuations (extensions, alternates), and a temp edit that splices them "wherever the picture
needs it" drops a beat, jumps the harmony or smears two drum kits together. The listener does not
know why, but the track randomly dips and stops feeling played. A musical edit follows three rules:
  1. join only on a downbeat, where both sides are playing the same harmony and bass (chroma and
     bass fingerprints of the bars around the join are compared, and the best match wins);
  2. line the two sides up by their drum transients (cross-correlation of percussive onsets, within
     +-40 ms of the tracked downbeat), then crossfade over ONE beat with an equal-power curve, so the
     downbeat hit comes whole from the incoming side;
  3. never time-stretch or pitch-shift. Every sample plays at its native speed. If two takes are in
     different tunings or tempos the report says so: pick other takes rather than bend them.

Modes:
  join  A B [C ...]   play A, then continue into B at the best matching downbeat, then into C, ...
                      By default the join is looked for in the last --search seconds of the audio so far
                      and the first --search seconds of the next take (a continuation usually starts by
                      replaying the end of the original). --at pins joins by hand; they are still
                      snapped to downbeats and aligned.
  fit   TRACK --target SECONDS
                      shorter: remove whole bars between two downbeats whose surroundings match;
                      longer: repeat whole bars the same way (jump back to a matching earlier downbeat).
                      The first --keep-head and last --keep-tail seconds are never cut, nor --protect spans.

Usage:
  python3 join_on_downbeats.py join original.wav continuation.m4a [more ...] --out score.wav
          [--search 30] [--at 61.2:3.9,...] [--match-level] [--bpb 4] [--report joins]
  python3 join_on_downbeats.py fit track.wav --target 58 --out track-58s.wav
          [--keep-head 4] [--keep-tail 8] [--protect 20-24.5,...] [--report fit]

Options common to both: --bpb beats per bar (default 4), --bpm a tempo hint for the beat tracker,
--downbeat T[,T...] a known downbeat time per input (fixes a wrong bar phase), --fade-beats (default 1),
--top N alternatives listed in the report (default 5).

Output: the WAV (same sample rate as the first input, 24-bit), <report>.json and <report>.md with
every join: times in each source and in the output, the transient lag, similarity scores (chroma,
bass, rhythm, total), grid drift one bar after the join, level and tuning differences, and the next
best candidates. Listen to every join; a similarity under about 0.8 usually sounds like an edit.

Requirements: pip install -r requirements.txt (numpy, scipy, soundfile, librosa); ffmpeg for m4a/mp3.
"""

import argparse
import json
import os
import sys

import numpy as np
import soundfile as sf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from musiclib import (
  align_transients,
  analyse,
  context_similarity,
  is_downbeat,
  level_db,  # noqa: E402
  load_audio,
  match_channels,
  refine_onset,
  splice,
  tuning_cents,
)

GOOD = 0.8  # a join scoring below this total similarity usually sounds like an edit


def parse_pairs(s):
  out = []
  for part in s.split(","):
    a, b = part.split(":") if ":" in part else part.split("-")
    out.append((float(a), float(b)))
  return out


def downbeat_indices(an, lo, hi, need_before=1, need_after=1):
  n = len(an["beats"])
  return [
    i
    for i in range(need_before, n - need_after)
    if is_downbeat(an, i) and lo <= an["beats"][i] <= hi
  ]


def rank_joins(A, B, a_lo, a_hi, b_lo, b_hi, bpb, same=False, length_ok=None):
  """Score every (downbeat in A, downbeat in B) pair in the ranges; best first."""
  ctx = 2 * bpb
  cands = []
  for i in downbeat_indices(A, a_lo, a_hi):
    for j in downbeat_indices(B, b_lo, b_hi):
      if same and abs(i - j) < bpb:
        continue
      if length_ok is not None and not length_ok(i, j):
        continue
      sim = context_similarity(A, i, B, j, ctx)
      if sim is not None:
        cands.append((sim["total"], i, j, sim))
  # best match first; among equal matches (to 0.01) the later join in A keeps more of the original
  cands.sort(key=lambda c: (-round(c[0], 2), -A["beats"][c[1]]))
  return cands


def make_join(yA, A, i, yB, B, j, sr, fade_beats, bpb):
  """Align and splice A's downbeat i to B's downbeat j. Returns (audio, record)."""
  bar = bpb * A["period"]
  tA = refine_onset(yA, sr, float(A["beats"][i]))
  tB = float(B["beats"][j])
  tB2, corr = align_transients(yA, tA, yB, tB, sr, pre=bar, post=bar)
  fade = fade_beats * A["period"]
  out, f0, f1 = splice(yA, tA, yB, tB2, sr, fade)
  # grid continuity: one bar after the join, where does B's next downbeat hit, against where A's
  # grid (its own next downbeat if A continues, else its tempo) says it should?
  k = min(j + bpb, len(B["beats"]) - 1)
  b_next = refine_onset(yB, sr, float(B["beats"][k])) - tB2
  if i + bpb < len(A["beats"]) and A["beats"][i + bpb] < yA.shape[1] / sr - 0.1:
    a_next = refine_onset(yA, sr, float(A["beats"][i + bpb])) - tA
  else:
    a_next = bpb * A["period"]
  drift = (b_next - a_next * (k - j) / bpb) * 1000
  rec = {
    "a_time": round(tA, 3),
    "b_time_tracked": round(tB, 3),
    "b_time": round(tB2, 4),
    "lag_ms": round((tB2 - tB) * 1000, 1),
    "transient_corr": round(corr, 3),
    "out_time": round(tA, 3),
    "fade": [round(f0, 3), round(f1, 3)],
    "grid_drift_ms_after_1_bar": round(float(drift), 1),
    "tempo_a": round(A["tempo"], 2),
    "tempo_b": round(B["tempo"], 2),
    "level_diff_db": round(
      level_db(yB, sr, tB2 - bar, tB2) - level_db(yA, sr, tA - bar, tA), 1
    ),
  }
  return out, rec


def describe(rec, sim, alts, label):
  warn = []
  if sim["total"] < GOOD:
    warn.append(
      f"low similarity {sim['total']:.2f}: likely audible, listen and consider --at"
    )
  if abs(rec["grid_drift_ms_after_1_bar"]) > 25:
    warn.append(
      f"beat grid drifts {rec['grid_drift_ms_after_1_bar']:+.0f} ms over the next bar (tempos differ)"
    )
  if abs(rec["level_diff_db"]) > 2:
    warn.append(f"level differs {rec['level_diff_db']:+.1f} dB (try --match-level)")
  if abs(rec.get("tuning_diff_cents", 0)) > 15:
    warn.append(
      f"tunings differ by {rec['tuning_diff_cents']:+.0f} cents: the join will sound sour"
    )
  rec.update(similarity=sim, alternatives=alts, warnings=warn, label=label)
  return rec


def report(path, meta, joins):
  with open(path + ".json", "w") as f:
    json.dump({**meta, "joins": joins}, f, indent=1)
  lines = [
    f"# {meta['mode']}: {os.path.basename(meta['output'])}",
    "",
    f"Output {meta['duration']:.2f} s at {meta['sr']} Hz. Sources: "
    + ", ".join(meta["sources"])
    + ".",
    "",
    "| # | join | source times | out time | fade | lag | chroma | bass | rhythm | total | drift 1 bar | level |",
    "|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|",
  ]
  for n, r in enumerate(joins, 1):
    s = r["similarity"]
    lines.append(
      f"| {n} | {r['label']} | {r['a_time']:.3f} > {r['b_time']:.3f} | {r['out_time']:.3f} | "
      f"{r['fade'][0]:.2f}-{r['fade'][1]:.2f} | {r['lag_ms']:+.1f} ms | {s['chroma']:.2f} | {s['bass']:.2f} | "
      f"{s['rhythm']:.2f} | **{s['total']:.2f}** | {r['grid_drift_ms_after_1_bar']:+.0f} ms | {r['level_diff_db']:+.1f} dB |"
    )
  for n, r in enumerate(joins, 1):
    for w in r["warnings"]:
      lines.append(f"- join {n}: {w}")
    if r["alternatives"]:
      alts = "; ".join(
        f"{a['a_time']:.2f} > {a['b_time']:.2f} ({a['total']:.2f})"
        for a in r["alternatives"]
      )
      lines.append(f"- join {n} alternatives: {alts}")
  md = "\n".join(lines) + "\n"
  with open(path + ".md", "w") as f:
    f.write(md)
  return md


def cmd_join(args):
  if len(args.inputs) < 2:
    sys.exit("join needs at least two inputs")
  firsts = [float(x) for x in args.downbeat.split(",")] if args.downbeat else []
  pins = parse_pairs(args.at) if args.at else []
  y, sr = load_audio(args.inputs[0])
  ch = y.shape[0]
  cur_an = analyse(y, sr, args.bpb, args.bpm, firsts[0] if firsts else None)
  tuning0 = tuning_cents(y, sr)
  joins, prev_join = [], 0.0
  for k, path in enumerate(args.inputs[1:], 1):
    yB, _ = load_audio(path, sr)
    yB = match_channels(yB, ch)
    B = analyse(yB, sr, args.bpb, args.bpm, firsts[k] if len(firsts) > k else None)
    bar = args.bpb * cur_an["period"]
    dur_a, dur_b = y.shape[1] / sr, yB.shape[1] / sr
    if len(pins) >= k:
      pa, pb = pins[k - 1]
      a_lo, a_hi, b_lo, b_hi = pa - bar / 2, pa + bar / 2, pb - bar / 2, pb + bar / 2
    else:
      a_lo, a_hi = max(prev_join + bar, dur_a - args.search), dur_a - bar
      b_lo, b_hi = 0.0, min(args.search, dur_b - 2 * bar)
    cands = rank_joins(cur_an, B, a_lo, a_hi, b_lo, b_hi, args.bpb)
    if not cands:
      sys.exit(
        f"no downbeat pair found for join {k} (A {a_lo:.1f}-{a_hi:.1f} s, B {b_lo:.1f}-{b_hi:.1f} s)"
      )
    _, i, j, sim = cands[0]
    if args.match_level:
      t = cur_an["beats"][i]
      g = level_db(y, sr, t - bar, t) - level_db(
        yB, sr, B["beats"][j] - bar, B["beats"][j]
      )
      yB = yB * 10 ** (g / 20)
    y, rec = make_join(y, cur_an, i, yB, B, j, sr, args.fade_beats, args.bpb)
    rec["tuning_diff_cents"] = round(tuning_cents(yB, sr) - tuning0, 1)
    if args.match_level:
      rec["gain_applied_db"] = round(g, 1)
    alts = [
      {
        "a_time": round(float(cur_an["beats"][a]), 3),
        "b_time": round(float(B["beats"][b]), 3),
        "total": t,
      }
      for t, a, b, _ in cands[1 : 1 + args.top]
    ]
    joins.append(
      describe(
        rec,
        sim,
        alts,
        f"{os.path.basename(args.inputs[k - 1]) if k == 1 else 'result'} > {os.path.basename(path)}",
      )
    )
    prev_join = rec["out_time"]
    cur_an = analyse(y, sr, args.bpb, args.bpm, rec["out_time"])
  return y, sr, joins


def cmd_fit(args):
  y, sr = load_audio(args.inputs[0])
  A = analyse(
    y,
    sr,
    args.bpb,
    args.bpm,
    float(args.downbeat.split(",")[0]) if args.downbeat else None,
  )
  dur = y.shape[1] / sr
  beats = A["beats"]
  delta = args.target - dur
  if abs(delta) < A["period"] / 2:
    sys.exit(f"already {dur:.2f} s, within half a beat of {args.target} s")
  protect = parse_pairs(args.protect) if args.protect else []
  head, tail = args.keep_head, dur - args.keep_tail

  def span(i, j):
    return beats[j] - beats[i]

  if delta < 0:
    # remove [beats[i], beats[j]) with i < j: result = dur - span
    def ok(i, j):
      if not (i < j and beats[i] >= head and beats[j] <= tail):
        return False
      return not any(beats[i] < b and a < beats[j] for a, b in protect)

    want = -delta
  else:
    # repeat [beats[i], beats[j]): play up to beats[j], then jump back to beats[i]
    def ok(i, j):
      return i < j and beats[i] >= head and beats[j] <= tail

    want = delta
  tol = args.tolerance if args.tolerance is not None else A["period"] / 2
  down = [i for i in range(1, len(beats) - 1) if is_downbeat(A, i)]
  lens = sorted(
    {round(span(i, j), 4) for i in down for j in down if ok(i, j)},
    key=lambda v: abs(v - want),
  )
  if not lens:
    sys.exit("no whole-bar span fits: loosen --keep-head/--keep-tail/--protect")
  best_err = abs(lens[0] - want)
  # among spans whose length is as close to the need as possible (within tol), the best-matching pair wins
  cands = rank_joins(
    A,
    A,
    0,
    dur,
    0,
    dur,
    args.bpb,
    same=True,
    length_ok=lambda i, j: ok(i, j) and abs(span(i, j) - want) - best_err <= tol,
  )
  if not cands:
    sys.exit("no matching pair of downbeats for that length")
  _, i, j, sim = cands[0]
  if delta < 0:
    out, rec = make_join(y, A, i, y, A, j, sr, args.fade_beats, args.bpb)
    label = f"remove {span(i, j):.2f} s ({(j - i) // args.bpb} bars) {beats[i]:.2f}-{beats[j]:.2f}"
  else:
    out, rec = make_join(y, A, j, y, A, i, sr, args.fade_beats, args.bpb)
    label = f"repeat {span(i, j):.2f} s ({(j - i) // args.bpb} bars) {beats[i]:.2f}-{beats[j]:.2f}"
  alts = [
    {
      "a_time": round(float(beats[a]), 3),
      "b_time": round(float(beats[b]), 3),
      "total": t,
    }
    for t, a, b, _ in cands[1 : 1 + args.top]
  ]
  return out, sr, [describe(rec, sim, alts, label)]


def main():
  ap = argparse.ArgumentParser(
    description="Join or fit music takes on matching downbeats, no time-stretch."
  )
  ap.add_argument("mode", choices=["join", "fit"])
  ap.add_argument("inputs", nargs="+")
  ap.add_argument("--out", required=True, help="output WAV")
  ap.add_argument(
    "--report", help="report path without extension (default: next to --out)"
  )
  ap.add_argument("--bpb", type=int, default=4, help="beats per bar")
  ap.add_argument("--bpm", type=float, help="tempo hint for the beat tracker")
  ap.add_argument("--downbeat", help="a known downbeat time per input, comma separated")
  ap.add_argument(
    "--fade-beats",
    type=float,
    default=1.0,
    help="crossfade length in beats (default 1)",
  )
  ap.add_argument("--top", type=int, default=5, help="alternatives to list per join")
  ap.add_argument(
    "--search",
    type=float,
    default=30.0,
    help="join: seconds to look in at the end of A and the start of B",
  )
  ap.add_argument(
    "--at", help="join: pinned joins A_TIME:B_TIME, comma separated, one per join"
  )
  ap.add_argument(
    "--match-level",
    action="store_true",
    help="join: gain the incoming take to match the bar before the join",
  )
  ap.add_argument("--target", type=float, help="fit: target length in seconds")
  ap.add_argument(
    "--tolerance",
    type=float,
    help="fit: accept spans this far from the ideal (default half a beat)",
  )
  ap.add_argument(
    "--keep-head",
    type=float,
    default=4.0,
    help="fit: never cut or repeat before this time",
  )
  ap.add_argument(
    "--keep-tail",
    type=float,
    default=8.0,
    help="fit: never cut the last N seconds (the ending)",
  )
  ap.add_argument("--protect", help="fit: spans that must survive, e.g. 20-24.5,40-41")
  args = ap.parse_args()

  if args.mode == "fit":
    if args.target is None:
      ap.error("fit needs --target")
    out, sr, joins = cmd_fit(args)
  else:
    out, sr, joins = cmd_join(args)
  peak = float(np.abs(out).max())
  if peak > 1.0:
    out = out / peak * 0.999
    print(
      f"! peak {20 * np.log10(peak):+.1f} dBFS after joining: scaled down to avoid clipping"
    )
  sf.write(args.out, out.T, sr, subtype="PCM_24")
  meta = {
    "mode": args.mode,
    "output": args.out,
    "sources": [os.path.basename(p) for p in args.inputs],
    "sr": sr,
    "duration": round(out.shape[1] / sr, 3),
  }
  if args.mode == "fit":
    meta["target"] = args.target
    off = meta["duration"] - args.target
    if abs(off) > 0.05:
      joins[0]["warnings"].append(
        f"whole bars only: the result is {meta['duration']:.2f} s, {off:+.2f} s from the "
        f"target. Fade the tail, or end the picture on the last downbeat"
      )
  rep = args.report or os.path.splitext(args.out)[0] + "-report"
  print(report(rep, meta, joins))
  print(f"wrote {args.out}, {rep}.json, {rep}.md")
  return 0


if __name__ == "__main__":
  sys.exit(main())
