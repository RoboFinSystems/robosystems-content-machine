#!/usr/bin/env python3
"""Build a self-contained animated webdeck HTML from a project's script.json.

The webdeck is the HTML/JS replacement for the PPTX->PDF->PNG slice path:
one page per video, every animation a pure function of time (window.__seek),
rendered frame-by-frame by tools/webdeck/render_webdeck.mjs.

Timing model (mirrors assemble_video.py conventions):
  - lead-in 0.3s before the first narration
  - poster: 16:9 thumbnail held for the first 1.5s (frame 0 = poster), then hook
  - gap 0.5s of breathing room between VO segments; the 0.5s crossfade
    transition to the next section fills the gap
  - section i's visuals start TRANS before its narration starts
  - tail hold ~2.5s on the last slide, 0.9s fade to black

Usage: python3 tools/build_webdeck.py TICKER [--no-poster]
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DS = REPO / "design-system"

LEAD_IN = 0.3
GAP = 0.5
TRANS = 0.5
POSTER_HOLD = 1.5
TAIL = 2.5

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
    rules = []
    for family, weight, fname in FONTS:
        src = (DS / "fonts" / fname).as_uri()
        rules.append(
            f"@font-face {{ font-family:'{family}'; font-weight:{weight}; "
            f"src:url('{src}') format('truetype'); }}"
        )
    return "\n".join(rules)


def tokens_css() -> str:
    parts = []
    for name in ("colors.css", "semantic.css", "typography.css"):
        parts.append((DS / "tokens" / name).read_text())
    return "\n".join(parts)


def mmss(t: float) -> str:
    t = int(round(t))
    return f"{t // 60}:{t % 60:02d}"


def probe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def load_durations(proj: Path, ticker: str, segments) -> dict:
    """Segment audio durations: media_durations.json if the assemble step wrote
    it, else ffprobe the VO files directly (webdeck path has no assemble)."""
    dur_path = proj / "videos" / "media_durations.json"
    if dur_path.exists():
        return json.loads(dur_path.read_text())["audio"]
    durations = {}
    for seg in segments:
        mp3 = proj / "videos" / "audio" / f"{ticker}_segment_{seg['id']}_voiceover.mp3"
        if not mp3.exists():
            print(f"ERROR: missing voiceover {mp3} (run voiceover first)", file=sys.stderr)
            sys.exit(1)
        durations[str(seg["id"])] = probe_duration(mp3)
    dur_path.parent.mkdir(parents=True, exist_ok=True)
    dur_path.write_text(json.dumps({"audio": durations}, indent=2))
    print(f"probed {len(durations)} VO durations -> {dur_path.name}")
    return durations


def eyebrow_for(seg, position: int, sidecar: dict):
    """Per-segment eyebrow: script.json field first, sidecar file second,
    a label derived from visual_ref last. CTA slides get none."""
    if seg.get("visual_ref") == "cta":
        return None
    num = f"{position:02d}"
    label = seg.get("eyebrow")
    if label:
        return [num, str(label)]
    sidecar_entry = sidecar.get(str(seg["id"]))
    if sidecar_entry:
        return sidecar_entry
    ref = str(seg.get("visual_ref") or "").replace("_", " ").strip().title()
    return [num, ref] if ref else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker")
    ap.add_argument("--no-poster", action="store_true",
                    help="skip the thumbnail poster hold at t=0")
    args = ap.parse_args()
    ticker = args.ticker.upper()

    proj = REPO / "projects" / ticker
    script = json.loads((proj / "scripts" / f"{ticker}_script.json").read_text())
    durations = load_durations(proj, ticker, script["segments"])

    out_dir = proj / "webdeck"
    out_dir.mkdir(exist_ok=True)

    eyebrows_path = out_dir / "eyebrows.json"
    sidecar = json.loads(eyebrows_path.read_text()) if eyebrows_path.exists() else {}

    poster = proj / "charts" / "png" / f"{ticker}_thumbnail.png"
    use_poster = poster.exists() and not args.no_poster
    poster_hold = POSTER_HOLD if use_poster else 0.0

    sections = []
    audio_cursor = LEAD_IN
    for pos, seg in enumerate(script["segments"], start=1):
        sid = str(seg["id"])
        if sid not in durations:
            print(f"ERROR: no audio duration for segment {sid}", file=sys.stderr)
            return 1
        dur = float(durations[sid])
        start = 0.0 if not sections else round(audio_cursor - TRANS, 3)
        sections.append({
            "id": seg["id"],
            "visual_type": seg["visual_type"],
            "visual_ref": seg.get("visual_ref", ""),
            "eyebrow": eyebrow_for(seg, pos, sidecar),
            "start": start,
            "audioStart": round(audio_cursor, 3),
            "audioDur": round(dur, 3),
            "slide": seg["slide"],
        })
        audio_cursor += dur + GAP

    total = round(audio_cursor - GAP + TAIL, 3)

    data = {
        "ticker": ticker,
        "company": script["metadata"].get("company", ticker),
        "total": total,
        "posterHold": poster_hold,
        "lockupSrc": (DS / "assets" / "robosystems_lockup.png").as_uri(),
        "markSrc": (DS / "assets" / "robosystems_mark_white.svg").as_uri(),
        "sections": sections,
    }

    template = (REPO / "tools" / "webdeck" / "template.html").read_text()
    html = (template
            .replace("{{TICKER}}", ticker)
            .replace("{{TOKENS_CSS}}", tokens_css())
            .replace("{{FONTS_CSS}}", fonts_css())
            .replace("{{POSTER_SRC}}", poster.as_uri() if use_poster else "")
            .replace("{{DATA_JSON}}", json.dumps(data)))

    out_html = out_dir / f"{ticker}_webdeck.html"
    out_html.write_text(html)

    ts_lines = []
    for s in sections:
        t = 0.0 if s["id"] == sections[0]["id"] else s["audioStart"] - TRANS
        ts_lines.append(f"{mmss(max(0, t))} - {s['slide']['headline']}")
    ts_path = out_dir / f"{ticker}_web_timestamps.txt"
    ts_path.write_text("\n".join(ts_lines) + "\n")

    # audio placement manifest for the mux step
    mux = {
        "total": total,
        "segments": [
            {"id": s["id"], "audioStart": s["audioStart"],
             "file": str(proj / "videos" / "audio" / f"{ticker}_segment_{s['id']}_voiceover.mp3")}
            for s in sections
        ],
    }
    (out_dir / f"{ticker}_mux_manifest.json").write_text(json.dumps(mux, indent=2))

    print(f"webdeck: {out_html}")
    print(f"total duration: {total}s ({mmss(total)}) across {len(sections)} sections")
    print(f"poster: {'embedded ' + str(poster.name) if use_poster else 'none'}")
    print(f"timestamps: {ts_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
