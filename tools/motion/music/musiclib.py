"""musiclib.py: shared helpers for the music scripts (join_on_downbeats.py, cue_sheet.py).

Beat and downbeat tracking, per-beat harmonic and rhythmic fingerprints, drum-transient alignment
and an equal-power crossfade. Nothing here time-stretches or pitch-shifts: a music edit that keeps
the one-performance feel only ever moves whole bars and lines their drum hits up.

Requirements: numpy, scipy, soundfile, librosa, and ffmpeg on PATH for compressed formats.
"""

import os
import subprocess

import librosa
import numpy as np
import soundfile as sf

AN_SR = 22050  # analysis rate
HOP = 256  # analysis hop: 11.6 ms at 22.05 kHz
NATIVE = {".wav", ".flac", ".aiff", ".aif", ".ogg"}


def load_audio(path, sr=None):
  """Decode to float32 [channels, samples]. WAV/FLAC/OGG are read directly; anything else (m4a, mp3)
  goes through ffmpeg. When sr is given and differs, ffmpeg resamples with the SoX resampler."""
  ext = os.path.splitext(path)[1].lower()
  if ext in NATIVE:
    info = sf.info(path)
    if sr is None or info.samplerate == sr:
      y, rate = sf.read(path, always_2d=True, dtype="float32")
      return y.T.copy(), rate
  probe = (
    subprocess.run(
      [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=sample_rate,channels",
        "-of",
        "csv=p=0",
        path,
      ],
      check=True,
      capture_output=True,
      text=True,
    )
    .stdout.strip()
    .split(",")
  )
  ch = min(int(probe[1]), 2)
  if sr is None:
    sr = int(probe[0])
  cmd = [
    "ffmpeg",
    "-v",
    "error",
    "-i",
    path,
    "-af",
    "aresample=resampler=soxr:precision=28",
    "-ar",
    str(sr),
    "-ac",
    str(ch),
    "-f",
    "f32le",
    "-",
  ]
  raw = subprocess.run(cmd, check=True, capture_output=True).stdout
  y = np.frombuffer(raw, dtype=np.float32).reshape(-1, ch).T.copy()
  return y, sr


def to_mono(y):
  return y.mean(0) if y.ndim == 2 else y


def match_channels(y, ch):
  if y.shape[0] == ch:
    return y
  if y.shape[0] == 1:
    return np.repeat(y, ch, axis=0)
  return np.repeat(y.mean(0, keepdims=True), ch, axis=0)


def _unit(v, axis=-1):
  return v / (np.linalg.norm(v, axis=axis, keepdims=True) + 1e-9)


def analyse(y, sr, bpb=4, start_bpm=None, first_downbeat=None):
  """Beat grid and per-beat fingerprints of one recording.

  Returns a dict with:
    beats      beat times (s), extended to cover the whole file at the tracked period
    tempo      BPM,  period  median beat length (s)
    phase      index of the first downbeat in beats (beats[phase::bpb] are downbeats)
    downbeats  downbeat times (s)
    chroma     per-beat pitch-class profile (unit length), shape [n_beats, 12]
    bass       per-beat bass pitch-class profile C1..B3 (unit length), [n_beats, 12]
    rhythm     per-beat onset pattern in 4 sixteenth slots, [n_beats, 4]
    rms_db     per-beat level in dBFS
  first_downbeat (s) overrides the automatic downbeat choice with any known downbeat time.
  """
  m = librosa.resample(to_mono(y).astype(np.float32), orig_sr=sr, target_sr=AN_SR)
  dur = len(m) / AN_SR
  oenv = librosa.onset.onset_strength(y=m, sr=AN_SR, hop_length=HOP)
  kw = dict(
    onset_envelope=oenv,
    sr=AN_SR,
    hop_length=HOP,
    tightness=400,
    units="time",
    trim=False,
  )
  if start_bpm:
    kw["start_bpm"] = start_bpm
  tempo, beats = librosa.beat.beat_track(**kw)
  tempo = float(np.atleast_1d(tempo)[0])
  if len(beats) < 2 * bpb:
    raise ValueError("too few beats tracked: is this music with a steady pulse?")
  period = float(np.median(np.diff(beats)))
  # extend the grid to the file edges so the first and last bars are addressable
  head = np.arange(beats[0] - period, -period * 0.25, -period)[::-1]
  tail = np.arange(beats[-1] + period, dur - period * 0.25, period)
  beats = np.r_[head, beats, tail]
  beats = beats[beats >= 0]

  # one analysis frame per beat, strictly increasing, so per-beat segments are [beat i, beat i+1)
  frames = np.minimum(
    librosa.time_to_frames(beats, sr=AN_SR, hop_length=HOP), len(oenv) - 2
  )
  keep = np.r_[True, np.diff(frames) > 0]
  beats, frames = beats[keep], frames[keep]
  # downbeat phase: bar lines carry the kick and the chord changes
  low = librosa.onset.onset_strength(y=m, sr=AN_SR, hop_length=HOP, fmax=160, n_mels=32)
  C = librosa.feature.chroma_cqt(
    y=m, sr=AN_SR, hop_length=HOP, fmin=librosa.note_to_hz("C2"), n_octaves=6
  )
  cb = librosa.util.sync(C, np.r_[frames, C.shape[1]], aggregate=np.median, pad=False).T
  cb = _unit(cb)
  change = np.r_[0.0, 1 - np.sum(cb[1:] * cb[:-1], axis=1)]
  kick = np.array(
    [low[max(0, f - 2) : f + 3].max() for f in np.minimum(frames, len(low) - 1)]
  )
  kick = kick / (kick.max() + 1e-9)
  change = change / (change.max() + 1e-9)
  if first_downbeat is not None:
    phase = int(np.argmin(np.abs(beats - first_downbeat))) % bpb
    confidence = None
  else:
    scores = [float(kick[p::bpb].mean() + change[p::bpb].mean()) for p in range(bpb)]
    phase = int(np.argmax(scores))
    srt = sorted(scores)
    confidence = round((srt[-1] - srt[-2]) / (srt[-1] + 1e-9), 3)

  # bass pitch classes from a constant-Q transform C1..B3
  Q = np.abs(
    librosa.cqt(m, sr=AN_SR, hop_length=HOP, fmin=librosa.note_to_hz("C1"), n_bins=36)
  )
  qb = librosa.util.sync(Q, np.r_[frames, Q.shape[1]], aggregate=np.mean, pad=False)
  bass = _unit(np.stack([qb[k::12].sum(0) for k in range(12)], axis=1))

  rhythm = np.zeros((len(beats), 4))
  for i, b in enumerate(beats):
    for s in range(4):
      f = librosa.time_to_frames(b + s * period / 4, sr=AN_SR, hop_length=HOP)
      if f < len(oenv):
        rhythm[i, s] = oenv[max(0, f - 1) : f + 2].max()
  rms = librosa.feature.rms(y=m, hop_length=HOP)[0]
  rb = librosa.util.sync(
    rms[None], np.r_[frames, len(rms)], aggregate=np.mean, pad=False
  )[0]
  return {
    "beats": beats,
    "tempo": tempo,
    "period": period,
    "phase": phase,
    "phase_confidence": confidence,
    "downbeats": beats[phase::bpb],
    "bpb": bpb,
    "duration": dur,
    "chroma": cb,
    "bass": bass,
    "rhythm": rhythm,
    "rms_db": 20 * np.log10(rb + 1e-9),
  }


def is_downbeat(an, i):
  return i >= 0 and (i - an["phase"]) % an["bpb"] == 0


def _cos(a, b):
  a, b = a.ravel(), b.ravel()
  return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def _corr(a, b):
  a, b = a.ravel() - a.mean(), b.ravel() - b.mean()
  return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def context_similarity(A, i, B, j, n):
  """How alike two join points sound: the n beats before beat i of A against the n beats before
  beat j of B, and likewise the n beats after, where both exist. Harmony (chroma), bass line and
  drum pattern are compared separately; total = 0.45 chroma + 0.35 bass + 0.2 rhythm."""
  parts = []
  for side in ("before", "after"):
    if side == "before":
      k = min(n, i, j)
      sa, sb = slice(i - k, i), slice(j - k, j)
    else:
      k = min(n, len(A["beats"]) - i, len(B["beats"]) - j)
      sa, sb = slice(i, i + k), slice(j, j + k)
    if k < max(1, n // 2):
      continue
    parts.append(
      (
        k,
        _cos(A["chroma"][sa], B["chroma"][sb]),
        _cos(A["bass"][sa], B["bass"][sb]),
        _corr(A["rhythm"][sa], B["rhythm"][sb]),
      )
    )
  if not parts:
    return None
  w = np.array([p[0] for p in parts], dtype=float)
  chroma = float(np.average([p[1] for p in parts], weights=w))
  bass = float(np.average([p[2] for p in parts], weights=w))
  rhythm = float(np.average([p[3] for p in parts], weights=w))
  return {
    "chroma": round(chroma, 3),
    "bass": round(bass, 3),
    "rhythm": round(rhythm, 3),
    "total": round(0.45 * chroma + 0.35 * bass + 0.2 * rhythm, 3),
    "beats_compared": int(w.sum()),
  }


# ---------------------------------------------------------------- drum-transient alignment
def perc_env(y, sr, t0, t1, hop=64):
  """Percussive onset envelope of the mono excerpt [t0, t1), one value per hop samples."""
  a, b = max(0, int(t0 * sr)), max(0, int(t1 * sr))
  x = to_mono(y)[a:b].astype(np.float32)
  if len(x) < 2048:
    return np.zeros(max(1, len(x) // hop))
  S = np.abs(librosa.stft(x, n_fft=1024, hop_length=hop))
  _, P = librosa.decompose.hpss(S, margin=1.5)
  flux = np.maximum(0, np.diff(np.log1p(50 * P), axis=1)).sum(0)
  env = np.r_[0, flux]
  if (
    t0 < 0
  ):  # keep the envelope anchored at t0 even when the excerpt starts before the file
    env = np.r_[np.zeros(int(-t0 * sr / hop)), env]
  return env


def refine_onset(y, sr, t, win=0.05):
  """Time (s) of the strongest transient within +-win of a tracked beat time t, to about 3 ms.
  Beat trackers place beats on a coarse frame grid and are often 10-25 ms off the actual hit.
  This uses spectral flux with a short 256-sample window, so the peak cannot sit more than a few
  milliseconds from the attack (a long analysis window would pull it earlier by half its length)."""
  a = max(0, int((t - win - 0.01) * sr))
  x = to_mono(y)[a : int((t + win + 0.01) * sr)].astype(np.float32)
  if len(x) < 512:
    return t
  hop = 16
  S = np.abs(librosa.stft(x, n_fft=256, hop_length=hop, center=True))
  flux = np.r_[0, np.maximum(0, np.diff(np.log1p(100 * S), axis=1)).sum(0)]
  tt = a / sr + np.arange(len(flux)) * hop / sr
  sel = (tt >= t - win) & (tt <= t + win)
  if not sel.any() or flux[sel].max() <= 0:
    return t
  return float(tt[sel][np.argmax(flux[sel])])


def align_transients(yA, tA, yB, tB, sr, pre, post, search=0.04):
  """Find tB' within +-search of tB so that B's drum hits around tB' line up with A's around tA.
  Returns (tB', correlation). The correlation is of percussive onset envelopes (hop 64 samples)."""
  hop = 64
  eA = perc_env(yA, sr, tA - pre, tA + post, hop)
  eB = perc_env(yB, sr, tB - pre - search, tB + post + search, hop)
  n, s = len(eA), int(search * sr / hop)
  best, lag = -2.0, s
  za = eA - eA.mean()
  for k in range(0, 2 * s + 1):
    seg = eB[k : k + n]
    if len(seg) < n:
      break
    zb = seg - seg.mean()
    c = float(za @ zb / (np.linalg.norm(za) * np.linalg.norm(zb) + 1e-9))
    if c > best:
      best, lag = c, k
  return tB + (lag - s) * hop / sr, best


def ep_fade(n):
  """Equal-power fade-out and fade-in curves of n samples (their powers sum to one)."""
  x = np.linspace(0, np.pi / 2, n, endpoint=False) if n > 0 else np.zeros(0)
  return np.cos(x), np.sin(x)


def splice(yA, tA, yB, tB, sr, fade):
  """Play A up to its downbeat tA, then B from its downbeat tB, crossfading over `fade` seconds.
  The fade covers the beat BEFORE the downbeat, so the downbeat hit itself comes from B alone,
  whole. If B has less than `fade` before tB, the fade covers the beat after instead.
  Returns (audio, fade_start_in_output, fade_end_in_output)."""
  n = int(round(fade * sr))
  ia, ib = int(round(tA * sr)), int(round(tB * sr))
  fo, fi = ep_fade(n)
  if ib - n >= 0 and ia - n >= 0:
    xa, xb = yA[:, ia - n : ia], yB[:, ib - n : ib]
    out = np.concatenate([yA[:, : ia - n], xa * fo + xb * fi, yB[:, ib:]], axis=1)
    return out, (ia - n) / sr, ia / sr
  xa, xb = yA[:, ia : ia + n], yB[:, ib : ib + n]
  k = min(xa.shape[1], xb.shape[1])
  out = np.concatenate(
    [yA[:, :ia], xa[:, :k] * fo[:k] + xb[:, :k] * fi[:k], yB[:, ib + k :]], axis=1
  )
  return out, ia / sr, (ia + k) / sr


def tuning_cents(y, sr):
  m = librosa.resample(to_mono(y).astype(np.float32), orig_sr=sr, target_sr=AN_SR)
  return float(librosa.estimate_tuning(y=m, sr=AN_SR, bins_per_octave=36)) * 100


def level_db(y, sr, t0, t1):
  a, b = max(0, int(t0 * sr)), max(0, int(t1 * sr))
  x = to_mono(y)[a:b]
  return float(20 * np.log10(np.sqrt(np.mean(x**2)) + 1e-9)) if len(x) else -120.0
