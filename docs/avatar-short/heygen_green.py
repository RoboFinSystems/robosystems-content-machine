import urllib.request, urllib.error, json, time, sys

def load_env(p=".env"):
    e = {}
    for l in open(p):
        l = l.strip()
        if l and not l.startswith("#") and "=" in l:
            k, v = l.split("=", 1); e[k.strip()] = v.strip().strip('"').strip("'")
    return e

env = load_env()
KEY = env["HEYGEN_API_KEY"]
VOICE = env["HEYGEN_VOICE_ID"]
# HeyGen studio avatars take the "look" id (Brandon_...) as avatar_id; fall back to the uuid.
AVATARS = [env.get("HEYGEN_AVATAR_LOOK_ID"), env.get("HEYGEN_AVATAR_ID")]
OUT = sys.argv[1]

SCRIPT = ("PepsiCo just hit a 52-week low. A dividend king yielding 4.4 percent, and the market still "
          "doesn't trust it. Why? Because that dividend now eats almost all of its free cash flow. "
          "Here's what the filing actually shows.")

def req(url, method="GET", body=None, retries=6):
    data = json.dumps(body).encode() if body else None
    h = {"X-Api-Key": KEY}
    if body:
        h["Content-Type"] = "application/json"
    for attempt in range(retries):
        r = urllib.request.Request(url, data=data, headers=h, method=method)
        try:
            return json.load(urllib.request.urlopen(r, timeout=120))
        except urllib.error.HTTPError as e:
            txt = e.read().decode()[:400]
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(5); continue
            return {"_http": e.code, "_body": txt}
        except (urllib.error.URLError, TimeoutError):
            if attempt < retries - 1:
                time.sleep(5); continue
            raise

def generate(avatar_id):
    payload = {
        "video_inputs": [{
            "character": {"type": "avatar", "avatar_id": avatar_id, "avatar_style": "normal"},
            "voice": {"type": "text", "input_text": SCRIPT, "voice_id": VOICE},
            "background": {"type": "color", "value": "#00FF00"},
        }],
        "dimension": {"width": 720, "height": 1280},
        "test": True,
    }
    return req("https://api.heygen.com/v2/video/generate", "POST", payload)

vid = None
for av in AVATARS:
    if not av:
        continue
    gen = generate(av)
    print(f"avatar_id={av[:24]}... -> {json.dumps(gen)[:220]}")
    vid = (gen.get("data") or {}).get("video_id")
    if vid:
        print("using avatar_id:", av)
        break

if not vid:
    print("No video_id from either id - aborting."); sys.exit(1)

for _ in range(150):
    time.sleep(5)
    st = req(f"https://api.heygen.com/v1/video_status.get?video_id={vid}")
    d = st.get("data") or {}
    status = d.get("status")
    print("  ", status)
    if status == "completed":
        data = urllib.request.urlopen(d.get("video_url"), timeout=300).read()
        open(OUT, "wb").write(data)
        print(f"saved {OUT} ({len(data)} bytes)")
        break
    if status in ("failed", "error"):
        print("FAILED:", json.dumps(d)[:400]); break
