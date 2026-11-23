"""
The industry classification tables: load them, check them, and answer "which industries
is this company in".

Two tables in classifications/:

  industries.csv  one row per node: id, parent, level, label, carried. The id is the
                  slug path (consumer-goods/cannabis/cannabis), so a node's ancestors
                  are its id's prefixes. Depth is open: a micro-industry is a new row
                  under a category.
  companies.csv   one row per company-industry pair: key (the projects/ slug), cik,
                  name, industry, primary. A company has one primary row and any
                  number of secondary rows.

Every subsector has at least one category. Where nobody has divided a subsector yet, its
one category is the subsector carried over (carried = yes); splitting it later replaces
that row with real categories.

Usage:
    uv run python tools/classifications.py            # check the tables, print a summary
    uv run python tools/classifications.py MSFT IREN  # show these companies' industries
"""

import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

DIR = Path(__file__).resolve().parent.parent / "classifications"
INDUSTRIES_CSV = DIR / "industries.csv"
COMPANIES_CSV = DIR / "companies.csv"
CROSSWALK_CSV = DIR / "sic-crosswalk.csv"
KEYS_CSV = DIR / "keys.csv"

LEVELS = ["sector", "subsector", "category", "micro"]


def _rows(path):
  with path.open(encoding="utf-8-sig", newline="") as f:
    return list(csv.DictReader(f))


def load_industries():
  """id -> row, in file order."""
  return {r["id"]: r for r in _rows(INDUSTRIES_CSV)}


def load_companies():
  return _rows(COMPANIES_CSV)


def lineage(node_id):
  """A node's ancestors and itself, root first: a/b/c -> [a, a/b, a/b/c]."""
  parts = node_id.split("/")
  return ["/".join(parts[: i + 1]) for i in range(len(parts))]


def labels(node_id, industries):
  """Display path, root first. A carried category repeats its subsector, so it is left out."""
  return [
    industries[n]["label"]
    for n in lineage(node_id)
    if industries[n]["carried"] != "yes"
  ]


def children(industries):
  out = defaultdict(list)
  for r in industries.values():
    if r["parent"]:
      out[r["parent"]].append(r["id"])
  return out


def resolve(sector, subsector, category, industries):
  """A (Sector, Subsector, Category) label triple, as sic-crosswalk.csv and keys.csv
  write it, to a node id. An empty category resolves to the carried category when the
  subsector has one, otherwise to the subsector itself (the row needs a per-company
  choice among its categories). None when the labels name no node."""
  by_parent_label = {(r["parent"], r["label"]): r["id"] for r in industries.values()}
  node = ""
  for label in (sector, subsector, category):
    if not label:
      break
    node = by_parent_label.get((node, label))
    if node is None:
      return None
  if node and not category and subsector:
    kids = children(industries)[node]
    if len(kids) == 1 and industries[kids[0]]["carried"] == "yes":
      return kids[0]
  return node or None


def memberships(industries=None, companies=None):
  """key -> [{id, labels, primary}], the primary industry first."""
  industries = industries or load_industries()
  out = defaultdict(list)
  for r in companies or load_companies():
    out[r["key"]].append(
      {
        "id": r["industry"],
        "labels": labels(r["industry"], industries),
        "primary": r["primary"] == "yes",
      }
    )
  for rows in out.values():
    rows.sort(key=lambda m: not m["primary"])
  return dict(out)


def catalog_industries():
  """key -> the `industries` list a research catalog item carries. A company gets its
  memberships; an aggregate key from keys.csv gets the one node it is the hub of."""
  industries = load_industries()
  out = memberships(industries)
  for r in _rows(KEYS_CSV):
    node = resolve(r["sector"], r["subsector"], r["category"], industries)
    if node:
      out[r["key"]] = [
        {"id": node, "labels": labels(node, industries), "primary": True, "hub": True}
      ]
  return out


def check():
  """Every rule the tables must hold. Returns a list of problems, empty when clean."""
  problems = []
  industries = load_industries()
  rows = _rows(INDUSTRIES_CSV)
  if len(rows) != len(industries):
    dupes = [i for i, n in Counter(r["id"] for r in rows).items() if n > 1]
    problems.append(f"industries.csv: duplicate ids {dupes}")
  kids = children(industries)

  for r in industries.values():
    i, depth = r["id"], r["id"].count("/")
    if r["parent"] != "/".join(i.split("/")[:-1]):
      problems.append(f"{i}: parent '{r['parent']}' is not the id's own prefix")
    if r["parent"] and r["parent"] not in industries:
      problems.append(f"{i}: parent '{r['parent']}' is not a node")
    if depth >= len(LEVELS) or r["level"] != LEVELS[depth]:
      problems.append(f"{i}: level '{r['level']}' does not match its depth")
    if r["level"] == "subsector" and not kids[i]:
      problems.append(f"{i}: a subsector needs at least one category")
    if r["carried"] == "yes":
      parent = industries.get(r["parent"], {})
      if r["level"] != "category" or r["label"] != parent.get("label"):
        problems.append(f"{i}: only a category named for its subsector is carried")
      if len(kids[r["parent"]]) != 1:
        problems.append(
          f"{i}: a carried category must be its subsector's only one; "
          "a split replaces it"
        )
      if kids[i]:
        problems.append(f"{i}: a carried category has no micro-industries; split it")

  primaries = Counter()
  seen = set()
  for r in load_companies():
    key, node = r["key"], r["industry"]
    if (key, node) in seen:
      problems.append(f"{key}: listed twice in {node}")
    seen.add((key, node))
    if node not in industries:
      problems.append(f"{key}: industry '{node}' is not a node")
      continue
    if industries[node]["level"] in ("sector", "subsector"):
      problems.append(f"{key}: attach at a category or deeper, not {node}")
    if kids[node]:
      problems.append(f"{key}: {node} has been divided; attach at one of its children")
    if r["primary"] == "yes":
      primaries[key] += 1
    else:
      primaries[key] += 0
  for key, n in primaries.items():
    if n != 1:
      problems.append(f"{key}: needs exactly one primary industry, has {n}")

  for path, cols in (
    (CROSSWALK_CSV, ("Sector", "Subsector", "Category")),
    (KEYS_CSV, ("sector", "subsector", "category")),
  ):
    for r in _rows(path):
      triple = tuple(r[c] for c in cols)
      if resolve(*triple, industries) is None:
        problems.append(
          f"{path.name}: {' > '.join(p for p in triple if p)} is not a node"
        )
  return problems


def main():
  industries = load_industries()
  by_key = memberships(industries)
  if len(sys.argv) > 1:
    for key in sys.argv[1:]:
      for m in by_key.get(key.upper(), []):
        mark = "primary" if m["primary"] else "also"
        print(f"{key.upper():8} {mark:8} {' > '.join(m['labels'])}  [{m['id']}]")
      if key.upper() not in by_key:
        print(f"{key.upper():8} not classified")
    return

  problems = check()
  levels = Counter(r["level"] for r in industries.values())
  carried = sum(1 for r in industries.values() if r["carried"] == "yes")
  companies = load_companies()
  print(
    f"industries: {len(industries)} nodes "
    f"({', '.join(f'{levels[lv]} {lv}' for lv in LEVELS if levels[lv])}; "
    f"{carried} categories carried over from their subsector)"
  )
  print(
    f"companies:  {len(by_key)} classified, {len(companies)} memberships, "
    f"{sum(1 for r in companies if r['review'] == 'yes')} marked for review"
  )
  if problems:
    print(f"\n{len(problems)} problem(s):")
    for p in problems:
      print(f"  - {p}")
    raise SystemExit(1)
  print("ok")


if __name__ == "__main__":
  main()
