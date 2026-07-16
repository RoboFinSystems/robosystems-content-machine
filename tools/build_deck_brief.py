"""
Generate the Claude Design hand-off brief from a video script.

Reads scripts/{TICKER}_script.json and renders deck/{TICKER}_deck_brief.md — a clean,
per-slide spec you paste into claude.ai/design to build the deck. Deriving it from the
script (rather than hand-writing it) keeps the hand-off in sync with the source of truth.
In project mode it also copies the full hand-off (DESIGN_INSTRUCTIONS.md + the brief) to
the macOS clipboard, paste-ready into Claude Design (mirrors `just kickoff`).

Usage:
    uv run python tools/build_deck_brief.py GTBIF
    # or standalone:
    uv run python tools/build_deck_brief.py --script path/to/script.json --out path/to/brief.md
"""

import argparse
import json
import os
import shutil
import subprocess
import sys

from helpers import get_project_dir

HOUSE_BRAND = "RoboSystems house brand (blue)"


def humanize(v):
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    if isinstance(v, (int, float)):
        return f"{v:,}"
    return str(v)


def _md_table(columns, rows):
    out = ["| " + " | ".join(str(c) for c in columns) + " |",
           "| " + " | ".join("---" for _ in columns) + " |"]
    for r in rows:
        out.append("| " + " | ".join(humanize(c) for c in r) + " |")
    return "\n".join(out)


# A bar series reads as visually flat when its smallest value is at least this
# fraction of its largest — a zero-baseline chart then shows near-level bars.
# Calibrated against real briefs: PEP revenue (0.85) flags; JEF net revenue (0.53),
# PEP P/E gap (0.62), and JEF IB (0.63) do not. Tune here.
NARROW_RANGE_RATIO = 0.70


def _numeric_values(data):
    """Numeric leaf values of a bar/line `data` map (booleans and non-numbers skipped)."""
    return [v for v in (data or {}).values()
            if isinstance(v, (int, float)) and not isinstance(v, bool)]


def chart_render_hint(chart_type, data):
    """Deterministic rendering guidance for a bar/line slide, derived from the data
    itself so the deck renderer never has to eyeball the scale. Flags negative series
    and visually-flat (narrow-range) series. Returns markdown, or None when N/A."""
    if chart_type not in ("bar", "line"):
        return None
    vals = _numeric_values(data)
    if len(vals) < 2:
        return None
    lo, hi = min(vals), max(vals)
    L = ["**Chart rendering (auto-derived — do not eyeball the scale):**"]
    if lo < 0:
        L.append("- Series has **negative values**: render on a signed axis with a visible "
                 "**zero line** — positive bars above, negatives **below zero in signal red**. "
                 "Never a floor stub or an absolute-value bar.")
    if chart_type == "bar" and lo >= 0:
        ratio = (lo / hi) if hi else 1.0
        if ratio >= NARROW_RANGE_RATIO:
            L.append(f"- **Narrow range** — the smallest value is {round(ratio * 100)}% of the "
                     "largest, so zero-baseline bars read nearly flat. Prefer an **honest reframe** "
                     "that shows the shape (plot the period-over-period change, or a labeled-axis "
                     "line) over a bar race. If you truncate the baseline, the **axis break must be "
                     "visibly marked** and **every bar labeled with its verbatim value**.")
        else:
            L.append("- **Zero baseline**; bar height strictly proportional to value "
                     "(height = value ÷ max × plot area). Equal bar widths and gaps.")
    elif chart_type == "line":
        L.append("- **Fit the y-axis to the data** (a trend line needs no forced zero); **even "
                 "x-spacing**, true slopes between points, and label the axis or the emphasized point.")
    return "\n".join(L)


def render_data(slide):
    """Render a slide's `data` (and bullets) into markdown, faithful to its shape."""
    out = []
    bullets = slide.get("bullets") or []
    if bullets:
        out.append("**Points:**")
        out += [f"- {b}" for b in bullets]
        out.append("")

    data = dict(slide.get("data") or {})
    context = data.pop("context", None)
    chart_type = slide.get("chart_type")

    if data:
        if chart_type == "table" or ("columns" in data and "rows" in data):
            out.append(_md_table(data.get("columns", []), data.get("rows", [])))
        elif "series" in data and isinstance(data["series"], dict):
            for name, series in data["series"].items():
                out.append(f"**{name}**")
                out.append(_md_table(["Label", "Value"], list(series.items())))
                out.append("")
        elif data and all(isinstance(v, dict) for v in data.values()):
            sub = sorted({k for v in data.values() for k in v})
            rows = [[label] + [v.get(k, "") for k in sub] for label, v in data.items()]
            out.append(_md_table(["Metric"] + sub, rows))
        elif isinstance(data, dict):
            out.append(_md_table(["Item", "Value"], list(data.items())))
        else:
            out.append("```json\n" + json.dumps(data, indent=2) + "\n```")

    if context:
        out.append(f"**Context line:** {context}")
    return "\n".join(out).strip()


def build_brief(script):
    meta = script.get("metadata", {})
    ticker = meta.get("ticker", "TICKER")
    company = meta.get("company", ticker)
    segments = [s for s in script.get("segments", []) if s.get("type") == "visual"]
    n = len(segments)

    L = [f"# {company} ({ticker}) — Video Deck Brief", ""]
    L.append(f"> Build a **16:9 presentation deck** in the **RoboSystems Content Design System** "
             f"Claude Design project — **{HOUSE_BRAND}**. Start from its **`video-deck`** template "
             f"(duplicate + fill). Dark theme; every slide **1920×1080**.")
    L.append(f"> Produce **exactly {n} slides**, one per section below, **in this order**. "
             f"Slide kinds used: title / chart / callout / dual.")
    L.append("> Keep every on-screen number EXACTLY as given. Narration is speaker context "
             "(it is *not* shown on the slide). Full conventions: `DESIGN_INSTRUCTIONS.md`.")
    L.append("")
    if meta.get("filing_type"):
        L.append(f"**Filing:** {meta.get('filing_type')} · {meta.get('filing_date','')}  ")
    if meta.get("video_title"):
        L.append(f"**Working title:** {meta['video_title']}")
    L.append("")
    L.append("---")

    for i, seg in enumerate(segments, 1):
        slide = seg.get("slide", {}) or {}
        kind = seg.get("visual_type", "chart")
        ct = slide.get("chart_type")
        kind_label = f"{kind} ({ct})" if ct else kind
        ref = seg.get("visual_ref", f"slide_{i}")
        dur = seg.get("duration_estimate_seconds")

        L.append("")
        L.append(f"## Slide {i} · {kind_label} · `{ref}`")
        if slide.get("headline"):
            label = "Big number" if kind == "callout" else "Headline"
            L.append(f"**{label}:** {slide['headline']}")
        if slide.get("subhead"):
            L.append(f"**Subhead:** {slide['subhead']}")
        if slide.get("visual_takeaway"):
            L.append(f"**Visual takeaway:** {slide['visual_takeaway']}")

        body = render_data(slide)
        if body:
            L.append("")
            L.append(body)

        hint = chart_render_hint(ct, slide.get("data"))
        if hint:
            L.append("")
            L.append(hint)

        extras = []
        if slide.get("highlight"):
            extras.append(f"**Emphasize:** {slide['highlight']}")
        if slide.get("tone"):
            extras.append(f"**Tone:** {slide['tone']}")
        if slide.get("source"):
            extras.append(f"**Source:** {slide['source']}")
        if extras:
            L.append("")
            L += extras

        narration = seg.get("narration", "")
        if narration:
            d = f"~{dur}s" if dur else ""
            L.append("")
            L.append(f"_Narration {d}:_ {narration}")
        L.append("")
        L.append("---")

    L.append("")
    L.append("### After the deck is built (operator: export deck, drop in thumbnails, run pipeline)")
    L.append(f"1. Export the **deck** as PDF (16:9, one slide/page) → `deck/{ticker}_deck.pdf`. "
             f"If Design's PDF export mangles the layout, export PPTX → PowerPoint → PDF instead.")
    L.append(f"2. **Thumbnails** are made in ChatGPT from this brief (not in Claude Design). Drop the "
             f"exports into `assets/`: `yt.png` (16:9 → YouTube + website), `x.png` (5:2 → X), "
             f"`spot.png` (1:1 → Spotify). The pipeline ingests them.")
    L.append(f"3. Run `just pipeline {ticker}` (slices the deck, ingests thumbnails, voices it, renders).")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description="Generate the Claude Design deck brief from a script")
    ap.add_argument("project", nargs="?", help="Project name (project mode)")
    ap.add_argument("--script", help="Path to a script.json (standalone)")
    ap.add_argument("--out", help="Output path for the brief (standalone)")
    args = ap.parse_args()

    if args.script:
        project_dir = None
        with open(args.script) as f:
            script = json.load(f)
        out_path = args.out or os.path.splitext(args.script)[0].replace("_script", "") + "_deck_brief.md"
    elif args.project:
        project_dir = get_project_dir(args.project)
        scripts_dir = os.path.join(project_dir, "scripts")
        files = [f for f in os.listdir(scripts_dir) if f.endswith("_script.json")]
        if not files:
            sys.exit(f"ERROR: no script in {scripts_dir}")
        with open(os.path.join(scripts_dir, files[0])) as f:
            script = json.load(f)
        ticker = script.get("metadata", {}).get("ticker", args.project)
        out_path = os.path.join(project_dir, "deck", f"{ticker}_deck_brief.md")
    else:
        ap.error("Provide a PROJECT name or --script PATH.")

    brief = build_brief(script)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        f.write(brief)
    n = len([s for s in script.get("segments", []) if s.get("type") == "visual"])
    print(f"Wrote deck brief ({n} slides) -> {out_path}")
    copy_design_handoff(project_dir, brief)


def copy_design_handoff(project_dir, brief):
    """Copy the full Design hand-off — DESIGN_INSTRUCTIONS.md + the deck brief — to the
    macOS clipboard so it's paste-ready into Claude Design (mirrors `just kickoff`).
    No-op when pbcopy is unavailable; the brief file is always written regardless."""
    pbcopy = shutil.which("pbcopy")
    if not pbcopy:
        return
    payload, what = brief, "deck brief"
    di = os.path.join(project_dir, "DESIGN_INSTRUCTIONS.md") if project_dir else None
    if di and os.path.exists(di):
        with open(di, encoding="utf-8") as f:
            payload = f.read().rstrip() + "\n\n---\n\n" + brief
        what = "DESIGN_INSTRUCTIONS.md + deck brief"
    subprocess.run([pbcopy], input=payload.encode("utf-8"), check=False)
    print(f"\033[32m✓ Copied to clipboard ({len(payload):,} chars: {what}) — paste into Claude Design.\033[0m")


if __name__ == "__main__":
    main()
