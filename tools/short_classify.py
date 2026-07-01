"""
short_classify.py — card-text → archetype inference for the 9:16 Short.

Pure Python (regex only, no Pillow): the Stage-1 inference that maps a caption
card's text to a frame archetype + payload, with no schema change. Extracted
from the retired Pillow renderer so the Playwright-based `renderer/` short path
(navy+teal DS-font scenes) can consume the same classification. Everything
falls back to a full-bleed `headline`, so an unmatched card is still on-brand.

Archetypes: identity, question, cta, alert, stat, hero, hook, headline.
"""

import re

_EXCH = r"(NYSE AMERICAN|NYSE|NASDAQ|OTCQX|OTCQB|OTCMKTS|OTC|CSE|TSXV|TSX)"

# separators that mean "two facts in tension": ·•  arrows  em/en/hyphen dash  ". "  ", "
_SPLIT = re.compile(r"\s*[·•]\s*|\s*(?:→|⟶|➜|->)\s*|\s+[—–-]\s+|\.\s+|,\s+")


def _two_facts(s):
    parts = [p.strip(" .,") for p in _SPLIT.split(s) if p and p.strip(" .,")]
    if len(parts) == 2 and any(re.search(r"\d", p) for p in parts):
        return {"a": parts[0], "b": parts[1]}
    return None


def _hero_split(s):
    s = s.replace("−", "-")
    toks = list(re.finditer(r"-?\$?\d[\d,]*(?:\.\d+)?\s*(?:%|x|bps|B|M|K)?", s))
    if len(toks) != 1:
        return None
    m = toks[0]
    num = re.sub(r"\s+", "", m.group(0))
    label = (s[:m.start()] + " " + s[m.end():]).strip(" —–-·,.:")
    label = re.sub(r"\s*[—–-]\s*", " ", label).strip(" :")
    label = " ".join(label.split())
    if not label or len(label) > 22:
        return None
    return {"number": num, "label": label}


def classify_card(text, idx, n):
    """Map a caption card to a frame archetype + payload. Everything falls back to a
    full-bleed branded `headline`, so an unmatched card is still on-brand, never broken."""
    s = " ".join(text.split())
    up = s.upper()
    last = idx == n - 1
    cta_extra = {"secondary": "Full breakdown → pinned comment", "handle": "@RoboFinSystems"}

    m = re.search(_EXCH + r"\s*[:\-]?\s*([A-Z][A-Z.]{1,6})", up)
    if m:
        company = re.split(r"[—–-]", s)[0].strip() or s
        return ("identity", {"company": company, "exchange": m.group(1), "ticker": m.group(2)})
    if s.endswith("?"):
        return ("cta" if last else "question", {"line": s, "text": s, **cta_extra})
    if last:
        return ("cta", {"line": s, "text": s, **cta_extra})
    if s.startswith(("…", "...")) or re.search(r"\b(LOSS|BLAME|TRAP|BANKRUPT|DISTRESS|STILL)\b", up):
        return ("alert", {"text": s})
    facts = _two_facts(s)
    if facts:
        return ("stat", facts)
    hero = _hero_split(s)
    if hero:
        return ("hero", hero)
    if idx == 0:
        return ("hook", {"text": s})
    return ("headline", {"text": s})
