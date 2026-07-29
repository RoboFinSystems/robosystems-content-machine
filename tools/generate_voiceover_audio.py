"""
Generate voiceover audio via ElevenLabs API — one MP3 per script segment.

Idempotent: skips segments whose MP3 already exists (use --force to regenerate).

Usage:
    uv run python tools/generate_voiceover_audio.py GTBIF
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
import urllib.error

from helpers import get_project_dir, require_env, normalize_for_tts

API_BASE = "https://api.elevenlabs.io/v1"

MAX_RETRIES = int(os.environ.get("HTTP_MAX_RETRIES", "4"))
_RETRYABLE_HTTP = (429, 500, 502, 503, 504)

# eleven_v3 is the quality model, not the latency model, and generation time scales with
# input length. Video segments are a couple hundred chars and return in seconds; a 2500-char
# blog chunk can take minutes and blew straight through the old 60s ceiling.
HTTP_TIMEOUT = float(os.environ.get("TTS_HTTP_TIMEOUT", "600"))


def api_request(path, data=None, method="POST"):
    url = f"{API_BASE}{path}"
    api_key = require_env("ELEVEN_LABS_API_KEY")
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    body = json.dumps(data).encode() if data else None
    for attempt in range(MAX_RETRIES):
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                content_type = resp.headers.get("Content-Type", "")
                if "audio" in content_type:
                    return resp.read()  # Binary audio data
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            if e.code in _RETRYABLE_HTTP and attempt < MAX_RETRIES - 1:
                wait = 2 ** attempt
                print(f"  ElevenLabs {e.code} (attempt {attempt+1}/{MAX_RETRIES}), retrying in {wait}s...")
                time.sleep(wait)
                continue
            print(f"  API Error {e.code}: {error_body}")
            return None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            # A read timeout surfaces as a bare TimeoutError, not a URLError — uncaught, it
            # killed the whole run instead of retrying the chunk.
            reason = getattr(e, "reason", e)
            if attempt < MAX_RETRIES - 1:
                wait = 2 ** attempt
                print(f"  ElevenLabs network error ({reason}), retrying in {wait}s...")
                time.sleep(wait)
                continue
            print(f"  Network error: {reason}")
            return None
    return None


# eleven_turbo_v2_5 stochastically inserted multi-second dead air mid-segment. Measured
# 2026-07-27: the same text, voice and settings gave max internal gaps of 1.91s, 3.48s,
# 3.28s and 1.96s across four runs. We answered that by generating up to three takes and
# keeping the cleanest, then capping whatever silence survived.
#
# Re-measured on eleven_v3 (2026-07-29, 12 raw takes, re-roll disabled): 6 short video
# segments came in at 0.93-1.20s and 6 long single-paragraph chunks at 1.13-1.32s. Zero
# takes over 1.5s, and the variance is tight where turbo's was wild. The artifact was a
# turbo defect and v3 does not reproduce it.
#
# So the re-roll is gone. It was not free: it tripled TTS spend, and its pause-capping
# fallback used silenceremove with stop_periods=-1, which clamps EVERY pause in the clip,
# not just the offending one - it flattened whole chunks of blog narration to a 0.7s
# rhythm. What is left is a passive warning: measure, report, never rewrite the audio.
# The threshold sits between real prosody (paragraph breaks reach ~1.9s) and a genuine
# turbo-style dropout (3s+), so a future model regression still surfaces in the log.
GAP_WARN = float(os.environ.get("TTS_GAP_WARN", "2.5"))     # seconds of mid-clip silence

# We render videos ahead of time, so generation latency is worth nothing to us and
# fidelity is worth a lot. The pipeline ran on eleven_turbo_v2_5 (the latency-optimized
# model) at the API's default 128kbps with style 0.3, which trades quality for speed we
# never use and stability we do want. eleven_v3 is the highest-quality model on the
# account; 192kbps removes compression mush that reads as slurring; style 0 keeps the
# read even. Chosen by ear from an A/B of the same sentence across both models.
TTS_MODEL = os.environ.get("TTS_MODEL", "eleven_v3")
TTS_FORMAT = os.environ.get("TTS_FORMAT", "mp3_44100_192")
TTS_STABILITY = float(os.environ.get("TTS_STABILITY", "0.5"))


def max_internal_gap(path):
    """Longest silence that is neither leading nor trailing, in seconds.

    Leading/trailing silence is normal and gets trimmed by the mux. Note this cannot tell
    a dropout from a paragraph break — both are just silence — so it is a smoke alarm, not
    a judge. Returns 0.0 if ffmpeg is unavailable so the check degrades to a no-op rather
    than blocking a run.
    """
    try:
        out = subprocess.run(
            ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
             "-af", "silencedetect=n=-42dB:d=0.4", "-f", "null", "-"],
            capture_output=True, text=True).stderr
        dur = float(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(path)],
            capture_output=True, text=True).stdout.strip() or 0)
    except (OSError, ValueError):
        return 0.0
    starts = [float(x) for x in re.findall(r"silence_start:\s*([\d.]+)", out)]
    durs = [float(x) for x in re.findall(r"silence_duration:\s*([\d.]+)", out)]
    internal = [d for s, d in zip(starts, durs) if s > 0.3 and s + d < dur - 0.3]
    return max(internal, default=0.0)


def generate_audio(voice_id, text, output_path):
    """Generate speech audio for a text segment.

    Text is run through normalize_for_tts() so mispronounced terms (e.g. EBITDA)
    are respelled phonetically for the audio only — the source script is unchanged.
    Both TTS paths (voiceover and short) call this, so the fix is global.

    Dead air is measured and reported but never corrected — see GAP_WARN. Any fix belongs
    in a re-run, not in a filter that silently rewrites the pacing of a good take.
    """
    data = {
        "text": normalize_for_tts(text),
        "model_id": TTS_MODEL,
        "voice_settings": {
            "stability": TTS_STABILITY,
            "similarity_boost": 0.8,
            "style": 0.0,
            "use_speaker_boost": True,
        },
    }

    audio_data = api_request(f"/text-to-speech/{voice_id}?output_format={TTS_FORMAT}", data)
    if not (audio_data and isinstance(audio_data, bytes)):
        return False
    with open(output_path, "wb") as f:
        f.write(audio_data)

    gap = max_internal_gap(output_path)
    if gap > GAP_WARN:
        print(f"    WARNING: {gap:.2f}s of silence mid-clip (over the {GAP_WARN:.1f}s "
              f"threshold) — listen before shipping: {output_path}", flush=True)
    return True


def generate_all(project_name, force=False, short=False):
    project_dir = get_project_dir(project_name)
    voice_id = require_env("ELEVEN_LABS_VOICE_ID")

    # Find script. --short reads the 9:16 companion (T_short_script.json) and
    # writes separate T_short_segment_* files so it never collides with the
    # long-form VO.
    scripts_dir = os.path.join(project_dir, "scripts")
    if short:
        script_files = [f for f in os.listdir(scripts_dir) if f.endswith("_short_script.json")]
    else:
        script_files = [f for f in os.listdir(scripts_dir)
                        if f.endswith("_script.json") and not f.endswith("_short_script.json")]
    if not script_files:
        kind = "short " if short else ""
        print(f"No {kind}script JSON found in {scripts_dir}")
        sys.exit(1)

    script_path = os.path.join(scripts_dir, script_files[0])
    with open(script_path) as f:
        script = json.load(f)

    ticker = script["metadata"]["ticker"]
    segments = script["segments"]
    seg_prefix = f"{ticker}_short_segment" if short else f"{ticker}_segment"

    # Deck mode: every segment is a slide with its own voiceover.
    visual_segments = segments
    print(f"Script: {ticker}{' (short)' if short else ''} | {len(visual_segments)} segments need voiceover\n")

    audio_dir = os.path.join(project_dir, "videos", "audio")
    os.makedirs(audio_dir, exist_ok=True)

    results = []
    for seg in visual_segments:
        seg_id = seg["id"]
        narration = seg["narration"]
        output_path = os.path.join(audio_dir, f"{seg_prefix}_{seg_id}_voiceover.mp3")
        ref = seg.get("visual_ref", seg.get("kind", seg.get("visual_type", "visual")))

        # Idempotent: skip already-generated audio unless --force. Re-running the
        # pipeline shouldn't re-bill every segment to ElevenLabs.
        if not force and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print(f"  Segment {seg_id} ({ref})... SKIP (already exists)")
            results.append({
                "segment_id": seg_id,
                "visual_ref": seg.get("visual_ref"),
                "filename": f"{seg_prefix}_{seg_id}_voiceover.mp3",
                "status": "skipped",
            })
            continue

        print(f"  Segment {seg_id} ({ref})... ({len(narration)} chars)")

        success = generate_audio(voice_id, narration, output_path)
        if success:
            size_kb = os.path.getsize(output_path) / 1024
            print(f"    -> OK ({size_kb:.0f}K) {output_path}")
            results.append({
                "segment_id": seg_id,
                "visual_ref": seg.get("visual_ref"),
                "filename": f"{seg_prefix}_{seg_id}_voiceover.mp3",
                "status": "done",
            })
        else:
            print(f"    -> FAILED")
            results.append({
                "segment_id": seg_id,
                "status": "failed",
            })

    # Save manifest
    manifest_name = "short_voiceover_manifest.json" if short else "voiceover_manifest.json"
    manifest_path = os.path.join(audio_dir, manifest_name)
    with open(manifest_path, "w") as f:
        json.dump({"ticker": ticker, "voice_id": voice_id, "segments": results}, f, indent=2)

    done = sum(1 for r in results if r["status"] == "done")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    failed = sum(1 for r in results if r["status"] == "failed")
    print(f"\n{done} generated, {skipped} skipped (already present), {failed} failed")
    if failed:
        print("  Re-run to retry failed segments (existing audio is reused automatically).")
    print(f"Audio files: {audio_dir}")
    print(f"Manifest: {manifest_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate voiceover audio via ElevenLabs")
    parser.add_argument("project", help="Project name (e.g., JPM_2025_10_K)")
    parser.add_argument("--force", action="store_true", help="Regenerate even if audio already exists")
    parser.add_argument("--short", action="store_true",
                        help="Voice the 9:16 short script (T_short_script.json) into T_short_segment_* files")
    args = parser.parse_args()
    generate_all(args.project, force=args.force, short=args.short)


if __name__ == "__main__":
    main()
