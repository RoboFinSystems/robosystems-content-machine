"""
Assemble the final video from deck slide PNGs and voiceover audio using the
Shotstack Edit API.

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

S3_BUCKET = require_env("AWS_S3_BUCKET")
S3_REGION = os.environ.get("AWS_REGION", "us-east-1")
EDIT_BASE = None  # Set in main() from CLI arg
_SHOTSTACK_API_KEY = None  # Set in main() based on environment

# ─── Reliability config (env-overridable) ──────────────────────
# Presigned URLs must outlive the entire render; long videos can take >1h, and the
# default 1h expiry was causing "access denied" failures on slow renders.
S3_URL_TTL = int(os.environ.get("SHOTSTACK_URL_TTL", "21600"))  # 6 hours
# Max time to wait for a render before giving up. Real renders routinely exceed the
# old 10-min cap, which made successful renders look like failures.
SHOTSTACK_MAX_WAIT = int(os.environ.get("SHOTSTACK_MAX_WAIT", "2700"))  # 45 min
# Exponential-backoff retry count for transient HTTP / S3 failures.
MAX_RETRIES = int(os.environ.get("HTTP_MAX_RETRIES", "4"))

# HTTP status codes worth retrying (rate limit + transient server errors).
_RETRYABLE_HTTP = (429, 500, 502, 503, 504)


def shotstack_request(method, path, data=None):
    url = f"{EDIT_BASE}{path}"
    headers = {
        "x-api-key": _SHOTSTACK_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    body = json.dumps(data).encode() if data else None
    for attempt in range(MAX_RETRIES):
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            if e.code in _RETRYABLE_HTTP and attempt < MAX_RETRIES - 1:
                wait = 2 ** attempt
                print(f"  Shotstack {e.code} (attempt {attempt+1}/{MAX_RETRIES}), retrying in {wait}s...")
                time.sleep(wait)
                continue
            print(f"  Shotstack API Error {e.code}: {error_body[:500]}")
            return None
        except urllib.error.URLError as e:
            if attempt < MAX_RETRIES - 1:
                wait = 2 ** attempt
                print(f"  Shotstack network error ({e.reason}), retrying in {wait}s...")
                time.sleep(wait)
                continue
            print(f"  Shotstack network error: {e.reason}")
            return None
    return None


# ─── S3 Asset Management ───────────────────────────────────────

def s3_presign(s3_key, expires=None):
    """Generate a presigned URL for an S3 object (TTL defaults to S3_URL_TTL)."""
    if expires is None:
        expires = S3_URL_TTL
    for attempt in range(MAX_RETRIES):
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
        if result.returncode == 0:
            return result.stdout.strip()
        if attempt < MAX_RETRIES - 1:
            time.sleep(2 ** attempt)
            continue
        print(f"  Presign failed for {s3_key}: {result.stderr}")
        return None


def s3_upload(local_path, s3_key):
    """Upload a local file to S3, retrying transient failures."""
    for attempt in range(MAX_RETRIES):
        result = subprocess.run(
            ["aws", "s3", "cp", local_path, f"s3://{S3_BUCKET}/{s3_key}", "--quiet"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return True
        if attempt < MAX_RETRIES - 1:
            time.sleep(2 ** attempt)
            continue
    return False


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
    """S3 prefix for Shotstack render staging. Namespaced under `staging/` (private,
    read by Shotstack via presigned URLs) and auto-expired by a bucket lifecycle rule,
    so render scratch never accumulates at the bucket root or mixes with content/."""
    return f"staging/{os.path.basename(project_dir)}"


def _any_newer_than(directory, suffix, ref_path):
    """True if any `*suffix` file in `directory` is newer than `ref_path` — i.e. the
    cache at `ref_path` is stale because a source asset was regenerated after it
    (e.g. a re-voice or a re-slice). Guards against shipping a stale render."""
    if not os.path.isdir(directory) or not os.path.exists(ref_path):
        return False
    ref_mtime = os.path.getmtime(ref_path)
    for f in os.listdir(directory):
        if f.endswith(suffix):
            try:
                if os.path.getmtime(os.path.join(directory, f)) > ref_mtime:
                    return True
            except OSError:
                continue
    return False


def build_asset_manifest(project_dir, ticker):
    """Upload local assets to S3 and build manifest with presigned URLs."""
    manifest_path = os.path.join(project_dir, "videos", "shotstack_assets.json")
    audio_dir = os.path.join(project_dir, "videos", "audio")
    png_dir = os.path.join(project_dir, "charts", "png")

    # Reuse a cached manifest only while its presigned URLs are still valid AND no
    # source asset (re-voiced audio / re-sliced PNG) is newer than the cache.
    if os.path.exists(manifest_path):
        with open(manifest_path) as f:
            existing = json.load(f)
        created = existing.get("_created", 0)
        fresh = time.time() - created < (S3_URL_TTL - 600)  # 10-min safety buffer
        stale = (_any_newer_than(audio_dir, "_voiceover.mp3", manifest_path)
                 or _any_newer_than(png_dir, ".png", manifest_path))
        if fresh and not stale:
            print(f"Using cached manifest ({len(existing) - 1} assets, still fresh)")
            return existing
        if stale:
            print("Source audio/slides changed since last upload — re-uploading.")

    s3_prefix = _get_s3_prefix(project_dir)
    assets = {"_created": time.time()}

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

    # Save manifest
    with open(manifest_path, "w") as f:
        json.dump(assets, f, indent=2)

    asset_count = len([k for k in assets if not k.startswith("_")])
    print(f"\nUploaded and presigned {asset_count} assets")
    return assets


# ─── Timeline Builder ───────────────────────────────────────────

def get_media_durations(project_dir):
    """Get actual voiceover durations (seg_id -> seconds) from cache or via ffprobe."""
    durations_path = os.path.join(project_dir, "videos", "media_durations.json")
    audio_dir = os.path.join(project_dir, "videos", "audio")

    # Use the cache only if no voiceover mp3 is newer than it (else re-probe after a re-voice).
    if os.path.exists(durations_path) and not _any_newer_than(audio_dir, ".mp3", durations_path):
        with open(durations_path) as f:
            return json.load(f).get("audio", {})

    audio = {}
    audio_dir = os.path.join(project_dir, "videos", "audio")
    if os.path.isdir(audio_dir):
        for f in os.listdir(audio_dir):
            if f.endswith(".mp3"):
                seg = f.split("segment_")[1].replace("_voiceover.mp3", "")
                dur = _ffprobe_duration(os.path.join(audio_dir, f))
                if dur:
                    audio[seg] = dur

    with open(durations_path, "w") as f:
        json.dump({"audio": audio}, f, indent=2)

    return audio


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
    """Run Whisper on each segment's voiceover MP3; return map seg_id -> srt_path."""
    srt_map = {}
    audio_dir = os.path.join(project_dir, "videos", "audio")

    for seg in segments:
        seg_id = seg["id"]
        audio_path = os.path.join(audio_dir, f"{ticker}_segment_{seg_id}_voiceover.mp3")
        if not os.path.exists(audio_path):
            continue

        print(f"  Seg {seg_id}...", end=" ")
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


def build_timeline(project_dir, ticker, assets, production=False):
    """Build the Shotstack timeline JSON from the script and uploaded assets."""
    script_path = os.path.join(project_dir, "scripts", f"{ticker}_script.json")
    with open(script_path) as f:
        script = json.load(f)

    segments = script["segments"]

    # Get ACTUAL voiceover durations (not estimates)
    audio_durations = get_media_durations(project_dir)

    print("\nSegment durations (actual):")

    # Build clips in sequence
    SEGMENT_GAP = 0.3   # seconds of black between slides
    video_clips = []
    audio_clips = []
    srt_entries = []      # for subtitle generation
    chapters = []         # (start, label) YouTube chapter markers from ACTUAL timing
    current_time = SEGMENT_GAP  # tiny lead-in before the first slide

    # ── Content slides (each: deck slide PNG + its voiceover) ──
    subtitles_on = os.environ.get("SUBTITLES", "true").lower() in ("true", "1", "yes")
    srt_index = 1
    for seg in segments:
        seg_id = seg["id"]

        # Slide PNG (named by visual_ref) + voiceover audio
        visual_ref = seg.get("visual_ref", "")
        chart_file = f"{visual_ref}.png" if visual_ref else None
        audio_file = f"{ticker}_segment_{seg_id}_voiceover.mp3"

        audio_info = assets.get(audio_file)
        chart_info = assets.get(chart_file) if chart_file else None

        if not audio_info:
            print(f"  Warning: No audio for segment {seg_id}, skipping")
            continue

        audio_duration = audio_durations.get(str(seg_id), seg["duration_estimate_seconds"])
        # Add buffer so voiceover finishes cleanly before the next slide
        AUDIO_TAIL_BUFFER = 0.5
        image_duration = audio_duration + AUDIO_TAIL_BUFFER
        slide_type = seg.get("visual_type", "chart")
        print(f"  Seg {seg_id} ({slide_type}): {audio_duration:.1f}s")

        if chart_info:
            # The first visible slide starts at frame 0 (absorbing the lead-in gap) with
            # NO fade-in — otherwise frame 0 is black and becomes the X/feed poster, since
            # X has no custom-thumbnail option for native video. Later slides keep the fade.
            is_first_clip = not video_clips
            clip = {
                "asset": {"type": "image", "src": chart_info["url"]},
                "start": 0.0 if is_first_clip else round(current_time, 2),
                "length": round(current_time + image_duration if is_first_clip else image_duration, 2),
            }
            if not is_first_clip:
                clip["transition"] = {"in": "fade"}
            video_clips.append(clip)

        audio_clips.append({
            "asset": {
                "type": "audio",
                "src": audio_info["url"],
                "volume": 1.0,
            },
            "start": round(current_time, 2),
            "length": round(audio_duration + 0.1, 2),  # slight buffer to avoid clipping
        })

        srt_entries.append({
            "seg_id": seg_id,
            "index": srt_index,
            "start": current_time,
            "end": current_time + audio_duration,
            "text": seg.get("narration", ""),
        })
        srt_index += 1
        label = (seg.get("slide") or {}).get("headline") or visual_ref or f"Segment {seg_id}"
        chapters.append((current_time, label))
        current_time += image_duration + SEGMENT_GAP

    # ── YouTube chapter timestamps (from ACTUAL durations, not estimates) ──
    def _mmss(t):
        t = int(round(t))
        return f"{t // 60}:{t % 60:02d}"
    chapters_path = os.path.join(project_dir, "videos", f"{ticker}_timestamps.txt")
    with open(chapters_path, "w") as cf:
        for i, (t, label) in enumerate(chapters):
            cf.write(f"{'0:00' if i == 0 else _mmss(t)} — {label}\n")
    print(f"  Chapters: -> {ticker}_timestamps.txt")

    # ── Whisper transcription for accurate subtitle timing (only when subtitles are on) ──
    if subtitles_on:
        print("\nTranscribing audio with Whisper...")
        whisper_srts = _whisper_transcribe_all(project_dir, ticker, segments)
        print(f"  Whisper: {len(whisper_srts)}/{len(srt_entries)} segments transcribed")
    else:
        whisper_srts = {}

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
        "resolution": "1080" if production else "hd",
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
    print(f"\nPolling render {render_id} (up to {SHOTSTACK_MAX_WAIT // 60} min)...")
    deadline = time.time() + SHOTSTACK_MAX_WAIT
    interval = 5
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        resp = shotstack_request("GET", f"/render/{render_id}")
        if not resp:
            time.sleep(interval)
            continue

        status = resp.get("response", {}).get("status", "unknown")
        elapsed = int(SHOTSTACK_MAX_WAIT - (deadline - time.time()))
        print(f"  [{attempt}] {elapsed}s — status: {status}")

        if status == "done":
            return resp["response"].get("url")
        elif status == "failed":
            error = resp.get("response", {}).get("error")
            print(f"  Render failed: {error}")
            return None

        time.sleep(interval)
        interval = min(interval + 2, 20)  # ramp 5s → 20s to ease API load on long renders

    print(f"  Still rendering after {SHOTSTACK_MAX_WAIT // 60} min — likely not failed, just slow.")
    print(f"  Check later:  uv run python tools/assemble_video.py PROJECT --status {render_id}")
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
    parser.add_argument("--production", action="store_true", help="Use Shotstack production API (v1) instead of stage")

    args = parser.parse_args()

    global EDIT_BASE, _SHOTSTACK_API_KEY
    if args.production:
        EDIT_BASE = "https://api.shotstack.io/edit/v1"
        _SHOTSTACK_API_KEY = require_env("SHOTSTACK_API_KEY")
    else:
        EDIT_BASE = "https://api.shotstack.io/edit/stage"
        _SHOTSTACK_API_KEY = os.environ.get("SHOTSTACK_API_KEY_SANDBOX", require_env("SHOTSTACK_API_KEY"))
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
    edit = build_timeline(project_dir, ticker, assets, production=args.production)

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
