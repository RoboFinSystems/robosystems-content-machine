"""
Assemble a per-platform "publish pack" for a project — one paste-ready document with each
platform's exact upload fields plus the public S3 media links. Makes manual native posting
(or a future API push) a copy/paste job.

Combines:
  - social/{t}_publish.json            (authored native copy: titles, first-comment)
  - social/{t}_x_post.txt              (the single X post)
  - social/{t}_youtube_description.txt (the YouTube description)
  - reports/{t}_brief.md               (the written brief — published on X as an X Article)
  - videos/{t}_timestamps.txt          (authoritative YouTube chapters from the render)
  - the published S3 media URLs        (content/{t}/...)

Writes projects/{t}/{t}_publish_pack.md. Degrades gracefully — missing media or unauthored
fields are flagged inline, never fatal. Sections appear only when their media/content exist.

Platform model (X-first; research lane) — each asset in the format its surface rewards:
  - X: the main post's native video is the 9:16 SHORT (native upload = the discovery, so no
    external link in the body), the brief is published as an X Article (the depth lane) and
    linked from the post. The 16:9 long-form is NOT posted natively to X — it lives on YouTube,
    reached via the Article's link.
  - YouTube: the 16:9 long-form, plus the 9:16 Short (its own upload; #Shorts; links the long-form).
    With no {t}_short.mp4 present the pack simply omits the Short.
  - The Q&A podcast is retired (no Spotify/podcast section).
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
    "short":       ("videos/{t}_short.mp4",         "{t}_short.mp4"),   # 9:16 (music variant) -> X post + YT Short
    "thumbnail":    ("charts/png/{t}_thumbnail.png",        "{t}_thumbnail.png"),         # 16:9 YouTube + website
    "thumbnail_x":  ("charts/png/{t}_thumbnail_x.png",      "{t}_thumbnail_x.png"),       # 5:2 X
    "thumbnail_sq": ("charts/png/{t}_thumbnail_square.png", "{t}_thumbnail_square.png"),  # 1:1 Spotify
}

# placeholders we expect the human (or a later step) to resolve before posting
PLACEHOLDER_HELP = {
    "[YOUTUBE_LINK]":   "paste the long-form URL after you upload to YouTube",
    "[LONGFORM_URL]":   "the long-form YouTube URL (fills the Short's description link)",
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
    short_x_post = read_text(os.path.join(project_dir, f"social/{t}_short_x_post.txt"))
    short_yt = read_text(os.path.join(project_dir, f"social/{t}_short_youtube.txt"))
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

    # ── X — publish the brief as an X Article FIRST, then the main post: 9:16 short + Article link ──
    main_x_copy = short_x_post or x_post
    if main_x_copy:
        # Strip any [YOUTUBE_LINK] line; the post carries the on-platform Article link instead
        # (an X Article link is internal, so it doesn't trip X's external-link throttle).
        body_lines = [ln for ln in main_x_copy.splitlines() if "[YOUTUBE_LINK]" not in ln]
        x_body = re.sub(r"\n{3,}", "\n\n", "\n".join(body_lines)).strip()
        lines = []
        # Step 1 — the X Article (the brief). Post it FIRST so its URL exists for the main post.
        # The brief is left as RAW markdown (not a code block) so a markdown preview renders it:
        # highlight the rendered brief and paste into the X Article (rich-text editor). The
        # end-of-build pass resolves [PROMO_CODE] + angle brackets here.
        lines.append("**Step 1 — publish the brief as an X Article FIRST** "
                     "(then copy its URL into `[X_ARTICLE_LINK]` in Step 2):")
        if urls.get("thumbnail_x"):
            lines.append(f"- Header image (5:2): {urls['thumbnail_x']}")
        if brief_text:
            ref = f" · published copy: {brief_url}" if brief_url else ""
            lines.append(f"- Highlight the rendered brief below + paste as the X Article{ref}:")
            lines.append("")
            lines.append(brief_text)
        elif brief_url:
            lines.append(f"- Brief to publish as the X Article: {brief_url}")
        # Step 2 — the main post: native video + a link to the now-live Article.
        lines.append("")
        lines.append("**Step 2 — the main post** (native video + a link to the Article from Step 1):")
        vid = urls["short"] or urls["final"]
        if vid:
            kind = "9:16 short" if urls["short"] else "16:9 long-form"
            lines.append(f"- **Native video** (upload the {kind}): {vid}")
        elif urls.get("thumbnail_x") or urls["thumbnail"]:
            img = urls.get("thumbnail_x") or urls["thumbnail"]
            lines.append(f"- **Image** (attach the 5:2 X thumbnail so it isn't a bare-text post): {img}")
        post_with_link = f"{x_body}\n\n📄 Full brief: [X_ARTICLE_LINK]"
        lines.append(f"- **Post** ({len(x_body)} chars + the Article link — one post, NOT a thread):")
        lines.append(block(post_with_link))
        add("X", lines)

    # ── YouTube Short (the 9:16 short as a Short; its description links the long-form) ──
    has_short = bool(urls["short"])
    if has_short:
        s_lines = [f"**Video (9:16):** {urls['short']}"]
        if short_yt:
            head_body = short_yt.split("\n", 1)
            s_lines += ["**Title:**", block(head_body[0].strip())]
            body = head_body[1].strip() if len(head_body) > 1 else ""
            if body:
                s_lines += ["**Description** (keep #Shorts; links the long-form):", block(body)]
        else:
            s_lines.append(f"_(author social/{t}_short_youtube.txt — line 1 = title, the rest = "
                           "description with [LONGFORM_URL] + #Shorts)_")
        add("YouTube Short", s_lines)

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
    ]
    order = [
        "1. **YouTube long-form** → copy the resulting URL (fill any `[YOUTUBE_LINK]` / `[LONGFORM_URL]`)",
    ]
    if has_short:
        order.append("2. **YouTube Short** (the 9:16) once the long-form is live, so its description "
                     "links the long-form")
    order.append(
        f"{3 if has_short else 2}. **X**: publish the brief as an X **Article FIRST** → copy its URL "
        "into `[X_ARTICLE_LINK]`, then the main post = "
        + ("the **9:16 short** as native video" if has_short else "the native video")
        + " + the Article link")
    order.append("_LinkedIn is reserved for the technical/blog lane; research analysis doesn't post there._")
    head.append("\n".join(order))

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
