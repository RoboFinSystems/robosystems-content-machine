"""
Build one research film: a 60 to 90 second cut of a published brief, in the brand film's form.

  just research-film MSFT            (spec: projects/MSFT/film/MSFT_film.json)
  just research-film MSFT --check    (the figure check only: no voice, no render)
  just research-film MSFT --stills 4,20,41
  just research-film PTC --dry --stills 3,12,20     (the picture laid out from word counts,
                                                     before the words are approved or voiced)

The spec is the film: its acts (the approved words, the cues, the scenes), the data its scenes
draw, and the source of every figure on screen.

  { "name": "MSFT_film", "format": "wide", "turn": "turn", "acts": [...],
    "script": { act: { "lead", "text", "cues", "scenes" } },     as tools/film/timing.py reads them
    "data": { "scenes": { name: { "kind", "at", ... } } },        what renderer/templates/research_film.html draws:
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

VOICE = "EXAVITQu4vr4xnSDxMaL"  # Sarah, the brand film's voice, until a research voice is chosen by ear
MUSIC = REPO / "assets" / "music" / "brand_film.mp3"
IDENT = REPO / "showcase" / "film_kit" / "ident_wide.mp4"
IDENT_PUSH = (
  190 / 30
)  # the ident's own second at which the camera leaves for the one fact
FIGURE = re.compile(r"\$[\d.,]*\d[BMK]?|[+−-]?\d[\d.,]*%|\b\d{1,3}(?:,\d{3})+\b")


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


def main():
  ticker = sys.argv[1].upper()
  film = REPO / "projects" / ticker / "film"
  spec = json.loads((film / f"{ticker}_film.json").read_text())
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
  tl = timing.build(
    spec,
    spec["script"],
    film,
    spec.get("voice", VOICE),
    REPO / spec["music"] if spec.get("music") else MUSIC,
    film / "audio",
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
    "renderer/templates/research_film.html",
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
  subprocess.run(motion, cwd=REPO, check=True)
  subprocess.run(
    [sys.executable, "tools/film/assemble.py", str(film)], cwd=REPO, check=True
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
