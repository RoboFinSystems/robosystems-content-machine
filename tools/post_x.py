#!/usr/bin/env python3
"""Post a project's single X post (native video + copy) via the X API v2.

One-time:  just x-auth               verify (or mint) the user access token
Then:      just x-post TICKER --dry-run     preview the assembled post
           just x-post TICKER --article-url https://x.com/...   post for real

All credentials live in .env (same as every other service in this repo):
  X_CONSUMER_KEY / X_SECRET_KEY     the app's consumer key + consumer secret
  X_ACCESS_TOKEN / X_ACCESS_SECRET  user-context token for the posting account
  X_BEARER_TOKEN                    app-only; cannot write - unused here
  X_HANDLE                          pin: refuse to post as any other account

Getting the access token (writes need USER context, not the bearer token):
  A) If the developer app lives on the posting account (@RoboFinSystems):
     developer portal -> app -> Keys and tokens -> Access Token and Secret ->
     Generate. App permissions must be "Read and write" BEFORE generating
     (regenerate after changing permissions). Paste both into .env.
  B) Otherwise: `! just x-auth` runs the OAuth 1.0a PIN flow - open the URL
     while logged in as the posting account, paste the PIN back. Requires
     "User authentication settings" configured on the app.

Posting model (see postpack): the brief goes up FIRST as an X Article -
X has NO public API for Articles, so that step stays manual - then this
tool sends the main post: native video + the Article link via --article-url.
Long-form native video (>2:20) requires X Premium on the posting account.
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
UPLOAD_URL = f"{API}/2/media/upload"
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


def build_post_text(ticker: str, args) -> str:
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
    if args.article_url:
        text += f"\n\n📄 Full brief: {args.article_url}"
    elif "[X_ARTICLE_LINK]" in text:
        sys.exit("copy contains [X_ARTICLE_LINK] but no --article-url was given")
    return text


def upload_video(sess, video: Path) -> str:
    """Chunked v2 media upload: INIT -> APPEND -> FINALIZE -> poll STATUS."""
    total = video.stat().st_size
    r = sess.post(UPLOAD_URL, data={
        "command": "INIT", "total_bytes": total,
        "media_type": "video/mp4", "media_category": "tweet_video",
    })
    if r.status_code >= 300:
        api_error(r, "INIT media upload")
    d = r.json().get("data", r.json())
    media_id = str(d.get("id") or d.get("media_id_string") or d.get("media_id"))

    sent, idx = 0, 0
    with open(video, "rb") as f:
        while chunk := f.read(CHUNK):
            r = sess.post(UPLOAD_URL,
                          data={"command": "APPEND", "media_id": media_id,
                                "segment_index": idx},
                          files={"media": chunk})
            if r.status_code >= 300:
                api_error(r, f"APPEND segment {idx}")
            sent += len(chunk)
            idx += 1
            print(f"  upload {int(sent / total * 100)}%")

    r = sess.post(UPLOAD_URL, data={"command": "FINALIZE", "media_id": media_id})
    if r.status_code >= 300:
        api_error(r, "FINALIZE media upload")
    info = r.json().get("data", r.json()).get("processing_info")

    while info and info.get("state") in ("pending", "in_progress"):
        wait = info.get("check_after_secs", 5)
        print(f"  processing ({info['state']}) - checking in {wait}s")
        time.sleep(wait)
        r = sess.get(UPLOAD_URL, params={"command": "STATUS", "media_id": media_id})
        if r.status_code >= 300:
            api_error(r, "STATUS poll")
        info = r.json().get("data", r.json()).get("processing_info")
    if info and info.get("state") != "succeeded":
        sys.exit(f"video processing failed: {json.dumps(info)}\n"
                 "(a >2:20 video needs X Premium on the posting account)")
    print("video processed")
    return media_id


def cmd_post(args) -> int:
    ticker = args.ticker.upper()
    proj = REPO / "projects" / ticker
    text = build_post_text(ticker, args)

    video = None
    if not args.no_video:
        video = Path(args.video) if args.video else proj / "videos" / f"{ticker}_final.mp4"
        if not video.exists():
            sys.exit(f"video not found: {video} (use --video, or --no-video for text-only)")

    print(f"post:      {len(text)} chars (280 is the non-Premium cap)")
    print(f"video:     {video} ({video.stat().st_size/1e6:.1f} MB)" if video else "video:     NONE")
    print(f"article:   {args.article_url or 'NONE'}")
    if args.dry_run:
        print("--- dry run: post text ---")
        print(text)
        return 0

    sess = oauth_session()
    handle = acting_user_guard(sess)

    payload = {"text": text}
    if video:
        payload["media"] = {"media_ids": [upload_video(sess, video)]}
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
        "article_url": args.article_url,
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
    po = sub.add_parser("post", help="send the single X post with native video")
    po.add_argument("ticker")
    po.add_argument("--article-url", help="URL of the already-published X Article")
    po.add_argument("--video", help="explicit video path (e.g. webdeck _music variant)")
    po.add_argument("--no-video", action="store_true", help="text-only post")
    po.add_argument("--campaign", help="promo-code campaign override")
    po.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.cmd == "auth":
        return cmd_auth(args)
    return cmd_post(args)


if __name__ == "__main__":
    sys.exit(main())
