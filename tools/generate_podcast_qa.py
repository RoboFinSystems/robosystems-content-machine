"""
Generate a two-voice Q&A podcast from a `qa_script` — CNBC-style interviewer + analyst.

Reads `scripts/{TICKER}_qa.json`, synthesizes each turn with ElevenLabs (analyst voice =
ELEVEN_LABS_VOICE_ID, interviewer = ELEVEN_LABS_INTERVIEWER_VOICE_ID or auto-picked), then:
  - concatenates the turns into `{TICKER}_qa_podcast.mp3`  (Spotify / Apple / Amazon)
  - muxes a static background image + the audio into `{TICKER}_qa_podcast.mp4`  (YouTube)

Idempotent: per-turn MP3s are reused unless --force.

Usage:
    uv run python tools/generate_podcast_qa.py TRLV
    uv run python tools/generate_podcast_qa.py TRLV --force
"""

import argparse
import json
import os
import subprocess
import sys

from helpers import get_project_dir, require_env
from generate_voiceover_audio import api_request, generate_audio

# Inter-turn silence (seconds) — natural conversational beat between speakers.
TURN_GAP = 0.45
# Preferred default interviewer voice name (overridden by ELEVEN_LABS_INTERVIEWER_VOICE_ID).
DEFAULT_INTERVIEWER_NAME = "Sarah"


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


def resolve_interviewer_voice(analyst_id):
    """Pick the interviewer voice: env override → named default → first premade != analyst."""
    env_id = os.environ.get("ELEVEN_LABS_INTERVIEWER_VOICE_ID")
    if env_id:
        return env_id, "env (ELEVEN_LABS_INTERVIEWER_VOICE_ID)"

    voices = api_request("/voices", method="GET")
    if not voices or "voices" not in voices:
        print("  Could not list voices and no ELEVEN_LABS_INTERVIEWER_VOICE_ID set.")
        sys.exit(1)
    vs = voices["voices"]

    # Prefer the named default voice (e.g. "Sarah").
    for v in vs:
        if v.get("name", "").split(" ")[0].lower() == DEFAULT_INTERVIEWER_NAME.lower() \
                and v["voice_id"] != analyst_id:
            return v["voice_id"], f"auto: {v['name']}"
    # Fall back to the first premade voice that isn't the analyst.
    for v in vs:
        if v.get("category") == "premade" and v["voice_id"] != analyst_id:
            return v["voice_id"], f"auto (fallback): {v['name']}"
    sys.exit("No usable interviewer voice found.")


def find_background(project_dir, ticker):
    """Background image for the YouTube MP4: dedicated cover → thumbnail → None."""
    candidates = [
        os.path.join(project_dir, "charts", "png", f"{ticker}_podcast_cover.png"),
        os.path.join(project_dir, "charts", "png", f"{ticker}_thumbnail.png"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def generate(project_name, force=False):
    project_dir = get_project_dir(project_name)
    analyst_id = require_env("ELEVEN_LABS_VOICE_ID")

    # Load the qa_script (separate file: scripts/{TICKER}_qa.json).
    scripts_dir = os.path.join(project_dir, "scripts")
    qa_files = [f for f in os.listdir(scripts_dir) if f.endswith("_qa.json")]
    if not qa_files:
        sys.exit(f"No *_qa.json found in {scripts_dir}. Author the Q&A script first.")
    qa_path = os.path.join(scripts_dir, qa_files[0])
    with open(qa_path) as f:
        qa = json.load(f)

    ticker = qa.get("ticker") or project_name
    turns = qa["turns"]
    print(f"Q&A: {ticker} | {len(turns)} turns\n")

    interviewer_id, how = resolve_interviewer_voice(analyst_id)
    print(f"  analyst     voice: ...{analyst_id[-4:]}")
    print(f"  interviewer voice: ...{interviewer_id[-4:]}  [{how}]\n")
    voice_for = {"interviewer": interviewer_id, "analyst": analyst_id}

    audio_dir = os.path.join(project_dir, "videos", "qa_audio")
    os.makedirs(audio_dir, exist_ok=True)

    turn_files = []
    for i, turn in enumerate(turns):
        speaker = turn["speaker"]
        text = turn["text"]
        vid = voice_for.get(speaker)
        if not vid:
            sys.exit(f"Turn {i}: unknown speaker '{speaker}' (expected interviewer|analyst)")
        out = os.path.join(audio_dir, f"{ticker}_qa_turn_{i:02d}_{speaker}.mp3")
        if not force and os.path.exists(out) and os.path.getsize(out) > 0:
            print(f"  Turn {i:02d} ({speaker})... SKIP")
        else:
            print(f"  Turn {i:02d} ({speaker})... ({len(text)} chars)")
            if not generate_audio(vid, text, out):
                sys.exit(f"  -> FAILED on turn {i}")
        turn_files.append(out)

    # Concatenate turns with a small silence between each.
    videos_dir = os.path.join(project_dir, "videos")
    mp3_out = os.path.join(videos_dir, f"{ticker}_qa_podcast.mp3")
    inputs = []
    for tf in turn_files:
        inputs += ["-i", tf]
    pads = ";".join(f"[{i}:a]apad=pad_dur={TURN_GAP}[a{i}]" for i in range(len(turn_files)))
    concat = "".join(f"[a{i}]" for i in range(len(turn_files))) + \
        f"concat=n={len(turn_files)}:v=0:a=1[out]"
    filter_complex = f"{pads};{concat}"
    cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", filter_complex,
           "-map", "[out]", "-c:a", "libmp3lame", "-q:a", "2", mp3_out]
    print("\n  Concatenating turns -> MP3 ...")
    subprocess.run(cmd, check=True, capture_output=True)
    dur = ffprobe_duration(mp3_out)
    print(f"  -> {mp3_out}  ({dur/60:.1f} min)")

    # Mux static background image + audio -> 16:9 MP4 for YouTube.
    bg = find_background(project_dir, ticker)
    mp4_out = os.path.join(videos_dir, f"{ticker}_qa_podcast.mp4")
    if bg:
        vf = ("scale=1920:1080:force_original_aspect_ratio=decrease,"
              "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x0A1F44,setsar=1")
        cmd = ["ffmpeg", "-y", "-loop", "1", "-i", bg, "-i", mp3_out,
               "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
               "-vf", vf, "-r", "2",
               "-c:a", "aac", "-b:a", "192k", "-shortest", mp4_out]
        print("  Muxing background + audio -> MP4 ...")
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"  -> {mp4_out}")
    else:
        print("  (no background image found — skipped MP4; add charts/png/"
              f"{ticker}_thumbnail.png or _podcast_cover.png)")

    print("\nDone.")
    print(f"  Spotify/Apple/Amazon: {mp3_out}")
    if bg:
        print(f"  YouTube:              {mp4_out}")


def main():
    p = argparse.ArgumentParser(description="Generate a two-voice Q&A podcast")
    p.add_argument("project", help="Project name (e.g., TRLV)")
    p.add_argument("--force", action="store_true", help="Regenerate turn audio even if present")
    args = p.parse_args()
    generate(args.project, force=args.force)


if __name__ == "__main__":
    main()
