"""
The narration engine shared by the blog and research lanes.

Both lanes do the same thing to different source text: clean markdown to prose, chunk it on
paragraph boundaries to stay under the TTS per-request limit, synthesize chunk-by-chunk via
ElevenLabs, and concatenate to one MP3. Only the source file and the cleaning differ, so the
engine lives here and `narrate_blog.py` / `narrate_research.py` supply the text.

Not merged into blog_common.py on purpose: that module is stdlib-only by design, and this one
imports the ElevenLabs client.
"""

import os
import subprocess
import sys
import tempfile

from generate_voiceover_audio import generate_audio
from helpers import require_env


def synthesize(chunks, out_path, label="narration"):
    """Render `chunks` to one MP3 at `out_path` via the research narrator voice.

    Returns out_path. Exits with a message if a chunk fails — a partial narration is worse
    than none, because it publishes as if it were complete.
    """
    if not chunks:
        sys.exit(f"Error: {label} is empty after cleaning — nothing to narrate.")
    voice_id = require_env("ELEVEN_LABS_VOICE_ID")
    print(f"Narrating {label}: {len(chunks)} chunk(s) via voice {voice_id}\n")

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="narr_") as tmp:
        parts = []
        for i, chunk in enumerate(chunks):
            part = os.path.join(tmp, f"part_{i:03d}.mp3")
            print(f"  chunk {i + 1}/{len(chunks)} ({len(chunk)} chars)...")
            if not generate_audio(voice_id, chunk, part):
                sys.exit(f"  -> FAILED on chunk {i + 1}")
            parts.append(part)

        if len(parts) == 1:
            os.replace(parts[0], out_path)
        else:
            # Re-encode-concat to one MP3. Match the TTS output bitrate (mp3_44100_192):
            # the old -q:a 2 landed around 110kbps on speech, which re-introduced exactly
            # the compression mush the move to eleven_v3 @192kbps was meant to remove.
            inputs = []
            for p in parts:
                inputs += ["-i", p]
            concat = "".join(f"[{i}:a]" for i in range(len(parts))) + \
                f"concat=n={len(parts)}:v=0:a=1[out]"
            cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", concat,
                   "-map", "[out]", "-c:a", "libmp3lame", "-b:a", "192k", out_path]
            print("\n  Concatenating chunks -> MP3 ...")
            subprocess.run(cmd, check=True, capture_output=True)

    print(f"\n  -> {out_path}  ({os.path.getsize(out_path) / 1e6:.1f} MB)")
    return out_path


def already_narrated(out_path, force=False):
    """True when a usable narration is already on disk and we were not asked to redo it."""
    if force or not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
        return False
    print(f"Narration already exists: {out_path}  (use --force to regenerate)")
    return True


def duration_seconds(path):
    """Length of an audio file in seconds, or 0.0 if ffprobe is unavailable."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", path],
            capture_output=True, text=True).stdout.strip()
        return float(out or 0)
    except (OSError, ValueError):
        return 0.0
