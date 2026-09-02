#!/usr/bin/env python3
"""Upload a project's final video to YouTube via the Data API v3.

One-time:  just yt-auth              interactive browser OAuth; writes YT_REFRESH_TOKEN to .env
Then:      just yt-upload TICKER     upload + thumbnail + chapters/tags, PRIVATE by default

All credentials live in .env (same as every other service in this repo):
  YT_CLIENT_ID / YT_CLIENT_SECRET   the OAuth client (from the GCP console)
  YT_REFRESH_TOKEN                  written by `just yt-auth`

Auth notes (web-type OAuth client):
  - the GCP console must list http://localhost:8090/ as an authorized redirect URI
    (or use a Desktop-app client, which allows any localhost port)
  - publish the OAuth consent screen to production, else refresh tokens expire in 7 days

YouTube policy note: videos uploaded through an UNAUDITED API project are locked
to private by YouTube. Until the API audit clears, upload private (the default),
review in Studio, and flip visibility there. After the audit, use --public.
Quota: one upload = 1,600 units of the 10,000/day default (about 6 uploads/day);
a first comment = 50 units.

First comment: `publish` (and `upload --public`) posts the channel's first comment
on the video - the written-brief link (publish.json `youtube_comment` overrides the
default; `[RESEARCH_URL]` resolves to the ticker's /research page). The API cannot
pin a comment; on a video with no other comments it sits on top anyway. Comments
need the youtube.force-ssl scope - tokens minted before it was added must re-run
`just yt-auth` once.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

import helpers

REPO = Path(__file__).resolve().parent.parent
ENV_FILE = REPO / ".env"
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",       # commentThreads.insert (first comment)
    "https://www.googleapis.com/auth/yt-analytics.readonly",   # read-only reach/retention (pull_analytics.py)
]
TOKEN_URI = "https://oauth2.googleapis.com/token"
OAUTH_PORT = 8090
THUMB_MAX_BYTES = 2 * 1024 * 1024   # YouTube custom-thumbnail hard limit


def env_client():
    cid = os.environ.get("YT_CLIENT_ID", "").strip()
    csec = os.environ.get("YT_CLIENT_SECRET", "").strip()
    if not (cid and csec):
        sys.exit("YT_CLIENT_ID / YT_CLIENT_SECRET missing from .env")
    return cid, csec


def save_refresh_token(token: str) -> None:
    """Idempotently set YT_REFRESH_TOKEN in .env, preserving everything else."""
    line = f'YT_REFRESH_TOKEN="{token}"'
    text = ENV_FILE.read_text() if ENV_FILE.exists() else ""
    if re.search(r"^YT_REFRESH_TOKEN=", text, flags=re.M):
        text = re.sub(r"^YT_REFRESH_TOKEN=.*$", line, text, flags=re.M)
    else:
        text = text.rstrip("\n") + "\n" + line + "\n"
    ENV_FILE.write_text(text)
    print("YT_REFRESH_TOKEN written to .env")


def get_creds(interactive: bool):
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    cid, csec = env_client()
    rtok = os.environ.get("YT_REFRESH_TOKEN", "").strip()
    if rtok:
        creds = Credentials(None, refresh_token=rtok, token_uri=TOKEN_URI,
                            client_id=cid, client_secret=csec, scopes=SCOPES)
        try:
            creds.refresh(Request())
            return creds
        except Exception as e:
            if not interactive:
                sys.exit(f"stored YT_REFRESH_TOKEN no longer valid ({e}) - "
                         "run `just yt-auth`")
            print("stored refresh token invalid (client changed?) - rerunning OAuth")
    elif not interactive:
        sys.exit("YT_REFRESH_TOKEN missing - run `just yt-auth` first")

    from google_auth_oauthlib.flow import InstalledAppFlow
    config = {"installed": {
        "client_id": cid,
        "client_secret": csec,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": TOKEN_URI,
        "redirect_uris": [f"http://localhost:{OAUTH_PORT}/"],
    }}
    flow = InstalledAppFlow.from_client_config(config, SCOPES)
    try:
        creds = flow.run_local_server(port=OAUTH_PORT, access_type="offline",
                                      prompt="consent")
    except Exception as e:
        sys.exit(f"OAuth flow failed ({e}).\nIf this is redirect_uri_mismatch: add "
                 f"http://localhost:{OAUTH_PORT}/ to the client's authorized redirect "
                 "URIs in the GCP console, or use a Desktop-app client.")
    if not creds.refresh_token:
        sys.exit("Google returned no refresh token - remove the app's prior grant at "
                 "myaccount.google.com/permissions and rerun `just yt-auth`")
    save_refresh_token(creds.refresh_token)
    return creds


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


# The written brief lives on roboinvestor.ai since 2026-09-02 (site-content-surfaces);
# robosystems.ai redirects the old path, so comments already posted keep working.
RESEARCH_URL = "https://roboinvestor.ai/research/{ticker}"
DEFAULT_COMMENT = ("Full written brief, with every number sourced to the filing: {url}")


def first_comment_text(ticker: str, override: str | None = None) -> str:
    """The first-comment body: --text override, else publish.json `youtube_comment`,
    else the default written-brief line. `[RESEARCH_URL]` resolves in all three."""
    url = RESEARCH_URL.format(ticker=ticker)
    text = (override or "").strip()
    if not text:
        pj = REPO / "projects" / ticker / "social" / f"{ticker}_publish.json"
        if pj.exists():
            try:
                text = str(json.loads(pj.read_text()).get("youtube_comment") or "").strip()
            except (json.JSONDecodeError, OSError):
                pass
    if not text:
        text = DEFAULT_COMMENT.format(url=url)
    return text.replace("[RESEARCH_URL]", url)


def post_first_comment(yt, vid: str, text: str, sidecar: Path, force: bool = False) -> None:
    """Post the channel's first comment on `vid`. Idempotent via the sidecar's
    `comment_id` (--force to post another). A failure never blocks publish - the
    video is already live; warn and move on."""
    data = json.loads(sidecar.read_text()) if sidecar.exists() else None
    if data and data.get("comment_id") and not force:
        print(f"first comment already posted ({data['comment_id']}) - --force posts another")
        return
    import time
    from googleapiclient.errors import HttpError
    body = {
        "snippet": {
            "videoId": vid,
            "topLevelComment": {"snippet": {"textOriginal": text}},
        },
    }
    resp = None
    for attempt in (1, 2):
        try:
            resp = yt.commentThreads().insert(part="snippet", body=body).execute()
            break
        except HttpError as e:
            try:
                reason = (e.error_details or [{}])[0].get("reason", "")
            except Exception:
                reason = ""
            if reason == "insufficientPermissions" or "scope" in str(e).lower():
                print("WARNING: first comment not posted - token lacks the comment scope. "
                      "Re-run `just yt-auth` once, then `just yt-comment TICKER`.")
                return
            if attempt == 1:
                # an insert seconds after the publish flip can 403 transiently - retry once
                print(f"comment insert {e.status_code} ({reason or 'no reason given'}) - "
                      "retrying in 20s")
                time.sleep(20)
                continue
            print(f"WARNING: first comment not posted ({e.status_code}: {reason or e}) - "
                  "retry later with `just yt-comment TICKER [--short]`")
            return
    cid = resp["id"]
    print(f"first comment posted: {text[:80]}{'...' if len(text) > 80 else ''}")
    print(f"  (thread {cid}; pin it in Studio if you want - the API cannot pin)")
    if data is not None:
        data["comment_id"] = cid
        sidecar.write_text(json.dumps(data, indent=2) + "\n")


def longform_url(proj: Path, ticker: str):
    """The long-form's public URL from its sidecar (for the Short description link)."""
    try:
        return json.loads((proj / "videos" / f"{ticker}_youtube.json").read_text()).get("url")
    except Exception:
        return None


def shorts_parts(proj: Path, ticker: str, args):
    """9:16 Short: title + description from social/{T}_short_youtube.txt (line 1 = title,
    rest = description), the {T}_short.mp4 (music variant), and short-script tags. The
    long-form link token resolves from the long-form sidecar - so upload the long-form
    FIRST for the Short to point at it."""
    copy = proj / "social" / f"{ticker}_short_youtube.txt"
    if not copy.exists():
        sys.exit(f"short YouTube copy not found: {copy}\n"
                 "  (line 1 = title, the rest = description; put [LONGFORM_URL] where the "
                 "long-form link should go)")
    raw = copy.read_text().splitlines()
    body_idx = next((i for i, ln in enumerate(raw) if ln.strip()), None)
    if body_idx is None:
        sys.exit(f"{copy.name} is empty")
    title = raw[body_idx].strip()
    description = "\n".join(raw[body_idx + 1:]).strip()

    lf = longform_url(proj, ticker)
    for token in ("[LONGFORM_URL]", "[YOUTUBE_LINK]"):
        if token in description:
            if lf:
                description = description.replace(token, lf)
            else:
                description = description.replace(token, "").strip()
                print(f"NOTE: {token} unresolved - upload the long-form first "
                      f"(just yt-upload {ticker}) so its URL exists in the Short description")
    if "#shorts" not in (title + " " + description).lower():
        description = (description + "\n\n#Shorts").strip()

    video = Path(args.video) if args.video else proj / "videos" / f"{ticker}_short.mp4"
    tags = []
    ss = proj / "scripts" / f"{ticker}_short_script.json"
    if ss.exists():
        try:
            tags = json.loads(ss.read_text()).get("metadata", {}).get("tags", [])
        except Exception:
            pass
    return title, description, tags, video, None   # no custom thumb: Shorts pick a frame


def build_request_parts(ticker: str, args):
    proj = REPO / "projects" / ticker
    if getattr(args, "short", False):
        title, description, raw_tags, video, thumb = shorts_parts(proj, ticker, args)
    else:
        script = json.loads((proj / "scripts" / f"{ticker}_script.json").read_text())
        meta = script["metadata"]
        # publish.json's `youtube_title` is the SEARCH-FIRST title (Company + Ticker + quarter +
        # the angle a viewer would type); script.json's `video_title` is the short curiosity line.
        # ~61% of this channel's traffic is search, and the authoring contract requires the two to
        # differ, so the search title has to win. Uploads before 2026-07-30 silently used
        # `video_title` and threw the search title away.
        pj = proj / "social" / f"{ticker}_publish.json"
        title = meta["video_title"]
        if pj.exists():
            title = json.loads(pj.read_text()).get("youtube_title") or title
        description = (proj / "social" / f"{ticker}_youtube_description.txt").read_text()
        raw_tags = meta.get("tags", [])
        video = Path(args.video) if args.video else proj / "videos" / f"{ticker}_final.mp4"
        thumb = proj / "charts" / "png" / f"{ticker}_thumbnail.png"
        thumb = thumb if thumb.exists() else None

    code = helpers.resolve_promo_code(args.campaign or detect_campaign(proj))
    description = helpers.apply_promo_code(description, code)
    if len(title) > 100:
        sys.exit(f"title is {len(title)} chars (YouTube max 100): {title}")
    if len(description.encode()) > 5000:
        sys.exit(f"description is {len(description.encode())} bytes (YouTube max 5000)")
    if not video.exists():
        sys.exit(f"video not found: {video} (use --video for a webdeck variant)")

    tags, budget = [], 480
    for t in raw_tags:
        if budget - len(t) < 0:
            break
        tags.append(t)
        budget -= len(t) + 1

    privacy = "public" if args.public else "unlisted" if args.unlisted else "private"
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": args.category,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }
    return body, video, thumb


def prepared_thumbnail(thumb: Path) -> Path:
    """YouTube rejects thumbnails over 2MB - recompress to JPEG if needed."""
    if thumb.stat().st_size <= THUMB_MAX_BYTES:
        return thumb
    from PIL import Image
    out = thumb.with_suffix(".upload.jpg")
    Image.open(thumb).convert("RGB").save(out, "JPEG", quality=88, optimize=True)
    print(f"thumbnail {thumb.stat().st_size//1024}KB > 2MB limit -> {out.name} "
          f"({out.stat().st_size//1024}KB)")
    return out


def cmd_upload(args) -> int:
    ticker = args.ticker.upper()
    body, video, thumb = build_request_parts(ticker, args)

    print(f"video:     {video} ({video.stat().st_size/1e6:.1f} MB)")
    print(f"title:     {body['snippet']['title']}")
    print(f"privacy:   {body['status']['privacyStatus']}")
    print(f"tags:      {', '.join(body['snippet']['tags'][:6])}...")
    print(f"thumbnail: {thumb if thumb else 'NONE'}")
    if args.dry_run:
        print("--- dry run: description ---")
        print(body["snippet"]["description"][:800])
        return 0

    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    yt = build("youtube", "v3", credentials=get_creds(interactive=False))
    acting_channel_guard(yt)
    media = MediaFileUpload(str(video), chunksize=8 * 1024 * 1024, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            print(f"  upload {int(status.progress() * 100)}%")
    vid = resp["id"]
    print(f"uploaded: https://youtu.be/{vid}")
    from datetime import datetime, timezone
    sc_name = f"{ticker}_short_youtube.json" if getattr(args, "short", False) else f"{ticker}_youtube.json"
    sidecar = REPO / "projects" / ticker / "videos" / sc_name
    sidecar.write_text(json.dumps({
        "video_id": vid,
        "url": f"https://youtu.be/{vid}",
        "privacy": body["status"]["privacyStatus"],
        "title": body["snippet"]["title"],
        "uploaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }, indent=2) + "\n")

    if thumb:
        from googleapiclient.errors import HttpError
        try:
            yt.thumbnails().set(videoId=vid,
                                media_body=str(prepared_thumbnail(thumb))).execute()
            print("thumbnail set")
        except HttpError as e:
            print(f"WARNING: thumbnail not set ({e.status_code}): wrong channel or "
                  "channel not verified for custom thumbnails. Video is uploaded; "
                  "set the thumbnail in Studio or retry after fixing auth.")

    if body["status"]["privacyStatus"] != "public":
        print("NOTE: uploaded non-public. If Studio shows it LOCKED private, the GCP "
              "project still needs the YouTube API audit. Once public, run "
              f"`just sync-youtube {ticker}` to stamp the portal meta.")
    else:
        post_first_comment(yt, vid, first_comment_text(ticker), sidecar)
    return 0


def acting_channel(yt):
    items = yt.channels().list(part="snippet", mine=True).execute().get("items", [])
    if not items:
        sys.exit("token has no channel - re-run `just yt-auth` and pick the channel")
    return items[0]["id"], items[0]["snippet"]["title"]


def acting_channel_guard(yt):
    """Print the channel this token acts as; abort on YT_CHANNEL_ID mismatch.
    Brand-account gotcha: the OAuth chooser binds the token to ONE channel -
    picking the personal identity instead of the brand channel uploads to the
    wrong channel entirely. Pin YT_CHANNEL_ID in .env to make that impossible."""
    cid, title = acting_channel(yt)
    print(f"channel:   {title} ({cid})")
    want = os.environ.get("YT_CHANNEL_ID", "").strip()
    if want and cid != want:
        sys.exit(f"ABORT: token is bound to '{title}' ({cid}) but .env pins "
                 f"YT_CHANNEL_ID={want}. Re-run `just yt-auth` and pick the right "
                 "channel on Google's account/channel chooser.")


def cmd_publish(args) -> int:
    """Flip an uploaded video to public - the post-watch-gate step."""
    ticker = args.ticker.upper()
    sc_name = f"{ticker}_short_youtube.json" if getattr(args, "short", False) else f"{ticker}_youtube.json"
    sidecar = REPO / "projects" / ticker / "videos" / sc_name
    if args.id:
        vid = args.id
    elif sidecar.exists():
        vid = json.loads(sidecar.read_text())["video_id"]
    else:
        sys.exit(f"no {sidecar.name} found - pass --id VIDEO_ID")

    from googleapiclient.discovery import build
    yt = build("youtube", "v3", credentials=get_creds(interactive=False))
    acting_channel_guard(yt)
    cur = yt.videos().list(part="status", id=vid).execute()["items"]
    if not cur:
        sys.exit(f"video {vid} not found on this channel")
    status = cur[0]["status"]
    status["privacyStatus"] = "public"
    yt.videos().update(part="status", body={"id": vid, "status": status}).execute()
    print(f"PUBLIC: https://youtu.be/{vid}")
    if sidecar.exists():
        data = json.loads(sidecar.read_text())
        data["privacy"] = "public"
        sidecar.write_text(json.dumps(data, indent=2) + "\n")
    post_first_comment(yt, vid, first_comment_text(ticker), sidecar)
    print(f"next: just sync-youtube {ticker} to stamp the portal meta")
    return 0


def cmd_comment(args) -> int:
    """Post (or re-post with --force) the first comment on an already-uploaded video.
    The backfill path for videos published before this step existed."""
    ticker = args.ticker.upper()
    sc_name = f"{ticker}_short_youtube.json" if getattr(args, "short", False) else f"{ticker}_youtube.json"
    sidecar = REPO / "projects" / ticker / "videos" / sc_name
    if args.id:
        vid = args.id
    elif sidecar.exists():
        vid = json.loads(sidecar.read_text())["video_id"]
    else:
        sys.exit(f"no {sidecar.name} found - pass --id VIDEO_ID")

    text = first_comment_text(ticker, args.text)
    if args.dry_run:
        print(f"video:   https://youtu.be/{vid}")
        print(f"comment: {text}")
        return 0

    from googleapiclient.discovery import build
    yt = build("youtube", "v3", credentials=get_creds(interactive=False))
    acting_channel_guard(yt)
    post_first_comment(yt, vid, text, sidecar, force=args.force)
    return 0


def cmd_auth(_args) -> int:
    creds = get_creds(interactive=True)
    from googleapiclient.discovery import build
    cid, title = acting_channel(build("youtube", "v3", credentials=creds))
    print(f"auth OK - token acts as channel: {title} ({cid})")
    print(f"pin it: add YT_CHANNEL_ID=\"{cid}\" to .env so uploads refuse any other "
          "channel; then try `just yt-upload TICKER --dry-run`")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("auth", help="one-time interactive OAuth")
    up = sub.add_parser("upload", help="upload a project's final video")
    up.add_argument("ticker")
    up.add_argument("--short", action="store_true",
                    help="upload the 9:16 Short (videos/{T}_short.mp4 + social/{T}_short_youtube.txt, "
                         "#Shorts, its own {T}_short_youtube.json sidecar)")
    up.add_argument("--video", help="explicit video path (e.g. webdeck _music variant)")
    up.add_argument("--public", action="store_true")
    up.add_argument("--unlisted", action="store_true")
    up.add_argument("--category", default="27", help="YouTube categoryId (27=Education)")
    up.add_argument("--campaign", help="promo-code campaign override")
    up.add_argument("--dry-run", action="store_true")
    pub = sub.add_parser("publish", help="flip an uploaded video to public")
    pub.add_argument("ticker")
    pub.add_argument("--short", action="store_true", help="publish the Short (its own sidecar)")
    pub.add_argument("--id", help="explicit video id (else videos/{T}_youtube.json)")
    cm = sub.add_parser("comment", help="post the first comment on an uploaded video")
    cm.add_argument("ticker")
    cm.add_argument("--short", action="store_true", help="comment on the Short (its own sidecar)")
    cm.add_argument("--id", help="explicit video id (else the sidecar)")
    cm.add_argument("--text", help="override the comment body ([RESEARCH_URL] resolves)")
    cm.add_argument("--force", action="store_true",
                    help="post even if the sidecar already records a comment_id")
    cm.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.cmd == "auth":
        return cmd_auth(args)
    if args.cmd == "publish":
        return cmd_publish(args)
    if args.cmd == "comment":
        return cmd_comment(args)
    return cmd_upload(args)


if __name__ == "__main__":
    sys.exit(main())
