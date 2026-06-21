"""
Assemble a 9:16 teaser Short from the `short` block in scripts/{TICKER}_script.json.

Layers (bottom -> top):
  1. B-roll bed   — clips resolved from assets/broll/manifest.json, scaled/cropped to 1080x1920.
  2. Music        — a track from assets/music/, ducked low under the VO, with fades.
  3. Voiceover    — ElevenLabs, the analyst voice (a dedicated short hook, not a slice of the full VO).
  4. Caption cards — curated PNG overlays (Space Grotesk), timed to VO beats. Stand alone sound-off.

Output: videos/{TICKER}_short.mp4 (1080x1920, H.264/AAC). Rendered locally with ffmpeg (free).

Requires Pillow for the cards — run via:  uv run --with pillow python tools/assemble_short.py TRLV
"""

import argparse
import json
import math
import os
import subprocess
import sys
import tempfile

from helpers import get_project_dir, require_env
from generate_voiceover_audio import generate_audio

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BROLL_DIR = os.path.join(ROOT, "assets", "broll")
MUSIC_DIR = os.path.join(ROOT, "assets", "music")

W, H = 1080, 1920
FPS = 30
MUSIC_VOL = 0.15
VO_VOL = 1.5
VO_DELAY = 0.3          # seconds before VO starts
TAIL = 0.8             # seconds of runtime past the end of VO
CARD_HOLD = 4.2        # seconds each card stays on screen

NAVY = (10, 31, 68, 235)
ACCENT = (0, 209, 178)  # teal underline
WHITE = (255, 255, 255, 255)

FONT_CANDIDATES = [
    os.path.expanduser("~/Library/Fonts/SpaceGrotesk-VariableFont_wght.ttf"),
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]


def load_manifest(path):
    with open(path) as f:
        return {item["id"]: item for item in json.load(f)}


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


def _font(size):
    from PIL import ImageFont
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            font = ImageFont.truetype(path, size)
            try:
                font.set_variation_by_axes([700])  # bold weight on the variable font
            except Exception:
                pass
            return font
    return ImageFont.load_default()


def _wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def render_card(text, out_path):
    """Full-canvas transparent PNG with a centered lower-third caption card."""
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = _font(76)
    max_text_w = W - 200
    lines = _wrap(draw, text, font, max_text_w)

    line_h = font.getbbox("Ag")[3] - font.getbbox("Ag")[1]
    gap = 18
    text_h = len(lines) * line_h + (len(lines) - 1) * gap
    text_w = max(draw.textlength(ln, font=font) for ln in lines)

    pad_x, pad_y = 56, 44
    box_w = text_w + 2 * pad_x
    box_h = text_h + 2 * pad_y
    box_x = (W - box_w) / 2
    box_y = H * 0.62  # lower third

    draw.rounded_rectangle(
        [box_x, box_y, box_x + box_w, box_y + box_h], radius=28, fill=NAVY)
    # accent underline
    draw.rounded_rectangle(
        [box_x + pad_x, box_y + box_h - 10, box_x + pad_x + min(140, text_w),
         box_y + box_h - 4], radius=3, fill=ACCENT)

    y = box_y + pad_y
    for ln in lines:
        lw = draw.textlength(ln, font=font)
        draw.text(((W - lw) / 2, y), ln, font=font, fill=WHITE)
        y += line_h + gap

    img.save(out_path)


def assemble(project_name, production=False, force=False):
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
    runtime = max(float(short.get("duration_target_seconds", 0)), vo_dur + VO_DELAY + TAIL)
    runtime = round(runtime, 2)
    print(f"  VO {vo_dur:.1f}s -> runtime {runtime:.1f}s")

    # --- 2. Resolve b-roll into slots covering the runtime ---
    broll_manifest = load_manifest(os.path.join(BROLL_DIR, "manifest.json"))
    ids = short["broll"]
    clip_max = min(broll_manifest[i]["duration"] for i in ids)
    n_slots = len(ids)
    while runtime / n_slots > clip_max:
        n_slots += len(ids)
    per_slot = runtime / n_slots
    slot_files = [os.path.join(BROLL_DIR, broll_manifest[ids[k % len(ids)]]["file"])
                  for k in range(n_slots)]
    print(f"  B-roll: {n_slots} slots x {per_slot:.2f}s")

    # --- 3. Music ---
    music_manifest = load_manifest(os.path.join(MUSIC_DIR, "manifest.json"))
    music_id = short.get("music") or next(iter(music_manifest))
    music_path = os.path.join(MUSIC_DIR, music_manifest[music_id]["file"])

    # --- 4. Caption cards -> PNGs ---
    tmpdir = tempfile.mkdtemp(prefix=f"{ticker}_short_")
    cards = short.get("cards", [])
    card_files = []
    for j, c in enumerate(cards):
        p = os.path.join(tmpdir, f"card_{j}.png")
        render_card(c["text"], p)
        card_files.append((p, float(c["at_seconds"])))

    # --- Build the ffmpeg graph ---
    inputs = []
    for sf in slot_files:
        inputs += ["-i", sf]                 # 0 .. n_slots-1
    inputs += ["-i", music_path]             # idx_music
    inputs += ["-i", vo_path]                # idx_vo
    idx_music = n_slots
    idx_vo = n_slots + 1
    for (p, _) in card_files:
        inputs += ["-loop", "1", "-i", p]    # idx_card_base + j
    idx_card_base = n_slots + 2

    parts = []
    for k in range(n_slots):
        parts.append(
            f"[{k}:v]trim=0:{per_slot:.3f},setpts=PTS-STARTPTS,"
            f"scale={W}:{H}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H},fps={FPS},setsar=1,format=yuv420p[v{k}]")
    concat = "".join(f"[v{k}]" for k in range(n_slots)) + \
        f"concat=n={n_slots}:v=1:a=0[bed]"
    parts.append(concat)

    cur = "bed"
    for j, (_, at) in enumerate(card_files):
        end = min(at + CARD_HOLD, runtime)
        ov = f"ov{j}"
        parts.append(
            f"[{cur}][{idx_card_base + j}:v]overlay=0:0:"
            f"enable='between(t,{at:.2f},{end:.2f})'[{ov}]")
        cur = ov
    video_label = cur

    parts.append(
        f"[{idx_music}:a]atrim=0:{runtime:.2f},asetpts=PTS-STARTPTS,"
        f"afade=t=in:st=0:d=1,afade=t=out:st={max(0, runtime-1.2):.2f}:d=1.2,"
        f"volume={MUSIC_VOL}[mus]")
    parts.append(
        f"[{idx_vo}:a]adelay={int(VO_DELAY*1000)}|{int(VO_DELAY*1000)},"
        f"volume={VO_VOL}[voa]")
    parts.append("[mus][voa]amix=inputs=2:duration=longest:normalize=0[aout]")

    filtergraph = ";".join(parts)

    out_dir = os.path.join(project_dir, "videos")
    out_path = os.path.join(out_dir, f"{ticker}_short.mp4")
    cmd = ["ffmpeg", "-y", *inputs,
           "-filter_complex", filtergraph,
           "-map", f"[{video_label}]", "-map", "[aout]",
           "-t", f"{runtime:.2f}",
           "-r", str(FPS), "-c:v", "libx264", "-pix_fmt", "yuv420p",
           "-crf", "18" if production else "23", "-preset", "medium",
           "-c:a", "aac", "-b:a", "192k", out_path]
    print("  Rendering 9:16 short with ffmpeg ...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stderr[-2000:])
        sys.exit("  -> ffmpeg FAILED")
    dur = ffprobe_duration(out_path)
    size_mb = os.path.getsize(out_path) / 1e6
    print(f"\nDone. {out_path}  ({dur:.1f}s, {size_mb:.1f} MB, {W}x{H})")


def main():
    p = argparse.ArgumentParser(description="Assemble a 9:16 teaser Short")
    p.add_argument("project", help="Project name (e.g., TRLV)")
    p.add_argument("--production", action="store_true", help="Higher quality (crf 18)")
    p.add_argument("--force", action="store_true", help="Regenerate the short VO")
    args = p.parse_args()
    assemble(args.project, production=args.production, force=args.force)


if __name__ == "__main__":
    main()
