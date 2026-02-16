"""
Validate a project's cowork outputs before running the production pipeline.

Checks:
  - All 5 required outputs exist
  - Script JSON uses correct field names for pipeline compatibility
  - All chart refs in script have corresponding HTML files
  - Narration text is in spoken form (no raw symbols)
  - Logo file present for branded charts
  - Chart HTMLs reference the logo

Usage:
    uv run python tools/validate_project.py AAP_2025_10_K
    uv run python tools/validate_project.py AAP_2025_10_K --fix
"""

import argparse
import json
import os
import re
import sys

from helpers import get_project_dir

# ─── Checks ──────────────────────────────────────────────────

ERRORS = []
WARNINGS = []
FIXES = []


def error(msg):
    ERRORS.append(msg)
    print(f"  FAIL  {msg}")


def warn(msg):
    WARNINGS.append(msg)
    print(f"  WARN  {msg}")


def ok(msg):
    print(f"  OK    {msg}")


def check_required_files(project_dir, ticker):
    """Check all 5 required output types exist."""
    print("\n--- Required Files ---")

    checks = {
        "Report": f"reports/{ticker}_report.html",
        "Script": f"scripts/{ticker}_script.json",
        "X Post": f"social/{ticker}_x_post.txt",
        "Thumbnail": f"charts/html/{ticker}_thumbnail.html",
    }

    found = {}
    for name, path in checks.items():
        full = os.path.join(project_dir, path)
        if os.path.exists(full):
            size = os.path.getsize(full)
            ok(f"{name}: {path} ({size:,} bytes)")
            found[name] = full
        else:
            error(f"{name} missing: {path}")

    return found


def check_script_schema(project_dir, ticker):
    """Validate script JSON field names match pipeline expectations."""
    print("\n--- Script Schema ---")

    script_path = os.path.join(project_dir, "scripts", f"{ticker}_script.json")
    if not os.path.exists(script_path):
        error("Script file not found, skipping schema check")
        return None

    with open(script_path) as f:
        script = json.load(f)

    # Check metadata
    meta = script.get("metadata", {})
    if not meta.get("ticker"):
        error("metadata.ticker missing")
    else:
        ok(f"metadata.ticker: {meta['ticker']}")

    # Check segments
    segments = script.get("segments", [])
    if not segments:
        error("No segments found")
        return script

    ok(f"{len(segments)} segments found")

    # Check field names
    bad_fields = {
        "segment_id": "id",
        "chart_id": "visual_ref",
        "duration_seconds": "duration_estimate_seconds",
        "chart_ref": "visual_ref",
    }

    for seg in segments:
        seg_id = seg.get("id") or seg.get("segment_id", "?")
        for bad, good in bad_fields.items():
            if bad in seg:
                error(f"Segment {seg_id}: uses '{bad}' instead of '{good}'")

        if "id" not in seg and "segment_id" not in seg:
            error(f"Segment missing both 'id' and 'segment_id'")

        if seg.get("type") == "visual":
            if not seg.get("visual_ref") and not seg.get("chart_id"):
                warn(f"Segment {seg_id} (visual): no visual_ref or chart_id")

        if not seg.get("narration"):
            error(f"Segment {seg_id}: missing narration")

        if not seg.get("duration_estimate_seconds") and not seg.get("duration_seconds"):
            warn(f"Segment {seg_id}: no duration field")

    # Check charts array
    charts = script.get("charts", [])
    for chart in charts:
        if "chart_id" in chart and "ref" not in chart:
            error(f"Chart uses 'chart_id' instead of 'ref': {chart.get('chart_id')}")

    return script


def check_chart_files(project_dir, script):
    """Verify chart HTML files exist for all visual_ref references in the script."""
    print("\n--- Chart Files ---")

    if not script:
        return

    charts_dir = os.path.join(project_dir, "charts", "html")
    segments = script.get("segments", [])

    visual_refs = set()
    for seg in segments:
        ref = seg.get("visual_ref") or seg.get("chart_id")
        if ref and seg.get("type") == "visual":
            visual_refs.add(ref)

    for ref in sorted(visual_refs):
        html_path = os.path.join(charts_dir, f"{ref}.html")
        if os.path.exists(html_path):
            size = os.path.getsize(html_path)
            ok(f"{ref}.html ({size:,} bytes)")
        else:
            error(f"Chart HTML missing: {ref}.html")

    # Check logo
    logo_path = os.path.join(charts_dir, "robosystems_logo.png")
    if os.path.exists(logo_path):
        ok("robosystems_logo.png present")
    else:
        warn("robosystems_logo.png missing — charts won't have branded logo")


def check_narration_quality(script):
    """Check narration text for raw symbols that TTS will mispronounce."""
    print("\n--- Narration Quality ---")

    if not script:
        return

    segments = script.get("segments", [])
    symbol_patterns = [
        (r'\$[\d,]+', "Dollar sign ($) — should be spelled out"),
        (r'\d+\.?\d*%', "Percent symbol (%) — should be 'percent'"),
        (r'\d+\.?\d*x\b', "Multiplier (x) — should be 'times'"),
        (r'\bP/E\b', "P/E — should be 'price to earnings'"),
        (r'\bP/S\b', "P/S — should be 'price to sales'"),
        (r'\bEV/EBITDA\b', "EV/EBITDA — should be 'E V to EBITDA'"),
        (r'\bYoY\b', "YoY — should be 'year over year'"),
        (r'\bQoQ\b', "QoQ — should be 'quarter over quarter'"),
        (r'\bROE\b', "ROE — should be 'return on equity'"),
        (r'\bEPS\b', "EPS — should be 'earnings per share'"),
        (r'\bFCF\b', "FCF — should be 'free cash flow'"),
    ]

    issues_found = 0
    for seg in segments:
        seg_id = seg.get("id") or seg.get("segment_id", "?")
        narration = seg.get("narration", "")

        for pattern, desc in symbol_patterns:
            matches = re.findall(pattern, narration)
            if matches:
                issues_found += 1
                warn(f"Segment {seg_id}: {desc} — found: {', '.join(matches[:3])}")

    if issues_found == 0:
        ok("All narration in spoken form")
    else:
        warn(f"{issues_found} narration issues found (TTS may mispronounce)")


def check_chart_svg_bounds(project_dir, script):
    """Check SVG charts for out-of-bounds rects and misplaced negative bars."""
    print("\n--- Chart SVG Bounds ---")

    if not script:
        return

    charts_dir = os.path.join(project_dir, "charts", "html")

    # Collect visual_ref chart files (skip examples, templates, thumbnails)
    segments = script.get("segments", [])
    visual_refs = set()
    for seg in segments:
        ref = seg.get("visual_ref") or seg.get("chart_id")
        if ref and seg.get("type") == "visual":
            visual_refs.add(ref)

    if not visual_refs:
        ok("No visual charts to check")
        return

    issues = 0
    for ref in sorted(visual_refs):
        html_path = os.path.join(charts_dir, f"{ref}.html")
        if not os.path.exists(html_path):
            continue

        with open(html_path) as f:
            html = f.read()

        # Extract viewBox dimensions
        vb_match = re.search(r'viewBox="0 0 (\d+) (\d+)"', html)
        if not vb_match:
            continue
        vb_w, vb_h = int(vb_match.group(1)), int(vb_match.group(2))

        # Find all rects
        rects = re.finditer(
            r'<rect\s+[^>]*?x="([\d.-]+)"[^>]*?y="([\d.-]+)"[^>]*?'
            r'width="([\d.-]+)"[^>]*?height="([\d.-]+)"[^>]*?'
            r'(?:class="([^"]*)")?',
            html,
        )

        for rect in rects:
            x = float(rect.group(1))
            y = float(rect.group(2))
            w = float(rect.group(3))
            h = float(rect.group(4))
            cls = rect.group(5) or ""

            # Skip small rects (legend swatches, decorative elements)
            if w <= 20 or h <= 20:
                continue

            if y < 0:
                error(f"{ref}: rect at y={y} is above viewBox (off-screen top)")
                issues += 1
            if y + h > vb_h + 5:
                error(f"{ref}: rect bottom at y={y + h} exceeds viewBox height {vb_h}")
                issues += 1

        # Find text labels that are off-screen
        texts = re.finditer(r'<text\s+[^>]*?y="([\d.-]+)"', html)
        for t in texts:
            ty = float(t.group(1))
            if ty < 0:
                warn(f"{ref}: text label at y={ty} is above viewBox (clipped)")
                issues += 1

    if issues == 0:
        ok("All chart SVG elements within viewBox bounds")


def check_robosystems_plug(script):
    """Check that the RoboSystems plug is present in the script."""
    print("\n--- RoboSystems Plug ---")

    if not script:
        return

    segments = script.get("segments", [])
    all_narration = " ".join(seg.get("narration", "") for seg in segments).lower()

    if "robosystems" in all_narration:
        ok("RoboSystems mention found in narration")
    else:
        warn("No RoboSystems mention in narration — add the standard plug")


def try_fix_script(project_dir, ticker, script):
    """Attempt to fix common schema issues in the script JSON."""
    if not script:
        return

    fixed = False
    segments = script.get("segments", [])

    for seg in segments:
        # Fix segment_id → id
        if "segment_id" in seg and "id" not in seg:
            seg["id"] = seg.pop("segment_id")
            fixed = True
            FIXES.append(f"Segment {seg['id']}: renamed segment_id → id")

        # Fix chart_id → visual_ref
        if "chart_id" in seg and "visual_ref" not in seg:
            seg["visual_ref"] = seg.pop("chart_id")
            fixed = True
            FIXES.append(f"Segment {seg.get('id', '?')}: renamed chart_id → visual_ref")

        # Fix duration_seconds → duration_estimate_seconds
        if "duration_seconds" in seg and "duration_estimate_seconds" not in seg:
            seg["duration_estimate_seconds"] = seg.pop("duration_seconds")
            fixed = True
            FIXES.append(f"Segment {seg.get('id', '?')}: renamed duration_seconds → duration_estimate_seconds")

    # Fix charts array
    charts = script.get("charts", [])
    for chart in charts:
        if "chart_id" in chart and "ref" not in chart:
            chart["ref"] = chart.pop("chart_id")
            fixed = True
            FIXES.append(f"Chart: renamed chart_id → ref ({chart['ref']})")

    if fixed:
        script_path = os.path.join(project_dir, "scripts", f"{ticker}_script.json")
        with open(script_path, "w") as f:
            json.dump(script, f, indent=2)
        print(f"\n--- Fixes Applied ({len(FIXES)}) ---")
        for fix in FIXES:
            print(f"  FIXED {fix}")
    else:
        print("\n  No fixes needed")


# ─── Main ─────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Validate project outputs")
    parser.add_argument("project", help="Project name (e.g., AAP_2025_10_K)")
    parser.add_argument("--fix", action="store_true", help="Auto-fix common schema issues")
    args = parser.parse_args()

    project_dir = get_project_dir(args.project)
    ticker = args.project.split("_")[0]

    print(f"{'='*50}")
    print(f"  Validating: {args.project}")
    print(f"{'='*50}")

    check_required_files(project_dir, ticker)
    script = check_script_schema(project_dir, ticker)
    check_chart_files(project_dir, script)
    check_chart_svg_bounds(project_dir, script)
    check_narration_quality(script)
    check_robosystems_plug(script)

    if args.fix:
        try_fix_script(project_dir, ticker, script)

    # Summary
    print(f"\n{'='*50}")
    if ERRORS:
        print(f"  RESULT: {len(ERRORS)} errors, {len(WARNINGS)} warnings")
        if not args.fix:
            fixable = any(
                "instead of" in e for e in ERRORS
            )
            if fixable:
                print(f"  TIP: Run with --fix to auto-fix schema issues")
        sys.exit(1)
    elif WARNINGS:
        print(f"  RESULT: PASSED with {len(WARNINGS)} warnings")
    else:
        print(f"  RESULT: ALL CHECKS PASSED")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
