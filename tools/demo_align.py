#!/usr/bin/env python3
"""
Word timings for a showcase walkthrough's narration, so actions can land on the words.

For each beat voiced by demo_narrate.py, faster-whisper transcribes the beat's mp3 with word
timestamps and the words are aligned back onto the beat's narration (the same alignment the
webdeck uses, tools/webdeck/align_words.py). The recorder then starts an action marked
`"cue": "phrase"` on the frame where the narration says that phrase, instead of at a guessed
offset.

Output: next to each beat's mp3, <name>_words.json  ->  {"narration": <hash>, "tokens": [[word, start], ...]}
Cached per beat: re-aligned only when the mp3 is newer or the narration changed.

Usage:
    uv run --with faster-whisper python tools/demo_align.py showcase/coffee_roaster/driftline.walkthrough.json
"""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "webdeck"))
from align_words import align, tokens_of  # noqa: E402


def main() -> int:
  ap = argparse.ArgumentParser()
  ap.add_argument("spec")
  ap.add_argument("--whisper", default="small.en")
  ap.add_argument("--force", action="store_true")
  args = ap.parse_args()

  spec_path = Path(args.spec).resolve()
  spec = json.loads(spec_path.read_text())
  model = None
  done = 0
  for beat in spec.get("beats", []):
    narration = (beat.get("narration") or "").strip()
    if not narration or not beat.get("audio"):
      continue
    mp3 = spec_path.parent / beat["audio"]
    if not mp3.exists():
      print(f"ERROR: missing voiceover {mp3} (run demo-narrate first)", file=sys.stderr)
      return 1
    out = mp3.with_name(mp3.stem + "_words.json")
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
    done += 1
    print(
      f"aligned {os.path.relpath(mp3, spec_path.parent)}: {len(toks)} tokens, {len(heard)} heard"
    )
  print(f"  {done} beat(s) aligned")
  return 0


if __name__ == "__main__":
  sys.exit(main())
