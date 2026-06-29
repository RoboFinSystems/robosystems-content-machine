"""
Assemble a footage-free 9:16 teaser Short from the `short` block in scripts/{TICKER}_script.json.

The hero of every frame is a number or a thesis — NOT b-roll. Each caption card becomes a
full 1080x1920 designed beat (navy ground, teal accent, Space Grotesk) rendered with motion
(count-up numbers, slam-ins, staggered facts), classified by content (see short_design.py).
This replaces the old shared-b-roll renderer, whose clips were a common pool — so every
ticker's Short came out looking the same. Now each Short is the company's own data.

Layers:
  1. Frames   — short_design.render_frame() per beat; rendered to PNG sequences + held stills.
  2. Music    — a track from assets/music/, ducked low under the VO, with fades (kept: energy).
  3. Voiceover — ElevenLabs analyst voice (a dedicated short hook, not a slice of the full VO).

Output: videos/{TICKER}_short.mp4 (1080x1920, H.264/AAC). Rendered locally with ffmpeg (free).
Run via:  uv run --with pillow python tools/assemble_short.py TRLV
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
from short_design import W, H, render_frame, classify_card, lerp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MUSIC_DIR = os.path.join(ROOT, "assets", "music")

FPS = 30
ENTRANCE = 0.5         # seconds of entrance animation per beat
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
        sys.exit("short.cards is empty — caption beats are what the deck renders.")
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

    # --- 3. Render each beat to a PNG entrance sequence + a held still ---
    n = len(cards)
    beats = plan_beats(cards, runtime)
    tmp = tempfile.mkdtemp(prefix=f"{ticker}_short_")
    inputs, vstreams, idx = [], [], 0
    print("  Rendering frames:")
    try:
        for i, (start, end) in enumerate(beats):
            kind, payload = classify_card(cards[i]["text"], i, n)
            dur = max(1 / FPS, end - start)
            total = max(1, round(dur * FPS))
            e_frames = min(total, max(1, round(ENTRANCE * FPS)))
            hold = total - e_frames
            t0 = 0.75 if i == 0 else 0.0     # open mid-entrance so the poster frame reads
            for fr in range(e_frames):
                t = lerp(t0, 1.0, (fr + 1) / e_frames)
                render_frame(kind, payload, t).save(os.path.join(tmp, f"b{i}_e_{fr:04d}.png"))
            inputs += ["-framerate", str(FPS), "-i", os.path.join(tmp, f"b{i}_e_%04d.png")]
            vstreams.append(idx); idx += 1
            if hold > 0:
                render_frame(kind, payload, 1.0).save(os.path.join(tmp, f"b{i}_s.png"))
                inputs += ["-loop", "1", "-framerate", str(FPS), "-t", f"{hold / FPS:.3f}",
                           "-i", os.path.join(tmp, f"b{i}_s.png")]
                vstreams.append(idx); idx += 1
            print(f"    {i+1}/{n}  [{kind:9}] {start:5.1f}-{end:4.1f}s  {cards[i]['text']!r}")

        inputs += ["-i", music_path]; idx_music = idx; idx += 1
        inputs += ["-i", vo_path];    idx_vo = idx; idx += 1

        # --- 4. ffmpeg: concat the beat streams, mix ducked music + VO ---
        parts = [f"[{k}:v]fps={FPS},format=yuv420p,setsar=1[v{k}]" for k in vstreams]
        parts.append("".join(f"[v{k}]" for k in vstreams) +
                     f"concat=n={len(vstreams)}:v=1:a=0[bed]")
        parts.append(
            f"[{idx_music}:a]atrim=0:{runtime:.2f},asetpts=PTS-STARTPTS,"
            f"afade=t=in:st=0:d=1,afade=t=out:st={max(0, runtime-1.2):.2f}:d=1.2,"
            f"volume={MUSIC_VOL}[mus]")
        parts.append(
            f"[{idx_vo}:a]adelay={int(VO_DELAY*1000)}|{int(VO_DELAY*1000)},volume={VO_VOL}[voa]")
        parts.append("[mus][voa]amix=inputs=2:duration=longest:normalize=0[aout]")
        filtergraph = ";".join(parts)

        out_dir = os.path.join(project_dir, "videos")
        suffix = f"_{music_override}" if music_override else ""
        out_path = os.path.join(out_dir, f"{ticker}_short{suffix}.mp4")
        cmd = ["ffmpeg", "-y", *inputs,
               "-filter_complex", filtergraph,
               "-map", "[bed]", "-map", "[aout]",
               "-t", f"{runtime:.2f}",
               "-r", str(FPS), "-c:v", "libx264", "-pix_fmt", "yuv420p",
               "-crf", "18" if production else "23", "-preset", "medium",
               "-c:a", "aac", "-b:a", "192k", out_path]
        print("  Encoding 9:16 short with ffmpeg ...")
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
