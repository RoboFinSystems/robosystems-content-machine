#!/usr/bin/env python3
"""Word timings for a project's narration, so the deck can build to the voice.

For each segment voiceover, faster-whisper transcribes the mp3 with word timestamps, and
the recognised words are aligned back onto the *script's* narration tokens (difflib over
normalised words). Every script token gets a start time: a matched token takes its word's
time, an unmatched one is interpolated between its matched neighbours. The deck then finds
a cue phrase among the script tokens, which is exact, instead of searching a transcript.

Output: videos/audio/{T}_segment_{id}_words.json  ->  {"tokens": [[word, start], ...]}
Cached per segment: re-aligned only when the mp3 or the narration is newer / different.

Shared with the showcase lane: tools/demo_align.py aligns walkthrough beats with the same align().

Usage: uv run --with faster-whisper python tools/align_words.py TICKER
"""

import argparse
import difflib
import hashlib
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def norm(w: str) -> str:
  return re.sub(r"[^a-z0-9]", "", w.lower())


def tokens_of(text: str) -> list[str]:
  return text.split()


def align(script_tokens: list[str], heard: list[tuple[str, float]], dur: float):
  a = [norm(w) for w in script_tokens]
  b = [norm(w) for w, _ in heard]
  times: list[float | None] = [None] * len(a)
  sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
  for blk in sm.get_matching_blocks():
    for k in range(blk.size):
      times[blk.a + k] = heard[blk.b + k][1]
  # interpolate the gaps between matched neighbours (and pin the ends)
  known = [i for i, t in enumerate(times) if t is not None]
  if not known:
    step = dur / max(1, len(a))
    return [(w, round(i * step, 3)) for i, w in enumerate(script_tokens)]
  out = list(times)
  first, last = known[0], known[-1]
  for i in range(first):
    out[i] = times[first] * i / max(1, first)
  for i in range(last + 1, len(a)):
    out[i] = times[last] + (dur - times[last]) * (i - last) / max(1, len(a) - last)
  for lo, hi in zip(known, known[1:]):
    for i in range(lo + 1, hi):
      out[i] = times[lo] + (times[hi] - times[lo]) * (i - lo) / (hi - lo)
  return [(w, round(t, 3)) for w, t in zip(script_tokens, out)]


def main() -> int:
  ap = argparse.ArgumentParser()
  ap.add_argument("ticker")
  ap.add_argument("--whisper", default="small.en")
  ap.add_argument("--force", action="store_true")
  args = ap.parse_args()
  t = args.ticker.upper()
  proj = REPO / "projects" / t

  script = json.loads((proj / "scripts" / f"{t}_script.json").read_text())
  items = [
    (
      s["id"],
      s["narration"],
      proj / "videos" / "audio" / f"{t}_segment_{s['id']}_voiceover.mp3",
    )
    for s in script["segments"]
  ]

  model = None
  for sid, narration, mp3 in items:
    if not mp3.exists():
      print(f"ERROR: missing voiceover {mp3} (run voiceover first)", file=sys.stderr)
      return 1
    out = mp3.with_name(mp3.name.replace("_voiceover.mp3", "_words.json"))
    digest = hashlib.sha1(narration.encode()).hexdigest()[:12]
    if out.exists() and not args.force:
      cached = json.loads(out.read_text())
      if (
        cached.get("narration") == digest and out.stat().st_mtime >= mp3.stat().st_mtime
      ):
        continue
    if model is None:
      from faster_whisper import WhisperModel

      model = WhisperModel(args.whisper, device="cpu", compute_type="int8")
    segs, info = model.transcribe(
      str(mp3), word_timestamps=True, language="en", beam_size=5
    )
    heard = [(w.word.strip(), float(w.start)) for s in segs for w in (s.words or [])]
    toks = align(tokens_of(narration), heard, float(info.duration))
    out.write_text(json.dumps({"narration": digest, "tokens": toks}))
    print(f"aligned {mp3.name}: {len(toks)} tokens, {len(heard)} heard")
  return 0


if __name__ == "__main__":
  sys.exit(main())
