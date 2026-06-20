"""
Generate voiceover audio via ElevenLabs API.

In slides-only mode (no avatar segments), generates voiceover for ALL segments.
In mixed mode (avatar + visual), generates voiceover only for visual segments
(avatar segments get their audio from HeyGen).

Usage:
    uv run python tools/generate_voiceover_audio.py JPM_2025_10_K
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error

from helpers import get_project_dir, require_env

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


def generate_audio(voice_id, text, output_path):
    """Generate speech audio for a text segment."""
    data = {
        "text": text,
        "model_id": "eleven_turbo_v2_5",
        "voice_settings": {
            "stability": 0.7,
            "similarity_boost": 0.8,
            "style": 0.3,
            "use_speaker_boost": True,
        },
    }

    audio_data = api_request(f"/text-to-speech/{voice_id}", data)

    if audio_data and isinstance(audio_data, bytes):
        with open(output_path, "wb") as f:
            f.write(audio_data)
        return True
    return False


def generate_all(project_name, force=False):
    project_dir = get_project_dir(project_name)
    voice_id = require_env("ELEVEN_LABS_VOICE_ID")

    # Find script
    scripts_dir = os.path.join(project_dir, "scripts")
    script_files = [f for f in os.listdir(scripts_dir) if f.endswith("_script.json")]
    if not script_files:
        print(f"No script JSON found in {scripts_dir}")
        sys.exit(1)

    script_path = os.path.join(scripts_dir, script_files[0])
    with open(script_path) as f:
        script = json.load(f)

    ticker = script["metadata"]["ticker"]
    segments = script["segments"]

    # Detect mode: if any avatar segments exist, only voiceover the visual ones
    has_avatar = any(s["type"] == "avatar" for s in segments)
    if has_avatar:
        visual_segments = [s for s in segments if s["type"] == "visual"]
        print(f"Script: {ticker} | Mixed mode: {len(visual_segments)} visual segments need voiceover\n")
    else:
        visual_segments = segments  # All segments get voiceover
        print(f"Script: {ticker} | Slides-only mode: {len(visual_segments)} segments need voiceover\n")

    audio_dir = os.path.join(project_dir, "videos", "audio")
    os.makedirs(audio_dir, exist_ok=True)

    results = []
    for seg in visual_segments:
        seg_id = seg["id"]
        narration = seg["narration"]
        output_path = os.path.join(audio_dir, f"{ticker}_segment_{seg_id}_voiceover.mp3")
        ref = seg.get("visual_ref", seg.get("visual_type", "visual"))

        # Idempotent: skip already-generated audio unless --force. Re-running the
        # pipeline shouldn't re-bill every segment to ElevenLabs.
        if not force and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print(f"  Segment {seg_id} ({ref})... SKIP (already exists)")
            results.append({
                "segment_id": seg_id,
                "visual_ref": seg.get("visual_ref"),
                "filename": f"{ticker}_segment_{seg_id}_voiceover.mp3",
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
                "filename": f"{ticker}_segment_{seg_id}_voiceover.mp3",
                "status": "done",
            })
        else:
            print(f"    -> FAILED")
            results.append({
                "segment_id": seg_id,
                "status": "failed",
            })

    # Save manifest
    manifest_path = os.path.join(audio_dir, "voiceover_manifest.json")
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
    args = parser.parse_args()
    generate_all(args.project, force=args.force)


if __name__ == "__main__":
    main()
