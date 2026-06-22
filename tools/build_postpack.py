"""
Assemble a per-platform "publish pack" for a project — one paste-ready document with each
platform's exact upload fields plus the public S3 media links. Makes manual native posting
(or a future API push) a copy/paste job.

Combines:
  - social/{t}_publish.json            (Cowork-authored native copy: titles, LinkedIn, IG, podcast notes)
  - social/{t}_x_post.txt              (the X post / thread)
  - social/{t}_youtube_description.txt (the YouTube description)
  - videos/{t}_timestamps.txt          (authoritative YouTube chapters from the render)
  - the published S3 media URLs        (content/{t}/...)

Writes projects/{t}/{t}_publish_pack.md. Degrades gracefully — missing media or unauthored
fields are flagged inline, never fatal. Sections appear only when their media/content exist
(e.g. no Short → no Short / Instagram Reel sections).

X handling: the long-form link is pulled OUT of the post body and into a first reply, and the
short is posted as native video — X throttles posts that carry an external link and rewards
native autoplay video.

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
    "[YOUTUBE_LINK]": "paste the long-form URL after you upload to YouTube",
    "[PROMO_CODE]":   "the live Stripe promo code (e.g. CANNABIS50 / ROBO50)",
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

    sections = []

    # ── 1) YouTube long-form ──
    if urls["final"]:
        s = ["## 1) YouTube — long-form", f"**Video:** {urls['final']}"]
        if urls["thumbnail"]:
            s.append(f"**Thumbnail:** {urls['thumbnail']}")
        s.append("**Title:**")
        s.append(block(field(pub, "youtube_title", t)))
        s.append("**Description:**")
        s.append(block(yt_desc) if yt_desc else f"_(missing social/{t}_youtube_description.txt)_")
        if chapters:
            s.append("**Chapters (authoritative, from the render — confirm they match the description):**")
            s.append(block(chapters))
        sections.append("\n".join(s))

    # ── 2) YouTube Short ──
    if urls["short"]:
        sections.append("\n".join([
            "## 2) YouTube — Short",
            f"**Video:** {urls['short']}",
            "**Title / caption:**",
            block(field(pub, "short_title", t)),
            "**Pinned comment** (drops the long-form link):",
            block(field(pub, "short_pinned_comment", t)),
        ]))

    # ── 3) Instagram Reel (uses the short) ──
    if urls["short"]:
        sections.append("\n".join([
            "## 3) Instagram — Reel",
            f"**Video:** {urls['short']}",
            "**Caption** (no clickable links on IG — point to the bio):",
            block(field(pub, "instagram_caption", t)),
        ]))

    # ── 4) X — native video in the post, long-form link in the first reply ──
    if x_post:
        # pull any [YOUTUBE_LINK] line out of the body; X throttles posts with external links
        body_lines, link_line = [], None
        for line in x_post.splitlines():
            if "[YOUTUBE_LINK]" in line:
                link_line = line.strip()
            else:
                body_lines.append(line)
        x_body = re.sub(r"\n{3,}", "\n\n", "\n".join(body_lines)).strip()
        x_reply = (pub.get("x_first_reply") or "").strip() or link_line or "Full breakdown ▶️ [YOUTUBE_LINK]"
        s = ["## 4) X"]
        if urls["short"]:
            s.append(f"**Native video** (upload the short — autoplays, beats link suppression): {urls['short']}")
        elif urls["thumbnail"]:
            s.append(f"**Image** (no short — attach the thumbnail so it isn't a bare-link post): {urls['thumbnail']}")
        s.append(f"**Post** ({len(x_body)} chars — no link in the body; single long-form post, or split at the numbered breaks into a thread):")
        s.append(block(x_body))
        s.append("**First reply** (the long-form link goes here, NOT the body):")
        s.append(block(x_reply))
        sections.append("\n".join(s))

    # ── 5) LinkedIn ──
    li_video = urls["final"] or urls["short"]
    s = ["## 5) LinkedIn"]
    if li_video:
        s.append(f"**Native video:** {li_video}")
    s.append("**Post:**")
    s.append(block(field(pub, "linkedin_post", t)))
    s.append("**First comment** (link goes here, not the body — beats reach suppression):")
    s.append(block(field(pub, "linkedin_first_comment", t)))
    sections.append("\n".join(s))

    # ── 6) Spotify / Podcast ──
    if urls["podcast_mp3"] or urls["podcast_mp4"]:
        s = ["## 6) Spotify / Podcast"]
        if urls["podcast_mp3"]:
            s.append(f"**Audio (MP3 — Spotify/Apple):** {urls['podcast_mp3']}")
        if urls["podcast_mp4"]:
            s.append(f"**Video (MP4 — YouTube podcast):** {urls['podcast_mp4']}")
        s.append("**Episode title:**")
        s.append(block(field(pub, "podcast_episode_title", t)))
        s.append("**Show notes:**")
        s.append(block(field(pub, "podcast_show_notes", t)))
        sections.append("\n".join(s))

    # ── placeholders found anywhere in the assembled sections (incl. synthesized text) ──
    tokens = sorted(set(re.findall(r"\[[A-Z_]+\]", "\n".join(sections))))
    fill = [f"- `{tok}` — {PLACEHOLDER_HELP.get(tok, 'fill before posting')}" for tok in tokens]

    head = [
        f"# {t} — Publish Pack",
        f"_Generated {today}. Media = public S3. Paste-ready; fill any placeholders first._",
        "## ⚠️ Fill before posting",
        "\n".join(fill) if fill else "_None — everything resolved._",
        "## Posting order",
        ("1. **YouTube long-form** → copy the resulting URL\n"
         "2. Replace every `[YOUTUBE_LINK]` below with that URL\n"
         "3. Post the rest: Short, X (+ first reply), LinkedIn (+ first comment), Instagram, Podcast"),
    ]

    text = "\n\n".join(head + sections) + "\n"
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
