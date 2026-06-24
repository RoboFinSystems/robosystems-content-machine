"""
Narrate a blog post: ElevenLabs text->speech of blog/<slug>/post.md -> <slug>_narration.mp3.

Single-voice narration (the research narrator voice, ELEVEN_LABS_VOICE_ID). The post body is
cleaned of code blocks / tables / markup, chunked on paragraph boundaries to stay under the
TTS per-request limit, synthesized chunk-by-chunk, then concatenated with ffmpeg — reusing the
exact tooling the research voiceover + Q&A podcast already use.

Idempotent: skips if the narration already exists (use --force to regenerate — it re-bills TTS).

Usage:
    uv run python tools/narrate_blog.py financial-knowledge-graph-manifesto
"""

import argparse
import os
import subprocess
import sys
import tempfile

import blog_common as bc
from generate_voiceover_audio import generate_audio
from helpers import require_env


def narrate(slug, force=False):
    if not bc.is_valid_slug(slug):
        sys.exit(f"Error: invalid slug '{slug}' (kebab-case expected).")
    voice_id = require_env("ELEVEN_LABS_VOICE_ID")
    post_dir = bc.blog_dir(slug)
    out_path = os.path.join(post_dir, f"{slug}_narration.mp3")

    if not force and os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        print(f"Narration already exists: {out_path}  (use --force to regenerate)")
        return out_path

    _, body = bc.parse_post(slug)
    chunks = bc.chunk_text(bc.clean_markdown_for_tts(body))
    if not chunks:
        sys.exit("Error: post body is empty after cleaning — nothing to narrate.")
    print(f"Narrating {slug}: {len(chunks)} chunk(s) via voice {voice_id}\n")

    with tempfile.TemporaryDirectory(prefix=f"{slug}_narr_") as tmp:
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
            # Re-encode-concat to one MP3 (same approach as the Q&A podcast assembler).
            inputs = []
            for p in parts:
                inputs += ["-i", p]
            concat = "".join(f"[{i}:a]" for i in range(len(parts))) + \
                f"concat=n={len(parts)}:v=0:a=1[out]"
            cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", concat,
                   "-map", "[out]", "-c:a", "libmp3lame", "-q:a", "2", out_path]
            print("\n  Concatenating chunks -> MP3 ...")
            subprocess.run(cmd, check=True, capture_output=True)

    size_mb = os.path.getsize(out_path) / 1e6
    print(f"\n  -> {out_path}  ({size_mb:.1f} MB)")
    print(f"  Publish with: just blog-publish {slug}")
    return out_path


def main():
    ap = argparse.ArgumentParser(description="Narrate a blog post via ElevenLabs TTS")
    ap.add_argument("slug", help="Post slug (the blog/<slug>/ folder name)")
    ap.add_argument("--force", action="store_true", help="Regenerate even if narration exists")
    args = ap.parse_args()
    narrate(args.slug, force=args.force)


if __name__ == "__main__":
    main()
