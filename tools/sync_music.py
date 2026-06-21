"""
Sync assets/music/manifest.json with the audio files actually present.

Drop tracks into assets/music/ (downloaded from ElevenLabs, Epidemic, etc.), then run this.
It probes each new track and appends a manifest entry with placeholder mood/description for
you to fill in. Existing entries are left untouched.

Usage:
    uv run python tools/sync_music.py
"""

import json
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MUSIC_DIR = os.path.join(ROOT, "assets", "music")
MANIFEST = os.path.join(MUSIC_DIR, "manifest.json")


def duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True,
    )
    try:
        return round(float(out.stdout.strip()), 1)
    except ValueError:
        return 0.0


def main():
    items = []
    if os.path.exists(MANIFEST):
        with open(MANIFEST) as f:
            items = json.load(f)
    known_files = {it["file"] for it in items}

    files = sorted(f for f in os.listdir(MUSIC_DIR) if f.lower().endswith((".mp3", ".wav")))
    present = set(files)

    for it in items:
        if it["file"] not in present:
            print(f"  MISSING file for manifest id '{it['id']}': {it['file']}")

    added = 0
    for fn in files:
        if fn in known_files:
            continue
        dur = duration(os.path.join(MUSIC_DIR, fn))
        track_id = os.path.splitext(fn)[0]
        items.append({
            "id": track_id,
            "file": fn,
            "duration": dur,
            "mood": [],
            "description": "TODO: describe the vibe (used by Cowork to pick a track).",
            "source": "manual",
        })
        added += 1
        print(f"  + {track_id}  ({dur}s)")

    if added:
        with open(MANIFEST, "w") as f:
            json.dump(items, f, indent=2)
        print(f"\nAdded {added} track(s). Fill in mood + description in {MANIFEST}")
    else:
        print("Manifest already in sync — no new tracks.")


if __name__ == "__main__":
    main()
