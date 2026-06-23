"""
Emit the "previously on..." card for continuing coverage.

On a re-cover, `just recover` archives the prior outputs to projects/{T}/.history/{ver}/
then calls this to distill them into projects/{T}/sources/_prior_coverage.md — which
`just kickoff` appends to the Cowork prompt so the new report is written as the next
chapter in a running, multi-quarter coverage thread (not a one-off).

Usage:
    uv run python tools/prior_coverage.py TICKER .history/2026-Q2 2026-Q2
    (paths are relative to projects/{TICKER}/)
"""

import argparse
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def section(md, *keywords):
    """Return the body of the first '## ...<keyword>...' section, else ''."""
    lines = md.splitlines()
    for i, ln in enumerate(lines):
        if re.match(r"^#{2,3}\s", ln) and any(k.lower() in ln.lower() for k in keywords):
            body = []
            for nxt in lines[i + 1:]:
                if re.match(r"^#{2,3}\s", nxt):
                    break
                body.append(nxt)
            return "\n".join(body).strip()
    return ""


def main():
    ap = argparse.ArgumentParser(description="Write sources/_prior_coverage.md from an archived version")
    ap.add_argument("ticker")
    ap.add_argument("prior_rel", help="prior version dir relative to the project (e.g. .history/2026-Q2)")
    ap.add_argument("version", help="prior version label (e.g. 2026-Q2)")
    args = ap.parse_args()

    pdir = os.path.join(ROOT, "projects", args.ticker)
    prior = os.path.join(pdir, args.prior_rel)
    t = args.ticker

    meta = {}
    sp = os.path.join(prior, "scripts", f"{t}_script.json")
    if os.path.exists(sp):
        with open(sp, encoding="utf-8") as f:
            meta = (json.load(f) or {}).get("metadata", {})

    brief_path = os.path.join(prior, "reports", f"{t}_brief.md")
    brief = ""
    if os.path.exists(brief_path):
        with open(brief_path, encoding="utf-8") as f:
            brief = f.read()

    h1 = next((l[2:].strip() for l in brief.splitlines() if l.startswith("# ")), t)
    priced = next((l.strip(" *") for l in brief.splitlines() if l.strip().startswith("*")), "")
    hook = section(brief, "Hook")
    bottom = section(brief, "Bottom Line", "Bottom-Line")

    label = meta.get("coverage_label")
    head = f"# Prior coverage — {args.version}" + (f" · {label}" if label else "")
    sub = " · ".join(x for x in [meta.get("filing_type"), meta.get("filing_date")] if x)

    out = [head]
    if sub:
        out.append(f"_{sub}_")
    out += [
        "",
        f"**Last report:** {meta.get('video_title') or h1}",
    ]
    if meta.get("video_description"):
        out.append(f"**Then, in one line:** {meta['video_description']}")
    if priced:
        out.append(f"**Filing/pricing note from last time:** {priced}")
    if hook:
        out += ["", "## What we said last quarter (prior hook)", hook]
    if bottom:
        out += ["", "## What we were watching (prior bottom line)", bottom]
    out += [
        "",
        "---",
        f"_This is **CONTINUING COVERAGE**. Full prior brief: `{args.prior_rel}/reports/{t}_brief.md`. "
        "Open the new brief and the video hook by referencing the above — what we said and the price/setup "
        "then — then lead with **what changed this quarter**. Carry the thesis forward and contrast then vs now. "
        "Set `metadata.coverage_label` (e.g. \"Q2 FY2026 update\") in the script._",
    ]

    dest = os.path.join(pdir, "sources", f"_prior_coverage.md")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(f"Wrote {dest}  (prior {args.version})")


if __name__ == "__main__":
    main()
