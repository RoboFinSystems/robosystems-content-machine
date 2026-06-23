"""
Assemble a per-platform "publish pack" for a project — one paste-ready document with each
platform's exact upload fields plus the public S3 media links. Makes manual native posting
(or a future API push) a copy/paste job.

Combines:
  - social/{t}_publish.json            (Cowork-authored native copy: titles, LinkedIn, podcast notes)
  - social/{t}_x_post.txt              (the single X post)
  - social/{t}_youtube_description.txt (the YouTube description)
  - reports/{t}_brief.md               (the written brief — published on X as an X Article)
  - videos/{t}_timestamps.txt          (authoritative YouTube chapters from the render)
  - the published S3 media URLs        (content/{t}/...)

Writes projects/{t}/{t}_publish_pack.md. Degrades gracefully — missing media or unauthored
fields are flagged inline, never fatal. Sections appear only when their media/content exist.

Platform model (revised after the first posting round):
  - YouTube gets THREE upload paths: long-form, Short, and the Q&A podcast video (MP4).
  - X: one long-form post (NOT a thread) + the long-form video uploaded NATIVELY (the native
    upload is the discovery, so no external link in the post) + the brief published as an
    X Article and linked in the first comment.
  - Spotify: the podcast audio (MP3) only — the podcast video lives on YouTube.
  - Instagram is dropped (wrong audience, strips links; the Short already covers that asset).

Usage:
    uv run python tools/build_postpack.py TRLV
"""

import argparse
import datetime
import json
import os
import re

from helpers import get_project_dir

# key -> (path under project dir, S3 object name) ; both templated on the ticker {t}
MEDIA = {
    "final":       ("videos/{t}_final.mp4",         "{t}_final.mp4"),
    "short":       ("videos/{t}_short.mp4",         "{t}_short.mp4"),
    "podcast_mp3": ("videos/{t}_qa_podcast.mp3",    "{t}_qa_podcast.mp3"),
    "podcast_mp4": ("videos/{t}_qa_podcast.mp4",    "{t}_qa_podcast.mp4"),
    "thumbnail":   ("charts/png/{t}_thumbnail.png", "{t}_thumbnail.png"),
}

# placeholders we expect the human (or a later step) to resolve before posting
PLACEHOLDER_HELP = {
    "[YOUTUBE_LINK]":   "paste the long-form URL after you upload to YouTube",
    "[X_ARTICLE_LINK]": "the link to the brief once you publish it as an X Article",
    "[PROMO_CODE]":     "the live Stripe promo code (e.g. CANNABIS50 / ROBO50)",
}


def read_text(path):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    return None


def media_url(bucket, ticker, project_dir, key):
    """Public S3 URL for a media artifact, or None if the local file doesn't exist."""
    rel, name = MEDIA[key]
    rel, name = rel.format(t=ticker), name.format(t=ticker)
    if not os.path.exists(os.path.join(project_dir, rel)):
        return None
    return f"https://{bucket}.s3.amazonaws.com/content/{ticker}/{name}"


def field(pub, key, ticker):
    """Authored field value, or an inline 'author this' note for the pack."""
    val = (pub.get(key) or "").strip() if pub else ""
    if val:
        return val
    return f"_(author in social/{ticker}_publish.json → `{key}`)_"


def block(text):
    """Wrap paste-ready copy in a fenced block."""
    return f"```\n{text}\n```"


def build(project):
    project_dir = get_project_dir(project)
    t = project
    bucket = os.environ.get("S3_BUCKET", "robosystems-marketing-assets")
    today = datetime.date.today().isoformat()

    pub = {}
    pj = os.path.join(project_dir, f"social/{t}_publish.json")
    if os.path.exists(pj):
        with open(pj, encoding="utf-8") as f:
            pub = json.load(f)

    x_post = read_text(os.path.join(project_dir, f"social/{t}_x_post.txt"))
    yt_desc = read_text(os.path.join(project_dir, f"social/{t}_youtube_description.txt"))
    chapters = read_text(os.path.join(project_dir, f"videos/{t}_timestamps.txt"))
    urls = {k: media_url(bucket, t, project_dir, k) for k in MEDIA}

    brief_local = os.path.join(project_dir, f"reports/{t}_brief.md")
    brief_url = (f"https://{bucket}.s3.amazonaws.com/content/{t}/{t}_brief.md"
                 if os.path.exists(brief_local) else None)

    sections = []  # (title, body) — numbered at the end so skipped sections don't misnumber

    def add(title, lines):
        sections.append((title, "\n".join(lines)))

    # ── YouTube — long-form ──
    if urls["final"]:
        lines = [f"**Video:** {urls['final']}"]
        if urls["thumbnail"]:
            lines.append(f"**Thumbnail:** {urls['thumbnail']}")
        lines += ["**Title:**", block(field(pub, "youtube_title", t)), "**Description:**"]
        lines.append(block(yt_desc) if yt_desc else f"_(missing social/{t}_youtube_description.txt)_")
        if chapters:
            lines.append("**Chapters (authoritative, from the render — confirm they match the description):**")
            lines.append(block(chapters))
        add("YouTube — long-form", lines)

    # ── YouTube — Short ──
    if urls["short"]:
        add("YouTube — Short", [
            f"**Video:** {urls['short']}",
            "**Title / caption:**", block(field(pub, "short_title", t)),
            "**Pinned comment** (drops the long-form link):", block(field(pub, "short_pinned_comment", t)),
        ])

    # ── YouTube — Podcast (the Q&A video) ──
    if urls["podcast_mp4"]:
        add("YouTube — Podcast", [
            f"**Video:** {urls['podcast_mp4']}",
            "**Title:**", block(field(pub, "podcast_episode_title", t)),
            "**Description:**", block(field(pub, "podcast_show_notes", t)),
        ])

    # ── X — one long-form post + native long-form video; brief as an X Article in the first comment ──
    if x_post:
        # X gets the native video; strip any [YOUTUBE_LINK] line — no external link in the post
        body_lines = [ln for ln in x_post.splitlines() if "[YOUTUBE_LINK]" not in ln]
        x_body = re.sub(r"\n{3,}", "\n\n", "\n".join(body_lines)).strip()
        lines = []
        vid = urls["final"] or urls["short"]
        if vid:
            lines.append(f"**Native video** (upload the 16:9 long-form — the native upload is the discovery, so keep links out of the post): {vid}")
        elif urls["thumbnail"]:
            lines.append(f"**Image** (attach the thumbnail so it isn't a bare-text post): {urls['thumbnail']}")
        lines.append(f"**Post** ({len(x_body)} chars — one long-form post, NOT a thread; no external link):")
        lines.append(block(x_body))
        lines.append("**First comment** (publish the brief as an X Article, then paste its link in for `[X_ARTICLE_LINK]`):")
        lines.append(block(field(pub, "x_first_comment", t)))
        src = f"`projects/{t}/reports/{t}_brief.md`" + (f"  ·  S3 copy: {brief_url}" if brief_url else "")
        lines.append(f"- Brief to publish as the X Article: {src}")
        add("X", lines)

    # ── LinkedIn ──
    li_video = urls["final"] or urls["short"]
    lines = []
    if li_video:
        lines.append(f"**Native video:** {li_video}")
    lines += ["**Post:**", block(field(pub, "linkedin_post", t)),
              "**First comment** (link goes here, not the body — beats reach suppression):",
              block(field(pub, "linkedin_first_comment", t))]
    add("LinkedIn", lines)

    # ── Spotify / Podcast (audio only — the video is on YouTube) ──
    if urls["podcast_mp3"]:
        add("Spotify / Podcast", [
            f"**Audio (MP3 — Spotify / Apple / Amazon):** {urls['podcast_mp3']}",
            "**Episode title:**", block(field(pub, "podcast_episode_title", t)),
            "**Show notes:**", block(field(pub, "podcast_show_notes", t)),
        ])

    numbered = [f"## {i}) {title}\n{body}" for i, (title, body) in enumerate(sections, 1)]

    # ── placeholders found anywhere in the assembled sections ──
    tokens = sorted(set(re.findall(r"\[[A-Z_]+\]", "\n".join(numbered))))
    fill = [f"- `{tok}` — {PLACEHOLDER_HELP.get(tok, 'fill before posting')}" for tok in tokens]

    head = [
        f"# {t} — Publish Pack",
        f"_Generated {today}. Media = public S3. Paste-ready; fill any placeholders first._",
        "## ⚠️ Fill before posting",
        "\n".join(fill) if fill else "_None — everything resolved._",
        "## Posting order",
        ("1. **YouTube long-form** → copy the resulting URL\n"
         "2. Replace every `[YOUTUBE_LINK]` below with that URL (Short pinned comment + LinkedIn first comment)\n"
         "3. Post the rest: YouTube Short, YouTube Podcast, X (native long-form video + brief as an X Article "
         "in the first comment), LinkedIn (+ first comment), Spotify"),
    ]

    text = "\n\n".join(head + numbered) + "\n"
    dest = os.path.join(project_dir, f"{t}_publish_pack.md")
    with open(dest, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Wrote {dest}")
    if tokens:
        print("Fill before posting: " + ", ".join(tokens))
    return dest


def main():
    ap = argparse.ArgumentParser(description="Assemble a per-platform publish pack")
    ap.add_argument("project", help="Project name / ticker (e.g., TRLV)")
    build(ap.parse_args().project)


if __name__ == "__main__":
    main()
