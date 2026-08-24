"""
Generate ElevenLabs voiceover for a product-demo walkthrough spec, and give the
video its clock.

The renderer fits each beat's choreography into exactly the number of frames its
narration occupies, so this runs *before* `rs-render demo`: it synthesises one
mp3 per beat, measures it, and writes `durationMs` back into the spec. Audio and
video then cannot drift, however long a sentence turns out to be.

Idempotent - a beat whose mp3 already exists is skipped unless --force, so
re-timing a spec after an edit only re-bills the beats that changed.

The spec owns its own sound: "voiceId" picks the narrator (falling back to
$ELEVEN_LABS_VOICE_ID) and "tailMs" the silence after each line, so a series can
give one scenario a different voice or a different pace without anyone
remembering a flag at the command line.

Usage:
    uv run python tools/demo_narrate.py showcase/coffee_roaster/driftline.walkthrough.json
    uv run python tools/demo_narrate.py <spec> --force
    uv run python tools/demo_narrate.py <spec> --voice-id <id>   # try a voice without editing the spec
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys

from helpers import require_env
from generate_voiceover_audio import generate_audio

# Silence after each line. Demo narration lands on a visual beat, and butting
# the next sentence straight onto the last syllable reads as rushed.
DEFAULT_TAIL_MS = 420


def resolve(flag, spec, key, default):
    """Flag beats spec beats default.

    Anything an episode should be able to declare belongs in its spec, so a
    demo reproduces from the spec alone and does not depend on someone
    remembering a flag. The flag stays for one-off experiments (trying a
    different voice without editing the file).
    """
    if flag is not None:
        return flag
    if key in spec and spec[key] is not None:
        return spec[key]
    return default


def probe_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", path],
        capture_output=True, text=True).stdout.strip()
    return float(out or 0)


def main():
    ap = argparse.ArgumentParser(description="Voiceover + timing for a demo walkthrough spec")
    ap.add_argument("spec", help="path to a *.walkthrough.json")
    ap.add_argument("--force", action="store_true", help="regenerate every beat")
    ap.add_argument("--tail-ms", type=int, default=None,
                    help=f'silence appended to each beat (spec "tailMs", default {DEFAULT_TAIL_MS})')
    ap.add_argument("--voice-id", default=None,
                    help='ElevenLabs voice (spec "voiceId", else $ELEVEN_LABS_VOICE_ID)')
    args = ap.parse_args()

    spec_path = os.path.abspath(args.spec)
    with open(spec_path) as f:
        spec = json.load(f)

    spec_dir = os.path.dirname(spec_path)
    slug = spec.get("slug") or os.path.basename(spec_path).split(".")[0]
    audio_dir = os.path.join(spec_dir, "audio")
    os.makedirs(audio_dir, exist_ok=True)

    # The voice is part of the episode, not of the machine that renders it: a
    # series can give one scenario a different narrator without changing env.
    voice_id = args.voice_id or spec.get("voiceId") or require_env("ELEVEN_LABS_VOICE_ID")
    tail_ms = resolve(args.tail_ms, spec, "tailMs", DEFAULT_TAIL_MS)
    beats = spec.get("beats") or []
    if not beats:
        print(f"ERROR: {args.spec} has no beats", file=sys.stderr)
        return 1

    print(f"{slug}: {len(beats)} beats  voice {voice_id}  tail {tail_ms}ms\n")
    total = 0.0
    for beat in beats:
        bid = beat.get("id") or f"beat{beats.index(beat)}"
        narration = (beat.get("narration") or "").strip()

        if not narration:
            # A silent beat still needs a length; the spec's own value wins.
            ms = int(beat.get("durationMs") or 2500)
            beat["durationMs"] = ms
            total += ms / 1000
            print(f"  {bid.ljust(20)} (silent)  {ms/1000:5.1f}s")
            continue

        out_path = os.path.join(audio_dir, f"{slug}_{bid}.mp3")
        # Re-synthesise when the words changed, not just when the file is gone -
        # editing narration and keeping stale audio is the quiet way to desync a
        # whole video.
        digest = hashlib.sha1(narration.encode()).hexdigest()[:12]
        stale = beat.get("narrationHash") != digest
        have = os.path.exists(out_path) and os.path.getsize(out_path) > 0

        if args.force or stale or not have:
            reason = "forced" if args.force else ("text changed" if have and stale else "new")
            print(f"  {bid.ljust(20)} {len(narration):4d} chars  ({reason})")
            if not generate_audio(voice_id, narration, out_path):
                print(f"ERROR: voiceover failed for beat {bid}", file=sys.stderr)
                return 1
        else:
            print(f"  {bid.ljust(20)} {len(narration):4d} chars  (cached)")

        dur = probe_duration(out_path)
        if dur <= 0:
            print(f"ERROR: {out_path} has no duration", file=sys.stderr)
            return 1

        beat["audio"] = os.path.relpath(out_path, spec_dir)
        beat["narrationHash"] = digest
        beat["durationMs"] = int(round(dur * 1000)) + tail_ms
        total += beat["durationMs"] / 1000

    with open(spec_path, "w") as f:
        json.dump(spec, f, indent=2)
        f.write("\n")

    print(f"\n  total {total:.1f}s -> durationMs written into {os.path.basename(spec_path)}")
    print(f"  next: node renderer/src/cli.mjs demo --spec {args.spec}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
