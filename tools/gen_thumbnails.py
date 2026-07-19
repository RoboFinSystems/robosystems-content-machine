"""Generate the 3 platform thumbnails via OpenAI, from the project's brief.

Replaces the manual "paste brief into ChatGPT" step. Two stages:
  1. A chat model reads the brief + a RoboSystems style guide and extracts the creative
     elements (company, ticker, the hook stat, a supporting figure, the visual concept).
  2. gpt-image-2 renders one image per platform aspect; we crop-to-fill the exact target and
     write assets/{yt,x,spot}.png — where the `slice` step already ingests them.

Usage:
    uv run python tools/gen_thumbnails.py PEP [--quality high|medium|low] [--dry-run]

Needs OPENAI_API_KEY in .env. Cost ~ $0.60/ticker at high quality (3 images) + a small chat call.
"""

import argparse
import base64
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

from helpers import get_project_dir

API = "https://api.openai.com/v1"
IMAGE_MODEL = "gpt-image-2"
CHAT_PREF = ["gpt-5", "gpt-5-mini", "gpt-4.1", "gpt-4.1-mini", "gpt-4o", "gpt-4o-mini"]

# gpt-image-2 accepts any size whose dims are divisible by 16, so we render at the EXACT target
# aspect (no crop that would clip the composition) then clean-scale to the final resolution.
#   (asset, gpt-image render size @ target aspect, final W, H, label)
PLATFORMS = [
    ("yt.png",   "1536x864",  1920, 1080, "16:9 · YouTube + website"),
    ("x.png",    "1440x576",  2000,  800, "5:2 · X"),
    ("spot.png", "1024x1024", 1440, 1440, "1:1 · Spotify (>=1400)"),
]

STYLE = (
    "You are the art director for RoboSystems, a financial-analysis video channel. Its thumbnails "
    "are dark-navy, high-contrast, high-CTR: a bold condensed headline on the left, photorealistic "
    "imagery relevant to the company on the right, a red stock-chart motif, and one small stat badge. "
    "Given an equity-research brief, extract the creative elements. Return STRICT JSON with keys: "
    "company_display, company_upper, ticker, exchange, "
    "hook_stat (the single most striking metric, 1-4 words, in punchy ALL-CAPS short form with "
    "symbols - e.g. '4.4% YIELD', '$6B FUEL HIT', '+57% EPS', 'BELOW BOOK' - never spelled out as "
    "lowercase words like 'nearly six billion dollars'), "
    "hook_line (a punchy 2-5 word tension phrase, e.g. 'MARKET DOESN'T TRUST IT'), "
    "key_stat (one supporting figure with a SHORT label for a small badge, punchy short-form with "
    "symbols - e.g. 'TRASM +12.1%', 'FCF ~$2.3B', 'ROIC 31.4%' - never a full spelled-out sentence), "
    "visual_concept (a vivid, brand-accurate description of photorealistic imagery for THIS company "
    "- specific products, buildings, a trading floor, etc.), "
    "chart_hint (a short stock-chart motif, e.g. 'a red candlestick chart trending sharply down'). "
    "Be faithful to the brief: copy every number exactly, use ONLY the current (post-split, if the "
    "brief mentions a split) share price and its stated range, and never mislabel the result (do not "
    "say 'miss' if the company beat). Prefer a non-price stat (margin, growth, yield, ROIC) for "
    "hook_stat and key_stat when the share price is volatile or recently split. "
    "All text must be correctly spelled for rendering. No markdown, JSON only."
)


def load_env(path=".env"):
    env = {}
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def _post(url, key, payload, timeout=300):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, method="POST")
    try:
        return json.load(urllib.request.urlopen(req, timeout=timeout))
    except urllib.error.HTTPError as e:
        sys.exit(f"OpenAI HTTP {e.code}: {e.read().decode()[:400]}")


def pick_chat_model(key):
    req = urllib.request.Request(f"{API}/models", headers={"Authorization": f"Bearer {key}"})
    ids = {m["id"] for m in json.load(urllib.request.urlopen(req, timeout=30))["data"]}
    for m in CHAT_PREF:
        if m in ids:
            return m
    sys.exit(f"No preferred chat model available. Have: {sorted(i for i in ids if i.startswith('gpt'))[:10]}")


def extract_elements(key, model, brief):
    r = _post(f"{API}/chat/completions", key, {
        "model": model,
        "messages": [{"role": "system", "content": STYLE},
                     {"role": "user", "content": "BRIEF:\n" + brief[:6000]}],
        "response_format": {"type": "json_object"},
    }, timeout=120)
    return json.loads(r["choices"][0]["message"]["content"])


def build_prompt(el, aspect_note):
    return (
        f"A high-CTR thumbnail graphic for a stock-analysis video on {el['company_display']}. "
        f"Dark navy studio background with a soft blue glow. On the right: {el['visual_concept']}. "
        f"{el['chart_hint']}, upper right, drawn as a PURELY DECORATIVE motif - no axis, no gridlines, "
        f"no price numbers, no tick labels, no dates, no text of any kind on the chart. "
        f"On the left, bold condensed headline text stacked: "
        f"'{el['company_upper']}' in white, '{el['hook_stat']}' in bright blue (#3b7af5), "
        f"'{el['hook_line']}' in white with the key word in red. A small rounded blue badge lower-left "
        f"reading '{el['key_stat']}'. Ticker '{el['ticker']} - {el['exchange']}'. "
        f"CRITICAL: render ONLY the exact text specified above, character for character. Do NOT add, "
        f"invent, complete, or overlay ANY price, share price, stock value, axis number, percentage, "
        f"date, or statistic that is not written verbatim in this prompt - in particular never guess a "
        f"stock's price from memory. "
        f"Cinematic high-contrast lighting, crisp, professional finance-channel style, no watermark. "
        f"Spell all text correctly. {aspect_note}"
    )


ASPECT_NOTE = {
    "yt.png":   "Format: a 16:9 landscape frame. Fill the whole frame edge to edge; keep every "
                "letter of the headline and all imagery inside a safe margin so NOTHING is cut off "
                "at the top, bottom, or sides.",
    "x.png":    "Format: a very wide 5:2 banner (two-and-a-half times wider than tall). Lay it out "
                "HORIZONTALLY - headline text on the left, product imagery on the right, everything "
                "vertically centered. Fill the whole frame edge to edge; keep all content inside a "
                "safe margin so NOTHING is cut off.",
    "spot.png": "Format: a 1:1 square frame. Fill the whole frame edge to edge; keep all text and "
                "imagery inside a safe margin so NOTHING is cut off.",
}


def gen_image(key, prompt, size, quality):
    r = _post(f"{API}/images/generations", key,
              {"model": IMAGE_MODEL, "prompt": prompt, "size": size, "quality": quality, "n": 1})
    return base64.b64decode(r["data"][0]["b64_json"])


def crop_to(src, out, w, h):
    """Crop-to-fill the source PNG to exactly w x h (scale to cover, center-crop). Needs ffmpeg."""
    vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-vf", vf, out], check=True)


def main():
    ap = argparse.ArgumentParser(description="Generate the 3 platform thumbnails via OpenAI from the brief")
    ap.add_argument("project")
    ap.add_argument("--quality", default="high", choices=["high", "medium", "low"])
    ap.add_argument("--dry-run", action="store_true", help="print the extracted elements + prompts, generate nothing")
    args = ap.parse_args()

    key = load_env().get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not key:
        sys.exit("OPENAI_API_KEY not found in .env")

    project_dir = get_project_dir(args.project)
    scripts_dir = os.path.join(project_dir, "scripts")
    sf = [f for f in os.listdir(scripts_dir) if f.endswith("_script.json")]
    ticker = json.load(open(os.path.join(scripts_dir, sf[0])))["metadata"]["ticker"] if sf else args.project
    brief_path = os.path.join(project_dir, "reports", f"{ticker}_brief.md")
    if not os.path.exists(brief_path):
        sys.exit(f"No brief at {brief_path}")
    brief = open(brief_path, encoding="utf-8").read()

    model = pick_chat_model(key)
    print(f"  chat model: {model}  ·  image model: {IMAGE_MODEL}  ·  quality: {args.quality}")
    el = extract_elements(key, model, brief)
    print(f"  hook: {el.get('hook_stat')!r} / {el.get('hook_line')!r}  ·  badge: {el.get('key_stat')!r}")

    assets = os.path.join(project_dir, "assets")
    os.makedirs(assets, exist_ok=True)
    tmp = os.path.join(assets, "_thumb_raw.png")

    for name, size, w, h, label in PLATFORMS:
        prompt = build_prompt(el, ASPECT_NOTE[name])
        if args.dry_run:
            print(f"\n[{name} · {label}]\n{prompt}")
            continue
        print(f"  generating {name} ({label}) ...", flush=True)
        open(tmp, "wb").write(gen_image(key, prompt, size, args.quality))
        crop_to(tmp, os.path.join(assets, name), w, h)
        print(f"    -> assets/{name} ({w}x{h})")
    if os.path.exists(tmp):
        os.remove(tmp)
    if not args.dry_run:
        print(f"\nDone. Run `just slice {ticker}` to ingest, then publish.")


if __name__ == "__main__":
    main()
