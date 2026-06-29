"""
Shared helpers for the content pipeline tools.

Environment variables are loaded by uv via UV_ENV_FILE — see the justfile
and shell scripts. These are just convenience functions.
"""

import os
import re
import sys


def get_project_dir(project_name):
  """Get the absolute path to a project directory."""
  root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
  project_dir = os.path.join(root_dir, "projects", project_name)
  if not os.path.isdir(project_dir):
    raise FileNotFoundError(f"Project not found: {project_dir}")
  return project_dir


def require_env(key):
  """Get a required environment variable or exit."""
  val = os.environ.get(key)
  if not val:
    print(f"Error: {key} not set. Check your .env file.")
    sys.exit(1)
  return val


def cdn_base():
  """Public base URL that published assets are served from.

  Prefers the CloudFront custom domain (AWS_CDN_DOMAIN_URL, e.g.
  "https://assets.robosystems.ai"); falls back to the raw S3 endpoint (the bucket is
  public-read) so URLs still resolve before the content CDN stack is deployed.
  """
  cdn = os.environ.get("AWS_CDN_DOMAIN_URL", "").strip().rstrip("/")
  if cdn:
    return cdn
  return f"https://{require_env('AWS_S3_BUCKET')}.s3.amazonaws.com"


def asset_url(key):
  """Public URL for an object key in the content bucket (e.g. "content/AAPL/x.mp4")."""
  return f"{cdn_base()}/{key.lstrip('/')}"


# ─── TTS text normalization ──────────────────────────────────────────────────
# ElevenLabs mispronounces some finance terms when fed verbatim. We respell them
# ONLY for the spoken audio — slides, briefs, and on-screen text keep the real
# spelling. Applied centrally in generate_audio(), so voiceover + podcast + short
# all inherit it. Add new (pattern, replacement) pairs here as they surface.
_TTS_SUBSTITUTIONS = [
  (re.compile(r"\bEBITDA\b", re.IGNORECASE), "Ebit-dah"),  # else read letter-by-letter
]


def normalize_for_tts(text):
  """Respell mispronounced terms before sending text to the TTS API."""
  for pattern, replacement in _TTS_SUBSTITUTIONS:
    text = pattern.sub(replacement, text)
  return text


# ─── Promo code resolution ───────────────────────────────────────────────────
# Social copy + briefs carry a literal "[PROMO_CODE]" placeholder so the real
# Stripe code is never committed to the repo. Distribution outputs must resolve it
# before going public — the published brief especially, which is auto-uploaded to
# the portal with NO human fill-in gate (unlike the social copy you paste by hand).
# Real codes live in .env (gitignored): PROMO_CODE_CANNABIS / PROMO_CODE_DEFAULT,
# or PROMO_CODE to force one. No code configured -> the promo sentence is dropped,
# so a raw placeholder never leaks to production either way.
def resolve_promo_code(campaign=None):
  """Live promo code for distribution outputs, read from .env. Cannabis campaign
  -> PROMO_CODE_CANNABIS, else PROMO_CODE_DEFAULT; PROMO_CODE overrides both.
  Returns None when nothing is configured (no promo running)."""
  override = os.environ.get("PROMO_CODE", "").strip()
  if override:
    return override
  key = "PROMO_CODE_CANNABIS" if "cannabis" in (campaign or "").lower() else "PROMO_CODE_DEFAULT"
  return os.environ.get(key, "").strip() or None


def apply_promo_code(text, code):
  """Resolve [PROMO_CODE] in distribution text. With a code -> substitute; with
  none -> drop the sentence carrying the placeholder so nothing leaks to production."""
  if not text or "[PROMO_CODE]" not in text:
    return text
  if code:
    return text.replace("[PROMO_CODE]", code)
  text = re.sub(r"\s*[^.\n]*\[PROMO_CODE\][^.\n]*\.", "", text)
  return text.replace("[PROMO_CODE]", "")


def strip_angle_brackets(text):
  """YouTube and X reject `<` / `>` (parsed as HTML tags) — pasting copy that contains
  them errors out. In finance copy they're always comparison operators, so spell them
  out: '<1x' -> 'under 1x', '>$740M' -> 'over $740M', capitalizing at a sentence start.
  A safety net — authored copy should avoid `< >` outright (see COWORK instructions)."""
  if not text or ("<" not in text and ">" not in text):
    return text
  out = re.sub(r"<\s*", "under ", text)
  out = re.sub(r">\s*", "over ", out)
  # a comparison promoted to sentence-initial should be capitalized
  return re.sub(r"(^|[.!?]\s+)(under|over)\b", lambda m: m.group(1) + m.group(2).capitalize(), out)
