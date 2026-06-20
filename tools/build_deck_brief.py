"""
Generate the Claude Design hand-off brief from a video script.

Reads scripts/{TICKER}_script.json and renders deck/{TICKER}_deck_brief.md — a clean,
per-slide spec you paste into claude.ai/design to build the deck. Deriving it from the
script (rather than hand-writing it) keeps the hand-off in sync with the source of truth.

Usage:
    uv run python tools/build_deck_brief.py GTBIF
    # or standalone:
    uv run python tools/build_deck_brief.py --script path/to/script.json --out path/to/brief.md
"""

import argparse
import json
import os
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
    L.append(f"> Build a **16:9 presentation deck** using the **@robosystems/core** design "
             f"system — **{HOUSE_BRAND}**. Dark theme; every slide **1920×1080**.")
    L.append(f"> Produce **exactly {n} slides**, one per section below, **in this order**. "
             f"Slide kinds used: title / chart / callout / dual.")
    L.append("> Keep every on-screen number EXACTLY as given. Narration is speaker context "
             "(it is *not* shown on the slide).")
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

        body = render_data(slide)
        if body:
            L.append("")
            L.append(body)

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
    L.append("### After you build it")
    L.append("1. Export the deck as **PDF** (16:9).")
    L.append(f"2. Save it to `deck/{ticker}_deck.pdf` in the project.")
    L.append(f"3. Run `just pipeline {ticker}` (slices the deck, voices it, renders the video).")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description="Generate the Claude Design deck brief from a script")
    ap.add_argument("project", nargs="?", help="Project name (project mode)")
    ap.add_argument("--script", help="Path to a script.json (standalone)")
    ap.add_argument("--out", help="Output path for the brief (standalone)")
    args = ap.parse_args()

    if args.script:
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


if __name__ == "__main__":
    main()
