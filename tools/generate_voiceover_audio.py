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
            with urllib.request.urlopen(req, timeout=60) as resp:
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
        except urllib.error.URLError as e:
            if attempt < MAX_RETRIES - 1:
                wait = 2 ** attempt
                print(f"  ElevenLabs network error ({e.reason}), retrying in {wait}s...")
                time.sleep(wait)
                continue
            print(f"  Network error: {e.reason}")
            return None
    return None


# ElevenLabs occasionally inserts multi-second dead air in the middle of a segment.
# Measured 2026-07-27: the same text, voice and settings produced max internal gaps of
# 1.91s, 3.48s, 3.28s and 1.96s across four runs, and a fifth run came back clean at
# 0.71s. It is stochastic, not a voice or a settings problem - which is why switching
# voices never fixed it. So generate, measure, and re-roll the bad takes.
GAP_LIMIT = float(os.environ.get("TTS_GAP_LIMIT", "1.5"))   # seconds of mid-clip silence
GAP_TAKES = int(os.environ.get("TTS_GAP_TAKES", "3"))       # attempts before keeping the best


def max_internal_gap(path):
    """Longest silence that is neither leading nor trailing, in seconds.

    Leading/trailing silence is normal and gets trimmed by the mux; a long pause in the
    middle of a sentence is the artifact we are hunting. Returns 0.0 if ffmpeg is
    unavailable so the check degrades to a no-op rather than blocking a run.
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

    Each take is checked for mid-clip dead air and re-rolled up to GAP_TAKES times;
    the cleanest take wins so a bad roll never reaches the render.
    """
    data = {
        "text": normalize_for_tts(text),
        "model_id": "eleven_turbo_v2_5",
        "voice_settings": {
            "stability": 0.7,
            "similarity_boost": 0.8,
            "style": 0.3,
            "use_speaker_boost": True,
        },
    }

    best_audio, best_gap = None, None
    for take in range(1, GAP_TAKES + 1):
        audio_data = api_request(f"/text-to-speech/{voice_id}", data)
        if not (audio_data and isinstance(audio_data, bytes)):
            continue
        with open(output_path, "wb") as f:
            f.write(audio_data)
        gap = max_internal_gap(output_path)
        if best_gap is None or gap < best_gap:
            best_audio, best_gap = audio_data, gap
        if gap <= GAP_LIMIT:
            break
        print(f"    take {take}: {gap:.2f}s of dead air mid-clip, re-rolling", flush=True)

    if best_audio is None:
        return False
    with open(output_path, "wb") as f:
        f.write(best_audio)

    # Re-rolling is a lottery and some inputs lose it repeatedly, so cap what is left.
    if best_gap > GAP_LIMIT:
        capped = cap_long_pauses(output_path)
        if capped is not None:
            print(f"    trimmed dead air: {best_gap:.2f}s -> {capped:.2f}s", flush=True)
        else:
            print(f"    WARNING: best of {GAP_TAKES} takes still has a {best_gap:.2f}s gap",
                  flush=True)
    return True


def cap_long_pauses(path, cap=0.7):
    """Trim any silence longer than `cap` seconds down to roughly `cap`.

    The dropouts cluster in the first few seconds of a clip: the voice says a phrase,
    goes quiet for 2-3 seconds, then resumes. Capping is deterministic where re-rolling
    is not. Returns the new max internal gap, or None if the trim was skipped because it
    did not help or because it removed so much audio that it likely ate speech.
    """
    before = max_internal_gap(path)
    tmp = f"{path}.capped.mp3"
    try:
        old_dur = float(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(path)],
            capture_output=True, text=True).stdout.strip() or 0)
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", str(path), "-af",
             f"silenceremove=stop_periods=-1:stop_duration={cap}:"
             f"stop_threshold=-42dB:detection=peak", tmp],
            capture_output=True, check=True)
        new_dur = float(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", tmp],
            capture_output=True, text=True).stdout.strip() or 0)
    except (OSError, ValueError, subprocess.CalledProcessError):
        if os.path.exists(tmp):
            os.remove(tmp)
        return None

    after = max_internal_gap(tmp)
    # Guard against the filter eating speech rather than silence.
    if new_dur < old_dur * 0.75 or after >= before:
        os.remove(tmp)
        return None
    os.replace(tmp, path)
    return after


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
