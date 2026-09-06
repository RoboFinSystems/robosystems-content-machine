"""
Narrate a blog post: ElevenLabs text->speech of blog/<slug>/post.md -> <slug>_narration.mp3.

Single-voice narration (the research narrator voice, ELEVEN_LABS_VOICE_ID). The post body is
cleaned of code blocks / tables / markup, chunked on paragraph boundaries to stay under the
TTS per-request limit, synthesized chunk-by-chunk, then concatenated with ffmpeg — the shared
engine in narrate_common, which the research briefs narrate through too.

Idempotent: skips if the narration already exists (use --force to regenerate — it re-bills TTS).

Usage:
    uv run python tools/narrate_blog.py financial-knowledge-graph-manifesto
"""

import argparse
import os
import sys

import blog_common as bc
import narrate_common


def narrate(slug, force=False):
    if not bc.is_valid_slug(slug):
        sys.exit(f"Error: invalid slug '{slug}' (kebab-case expected).")
    out_path = os.path.join(bc.blog_dir(slug), f"{slug}_narration.mp3")
    if narrate_common.already_narrated(out_path, force):
        return out_path

    _, body = bc.parse_post(slug)
    narrate_common.synthesize(bc.chunk_text(bc.clean_markdown_for_tts(body)), out_path, slug)
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
