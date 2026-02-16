"""
Generate all avatar segments for a video script via HeyGen API.

Usage:
    uv run python tools/generate_avatar_segments.py JPM_2025_10_K

    # Resume polling if interrupted
    uv run python tools/generate_avatar_segments.py JPM_2025_10_K --poll
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error

from helpers import get_project_dir, require_env

API_BASE = "https://api.heygen.com"

# Motion prompt controls avatar body language and gestures
MOTION_PROMPT = (
    "Talking Naturally: Subject talks in a calm and confident manner while maintaining direct eye contact "
    "with the camera. Background elements subtly move to enhance realism. "
    "Camera remains absolutely static."
)


def api_request(method, path, data=None):
    url = f"{API_BASE}{path}"
    headers = {
        "x-api-key": require_env("HEYGEN_API_KEY"),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"  API Error {e.code}: {error_body}")
        return {"error": error_body}


def submit_segment(segment, avatar_id, voice_id, ticker, emotion="Serious"):
    payload = {
        "video_inputs": [
            {
                "character": {
                    "type": "avatar",
                    "avatar_id": avatar_id,
                    "scale": 1,
                    "avatar_style": "normal",
                    "custom_motion_prompt": MOTION_PROMPT,
                    "enhance_custom_motion_prompt": True,
                },
                "voice": {
                    "type": "text",
                    "voice_id": voice_id,
                    "input_text": segment["narration"],
                    "speed": 1.0,
                    "emotion": emotion,
                },
                "background": {"type": "color", "value": "#0a0a0a"},
            }
        ],
        "dimension": {"width": 1280, "height": 720},
        "title": f"{ticker} - Segment {segment['id']}",
    }
    resp = api_request("POST", "/v2/video/generate", payload)
    return resp.get("data", {}).get("video_id")


def submit_all(project_dir):
    avatar_id = require_env("HEYGEN_AVATAR_ID")
    voice_id = require_env("HEYGEN_VOICE_ID")

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
    avatar_segments = [s for s in segments if s["type"] == "avatar"]

    print(
        f"Script: {ticker} | {len(segments)} total | {len(avatar_segments)} avatar segments"
    )
    print(f"  Motion prompt: enabled\n")

    jobs = {
        "ticker": ticker,
        "script_file": script_files[0],
        "avatar_id": avatar_id,
        "voice_id": voice_id,
        "submitted_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "segments": {},
    }

    for seg in avatar_segments:
        seg_id = seg["id"]
        print(
            f"  Submitting segment {seg_id} ({seg['duration_estimate_seconds']}s est)...",
            end=" ",
        )

        video_id = submit_segment(seg, avatar_id, voice_id, ticker)
        if video_id:
            print(f"OK -> {video_id}")
            jobs["segments"][str(seg_id)] = {
                "video_id": video_id,
                "status": "submitted",
                "narration_preview": seg["narration"][:60] + "...",
                "estimated_seconds": seg["duration_estimate_seconds"],
            }
        else:
            print("FAILED")
            jobs["segments"][str(seg_id)] = {"video_id": None, "status": "failed"}

        time.sleep(1)

    jobs_path = os.path.join(project_dir, "videos", "heygen_jobs.json")
    os.makedirs(os.path.dirname(jobs_path), exist_ok=True)
    with open(jobs_path, "w") as f:
        json.dump(jobs, f, indent=2)

    print(
        f"\n{len([s for s in jobs['segments'].values() if s.get('video_id')])} segments submitted"
    )
    print(f"Jobs saved to: {jobs_path}")
    return jobs_path


def poll_and_download(project_dir):
    jobs_path = os.path.join(project_dir, "videos", "heygen_jobs.json")
    if not os.path.exists(jobs_path):
        print(f"No jobs file found at {jobs_path}")
        print("Run without --poll first to submit segments.")
        sys.exit(1)

    with open(jobs_path) as f:
        jobs = json.load(f)

    ticker = jobs["ticker"]
    output_dir = os.path.join(project_dir, "videos")
    all_done = False
    attempt = 0

    while not all_done:
        attempt += 1
        all_done = True
        pending = completed = failed = 0

        print(f"\n--- Poll attempt {attempt} ---")

        for seg_id, seg_info in jobs["segments"].items():
            video_id = seg_info.get("video_id")
            if not video_id or seg_info.get("status") in ("downloaded", "failed"):
                if seg_info.get("status") == "downloaded":
                    completed += 1
                else:
                    failed += 1
                continue

            resp = api_request("GET", f"/v1/video_status.get?video_id={video_id}")
            data = resp.get("data", {})
            status = data.get("status", "unknown")

            if status == "completed":
                duration = data.get("duration")
                filename = f"{ticker}_segment_{seg_id}.mp4"
                filepath = os.path.join(output_dir, filename)

                print(f"  Segment {seg_id}: COMPLETED ({duration}s) -> downloading...")
                urllib.request.urlretrieve(data["video_url"], filepath)

                seg_info["status"] = "downloaded"
                seg_info["duration"] = duration
                seg_info["filename"] = filename
                completed += 1
            elif status == "failed":
                print(f"  Segment {seg_id}: FAILED -> {data.get('error')}")
                seg_info["status"] = "failed"
                seg_info["error"] = str(data.get("error"))
                failed += 1
            else:
                print(f"  Segment {seg_id}: {status}")
                all_done = False
                pending += 1

        with open(jobs_path, "w") as f:
            json.dump(jobs, f, indent=2)

        print(f"  Completed: {completed} | Pending: {pending} | Failed: {failed}")

        if not all_done:
            print("  Waiting 15 seconds...")
            time.sleep(15)

    print(f"\n=== ALL DONE ===")
    total_duration = 0
    for seg_id, seg_info in sorted(jobs["segments"].items(), key=lambda x: int(x[0])):
        if seg_info.get("status") == "downloaded":
            d = seg_info.get("duration", 0)
            total_duration += d
            print(f"  Segment {seg_id}: {d}s -> {seg_info.get('filename')}")
        else:
            print(f"  Segment {seg_id}: {seg_info.get('status')}")

    print(
        f"\n  Total avatar duration: {total_duration:.1f}s ({total_duration / 60:.1f} min)"
    )


def main():
    parser = argparse.ArgumentParser(description="Generate avatar segments via HeyGen")
    parser.add_argument("project", help="Project name (e.g., JPM_2025_10_K)")
    parser.add_argument(
        "--poll", action="store_true", help="Resume polling only (skip submit)"
    )
    args = parser.parse_args()

    project_dir = get_project_dir(args.project)

    if args.poll:
        poll_and_download(project_dir)
    else:
        submit_all(project_dir)
        print("\nStarting download poll...\n")
        poll_and_download(project_dir)


if __name__ == "__main__":
    main()
