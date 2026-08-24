"""
Mux a rendered product-demo walkthrough: silent mp4 + per-beat voiceover
(+ an optional ducked music bed).

Each beat's audio is delayed to the frame boundary the renderer gave it, which
is the same offset the renderer used to size the beat - so the narration lands
on its own visuals by construction rather than by nudging.

Two outputs, matching the webdeck convention:
  renders/<slug>_vo.mp4     VO only, the comparison cut
  renders/<slug>_final.mp4  VO + ducked music, the publish candidate

The bed is part of the episode: "music" (repo-relative or absolute, or null to
ship without one) and "musicGain" come from the spec, so the publish candidate
reproduces from the spec alone. Flags still override for a one-off.

Usage:
    uv run python tools/demo_mux.py showcase/coffee_roaster/driftline.walkthrough.json
            [--music assets/music/tech_corporate.mp3] [--music-gain -22] [--skip-music]
"""

import argparse
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Demos sit quieter than research videos: the bed is there to kill silence, not
# to carry the piece.
DEFAULT_MUSIC = "assets/music/tech_corporate.mp3"
DEFAULT_MUSIC_GAIN = -22.0


def run(cmd):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-3000:], file=sys.stderr)
        raise SystemExit(f"ffmpeg failed ({r.returncode})")


def probe_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", path],
        capture_output=True, text=True).stdout.strip()
    return float(out or 0)


def main():
    ap = argparse.ArgumentParser(description="Mux VO + music onto a rendered demo walkthrough")
    ap.add_argument("spec", help="path to a *.walkthrough.json")
    ap.add_argument("--music", default=None,
                    help=f'bed, repo-relative or absolute (spec "music", default {DEFAULT_MUSIC})')
    ap.add_argument("--music-gain", type=float, default=None,
                    help=f'bed gain in dB before ducking (spec "musicGain", default {DEFAULT_MUSIC_GAIN})')
    ap.add_argument("--skip-music", action="store_true")
    ap.add_argument("--silent", default=None, help="override the silent render path")
    args = ap.parse_args()

    spec_path = os.path.abspath(args.spec)
    with open(spec_path) as f:
        spec = json.load(f)
    spec_dir = os.path.dirname(spec_path)
    slug = spec.get("slug") or os.path.basename(spec_path).split(".")[0]

    # Flag beats spec beats default, so a demo reproduces from its spec alone
    # rather than from someone remembering the flags. A spec may declare
    # "music": null to ship deliberately without a bed.
    music_rel = args.music if args.music is not None else (
        spec.get("music") if "music" in spec else DEFAULT_MUSIC)
    music_gain = args.music_gain if args.music_gain is not None else (
        spec.get("musicGain") if spec.get("musicGain") is not None else DEFAULT_MUSIC_GAIN)

    renders = os.path.join(spec_dir, "renders")
    silent = args.silent or os.path.join(renders, f"{slug}.mp4")
    if not os.path.exists(silent):
        print(f"ERROR: {silent} not found - render first:\n"
              f"  node renderer/src/cli.mjs demo --spec {args.spec}", file=sys.stderr)
        return 1

    beats = spec.get("beats") or []
    segs, offset = [], 0.0
    for beat in beats:
        ms = beat.get("durationMs")
        if not ms:
            print(f"ERROR: beat {beat.get('id')} has no durationMs - run tools/demo_narrate.py first",
                  file=sys.stderr)
            return 1
        if beat.get("audio"):
            path = os.path.join(spec_dir, beat["audio"])
            if not os.path.exists(path):
                print(f"ERROR: missing audio {path}", file=sys.stderr)
                return 1
            segs.append({"file": path, "start": offset, "id": beat.get("id")})
        offset += ms / 1000.0

    total = offset
    video_len = probe_duration(silent)
    # The renderer pads every beat to its narration, so these should agree. A
    # real gap means the spec was re-narrated after the render and the video is
    # about to be muxed against the wrong timings.
    if abs(video_len - total) > 0.75:
        print(f"WARNING: video is {video_len:.1f}s but the spec's beats total {total:.1f}s.\n"
              f"         Re-render before publishing - the narration will drift.", file=sys.stderr)

    if not segs:
        print("ERROR: no beats carry audio - run tools/demo_narrate.py first", file=sys.stderr)
        return 1

    out_vo = os.path.join(renders, f"{slug}_vo.mp4")
    out_final = os.path.join(renders, f"{slug}_final.mp4")

    inputs = ["-i", silent]
    for s in segs:
        inputs += ["-i", s["file"]]
    parts, labels = [], []
    for n, s in enumerate(segs):
        ms = round(s["start"] * 1000)
        parts.append(f"[{n+1}:a]aresample=48000,adelay={ms}|{ms}[a{n}]")
        labels.append(f"[a{n}]")
    vo_mix = ";".join(parts) + f";{''.join(labels)}amix=inputs={len(segs)}:normalize=0[vo]"

    run(["ffmpeg", "-y", *inputs,
         "-filter_complex", vo_mix + ";[vo]apad[aout]",
         "-map", "0:v", "-map", "[aout]",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-t", f"{total}", out_vo])
    print(f"A (VO only):   {os.path.relpath(out_vo, REPO)}")

    if args.skip_music or not music_rel:
        why = "--skip-music" if args.skip_music else 'spec declares no music bed'
        print(f"  {why} - keeping the VO-only cut")
        return 0

    music = music_rel if os.path.isabs(music_rel) else os.path.join(REPO, music_rel)
    if not os.path.exists(music):
        print(f"  no music bed at {music_rel} - keeping the VO-only cut", file=sys.stderr)
        return 0

    fade_out_start = max(0.0, total - 4.0)
    # apad before the split: sidechaincompress EOFs with its key input, which
    # would cut the bed at the last spoken sample instead of the video end.
    fc = (vo_mix +
          f";[vo]apad,atrim=0:{total}[vop];[vop]asplit=2[voref][vomain]" +
          f";[{len(segs)+1}:a]aresample=48000,atrim=0:{total}," +
          f"afade=t=in:st=0:d=2,afade=t=out:st={fade_out_start}:d=4," +
          f"volume={music_gain}dB[mus]" +
          ";[mus][voref]sidechaincompress=threshold=0.02:ratio=8:attack=180:release=1000[musd]" +
          ";[vomain][musd]amix=inputs=2:normalize=0,apad[aout]")
    run(["ffmpeg", "-y", *inputs, "-i", music,
         "-filter_complex", fc,
         "-map", "0:v", "-map", "[aout]",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-t", f"{total}", out_final])
    print(f"B (VO+music):  {os.path.relpath(out_final, REPO)}   <- publish candidate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
