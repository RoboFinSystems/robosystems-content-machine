"""
Roll a coverage KEY up into its aggregate project's sources.

A key is a ticker-form identity for a node in the coverage graph. Company keys are SEC
tickers; aggregate keys (sectors + industries) are defined in classifications/keys.csv.
Every key indexes projects/{KEY}/, so "sector" vs "industry" is not a structural
distinction - just a key mapping to a taxonomy node at some depth. The rollup is uniform:

  - an INDUSTRY key (maps to a leaf node; has a `campaign` with a universe.json) rolls up
    its member COMPANIES' briefs, matched to projects by CIK (slug fallback);
  - a SECTOR key (has child keys in the registry) rolls up its child INDUSTRIES' briefs.

Children are gathered into projects/{KEY}/sources/_briefs/ and sources/_watchlist.md is
regenerated. Dry-run by default (prints the plan + diffs the existing _briefs/); --write
applies. Only _briefs/ + _watchlist.md are written - hand-authored sources are untouched.

Usage:
    uv run python tools/rollup_sources.py CANNABIS            # industry -> companies
    uv run python tools/rollup_sources.py CONSUMER            # sector   -> industries
    uv run python tools/rollup_sources.py CANNABIS --write
    uv run python tools/rollup_sources.py CANNABIS --statuses DONE,READY,STALE
"""

import argparse
import csv
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECTS = ROOT / "projects"
CAMPAIGNS = ROOT / "campaigns"
KEYS_CSV = ROOT / "classifications" / "keys.csv"

DEFAULT_ROLLUP_WHEN = ["DONE", "READY"]


def load_keys():
    """Registry of aggregate keys: key -> row (parent, sector, subsector, category, campaign, title)."""
    with KEYS_CSV.open(encoding="utf-8") as f:
        return {r["key"]: r for r in csv.DictReader(f)}


def node_str(row):
    return " > ".join(p for p in (row["sector"], row["subsector"], row["category"]) if p)


def extract_cik(text):
    m = re.search(r"CIK[:#\s]*0*(\d{1,10})", text)
    return m.group(1).zfill(10) if m else None


def index_projects(agg_slug):
    """(by_cik, by_slug) over projects with a brief. by_cik handles ticker churn; by_slug is the fallback."""
    by_cik, by_slug = {}, {}
    for pdir in sorted(PROJECTS.iterdir()):
        if not pdir.is_dir() or pdir.name == agg_slug:
            continue
        brief = pdir / "reports" / f"{pdir.name}_brief.md"
        if not brief.exists():
            continue
        rec = (pdir.name, brief)
        by_slug[pdir.name] = rec
        cik = extract_cik(brief.read_text(encoding="utf-8"))
        if cik:
            by_cik[cik] = rec
    return by_cik, by_slug


def parse_rollup_when(campaign):
    cfg = CAMPAIGNS / campaign / "campaign.yml"
    if cfg.exists():
        m = re.search(r"^\s*rollup_when:\s*\[([^\]]*)\]", cfg.read_text(encoding="utf-8"), re.M)
        if m:
            vals = [v.strip().strip("'\"") for v in m.group(1).split(",") if v.strip()]
            if vals:
                return vals
    return DEFAULT_ROLLUP_WHEN


def plan_industry(key, registry, statuses):
    """Roll up member companies of an industry key from its campaign's universe.json."""
    campaign = registry[key]["campaign"]
    uni = json.loads((CAMPAIGNS / campaign / "universe.json").read_text(encoding="utf-8"))
    rollup_when = statuses or parse_rollup_when(campaign)
    by_cik, by_slug = index_projects(key)

    buckets = {k: [] for k in ("rolled", "queued", "stale", "blocked", "discovered", "funds")}
    plan = []
    for m in uni.get("members", []):
        status = (m.get("coverage") or {}).get("status", "")
        hit = (by_cik.get(m.get("cik")) if m.get("cik") else None) or by_slug.get(m["ticker"])
        e = {"tag": m["ticker"], "name": m["name"]}
        if status in rollup_when and hit:
            slug, brief = hit
            e["note"] = f"{slug} ({status})"
            buckets["rolled"].append(e)
            plan.append((slug, brief))
        elif status in rollup_when:
            e["note"] = f"{status}, no project brief yet"
            buckets["queued"].append(e)
        elif status == "STALE":
            e["note"] = "data stale"
            buckets["stale"].append(e)
        elif status == "BLOCKED":
            e["note"] = (m.get("notes") or "")[:70]
            buckets["blocked"].append(e)
        elif status == "DISCOVERED":
            e["note"] = (m.get("notes") or "")[:70]
            buckets["discovered"].append(e)
    for f in uni.get("funds", []):
        buckets["funds"].append({"tag": f["ticker"], "name": f["name"], "note": f.get("role", "")})
    return plan, buckets, rollup_when


def plan_sector(key, registry):
    """Roll up child industry keys of a sector key (children = registry rows whose parent == key)."""
    buckets = {k: [] for k in ("rolled", "queued")}
    plan = []
    for child, row in registry.items():
        if row["parent"] != key:
            continue
        brief = PROJECTS / child / "reports" / f"{child}_brief.md"
        e = {"tag": child, "name": row["title"] or node_str(row)}
        if brief.exists():
            e["note"] = "industry report"
            buckets["rolled"].append(e)
            plan.append((child, brief))
        else:
            e["note"] = "no industry report yet"
            buckets["queued"].append(e)
    return plan, buckets, None


SECTIONS = [
    ("rolled", "Rolled up (brief gathered into _briefs/)"),
    ("queued", "Queued - no brief scaffolded yet"),
    ("stale", "Stale - coverage exists but data is stale"),
    ("blocked", "Blocked - in EDGAR, no loaded XBRL (revisit on uplist)"),
    ("discovered", "Discovered - classified in, not yet scaffolded (the coverage gap)"),
    ("funds", "Benchmarks - sector ETFs (reference, not coverage targets)"),
]


def render_watchlist(key, resolved, buckets):
    out = [
        f"# {key} Coverage - Watchlist (generated from the classified universe)",
        "",
        f"Aggregate key **{key}** = {resolved}. Regenerated by `tools/rollup_sources.py`;",
        "do not hand-edit - re-run after re-classifying.",
        "",
    ]
    for name, header in SECTIONS:
        if not buckets.get(name):
            continue
        out.append(f"## {header}")
        out += [f"- {b['tag']} ({b['name']}){' - ' + b['note'] if b.get('note') else ''}"
                for b in buckets[name]]
        out.append("")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="Roll a coverage key up into its aggregate project's sources")
    ap.add_argument("key", help="an aggregate key from classifications/keys.csv (e.g. CANNABIS, CONSUMER)")
    ap.add_argument("--statuses", help="comma list overriding campaign.yml rollup_when (industry keys only)")
    ap.add_argument("--write", action="store_true", help="apply (default is a dry run)")
    args = ap.parse_args()

    registry = load_keys()
    if args.key not in registry:
        raise SystemExit(f"Unknown key '{args.key}'. Defined keys: {', '.join(registry)}")
    row = registry[args.key]
    resolved = node_str(row)
    statuses = [s.strip().upper() for s in args.statuses.split(",")] if args.statuses else None

    if row["campaign"]:
        kind = "industry -> companies"
        plan, buckets, rollup_when = plan_industry(args.key, registry, statuses)
    else:
        kind = "sector -> industries"
        plan, buckets, rollup_when = plan_sector(args.key, registry)

    print(f"Rollup [{kind}]: {args.key} = {resolved}  ->  projects/{args.key}/sources/")
    if rollup_when:
        print(f"rollup_when = {rollup_when}")
    print(f"\nMatched {len(plan)} briefs:")
    for slug, _ in plan:
        print(f"  + {slug}")

    agg_dir = PROJECTS / args.key
    briefs_dir = agg_dir / "sources" / "_briefs"
    existing = {p.name for p in briefs_dir.glob("*_brief.md")} if briefs_dir.exists() else set()
    planned = {f"{slug}_brief.md" for slug, _ in plan}
    if existing:
        print("\nDiff vs existing _briefs/:")
        print(f"  reproduced : {sorted(existing & planned)}")
        print(f"  added      : {sorted(planned - existing) or '(none)'}")
        print(f"  in existing, NOT in plan: {sorted(existing - planned) or '(none)'} <- kept, review")
    for name, _ in SECTIONS:
        if name != "rolled" and buckets.get(name):
            print(f"\n{name}: {', '.join(b['tag'] for b in buckets[name])}")

    if not args.write:
        print("\nDry run. Re-run with --write to copy briefs + regenerate _watchlist.md.")
        return
    if not agg_dir.is_dir():
        raise SystemExit(f"\nAggregate project {agg_dir} does not exist - scaffold it first (e.g. just new {args.key}).")

    briefs_dir.mkdir(parents=True, exist_ok=True)
    for slug, brief in plan:
        shutil.copyfile(brief, briefs_dir / f"{slug}_brief.md")
    (agg_dir / "sources" / "_watchlist.md").write_text(render_watchlist(args.key, resolved, buckets), encoding="utf-8")
    print(f"\nWrote {len(plan)} briefs -> {briefs_dir.relative_to(ROOT)} and regenerated _watchlist.md.")


if __name__ == "__main__":
    main()
