"""
Generate a background music bed via the ElevenLabs Music API (experimental).

ElevenLabs music is text-prompted (unlike video, which is Studio-UI only). This tries the
music compose endpoint and saves the returned audio into assets/music/. "Just see what
happens" — it prints the HTTP status + content-type so we learn the real contract if the
endpoint/params differ.

Usage:
    uv run python tools/generate_music.py tech_corporate --length 30
    uv run python tools/generate_music.py "driving corporate electronic, no vocals" --length 30 --id custom
    uv run python tools/generate_music.py tech_corporate --length 30 --append-manifest
"""

import argparse
import json
import os
import urllib.error
import urllib.request

from helpers import require_env

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MUSIC_DIR = os.path.join(ROOT, "assets", "music")
API_BASE = "https://api.elevenlabs.io/v1"

# Named prompt presets — house vibe: electronic / EDM-adjacent, corporate but not cheesy,
# confident but not a rave. No vocals (it sits under a voiceover).
PRESETS = {
    "tech_corporate": (
        "Clean corporate electronic underscore. Driving but understated four-on-the-floor "
        "pulse, warm analog synth pads, subtle arpeggios, light plucks. Confident, modern, "
        "polished — suitable for a financial explainer. No vocals. Not cheesy, not aggressive. "
        "Around 90 BPM."
    ),
    "uplift_edm": (
        "Uplifting modern EDM, corporate-clean. Bright plucks, side-chained pads, a tasteful "
        "build and a restrained drop. Energetic and optimistic but professional — for a short "
        "social teaser. No vocals. Around 120 BPM."
    ),
    "tense_minimal": (
        "Minimal tense electronic underscore. Low pulsing bass, sparse percussion, a single "
        "cold arpeggio, slow tension build. Serious, analytical mood for a risk segment. "
        "No vocals. Around 80 BPM."
    ),
}

# Candidate endpoints/params to try, in order (the API surface is new — learn from the response).
ENDPOINTS = ["/music", "/music/compose"]


def music_request(path, data, api_key):
    url = f"{API_BASE}{path}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=240) as resp:
            return resp.status, resp.headers.get("Content-Type", ""), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type", ""), e.read()
    except urllib.error.URLError as e:
        return None, "", str(e.reason).encode()


def generate(prompt, length_s, out_id, append_manifest):
    api_key = require_env("ELEVEN_LABS_API_KEY")
    os.makedirs(MUSIC_DIR, exist_ok=True)
    length_ms = int(length_s * 1000)
    data = {"prompt": prompt, "music_length_ms": length_ms}

    print(f"Prompt: {prompt}\nLength: {length_s}s\n")
    for path in ENDPOINTS:
        print(f"  POST {path} ...")
        status, ctype, payload = music_request(path, data, api_key)
        print(f"    -> status={status} content-type={ctype} bytes={len(payload) if payload else 0}")
        if status == 200 and "audio" in ctype:
            out_path = os.path.join(MUSIC_DIR, f"{out_id}.mp3")
            with open(out_path, "wb") as f:
                f.write(payload)
            print(f"    -> saved {out_path} ({len(payload)/1024:.0f} KB)")
            if append_manifest:
                _append_manifest(out_id, prompt, length_s)
            print("\nDone.")
            return
        # Not audio — show the server's message so we can correct the contract.
        try:
            print("    body:", json.dumps(json.loads(payload.decode()), indent=2)[:1500])
        except Exception:
            print("    body:", payload[:800])
    print("\nNo endpoint returned audio. See the bodies above for the expected params.")


def _append_manifest(out_id, prompt, length_s):
    path = os.path.join(MUSIC_DIR, "manifest.json")
    items = []
    if os.path.exists(path):
        with open(path) as f:
            items = json.load(f)
    if any(it["id"] == out_id for it in items):
        print(f"    (manifest already has '{out_id}' — not duplicating)")
        return
    items.append({
        "id": out_id,
        "file": f"{out_id}.mp3",
        "duration": round(length_s, 1),
        "mood": ["electronic", "corporate"],
        "description": prompt,
        "source": "ElevenLabs Music API",
    })
    with open(path, "w") as f:
        json.dump(items, f, indent=2)
    print(f"    -> appended '{out_id}' to music manifest")


def main():
    p = argparse.ArgumentParser(description="Generate a music bed via ElevenLabs Music API")
    p.add_argument("prompt", help=f"A preset name ({', '.join(PRESETS)}) or a literal prompt")
    p.add_argument("--length", type=float, default=30, help="Length in seconds (default 30)")
    p.add_argument("--id", default=None, help="Output id (default: preset name or 'generated')")
    p.add_argument("--append-manifest", action="store_true", help="Add to assets/music/manifest.json")
    args = p.parse_args()

    prompt = PRESETS.get(args.prompt, args.prompt)
    out_id = args.id or (args.prompt if args.prompt in PRESETS else "generated")
    generate(prompt, args.length, out_id, args.append_manifest)


if __name__ == "__main__":
    main()
