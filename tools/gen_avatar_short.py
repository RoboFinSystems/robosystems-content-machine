"""Generate the canonical 9:16 avatar short, headless from the brief.

Chain: brief -> gpt-5 (short script + hook + backdrop prompt) -> HeyGen avatar on green (our
ElevenLabs voice) -> whisper-1 (word timings) -> gpt-image-2 backdrop (safe-zone) -> PIL brand
overlay + animated word-synced captions -> ffmpeg key + composite -> videos/{T}_short.mp4.

Usage:
    uv run python tools/gen_avatar_short.py PEP [--test] [--quality high|medium|low]
    --test  = free watermarked HeyGen render (POC); omit for a clean paid render.

Needs HEYGEN_API_KEY, HEYGEN_AVATAR_LOOK_ID, HEYGEN_VOICE_ID, OPENAI_API_KEY in .env.
See docs/avatar-short/README.md for the recipe this automates.
"""
import argparse, base64, json, os, subprocess, sys, time, urllib.error, urllib.request
from PIL import Image, ImageDraw, ImageFont
from helpers import get_project_dir

W, H, FPS = 720, 1280, 30
FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
CHAT_PREF = ["gpt-5", "gpt-5-mini", "gpt-4.1", "gpt-4o"]
NAVY, BLUE, WHITE, GOLD, GREY, STROKE = (10, 14, 26), (91, 140, 249), (255, 255, 255), (255, 210, 59), (194, 205, 223), (0, 0, 0, 235)

STYLE = (
    "You are the writer/art-director for RoboSystems, a SEC-filing-grounded equity-research channel. "
    "Given a research brief, produce a punchy 9:16 talking-head SHORT. Return STRICT JSON: "
    "narration (a fresh, self-contained spoken script for the avatar - STRICTLY 60-85 words, do NOT "
    "exceed 85 words: name the company + ticker, land the single most striking tension, end on a "
    "hook/question; spoken-form, no symbols - write '4.4 percent' not '4.4%'), "
    "hook_headline (a short on-screen headline, <= 6 words), "
    "eyebrow (e.g. 'INITIATING COVERAGE'), "
    "company_upper, ticker, exchange, "
    "backdrop_prompt (a gpt-image-2 prompt for a 9:16 background plate: NO people/text/logos, rich "
    "on-topic imagery + a red down-chart in the UPPER third, and a clean DARK EMPTY lower two-thirds "
    "where a presenter is composited). JSON only."
)


def load_env(path=".env"):
    e = {}
    if os.path.exists(path):
        for ln in open(path):
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, v = ln.split("=", 1); e[k.strip()] = v.strip().strip('"').strip("'")
    return e


ENV = load_env()
def env(k): return ENV.get(k) or os.environ.get(k)


def _http(url, headers, body=None, retries=6, timeout=180):
    data = json.dumps(body).encode() if body is not None else None
    h = dict(headers)
    if body is not None:
        h["Content-Type"] = "application/json"
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers=h, method="POST" if body is not None else "GET")
            return json.load(urllib.request.urlopen(req, timeout=timeout))
        except urllib.error.HTTPError as e:
            txt = e.read().decode()[:400]
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(5); continue
            sys.exit(f"HTTP {e.code} on {url}:\n{txt}")
        except (urllib.error.URLError, TimeoutError):
            if attempt < retries - 1:
                time.sleep(5); continue
            raise


# ---------- OpenAI ----------
def oai(path, body=None):
    return _http("https://api.openai.com/v1" + path, {"Authorization": f"Bearer {env('OPENAI_API_KEY')}"}, body)


def pick_chat_model():
    ids = {m["id"] for m in oai("/models")["data"]}
    return next((m for m in CHAT_PREF if m in ids), "gpt-4o")


def write_brief(brief):
    model = pick_chat_model()
    r = oai("/chat/completions", {
        "model": model,
        "messages": [{"role": "system", "content": STYLE}, {"role": "user", "content": "BRIEF:\n" + brief[:6000]}],
        "response_format": {"type": "json_object"},
    })
    return model, json.loads(r["choices"][0]["message"]["content"])


def gen_backdrop(prompt, quality, out):
    r = oai("/images/generations", {"model": "gpt-image-2", "prompt": prompt, "size": "720x1280", "quality": quality, "n": 1})
    open(out, "wb").write(base64.b64decode(r["data"][0]["b64_json"]))


def transcribe(mp3):
    r = subprocess.run(["curl", "-s", "https://api.openai.com/v1/audio/transcriptions",
                        "-H", f"Authorization: Bearer {env('OPENAI_API_KEY')}",
                        "-F", f"file=@{mp3}", "-F", "model=whisper-1", "-F", "response_format=verbose_json",
                        "-F", "timestamp_granularities[]=word"], capture_output=True, text=True)
    d = json.loads(r.stdout)
    return d["words"], float(d["duration"])


# ---------- HeyGen ----------
def heygen(narration, test):
    key = env("HEYGEN_API_KEY")
    hdr = {"X-Api-Key": key}
    avatar = env("HEYGEN_AVATAR_LOOK_ID") or env("HEYGEN_AVATAR_ID")
    payload = {"video_inputs": [{
        "character": {"type": "avatar", "avatar_id": avatar, "avatar_style": "normal"},
        "voice": {"type": "text", "input_text": narration, "voice_id": env("HEYGEN_VOICE_ID")},
        "background": {"type": "color", "value": "#00FF00"}}],
        "dimension": {"width": W, "height": H}, "test": test}
    gen = _http("https://api.heygen.com/v2/video/generate", hdr, payload)
    vid = (gen.get("data") or {}).get("video_id")
    if not vid:
        sys.exit(f"HeyGen: no video_id: {json.dumps(gen)[:300]}")
    for _ in range(180):
        time.sleep(5)
        d = (_http(f"https://api.heygen.com/v1/video_status.get?video_id={vid}", hdr).get("data") or {})
        st = d.get("status")
        if st == "completed":
            return urllib.request.urlopen(d["video_url"], timeout=300).read()
        if st in ("failed", "error"):
            sys.exit(f"HeyGen failed: {json.dumps(d)[:300]}")
    sys.exit("HeyGen timed out")


# ---------- PIL rendering ----------
def _wrap(draw, text, font, maxw):
    lines, cur = [], ""
    for word in text.split():
        t = (cur + " " + word).strip()
        if draw.textlength(t, font=font) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur); cur = word
    if cur:
        lines.append(cur)
    return lines


def render_overlay(el, out):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f_wm, f_tick, f_eye, f_hook, f_foot = (ImageFont.truetype(FONT, s) for s in (34, 27, 26, 60, 26))
    # wordmark
    d.text((36, 50), "Robo", font=f_wm, fill=WHITE, stroke_width=3, stroke_fill=STROKE)
    rw = d.textlength("Robo", font=f_wm)
    d.text((36 + rw, 50), "Systems", font=f_wm, fill=BLUE, stroke_width=3, stroke_fill=STROKE)
    # ticker (right)
    _t = el["ticker"]
    tick = f"{_t if _t.startswith('$') else '$' + _t}  ·  {el['exchange']}"
    d.text((W - 36 - d.textlength(tick, font=f_tick), 56), tick, font=f_tick, fill=GREY, stroke_width=2, stroke_fill=STROKE)
    # eyebrow + hook
    d.text((36, 118), " ".join(el["eyebrow"].upper()), font=f_eye, fill=BLUE, stroke_width=2, stroke_fill=STROKE)
    y = 158
    for line in _wrap(d, el["hook_headline"], f_hook, W - 72):
        d.text((36, y), line, font=f_hook, fill=WHITE, stroke_width=4, stroke_fill=STROKE); y += 68
    # foot
    foot = "robosystems.ai  ·  SEC filing data"
    d.text(((W - d.textlength(foot, font=f_foot)) / 2, H - 80), foot, font=f_foot, fill=GREY, stroke_width=2, stroke_fill=STROKE)
    img.save(out)


def render_captions(words, dur, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    font = ImageFont.truetype(FONT, 58)
    per_line, cy = 3, 1015

    def active(t):
        idx = -1
        for i, w in enumerate(words):
            if w["start"] <= t + 1e-6:
                idx = i
            else:
                break
        return idx

    cache = {}
    def state(i):
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        if i < 0:
            return img
        line = i // per_line
        parts = [w["word"].strip() for w in words[line * per_line: line * per_line + per_line]]
        act = i - line * per_line
        d = ImageDraw.Draw(img)
        space = d.textlength(" ", font=font)
        widths = [d.textlength(p, font=font) for p in parts]
        x = (W - (sum(widths) + space * (len(parts) - 1))) / 2
        for j, p in enumerate(parts):
            d.text((x, cy), p, font=font, fill=(GOLD if j == act else WHITE), stroke_width=6, stroke_fill=STROKE, anchor="lm")
            x += widths[j] + space
        return img

    n = int(dur * FPS) + 1
    for fr in range(n):
        i = active(fr / FPS)
        cache.setdefault(i, state(i)).save(f"{out_dir}/cap_{fr:05d}.png")


def composite(backdrop, avatar_mp4, overlay, caps_dir, out):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error",
                    "-loop", "1", "-i", backdrop, "-i", avatar_mp4, "-loop", "1", "-i", overlay,
                    "-framerate", str(FPS), "-i", f"{caps_dir}/cap_%05d.png",
                    "-filter_complex",
                    "[0:v]scale=720:1280,setsar=1[bg];"
                    "[1:v]chromakey=0x00FF00:0.13:0.06,despill=type=green[ky];"
                    "[bg][ky]overlay=0:0[a];[a][2:v]overlay=0:0[b];[b][3:v]overlay=0:0:shortest=1[out]",
                    "-map", "[out]", "-map", "1:a", "-shortest", "-r", str(FPS),
                    "-pix_fmt", "yuv420p", "-c:v", "libx264", "-c:a", "aac", out], check=True)


def main():
    ap = argparse.ArgumentParser(description="Generate the canonical 9:16 avatar short from the brief")
    ap.add_argument("project")
    ap.add_argument("--test", action="store_true", help="free watermarked HeyGen render (POC)")
    ap.add_argument("--quality", default="high", choices=["high", "medium", "low"])
    args = ap.parse_args()
    for k in ("OPENAI_API_KEY", "HEYGEN_API_KEY", "HEYGEN_VOICE_ID"):
        if not env(k):
            sys.exit(f"{k} not in .env")

    pdir = get_project_dir(args.project)
    sfiles = [f for f in os.listdir(os.path.join(pdir, "scripts")) if f.endswith("_script.json")]
    ticker = json.load(open(os.path.join(pdir, "scripts", sfiles[0])))["metadata"]["ticker"] if sfiles else args.project
    brief_path = os.path.join(pdir, "reports", f"{ticker}_brief.md")
    if not os.path.exists(brief_path):
        sys.exit(f"No brief at {brief_path}")

    work = os.path.join(pdir, "videos", "short_build")
    os.makedirs(work, exist_ok=True)

    model, el = write_brief(open(brief_path, encoding="utf-8").read())
    print(f"  script model: {model}  ({'TEST render' if args.test else 'PAID render'})")
    print(f"  hook: {el['hook_headline']!r}")
    print(f"  narration ({len(el['narration'])} chars): {el['narration'][:90]}...")

    print("  rendering HeyGen avatar (green) ...", flush=True)
    avatar_mp4 = os.path.join(work, "avatar_green.mp4")
    open(avatar_mp4, "wb").write(heygen(el["narration"], args.test))

    print("  transcribing for captions ...", flush=True)
    mp3 = os.path.join(work, "vo.mp3")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", avatar_mp4, "-vn", "-acodec", "libmp3lame", "-q:a", "4", mp3], check=True)
    words, dur = transcribe(mp3)

    print("  generating backdrop (gpt-image-2) ...", flush=True)
    backdrop = os.path.join(work, "backdrop.png")
    gen_backdrop(el["backdrop_prompt"], args.quality, backdrop)

    print("  rendering overlay + captions ...", flush=True)
    overlay = os.path.join(work, "overlay.png")
    render_overlay(el, overlay)
    caps = os.path.join(work, "caps")
    render_captions(words, dur, caps)

    out = os.path.join(pdir, "videos", f"{ticker}_short.mp4")
    print("  compositing ...", flush=True)
    composite(backdrop, avatar_mp4, overlay, caps, out)
    print(f"\nDone -> {out}  ({dur:.1f}s)")


if __name__ == "__main__":
    main()
