"""
Shared helpers for the blog pipeline (stdlib-only, like the rest of tools/).

A blog post is a single markdown file with YAML-ish frontmatter:

    blog/<slug>/post.md       # frontmatter + body (the source of truth, git-versioned)
    blog/<slug>/cover.png     # optional cover image (authored)
    blog/<slug>/<slug>_x_post.txt        # optional social copy (authored)
    blog/<slug>/<slug>_narration.mp3     # optional narration (generated, gitignored)

`parse_post` returns (frontmatter_dict, body). The frontmatter parser is intentionally
minimal — it handles the shapes the blog uses (quoted/bare scalars, booleans, and flow-style
arrays that may span multiple lines) rather than pulling in PyYAML, keeping the toolchain
zero-install like every other script here.
"""

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLOG = os.path.join(ROOT, "blog")

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def is_valid_slug(slug):
    return bool(SLUG_RE.match(slug or ""))


def blog_dir(slug, must_exist=True):
    d = os.path.join(BLOG, slug)
    if must_exist and not os.path.isdir(d):
        raise FileNotFoundError(f"Blog post not found: {d}  (scaffold it with `just blog-new {slug}`)")
    return d


def split_frontmatter(text):
    """(raw_frontmatter, body) from a leading '---' fenced block; ('', text) if none."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.DOTALL)
    if not m:
        return "", text
    return m.group(1), m.group(2)


def _coerce_scalar(v):
    v = v.strip()
    if len(v) >= 2 and v[0] in "'\"" and v[-1] == v[0]:
        return v[1:-1]
    low = v.lower()
    if low in ("true", "false"):
        return low == "true"
    if v == "" or low in ("null", "~"):
        return None
    return v


def _parse_flow_array(buf):
    """'[a, b, c]' (possibly already line-joined) -> [a, b, c] with quotes stripped."""
    inner = buf[buf.index("[") + 1: buf.rindex("]")]
    out = []
    for part in inner.split(","):
        val = _coerce_scalar(part)
        if val is not None and val != "":
            out.append(val)
    return out


def parse_frontmatter(raw):
    """Minimal frontmatter parser for the blog's known shapes (NOT general YAML):
    `key: scalar`, `key: true/false`, and flow arrays `key: [..]` that may start on the
    next line and span several lines. Keys are top-level only (column 0)."""
    meta = {}
    lines = raw.split("\n")
    key_re = re.compile(r"^([A-Za-z][\w]*):\s*(.*)$")
    i = 0
    while i < len(lines):
        m = key_re.match(lines[i])
        if not m:
            i += 1
            continue
        key, rest = m.group(1), m.group(2).strip()
        if rest.startswith("["):
            buf = rest
        elif rest == "" and i + 1 < len(lines) and lines[i + 1].lstrip().startswith("["):
            i += 1
            buf = lines[i].strip()
        else:
            meta[key] = _coerce_scalar(rest)
            i += 1
            continue
        while buf.count("[") > buf.count("]") and i + 1 < len(lines):
            i += 1
            buf += " " + lines[i].strip()
        meta[key] = _parse_flow_array(buf)
        i += 1
    return meta


def parse_post(slug):
    """Return (frontmatter_dict, body_str) for blog/<slug>/post.md."""
    path = os.path.join(blog_dir(slug), "post.md")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing post body: {path}")
    with open(path, encoding="utf-8") as f:
        raw_fm, body = split_frontmatter(f.read())
    return parse_frontmatter(raw_fm), body


def normalize_date(s):
    """'2025-9-1' -> '2025-09-01' (zero-pad); pass anything else through unchanged."""
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})", str(s).strip())
    if not m:
        return str(s).strip()
    y, mo, d = m.groups()
    return f"{y}-{int(mo):02d}-{int(d):02d}"


def reading_time_minutes(body):
    """~200 wpm, rounded, floored at 1 — precomputed so the app drops its reading-time dep."""
    words = len(re.findall(r"\w+", body))
    return max(1, round(words / 200))


def excerpt_fallback(meta, body, limit=160):
    if meta.get("excerpt"):
        return meta["excerpt"]
    flat = re.sub(r"\s+", " ", clean_markdown_for_tts(body)).strip()
    return (flat[:limit] + "…") if len(flat) > limit else flat


def clean_markdown_for_tts(body):
    """Strip markdown to clean prose for narration: drop code blocks/tables/images, unwrap
    links/headings/lists, remove emphasis + inline-code markers, collapse blank lines."""
    text = re.sub(r"```.*?```", "", body, flags=re.DOTALL)      # fenced code
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)            # images
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)        # links -> text
    out = []
    for ln in text.split("\n"):
        s = ln.strip()
        if re.match(r"^\|?\s*:?-{3,}", s) or (s.startswith("|") and s.endswith("|")):
            continue  # markdown table separator / row — reads terribly aloud
        ln = re.sub(r"^#{1,6}\s+", "", ln)        # heading markers (keep the text)
        ln = re.sub(r"^\s*>\s?", "", ln)          # blockquote
        ln = re.sub(r"^\s*[-*+]\s+", "", ln)      # bullet
        ln = re.sub(r"^\s*\d+\.\s+", "", ln)      # numbered list
        out.append(ln)
    text = "\n".join(out).replace("`", "")
    text = re.sub(r"(\*\*|__|\*|_)", "", text)    # bold / italic
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def chunk_text(text, limit=2500):
    """Split into <=limit-char chunks on paragraph (then sentence) boundaries for TTS."""
    chunks, cur = [], ""
    for para in (p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()):
        if len(para) > limit:  # rare: hard-split an over-long paragraph on sentence ends
            for sent in re.split(r"(?<=[.!?])\s+", para):
                if cur and len(cur) + len(sent) + 1 > limit:
                    chunks.append(cur); cur = sent
                else:
                    cur = f"{cur} {sent}".strip()
            continue
        if cur and len(cur) + len(para) + 2 > limit:
            chunks.append(cur); cur = para
        else:
            cur = f"{cur}\n\n{para}" if cur else para
    if cur:
        chunks.append(cur)
    return chunks
