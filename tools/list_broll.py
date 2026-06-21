"""
Show the b-roll library and its coverage across the shoot-list categories
(see local/specs/broll-prompts.md). Helps you see which categories are thin before a shoot.

Usage:
    uv run python tools/list_broll.py
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, "assets", "broll", "manifest.json")

# Shoot-list categories -> representative tags that count toward coverage.
CATEGORIES = [
    ("Cultivation & production", {"cultivation", "grow", "production", "operations", "canopy"}),
    ("Retail & demand",          {"retail", "dispensary", "consumer", "demand"}),
    ("Markets, capital & data",  {"markets", "data", "fintech", "capital", "valuation"}),
    ("Corporate / growth",       {"corporate", "city", "growth", "aspirational", "m&a"}),
    ("Policy & regulation",      {"policy", "regulation", "legal", "government", "catalyst"}),
    ("Mood (bull / bear)",       {"relief", "bullish", "risk", "bearish", "mood", "uncertainty"}),
    ("Texture / transition",     {"macro", "texture", "transition", "insert", "closeup"}),
]


def main():
    if not os.path.exists(MANIFEST):
        print("No b-roll manifest yet. Add clips to assets/broll/ then run: just broll-sync")
        return
    with open(MANIFEST) as f:
        items = json.load(f)

    print(f"B-roll library — {len(items)} clip(s)\n")
    for it in items:
        tags = ", ".join(it.get("tags", [])) or "(untagged — fill in tags!)"
        print(f"  {it['id']:<22} {it.get('duration', '?')}s  [{tags}]")

    print("\nCoverage by shoot-list category:")
    for name, tagset in CATEGORIES:
        n = sum(1 for it in items if tagset & {t.lower() for t in it.get("tags", [])})
        print(f"  {'OK ' if n else '-- '} {name:<26} {n} clip(s)")

    untagged = [it["id"] for it in items if not it.get("tags")]
    if untagged:
        print(f"\n  WARN untagged (invisible to broll_theme): {', '.join(untagged)}")


if __name__ == "__main__":
    main()
