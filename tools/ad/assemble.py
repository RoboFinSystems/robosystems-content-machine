"""
Finish a film: screen each Blender plate under its window of the type layer, mix the voice
over the ducked music at -14 LUFS.

  python3 tools/ad/assemble.py <film name>     -> showcase/robosystems_ad/films/<name>/renders/<name>.mp4
"""

import json
import subprocess
import sys
from pathlib import Path

WORK = Path(__file__).resolve().parents[2] / "showcase" / "robosystems_ad"
PLATE = {
  "reveal": "graph_hero",
  "trace": "trace",
  "share": "share",
}  # scene -> the Blender shot under it

film = WORK / "films" / sys.argv[1]
tl = json.loads((film / "timeline.json").read_text())
total = tl["total"]
ins, fc, last, n = [], "[0:v]format=gbrp[v0]", "v0", 0
for s in tl["scenes"]:
  if s["name"] not in PLATE:
    continue
  n += 1
  f0, f1 = s["frame"], s["frame"] + s["frames"]
  ins += ["-i", str(film / "plates" / f"{PLATE[s['name']]}.mp4")]
  fc += (
    f";[{n}:v]tpad=start={f0}:start_mode=clone:stop_mode=clone:stop_duration=90,format=gbrp[p{n}]"
    f";[{last}][p{n}]blend=all_mode=screen:enable='gte(t,{f0 / 30 - 0.005:.3f})*lt(t,{f1 / 30 - 0.005:.3f})'[v{n}]"
  )
  last = f"v{n}"
fc += (
  f";[{last}]format=yuv420p[v];[{n + 1}:a]asplit=2[vo][key];[{n + 2}:a]volume=-11dB,afade=t=out:st={total - 1.95:.2f}:d=1.9[mus]"
  ";[mus][key]sidechaincompress=threshold=0.02:ratio=5:attack=120:release=700[duck]"
  ";[vo][duck]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]"
)
out = film / "renders" / f"{tl['name']}.mp4"
subprocess.run(
  [
    "ffmpeg",
    "-v",
    "error",
    "-y",
    "-i",
    str(film / "renders" / "layer.mp4"),
    *ins,
    "-i",
    str(film / "voice.wav"),
    "-i",
    str(film / "music.wav"),
    "-filter_complex",
    fc,
    "-map",
    "[v]",
    "-map",
    "[a]",
    "-t",
    str(total),
    "-c:v",
    "libx264",
    "-crf",
    "17",
    "-preset",
    "medium",
    "-pix_fmt",
    "yuv420p",
    "-c:a",
    "aac",
    "-b:a",
    "256k",
    "-movflags",
    "+faststart",
    str(out),
  ],
  check=True,
)
print(f"{out}  ({total}s, {n} plate(s))")
