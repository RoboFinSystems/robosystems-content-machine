"""
The film kit's timing: voice the acts, fit the music, write the timeline the picture is cut to.
Lane-neutral. A lane hands it a spec, its acts and where to write; the brand film
(tools/ad/film.py) and the research film (tools/research_film/build.py) both build on it.

  spec: { "name", "format": "wide" | "tall", "acts": [ids], "turn"?, "turn_cue"?,
          "leads"?: { act: seconds }, "tail"?, "data"? }
  acts: { id: { "lead", "text", "cues": { name: word },
                "scenes": [[name, "act" | "cue", cue, offset]] } }

lead: silence before the take (the music carries it). cues: name -> the word it lands on.
scenes: a scene starts at the act's start, or at a cue, plus the offset, and runs until the
next scene starts. The turn is the act the music's hit lands on: on its first word, or on one
of its cues when the spec names a turn_cue.

Voice: one take per act, cached by voice + act + text, so a new cut of existing acts costs
nothing. Music: the bed has one big hit; it is lengthened by whole bars, or started later, so
the hit lands on the turn, and bars after the hit are repeated when the film outlasts the bed.
"""

import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from align_words import align, norm, tokens_of  # noqa: E402
from generate_voiceover_audio import generate_audio  # noqa: E402

FPS = 30


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


def take(act, text, voice, audio, force=False):
  audio.mkdir(parents=True, exist_ok=True)
  mp3 = audio / f"{voice}_{act}_{hashlib.sha1(text.encode()).hexdigest()[:8]}.mp3"
  if force or not mp3.exists():
    print(f"  voicing {act} (new take)")
    generate_audio(voice, text, str(mp3))
  return mp3


def repeat(y, a, b, sr):
  """The bed with samples a..b played twice, crossfaded at the joins."""
  import numpy as np

  x = int(0.03 * sr)
  fade = np.linspace(0, 1, x)
  head, loop, tail = y[:, :b].copy(), y[:, a:b].copy(), y[:, b:].copy()
  head[:, -x:] *= 1 - fade
  loop[:, :x] *= fade
  loop[:, -x:] *= 1 - fade
  tail[:, :x] *= fade
  return np.concatenate(
    [
      head[:, :-x],
      head[:, -x:] + loop[:, :x],
      loop[:, x:-x],
      loop[:, -x:] + tail[:, :x],
      tail[:, x:],
    ],
    axis=1,
  )


def music_bed(music, turn_natural, out, after=0.0):
  """Fit the bed so its hit falls at or just after the turn, with at least `after` seconds
  of music following the hit. Returns (hit, bed length)."""
  import librosa
  import numpy as np
  import soundfile as sf

  y, sr = librosa.load(str(music), sr=44100, mono=False)
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
  hit0 = hit  # where the hit sits in the bed as recorded
  need = turn_natural - hit
  if need > 0:  # a long film: repeat whole bars of the build
    bars = math.ceil(need / (4 * beat))
    pre = [b for b in bt if b <= hit - 2.0]
    e, s = pre[-1], pre[-1 - 4 * bars]
    a, b = int(s * sr), int(e * sr)
    y = repeat(y, a, b, sr)
    hit += (b - a - int(0.03 * sr)) / sr
    how = f"+{bars} bar(s)"
  else:  # a short film: come in later, on a beat
    # on a beat where the bed has one that early; a bed with a free intro starts where it must
    start = max([b for b in bt if b <= -need] or [-need])
    a = int(start * sr)
    y = y[:, a:].copy()
    x = int(0.5 * sr)
    y[:, :x] *= np.linspace(0, 1, x)
    hit -= start
    how = f"starts {start:.2f}s in"
  # a film that runs long after its turn: repeat whole bars after the hit until it is covered
  post = [b for b in bt - (hit0 - hit) if hit + 1.0 <= b <= y.shape[1] / sr - 8.0]
  added = 0
  while after > y.shape[1] / sr - hit and len(post) > 4:
    bars = min(
      math.ceil((after - (y.shape[1] / sr - hit)) / (4 * beat)), (len(post) - 1) // 4
    )
    y = repeat(y, int(post[-1 - 4 * bars] * sr), int(post[-1] * sr), sr)
    added += bars
  if added:
    how += f", +{added} bar(s) after the hit"
  sf.write(str(out), y.T, sr)
  print(
    f"  music: beat {beat:.3f}s, {how}, hit at {hit:.2f}s, bed {y.shape[1] / sr:.1f}s"
  )
  return hit, y.shape[1] / sr


def build(spec, ACTS, out, voice, music, audio, plates=None, force=False):
  """Voice the spec's acts, fit the bed, and write timeline.json, voice.wav and music.wav
  into `out`. `plates` maps a scene to the footage under it: a path relative to `out`, or
  {"file", "holdout"?} with, for footage that is not rendered to the scene's length,
  {"at": a cue, "mark": the plate's own second that falls on that cue}. Returns the timeline."""
  from faster_whisper import WhisperModel

  name, ids = spec["name"], spec["acts"]
  out.mkdir(parents=True, exist_ok=True)
  leads = {a: spec.get("leads", {}).get(a, ACTS[a]["lead"]) for a in ids}
  tail, turn = spec.get("tail", 3.2), spec.get("turn")

  model = WhisperModel("small.en", compute_type="int8")
  takes = {}
  for a in ids:
    mp3 = take(a, ACTS[a]["text"], voice, audio, force)
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
    at = starts[turn] + first
    hit, _ = music_bed(music, at, out / "music.wav", total - at - 1.0)
    starts, total = layout(max(0.0, hit - at))
  else:
    music_bed(music, 0.0, out / "music.wav")
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
    p = (plates or {}).get(scene)
    if p:
      p = dict(p) if isinstance(p, dict) else {"file": p}
      if (
        "at" in p
      ):  # skip into the plate, or hold its first frame, so its mark meets the cue
        p["skip"] = round(p.pop("mark") - (cues[p.pop("at")] - s), 3)
      scenes[-1]["plate"] = p

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
  if "data" in spec:  # handed to the type layer untouched
    tl["data"] = spec["data"]
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

  return tl
