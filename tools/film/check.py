"""
The kit's guard: recompute each brand film's timeline and compare it with the tracked copy.
A change to the timing (tools/film/timing.py) or to the ad's acts that moves a cue, a scene or
the music's hit shows up here before anything is rendered.

  just film-check              compare main and the short cuts with tools/ad/films/expected/
  just film-check --save       record the timelines as they are now (after an intended change)

It needs the voice takes already cached (showcase/robosystems_ad/audio/, not tracked), so it
runs where the films have been built; a film whose takes are missing is skipped and named,
and never voiced. It checks timings only: it does not render, so a change to a page or a
Blender shot is compared by building the film (`just ad-film main`) against the last render.
"""

import hashlib
import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools" / "ad"))
import film as ad  # noqa: E402
import timing  # noqa: E402  (tools/film is on the path once the ad lane is imported)

EXPECTED = REPO / "tools" / "ad" / "films" / "expected"
KEYS = ("format", "total", "hit", "acts", "cues", "scenes")
TOLERANCE = (
  0.02  # seconds: the word aligner may differ by a frame fraction across machines
)


def differs(a, b, path=""):
  if isinstance(a, dict) and isinstance(b, dict):
    out = [f"{path}/{k}: only in one" for k in a.keys() ^ b.keys()]
    for k in a.keys() & b.keys():
      out += differs(a[k], b[k], f"{path}/{k}")
    return out
  if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
    return [
      d for i, (x, y) in enumerate(zip(a, b)) for d in differs(x, y, f"{path}/{i}")
    ]
  if isinstance(a, (int, float)) and isinstance(b, (int, float)):
    return [] if abs(a - b) <= TOLERANCE else [f"{path}: {b} expected, {a} now"]
  return [] if a == b else [f"{path}: {b!r} expected, {a!r} now"]


def main():
  save, bad = "--save" in sys.argv, 0
  for spec_file in sorted((REPO / "tools" / "ad" / "films").glob("*.json")):
    spec = json.loads(spec_file.read_text())
    missing = [
      a
      for a in spec["acts"]
      if not (
        ad.WORK
        / "audio"
        / f"{ad.VOICE}_{a}_{hashlib.sha1(ad.ACTS[a]['text'].encode()).hexdigest()[:8]}.mp3"
      ).exists()
    ]
    if missing:
      print(f"  {spec['name']:16s} skipped: no cached take for {', '.join(missing)}")
      continue
    with tempfile.TemporaryDirectory() as tmp:
      tl = timing.build(
        spec,
        ad.ACTS,
        Path(tmp),
        ad.VOICE,
        ad.MUSIC,
        ad.WORK / "audio",
        ad.PLATES,
        quiet=True,
      )
    now = {k: tl[k] for k in KEYS}
    want = EXPECTED / f"{spec['name']}.json"
    if save:
      want.write_text(json.dumps(now, indent=2) + "\n")
      print(f"  {spec['name']:16s} saved")
      continue
    diff = (
      differs(now, json.loads(want.read_text()))
      if want.exists()
      else ["no expected timeline: run with --save"]
    )
    bad += bool(diff)
    print(f"  {spec['name']:16s} {'DIFFERS' if diff else 'same'}")
    for d in diff[:12]:
      print("     ", d)
  sys.exit(1 if bad else 0)


if __name__ == "__main__":
  main()
