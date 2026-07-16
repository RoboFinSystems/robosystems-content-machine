"""Generate the canonical 9:16 avatar short, headless from the brief.

Single short (default): brief -> gpt-5 (script + hook + backdrop prompt) -> HeyGen avatar on green
(our ElevenLabs voice) -> whisper-1 (word timings) -> gpt-image-2 backdrop (safe-zone) -> PIL brand
overlay + word-synced captions -> ffmpeg key + composite -> videos/{T}_short.mp4.

Q&A short (--qa): a purpose-authored 2-4 turn exchange from scripts/{T}_qa.json's `short` block,
rendered as two avatars (host vs analyst pool + voice) cut-between over one shared backdrop, then
concatenated into the same videos/{T}_short.mp4. The turns are authored by Cowork, not gpt-5.

Usage:
    uv run python tools/gen_avatar_short.py PEP [--test] [--quality high|medium|low] [--qa]
    --test  = free watermarked HeyGen render (POC); omit for a clean paid render.

Needs OPENAI_API_KEY, HEYGEN_API_KEY, HEYGEN_VOICE_ID (+ HEYGEN_AVATAR_LOOK_ID) in .env;
--qa also needs HEYGEN_VOICE_ID2 + HEYGEN_AVATAR_LOOK_ID2 (the host pool).
"""
import argparse, base64, json, os, random, subprocess, sys, time, urllib.error, urllib.request
from PIL import Image, ImageDraw, ImageFont
from helpers import get_project_dir

W, H, FPS = 720, 1280, 30
FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
CHAT_PREF = ["gpt-5", "gpt-5-mini", "gpt-4.1", "gpt-4o"]
NAVY, BLUE, WHITE, GOLD, GREY, STROKE = (10, 14, 26), (91, 140, 249), (255, 255, 255), (255, 210, 59), (194, 205, 223), (0, 0, 0, 235)

# Q&A short: each turn is one speaker, cut-between over a shared backdrop. The host and the analyst
# draw from separate HeyGen look pools + voices; a coloured HOST/ANALYST pill distinguishes them.
SPEAKER = {
    "analyst":     {"label": "ANALYST", "fill": BLUE, "text_col": WHITE, "look_var": "HEYGEN_AVATAR_LOOK_ID",  "voice_var": "HEYGEN_VOICE_ID"},
    "interviewer": {"label": "HOST",    "fill": GOLD, "text_col": NAVY,  "look_var": "HEYGEN_AVATAR_LOOK_ID2", "voice_var": "HEYGEN_VOICE_ID2"},
}
_LOOK_FALLBACK = {"HEYGEN_AVATAR_LOOK_ID": "HEYGEN_AVATAR_ID", "HEYGEN_AVATAR_LOOK_ID2": "HEYGEN_AVATAR_ID2"}

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
def avatar_looks(var="HEYGEN_AVATAR_LOOK_ID"):
    """A comma-separated pool of HeyGen look ids for one speaker. `HEYGEN_AVATAR_LOOK_ID` is the
    single-short presenter / Q&A analyst pool; `HEYGEN_AVATAR_LOOK_ID2` is the Q&A host pool. One is
    picked at random per render for variety. Falls back to the matching avatar-group uuid."""
    raw = env(var) or env(_LOOK_FALLBACK.get(var, "")) or ""
    return [x.strip() for x in raw.split(",") if x.strip()]


def heygen(narration, test, avatar=None, voice=None):
    hdr = {"X-Api-Key": env("HEYGEN_API_KEY")}
    avatar = avatar or random.choice(avatar_looks() or [env("HEYGEN_AVATAR_ID")])
    voice = voice or env("HEYGEN_VOICE_ID")
    payload = {"video_inputs": [{
        "character": {"type": "avatar", "avatar_id": avatar, "avatar_style": "normal"},
        "voice": {"type": "text", "input_text": narration, "voice_id": voice},
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


def render_overlay(el, out, speaker_label=None, label_fill=BLUE, label_text=WHITE):
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
    # speaker pill (Q&A short only) — a HOST/ANALYST chip just above the captions
    if speaker_label:
        f_lab = ImageFont.truetype(FONT, 32)
        pad_x, pill_h, y0 = 26, 56, 926
        pw = d.textlength(speaker_label, font=f_lab) + pad_x * 2
        x0 = (W - pw) / 2
        d.rounded_rectangle([x0, y0, x0 + pw, y0 + pill_h], radius=pill_h / 2,
                            fill=(label_fill[0], label_fill[1], label_fill[2], 235), outline=WHITE, width=3)
        d.text((W / 2, y0 + pill_h / 2), speaker_label, font=f_lab, fill=label_text, anchor="mm")
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


def concat_turns(parts, out):
    """Concat the per-turn mp4s (identical params) into one short via the concat filter."""
    ins = []
    for p in parts:
        ins += ["-i", p]
    n = len(parts)
    streams = "".join(f"[{i}:v][{i}:a]" for i in range(n))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *ins,
                    "-filter_complex", f"{streams}concat=n={n}:v=1:a=1[v][a]",
                    "-map", "[v]", "-map", "[a]", "-r", str(FPS),
                    "-pix_fmt", "yuv420p", "-c:v", "libx264", "-c:a", "aac", out], check=True)


def load_qa_short(pdir, ticker):
    """The purpose-authored short exchange (2-4 turns) from scripts/{T}_qa.json's `short` block.
    Authored by Cowork (COWORK_INSTRUCTIONS #6) — NOT derived from the podcast at render time."""
    qpath = os.path.join(pdir, "scripts", f"{ticker}_qa.json")
    if not os.path.exists(qpath):
        sys.exit(f"No Q&A script at {qpath}")
    qa = json.load(open(qpath, encoding="utf-8"))
    short = qa.get("short") if isinstance(qa.get("short"), dict) else None
    turns = (short or {}).get("turns")
    if not turns:
        sys.exit(
            f"No `short` block in {os.path.basename(qpath)}. The Q&A short reads a purpose-authored\n"
            f"  short.turns exchange (2-4 turns, ~45s) that Cowork writes (see COWORK_INSTRUCTIONS #6).\n"
            f"  Re-run Cowork for this name, or hand-add a short.turns block for an older project.")
    return turns


def gen_qa_short(pdir, ticker, el, args, work):
    """Two-avatar Q&A short: render each authored turn on green (host vs analyst pool + voice),
    cut-between over one shared backdrop, then concat. Reuses the single-short compositor per turn."""
    if not env("HEYGEN_VOICE_ID2"):
        sys.exit("HEYGEN_VOICE_ID2 not in .env — needed for the Q&A host voice.")
    turns = load_qa_short(pdir, ticker)
    print(f"  Q&A short: {len(turns)} turns, cut-between over a shared backdrop")

    print("  generating shared backdrop (gpt-image-2) ...", flush=True)
    backdrop = os.path.join(work, "backdrop.png")
    gen_backdrop(el["backdrop_prompt"], args.quality, backdrop)

    parts, total = [], 0.0
    for i, t in enumerate(turns):
        sp = SPEAKER.get(t.get("speaker"), SPEAKER["analyst"])
        looks = avatar_looks(sp["look_var"]) or avatar_looks() or [env("HEYGEN_AVATAR_ID")]
        avatar = random.choice(looks)
        voice = env(sp["voice_var"]) or env("HEYGEN_VOICE_ID")
        text = t["text"].strip()
        print(f"  turn {i + 1}/{len(turns)} [{sp['label']}] look {avatar} (of {len(looks)}) — {text[:55]}...", flush=True)
        green = os.path.join(work, f"turn{i}_green.mp4")
        open(green, "wb").write(heygen(text, args.test, avatar=avatar, voice=voice))
        mp3 = os.path.join(work, f"turn{i}.mp3")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", green, "-vn", "-acodec", "libmp3lame", "-q:a", "4", mp3], check=True)
        words, dur = transcribe(mp3)
        total += dur
        overlay = os.path.join(work, f"turn{i}_overlay.png")
        render_overlay(el, overlay, speaker_label=sp["label"], label_fill=sp["fill"], label_text=sp["text_col"])
        caps = os.path.join(work, f"turn{i}_caps")
        render_captions(words, dur, caps)
        part = os.path.join(work, f"turn{i}.mp4")
        composite(backdrop, green, overlay, caps, part)
        parts.append(part)

    out = os.path.join(pdir, "videos", f"{ticker}_short.mp4")
    print("  concatenating turns ...", flush=True)
    concat_turns(parts, out)
    print(f"\nDone -> {out}  ({total:.1f}s, {len(turns)} turns)")


def main():
    ap = argparse.ArgumentParser(description="Generate the canonical 9:16 avatar short from the brief")
    ap.add_argument("project")
    ap.add_argument("--test", action="store_true", help="free watermarked HeyGen render (POC)")
    ap.add_argument("--quality", default="high", choices=["high", "medium", "low"])
    ap.add_argument("--qa", action="store_true",
                    help="two-avatar Q&A short from scripts/{T}_qa.json's `short` block (host + analyst, cut-between)")
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

    # write_brief supplies the on-screen CHROME (ticker/exchange/hook/eyebrow) + backdrop prompt for
    # both paths. The single short also uses its narration; the Q&A short ignores it (turns come from
    # the authored qa.json `short` block, not gpt-5).
    model, el = write_brief(open(brief_path, encoding="utf-8").read())
    print(f"  script model: {model}  ({'TEST render' if args.test else 'PAID render'})")
    print(f"  hook: {el['hook_headline']!r}")

    if args.qa:
        gen_qa_short(pdir, ticker, el, args, work)
        return

    print(f"  narration ({len(el['narration'])} chars): {el['narration'][:90]}...")
    looks = avatar_looks() or [env("HEYGEN_AVATAR_ID")]
    avatar = random.choice(looks)
    print(f"  rendering HeyGen avatar (green) — look {avatar} (random of {len(looks)}) ...", flush=True)
    avatar_mp4 = os.path.join(work, "avatar_green.mp4")
    open(avatar_mp4, "wb").write(heygen(el["narration"], args.test, avatar=avatar))

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
