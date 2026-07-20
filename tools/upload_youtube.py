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
Quota: one upload = 1,600 units of the 10,000/day default (about 6 uploads/day).
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


def build_request_parts(ticker: str, args):
    proj = REPO / "projects" / ticker
    script = json.loads((proj / "scripts" / f"{ticker}_script.json").read_text())
    meta = script["metadata"]

    title = meta["video_title"]
    if len(title) > 100:
        sys.exit(f"title is {len(title)} chars (YouTube max 100): {title}")

    desc_path = proj / "social" / f"{ticker}_youtube_description.txt"
    description = desc_path.read_text()
    code = helpers.resolve_promo_code(args.campaign or detect_campaign(proj))
    description = helpers.apply_promo_code(description, code)
    if len(description.encode()) > 5000:
        sys.exit(f"description is {len(description.encode())} bytes (YouTube max 5000)")

    tags, budget = [], 480
    for t in meta.get("tags", []):
        if budget - len(t) < 0:
            break
        tags.append(t)
        budget -= len(t) + 1

    video = Path(args.video) if args.video else proj / "videos" / f"{ticker}_final.mp4"
    if not video.exists():
        sys.exit(f"video not found: {video} (use --video for a webdeck variant)")

    thumb = proj / "charts" / "png" / f"{ticker}_thumbnail.png"

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
    return body, video, (thumb if thumb.exists() else None)


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
    up.add_argument("--video", help="explicit video path (e.g. webdeck _music variant)")
    up.add_argument("--public", action="store_true")
    up.add_argument("--unlisted", action="store_true")
    up.add_argument("--category", default="27", help="YouTube categoryId (27=Education)")
    up.add_argument("--campaign", help="promo-code campaign override")
    up.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    return cmd_auth(args) if args.cmd == "auth" else cmd_upload(args)


if __name__ == "__main__":
    sys.exit(main())
