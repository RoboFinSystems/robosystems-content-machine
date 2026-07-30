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


# ─── Slide/narration coherence ───────────────────────────────
# A one-shot pipeline renders straight from the script, so nobody ever sees an
# intermediate artifact. That makes "the slide says one thing while the voice says
# another" the easiest defect to ship - it happened on RGP's short, where a card read
# "$52M enterprise value" under a burned-in caption about a risk factor. The contract
# has always required slide and narration to agree; nothing enforced it until now.

_STOP = {
    "the", "and", "for", "with", "that", "this", "from", "into", "than", "then",
    "was", "were", "are", "its", "it's", "has", "have", "had", "not", "but", "you",
    "your", "our", "their", "they", "them", "what", "when", "which", "while", "who",
    "how", "why", "all", "any", "one", "two", "out", "off", "over", "under", "just",
    "now", "here", "there", "still", "only", "even", "more", "most", "less", "least",
    "about", "after", "before", "because", "been", "being", "does", "did", "done",
    "can", "could", "would", "should", "will", "may", "might", "must", "per",
}
# slide keys that carry presentation, not content
_SKIP_KEYS = {"tone", "chart_type", "source", "visual_takeaway", "highlight"}


def _content_tokens(text):
    """Lowercase content words (len>2, non-stopword). Digits are stripped out - the
    narration is spoken-form, so '17.5' never literally matches 'seventeen point five'
    and comparing them would be noise."""
    words = re.findall(r"[A-Za-z][A-Za-z'&.]*", str(text).lower())
    return {w.strip("'&.") for w in words
            if len(w.strip("'&.")) > 2 and w.strip("'&.") not in _STOP}


def _slide_text(slide):
    """Every human-readable string in a slide, minus presentation-only keys."""
    out = []

    def walk(node, key=None):
        if key in _SKIP_KEYS:
            return
        if isinstance(node, dict):
            for k, v in node.items():
                if k not in _SKIP_KEYS:
                    out.append(k)          # data keys are on-screen labels
                    walk(v, k)
        elif isinstance(node, list):
            for v in node:
                walk(v, key)
        elif isinstance(node, str):
            out.append(node)

    walk(slide)
    return " ".join(out)


_ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
         "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
         "seventeen", "eighteen", "nineteen"]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]


def _int_words(n):
    """Spoken form of 0-999 (the range slide figures land in once scaled)."""
    if n < 20:
        return _ONES[n]
    if n < 100:
        return (_TENS[n // 10] + (" " + _ONES[n % 10] if n % 10 else "")).strip()
    rest = n % 100
    return (_ONES[n // 100] + " hundred" + (" " + _int_words(rest) if rest else "")).strip()


def _small_forms(num_str):
    """Spoken renderings of a figure under 1000.
    '17.5' -> 'seventeen point five'; '52' -> 'fifty two' / 'fifty-two'."""
    forms = {num_str}
    try:
        whole, _, frac = num_str.partition(".")
        w = int(whole)
        if w > 999:
            return forms
        base = _int_words(w)
        forms.add(base)
        forms.add(base.replace(" ", "-"))
        if frac:
            digits = " ".join(_ONES[int(d)] for d in frac if d.isdigit())
            forms.add(f"{base} point {digits}")
    except (ValueError, IndexError):
        pass
    return forms


def _spoken_forms(num_str):
    """Every way a slide figure might be spoken. Chart `data` carries raw base units
    (revenue $8.2B is stored 8200500000) while narration says "eight point two billion",
    so large values are also matched at their scaled magnitudes."""
    forms = set(_small_forms(num_str))
    try:
        val = float(num_str)
    except ValueError:
        return forms
    for scale in (1e9, 1e6, 1e3):
        if val >= scale:
            for places in (1, 2):
                scaled = round(val / scale, places)
                text = f"{scaled:.{places}f}".rstrip("0").rstrip(".")
                forms |= _small_forms(text)
    return forms


def _slide_numbers(text):
    return re.findall(r"\d+(?:\.\d+)?", text)


# Hooks and CTAs are deliberately punchy and do not restate their narration, so the
# vocabulary test does not apply to them.
_NO_RESTATE = {"hook", "cta"}


def check_slide_narration_coherence(segments, label, narration_key="narration",
                                    slide_key="slide", id_key="id"):
    """Flag any segment whose slide appears to describe something other than its narration.

    A segment passes if EITHER the wording overlaps OR a figure on the slide is spoken in
    the narration. Numbers matter more than words here: good short-form writing avoids
    reading its own slide, so lexical overlap alone produced mostly false positives, but a
    slide showing $52M whose narration never says fifty-two million is genuinely wrong.
    """
    flagged = 0
    for seg in segments:
        slide = seg.get(slide_key) or {}
        narr = seg.get(narration_key) or ""
        kind = (seg.get("kind") or "").lower()
        if kind in _NO_RESTATE or seg.get("visual_ref") == "cta" or not narr:
            continue
        stext = _slide_text(slide)
        s_toks = _content_tokens(stext)
        if not s_toks:
            continue

        shared = s_toks & _content_tokens(narr)
        if len(shared) / len(s_toks) >= 0.15:
            continue

        narr_l = narr.lower()
        if any(any(f in narr_l for f in _spoken_forms(n)) for n in _slide_numbers(stext)):
            continue

        flagged += 1
        face = slide.get("headline") or slide.get("big") or slide.get("kicker") or ""
        warn(f"{label} segment {seg.get(id_key, '?')}: slide shares neither wording nor "
             f"any figure with its narration - do they describe the same thing? "
             f"slide: \"{str(face)[:50]}\"")
    if not flagged:
        ok(f"{label}: every slide agrees with its narration")
    return flagged


def check_brief(project_dir, ticker):
    """Brief-only (tier 1) coverage — the brief IS the deliverable, so it carries the
    checks the script would otherwise cover. `reindex` admits a ticker to the catalog on
    the brief and reads the page title/summary off its leading H1 (which the portal then
    strips from the body), so a missing H1 silently degrades the /research page."""
    print("\n--- Brief ---")
    path = os.path.join(project_dir, "reports", f"{ticker}_brief.md")
    if not os.path.exists(path):
        error(f"Brief missing: reports/{ticker}_brief.md")
        return
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    ok(f"Brief: reports/{ticker}_brief.md ({len(text):,} bytes)")

    lines = text.splitlines()
    if any(ln.startswith("# ") for ln in lines):
        ok("H1 present (becomes the /research page title)")
    else:
        error("No '# ' H1 — the portal takes the page title from it")

    # X Article pickup needs a space-preceded cashtag; "($TICKER)" does not register.
    if re.search(rf"(?:^|\s)\${ticker}\b", "\n".join(lines[:20]), re.M):
        ok(f"${ticker} cashtag in the opening")
    else:
        warn(f"No space-preceded ${ticker} in the first 20 lines — X Article pickup needs one")

    # publish resolves [PROMO_CODE]; anything else in that shape renders literally on /research.
    stray = sorted(set(re.findall(r"\[([A-Z][A-Z0-9_]{3,})\]", text)) - {"PROMO_CODE"})
    if stray:
        error(f"Unresolved placeholder(s) would render literally: {', '.join(stray)}")
    else:
        ok("No unresolved placeholders")


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

    check_slide_narration_coherence(segs, "long-form")

    # The table renderer fits rows into a fixed band above the footer rule. Measured on the
    # 2026-07-29 batch: 6 data rows clear the divider cleanly (ENPH), 7 push the last row
    # down until the footer rule strikes through it (JBLU shipped two such tables, and the
    # struck row was the total - the most important line on the slide). The older 7/9
    # thresholds here were set when the renderer was expected to compute its own padding;
    # it does not, so 6 is the real ceiling. Move a subtotal into the subhead rather than
    # deleting a data row.
    for seg in segs:
        slide = seg.get("slide") or {}
        if slide.get("chart_type") != "table":
            continue
        n = len(((slide.get("data") or {}).get("rows")) or [])
        if n > 6:
            error(f"segment {seg.get('id')}: table has {n} data rows - the footer rule strikes "
                  f"through the last one past 6. Fold a subtotal into the subhead, or split "
                  f"the table across two slides.")

        # A row label that wraps costs a second line of height, so a 6-row table with a long
        # label overflows exactly as a 7-row one does. Whether it wraps depends on the label
        # against the column width, so this is a heuristic: CSBR wrapped a 34-char label in a
        # 4-column table, while ENPH fit 40 chars in a 2-column one where the label column is
        # far wider.
        cols = len(((slide.get("data") or {}).get("columns")) or [])
        if n >= 6 and cols >= 4:
            long_labels = [str(r[0]) for r in ((slide.get("data") or {}).get("rows") or [])
                           if r and len(str(r[0])) > 30]
            if long_labels:
                warn(f"segment {seg.get('id')}: {n}-row, {cols}-column table with a long row "
                     f"label ({long_labels[0]!r}, {len(long_labels[0])} chars) - it may wrap to "
                     f"two lines and push the last row onto the footer. Shorten it to ~28 "
                     f"characters or drop to 5 rows.")

    # `dual` renders <=4 data entries as a 2x2 mini grid and 5+ as a taller stat panel whose
    # last row lands on top of the RoboSystems footer mark. JBLU seg7 printed "-$147M" over
    # the wordmark, illegible. Four is the ceiling; fold the extra stat into the subhead.
    for seg in segs:
        slide = seg.get("slide") or {}
        if seg.get("visual_type") != "dual":
            continue
        n = len(slide.get("data") or {})
        if n > 4:
            error(f"segment {seg.get('id')}: dual slide has {n} data entries - past 4 the stat "
                  f"panel overflows onto the footer mark. Fold one into the subhead or bullets.")

    # `dual` and `callout` stringify their data values (String(v) in buildDual), so an object
    # renders as the literal "[object Object]" and its width shoves the card off the canvas.
    # Only chart_type "metric_cards" takes the {value, change} shape. AEHR shipped three such
    # slides and ENPH two - the two shapes sit next to each other in PRODUCTION_CONTRACT and
    # are easy to transpose. Correct form is "value (note)": splitValue() peels the
    # parenthetical off and renders it as a sub-label, so nothing is lost.
    for seg in segs:
        slide = seg.get("slide") or {}
        kind = seg.get("visual_type")
        if kind not in ("dual", "callout"):
            continue
        for key, val in (slide.get("data") or {}).items():
            if isinstance(val, (dict, list)):
                error(f"segment {seg.get('id')}: {kind} slide data[{key!r}] is a "
                      f"{type(val).__name__} - {kind} renders it as '[object Object]'. Use a "
                      f'flat string like "$116.36M (from $24.53M)"; only metric_cards takes '
                      f"{{value, change}}.")

    # bar and line take a FLAT {label: number} map. A nested shape - most often
    # {"series": {...}} for a multi-line comparison - reads as valid JSON, passes every
    # other check, and then throws mid-render: the values coerce to NaN, the end-of-line
    # label becomes "NaN%", and the count-up parser returns null. LW died three minutes
    # into a fifteen-minute render this way. The shape predates webdeck (Claude Design had
    # a human reading the data), so older scripts still carry it.
    for seg in segs:
        slide = seg.get("slide") or {}
        if slide.get("chart_type") not in ("bar", "line"):
            continue
        data = slide.get("data")
        if not isinstance(data, dict) or not data:
            error(f"segment {seg.get('id')}: {slide.get('chart_type')} chart has no data map")
            continue
        bad = sorted(k for k, v in data.items() if not isinstance(v, (int, float)))
        if bad:
            error(f"segment {seg.get('id')}: {slide.get('chart_type')} chart data must be a flat "
                  f"{{label: number}} map - {', '.join(bad)} is not a number. The renderer draws "
                  f"one series; for a multi-series comparison use a table.")
            continue

        # fmtBarValue prints millions with .toFixed(0), so 80,600,000 draws as "$81M" while
        # the narration says "eighty point six million" - a mismatch no other check can see,
        # because the script's data is correct and only the rendered label is rounded. Put the
        # exact figure in the headline or subhead (AEHR: "Backlog: $15.2M to $80.6M in One
        # Year") and the bar labels read as scale rather than as the claim.
        if slide.get("chart_type") == "bar":
            head = f"{slide.get('headline', '')} {slide.get('subhead', '')}".replace(",", "")
            for key, val in data.items():
                mag = abs(val)
                if not 1e6 <= mag < 1e9:
                    continue
                exact = f"{mag / 1e6:.1f}".rstrip("0").rstrip(".")
                shown = f"{mag / 1e6:.0f}"
                if exact != shown and f"{exact}M" not in head:
                    warn(f"segment {seg.get('id')}: bar {key!r}={val:,} renders as ${shown}M but "
                         f"is ${exact}M - if the narration says the exact figure, put it in the "
                         f"headline or subhead.")

    # Thumbnails are generated by `just thumbnails` into assets/ (yt/x/spot.png), not a script
    # block; the canonical 16:9 charts/png/{ticker}_thumbnail.png is checked with the publish
    # artifacts above.


def check_render_freshness(project_dir, ticker, script):
    """Catch renders/timelines built from stale inputs.

    build_webdeck caches VO durations in videos/media_durations.json. That cache going
    stale against re-voiced audio silently misaligns narration from slides (and can make
    segments overlap), which is invisible in every other check - the schema is still valid
    and the video still plays. Same idea for a final MP4 older than the script it came from.
    """
    print("\n--- Render Freshness ---")
    vids = os.path.join(project_dir, "videos")
    audio_dir = os.path.join(vids, "audio")
    if not os.path.isdir(audio_dir):
        return

    mp3s = [os.path.join(audio_dir, f) for f in os.listdir(audio_dir)
            if f.endswith(".mp3") and "_short_" not in f]
    cache = os.path.join(vids, "media_durations.json")
    if mp3s and os.path.exists(cache):
        stale = [os.path.basename(m) for m in mp3s
                 if os.path.getmtime(m) > os.path.getmtime(cache)]
        if stale:
            error(f"VO duration cache is older than {len(stale)} re-voiced file(s) - "
                  f"rebuild before rendering or narration will drift off its slides "
                  f"(just webdeck {ticker})")
        else:
            ok("VO duration cache is current with the audio")

    final = os.path.join(vids, f"{ticker}_final.mp4")
    spath = os.path.join(project_dir, "scripts", f"{ticker}_script.json")
    # The built HTML is included deliberately: a renderer/template fix changes what the
    # slides look like without touching the script or the audio, so comparing only those
    # two reports a stale video as current. That happened on AMC - the table overflow fix
    # rebuilt the page, the re-render was interrupted, and validate still said PASSED.
    html = os.path.join(project_dir, "webdeck", f"{ticker}_webdeck.html")
    # ...and the sources that GENERATE that page, because comparing to the built page alone
    # only catches a template fix once something happens to rebuild it. Edit the template
    # and every already-rendered project keeps reporting "current" while its slides are
    # built from the old renderer. That is how a broken negative-bar chart nearly shipped.
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    renderer = [os.path.join(repo, "tools", "webdeck", "template.html"),
                os.path.join(repo, "tools", "webdeck", "render_webdeck.mjs"),
                os.path.join(repo, "tools", "build_webdeck.py")]
    if os.path.exists(final) and os.path.exists(spath):
        newer_than = []
        if os.path.getmtime(spath) > os.path.getmtime(final):
            newer_than.append("the script")
        if mp3s and max(os.path.getmtime(m) for m in mp3s) > os.path.getmtime(final):
            newer_than.append("the voiceover")
        if os.path.exists(html) and os.path.getmtime(html) > os.path.getmtime(final):
            newer_than.append("the built webdeck page")
        rsrc = [p for p in renderer
                if os.path.exists(p) and os.path.getmtime(p) > os.path.getmtime(final)]
        if rsrc:
            newer_than.append("the renderer (" +
                              ", ".join(os.path.basename(p) for p in rsrc) + ")")
        if newer_than:
            error(f"{ticker}_final.mp4 is older than {' and '.join(newer_than)} - "
                  f"re-render before publishing (just webdeck-render {ticker} && "
                  f"just webdeck-mux {ticker})")
        else:
            ok("final render is current with the script, audio and built page")


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

    # Measured on both rendered shorts (2026-07-27): ElevenLabs runs ~15-16 chars/sec, and the
    # rendered video lands ~1.1x the narration once transitions and holds are added.
    #   NFLX  688 chars -> 46.6s VO -> 50.2s video (1.08x)
    #   RGP   507 chars -> 31.7s VO -> 35.3s video (1.11x)
    # So a ~45s short is ~41s of narration, about 630 characters.
    chars = sum(len(s.get("narration") or "") for s in segs)
    est = chars / 15.5
    if not (4 <= len(segs) <= 7):
        warn(f"short has {len(segs)} beats (aim for 5-6)")
    if est > 45:
        warn(f"short narration is ~{est:.0f}s ({chars} chars) -> ~{est * 1.1:.0f}s rendered; "
             f"aim under ~630 chars for a ~45s short")
    else:
        ok(f"short: {len(segs)} beats, ~{est:.0f}s narration (~{est * 1.1:.0f}s rendered)")

    check_slide_narration_coherence(segs, "short")

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
    # The freshness check exists to stop a stale video reaching publish. Running it as a
    # pre-render gate is circular: the render is what clears the staleness, so an error
    # here blocks the fix and the pipeline silently keeps the old MP4. webdeck-pipeline
    # passes this; a bare `just validate` still runs the full check.
    parser.add_argument("--pre-render", action="store_true",
                        help="Skip the render-freshness check (the render about to run clears it)")
    # Tier 1 (volume): brief -> /research page, no video. The script-, deck- and
    # render-centric checks below have nothing to inspect, so run only the brief's.
    parser.add_argument("--brief-only", action="store_true",
                        help="Validate a brief-only project (no script/video expected)")
    args = parser.parse_args()

    project_dir = get_project_dir(args.project)
    # Company-centric projects use ticker as project name (e.g., "GTBIF")
    # Legacy projects use TICKER_YEAR_FILING format (e.g., "UBER_2025_10_K")
    ticker = args.project.split("_")[0]

    print(f"{'='*50}")
    print(f"  Validating: {args.project}")
    print(f"{'='*50}")

    if args.brief_only:
        check_brief(project_dir, ticker)
    else:
        check_required_files(project_dir, ticker)
        script = check_script_schema(project_dir, ticker)
        check_deck_contract(project_dir, script)
        check_narration_quality(script)
        check_robosystems_plug(script)
        check_companion_formats(project_dir, ticker, script)
        check_publish_metadata(project_dir, ticker, script)
        if not args.pre_render:
            check_render_freshness(project_dir, ticker, script)

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
