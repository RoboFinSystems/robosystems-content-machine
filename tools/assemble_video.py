"""
Assemble the final video from avatar segments, chart PNGs, and voiceover audio
using the Shotstack Edit API.

Flow:
  1. Upload assets to S3 and generate presigned URLs
  2. Build a timeline JSON from the script
  3. Submit render to Shotstack
  4. Poll for completion and download

Usage:
    uv run python tools/assemble_video.py JPM_2025_10_K

    # Build edit JSON only (no render)
    uv run python tools/assemble_video.py JPM_2025_10_K --edit-only

    # Check render status
    uv run python tools/assemble_video.py JPM_2025_10_K --status RENDER_ID

Requires: AWS CLI configured, SHOTSTACK_API_KEY in .env
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error

from helpers import get_project_dir, require_env

S3_BUCKET = require_env("S3_BUCKET")
S3_REGION = os.environ.get("S3_REGION", "us-east-1")
EDIT_BASE = "https://api.shotstack.io/edit/stage"


def shotstack_request(method, path, data=None):
    url = f"{EDIT_BASE}{path}"
    headers = {
        "x-api-key": require_env("SHOTSTACK_API_KEY"),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"  Shotstack API Error {e.code}: {error_body[:500]}")
        return None


# ─── S3 Asset Management ───────────────────────────────────────

def s3_presign(s3_key, expires=3600):
    """Generate a presigned URL for an S3 object (valid 1 hour)."""
    result = subprocess.run(
        [
            "aws", "s3", "presign",
            f"s3://{S3_BUCKET}/{s3_key}",
            "--expires-in", str(expires),
            "--region", S3_REGION,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"  Presign failed for {s3_key}: {result.stderr}")
        return None
    return result.stdout.strip()


def s3_upload(local_path, s3_key):
    """Upload a local file to S3."""
    result = subprocess.run(
        ["aws", "s3", "cp", local_path, f"s3://{S3_BUCKET}/{s3_key}", "--quiet"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def check_aws_credentials():
    """Verify AWS credentials are available before doing anything."""
    result = subprocess.run(
        ["aws", "sts", "get-caller-identity", "--query", "Account", "--output", "text"],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode != 0:
        print("ERROR: AWS credentials not configured.")
        print("  The assemble step needs AWS access to upload assets to S3.")
        print("  Options:")
        print("    1. Set AWS_PROFILE in your .env file")
        print("    2. Export AWS credentials: export AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=...")
        print("    3. Run from a directory with direnv configured")
        sys.exit(1)


def _get_s3_prefix(project_dir):
    """Derive S3 prefix from the project directory name."""
    return os.path.basename(project_dir)


def build_asset_manifest(project_dir, ticker):
    """Upload local assets to S3 and build manifest with presigned URLs."""
    manifest_path = os.path.join(project_dir, "videos", "shotstack_assets.json")

    # Check for fresh manifest (presigned URLs valid for 1 hour)
    if os.path.exists(manifest_path):
        with open(manifest_path) as f:
            existing = json.load(f)
        created = existing.get("_created", 0)
        if time.time() - created < 3000:  # Less than 50 min old
            print(f"Using cached manifest ({len(existing) - 1} assets, still fresh)")
            return existing

    s3_prefix = _get_s3_prefix(project_dir)
    assets = {"_created": time.time()}

    # Avatar MP4s (skip _original backups from padding step)
    videos_dir = os.path.join(project_dir, "videos")
    for f in sorted(os.listdir(videos_dir)):
        if f.startswith(f"{ticker}_segment_") and f.endswith(".mp4") and "_original" not in f:
            local_path = os.path.join(videos_dir, f)
            s3_key = f"{s3_prefix}/videos/{f}"
            print(f"  Uploading {f}...", end=" ")
            if s3_upload(local_path, s3_key):
                url = s3_presign(s3_key)
                if url:
                    assets[f] = {"type": "video", "url": url, "s3_key": s3_key}
                    print("OK")
                else:
                    print("presign failed")
            else:
                print("upload failed")

    # Voiceover MP3s
    audio_dir = os.path.join(project_dir, "videos", "audio")
    if os.path.isdir(audio_dir):
        for f in sorted(os.listdir(audio_dir)):
            if f.endswith("_voiceover.mp3"):
                local_path = os.path.join(audio_dir, f)
                s3_key = f"{s3_prefix}/audio/{f}"
                print(f"  Uploading {f}...", end=" ")
                if s3_upload(local_path, s3_key):
                    url = s3_presign(s3_key)
                    if url:
                        assets[f] = {"type": "audio", "url": url, "s3_key": s3_key}
                        print("OK")
                    else:
                        print("presign failed")
                else:
                    print("upload failed")

    # Chart PNGs
    png_dir = os.path.join(project_dir, "charts", "png")
    if os.path.isdir(png_dir):
        for f in sorted(os.listdir(png_dir)):
            if f.endswith(".png") and not f.startswith(f"{ticker}_thumbnail"):
                local_path = os.path.join(png_dir, f)
                s3_key = f"{s3_prefix}/charts/{f}"
                print(f"  Uploading {f}...", end=" ")
                if s3_upload(local_path, s3_key):
                    url = s3_presign(s3_key)
                    if url:
                        assets[f] = {"type": "image", "url": url, "s3_key": s3_key}
                        print("OK")
                    else:
                        print("presign failed")
                else:
                    print("upload failed")

    # Intro/outro slides — check project charts/png/ first (campaign overrides),
    # then fall back to template directory
    tools_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(tools_dir)
    for slide_name in ("intro_slide", "outro_slide"):
        slide_png = f"{slide_name}.png"
        # Prefer project-local (screenshotted from campaign override HTML)
        slide_path = os.path.join(project_dir, "charts", "png", f"INTRO_SLIDE.png" if "intro" in slide_name else "OUTRO_SLIDE.png")
        if not os.path.exists(slide_path):
            slide_path = os.path.join(root_dir, "template", "charts", "png", slide_png)
        if os.path.exists(slide_path):
            s3_key = f"{s3_prefix}/slides/{slide_png}"
            print(f"  Uploading {slide_png}...", end=" ")
            if s3_upload(slide_path, s3_key):
                url = s3_presign(s3_key)
                if url:
                    assets[slide_png] = {"type": "image", "url": url, "s3_key": s3_key}
                    print("OK")
                else:
                    print("presign failed")
            else:
                print("upload failed")

    # Save manifest
    with open(manifest_path, "w") as f:
        json.dump(assets, f, indent=2)

    asset_count = len([k for k in assets if not k.startswith("_")])
    print(f"\nUploaded and presigned {asset_count} assets")
    return assets


# ─── Avatar Segment Padding ────────────────────────────────────

def pad_avatar_segment(project_dir, ticker, seg_id, pad_seconds=0.4):
    """Pad an avatar segment with black/silence to prevent codec startup glitch.

    Shotstack's renderer produces an audio pop/glitch when a video clip starts.
    Adding a short black+silent lead-in avoids this.
    Skips if already padded (checks for _original backup file).
    """
    videos_dir = os.path.join(project_dir, "videos")
    segment_file = os.path.join(videos_dir, f"{ticker}_segment_{seg_id}.mp4")
    original_file = os.path.join(videos_dir, f"{ticker}_segment_{seg_id}_original.mp4")

    if not os.path.exists(segment_file):
        return

    # Skip if already padded
    if os.path.exists(original_file):
        return True  # already done

    import shutil
    shutil.copy2(segment_file, original_file)

    delay_ms = int(pad_seconds * 1000)
    padded_tmp = segment_file + ".tmp.mp4"

    result = subprocess.run(
        [
            "ffmpeg", "-y", "-i", original_file,
            "-vf", f"tpad=start_duration={pad_seconds}:start_mode=clone",
            "-af", f"adelay={delay_ms}|{delay_ms}",
            "-c:v", "libx264", "-c:a", "aac",
            padded_tmp,
        ],
        capture_output=True, text=True, timeout=60,
    )

    if result.returncode == 0:
        os.replace(padded_tmp, segment_file)
        new_dur = _ffprobe_duration(segment_file)
        print(f"  Padded segment {seg_id}: +{pad_seconds}s → {new_dur:.2f}s")
        return new_dur
    else:
        print(f"  Warning: ffmpeg padding failed for segment {seg_id}: {result.stderr[:200]}")
        if os.path.exists(padded_tmp):
            os.remove(padded_tmp)
        return None


def pad_all_avatar_segments(project_dir, ticker, segments, pad_seconds=0.4):
    """Pad all avatar segments and update media_durations.json."""
    avatar_ids = [s["id"] for s in segments if s["type"] == "avatar"]
    if not avatar_ids:
        return

    print(f"\nPadding {len(avatar_ids)} avatar segments (+{pad_seconds}s each)...")
    durations_path = os.path.join(project_dir, "videos", "media_durations.json")
    durations_data = None
    if os.path.exists(durations_path):
        with open(durations_path) as f:
            durations_data = json.load(f)

    padded_count = 0
    skipped_count = 0
    for seg_id in avatar_ids:
        result = pad_avatar_segment(project_dir, ticker, seg_id, pad_seconds)
        if result is True:
            skipped_count += 1
        elif result and durations_data:
            durations_data.get("videos", {})[str(seg_id)] = round(result, 4)
            padded_count += 1

    if padded_count > 0 and durations_data:
        with open(durations_path, "w") as f:
            json.dump(durations_data, f, indent=2)

    if skipped_count == len(avatar_ids):
        print(f"  All {len(avatar_ids)} segments already padded")
    elif padded_count > 0:
        print(f"  Padded {padded_count} segments, {skipped_count} already done")


# ─── Timeline Builder ───────────────────────────────────────────

def get_media_durations(project_dir):
    """Get actual media durations from media_durations.json or via ffprobe."""
    durations_path = os.path.join(project_dir, "videos", "media_durations.json")

    if os.path.exists(durations_path):
        with open(durations_path) as f:
            data = json.load(f)
        return data.get("videos", {}), data.get("audio", {})

    # Generate via ffprobe if not cached
    videos, audio = {}, {}

    videos_dir = os.path.join(project_dir, "videos")
    for f in os.listdir(videos_dir):
        if f.endswith(".mp4") and "segment" in f:
            seg = f.split("segment_")[1].replace(".mp4", "")
            dur = _ffprobe_duration(os.path.join(videos_dir, f))
            if dur:
                videos[seg] = dur

    audio_dir = os.path.join(project_dir, "videos", "audio")
    if os.path.isdir(audio_dir):
        for f in os.listdir(audio_dir):
            if f.endswith(".mp3"):
                seg = f.split("segment_")[1].replace("_voiceover.mp3", "")
                dur = _ffprobe_duration(os.path.join(audio_dir, f))
                if dur:
                    audio[seg] = dur

    # Cache
    with open(durations_path, "w") as f:
        json.dump({"videos": videos, "audio": audio}, f, indent=2)

    return videos, audio


def _ffprobe_duration(filepath):
    """Get duration of a media file via ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", filepath],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return float(data["format"]["duration"])
    except Exception:
        pass
    return None


def _srt_timestamp(seconds):
    """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _parse_srt_timestamp(ts):
    """Parse SRT timestamp (HH:MM:SS,mmm) to seconds."""
    ts = ts.strip().replace(",", ".")
    parts = ts.split(":")
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])


def _parse_srt(srt_path):
    """Parse an SRT file into a list of (start_seconds, end_seconds, text) tuples."""
    entries = []
    with open(srt_path) as f:
        content = f.read().strip()
    if not content:
        return entries

    blocks = content.split("\n\n")
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue
        # lines[0] = sequence number, lines[1] = timestamps, lines[2:] = text
        timestamps = lines[1]
        if " --> " not in timestamps:
            continue
        start_str, end_str = timestamps.split(" --> ")
        start = _parse_srt_timestamp(start_str)
        end = _parse_srt_timestamp(end_str)
        text = " ".join(lines[2:])
        entries.append((start, end, text))
    return entries


def _whisper_transcribe(audio_path):
    """Run Whisper on an audio file and return the generated SRT path."""
    srt_path = os.path.splitext(audio_path)[0] + ".srt"
    if os.path.exists(srt_path):
        return srt_path

    output_dir = os.path.dirname(audio_path)
    result = subprocess.run(
        [
            "whisper", audio_path,
            "--model", "base",
            "--language", "en",
            "--output_format", "srt",
            "--output_dir", output_dir,
        ],
        capture_output=True, text=True, timeout=180,
    )
    if result.returncode == 0 and os.path.exists(srt_path):
        return srt_path
    else:
        print(f"    Whisper failed for {os.path.basename(audio_path)}: {result.stderr[:200]}")
        return None


def _whisper_transcribe_all(project_dir, ticker, segments):
    """Run Whisper on all avatar MP4s and voiceover MP3s, return map of seg_id -> srt_path."""
    srt_map = {}
    videos_dir = os.path.join(project_dir, "videos")
    audio_dir = os.path.join(project_dir, "videos", "audio")

    for seg in segments:
        seg_id = seg["id"]
        seg_type = seg["type"]

        if seg_type == "avatar":
            audio_path = os.path.join(videos_dir, f"{ticker}_segment_{seg_id}.mp4")
        elif seg_type == "visual":
            audio_path = os.path.join(audio_dir, f"{ticker}_segment_{seg_id}_voiceover.mp3")
        else:
            continue

        if not os.path.exists(audio_path):
            continue

        print(f"  Seg {seg_id} ({seg_type})...", end=" ")
        srt_path = _whisper_transcribe(audio_path)
        if srt_path:
            srt_map[seg_id] = srt_path
            print("OK")
        else:
            print("FAILED")

    return srt_map


def _write_srt(path, entries, whisper_srts=None):
    """Write SRT subtitle file.

    If whisper_srts is provided (map of seg_id -> srt_path), uses Whisper's
    word-accurate timestamps offset by each segment's timeline position.
    Falls back to proportional chunking for segments without Whisper data.
    """
    seq = 1
    with open(path, "w") as f:
        for entry in entries:
            seg_id = entry.get("seg_id")
            timeline_offset = entry["start"]

            # Try Whisper SRT first
            if whisper_srts and seg_id in whisper_srts:
                whisper_entries = _parse_srt(whisper_srts[seg_id])
                for w_start, w_end, w_text in whisper_entries:
                    f.write(f"{seq}\n")
                    f.write(f"{_srt_timestamp(timeline_offset + w_start)} --> {_srt_timestamp(timeline_offset + w_end)}\n")
                    f.write(f"{w_text}\n\n")
                    seq += 1
                continue

            # Fallback: proportional chunking
            words = entry["text"].split()
            chunk_size = 10
            chunks = [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]
            if not chunks:
                continue

            total_duration = entry["end"] - entry["start"]
            chunk_duration = total_duration / len(chunks)

            for j, chunk in enumerate(chunks):
                start = entry["start"] + j * chunk_duration
                end = start + chunk_duration
                f.write(f"{seq}\n")
                f.write(f"{_srt_timestamp(start)} --> {_srt_timestamp(end)}\n")
                f.write(f"{chunk}\n\n")
                seq += 1


def normalize_audio(video_path):
    """Apply loudnorm audio normalization to the final video via ffmpeg."""
    normalized_path = video_path.replace(".mp4", "_normalized.mp4")
    print("\nNormalizing audio levels...")

    result = subprocess.run(
        [
            "ffmpeg", "-y", "-i", video_path,
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            normalized_path,
        ],
        capture_output=True, text=True, timeout=120,
    )

    if result.returncode == 0:
        os.replace(normalized_path, video_path)
        size_mb = os.path.getsize(video_path) / (1024 * 1024)
        print(f"  Audio normalized ({size_mb:.1f}MB)")
        return True
    else:
        print(f"  Warning: Audio normalization failed: {result.stderr[:200]}")
        if os.path.exists(normalized_path):
            os.remove(normalized_path)
        return False


def build_timeline(project_dir, ticker, assets):
    """Build the Shotstack timeline JSON from the script and uploaded assets."""
    script_path = os.path.join(project_dir, "scripts", f"{ticker}_script.json")
    with open(script_path) as f:
        script = json.load(f)

    segments = script["segments"]

    # Detect mode
    has_avatar = any(s["type"] == "avatar" for s in segments)

    # Pad all avatar segments to prevent codec startup audio glitch (mixed mode only)
    if has_avatar:
        pad_all_avatar_segments(project_dir, ticker, segments)

    # Map visual_ref to chart PNG filenames
    chart_map = {}
    for chart in script.get("charts", []):
        ref = chart["ref"]
        chart_map[ref] = f"{ref}.png"

    # Get ACTUAL durations (not estimates) — read AFTER padding so duration is current
    video_durations, audio_durations = get_media_durations(project_dir)

    print("\nSegment durations (actual):")

    # Build clips in sequence
    SEGMENT_GAP = 0.3   # seconds of black between segments
    INTRO_DURATION = 4   # seconds for intro slide
    OUTRO_DURATION = 5   # seconds for outro slide
    video_clips = []
    audio_clips = []
    srt_entries = []      # for subtitle generation
    current_time = 0.0

    # ── Intro slide ──
    intro_info = assets.get("intro_slide.png")
    if intro_info:
        video_clips.append({
            "asset": {"type": "image", "src": intro_info["url"]},
            "start": 0,
            "length": INTRO_DURATION,
            "transition": {"in": "fade", "out": "fade"},
        })
        current_time = INTRO_DURATION + SEGMENT_GAP
        print(f"  Intro: {INTRO_DURATION}s")
    else:
        current_time = SEGMENT_GAP

    # ── Content segments ──
    subtitles_on = os.environ.get("SUBTITLES", "true").lower() in ("true", "1", "yes")
    srt_index = 1
    for i, seg in enumerate(segments):
        seg_id = seg["id"]
        seg_type = seg["type"]

        if seg_type == "avatar" and has_avatar:
            # Mixed mode: avatar segment with HeyGen video
            video_file = f"{ticker}_segment_{seg_id}.mp4"
            asset_info = assets.get(video_file)
            if not asset_info:
                print(f"  Warning: No asset for {video_file}, skipping")
                continue

            duration = video_durations.get(str(seg_id), seg["duration_estimate_seconds"])
            print(f"  Seg {seg_id} (avatar): {duration:.1f}s")

            avatar_clip = {
                "asset": {
                    "type": "video",
                    "src": asset_info["url"],
                    "volume": 1.0,
                },
                "start": round(current_time, 2),
                "length": round(duration, 2),
                "transition": {"in": "fade"},
            }
            video_clips.append(avatar_clip)

            srt_entries.append({
                "seg_id": seg_id,
                "index": srt_index,
                "start": current_time,
                "end": current_time + duration,
                "text": seg.get("narration", ""),
            })
            srt_index += 1
            current_time += duration + SEGMENT_GAP

        elif seg_type == "visual":
            # Visual segment: slide PNG + voiceover audio
            visual_ref = seg.get("visual_ref", "")
            chart_file = chart_map.get(visual_ref)
            audio_file = f"{ticker}_segment_{seg_id}_voiceover.mp3"

            audio_info = assets.get(audio_file)
            chart_info = assets.get(chart_file) if chart_file else None

            if not audio_info:
                print(f"  Warning: No audio for segment {seg_id}, skipping")
                continue

            duration = audio_durations.get(str(seg_id), seg["duration_estimate_seconds"])
            slide_type = seg.get("visual_type", "chart")
            print(f"  Seg {seg_id} ({slide_type}): {duration:.1f}s")

            if chart_info:
                video_clips.append({
                    "asset": {"type": "image", "src": chart_info["url"]},
                    "start": round(current_time, 2),
                    "length": round(duration, 2),
                    "transition": {"in": "fade"},
                })

            audio_clip = {
                "asset": {
                    "type": "audio",
                    "src": audio_info["url"],
                    "volume": 1.0,
                },
                "start": round(current_time, 2),
                "length": round(duration, 2),
            }
            audio_clips.append(audio_clip)

            srt_entries.append({
                "seg_id": seg_id,
                "index": srt_index,
                "start": current_time,
                "end": current_time + duration,
                "text": seg.get("narration", ""),
            })
            srt_index += 1
            current_time += duration + SEGMENT_GAP

    # ── Outro slide ──
    outro_info = assets.get("outro_slide.png")
    if outro_info:
        video_clips.append({
            "asset": {"type": "image", "src": outro_info["url"]},
            "start": round(current_time, 2),
            "length": OUTRO_DURATION,
            "transition": {"in": "fade", "out": "fade"},
        })
        current_time += OUTRO_DURATION
        print(f"  Outro: {OUTRO_DURATION}s")

    # ── Whisper transcription for accurate subtitle timing ──
    print("\nTranscribing audio with Whisper...")
    whisper_srts = _whisper_transcribe_all(project_dir, ticker, segments)
    print(f"  Whisper: {len(whisper_srts)}/{len(srt_entries)} segments transcribed")

    # ── Generate SRT subtitle file ──
    srt_path = os.path.join(project_dir, "videos", f"{ticker}_captions.srt")
    _write_srt(srt_path, srt_entries, whisper_srts=whisper_srts)
    print(f"  Captions: -> {os.path.basename(srt_path)}")

    # Burn in subtitles via SRT upload to Shotstack
    caption_clips = []
    if subtitles_on:
        caption_style = {
            "font": {
                "color": "#ffffff",
                "family": "Clear Sans",
                "size": 28,
            },
            "background": {
                "color": "#000000",
                "padding": 8,
                "borderRadius": 4,
                "opacity": 0.6,
            },
        }
        s3_prefix = _get_s3_prefix(project_dir)
        srt_s3_key = f"{s3_prefix}/captions/{os.path.basename(srt_path)}"
        if s3_upload(srt_path, srt_s3_key):
            srt_url = s3_presign(srt_s3_key)
            if srt_url:
                caption_clips.append({
                    "asset": {"type": "caption", "src": srt_url, **caption_style},
                    "start": 0,
                    "length": "end",
                })
        print("  Subtitles: ON (Whisper-timed)")
    else:
        print("  Subtitles: OFF")

    # ── Assemble timeline ──
    # Shotstack renders tracks front-to-back: first track = on top
    tracks = []
    if caption_clips:
        tracks.append({"clips": caption_clips})
    tracks.append({"clips": video_clips})
    tracks.append({"clips": audio_clips})

    timeline = {
        "background": "#0a0a0a",
        "tracks": tracks,
    }

    output = {
        "format": "mp4",
        "resolution": "hd",
        "fps": 25,
    }

    edit = {
        "timeline": timeline,
        "output": output,
    }

    # Save edit JSON
    edit_path = os.path.join(project_dir, "videos", "shotstack_edit.json")
    with open(edit_path, "w") as f:
        json.dump(edit, f, indent=2)

    print(f"\nTimeline: {len(video_clips)} video/image clips, {len(audio_clips)} audio clips, {len(caption_clips)} caption tracks")
    print(f"Duration: ~{current_time:.0f}s ({current_time/60:.1f} min)")
    print(f"Edit JSON: {edit_path}")

    return edit


# ─── Render ─────────────────────────────────────────────────────

def submit_render(edit):
    print("\nSubmitting render to Shotstack...")
    resp = shotstack_request("POST", "/render", edit)
    if not resp:
        return None

    render_id = resp.get("response", {}).get("id")
    if render_id:
        print(f"Render queued! ID: {render_id}")
    else:
        print(f"Unexpected response: {json.dumps(resp, indent=2)}")
    return render_id


def poll_render(render_id):
    print(f"\nPolling render {render_id}...")
    for attempt in range(120):
        resp = shotstack_request("GET", f"/render/{render_id}")
        if not resp:
            time.sleep(5)
            continue

        status = resp.get("response", {}).get("status", "unknown")
        print(f"  [{attempt+1}] Status: {status}")

        if status == "done":
            return resp["response"].get("url")
        elif status == "failed":
            error = resp.get("response", {}).get("error")
            print(f"  Render failed: {error}")
            return None

        time.sleep(5)

    print("  Render timed out")
    return None


def download_result(video_url, project_dir, ticker):
    output_path = os.path.join(project_dir, "videos", f"{ticker}_final.mp4")
    print(f"\nDownloading final video...")
    urllib.request.urlretrieve(video_url, output_path)
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Saved: {output_path} ({size_mb:.1f}MB)")
    print(f"Open: open '{output_path}'")
    return output_path


# ─── Main ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Assemble final video via Shotstack")
    parser.add_argument("project", help="Project name (e.g., JPM_2025_10_K)")
    parser.add_argument("--edit-only", action="store_true", help="Build edit JSON only (no render)")
    parser.add_argument("--status", metavar="RENDER_ID", help="Check render status")

    args = parser.parse_args()
    project_dir = get_project_dir(args.project)

    # Find ticker
    scripts_dir = os.path.join(project_dir, "scripts")
    script_files = [f for f in os.listdir(scripts_dir) if f.endswith("_script.json")]
    if not script_files:
        print(f"No script found in {scripts_dir}")
        sys.exit(1)

    with open(os.path.join(scripts_dir, script_files[0])) as f:
        ticker = json.load(f)["metadata"]["ticker"]

    if args.status:
        url = poll_render(args.status)
        if url:
            download_result(url, project_dir, ticker)
        return

    print("=" * 50)
    print(f"  Shotstack Assembly: {ticker}")
    print("=" * 50)

    # Step 0: Verify AWS access
    check_aws_credentials()

    # Step 1: Upload assets to S3 and generate presigned URLs
    print("\nUploading assets to S3...")
    assets = build_asset_manifest(project_dir, ticker)

    # Step 2: Build timeline
    edit = build_timeline(project_dir, ticker, assets)

    if args.edit_only:
        print("\nEdit JSON saved. Skipping render (--edit-only).")
        return

    # Step 3: Submit render
    render_id = submit_render(edit)
    if not render_id:
        sys.exit(1)

    # Save render ID
    render_path = os.path.join(project_dir, "videos", "shotstack_render.json")
    with open(render_path, "w") as f:
        json.dump({"render_id": render_id, "submitted_at": time.strftime("%Y-%m-%d %H:%M:%S")}, f, indent=2)

    # Step 4: Poll and download
    video_url = poll_render(render_id)
    if video_url:
        output_path = download_result(video_url, project_dir, ticker)
        normalize_audio(output_path)
    else:
        print(f"\nCheck later:")
        print(f"  uv run python tools/assemble_video.py {args.project} --status {render_id}")


if __name__ == "__main__":
    main()
