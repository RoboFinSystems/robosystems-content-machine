#!/usr/bin/env python3
"""
Assemble a showcase episode: motion shots, live walkthroughs and chat takes, cut to the voice.

The episode is showcase/<episode>/episode.json, a list of segments:

  { "id": "open", "kind": "motion", "template": "intro", "data": {...}, "narration": "..." }
  { "id": "ask",  "kind": "walkthrough", "spec": "ask.walkthrough.json" }
  { "id": "chat", "kind": "clip", "file": "takes/chat.mp4", "in": 12.0, "out": 27.5,
    "narration": "...", "keepAudio": false }

- motion       a template from motion/ (intro, outro, slide) rendered to the length of its
               narration plus a tail, so the picture follows the voice.
- walkthrough  a live walkthrough already recorded by `just demo-pipeline`; its narration
               lives in its own beats, so the assembler takes renders/<slug>_vo.mp4 as is.
- clip         a span of a recording (a chat take): trimmed, scaled to 1920x1080, voiced
               with its narration, or keeping its own audio with "keepAudio": true.

Segments dissolve into each other (0.4s, "fade" per episode); motion shots already fade
into the shared backdrop, so no cut dips to black. The voice is one track built from every
segment's audio; the music bed is ducked under it, the same mix as demo_mux.py. Outputs in
showcase/<episode>/renders/:

  <slug>_silent.mp4   picture only, for the pop scan
  <slug>_vo.mp4       voice only, the comparison cut
  <slug>_final.mp4    voice + ducked music at -14 LUFS (YouTube's target), the publish candidate

Usage:
  uv run python tools/demo_assemble.py showcase/pilot/episode.json [--no-voice] [--skip-music]
      --no-voice  skip TTS: motion shots use their data.duration and clips stay silent
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import urllib.parse
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))

W, H, FPS = 1920, 1080, 30
DEFAULT_TAIL_MS = 500
DEFAULT_FADE = 0.4
MUSIC_GAIN = -22
RL_PUBLIC = Path(
  os.environ.get("ROBOLEDGER_PUBLIC", Path.home() / "Projects/roboledger-app/public")
)


def run(cmd):
  r = subprocess.run(cmd, capture_output=True, text=True)
  if r.returncode != 0:
    sys.stderr.write(r.stderr[-3000:])
    raise SystemExit(f"failed ({r.returncode}): {' '.join(map(str, cmd[:4]))} ...")
  return r


def duration(path):
  out = run(
    [
      "ffprobe",
      "-v",
      "error",
      "-show_entries",
      "format=duration",
      "-of",
      "csv=p=0",
      str(path),
    ]
  ).stdout
  return float(out.strip())


def voice(seg, audio_dir, slug, voice_id, no_voice):
  """The segment's narration mp3, synthesised once per text (cached by hash)."""
  text = (seg.get("narration") or "").strip()
  if not text or no_voice:
    return None
  digest = hashlib.sha1(text.encode()).hexdigest()[:10]
  out = audio_dir / f"{slug}_{seg['id']}_{digest}.mp3"
  if not out.exists():
    from generate_voiceover_audio import generate_audio

    if not voice_id:
      raise SystemExit("no voice: set episode 'voiceId' or $ELEVEN_LABS_VOICE_ID")
    if not generate_audio(voice_id, text, str(out)):
      raise SystemExit(f"TTS failed for segment {seg['id']}")
  return out


def render_motion(seg, secs, out_dir, name):
  data = dict(seg.get("data") or {})
  if secs:
    data["duration"] = round(secs, 3)
  query = f"t={seg['template']}&data={urllib.parse.quote(json.dumps(data))}"
  mounts = (
    f"/demos/={RL_PUBLIC}/demos,/fonts/={RL_PUBLIC}/fonts,/images/={RL_PUBLIC}/images"
  )
  run(
    [
      "node",
      str(REPO / "renderer/src/cli.mjs"),
      "motion",
      "--root",
      str(REPO / "motion"),
      "--html",
      str(REPO / "motion/render.html"),
      "--mount",
      mounts,
      "--query",
      query,
      "--name",
      name,
      "--out",
      str(out_dir),
    ]
  )
  return out_dir / f"{name}.mp4"


def normalize(
  src, dst, audio=None, keep_audio=False, t_in=None, t_out=None, length=None
):
  """One segment as 1920x1080@30 with a stereo 48k audio track (silent if it has none)."""
  cmd = ["ffmpeg", "-y", "-loglevel", "error"]
  if t_in is not None:
    cmd += ["-ss", str(t_in)]
  if t_out is not None:
    cmd += ["-to", str(t_out)]
  cmd += ["-i", str(src)]
  if audio:
    cmd += ["-i", str(audio)]
  else:
    cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
  vf = f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black,fps={FPS},format=yuv420p"
  if length:
    # a line longer than its clip holds the clip's last frame rather than ending early
    vf += f",tpad=stop_mode=clone:stop_duration={length:.3f}"
  a_src = "0:a" if keep_audio else "1:a"
  cmd += [
    "-filter_complex",
    f"[0:v]{vf}[v];[{a_src}]aresample=48000,aformat=channel_layouts=stereo,apad[a]",
    "-map",
    "[v]",
    "-map",
    "[a]",
  ]
  if length:
    cmd += ["-t", f"{length:.3f}"]
  else:
    cmd += ["-shortest"]
  cmd += [
    "-c:v",
    "libx264",
    "-crf",
    "16",
    "-preset",
    "medium",
    "-c:a",
    "aac",
    "-b:a",
    "192k",
    str(dst),
  ]
  run(cmd)
  return dst


def main() -> int:
  ap = argparse.ArgumentParser()
  ap.add_argument("episode")
  ap.add_argument("--no-voice", action="store_true")
  ap.add_argument("--skip-music", action="store_true")
  args = ap.parse_args()

  ep_path = Path(args.episode).resolve()
  ep = json.loads(ep_path.read_text())
  ep_dir = ep_path.parent
  slug = ep.get("slug") or ep_dir.name
  renders = ep_dir / "renders"
  work = renders / "segments"
  audio_dir = ep_dir / "audio"
  for d in (renders, work, audio_dir):
    d.mkdir(parents=True, exist_ok=True)
  voice_id = ep.get("voiceId") or os.environ.get("ELEVEN_LABS_VOICE_ID")
  tail = (ep.get("tailMs", DEFAULT_TAIL_MS)) / 1000
  fade = float(ep.get("fade", DEFAULT_FADE))

  parts = []
  for seg in ep["segments"]:
    sid, kind = seg["id"], seg["kind"]
    out = work / f"{sid}.mp4"
    vo = voice(seg, audio_dir, slug, voice_id, args.no_voice)
    if kind == "motion":
      secs = (duration(vo) + tail + fade) if vo else None
      raw = render_motion(seg, secs, work, f"{sid}_raw")
      normalize(raw, out, audio=vo)
    elif kind == "walkthrough":
      spec = json.loads((ep_dir / seg["spec"]).read_text())
      wslug = spec.get("slug", "demo")
      src = ep_dir / seg.get("render", f"renders/{wslug}_vo.mp4")
      if not src.exists():
        raise SystemExit(
          f"segment {sid}: no render at {src} (run just demo-pipeline on {seg['spec']})"
        )
      normalize(src, out, keep_audio=True)
    elif kind == "clip":
      t_in, t_out = seg.get("in"), seg.get("out")
      span = (t_out - t_in) if (t_in is not None and t_out is not None) else None
      length = max(span or 0, (duration(vo) + tail) if vo else 0) or None
      normalize(
        ep_dir / seg["file"],
        out,
        audio=vo,
        keep_audio=seg.get("keepAudio", False),
        t_in=t_in,
        t_out=t_out,
        length=length,
      )
    else:
      raise SystemExit(
        f"segment {sid}: unknown kind {kind!r} (motion, walkthrough, clip)"
      )
    d = duration(out)
    parts.append((sid, out, d))
    print(f"  {sid:<14} {kind:<11} {d:6.2f}s")

  # dissolve chain: each join overlaps the segments by `fade` seconds
  inputs, vchain, achain, cuts = [], "", "", []
  for i, (_, p, _) in enumerate(parts):
    inputs += ["-i", str(p)]
  t = parts[0][2]
  vlast, alast = "[0:v]", "[0:a]"
  for i in range(1, len(parts)):
    off = t - fade
    cuts.append(round(off + fade / 2, 3))
    vchain += (
      f"{vlast}[{i}:v]xfade=transition=fade:duration={fade}:offset={off:.3f}[v{i}];"
    )
    achain += f"{alast}[{i}:a]acrossfade=d={fade}[a{i}];"
    vlast, alast = f"[v{i}]", f"[a{i}]"
    t = off + parts[i][2]
  silent = renders / f"{slug}_silent.mp4"
  vo_out = renders / f"{slug}_vo.mp4"
  run(
    [
      "ffmpeg",
      "-y",
      "-loglevel",
      "error",
      *inputs,
      "-filter_complex",
      (vchain + achain).rstrip(";"),
      "-map",
      vlast,
      "-map",
      alast,
      "-c:v",
      "libx264",
      "-crf",
      "16",
      "-preset",
      "medium",
      "-pix_fmt",
      "yuv420p",
      "-c:a",
      "aac",
      "-b:a",
      "192k",
      "-movflags",
      "+faststart",
      str(vo_out),
    ]
  )
  run(
    [
      "ffmpeg",
      "-y",
      "-loglevel",
      "error",
      "-i",
      str(vo_out),
      "-an",
      "-c:v",
      "copy",
      str(silent),
    ]
  )
  print(f"\n  {len(parts)} segments, {t:.1f}s, joins at {', '.join(map(str, cuts))}")

  music = ep.get("music")
  final = renders / f"{slug}_final.mp4"
  if music and not args.skip_music:
    mpath = Path(music) if Path(music).is_absolute() else REPO / music
    gain = ep.get("musicGain", MUSIC_GAIN)
    run(
      [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(vo_out),
        "-stream_loop",
        "-1",
        "-i",
        str(mpath),
        "-filter_complex",
        f"[0:a]asplit=2[vomain][voref];[1:a]aresample=48000,volume={gain}dB,"
        f"afade=t=in:d=1.5,afade=t=out:st={max(0, t - 2):.2f}:d=2[mus];"
        "[mus][voref]sidechaincompress=threshold=0.02:ratio=8:attack=180:release=1000[musd];"
        "[vomain][musd]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[aout]",
        "-map",
        "0:v",
        "-map",
        "[aout]",
        "-t",
        f"{t:.3f}",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        str(final),
      ]
    )
  print(
    f"  wrote {vo_out.relative_to(ep_dir)}"
    + (f", {final.relative_to(ep_dir)}" if final.exists() else "")
  )
  print(f"  pop scan: just motion-pops {silent} --cuts {','.join(map(str, cuts))}")
  (renders / f"{slug}_cuts.txt").write_text(",".join(map(str, cuts)))
  return 0


if __name__ == "__main__":
  sys.exit(main())
