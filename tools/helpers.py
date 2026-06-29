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
