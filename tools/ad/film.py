"""
One core, many films. A film is a spec (tools/ad/films/<name>.json): which acts, in what order, in
what frame shape. This builds everything the picture is cut to.

  { "name": "main", "format": "wide" | "tall", "acts": ["problem", "reveal", ...],
    "turn": "yours", "turn_cue": "trains", "leads": { "reveal": 0.9 }, "tail": 3.2 }

The turn is the act the music's hit lands on: on its first word, or on one of its cues
when the spec names a turn_cue.

An act is a unit of the script: its words, the cues inside it (the word each build lands
on) and the scenes it puts on screen. Acts live here, in ACTS, so every film says the
approved words the same way; a variant with new words adds a new act.

The timing itself (takes, word alignment, the music fit, the timeline) is the film kit's,
tools/film/timing.py, shared with every lane built on the film's form. This file holds the
brand film's own: its approved words, its voice, its bed and its plates.

Writes showcase/robosystems_ad/films/<name>/timeline.json (acts, cues, scenes, format),
voice.wav and music.wav. Nothing it writes is tracked.

  UV_ENV_FILE=.env uv run --with faster-whisper --with 'av<16' --with librosa --with soundfile \
      python tools/ad/film.py tools/ad/films/main.json
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WORK = (
  REPO / "showcase" / "robosystems_ad"
)  # gitignored: takes, timelines, plates, renders
sys.path.insert(0, str(REPO / "tools" / "film"))
import timing  # noqa: E402

VOICE = "EXAVITQu4vr4xnSDxMaL"  # Sarah (premade), chosen by ear against the music bed.
MUSIC = (
  REPO / "assets" / "music" / "brand_film.mp3"
)  # ElevenLabs Music, generated for this film; one big hit
PLATES = {  # scene -> the Blender shot under it; trace is cut back around its labels
  "reveal": "plates/graph_hero.mp4",
  "trace": {"file": "plates/trace.mp4", "holdout": True},
  "share": "plates/share.mp4",
}

# lead: silence before the take (the music carries it). cues: name -> the word it lands on.
# scenes: [name, "act" | "cue", cue name, offset]: the scene starts at the act's start, or at
# a cue, plus the offset, and runs until the next scene starts.
ACTS = {
  "problem": {
    "lead": 1.0,
    "text": "Every company runs on its numbers. But hand them to an AI, and they get hard to trace. And harder to trust.",
    "cues": {"hand": "hand", "trace": "trace", "harder": "harder"},
    "scenes": [["field", "act", None, -1.0], ["problem", "cue", "hand", -0.15]],
  },
  "reveal": {
    "lead": 1.7,
    "text": "Meet RoboSystems. The open-source knowledge graph for finance.",
    "cues": {"meet": "meet", "name": "robosystems", "category": "the"},
    "scenes": [["reveal", "act", None, -0.75]],
  },
  "how": {
    "lead": 1.5,
    "text": "Your company's event ledger. Reports from it. Benchmarkable against public filings, in the same ontology. Every number opens to the entries behind it. And your AI reads it all, from Claude, ChatGPT, or any MCP client.",
    "cues": {
      "ledger": "your",
      "reports": "reports",
      "bench": "benchmarkable",
      "same": "in",
      "every": "every",
      "entries": "entries",
      "reads": "and",
      "claude": "claude",
      "chatgpt": "chatgpt",
      "mcp": "any",
    },
    "scenes": [["what", "act", None, -0.45], ["trace", "cue", "every", -0.35]],
  },
  "share": {
    "lead": 1.3,
    "text": "Publish a report, and share it. It lands in your investor's graph: the statements, never the ledger. Every company they hold, on one model.",
    "cues": {
      "publish": "publish",
      "shareit": "share",
      "lands": "lands",
      "statements": "statements",
      "hold": "every",
      "onemodel": "on",
    },
    "scenes": [["share", "act", None, -0.5]],
  },
  "yours": {
    "lead": 1.2,
    "text": "And it's yours. The code. The data. The deployment. On your infrastructure. With the model you choose. Your data trains no one's model.",
    "cues": {
      "yours": "and",
      "code": "code",
      "data": "data",
      "deployment": "deployment",
      "infra": "on",
      "model": "with",
      "trains": "trains",
    },
    "scenes": [["yours", "act", None, -0.55], ["props", "cue", "infra", -0.3]],
  },
  "end": {
    "lead": 1.8,
    "text": "RoboSystems. The open-source knowledge graph for finance.",
    "cues": {"endname": "robosystems", "endline": "the"},
    "scenes": [["end", "act", None, -0.6]],
  },
}


def main():
  spec = json.loads(Path(sys.argv[1]).read_text())
  timing.build(
    spec,
    ACTS,
    WORK / "films" / spec["name"],
    VOICE,
    MUSIC,
    WORK / "audio",
    PLATES,
    "--force" in sys.argv,
  )


if __name__ == "__main__":
  main()
