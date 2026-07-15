"""
Slice a Claude Design deck export (PDF) into per-slide 1920x1080 PNGs.

Claude Design exports a deck as a 16:9 PDF, one slide per page. This rasterizes each
page to a 1920x1080 PNG named by the script's visual_ref (the join key the assemble
step uses). Replaces the old per-HTML screenshot step in deck mode.

Usage:
    # Project mode — reads scripts/{TICKER}_script.json, names PNGs {visual_ref}.png
    uv run python tools/slice_deck.py GTBIF

    # Standalone — slice any PDF to slide-NN.png in an output dir
    uv run python tools/slice_deck.py --pdf path/to/deck.pdf --out path/to/dir

Requires: poppler (pdftoppm, pdfinfo).
"""

import argparse
import glob
import json
import os
import subprocess
import sys
from shutil import copyfile, which

from helpers import get_project_dir

WIDTH, HEIGHT = 1920, 1080
TARGET_RATIO = WIDTH / HEIGHT


def _require_poppler():
    if not all(which(t) for t in ("pdftoppm", "pdfinfo", "pdftotext")):
        sys.exit("ERROR: poppler not found. Install it (macOS: brew install poppler).")


def _page_is_blank(pdf, page_no):
    """True if a page has no extractable text — a blank separator page some PDF
    exports insert between slides. Real slides always carry headline/label text."""
    out = subprocess.run(["pdftotext", "-f", str(page_no), "-l", str(page_no), pdf, "-"],
                         capture_output=True, text=True)
    return not out.stdout.strip()


def _pdfinfo(pdf):
    """Return (page_count, width_pts, height_pts)."""
    out = subprocess.run(["pdfinfo", pdf], capture_output=True, text=True)
    pages = w = h = None
    for line in out.stdout.splitlines():
        if line.startswith("Pages:"):
            pages = int(line.split(":", 1)[1])
        elif line.startswith("Page size:"):
            parts = line.split(":", 1)[1].strip().split()  # "1440 x 810 pts"
            w, h = float(parts[0]), float(parts[2])
    return pages, w, h


def rasterize(pdf, out_dir, prefix="slide"):
    """Rasterize every PDF page to {prefix}-NN.png at 1920x1080. Returns (png_paths, page_count)."""
    if not os.path.exists(pdf):
        sys.exit(f"ERROR: deck PDF not found: {pdf}")
    os.makedirs(out_dir, exist_ok=True)

    pages, w, h = _pdfinfo(pdf)
    if w and h:
        ratio = w / h
        flag = "OK" if abs(ratio - TARGET_RATIO) < 0.02 else "WARN: not 16:9 — forcing size will distort"
        print(f"  Deck: {pages} pages, {w:.0f}x{h:.0f} pts (ratio {ratio:.3f}) — {flag}")

    out_prefix = os.path.join(out_dir, prefix)
    for old in glob.glob(out_prefix + "-*.png"):
        os.remove(old)
    subprocess.run(
        ["pdftoppm", "-png", "-scale-to-x", str(WIDTH), "-scale-to-y", str(HEIGHT), pdf, out_prefix],
        check=True,
    )
    return sorted(glob.glob(out_prefix + "-*.png")), pages


def _png_size(path):
    """(width, height) read from a PNG's IHDR chunk — dependency-free. None if not a PNG."""
    with open(path, "rb") as fh:
        head = fh.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")


def _normalize_png_thumbnail(src, out):
    """Write a 1920x1080 thumbnail from a source PNG. **Center-crops** to 16:9 (never
    distorts) when the source isn't 16:9 — Claude Design's PNG export can come out a few
    percent off. Uses ffmpeg; copies as-is (with a warning) if ffmpeg is unavailable."""
    note = ""
    size = _png_size(src)
    if size:
        w, h = size
        ratio = w / h
        if abs(ratio - TARGET_RATIO) >= 0.02:
            note = (f"  [source {w}x{h}, ratio {ratio:.3f} is NOT 16:9 — center-cropped to fit; "
                    f"eyeball that the hero metric isn't clipped]")
    if which("ffmpeg"):
        # scale to cover, then center-crop to exactly WIDTHxHEIGHT — preserves aspect, no squish
        vf = f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,crop={WIDTH}:{HEIGHT}"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-vf", vf, out], check=True)
    else:
        copyfile(src, out)
        note += "  [ffmpeg not found — copied as-is, NOT resized; install ffmpeg to normalize]"
    print(f"  Thumbnail: deck/{os.path.basename(src)} -> "
          f"charts/png/{os.path.basename(out)} ({WIDTH}x{HEIGHT}){note}")


def rasterize_thumbnail(project_dir, ticker):
    """Produce charts/png/{ticker}_thumbnail.png (1920x1080) from whatever Claude Design
    exported. Two supported inputs, in priority order:
      1. deck/{ticker}_thumbnail.pdf  — rasterized (the original 16:9-PDF path)
      2. deck/{ticker}_thumbnail.png  — center-cropped to 16:9 (fallback for when
         Design's PDF export misbehaves and PNG is the reliable export)
    """
    deck_dir = os.path.join(project_dir, "deck")
    png_dir = os.path.join(project_dir, "charts", "png")
    os.makedirs(png_dir, exist_ok=True)
    out = os.path.join(png_dir, f"{ticker}_thumbnail.png")

    pdf = os.path.join(deck_dir, f"{ticker}_thumbnail.pdf")
    png = os.path.join(deck_dir, f"{ticker}_thumbnail.png")

    if os.path.exists(pdf):
        subprocess.run(
            ["pdftoppm", "-png", "-singlefile", "-scale-to-x", str(WIDTH), "-scale-to-y", str(HEIGHT),
             pdf, os.path.join(png_dir, f"{ticker}_thumbnail")],
            check=True,
        )
        print(f"  Thumbnail: deck/{ticker}_thumbnail.pdf -> charts/png/{ticker}_thumbnail.png ({WIDTH}x{HEIGHT})")
    elif os.path.exists(png):
        _normalize_png_thumbnail(png, out)
    else:
        print(f"  Thumbnail: no deck/{ticker}_thumbnail.pdf or deck/{ticker}_thumbnail.png "
              f"— export it from Claude Design (skipped)")


def slice_standalone(pdf, out_dir):
    print(f"Slicing {os.path.basename(pdf)} -> {out_dir}")
    pngs, _ = rasterize(pdf, out_dir)
    print(f"\nSliced {len(pngs)} slides:")
    for p in pngs:
        print("   ", os.path.basename(p))


def slice_project(project, pdf_override=None):
    project_dir = get_project_dir(project)

    scripts_dir = os.path.join(project_dir, "scripts")
    script_files = [f for f in os.listdir(scripts_dir) if f.endswith("_script.json")]
    if not script_files:
        sys.exit(f"ERROR: no script in {scripts_dir}")
    with open(os.path.join(scripts_dir, script_files[0])) as f:
        script = json.load(f)

    ticker = script.get("metadata", {}).get("ticker", project)
    visual = [s for s in script["segments"] if s.get("type") == "visual"]
    refs = [s["visual_ref"] for s in visual]
    if len(refs) != len(set(refs)):
        sys.exit("ERROR: visual_ref values are not unique — they must be unique, ordered slide ids.")

    source = (script.get("deck") or {}).get("source") or f"deck/{ticker}_deck.pdf"
    pdf = pdf_override or os.path.join(project_dir, source)
    if not os.path.exists(pdf):
        sys.exit(f"ERROR: deck not found: {pdf}\n"
                 f"  Build the deck in Claude Design, export PDF, and save it there.")

    png_dir = os.path.join(project_dir, "charts", "png")
    tmp_dir = os.path.join(png_dir, "_deck_tmp")
    pngs, pages = rasterize(pdf, tmp_dir)

    # Some Claude Design PDF exports interleave a blank separator page after each
    # slide (no @page/print rules in the deck template). Drop text-less pages so the
    # real slides map 1:1 to the script's segments.
    if pages != len(visual):
        kept = [p for i, p in enumerate(pngs, start=1) if not _page_is_blank(pdf, i)]
        if len(kept) == len(visual):
            for p in pngs:
                if p not in kept:
                    os.remove(p)
            print(f"  Dropped {pages - len(kept)} blank separator page(s) from the export")
            pngs, pages = kept, len(kept)

    if pages != len(visual):
        # leave tmp for inspection
        sys.exit(f"ERROR: deck has {pages} pages but the script has {len(visual)} visual "
                 f"segments — they must match. Align the deck or the script.")

    os.makedirs(png_dir, exist_ok=True)
    for ref, src in zip(refs, pngs):
        os.replace(src, os.path.join(png_dir, f"{ref}.png"))
        print(f"   slide -> {ref}.png")
    os.rmdir(tmp_dir)
    print(f"\nSliced {len(refs)} slides into {png_dir}")
    rasterize_thumbnail(project_dir, ticker)


def main():
    _require_poppler()
    ap = argparse.ArgumentParser(description="Slice a Claude Design deck PDF into 1920x1080 slide PNGs")
    ap.add_argument("project", nargs="?", help="Project name (project mode)")
    ap.add_argument("--pdf", help="Path to the deck PDF (overrides project deck.source)")
    ap.add_argument("--out", help="Output dir (standalone mode)")
    args = ap.parse_args()

    if args.out and args.pdf and not args.project:
        slice_standalone(args.pdf, args.out)
    elif args.project:
        slice_project(args.project, pdf_override=args.pdf)
    else:
        ap.error("Provide a PROJECT name, or (--pdf and --out) for standalone.")


if __name__ == "__main__":
    main()
