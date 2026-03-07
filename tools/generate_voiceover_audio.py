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
import urllib.request
import urllib.error

from helpers import get_project_dir, require_env

API_BASE = "https://api.elevenlabs.io/v1"


def api_request(path, data=None, method="POST"):
    url = f"{API_BASE}{path}"
    api_key = require_env("ELEVEN_LABS_API_KEY")
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            content_type = resp.headers.get("Content-Type", "")
            if "audio" in content_type:
                return resp.read()  # Binary audio data
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"  API Error {e.code}: {error_body}")
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


def generate_all(project_name):
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

        print(f"  Segment {seg_id} ({seg.get('visual_ref', seg.get('visual_type', 'visual'))})...", end=" ")
        print(f"({len(narration)} chars)")

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
    print(f"\n{done}/{len(results)} voiceovers generated")
    print(f"Audio files: {audio_dir}")
    print(f"Manifest: {manifest_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate voiceover audio via ElevenLabs")
    parser.add_argument("project", help="Project name (e.g., JPM_2025_10_K)")
    args = parser.parse_args()
    generate_all(args.project)


if __name__ == "__main__":
    main()
