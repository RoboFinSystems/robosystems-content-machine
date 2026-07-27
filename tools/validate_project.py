"""
Validate a project's authored outputs before running the webdeck pipeline.

Checks:
  - The script exists; publish artifacts (brief, X post, thumbnail) are noted if missing
  - Script JSON uses correct field names for pipeline compatibility
  - Slide contract: slide_count == visual segments, unique/ordered visual_ref, one cta
  - The 9:16 short script: known kinds, narration present, length in range, social copy
  - Narration is in spoken form (no raw symbols / bad TTS spacings)
  - Publish metadata (social/{ticker}_publish.json) has the fields postpack needs
  - Continuing coverage: a coverage_label when a prior-coverage card is present

Usage:
    uv run python tools/validate_project.py GTBIF
    uv run python tools/validate_project.py GTBIF --fix
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
    """Check outputs. Only the script is required to render; the rest are publish artifacts."""
    print("\n--- Required Files ---")

    # Report can be either HTML (generic) or markdown brief (campaign)
    report_html = f"reports/{ticker}_report.html"
    report_md = f"reports/{ticker}_brief.md"
    report_path = report_html
    if os.path.exists(os.path.join(project_dir, report_md)):
        report_path = report_md
    elif not os.path.exists(os.path.join(project_dir, report_html)):
        report_path = report_md  # will show as missing

    required = {"Script": f"scripts/{ticker}_script.json"}
    # Publish artifacts — needed to ship, not to render. Thumbnail is made in ChatGPT (assets/).
    recommended = {
        "Report/Brief": report_path,
        "X Post": f"social/{ticker}_x_post.txt",
        "Thumbnail": f"charts/png/{ticker}_thumbnail.png",
    }
    found = {}
    for name, path in required.items():
        full = os.path.join(project_dir, path)
        if os.path.exists(full):
            ok(f"{name}: {path} ({os.path.getsize(full):,} bytes)")
            found[name] = full
        else:
            error(f"{name} missing: {path}")

    for name, path in recommended.items():
        full = os.path.join(project_dir, path)
        if os.path.exists(full):
            ok(f"{name}: {path} ({os.path.getsize(full):,} bytes)")
            found[name] = full
        else:
            warn(f"{name} missing (needed to publish, not to render): {path}")

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

    # Continuing coverage: if `just recover` emitted a prior-coverage card, the script
    # should carry a coverage_label for the version thread (e.g. "Q2 FY2026 update").
    if os.path.exists(os.path.join(project_dir, "sources", "_prior_coverage.md")):
        if meta.get("coverage_label"):
            ok(f"continuing coverage: coverage_label = {meta['coverage_label']}")
        else:
            warn("continuing coverage (sources/_prior_coverage.md present) but metadata.coverage_label not set")

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
        (r'\bA I\b', 'Spaced "A I" — TTS reads it as the word "ai"; use "AI" or "A.I."'),
        (r'\bD E A\b', 'Spaced "D E A" — TTS drags it; spell out "Drug Enforcement Administration"'),
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


def check_deck_contract(project_dir, script):
    """Validate the script↔slide contract the webdeck renderer depends on."""
    print("\n--- Slide Contract ---")
    if not script:
        return

    segs = [s for s in script.get("segments", []) if s.get("type") == "visual"]
    refs = [s.get("visual_ref") for s in segs]

    if not all(refs):
        error("Some visual segments are missing visual_ref")
    elif len(refs) != len(set(refs)):
        dupes = sorted({r for r in refs if refs.count(r) > 1})
        error(f"visual_ref not unique: {', '.join(dupes)}")
    else:
        ok(f"{len(refs)} unique, ordered visual_ref slide ids")

    deck = script.get("deck", {})
    declared = deck.get("slide_count")
    if declared is not None and declared != len(segs):
        error(f"deck.slide_count={declared} but {len(segs)} visual segments — must match")
    elif declared is not None:
        ok(f"deck.slide_count matches segment count ({len(segs)})")
    else:
        warn("deck.slide_count not set (set it to the number of visual segments)")

    # The webdeck renderer draws every slide from the script, so there is no deck artifact
    # to check. `visual_ref: "cta"` selects the CTA layout, so the closing segment should
    # claim it and nothing else should.
    cta_refs = [r for r in refs if r == "cta"]
    if len(cta_refs) > 1:
        error("visual_ref 'cta' used more than once — it selects the CTA layout")
    elif not cta_refs:
        warn("no segment uses visual_ref 'cta' — the closing segment normally does")
    elif refs[-1] != "cta":
        warn("visual_ref 'cta' is not the last segment — it renders the closing layout")
    else:
        ok("closing segment uses the cta layout")

    # Thumbnails are generated by `just thumbnails` into assets/ (yt/x/spot.png), not a script
    # block; the canonical 16:9 charts/png/{ticker}_thumbnail.png is checked with the publish
    # artifacts above.


def _load_manifest_ids(rel_path):
    """Return the set of ids in a shared assets manifest (repo-root relative)."""
    items = _load_manifest_items(rel_path)
    return {item["id"] for item in items} if items is not None else None


def _load_manifest_items(rel_path):
    """Return the list of entries in a shared assets manifest (repo-root relative)."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, rel_path)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


SHORT_KINDS = {"hook", "stat", "cards", "points", "cta"}


def check_companion_formats(project_dir, ticker, script):
    """Validate the 9:16 short script — required for every name since 2026-07-21."""
    print("\n--- Companion Format (9:16 short) ---")

    path = os.path.join(project_dir, "scripts", f"{ticker}_short_script.json")
    if not os.path.exists(path):
        warn(f"short script missing: scripts/{ticker}_short_script.json "
             f"(needed for `just webdeck-short-pipeline`, not for the long-form render)")
        return

    try:
        with open(path) as f:
            short = json.load(f)
    except json.JSONDecodeError as e:
        error(f"short script invalid JSON: {e}")
        return

    segs = short.get("segments") or []
    if not segs:
        error("short script has no segments")
        return

    bad_kind = [f"{s.get('id', '?')}:{s.get('kind')}" for s in segs
                if s.get("kind") not in SHORT_KINDS]
    if bad_kind:
        error(f"short: unknown kind(s) {', '.join(bad_kind)} — "
              f"use {' | '.join(sorted(SHORT_KINDS))}")
    if any(not str(s.get("narration") or "").strip() for s in segs):
        error("short: every segment needs narration (captions derive from it)")
    if any(not isinstance(s.get("slide"), dict) for s in segs):
        error("short: every segment needs a slide object")

    # ~15.5 chars/sec is the pace build_webdeck_short.py estimates with. The RENDERED short
    # runs longer than its narration once transitions and holds are added: the NFLX pilot was
    # ~44s of narration and a 63s video, so ~1.4x. Target a ~45s video => ~32s of narration.
    chars = sum(len(s.get("narration") or "") for s in segs)
    est = chars / 15.5
    if not (4 <= len(segs) <= 7):
        warn(f"short has {len(segs)} beats (aim for 5-6)")
    if est > 35:
        warn(f"short narration is ~{est:.0f}s ({chars} chars) -> ~{est * 1.4:.0f}s rendered; "
             f"aim ~32s of narration for a ~45s short")
    else:
        ok(f"short: {len(segs)} beats, ~{est:.0f}s narration (~{est * 1.4:.0f}s rendered)")

    for name in (f"social/{ticker}_short_x_post.txt", f"social/{ticker}_short_youtube.txt"):
        if not os.path.exists(os.path.join(project_dir, name)):
            warn(f"short social copy missing: {name}")


def check_publish_metadata(project_dir, ticker, script):
    """Validate social/{ticker}_publish.json — the per-platform copy postpack stitches.
    Missing is a warning (needed to publish, not to render); malformed/incomplete is flagged."""
    print("\n--- Publish Metadata (social/{ticker}_publish.json) ---".replace("{ticker}", ticker))

    path = os.path.join(project_dir, "social", f"{ticker}_publish.json")
    if not os.path.exists(path):
        warn(f"publish.json missing (needed for postpack, not to render): social/{ticker}_publish.json")
        return None

    try:
        with open(path) as f:
            pub = json.load(f)
    except json.JSONDecodeError as e:
        error(f"publish.json invalid JSON: {e}")
        return None

    # the 9:16 short carries its own copy in social/{t}_short_x_post.txt and
    # social/{t}_short_youtube.txt (checked in check_companion_formats), not in publish.json
    expected = [
        "youtube_title",
        "x_first_comment",
    ]

    missing = [k for k in expected if not str(pub.get(k) or "").strip()]
    if missing:
        warn(f"publish.json missing/empty: {', '.join(missing)}")
    else:
        ok(f"publish.json: all {len(expected)} expected fields present")

    # Fields retired in the 2026-06 distribution rework — nudge to drop them.
    # (LinkedIn is reserved for the technical/blog lane; research analysis doesn't post there.)
    stale = [k for k in ("instagram_caption", "x_first_reply",
                         "linkedin_post", "linkedin_first_comment") if k in pub]
    if stale:
        warn(f"publish.json has retired fields (Instagram cut; LinkedIn → technical lane; first-reply → x_first_comment): {', '.join(stale)}")

    return pub


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
    # Company-centric projects use ticker as project name (e.g., "GTBIF")
    # Legacy projects use TICKER_YEAR_FILING format (e.g., "UBER_2025_10_K")
    ticker = args.project.split("_")[0]

    print(f"{'='*50}")
    print(f"  Validating: {args.project}")
    print(f"{'='*50}")

    check_required_files(project_dir, ticker)
    script = check_script_schema(project_dir, ticker)
    check_deck_contract(project_dir, script)
    check_narration_quality(script)
    check_robosystems_plug(script)
    check_companion_formats(project_dir, ticker, script)
    check_publish_metadata(project_dir, ticker, script)

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
