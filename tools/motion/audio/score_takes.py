#!/usr/bin/env python3
"""score_takes.py: rank voiceover takes with listening proxies, not by reading the text.

The principle: a take is chosen by ear, but ears tire and a long list of takes blurs together. These
measurements shortlist the takes worth listening to, and catch the ones that misread the script.

For every take this measures:
  - words and timings (faster-whisper, word timestamps) and word accuracy against the script;
  - dimensional emotion (audeering wav2vec2 MSP-Podcast model): arousal, dominance, valence, 0..1;
  - pitch range in semitones (5th to 95th percentile of f0) and loudness variation: low numbers
    mean a flat, monotone read;
  - pace (words per second) and the real pauses, measured from the audio (silences of 200 ms or
    more). Whisper's word times are not used for this: it hangs pauses on the next word's start.

Then it ranks the takes of each act: word-perfect takes first, then by closeness to an optional
emotion target, then by expressiveness. The ranking is a shortlist. Listen to the top two.

Usage:
  python3 score_takes.py takes/takes.json [--out scores.json] [--lines lines.json]
                         [--whisper small.en] [--device cpu] [--no-emotion]
  python3 score_takes.py --wav a.wav b.wav --text "The script these takes read." [--out scores.json]

takes.json is the index written by tts-cartesia.ts: [{file, act, take, text, emotion, speed}].
File paths are resolved relative to the index file.

Phonetic spellings: if the script spells a name the way it should be said ("Acme ly"), map it to
how the transcriber writes it with --alias "Acme ly=Acmely" or an "aliases" object in lines.json,
so the take is not marked wrong for saying the name correctly.

Emotion targets (optional) come from lines.json: an act may carry
  "target": {"arousal": 0.35, "valence": 0.25}
meaning "lower energy, negative". The model's scale is relative: calibrate by scoring a few takes
you like and copying their numbers. Without targets, takes rank by accuracy then expressiveness.

Requirements:
  pip install faster-whisper librosa soundfile numpy torch transformers
The emotion model (about 1.2 GB) downloads from Hugging Face on first run. --no-emotion skips it.
"""

import argparse
import difflib
import json
import os
import re
import sys

import librosa
import numpy as np

EMOTION_MODEL = "audeering/wav2vec2-large-robust-12-ft-emotion-msp-dim"
SR = 16000

NUMBER_WORDS = {
  "zero": "0",
  "one": "1",
  "two": "2",
  "three": "3",
  "four": "4",
  "five": "5",
  "six": "6",
  "seven": "7",
  "eight": "8",
  "nine": "9",
  "ten": "10",
  "eleven": "11",
  "twelve": "12",
  "thirteen": "13",
  "fourteen": "14",
  "fifteen": "15",
  "sixteen": "16",
  "seventeen": "17",
  "eighteen": "18",
  "nineteen": "19",
  "twenty": "20",
  "thirty": "30",
  "forty": "40",
  "fifty": "50",
  "sixty": "60",
  "seventy": "70",
  "eighty": "80",
  "ninety": "90",
}
SCALE_WORDS = {"hundred", "thousand", "million", "billion"}


def norm_tokens(text):
  """Lowercase word tokens without punctuation, markup tags or hyphens. Spelled-out numbers
  collapse to one token 'N' and digits to 'N', so "two hundred" and "200" compare equal."""
  s = re.sub(r"<[^>]+>", " ", text.lower()).replace("-", " ")
  s = re.sub(r"[^a-z0-9' ]", " ", s).replace("'", "")
  raw = s.split()
  toks = []
  for i, w in enumerate(raw):
    a_scale = w == "a" and i + 1 < len(raw) and raw[i + 1] in SCALE_WORDS  # "a hundred"
    toks.append(
      "N" if (w.isdigit() or w in NUMBER_WORDS or w in SCALE_WORDS or a_scale) else w
    )
  out = []
  for i, w in enumerate(toks):
    # "one hundred and forty eight" -> N: drop 'and' between number words, then merge runs of N
    if (
      w == "and" and out and out[-1] == "N" and i + 1 < len(toks) and toks[i + 1] == "N"
    ):
      continue
    if w == "N" and out and out[-1] == "N":
      continue
    out.append(w)
  return out


def word_accuracy(script, heard, aliases=None):
  """Symmetric word accuracy in 0..1 plus the differing spans. aliases maps a phonetic spelling
  used in the script ("Acme ly") to what the transcriber writes ("Acmely")."""
  a, b = norm_tokens(script), norm_tokens(heard)
  for spoken, written in (aliases or {}).items():
    canon = "".join(norm_tokens(written))
    forms = {" ".join(norm_tokens(spoken)), " ".join(norm_tokens(written))}
    for form in forms:
      a = f" {' '.join(a)} ".replace(f" {form} ", f" {canon} ").split()
      b = f" {' '.join(b)} ".replace(f" {form} ", f" {canon} ").split()
  if not a:
    return 1.0, []
  sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
  matched = sum(m.size for m in sm.get_matching_blocks())
  errors = []
  for op, i1, i2, j1, j2 in sm.get_opcodes():
    if op != "equal":
      errors.append(
        {"op": op, "script": " ".join(a[i1:i2]), "heard": " ".join(b[j1:j2])}
      )
  # symmetric: extra words count against the take too
  return round(2 * matched / (len(a) + len(b)), 3), errors


class EmotionModel:
  def __init__(self, device):
    import torch
    import torch.nn as nn
    from transformers import Wav2Vec2Processor
    from transformers.models.wav2vec2.modeling_wav2vec2 import (
      Wav2Vec2Model,
      Wav2Vec2PreTrainedModel,
    )

    class Head(nn.Module):
      def __init__(self, c):
        super().__init__()
        self.dense = nn.Linear(c.hidden_size, c.hidden_size)
        self.dropout = nn.Dropout(c.final_dropout)
        self.out_proj = nn.Linear(c.hidden_size, c.num_labels)

      def forward(self, x):
        return self.out_proj(self.dropout(torch.tanh(self.dense(self.dropout(x)))))

    class Emo(Wav2Vec2PreTrainedModel):
      def __init__(self, c):
        super().__init__(c)
        self.wav2vec2 = Wav2Vec2Model(c)
        self.classifier = Head(c)
        self.init_weights()

      def forward(self, v):
        return self.classifier(self.wav2vec2(v)[0].mean(1))

    self.torch = torch
    self.device = device
    self.proc = Wav2Vec2Processor.from_pretrained(EMOTION_MODEL)
    self.model = Emo.from_pretrained(EMOTION_MODEL).to(device).eval()

  def __call__(self, y):
    with self.torch.no_grad():
      x = self.torch.tensor(self.proc(y, sampling_rate=SR).input_values[0])[None].to(
        self.device
      )
      arousal, dominance, valence = self.model(x)[0].tolist()
    return arousal, dominance, valence


def pauses(y, words, min_pause=0.2, quiet_db=-50.0):
  """Silent stretches (below quiet_db) of at least min_pause seconds between the first and last word.
  Measured from the audio, not from whisper's word times: whisper attaches most of a pause to the
  start of the next word, and its end times run early. Pauses are where a take can be split."""
  hop = int(0.005 * SR)
  rms = librosa.feature.rms(
    y=y, frame_length=int(0.02 * SR), hop_length=hop, center=True
  )[0]
  quiet = 20 * np.log10(rms + 1e-9) < quiet_db
  if not words:
    return []
  t0, t1 = words[0][1], words[-1][2]
  out, start = [], None
  for i, q in enumerate(np.r_[quiet, False]):
    if q and start is None:
      start = i
    elif not q and start is not None:
      a, b = start * hop / SR, i * hop / SR
      if b - a >= min_pause and a > t0 and b < t1 + 0.3:
        out.append([round(a, 3), round(b, 3)])
      start = None
  return out


def measure(path, script, whisper, emo, aliases=None):
  y, _ = librosa.load(path, sr=SR, mono=True)
  segs, _ = whisper.transcribe(path, word_timestamps=True, language="en", beam_size=5)
  words = [
    (w.word.strip(), round(w.start, 3), round(w.end, 3)) for s in segs for w in s.words
  ]
  heard = " ".join(w[0] for w in words)
  acc, errors = word_accuracy(script, heard, aliases)
  f0, _, _ = librosa.pyin(y, fmin=60, fmax=400, sr=SR)
  f0 = f0[~np.isnan(f0)]
  pitch_range = (
    float(12 * np.log2(np.percentile(f0, 95) / np.percentile(f0, 5)))
    if len(f0) > 10
    else 0.0
  )
  rms = librosa.feature.rms(y=y)[0]
  loud_var = (
    float(np.std(20 * np.log10(rms[rms > 1e-3]))) if np.any(rms > 1e-3) else 0.0
  )
  speech_dur = (words[-1][2] - words[0][1]) if words else 0.0
  r = {
    "heard": heard,
    "accuracy": acc,
    "exact": acc == 1.0,
    "errors": errors,
    "pitch_range_st": round(pitch_range, 1),
    "loud_var_db": round(loud_var, 2),
    "dur": round(len(y) / SR, 3),
    "words_per_sec": round(len(words) / speech_dur, 2) if speech_dur > 0 else 0.0,
    "pauses": pauses(y, words),
    "words": [list(w) for w in words],
  }
  if emo is not None:
    a, d, v = emo(y)
    r.update(arousal=round(a, 3), dominance=round(d, 3), valence=round(v, 3))
  return r


def rank_key(t, target):
  """Sort key, lower is better: accuracy gate, emotion distance, then expressiveness."""
  dist = 0.0
  if target and "arousal" in t:
    dist = float(
      np.sqrt(
        sum(
          (t[k] - target[k]) ** 2
          for k in ("arousal", "valence", "dominance")
          if k in target
        )
      )
    )
  return (-t["accuracy"], round(dist, 2), -t["pitch_range_st"])


def main():
  ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
  ap.add_argument("index", nargs="?", help="takes.json from tts-cartesia.ts")
  ap.add_argument("--wav", nargs="*", help="score these files instead of an index")
  ap.add_argument("--text", help="script text for --wav files")
  ap.add_argument("--lines", help='lines.json with optional per-act "target" emotion')
  ap.add_argument("--out", default="scores.json")
  ap.add_argument(
    "--whisper",
    default="small.en",
    help="faster-whisper model size (small.en is a good default)",
  )
  ap.add_argument("--device", default="cpu")
  ap.add_argument("--no-emotion", action="store_true", help="skip the emotion model")
  ap.add_argument(
    "--alias",
    action="append",
    default=[],
    metavar="SPOKEN=WRITTEN",
    help='phonetic spelling in the script and how the transcriber writes it, e.g. "Acme ly=Acmely"',
  )
  args = ap.parse_args()

  if args.wav:
    if not args.text:
      ap.error("--wav needs --text")
    takes = [
      {"file": os.path.abspath(p), "act": "take", "take": i + 1, "text": args.text}
      for i, p in enumerate(args.wav)
    ]
  elif args.index:
    base = os.path.dirname(os.path.abspath(args.index))
    takes = json.load(open(args.index))
    for t in takes:
      t["file"] = (
        os.path.join(base, t["file"]) if not os.path.isabs(t["file"]) else t["file"]
      )
      t.setdefault("act", t.get("line", "take"))
  else:
    ap.error("pass takes.json or --wav")

  targets = {}
  aliases = dict(a.split("=", 1) for a in args.alias)
  if args.lines:
    spec = json.load(open(args.lines))
    acts = spec if isinstance(spec, list) else spec.get("acts", [])
    targets = {a["id"]: a["target"] for a in acts if "target" in a}
    if isinstance(spec, dict):
      aliases = {**spec.get("aliases", {}), **aliases}

  from faster_whisper import WhisperModel

  whisper = WhisperModel(args.whisper, device=args.device, compute_type="int8")
  emo = None if args.no_emotion else EmotionModel(args.device)

  results = []
  for t in takes:
    r = {**t, **measure(t["file"], t["text"], whisper, emo, aliases)}
    results.append(r)
    emo_s = (
      f"A{r['arousal']:.2f} D{r['dominance']:.2f} V{r['valence']:.2f} "
      if "arousal" in r
      else ""
    )
    flag = "OK " if r["exact"] else f"{r['accuracy']:.2f}"
    gaps = f" pauses:{len(r['pauses'])}"
    print(
      f"{os.path.basename(t['file']):24} {str(t.get('emotion') or ''):13} {emo_s}pr{r['pitch_range_st']:4.1f} "
      f"{r['words_per_sec']:.1f}w/s {flag}{gaps}  {r['heard']}",
      flush=True,
    )

  ranking = {}
  for act in dict.fromkeys(r["act"] for r in results):
    group = sorted(
      [r for r in results if r["act"] == act],
      key=lambda r: rank_key(r, targets.get(act)),
    )
    ranking[act] = [os.path.basename(r["file"]) for r in group]
  json.dump({"ranking": ranking, "takes": results}, open(args.out, "w"), indent=1)
  print("\nshortlist (listen to the top two of each):")
  for act, files in ranking.items():
    print(f"  {act}: " + " > ".join(files))
  print("wrote", args.out)


if __name__ == "__main__":
  sys.exit(main())
