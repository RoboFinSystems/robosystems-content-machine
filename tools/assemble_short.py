"""
Assemble a footage-free 9:16 teaser Short from the `short` block in scripts/{TICKER}_script.json.

The hero of every frame is a number or a thesis — NOT b-roll. Each caption card becomes a
full 1080x1920 designed beat (navy ground, teal accent, Space Grotesk) with motion (count-up
numbers, slam-ins, staggered facts), classified by content (short_classify.classify_card).

Visuals are rendered by the Playwright renderer (`renderer/`, brand="research"), which mounts
the design-system fonts/primitives in a headless browser — one brand source, shared with the
deck and the showcase series. This replaced the Pillow renderer (short_design.py). Python stays
the orchestrator and owns audio: it generates the VO, picks the music, sets the beat timing,
and muxes the ducked music + VO onto the renderer's silent visual bed.

Layers:
  1. Visual   — renderer/ turns the classified cards → a silent 1080x1920 mp4 (motion bed).
  2. Music    — a track from assets/music/, ducked low under the VO, with fades.
  3. Voiceover — ElevenLabs analyst voice (a dedicated short hook, not a slice of the full VO).

Output: videos/{TICKER}_short.mp4 (1080x1920, H.264/AAC). Rendered locally (free).
Run via:  uv run python tools/assemble_short.py TRLV     (needs `just render-setup` once)
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

from helpers import get_project_dir, require_env
from generate_voiceover_audio import generate_audio
from short_classify import classify_card

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MUSIC_DIR = os.path.join(ROOT, "assets", "music")
RENDERER_CLI = os.path.join(ROOT, "renderer", "src", "cli.mjs")

W, H = 1080, 1920
FPS = 30
MUSIC_VOL = 0.12
VO_VOL = 1.5
VO_DELAY = 0.3         # seconds before VO starts
TAIL = 0.8            # seconds of runtime past the end of VO


def load_manifest(path):
    with open(path) as f:
        return {item["id"]: item for item in json.load(f)}


def select_music(short, manifest):
    """Pick one track: explicit `music` id > `music_mood` tag match > first track."""
    mid = short.get("music")
    if mid:
        if mid not in manifest:
            sys.exit(f"short.music id '{mid}' not in music manifest")
        return manifest[mid]
    items = list(manifest.values())
    if not items:
        sys.exit("No music tracks available (empty manifest).")
    mood = short.get("music_mood")
    if mood:
        want = set(mood)
        best = max(items, key=lambda it: len(want & set(it.get("mood", []))))
        if want & set(best.get("mood", [])):
            return best
        print(f"  WARN: music_mood {sorted(want)} matched no track moods — using first")
    return items[0]


def ffprobe_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True,
    )
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


def plan_beats(cards, runtime):
    """Turn timed cards into [start, end) beats. The first beat starts at t=0 (so the very
    first frame — the feed poster — is a solid branded hook, never black); each later card
    starts at its `at_seconds`, kept strictly increasing and inside the runtime."""
    starts = [0.0]
    for c in cards[1:]:
        s = float(c.get("at_seconds", starts[-1] + 1.0))
        s = min(max(s, starts[-1] + 0.4), runtime - 0.4)   # monotonic, min gap, in-bounds
        starts.append(max(s, starts[-1] + 0.05))
    ends = starts[1:] + [runtime]
    return list(zip(starts, ends))


def card_to_scene(kind, payload, dur_ms):
    """Map a (classify_card archetype, payload) to a renderer scene. `hero`/`stat` are
    renamed to bignum/statpair so they don't collide with the showcase-series scene kinds."""
    base = {"durationMs": dur_ms}
    if kind == "hero":
        return {**base, "kind": "bignum", "number": payload["number"], "label": payload.get("label", "")}
    if kind == "stat":
        return {**base, "kind": "statpair", "a": payload["a"], "b": payload["b"]}
    if kind == "identity":
        return {**base, "kind": "identity", "company": payload["company"],
                "exchange": payload["exchange"], "ticker": payload["ticker"]}
    if kind == "cta":
        return {**base, "kind": "cta", "line": payload["line"],
                "secondary": payload.get("secondary", ""), "handle": payload.get("handle", "")}
    if kind in ("alert", "hook", "headline", "question"):
        return {**base, "kind": kind, "text": payload["text"]}
    return {**base, "kind": "headline", "text": payload.get("text", "")}


def assemble(project_name, production=False, force=False, music_override=None):
    project_dir = get_project_dir(project_name)
    analyst_id = require_env("ELEVEN_LABS_VOICE_ID")

    scripts_dir = os.path.join(project_dir, "scripts")
    script_files = [f for f in os.listdir(scripts_dir) if f.endswith("_script.json")]
    if not script_files:
        sys.exit(f"No *_script.json in {scripts_dir}")
    with open(os.path.join(scripts_dir, script_files[0])) as f:
        script = json.load(f)

    ticker = script["metadata"]["ticker"]
    short = script.get("short")
    if not short:
        sys.exit("No `short` block in the script. Add one (see template/PRODUCTION_CONTRACT.md).")
    cards = short.get("cards") or []
    if not cards:
        sys.exit("short.cards is empty — caption beats are what the short renders.")
    if music_override:
        short = {**short, "music": music_override}

    # --- 1. Voiceover for the short hook ---
    vo_dir = os.path.join(project_dir, "videos", "short_audio")
    os.makedirs(vo_dir, exist_ok=True)
    vo_path = os.path.join(vo_dir, f"{ticker}_short_vo.mp3")
    if force or not (os.path.exists(vo_path) and os.path.getsize(vo_path) > 0):
        print(f"  VO ({len(short['narration'])} chars)...")
        if not generate_audio(analyst_id, short["narration"], vo_path):
            sys.exit("  -> VO generation FAILED")
    else:
        print("  VO... SKIP (exists)")
    vo_dur = ffprobe_duration(vo_path)
    runtime = round(max(float(short.get("duration_target_seconds", 0)), vo_dur + VO_DELAY + TAIL), 2)
    print(f"  VO {vo_dur:.1f}s -> runtime {runtime:.1f}s")

    # --- 2. Music: explicit id > music_mood match > first track ---
    music_manifest = load_manifest(os.path.join(MUSIC_DIR, "manifest.json"))
    music_entry = select_music(short, music_manifest)
    music_path = os.path.join(MUSIC_DIR, music_entry["file"])
    print(f"  Music: {music_entry['id']}")

    # --- 3. Classify each card → a renderer scene; render the silent visual bed ---
    n = len(cards)
    beats = plan_beats(cards, runtime)
    scenes = []
    print("  Beats:")
    for i, (start, end) in enumerate(beats):
        kind, payload = classify_card(cards[i]["text"], i, n)
        scenes.append(card_to_scene(kind, payload, round((end - start) * 1000)))
        print(f"    {i+1}/{n}  [{kind:9}] {start:5.1f}-{end:4.1f}s  {cards[i]['text']!r}")

    spec = {"slug": f"{ticker}_short", "brand": "research",
            "width": W, "height": H, "fps": FPS, "scenes": scenes}

    tmp = tempfile.mkdtemp(prefix=f"{ticker}_short_")
    try:
        spec_path = os.path.join(tmp, "spec.json")
        with open(spec_path, "w") as f:
            json.dump(spec, f)

        print("  Rendering visual bed (Playwright) ...")
        res = subprocess.run(
            ["node", RENDERER_CLI, "short", "--spec", spec_path, "--out", tmp],
            capture_output=True, text=True,
        )
        if res.returncode != 0:
            print(res.stdout[-1500:]); print(res.stderr[-2000:])
            sys.exit("  -> renderer FAILED (did you run `just render-setup`?)")
        print("   ", res.stdout.strip().splitlines()[-1] if res.stdout.strip() else "(rendered)")

        visual = os.path.join(tmp, f"{ticker}_short.mp4")
        if not os.path.exists(visual):
            sys.exit(f"  -> renderer produced no {visual}")
        vdur = ffprobe_duration(visual)

        # --- 4. ffmpeg: mux ducked music + VO onto the visual bed ---
        parts = [
            f"[1:a]atrim=0:{vdur:.2f},asetpts=PTS-STARTPTS,"
            f"afade=t=in:st=0:d=1,afade=t=out:st={max(0, vdur-1.2):.2f}:d=1.2,"
            f"volume={MUSIC_VOL}[mus]",
            f"[2:a]adelay={int(VO_DELAY*1000)}|{int(VO_DELAY*1000)},volume={VO_VOL}[voa]",
            "[mus][voa]amix=inputs=2:duration=longest:normalize=0[aout]",
        ]
        out_dir = os.path.join(project_dir, "videos")
        suffix = f"_{music_override}" if music_override else ""
        out_path = os.path.join(out_dir, f"{ticker}_short{suffix}.mp4")
        cmd = ["ffmpeg", "-y", "-i", visual, "-i", music_path, "-i", vo_path,
               "-filter_complex", ";".join(parts),
               "-map", "0:v", "-map", "[aout]", "-t", f"{vdur:.2f}",
               "-r", str(FPS), "-c:v", "libx264", "-pix_fmt", "yuv420p",
               "-crf", "18" if production else "23", "-preset", "medium",
               "-c:a", "aac", "-b:a", "192k", out_path]
        print("  Muxing audio ...")
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(res.stderr[-2500:])
            sys.exit("  -> ffmpeg FAILED")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    dur = ffprobe_duration(out_path)
    size_mb = os.path.getsize(out_path) / 1e6
    print(f"\nDone. {out_path}  ({dur:.1f}s, {size_mb:.1f} MB, {W}x{H})")


def main():
    p = argparse.ArgumentParser(description="Assemble a footage-free 9:16 teaser Short")
    p.add_argument("project", help="Project name (e.g., TRLV)")
    p.add_argument("--production", action="store_true", help="Higher quality (crf 18)")
    p.add_argument("--force", action="store_true", help="Regenerate the short VO")
    p.add_argument("--music", default=None, help="Override the music track id (output named _<id>; for A/B)")
    args = p.parse_args()
    assemble(args.project, production=args.production, force=args.force, music_override=args.music)


if __name__ == "__main__":
    main()
