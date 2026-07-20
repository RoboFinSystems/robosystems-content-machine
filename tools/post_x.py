#!/usr/bin/env python3
"""Post a project's X presence via the X API v2: the brief as an X Article,
then the single main post with native video linking to it.

One-time:  just x-auth                    verify (or mint) the user access token
Then:      just x-article TICKER          create the Article DRAFT from reports/{T}_brief.md
           (review the draft in the X Articles editor)
           just x-article TICKER --publish    publish it; sidecar stores the URL
           just x-post TICKER             main post: native video + Article link
                                          (link auto-read from the article sidecar)

All credentials live in .env (same as every other service in this repo):
  X_CONSUMER_KEY / X_SECRET_KEY     the app's consumer key + consumer secret
  X_ACCESS_TOKEN / X_ACCESS_SECRET  user-context token for the posting account
  X_BEARER_TOKEN                    app-only; cannot write - unused here
  X_HANDLE                          pin: refuse to post as any other account

Getting the access token (writes need USER context, not the bearer token):
  A) If the developer app lives on the posting account (@RoboFinSystems):
     developer portal -> app -> Keys and tokens -> Access Token and Secret ->
     Generate. App permissions must be "Read and write" BEFORE generating.
  B) Otherwise: `! just x-auth` runs the OAuth 1.0a PIN flow - open the URL
     while logged in as the posting account, paste the PIN back.

API notes:
  - media: split endpoints POST /2/media/upload/initialize -> /{id}/append
    (multipart) -> /{id}/finalize -> GET /2/media/upload?command=STATUS
  - articles: POST /2/articles/draft (DraftJS content_state built from the
    brief markdown) -> POST /2/articles/{id}/publish -> returns the post_id
  - OAuth 1.0a user tokens cover every scope and never expire
  - long native video (>2:20) and >280-char posts require X Premium
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import helpers

REPO = Path(__file__).resolve().parent.parent
ENV_FILE = REPO / ".env"
API = "https://api.x.com"
UPLOAD = f"{API}/2/media/upload"
CHUNK = 4 * 1024 * 1024


def oauth_session():
    from requests_oauthlib import OAuth1Session
    ck = os.environ.get("X_CONSUMER_KEY", "").strip()
    cs = os.environ.get("X_SECRET_KEY", "").strip()
    at = os.environ.get("X_ACCESS_TOKEN", "").strip()
    ats = os.environ.get("X_ACCESS_SECRET", "").strip()
    if not (ck and cs):
        sys.exit("X_CONSUMER_KEY / X_SECRET_KEY missing from .env")
    if not (at and ats):
        sys.exit("X_ACCESS_TOKEN / X_ACCESS_SECRET missing from .env - "
                 "run `just x-auth` (see tools/post_x.py docstring)")
    return OAuth1Session(ck, client_secret=cs,
                         resource_owner_key=at, resource_owner_secret=ats)


def save_env(**pairs):
    """Idempotently set vars in .env, preserving everything else."""
    text = ENV_FILE.read_text() if ENV_FILE.exists() else ""
    for k, v in pairs.items():
        line = f'{k}="{v}"'
        if re.search(rf"^{k}=", text, flags=re.M):
            text = re.sub(rf"^{k}=.*$", line, text, flags=re.M)
        else:
            text = text.rstrip("\n") + "\n" + line + "\n"
    ENV_FILE.write_text(text)
    print(f"{', '.join(pairs)} written to .env")


def api_error(r, doing):
    sys.exit(f"X API error while {doing}: HTTP {r.status_code}\n{r.text[:1000]}")


def acting_user(sess):
    r = sess.get(f"{API}/2/users/me")
    if r.status_code != 200:
        api_error(r, "checking the acting account (GET /2/users/me)")
    d = r.json()["data"]
    return d["username"], d["id"], d.get("name", "")


def acting_user_guard(sess):
    """Print the account this token acts as; abort on X_HANDLE mismatch.
    Same lesson as YouTube: the token binds to whoever granted it - pin the
    handle in .env so a personal-account token can never post as the brand."""
    handle, uid, name = acting_user(sess)
    print(f"account:   @{handle} ({name}, id {uid})")
    want = os.environ.get("X_HANDLE", "").strip().lstrip("@")
    if want and handle.lower() != want.lower():
        sys.exit(f"ABORT: token acts as @{handle} but .env pins X_HANDLE={want}. "
                 "Re-run `just x-auth` logged in as the right account.")
    return handle


def detect_campaign(proj: Path) -> str | None:
    pub = next(iter(proj.glob("social/*_publish.json")), None)
    if pub:
        try:
            c = json.loads(pub.read_text()).get("campaign")
            if c:
                return str(c)
        except (json.JSONDecodeError, OSError):
            pass
    return None


# ── media upload (split v2 endpoints) ────────────────────────────────────────

def upload_media(sess, path: Path, media_type: str, category: str) -> str:
    total = path.stat().st_size
    r = sess.post(f"{UPLOAD}/initialize", json={
        "media_type": media_type, "total_bytes": total, "media_category": category,
    })
    if r.status_code >= 300:
        api_error(r, "initialize media upload")
    media_id = str(r.json()["data"]["id"])

    sent, idx = 0, 0
    with open(path, "rb") as f:
        while chunk := f.read(CHUNK):
            r = sess.post(f"{UPLOAD}/{media_id}/append",
                          data={"segment_index": idx},
                          files={"media": chunk})
            if r.status_code >= 300:
                api_error(r, f"append segment {idx}")
            sent += len(chunk)
            idx += 1
            if total > CHUNK:
                print(f"  upload {int(sent / total * 100)}%")

    r = sess.post(f"{UPLOAD}/{media_id}/finalize")
    if r.status_code >= 300:
        api_error(r, "finalize media upload")
    info = r.json()["data"].get("processing_info")

    while info and info.get("state") in ("pending", "in_progress"):
        wait = info.get("check_after_secs", 5)
        print(f"  processing ({info['state']}) - checking in {wait}s")
        time.sleep(wait)
        r = sess.get(UPLOAD, params={"command": "STATUS", "media_id": media_id})
        if r.status_code >= 300:
            api_error(r, "poll processing status")
        info = r.json()["data"].get("processing_info")
    if info and info.get("state") != "succeeded":
        sys.exit(f"media processing failed: {json.dumps(info)}\n"
                 "(a >2:20 video needs X Premium on the posting account)")
    return media_id


# ── markdown -> DraftJS content_state (for the Article body) ─────────────────

def u16len(s: str) -> int:
    """DraftJS offsets count UTF-16 code units, not codepoints."""
    return len(s.encode("utf-16-le")) // 2


INLINE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)"    # [text](url)
                    r"|\*\*([^*]+)\*\*"             # **bold**
                    r"|\*([^*\n]+)\*")              # *italic*


def parse_inline(md: str):
    """Strip inline markdown, returning (plain text, style ranges, link ranges)."""
    parts, styles, links = [], [], []
    pos = off = 0
    for m in INLINE.finditer(md):
        lead = md[pos:m.start()]
        parts.append(lead)
        off += u16len(lead)
        if m.group(1) is not None:
            t = m.group(1)
            links.append((off, u16len(t), m.group(2)))
        elif m.group(3) is not None:
            t = m.group(3)
            styles.append((off, u16len(t), "bold"))
        else:
            t = m.group(4)
            styles.append((off, u16len(t), "italic"))
        parts.append(t)
        off += u16len(t)
        pos = m.end()
    parts.append(md[pos:])
    return "".join(parts), styles, links


def md_to_content_state(md: str):
    """Convert brief markdown to (title, DraftJS content_state).
    The first H1 becomes the article title, not a body block."""
    blocks, entities = [], []
    title = None

    def add(text, btype):
        plain, styles, links = parse_inline(text)
        blk = {"text": plain, "type": btype}
        if styles:
            blk["inline_style_ranges"] = [
                {"offset": o, "length": ln, "style": s} for o, ln, s in styles]
        if links:
            ranges = []
            for o, ln, url in links:
                # entities[].key is a string, but entity_ranges[].key must be
                # the INTEGER index (API rejects strings despite the docs)
                idx = len(entities)
                entities.append({"key": str(idx), "value": {
                    "type": "link", "mutability": "mutable", "data": {"url": url}}})
                ranges.append({"key": idx, "offset": o, "length": ln})
            blk["entity_ranges"] = ranges
        blocks.append(blk)

    para = []
    table = []

    def flush():
        if para:
            add(" ".join(para), "unstyled")
            para.clear()

    def flush_table():
        # Undocumented but verified 2026-07-20: an atomic block whose entity is
        # type "markdown" renders a real table from the markdown it carries
        # (same mechanism as the editor's paste-markdown-to-table trick).
        if table:
            idx = len(entities)
            entities.append({"key": str(idx), "value": {
                "type": "markdown", "mutability": "immutable",
                "data": {"markdown": "\n".join(table)}}})
            blocks.append({"text": " ", "type": "atomic",
                           "entity_ranges": [{"key": idx, "offset": 0, "length": 1}]})
            table.clear()

    for raw in md.splitlines():
        st = raw.strip()
        if st.startswith("|") and st.endswith("|") and st.count("|") >= 2:
            flush()
            table.append(st)
            continue
        flush_table()
        if not st:
            flush()
        elif re.fullmatch(r"-{3,}|\*{3,}|_{3,}", st):
            flush()  # horizontal rule - no DraftJS equivalent
        elif st.startswith("# "):
            flush()
            if title is None:
                title = parse_inline(st[2:])[0]
            else:
                add(st[2:], "header-one")
        elif st.startswith("## "):
            flush()
            add(st[3:], "header-two")
        elif st.startswith("### "):
            flush()
            add(st[4:], "header-three")
        elif re.match(r"^[-*•]\s+", st):
            flush()
            add(re.sub(r"^[-*•]\s+", "", st), "unordered-list-item")
        elif re.match(r"^\d+[.)]\s+", st):
            flush()
            add(re.sub(r"^\d+[.)]\s+", "", st), "ordered-list-item")
        elif st.startswith("> "):
            flush()
            add(st[2:], "blockquote")
        else:
            para.append(st)
    flush()
    flush_table()
    return title, {"blocks": blocks, "entities": entities}


# ── commands ─────────────────────────────────────────────────────────────────

def article_sidecar(proj: Path, ticker: str) -> Path:
    return proj / "social" / f"{ticker}_x_article.json"


def cmd_article(args) -> int:
    ticker = args.ticker.upper()
    proj = REPO / "projects" / ticker
    sidecar = article_sidecar(proj, ticker)

    if args.publish:
        if args.id:
            article_id = args.id
        elif sidecar.exists():
            article_id = json.loads(sidecar.read_text())["article_id"]
        else:
            sys.exit(f"no {sidecar.name} found - run `just x-article {ticker}` first "
                     "(or pass --id ARTICLE_ID)")
        sess = oauth_session()
        handle = acting_user_guard(sess)
        r = sess.post(f"{API}/2/articles/{article_id}/publish")
        if r.status_code >= 300:
            api_error(r, "publishing the article")
        post_id = r.json()["data"]["post_id"]
        url = f"https://x.com/{handle}/status/{post_id}"
        print(f"ARTICLE LIVE: {url}")
        data = json.loads(sidecar.read_text()) if sidecar.exists() else {"article_id": article_id}
        from datetime import datetime, timezone
        data.update(status="published", post_id=post_id, url=url,
                    published_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
        sidecar.write_text(json.dumps(data, indent=2) + "\n")
        print(f"next: just x-post {ticker} (picks up the Article link automatically)")
        return 0

    brief = proj / "reports" / f"{ticker}_brief.md"
    if not brief.exists():
        sys.exit(f"brief not found: {brief}")
    text = brief.read_text()
    code = helpers.resolve_promo_code(args.campaign or detect_campaign(proj))
    text = helpers.apply_promo_code(text, code)
    title, content_state = md_to_content_state(text)
    if not title:
        sys.exit("brief has no H1 - the first `# ` line becomes the Article title")

    cover = proj / "charts" / "png" / f"{ticker}_thumbnail_x.png"
    cover = cover if (cover.exists() and not args.no_cover) else None

    kinds = {}
    for b in content_state["blocks"]:
        kinds[b["type"]] = kinds.get(b["type"], 0) + 1
    print(f"title:     {title}")
    print(f"blocks:    {sum(kinds.values())} ({', '.join(f'{v} {k}' for k, v in kinds.items())})")
    print(f"entities:  {len(content_state['entities'])}")
    print(f"cover:     {cover if cover else 'NONE'}")
    if args.dry_run:
        print("--- dry run: first blocks ---")
        for b in content_state["blocks"][:4]:
            print(f"[{b['type']}] {b['text'][:110]}")
        return 0

    sess = oauth_session()
    acting_user_guard(sess)
    payload = {"title": title, "content_state": content_state}
    if cover:
        payload["cover_media"] = {
            "media_category": "tweet_image",
            "media_id": upload_media(sess, cover, "image/png", "tweet_image"),
        }
    r = sess.post(f"{API}/2/articles/draft", json=payload)
    if r.status_code >= 300:
        api_error(r, "creating the article draft")
    article_id = r.json()["data"]["id"]
    print(f"DRAFT created: article {article_id}")

    from datetime import datetime, timezone
    sidecar.write_text(json.dumps({
        "article_id": article_id,
        "title": title,
        "status": "draft",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }, indent=2) + "\n")
    print("review it in the X Articles editor (x.com -> Premium -> Articles), then:")
    print(f"  just x-article {ticker} --publish")
    return 0


def resolve_article_url(proj: Path, ticker: str, args) -> str | None:
    if args.article_url:
        return args.article_url
    sidecar = article_sidecar(proj, ticker)
    if sidecar.exists():
        data = json.loads(sidecar.read_text())
        if data.get("status") == "published" and data.get("url"):
            return data["url"]
        print(f"NOTE: article draft exists but is unpublished - "
              f"run `just x-article {ticker} --publish` first for the link")
    return None


def build_post_text(ticker: str, args, article_url: str | None) -> str:
    proj = REPO / "projects" / ticker
    src = proj / "social" / f"{ticker}_x_post.txt"
    if not src.exists():
        sys.exit(f"post copy not found: {src}")
    # Same assembly as postpack: native video replaces any [YOUTUBE_LINK] line,
    # and the Article link (internal, so no external-link throttle) goes last.
    lines = [ln for ln in src.read_text().splitlines() if "[YOUTUBE_LINK]" not in ln]
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    code = helpers.resolve_promo_code(args.campaign or detect_campaign(proj))
    text = helpers.apply_promo_code(text, code)
    if article_url:
        text += f"\n\n📄 Full brief: {article_url}"
    elif "[X_ARTICLE_LINK]" in text:
        sys.exit("copy contains [X_ARTICLE_LINK] but there is no published article - "
                 f"run `just x-article {ticker}` / --publish, or pass --article-url")
    return text


def cmd_post(args) -> int:
    ticker = args.ticker.upper()
    proj = REPO / "projects" / ticker
    article_url = resolve_article_url(proj, ticker, args)
    text = build_post_text(ticker, args, article_url)

    video = None
    if not args.no_video:
        video = Path(args.video) if args.video else proj / "videos" / f"{ticker}_final.mp4"
        if not video.exists():
            sys.exit(f"video not found: {video} (use --video, or --no-video for text-only)")

    print(f"post:      {len(text)} chars (280 is the non-Premium cap)")
    print(f"video:     {video} ({video.stat().st_size/1e6:.1f} MB)" if video else "video:     NONE")
    print(f"article:   {article_url or 'NONE'}")
    if args.dry_run:
        print("--- dry run: post text ---")
        print(text)
        return 0

    sess = oauth_session()
    handle = acting_user_guard(sess)

    payload = {"text": text}
    if video:
        payload["media"] = {"media_ids": [
            upload_media(sess, video, "video/mp4", "tweet_video")]}
        print("video processed")
    r = sess.post(f"{API}/2/tweets", json=payload)
    if r.status_code >= 300:
        api_error(r, "creating the post (POST /2/tweets)")
    tweet_id = r.json()["data"]["id"]
    url = f"https://x.com/{handle}/status/{tweet_id}"
    print(f"posted: {url}")

    from datetime import datetime, timezone
    sidecar = proj / "videos" / f"{ticker}_x.json"
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text(json.dumps({
        "tweet_id": tweet_id,
        "url": url,
        "article_url": article_url,
        "chars": len(text),
        "video": str(video) if video else None,
        "posted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }, indent=2) + "\n")
    return 0


def cmd_auth(_args) -> int:
    at = os.environ.get("X_ACCESS_TOKEN", "").strip()
    if at:
        sess = oauth_session()
        handle, uid, name = acting_user(sess)
        print(f"auth OK - token acts as: @{handle} ({name}, id {uid})")
        if not os.environ.get("X_HANDLE", "").strip():
            print(f'pin it: add X_HANDLE="{handle}" to .env so posts refuse any '
                  "other account; then try `just x-post TICKER --dry-run`")
        return 0

    # PIN-based OAuth 1.0a - needs a TTY for the PIN paste: run as `! just x-auth`
    from requests_oauthlib import OAuth1Session
    ck = os.environ.get("X_CONSUMER_KEY", "").strip()
    cs = os.environ.get("X_SECRET_KEY", "").strip()
    if not (ck and cs):
        sys.exit("X_CONSUMER_KEY / X_SECRET_KEY missing from .env")
    sess = OAuth1Session(ck, client_secret=cs, callback_uri="oob")
    try:
        sess.fetch_request_token(f"{API}/oauth/request_token")
    except Exception as e:
        sys.exit(f"request_token failed ({e}).\nThe app needs 'User authentication "
                 "settings' configured (permissions: Read and write) in the "
                 "developer portal - or skip this flow entirely by generating the "
                 "Access Token and Secret in Keys and tokens (see docstring).")
    print("Visit this URL logged in as the POSTING account (@RoboFinSystems):")
    print(sess.authorization_url(f"{API}/oauth/authorize"))
    pin = input("PIN: ").strip()
    tok = sess.fetch_access_token(f"{API}/oauth/access_token", verifier=pin)
    save_env(X_ACCESS_TOKEN=tok["oauth_token"], X_ACCESS_SECRET=tok["oauth_token_secret"])
    os.environ["X_ACCESS_TOKEN"] = tok["oauth_token"]
    os.environ["X_ACCESS_SECRET"] = tok["oauth_token_secret"]
    handle, uid, name = acting_user(oauth_session())
    print(f"auth OK - token acts as: @{handle} ({name}, id {uid})")
    print(f'pin it: add X_HANDLE="{handle}" to .env')
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("auth", help="verify (or mint via PIN flow) the user token")

    ar = sub.add_parser("article", help="create (or --publish) the brief as an X Article")
    ar.add_argument("ticker")
    ar.add_argument("--publish", action="store_true",
                    help="publish the draft from the sidecar (the post-review step)")
    ar.add_argument("--id", help="explicit article id (else social/{T}_x_article.json)")
    ar.add_argument("--no-cover", action="store_true", help="skip the 5:2 cover image")
    ar.add_argument("--campaign", help="promo-code campaign override")
    ar.add_argument("--dry-run", action="store_true")

    po = sub.add_parser("post", help="send the single X post with native video")
    po.add_argument("ticker")
    po.add_argument("--article-url", help="override the Article link (else the sidecar)")
    po.add_argument("--video", help="explicit video path (e.g. webdeck _music variant)")
    po.add_argument("--no-video", action="store_true", help="text-only post")
    po.add_argument("--campaign", help="promo-code campaign override")
    po.add_argument("--dry-run", action="store_true")

    args = ap.parse_args()
    if args.cmd == "auth":
        return cmd_auth(args)
    if args.cmd == "article":
        return cmd_article(args)
    return cmd_post(args)


if __name__ == "__main__":
    sys.exit(main())
