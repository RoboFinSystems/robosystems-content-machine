"""
Finish a film: screen each Blender plate under its window of the type layer, mix the voice
over the ducked music at -14 LUFS. A plate with labels set among its lines is first cut back
around the type, so a line passes behind a label and never through it.

A scene's plate is named in the timeline (tools/film/timing.py writes it): its file, whether
it is held out around the type (true, or how many pixels wide the cut is), and how far into the footage the scene starts ("skip";
negative holds the first frame that long).

  python3 tools/film/assemble.py <film folder>     -> <film folder>/renders/<name>.mp4
"""

import json
import subprocess
import sys
from pathlib import Path

film = Path(sys.argv[1]).resolve()
tl = json.loads((film / "timeline.json").read_text())
total = tl["total"]
held = [s["name"] for s in tl["scenes"] if s.get("plate", {}).get("holdout")]
ins, last, n = [], "v0", 0
fc = (
  f"[0:v]split={len(held) + 1}[base]" + "".join(f"[h{i}]" for i in range(len(held)))
  if held
  else "[0:v]copy[base]"
) + ";[base]format=gbrp[v0]"
for s in tl["scenes"]:
  plate = s.get("plate")
  if not plate:
    continue
  n += 1
  f0, f1 = s["frame"], s["frame"] + s["frames"]
  skip = round(plate.get("skip", 0) * 30)
  ins += ["-i", str((film / plate["file"]).resolve())]
  fc += (
    f";[{n}:v]"
    + (f"trim=start_frame={skip},setpts=PTS-STARTPTS," if skip > 0 else "")
    + f"tpad=start={f0 - min(skip, 0)}:start_mode=clone:stop_mode=clone:stop_duration=90,format=gbrp"
  )
  if plate.get("holdout"):  # the type, widened and softened, as a matte over the plate
    fc += (
      f"[q{n}];[h{held.index(s['name'])}]format=gray,lut=y='clip((val-24)*5,0,255)',"
      f"{'dilation,' * (3 if plate['holdout'] is True else plate['holdout'])}gblur=sigma=2,negate,format=gbrp[m{n}]"
      f";[q{n}][m{n}]blend=all_mode=multiply"
    )
  fc += (
    f"[p{n}]"
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
