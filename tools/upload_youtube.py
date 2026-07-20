#!/usr/bin/env python3
"""Upload a project's final video to YouTube via the Data API v3.

One-time:  just yt-auth              interactive browser OAuth; stores .gcp/token.json
Then:      just yt-upload TICKER     upload + thumbnail + chapters/tags, PRIVATE by default

Auth notes (web-type OAuth client at .gcp/secret.json):
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
import sys
from pathlib import Path

import helpers

REPO = Path(__file__).resolve().parent.parent
SECRET = REPO / ".gcp" / "secret.json"
TOKEN = REPO / ".gcp" / "token.json"
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]
OAUTH_PORT = 8090
THUMB_MAX_BYTES = 2 * 1024 * 1024   # YouTube custom-thumbnail hard limit


def get_creds(interactive: bool):
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    creds = None
    if TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN.write_text(creds.to_json())
        return creds
    if not interactive:
        sys.exit("no valid YouTube token - run `just yt-auth` first")

    from google_auth_oauthlib.flow import InstalledAppFlow
    flow = InstalledAppFlow.from_client_secrets_file(str(SECRET), SCOPES)
    try:
        creds = flow.run_local_server(port=OAUTH_PORT, access_type="offline",
                                      prompt="consent")
    except Exception as e:
        sys.exit(f"OAuth flow failed ({e}).\nIf this is redirect_uri_mismatch: add "
                 f"http://localhost:{OAUTH_PORT}/ to the client's authorized redirect "
                 "URIs in the GCP console, or download a Desktop-app client secret.")
    TOKEN.write_text(creds.to_json())
    print(f"token stored: {TOKEN}")
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
        yt.thumbnails().set(videoId=vid, media_body=str(prepared_thumbnail(thumb))).execute()
        print("thumbnail set")

    if body["status"]["privacyStatus"] != "public":
        print("NOTE: uploaded non-public. If Studio shows it LOCKED private, the GCP "
              "project still needs the YouTube API audit. Once public, run "
              f"`just sync-youtube {ticker}` to stamp the portal meta.")
    return 0


def cmd_auth(_args) -> int:
    get_creds(interactive=True)
    print("auth OK - try: just yt-upload TICKER --dry-run")
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
