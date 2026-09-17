"""
Card-sized webp variants of a research thumbnail.

The research thumbnail is a 1920x1080 PNG, 2.6 MB at the median and 3.3 MB at the
largest. The /research grid used to hand it to next/image, which decoded and shrank
it on a 0.25 vCPU App Runner instance at 0.4-1.5 s of CPU per image. A screen of cards
kept the server busy for about 20 s, and clicks waited behind it (measured on prod
2026-09-16). These variants are published next to the PNG so the card loads them
straight from the CDN and the app does no image work at all.

Two widths, picked by the browser from `srcSet`: 800 covers a ~400px desktop card at 2x,
1200 covers a full-width phone card at 3x. At quality 80 they run 52-85 KB and
90-158 KB against the PNG's megabytes. The PNG stays the social and search image.

Usage:
    uv run python tools/card_thumbnails.py projects/MSFT/charts/png/MSFT_thumbnail.png
"""

import os
import sys

from PIL import Image

CARD_WIDTHS = (800, 1200)
CARD_QUALITY = 80


def card_path(png_path, width):
  """projects/T/charts/png/T_thumbnail.png -> .../T_thumbnail_card_800.webp"""
  stem, _ = os.path.splitext(png_path)
  return f"{stem}_card_{width}.webp"


def write_card_webps(png_path):
  """Write every card width next to the PNG. Returns the paths written.

  Always rewrites: a thumbnail re-rendered under the same name must not leave a stale
  card behind, and a pass costs well under a second.
  """
  with Image.open(png_path) as src:
    image = src.convert("RGB")
    written = []
    for width in CARD_WIDTHS:
      height = round(width * image.height / image.width)
      out = card_path(png_path, width)
      image.resize((width, height), Image.LANCZOS).save(
        out, "WEBP", quality=CARD_QUALITY, method=6
      )
      written.append(out)
  return written


def main():
  if len(sys.argv) != 2:
    raise SystemExit("usage: card_thumbnails.py <path/to/T_thumbnail.png>")
  for out in write_card_webps(sys.argv[1]):
    print(f"  {out}  ({os.path.getsize(out) / 1e3:.0f} KB)")


if __name__ == "__main__":
  main()
