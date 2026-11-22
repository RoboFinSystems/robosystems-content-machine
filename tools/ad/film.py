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

Voice: one take per act, cached by voice + act + text (audio/), so a new cut of existing
acts costs nothing. Music: the bed has one big hit; it is lengthened by whole bars, or
started later on a beat, so the hit lands on the turn.

Writes showcase/robosystems_ad/films/<name>/timeline.json (acts, cues, scenes, format),
voice.wav and music.wav. Nothing it writes is tracked.

  UV_ENV_FILE=.env uv run --with faster-whisper --with 'av<16' --with librosa --with soundfile \
      python tools/ad/film.py tools/ad/films/main.json
"""

import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WORK = (
  REPO / "showcase" / "robosystems_ad"
)  # gitignored: takes, timelines, plates, renders
sys.path.insert(0, str(REPO / "tools"))
from align_words import align, norm, tokens_of  # noqa: E402
from generate_voiceover_audio import generate_audio  # noqa: E402

VOICE = "EXAVITQu4vr4xnSDxMaL"  # Sarah (premade), chosen by ear against the music bed.
MUSIC = (
  REPO / "assets" / "music" / "brand_film.mp3"
)  # ElevenLabs Music, generated for this film; one big hit
FPS = 30

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


def dur(p):
  return float(
    subprocess.check_output(
      [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "csv=p=0",
        str(p),
      ]
    )
  )


def take(act, force=False):
  text = ACTS[act]["text"]
  (WORK / "audio").mkdir(parents=True, exist_ok=True)
  mp3 = (
    WORK / "audio" / f"{VOICE}_{act}_{hashlib.sha1(text.encode()).hexdigest()[:8]}.mp3"
  )
  if force or not mp3.exists():
    print(f"  voicing {act} (new take)")
    generate_audio(VOICE, text, str(mp3))
  return mp3


def music_bed(turn_natural, out):
  """Fit the bed so its hit falls at or just after the turn. Returns (hit, bed length)."""
  import librosa
  import numpy as np
  import soundfile as sf

  y, sr = librosa.load(str(MUSIC), sr=44100, mono=False)
  mono = librosa.to_mono(y)
  hop = 512
  rms = librosa.feature.rms(y=mono, frame_length=4096, hop_length=hop)[0]
  t = librosa.times_like(rms, sr=sr, hop_length=hop)
  win = int(1.0 * sr / hop)
  jump = [
    np.mean(rms[i : i + win]) / (np.mean(rms[i - win : i]) + 1e-9)
    if win <= i < len(rms) - win and t[i] > 20
    else 0
    for i in range(len(rms))
  ]
  hit = float(t[int(np.argmax(jump))])
  _, beats = librosa.beat.beat_track(y=mono, sr=sr, hop_length=hop)
  bt = librosa.frames_to_time(beats, sr=sr, hop_length=hop)
  beat = float(np.median(np.diff(bt)))
  need = turn_natural - hit
  if need > 0:  # a long film: repeat whole bars of the build
    bars = math.ceil(need / (4 * beat))
    pre = [b for b in bt if b <= hit - 2.0]
    e, s = pre[-1], pre[-1 - 4 * bars]
    a, b = int(s * sr), int(e * sr)
    x = int(0.03 * sr)
    fade = np.linspace(0, 1, x)
    head, loop, tail = y[:, :b].copy(), y[:, a:b].copy(), y[:, b:].copy()
    head[:, -x:] *= 1 - fade
    loop[:, :x] *= fade
    loop[:, -x:] *= 1 - fade
    tail[:, :x] *= fade
    y = np.concatenate(
      [
        head[:, :-x],
        head[:, -x:] + loop[:, :x],
        loop[:, x:-x],
        loop[:, -x:] + tail[:, :x],
        tail[:, x:],
      ],
      axis=1,
    )
    hit += (b - a - x) / sr
    how = f"+{bars} bar(s)"
  else:  # a short film: come in later, on a beat
    start = max([b for b in bt if b <= -need] or [0.0])
    a = int(start * sr)
    y = y[:, a:].copy()
    x = int(0.5 * sr)
    y[:, :x] *= np.linspace(0, 1, x)
    hit -= start
    how = f"starts {start:.2f}s in"
  sf.write(str(out), y.T, sr)
  print(
    f"  music: beat {beat:.3f}s, {how}, hit at {hit:.2f}s, bed {y.shape[1] / sr:.1f}s"
  )
  return hit, y.shape[1] / sr


def main():
  from faster_whisper import WhisperModel

  spec = json.loads(Path(sys.argv[1]).read_text())
  name, ids = spec["name"], spec["acts"]
  out = WORK / "films" / name
  out.mkdir(parents=True, exist_ok=True)
  leads = {a: spec.get("leads", {}).get(a, ACTS[a]["lead"]) for a in ids}
  tail, turn = spec.get("tail", 3.2), spec.get("turn")

  model = WhisperModel("small.en", compute_type="int8")
  takes = {}
  for a in ids:
    mp3 = take(a, "--force" in sys.argv)
    d = dur(mp3)
    segs, _ = model.transcribe(str(mp3), word_timestamps=True)
    heard = [(w.word, w.start) for s in segs for w in s.words]
    takes[a] = (
      mp3,
      d,
      [(norm(w), tm) for w, tm in align(tokens_of(ACTS[a]["text"]), heard, d)],
    )

  def layout(extra=0.0):
    t, st = 0.0, {}
    for a in ids:
      t += leads[a] + (extra if a == turn else 0)
      st[a] = t
      t += takes[a][1]
    return st, t + tail

  starts, total = layout()
  hit = None
  if turn:
    first = takes[turn][2][0][1]
    if spec.get("turn_cue"):
      word = ACTS[turn]["cues"][spec["turn_cue"]]
      first = next(tm for w, tm in takes[turn][2] if w == word)
    hit, _ = music_bed(starts[turn] + first, out / "music.wav")
    starts, total = layout(max(0.0, hit - (starts[turn] + first)))
  else:
    music_bed(0.0, out / "music.wav")
  total = round(total, 2)

  cues = {}
  for a in ids:
    for cue, word in ACTS[a]["cues"].items():
      cues[cue] = round(starts[a] + next(tm for w, tm in takes[a][2] if w == word), 3)
  acts = {a: [round(starts[a], 3), round(starts[a] + takes[a][1], 3)] for a in ids}

  # scenes: each starts where its act says and runs to the next; the first owns the opening
  marks = []
  for a in ids:
    for scene, kind, cue, off in ACTS[a]["scenes"]:
      marks.append([scene, (cues[cue] if kind == "cue" else starts[a]) + off])
  marks[0][1] = 0.0
  scenes = []
  for i, (scene, s) in enumerate(marks):
    e = marks[i + 1][1] if i + 1 < len(marks) else total
    f0, f1 = math.ceil(s * FPS - 1e-6), math.ceil(e * FPS - 1e-6)
    scenes.append(
      {
        "name": scene,
        "start": round(s, 3),
        "end": round(e, 3),
        "frame": f0,
        "frames": f1 - f0,
      }
    )

  tl = {
    "name": name,
    "format": spec.get("format", "wide"),
    "fps": FPS,
    "total": total,
    "hit": hit and round(hit, 3),
    "acts": acts,
    "cues": cues,
    "scenes": scenes,
  }
  (out / "timeline.json").write_text(json.dumps(tl, indent=2))

  inputs = [x for a in ids for x in ("-i", str(takes[a][0]))]
  fc = ";".join(
    f"[{i}:a]adelay={int(starts[a] * 1000)}:all=1[a{i}]" for i, a in enumerate(ids)
  )
  fc += (
    ";"
    + "".join(f"[a{i}]" for i in range(len(ids)))
    + f"amix=inputs={len(ids)}:normalize=0,apad=whole_dur={total}[vo]"
  )
  subprocess.run(
    [
      "ffmpeg",
      "-v",
      "error",
      "-y",
      *inputs,
      "-filter_complex",
      fc,
      "-map",
      "[vo]",
      "-ar",
      "48000",
      "-ac",
      "2",
      str(out / "voice.wav"),
    ],
    check=True,
  )
  for s in scenes:
    print(
      f"  {s['name']:8s} {s['start']:6.2f} -> {s['end']:6.2f}  ({s['frames']} frames)"
    )
  print(
    f"{name} ({tl['format']}): {total}s"
    + (
      f"; the turn at {cues.get(spec.get('turn_cue')) or acts[turn][0]}s, the hit at {hit:.2f}s"
      if turn
      else ""
    )
  )


if __name__ == "__main__":
  main()
