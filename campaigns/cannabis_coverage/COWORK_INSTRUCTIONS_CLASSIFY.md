# Cannabis Coverage: Universe Classification - Cowork Instructions (classify mode)

You are building this campaign's **coverage universe by classification**, not by
hand. The campaign is keyed to an industry-taxonomy node
(`campaign.yml`: `key: CANNABIS` = **Consumer Goods > Cannabis**). Your job is to
produce `universe.json`: the set of SEC-registered entities that classify into
that node, each marked with how classifiable it is and how coverage-ready it is.

There are two passes. **Pass 1 validates** the names we already cover (a known
answer to check the method against). **Pass 2 discovers** the cannabis companies
we do NOT cover yet - especially the Canadian LPs and other SEC filers that are
in the knowledge graph with loaded reports. Discovery is the point: it finds the
coverage gaps.

## Read before starting
- **`campaign.yml`** - the industry key and the coverage policy.
- **`../../classifications/README.md`** - the model + the classification method.
- **`../../classifications/industry-classification.csv`** - the vocabulary. Confirm
  the exact leaf: `Consumer Goods,Cannabis,` (subsector, no category).
- **`../../classifications/sic-crosswalk.csv`** - the SIC routing hints. Note there
  is **no cannabis SIC**: MSOs file under `2833` (crosswalks to Health Care > Drug
  Manufacturers - wrong), agricultural `0100`/`0200`, drug retail, or "Services".
  Use these as discovery seeds, but classify by recall, not by the SIC's target.
- **`../../classifications/etf-classifications.csv`** - the ETF/fund taxonomy. Any ETF
  you find (e.g. `$MSOS`) classifies here, not in the company taxonomy: a cannabis fund
  is `Equities > Industries > Cannabis`. Funds go in the `funds` output, not `members`.
- **`sources/tickers.md`** + **`sources/ticker_crosswalk.md`** - the known covered
  set and the CIK crosswalk. **CIK is the stable join key** - tickers churn.
- **`sources/universe_*.csv`** (Seeking Alpha export) - a broad cannabis universe
  that already reaches past our covered names. A strong discovery seed.

## The classification rule (per entity)
**Step 0 - route by entity type.** An operating company (files 10-K / 20-F / 40-F
financials) uses the steps below and lands in `members` or `adjacent`. An ETF / fund
(holds other companies) uses `etf-classifications.csv` instead and lands in `funds` -
key it by ticker + SEC `seriesId`, since ETFs in one trust share a CIK (MSOS / MSOX /
YOLO are all AdvisorShares Trust). Funds are reference / benchmark entities, not
coverage targets.

1. **Crosswalk floor.** Look up `e.sic` in the crosswalk. An `exact` full-leaf
   match is trustworthy. For cannabis it will not be - proceed to recall.
2. **Recall override.** Classify the real business from your own knowledge of the
   company (name + ticker are usually enough), using the crosswalk `Notes` as a
   hint you may override. Cannabis operators -> `Consumer Goods > Cannabis`.
3. **Confidence + fallback.** Record a 0-1 confidence. Below ~0.6, or for a name
   you do not recognize, fall back to the crosswalk's structural map and say so.
4. **One primary, gated secondary.** Exactly one primary node. Add a secondary
   only if the company draws material revenue from a genuinely distinct sector
   (SNDL = cannabis + liquor retail; Village Farms = cannabis + produce). Cap 2.
5. **Structural vs adjacent.** Plant-touching (cultivation / processing / branded
   product / dispensary) -> a `members` entry. Cannabis-themed but classifies
   elsewhere (REIT, lender, ETF, hydroponics retailer, psychedelics biotech) ->
   an `adjacent` entry with its REAL node. Do not tag cannabis-as-investment
   (a tobacco company with a cannabis stake) as cannabis.

## The SEC graph
Entities carry `identifier` (PK), `cik`, `ticker` (legacy OTC), `name`, `sic`,
`sic_description`, `state_of_incorporation`. Facts hang off entities:
`(f:Fact)-[:FACT_HAS_ENTITY]->(e:Entity)`, `(f)-[:FACT_HAS_PERIOD]->(p:Period)`.
**Keep queries single-entity or single-label** - multi-hop cross-company grids
time out. Use `read-graph-cypher` (fast). One entity at a time for anything that
traverses Facts.

## Pass 1 - Validate the known set

For each covered CIK in `tickers.md` (key by CIK or the legacy ticker the graph
carries), pull the entity, classify it, and confirm it lands in
`Consumer Goods > Cannabis`. Flag any that do not - that is a curation error worth
surfacing.

**Entity + SIC:**
```cypher
MATCH (e:Entity)
WHERE e.ticker = 'GTBIF'          // or: e.cik = '0001795139'
RETURN e.identifier, e.cik, e.ticker, e.name, e.sic, e.sic_description,
       e.state_of_incorporation
```
Classify from the returned name/SIC + your recall. Expect the SIC to disagree
(e.g. `2833` -> the crosswalk says Health Care; you override to Cannabis). Record
`method: "recall"` and the confidence.

## Pass 2 - Discover the uncovered

Find cannabis entities in the graph that are NOT in `tickers.md`. Run all four
strategies, union the candidates, then classify each by recall and gate on
confidence. **The Canadian LPs (Canopy, Tilray, Cronos, Aurora, SNDL, Village
Farms, OrganiGram) are the priority target** - they are plant-touching and many
file with the SEC.

**(a) Name-keyword scan (single-label, fast):**
```cypher
MATCH (e:Entity)
WHERE toLower(e.name) CONTAINS 'cannabis' OR toLower(e.name) CONTAINS 'marijuana'
   OR toLower(e.name) CONTAINS 'cbd'      OR toLower(e.name) CONTAINS 'hemp'
   OR toLower(e.name) CONTAINS 'dispensar'OR toLower(e.name) CONTAINS 'weed'
RETURN e.cik, e.ticker, e.name, e.sic, e.sic_description ORDER BY e.name
```
(Catches "Canopy", "Cannabist", "Cannabis"; misses "Trulieve", "Tilray", "Cronos",
"Aurora" - which is why the next two strategies matter.)

**(b) SIC-cluster scan** - the SICs cannabis names hide in; recall filters out the
real pharma/ag companies:
```cypher
MATCH (e:Entity)
WHERE e.sic IN ['2833','0100','0200','2836','5912','8000','2000','0900']
RETURN e.cik, e.ticker, e.name, e.sic, e.sic_description ORDER BY e.sic, e.name
```

**(c) Cross-check the Seeking Alpha universe.** For every ticker in
`sources/universe_summary.csv` not already in `tickers.md`, look it up by ticker
in the graph and classify it. This list already contains ACB, CGC, CRON, and other
uncovered names.

**(d) Business-description search.** Use `search-documents` for
"cannabis cultivation", "multi-state operator", "adult-use", "licensed producer",
then `get-document-section` and map the document back to its entity. This catches
operators whose name and SIC give nothing away.

For each candidate: classify (recall), gate confidence, and if it is genuinely
`Consumer Goods > Cannabis` and not already covered, add it as a `members` entry
with `coverage.status: "DISCOVERED"`.

## Coverage-readiness gate (per member)

A member is coverage-ready only if it is in the graph WITH loaded XBRL reports.
Check each one entity at a time:
```cypher
MATCH (e:Entity)<-[:FACT_HAS_ENTITY]-(f:Fact)-[:FACT_HAS_PERIOD]->(p:Period)
WHERE e.ticker = 'CGC' AND p.duration_type = 'annual'
RETURN count(DISTINCT f) AS fact_count,
       collect(DISTINCT substring(p.end_date, 0, 4)) AS fiscal_years
```
- `fact_count > 0` -> record `sec.has_xbrl_facts: true`, `sec.fiscal_years`, and a
  `status` of `READY` (or `DISCOVERED` if new).
- In EDGAR but `fact_count = 0` (common for **40-F** Canadian/foreign filers whose
  XBRL is not loaded) -> `status: "BLOCKED"`, `sec.has_xbrl_facts: false`, and a
  note. Do not drop it - the blocked coverage gap is a finding.

## Output

### 1. `universe.json`
```jsonc
{
  "key": "cannabis",
  "resolved": "Consumer Goods > Cannabis",
  "generated_at": "<ISO-8601>",
  "method": "cowork-classify v1 (crosswalk floor + recall override + SEC-graph verification)",
  "members": [
    {
      "cik": "0001795139", "ticker": "GTBIF", "name": "Green Thumb Industries",
      "sector": "Consumer Goods", "subsector": "Cannabis", "category": null,
      "is_primary": true, "secondary": null,
      "confidence": 0.99, "method": "recall",
      "sec": { "in_graph": true, "filing_type": "10-K",
               "fiscal_years": ["2022","2023","2024","2025"], "has_xbrl_facts": true },
      "coverage": { "covered": true, "status": "DONE", "source": "known" },
      "notes": "SIC 2833 -> crosswalk says Health Care; overridden to Cannabis by recall."
    }
  ],
  "adjacent": [
    {
      "cik": "...", "ticker": "IIPR", "name": "Innovative Industrial Properties",
      "sector": "Real Estate", "subsector": "Diversified", "category": null,
      "theme": "cannabis", "confidence": 0.95,
      "reason": "Cannabis-focused REIT (landlord to operators), not plant-touching."
    }
  ]
}
```
`coverage.status` values: `DONE` / `READY` / `STALE` / `BLOCKED` (from `tickers.md`
for known names) and `DISCOVERED` for new finds. `coverage.source`: `known` or
`discovered`.

Add a `funds` array for any ETFs found: `{ cik, series, ticker, name,
taxonomy: "etf", asset_class, sector, subsector, category, role, notes }`, classified
via `etf-classifications.csv` (cannabis funds -> `Equities > Industries > Cannabis`;
leveraged -> `Alternatives > Leveraged & Inverse > Index Leveraged`).

### 2. `_classification_notes.md`
A short human-readable summary: what discovery found (especially the uncovered
Canadian LPs and their coverage status), what is BLOCKED and why, any known name
that failed to classify as cannabis (a possible curation error), and any secondary
classifications assigned. This is the read-out that decides what gets covered next.

## Guardrails
- Every classification traces to recall + the graph evidence you pulled. Never
  fabricate an SEC-graph fact - if you did not query it, mark the field `null`.
- Do not over-tag. Psychedelics (Compass Pathways), hemp-adjacent wellness, a
  cannabis ETF, a REIT, or a company with only a cannabis investment are NOT
  `Consumer Goods > Cannabis` - they are `adjacent` (with their real node) or out.
- Prefer the CIK for every graph lookup and every row you write. Tickers move.
