#!/usr/bin/env python3
"""Build a self-contained 9:16 animated SHORT from a project's short script.

The vertical companion to build_webdeck.py: same deterministic __seek(t) engine,
a 1080x1920 stage, purpose-built for muted autoplay (burned-in kinetic captions).
Reads projects/{T}/scripts/{T}_short_script.json and the short VO segments, then
writes projects/{T}/webdeck/{T}_short.html + a mux manifest.

Timing model (snappier than the long-form):
  lead-in 0.25s · gap 0.35s between beats · 0.35s crossfade · 1.6s tail · 0.7s fade

Usage: python3 tools/build_webdeck_short.py TICKER
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DS = REPO / "design-system"

LEAD_IN = 0.25
GAP = 0.35
TRANS = 0.35
TAIL = 1.6

FONTS = [
    ("Orbitron", 400, "Orbitron-Regular.ttf"),
    ("Orbitron", 500, "Orbitron-Medium.ttf"),
    ("Orbitron", 600, "Orbitron-SemiBold.ttf"),
    ("Orbitron", 700, "Orbitron-Bold.ttf"),
    ("Orbitron", 800, "Orbitron-ExtraBold.ttf"),
    ("Orbitron", 900, "Orbitron-Black.ttf"),
    ("Space Grotesk", 300, "SpaceGrotesk-Light.ttf"),
    ("Space Grotesk", 400, "SpaceGrotesk-Regular.ttf"),
    ("Space Grotesk", 500, "SpaceGrotesk-Medium.ttf"),
    ("Space Grotesk", 600, "SpaceGrotesk-SemiBold.ttf"),
    ("Space Grotesk", 700, "SpaceGrotesk-Bold.ttf"),
]


def fonts_css() -> str:
    out = []
    for family, weight, fname in FONTS:
        src = (DS / "fonts" / fname).as_uri()
        out.append(f"@font-face {{ font-family:'{family}'; font-weight:{weight}; "
                   f"src:url('{src}') format('truetype'); }}")
    return "\n".join(out)


def tokens_css() -> str:
    return "\n".join((DS / "tokens" / n).read_text()
                     for n in ("colors.css", "semantic.css", "typography.css"))


def mmss(t: float) -> str:
    t = int(round(t))
    return f"{t // 60}:{t % 60:02d}"


def probe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def load_durations(proj: Path, ticker: str, segments, estimate: bool) -> dict:
    """Short VO durations: ffprobe {T}_short_segment_{id}_voiceover.mp3, or - with
    --estimate - a chars/15.5 guess for a fast pre-VO stills check."""
    durations = {}
    for seg in segments:
        mp3 = proj / "videos" / "audio" / f"{ticker}_short_segment_{seg['id']}_voiceover.mp3"
        if mp3.exists():
            durations[str(seg["id"])] = probe_duration(mp3)
        elif estimate:
            durations[str(seg["id"])] = max(2.0, len(seg["narration"]) / 15.5)
        else:
            print(f"ERROR: missing short voiceover {mp3.name} "
                  f"(run: just webdeck-short-vo {ticker}, or pass --estimate)", file=sys.stderr)
            sys.exit(1)
    return durations


def caption_chunks(narration: str, audio_start: float, audio_dur: float):
    """Split narration into short caption phrases, timed proportionally by
    character length across the segment's audio window. Deterministic - no aligner."""
    words = narration.split()
    chunks, cur, cur_chars = [], [], 0
    for w in words:
        cur.append(w)
        cur_chars += len(w) + 1
        ends_sentence = bool(re.search(r"[.!?]$", w))
        ends_clause = bool(re.search(r"[,:;]$", w))
        # prefer breaking at sentence ends, then clauses, then a hard length cap
        if ((ends_sentence and cur_chars >= 12) or (ends_clause and cur_chars >= 26)
                or cur_chars >= 44 or len(cur) >= 9):
            chunks.append(" ".join(cur))
            cur, cur_chars = [], 0
    if cur:
        chunks.append(" ".join(cur))

    total_chars = sum(len(c) for c in chunks) or 1
    out, cursor = [], audio_start
    for c in chunks:
        share = len(c) / total_chars
        dur = audio_dur * share
        out.append({"t0": round(cursor, 3), "t1": round(cursor + dur, 3), "text": c})
        cursor += dur
    if out:  # let the last caption linger to the true audio end
        out[-1]["t1"] = round(audio_start + audio_dur, 3)
    return out


def eyebrow_for(seg, position: int):
    if seg["kind"] in ("hook", "cta", "stat"):
        return None
    label = seg["slide"].get("eyebrow")
    return [f"{position:02d}", str(label)] if label else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker")
    ap.add_argument("--estimate", action="store_true",
                    help="estimate VO durations (fast stills check before generating audio)")
    args = ap.parse_args()
    ticker = args.ticker.upper()

    proj = REPO / "projects" / ticker
    script_path = proj / "scripts" / f"{ticker}_short_script.json"
    if not script_path.exists():
        print(f"ERROR: {script_path} not found", file=sys.stderr)
        return 1
    script = json.loads(script_path.read_text())
    segments = script["segments"]
    durations = load_durations(proj, ticker, segments, args.estimate)

    out_dir = proj / "webdeck"
    out_dir.mkdir(exist_ok=True)

    sections, audio_cursor = [], LEAD_IN
    for pos, seg in enumerate(segments, start=1):
        sid = str(seg["id"])
        dur = float(durations[sid])
        start = 0.0 if not sections else round(audio_cursor - TRANS, 3)
        sections.append({
            "id": seg["id"],
            "kind": seg["kind"],
            "eyebrow": eyebrow_for(seg, pos),
            "start": start,
            "audioStart": round(audio_cursor, 3),
            "audioDur": round(dur, 3),
            "slide": seg["slide"],
            "captions": caption_chunks(seg["narration"], round(audio_cursor, 3), round(dur, 3)),
        })
        audio_cursor += dur + GAP

    total = round(audio_cursor - GAP + TAIL, 3)

    meta = script.get("metadata", {})
    quarter_tag = meta.get("quarter", "")
    if not quarter_tag:  # fall back to scraping a slide kicker
        for seg in segments:
            m = re.search(r"·\s*(Q[1-4]\s*\d{4}|FY\s*\d{4})", seg["slide"].get("kicker", ""))
            if m:
                quarter_tag = m.group(1)
                break

    data = {
        "ticker": ticker,
        "company": meta.get("company", ticker),
        "total": total,
        "header": {"ticker": f"${ticker}", "tag": quarter_tag},
        "markSrc": (DS / "assets" / "robosystems_mark_white.svg").as_uri(),
        "sections": sections,
    }

    template = (REPO / "tools" / "webdeck" / "template_short.html").read_text()
    html = (template
            .replace("{{TICKER}}", ticker)
            .replace("{{TOKENS_CSS}}", tokens_css())
            .replace("{{FONTS_CSS}}", fonts_css())
            .replace("{{DATA_JSON}}", json.dumps(data)))
    out_html = out_dir / f"{ticker}_short.html"
    out_html.write_text(html)

    mux = {
        "total": total,
        "segments": [
            {"id": s["id"], "audioStart": s["audioStart"],
             "file": str(proj / "videos" / "audio" / f"{ticker}_short_segment_{s['id']}_voiceover.mp3")}
            for s in sections
        ],
    }
    (out_dir / f"{ticker}_short_mux_manifest.json").write_text(json.dumps(mux, indent=2))

    print(f"short webdeck: {out_html}")
    print(f"total duration: {total}s ({mmss(total)}) across {len(sections)} beats"
          + ("  [ESTIMATED durations]" if args.estimate else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
