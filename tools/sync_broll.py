"""
Sync assets/broll/manifest.json with the .mp4 files actually present.

Drop new clips into assets/broll/ (produced in ElevenLabs Studio / Veo — there is no
video-generation API), then run this. It probes each new clip and appends a manifest entry
with a placeholder description for you to fill in. Existing entries are left untouched.

Usage:
    uv run python tools/sync_broll.py
"""

import json
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BROLL_DIR = os.path.join(ROOT, "assets", "broll")
MANIFEST = os.path.join(BROLL_DIR, "manifest.json")


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,r_frame_rate",
         "-show_entries", "format=duration",
         "-of", "json", path],
        capture_output=True, text=True,
    )
    info = json.loads(out.stdout)
    st = (info.get("streams") or [{}])[0]
    w, h = st.get("width"), st.get("height")
    rfr = st.get("r_frame_rate", "0/1")
    try:
        num, den = rfr.split("/")
        fps = round(float(num) / float(den)) if float(den) else None
    except Exception:
        fps = None
    dur = round(float(info.get("format", {}).get("duration", 0)), 1)
    return w, h, fps, dur


def main():
    items = []
    if os.path.exists(MANIFEST):
        with open(MANIFEST) as f:
            items = json.load(f)
    known_files = {it["file"] for it in items}

    files = sorted(f for f in os.listdir(BROLL_DIR) if f.lower().endswith((".mp4", ".mov")))

    # Flag manifest entries whose file is gone.
    present = set(files)
    for it in items:
        if it["file"] not in present:
            print(f"  MISSING file for manifest id '{it['id']}': {it['file']}")

    added = 0
    for fn in files:
        if fn in known_files:
            continue
        w, h, fps, dur = probe(os.path.join(BROLL_DIR, fn))
        clip_id = os.path.splitext(fn)[0]
        items.append({
            "id": clip_id,
            "file": fn,
            "duration": dur,
            "resolution": f"{w}x{h}",
            "fps": fps,
            "tags": [],
            "description": "TODO: describe the shot (used by Cowork to pick clips by tag/description).",
        })
        added += 1
        print(f"  + {clip_id}  ({w}x{h}, {dur}s)")

    if added:
        with open(MANIFEST, "w") as f:
            json.dump(items, f, indent=2)
        print(f"\nAdded {added} clip(s). Fill in tags + description in {MANIFEST}")
    else:
        print("Manifest already in sync — no new clips.")


if __name__ == "__main__":
    main()
