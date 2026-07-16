"""
Assemble a per-platform "publish pack" for a project — one paste-ready document with each
platform's exact upload fields plus the public S3 media links. Makes manual native posting
(or a future API push) a copy/paste job.

Combines:
  - social/{t}_publish.json            (Cowork-authored native copy: titles, podcast notes)
  - social/{t}_x_post.txt              (the single X post)
  - social/{t}_youtube_description.txt (the YouTube description)
  - reports/{t}_brief.md               (the written brief — published on X as an X Article)
  - videos/{t}_timestamps.txt          (authoritative YouTube chapters from the render)
  - the published S3 media URLs        (content/{t}/...)

Writes projects/{t}/{t}_publish_pack.md. Degrades gracefully — missing media or unauthored
fields are flagged inline, never fatal. Sections appear only when their media/content exist.

Platform model (X-first; research lane):
  - X is the engine: one long-form post (NOT a thread) + the long-form video uploaded NATIVELY
    (the native upload is the discovery, so no external link in the post) + the brief published as
    an X Article and linked in the first comment. The 9:16 Short ALSO posts as a separate native
    X video — a second cashtag at-bat, on a different day.
  - YouTube + Spotify are byproducts (presence, not optimization): long-form + Short to YouTube;
    podcast MP3 to Spotify, which auto-mirrors the episode to YouTube via the connected RSS.
  - LinkedIn is NOT used for research — it's reserved for the technical/blog lane (build_blog_postpack.py).
  - Instagram is dropped (wrong audience, strips links).

Usage:
    uv run python tools/build_postpack.py TRLV
"""

import argparse
import datetime
import json
import os
import re

import reindex
from helpers import apply_promo_code, asset_url, get_project_dir, resolve_promo_code, strip_angle_brackets

# key -> (path under project dir, S3 object name) ; both templated on the ticker {t}
MEDIA = {
    "final":       ("videos/{t}_final.mp4",         "{t}_final.mp4"),
    "short":       ("videos/{t}_short.mp4",         "{t}_short.mp4"),
    "podcast_mp3": ("videos/{t}_qa_podcast.mp3",    "{t}_qa_podcast.mp3"),
    "podcast_mp4": ("videos/{t}_qa_podcast.mp4",    "{t}_qa_podcast.mp4"),
    "thumbnail":    ("charts/png/{t}_thumbnail.png",        "{t}_thumbnail.png"),         # 16:9 YouTube + website
    "thumbnail_x":  ("charts/png/{t}_thumbnail_x.png",      "{t}_thumbnail_x.png"),       # 5:2 X
    "thumbnail_sq": ("charts/png/{t}_thumbnail_square.png", "{t}_thumbnail_square.png"),  # 1:1 Spotify
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


def media_url(ticker, project_dir, key):
    """Public URL for a media artifact, or None if the local file doesn't exist."""
    rel, name = MEDIA[key]
    rel, name = rel.format(t=ticker), name.format(t=ticker)
    if not os.path.exists(os.path.join(project_dir, rel)):
        return None
    return asset_url(f"content/{ticker}/{name}")


def field(pub, key, ticker):
    """Authored field value, or an inline 'author this' note for the pack."""
    val = (pub.get(key) or "").strip() if pub else ""
    if val:
        return val
    return f"_(author in social/{ticker}_publish.json → `{key}`)_"


def block(text):
    """Wrap paste-ready copy in a fenced block."""
    return f"```\n{text}\n```"


def finalize_chapters(yt_desc, chapters_text):
    """Replace the hand-drafted chapters block in the YouTube description with the
    authoritative chapters from the render (correct times + the real segment list)
    and drop any '(draft — finalized after render)' label. Cowork estimates chapter
    times before the render; only the render knows the real ones, so the description
    must be finalized here or it ships wrong timestamps. Returns paste-ready text."""
    if not yt_desc:
        return yt_desc
    # authoritative lines from timestamps.txt: "0:00 — Title" -> "0:00 Title"
    auth = []
    for ln in (chapters_text or "").splitlines():
        m = re.match(r"^\s*(\d+:\d{2})\s*[—–-]?\s*(.*)$", ln)
        if m:
            auth.append(f"{m.group(1)} {m.group(2)}".rstrip())
    if not auth:
        return yt_desc  # nothing authoritative to inject; leave as-authored
    new_block = "⏱️ Chapters:\n" + "\n".join(auth)

    lines = yt_desc.splitlines()
    ts = re.compile(r"^\s*\d+:\d{2}\b")
    start = next((i for i, ln in enumerate(lines)
                  if re.search(r"chapters", ln, re.I) and not ts.match(ln)
                  and i + 1 < len(lines) and ts.match(lines[i + 1])), None)
    if start is None:
        return yt_desc.rstrip() + "\n\n" + new_block  # no block authored -> append
    end = start + 1
    while end < len(lines) and ts.match(lines[end]):
        end += 1
    return "\n".join(lines[:start] + new_block.splitlines() + lines[end:])


def build(project):
    project_dir = get_project_dir(project)
    t = project
    today = datetime.date.today().isoformat()

    pub = {}
    pj = os.path.join(project_dir, f"social/{t}_publish.json")
    if os.path.exists(pj):
        with open(pj, encoding="utf-8") as f:
            pub = json.load(f)

    x_post = read_text(os.path.join(project_dir, f"social/{t}_x_post.txt"))
    yt_desc = read_text(os.path.join(project_dir, f"social/{t}_youtube_description.txt"))
    chapters = read_text(os.path.join(project_dir, f"videos/{t}_timestamps.txt"))
    urls = {k: media_url(t, project_dir, k) for k in MEDIA}

    brief_local = os.path.join(project_dir, f"reports/{t}_brief.md")
    brief_text = read_text(brief_local)
    brief_url = (asset_url(f"content/{t}/{t}_brief.md")
                 if os.path.exists(brief_local) else None)

    sections = []  # (title, body) — numbered at the end so skipped sections don't misnumber

    def add(title, lines):
        sections.append((title, "\n".join(lines)))

    # ── YouTube — long-form ──
    if urls["final"]:
        lines = [f"**Video:** {urls['final']}"]
        if urls["thumbnail"]:
            lines.append(f"**Thumbnail:** {urls['thumbnail']}")
        # Finalize the draft chapter block against the render before pasting, so the
        # description carries the REAL timestamps (and no "draft" label) inline.
        final_desc = finalize_chapters(yt_desc, chapters) if yt_desc else yt_desc
        lines += ["**Title:**", block(field(pub, "youtube_title", t)), "**Description:**"]
        lines.append(block(final_desc) if final_desc else f"_(missing social/{t}_youtube_description.txt)_")
        add("YouTube — long-form", lines)

    # ── YouTube — Short ──
    if urls["short"]:
        add("YouTube — Short", [
            f"**Video:** {urls['short']}",
            "**Title / caption:**", block(field(pub, "short_title", t)),
            "**Pinned comment** (drops the long-form link):", block(field(pub, "short_pinned_comment", t)),
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
        elif urls.get("thumbnail_x") or urls["thumbnail"]:
            img = urls.get("thumbnail_x") or urls["thumbnail"]
            lines.append(f"**Image** (attach the 5:2 X thumbnail so it isn't a bare-text post): {img}")
        if urls.get("thumbnail_x"):
            lines.append(f"**X thumbnail (5:2)** — use as the X Article header image: {urls['thumbnail_x']}")
        lines.append(f"**Post** ({len(x_body)} chars — one long-form post, NOT a thread; no external link):")
        lines.append(block(x_body))
        lines.append("**First comment** (publish the brief as an X Article, then paste its link in for `[X_ARTICLE_LINK]`):")
        lines.append(block(field(pub, "x_first_comment", t)))
        # The brief is left as RAW markdown — NOT in a code block — so a markdown preview
        # renders it: highlight the rendered brief and paste straight into the X Article
        # (rich-text editor, not markdown). The end-of-build pass still resolves
        # [PROMO_CODE] + angle brackets here. (The local source keeps the placeholder.)
        if brief_text:
            ref = f" · published copy: {brief_url}" if brief_url else ""
            lines.append(f"**Brief — highlight the rendered brief below + paste as the X Article**{ref}:")
            lines.append("")
            lines.append(brief_text)
        elif brief_url:
            lines.append(f"- Brief to publish as the X Article: {brief_url}")
        add("X", lines)

    # ── X — Short clip (second at-bat: the 9:16 Short as a standalone native X post) ──
    if urls["short"]:
        add("X — Short (post on a DIFFERENT day from the main post — a second cashtag at-bat)", [
            f"**Native video** (upload the 9:16 Short as its own post, NOT a reply): {urls['short']}",
            "**Caption:**", block(field(pub, "short_title", t)),
            f"_Standalone native-video post so the Short gets its own run in For You + the ${t} cashtag "
            f"feed. Keep ${t} in the caption; no external link in the body._",
        ])

    # ── Spotify / Podcast (audio MP3 → Spotify; the connected RSS auto-posts it to YouTube too) ──
    if urls["podcast_mp3"]:
        cover = [f"**Cover art (1:1, ≥1400px):** {urls['thumbnail_sq']}"] if urls.get("thumbnail_sq") else []
        add("Spotify / Podcast", [
            f"**Audio (MP3 — Spotify / Apple / Amazon):** {urls['podcast_mp3']}",
            *cover,
            "_Posting to Spotify also publishes the episode to YouTube via the connected RSS feed; then `just sync-youtube` captures its URL._",
            "**Episode title:**", block(field(pub, "podcast_episode_title", t)),
            "**Show notes:**", block(field(pub, "podcast_show_notes", t)),
        ])

    numbered = [f"## {i}) {title}\n{body}" for i, (title, body) in enumerate(sections, 1)]

    # Resolve [PROMO_CODE] now (campaign-derived, known at build time) so the pack is
    # paste-ready; only the post-hoc links ([YOUTUBE_LINK]/[X_ARTICLE_LINK]) stay open.
    promo = resolve_promo_code((reindex.project_meta(t) or {}).get("campaign"))
    numbered = [strip_angle_brackets(apply_promo_code(s, promo)) for s in numbered]

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
         "2. Replace every `[YOUTUBE_LINK]` below with that URL (the Short's pinned comment)\n"
         "3. Post the rest: YouTube Short, X (native long-form video + brief as an X Article in the "
         "first comment), Spotify (auto-posts to YouTube via RSS)\n"
         "4. On a later day: the **X — Short** post — a second cashtag at-bat.\n"
         "_LinkedIn is reserved for the technical/blog lane; research analysis doesn't post there._"),
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
