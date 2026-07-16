import urllib.request, urllib.error, json, base64, sys

def load_env(p=".env"):
    e = {}
    for l in open(p):
        l = l.strip()
        if l and not l.startswith("#") and "=" in l:
            k, v = l.split("=", 1); e[k.strip()] = v.strip().strip('"').strip("'")
    return e

KEY = load_env()["OPENAI_API_KEY"]
OUT = sys.argv[1]

prompt = (
    "Vertical 9:16 background plate for a finance video. Absolutely NO people, NO text, NO logos. "
    "A dark navy studio with a soft blue volumetric glow. In the UPPER third: a dramatic glowing red "
    "descending stock-market candlestick chart with a downward trend line, plus subtle abstract soda-can "
    "and chip-bag silhouettes dissolving into shadow. The LOWER two-thirds must be a clean, smooth, very "
    "dark navy gradient with almost no detail - deliberately empty so a presenter can be composited there. "
    "Cinematic, moody, premium, high-contrast lighting concentrated at the top, deep shadow at the bottom."
)

payload = {"model": "gpt-image-2", "prompt": prompt, "size": "720x1280", "quality": "high", "n": 1}
req = urllib.request.Request("https://api.openai.com/v1/images/generations", data=json.dumps(payload).encode(),
    headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}, method="POST")
try:
    r = json.load(urllib.request.urlopen(req, timeout=300))
    open(OUT, "wb").write(base64.b64decode(r["data"][0]["b64_json"]))
    print("saved", OUT)
except urllib.error.HTTPError as e:
    print("ERROR", e.code, e.read().decode()[:300])
