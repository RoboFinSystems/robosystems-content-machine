#!/usr/bin/env python3
"""split_takes.py: split continuous voiceover takes into line pieces, cutting only in true silences.

Why this exists: each act is recorded as ONE continuous take so the delivery flows. The edit then
needs the act as separate pieces (one per caption or picture beat). Cutting at "the energy minimum
between the transcriber's word boundaries" is not safe:
  - whisper's word END times run early, and it hangs most of a pause on the NEXT word's start, so a
    boundary such as waited(0.96-1.40) / and(1.40-2.06) says nothing about where the pause is;
  - plosive closures inside a word ("wai|ted", "ac|tually") are 40-120 ms of near silence, so the
    quietest point near a boundary is often inside a word. A cut there leaves "-ted" at the head
    of the next piece and the listener hears a stitch.

The rule this script enforces, per boundary between piece k and piece k+1:
  1. search [start of k's last word, end of k+1's first word] (whisper times, deliberately wide);
  2. the cut sits inside a quiet run: at least --min-quiet (150 ms) continuously below --quiet-db
     (-50 dBFS, 20 ms RMS windows), with --margin (40 ms) of that silence on both sides of the cut;
  3. the cut is after whisper's end of k's last word and not inside any other word's span;
  4. the longest valid quiet run wins (real phrase pauses are long; closures are short);
  5. if no run qualifies, the boundary FAILS: nothing is written for that take. Re-record with a
     clearer pause (a full stop, or a <break> tag) or merge the two pieces;
  6. after cutting, every piece is transcribed again and must read back as exactly its text
     (--no-verify skips this). This is the check that catches a word split across two pieces.

The pieces tile the take exactly (piece k ends where k+1 begins, with a 4 ms fade on each side of a
cut, inside the silence), so placing them at their recorded spacing reproduces the original take.
check_vo_spacing.py checks a timing plan against that spacing.

Usage:
  python3 split_takes.py split.json [--scores scores.json] [--out-dir pieces/] [--vo vo.json]
                         [--quiet-db -50] [--min-quiet 0.15] [--speech-db -40] [--no-verify] [--dry-run]

split.json (paths relative to the file):
  { "aliases": {"Acme ly": "Acmely"},
    "takes": [
      { "take": "takes/A1-t1.wav", "emotion": "calm",
        "pieces": [ {"id": "l01", "text": "Your invoices are late again."},
                    {"id": "l02", "text": "Nobody noticed until Friday.", "breath": "g1"},
                    {"id": "l03", "text": "So the client called, and waited on hold.", "breath": "g1"} ] } ] }
  The pieces' texts, in order, must add up to the take's script. "breath" (optional) names a group
  of pieces that must play at their recorded spacing (a line meant as one breath).

--scores reuses word timings from score_takes.py (matched by file name) instead of running whisper.

Output: <out-dir>/<id>.wav (same sample rate as the take, 24-bit) and vo.json (merged if it exists):
  { "<id>": { "file", "text", "emotion", "source", "source_offset", "take_order", "on", "off", "dur",
              "words": [[word, start, end], ...], "cut_in": {...}, "cut_out": {...}, "breath"? } }
  on/off = speech onset/offset inside the piece file (first/last 20 ms frame above --speech-db),
  words are relative to the piece file, source_offset = where the piece file starts in the take.
Exit status 1 if any boundary or read-back check fails.

Requirements: pip install numpy soundfile librosa faster-whisper  (score_takes.py next to this file)
"""

import argparse
import difflib
import json
import os
import sys

import numpy as np
import soundfile as sf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from score_takes import norm_tokens, word_accuracy  # noqa: E402

FRAME = 0.02
HOP = 0.005
FADE = 0.004


def frame_db(y, sr):
  """20 ms RMS in dBFS every 5 ms; element i describes the window centred on i * HOP."""
  hop, win = int(HOP * sr), int(FRAME * sr)
  pad = np.pad(y, (win // 2, win // 2))
  n = 1 + (len(pad) - win) // hop
  idx = np.arange(win)[None, :] + hop * np.arange(n)[:, None]
  rms = np.sqrt(np.mean(pad[idx] ** 2, axis=1))
  return 20 * np.log10(rms + 1e-10)


def quiet_runs(db, quiet_db, t0, t1):
  """Maximal runs of frames below quiet_db inside [t0, t1], as (start_s, end_s, max_db)."""
  i0, i1 = max(0, int(t0 / HOP)), min(len(db), int(np.ceil(t1 / HOP)) + 1)
  runs, start = [], None
  for i in range(i0, i1 + 1):
    q = i < i1 and db[i] < quiet_db
    if q and start is None:
      start = i
    elif not q and start is not None:
      runs.append((start * HOP, (i - 1) * HOP, float(db[start:i].max())))
      start = None
  return runs


def load_words(path, scores, whisper_model):
  name = os.path.basename(path)
  for entry in scores:
    if os.path.basename(entry["file"]) == name and entry.get("words"):
      return [(w[0], float(w[1]), float(w[2])) for w in entry["words"]]
  segs, _ = whisper_model().transcribe(
    path, word_timestamps=True, language="en", beam_size=5
  )
  return [(w.word.strip(), float(w.start), float(w.end)) for s in segs for w in s.words]


def piece_word_ranges(pieces, words, aliases):
  """Map each piece to (first_word_index, last_word_index) in the heard words by aligning tokens."""

  def canon(tokens):
    s = f" {' '.join(tokens)} "
    for spoken, written in aliases.items():
      c = "".join(norm_tokens(written))
      for form in {" ".join(norm_tokens(spoken)), " ".join(norm_tokens(written))}:
        s = s.replace(f" {form} ", f" {c} ")
    return s.split()

  script, owner = [], []
  for k, p in enumerate(pieces):
    toks = canon(norm_tokens(p["text"]))
    if not toks:
      raise ValueError(f"piece {p['id']} has no words")
    script += toks
    owner += [k] * len(toks)
  heard, word_of = [], []
  for wi, (w, _, _) in enumerate(words):
    for tok in canon(norm_tokens(w)):
      heard.append(tok)
      word_of.append(wi)
  ops = difflib.SequenceMatcher(a=script, b=heard, autojunk=False).get_opcodes()

  def heard_index(i):
    for op, i1, i2, j1, j2 in ops:
      if i1 <= i < i2:
        if op == "equal":
          return j1 + (i - i1)
        if j2 > j1:
          return min(j2 - 1, j1 + (i - i1) * (j2 - j1) // (i2 - i1))
        return min(j1, len(heard) - 1)
    return len(heard) - 1

  starts = [
    script_i
    for script_i in range(len(script))
    if script_i == 0 or owner[script_i] != owner[script_i - 1]
  ]
  first_word = [word_of[heard_index(i)] for i in starts]
  ranges = []
  for k in range(len(pieces)):
    a = first_word[k]
    b = first_word[k + 1] - 1 if k + 1 < len(pieces) else len(words) - 1
    if b < a:
      raise ValueError(f"could not align piece {pieces[k]['id']} to the transcript")
    ranges.append((a, b))
  return ranges


def choose_cut(db, words, last_k, first_k1, args):
  """Pick the cut between word last_k (end of piece k) and word first_k1 (start of piece k+1)."""
  w_last, w_next = words[last_k], words[first_k1]
  lo, hi = w_last[1], w_next[2]
  candidates, rejected = [], []
  for a, b, peak in quiet_runs(db, args.quiet_db, lo, hi):
    length = b - a
    c = (a + b) / 2
    reason = None
    if length < args.min_quiet:
      reason = f"quiet run {a:.3f}-{b:.3f} is {length * 1000:.0f} ms (< {args.min_quiet * 1000:.0f} ms): likely a closure inside a word"
    elif c - a < args.margin or b - c < args.margin:
      reason = "no margin"
    elif c < w_last[2]:
      reason = (
        f'cut {c:.3f} is before whisper\'s end of "{w_last[0]}" ({w_last[2]:.2f})'
      )
    elif not np.any(db[int(b / HOP) : int(hi / HOP) + 1] >= args.speech_db):
      reason = (
        f'cut {c:.3f} is after all the sound of "{w_next[0]}" (whisper end {hi:.2f})'
      )
    else:
      inside = [
        w
        for i, w in enumerate(words)
        if i not in (last_k, first_k1) and w[1] < c < w[2]
      ]
      if inside:
        reason = f'cut {c:.3f} is inside "{inside[0][0]}"'
    if reason:
      rejected.append(reason)
    else:
      candidates.append((length, a, b, peak, c))
  if not candidates:
    return None, rejected
  length, a, b, peak, c = max(candidates)
  return {
    "at": round(c, 4),
    "quiet_from": round(a, 3),
    "quiet_to": round(b, 3),
    "quiet_ms": int(round(length * 1000)),
    "max_db": round(peak, 1),
  }, rejected


def speech_bounds(db, t0, t1, speech_db):
  i0, i1 = int(t0 / HOP), min(len(db), int(t1 / HOP) + 1)
  loud = np.where(db[i0:i1] >= speech_db)[0]
  if len(loud) == 0:
    return None
  return (i0 + loud[0]) * HOP - FRAME / 2, (i0 + loud[-1]) * HOP + FRAME / 2


def main():
  ap = argparse.ArgumentParser(
    description="Split continuous VO takes into pieces at verified silences."
  )
  ap.add_argument("spec", help="split.json")
  ap.add_argument(
    "--scores", help="scores.json from score_takes.py (reuses its word timings)"
  )
  ap.add_argument("--out-dir", default="pieces")
  ap.add_argument("--vo", default="vo.json", help="vo.json to write or merge into")
  ap.add_argument("--quiet-db", type=float, default=-50.0)
  ap.add_argument(
    "--min-quiet",
    type=float,
    default=0.15,
    help="seconds of continuous silence a cut needs",
  )
  ap.add_argument(
    "--margin", type=float, default=0.04, help="silence kept on each side of the cut"
  )
  ap.add_argument(
    "--speech-db",
    type=float,
    default=-40.0,
    help="level that counts as speech for on/off",
  )
  ap.add_argument("--whisper", default="small.en")
  ap.add_argument(
    "--no-verify", action="store_true", help="skip re-transcribing each piece"
  )
  ap.add_argument("--dry-run", action="store_true", help="report cuts, write nothing")
  args = ap.parse_args()

  spec_dir = os.path.dirname(os.path.abspath(args.spec))
  spec = json.load(open(args.spec))
  aliases = spec.get("aliases", {})
  scores = []
  if args.scores:
    s = json.load(open(args.scores))
    scores = s["takes"] if isinstance(s, dict) else s
  cache = {}

  def whisper_model():
    if "m" not in cache:
      from faster_whisper import WhisperModel

      cache["m"] = WhisperModel(args.whisper, device="cpu", compute_type="int8")
    return cache["m"]

  vo = json.load(open(args.vo)) if os.path.exists(args.vo) else {}
  os.makedirs(args.out_dir, exist_ok=True)
  failed = False

  for tk in spec["takes"]:
    path = (
      tk["take"] if os.path.isabs(tk["take"]) else os.path.join(spec_dir, tk["take"])
    )
    y, sr = sf.read(path, always_2d=True)
    y = y.mean(1)
    db = frame_db(y, sr)
    words = load_words(path, scores, whisper_model)
    pieces = tk["pieces"]
    print(
      f"\n{os.path.basename(path)}  ({len(y) / sr:.2f} s, {len(words)} words, {len(pieces)} pieces)"
    )
    try:
      ranges = piece_word_ranges(pieces, words, aliases)
    except ValueError as e:
      print("  FAIL", e)
      failed = True
      continue

    cuts, ok = [], True
    for k in range(len(pieces) - 1):
      last_k, first_k1 = ranges[k][1], ranges[k + 1][0]
      cut, rejected = choose_cut(db, words, last_k, first_k1, args)
      label = f'  {pieces[k]["id"]} | {pieces[k + 1]["id"]}  "{words[last_k][0]}" / "{words[first_k1][0]}"'
      if cut is None:
        ok = False
        print(f"{label}: FAIL no safe cut")
        for r in rejected or ["no quiet run at all between these words"]:
          print("      rejected:", r)
        continue
      print(
        f"{label}: cut {cut['at']:.3f} s in {cut['quiet_ms']} ms of silence (max {cut['max_db']} dBFS)"
        + (f"; rejected {len(rejected)} shorter/unsafe run(s)" if rejected else "")
      )
      cuts.append(cut)
    if not ok:
      failed = True
      print(
        "  nothing written for this take: re-record with a clearer pause at the failing boundary, or merge those pieces"
      )
      continue

    bounds = [0.0] + [c["at"] for c in cuts] + [len(y) / sr]
    for k, p in enumerate(pieces):
      a, b = bounds[k], bounds[k + 1]
      ia, ib = int(round(a * sr)), int(round(b * sr))
      seg = y[ia:ib].copy()
      nf = int(FADE * sr)
      if k > 0:
        seg[:nf] *= np.linspace(0, 1, nf)
      if k < len(pieces) - 1:
        seg[-nf:] *= np.linspace(1, 0, nf)
      sb = speech_bounds(db, a, b, args.speech_db)
      if sb is None:
        print(f"  FAIL {p['id']}: no speech above {args.speech_db} dBFS")
        failed = True
        continue
      on, off = max(0.0, sb[0] - a), min(b - a, sb[1] - a)
      wa, wb = ranges[k]
      entry = {
        "file": os.path.relpath(
          os.path.join(args.out_dir, f"{p['id']}.wav"),
          os.path.dirname(os.path.abspath(args.vo)),
        ),
        "text": p["text"],
        "emotion": tk.get("emotion"),
        "source": os.path.basename(path),
        "source_offset": round(a, 4),
        "take_order": k,
        "on": round(on, 3),
        "off": round(off, 3),
        "dur": round(b - a, 4),
        "words": [
          [w, round(max(0.0, s - a), 3), round(min(b - a, e - a), 3)]
          for w, s, e in words[wa : wb + 1]
        ],
        "cut_in": {"at": "take start"} if k == 0 else cuts[k - 1],
        "cut_out": {"at": "take end"} if k == len(pieces) - 1 else cuts[k],
      }
      if p.get("breath"):
        entry["breath"] = p["breath"]
      print(f"  {p['id']:6} {a:7.3f}-{b:7.3f}  on {on:.3f} off {off:.3f}  {p['text']}")
      if args.dry_run:
        continue
      out_path = os.path.join(args.out_dir, f"{p['id']}.wav")
      sf.write(out_path, seg, sr, subtype="PCM_24")
      if not args.no_verify:
        segs, _ = whisper_model().transcribe(
          out_path, word_timestamps=False, language="en", beam_size=5
        )
        heard = " ".join(s.text.strip() for s in segs)
        acc, errors = word_accuracy(p["text"], heard, aliases)
        entry["readback"] = heard
        if acc < 1.0:
          failed = True
          print(
            f'  FAIL {p["id"]} reads back as "{heard}" ({acc:.2f}): a word was split or clipped'
          )
      vo[p["id"]] = entry

  if not args.dry_run:
    json.dump(vo, open(args.vo, "w"), indent=1)
    print(f"\nwrote {args.vo} ({len(vo)} pieces)")
  return 1 if failed else 0


if __name__ == "__main__":
  sys.exit(main())
