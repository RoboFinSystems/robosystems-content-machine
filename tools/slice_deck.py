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
from shutil import which

from helpers import get_project_dir

WIDTH, HEIGHT = 1920, 1080
TARGET_RATIO = WIDTH / HEIGHT


def _require_poppler():
    if not which("pdftoppm") or not which("pdfinfo"):
        sys.exit("ERROR: poppler not found. Install it (macOS: brew install poppler).")


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


def rasterize_thumbnail(project_dir, ticker):
    """Rasterize the Claude Design thumbnail PDF -> charts/png/{ticker}_thumbnail.png (1920x1080).

    Claude Design exports PDF only, so the thumbnail is exported as a 16:9 PDF
    (deck/{ticker}_thumbnail.pdf) and rasterized here — no manual pdftoppm step.
    """
    pdf = os.path.join(project_dir, "deck", f"{ticker}_thumbnail.pdf")
    if not os.path.exists(pdf):
        print(f"  Thumbnail: no deck/{ticker}_thumbnail.pdf — export it from Claude Design (skipped)")
        return
    png_dir = os.path.join(project_dir, "charts", "png")
    os.makedirs(png_dir, exist_ok=True)
    out_root = os.path.join(png_dir, f"{ticker}_thumbnail")
    subprocess.run(
        ["pdftoppm", "-png", "-singlefile", "-scale-to-x", str(WIDTH), "-scale-to-y", str(HEIGHT),
         pdf, out_root],
        check=True,
    )
    print(f"  Thumbnail: deck/{ticker}_thumbnail.pdf -> charts/png/{ticker}_thumbnail.png ({WIDTH}x{HEIGHT})")


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
