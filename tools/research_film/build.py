"""
Build one research film: a 60 to 90 second cut of a published brief, in the brand film's form.

  just research-film MSFT            (spec: projects/MSFT/film/MSFT_film.json)
  just research-film MSFT --check    (the figure check only: no voice, no render)
  just research-film MSFT --stills 4,20,41
  just research-film MSFT --cut long --from how   (re-render the picture from the scene named, and
                                      keep what is before it: for a change near the end of a long film)
  just research-film MSFT --cut long (a second cut of the same ticker: spec MSFT_film_long.json,
                                      built in projects/MSFT/film/long/; voice takes are shared)
  just research-film PTC --dry --stills 3,12,20     (the picture laid out from word counts,
                                                     before the words are approved or voiced)

The spec is the film: its acts (the approved words, the cues, the scenes), the data its scenes
draw, and the source of every figure on screen.

  { "name": "MSFT_film", "format": "wide", "turn": "turn", "acts": [...],
    "script": { act: { "lead", "text", "cues", "scenes" } },     as tools/film/timing.py reads them
    "data": { "scenes": { name: { "kind", "at", ... } } },        what renderer/templates/film.html draws:
                                                                  one entry per scene the acts name; the kinds and
                                                                  what each takes are listed at the top of the page
    "figures": [{ "text": "$364.6B", "source": "Form 10-Q, Note 12 (0001193125-26-436133)" }],
    "voice"?, "music"? }

The figure check runs first and stops the build: every figure the picture shows must be listed
in "figures" with the filing it was read from, and every listed figure must still be on screen.
It cannot check a figure against the filing; it makes sure none reaches the screen unsourced.
Spoken figures are written as words and are not checked here: they are the same figures.

The voice, the music fit, the timeline and the assembly are the film kit's (tools/film/). The
opener is the kit's filing ident (just film-ident), the same footage under every film.
Everything is written under projects/<TICKER>/film/, which is not tracked.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools" / "film"))

VOICE = (
  "EXAVITQu4vr4xnSDxMaL"  # Sarah: one voice for every film (chosen by ear, 2026-11-22)
)
MUSIC = REPO / "assets" / "music" / "brand_film.mp3"
IDENT = REPO / "showcase" / "film_kit" / "ident_wide.mp4"
IDENT_PUSH = (
  190 / 30
)  # the ident's own second at which the camera leaves for the one fact
FIGURE = re.compile(
  r"[+−-]?\$[\d.,]*\d[TBMK]?|[+−-]?\d[\d.,]*%|\b\d{1,3}(?:,\d{3})+\b|\b\d+¢|\b\d[\d.]* years\b"
)


def strings(x):
  if isinstance(x, dict):
    for v in x.values():
      yield from strings(v)
  elif isinstance(x, list):
    for v in x:
      yield from strings(v)
  elif isinstance(x, str):
    yield x


def check_figures(spec):
  shown = set()
  for s in strings(spec["data"]):
    shown.update(FIGURE.findall(s))
  for sc in spec["data"]["scenes"].values():
    if "facts" in sc:
      shown.add(f"{sc['facts']:,}")
  listed = {f["text"]: f.get("source", "") for f in spec.get("figures", [])}
  bad = [f"on screen with no source: {t}" for t in sorted(shown - set(listed))]
  bad += [f"listed but not on screen: {t}" for t in sorted(set(listed) - shown)]
  bad += [f"listed with no source: {t}" for t, src in listed.items() if not src.strip()]
  for t in sorted(shown & set(listed)):
    print(f"  {t:>10}  {listed[t]}")
  if bad:
    sys.exit("figure check failed:\n  " + "\n  ".join(bad))
  print(f"figure check: {len(shown)} figures on screen, each with a source")


def tail_start(argv, old, tl, film):
  """Where a --from render may start: the named scene's first second, if every scene before
  it is timed and drawn as it was in the last build. None means render the whole film."""
  if "--from" not in argv:
    return None
  name = argv[argv.index("--from") + 1]
  names = [s["name"] for s in tl["scenes"]]
  if old is None or name not in names or not (film / "renders" / "layer.mp4").exists():
    print(f"--from {name}: nothing to keep, rendering the whole film")
    return None
  i = names.index(name)
  edge = tl["scenes"][i]["start"]

  def kept(t):  # the scenes before the edge, as timed and as drawn
    return [
      (s["name"], s["start"], s["end"], t["data"]["scenes"][s["name"]])
      for s in t["scenes"][:i]
    ]

  def cues(t):
    return {k: v for k, v in t["cues"].items() if v < edge}

  if len(old["scenes"]) < i or kept(old) != kept(tl) or cues(old) != cues(tl):
    print(f"--from {name}: a scene before it changed, rendering the whole film")
    return None
  return tl["scenes"][i]["frame"] / 30


def main():
  ticker = sys.argv[1].upper()
  home = REPO / "projects" / ticker / "film"
  cut = sys.argv[sys.argv.index("--cut") + 1] if "--cut" in sys.argv else ""
  film = home / cut if cut else home
  spec = json.loads(
    (home / f"{ticker}_film{'_' + cut if cut else ''}.json").read_text()
  )
  check_figures(spec)
  if "--check" in sys.argv:
    return
  if not IDENT.exists():
    sys.exit("the filing ident is not rendered yet: run `just film-ident` once")

  import timing

  plates = {
    name: {
      "file": str(IDENT),
      "holdout": 12,  # the ident's links are bright and thick: a wide cut around the type
      "at": sc["at"]["push"],
      "mark": IDENT_PUSH,
    }
    for name, sc in spec["data"]["scenes"].items()
    if sc["kind"] == "ident"
  }
  before = film / "timeline.json"
  old = json.loads(before.read_text()) if before.exists() else None
  tl = timing.build(
    spec,
    spec["script"],
    film,
    spec.get("voice", VOICE),
    REPO / spec["music"] if spec.get("music") else MUSIC,
    home / "audio",
    plates,
    "--force" in sys.argv,
    dry="--dry" in sys.argv,
  )
  motion = [
    "node",
    "renderer/src/cli.mjs",
    "motion",
    "--root",
    "renderer/templates",
    "--html",
    "renderer/templates/film.html",
    "--width",
    "1920",
    "--height",
    "1080",
    "--mount",
    f"/ds/=design-system,/node_modules/=renderer/node_modules,/film/={film.relative_to(REPO)}",
    "--name",
    "layer",
    "--out",
    str(film / "renders"),
  ]
  if "--stills" in sys.argv or "--dry" in sys.argv:
    if "--stills" in sys.argv:
      motion += ["--stills", sys.argv[sys.argv.index("--stills") + 1]]
    subprocess.run(motion, cwd=REPO, check=True)
    return
  motion += ["--workers", "4"]
  # the ticker's cover is the film's first frame: what a feed shows before the video plays
  cover = [str(c)] if (c := home.parent / "assets" / "yt.png").exists() else []
  start = tail_start(sys.argv, old, tl, film)
  if start is None:
    subprocess.run(motion, cwd=REPO, check=True)
  else:  # the picture before `start` stands: render the rest and join the two
    motion[motion.index("layer")] = "layer_tail"
    subprocess.run([*motion, "--from", str(start)], cwd=REPO, check=True)
    r = film / "renders"
    subprocess.run(
      [
        "ffmpeg", "-v", "error", "-y", "-i", str(r / "layer.mp4"), "-i", str(r / "layer_tail.mp4"),
        "-filter_complex", f"[0:v]trim=end_frame={round(start * 30)},setpts=PTS-STARTPTS[a];[a][1:v]concat=n=2:v=1[v]",
        "-map", "[v]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "12", "-movflags", "+faststart", str(r / "layer_new.mp4"),
      ],
      check=True,
    )  # fmt: skip
    (r / "layer_new.mp4").replace(r / "layer.mp4")
    (r / "layer_tail.mp4").unlink()
  subprocess.run(
    [sys.executable, "tools/film/assemble.py", str(film), *cover], cwd=REPO, check=True
  )
  subprocess.run(
    [
      sys.executable,
      "tools/motion/qa/pop-scan.py",
      str(film / "renders" / f"{tl['name']}.mp4"),
      "--sheet",
      "none",
      "--cuts",
      ",".join(str(s["start"]) for s in tl["scenes"][1:]),
    ],
    cwd=REPO,
  )


if __name__ == "__main__":
  main()
