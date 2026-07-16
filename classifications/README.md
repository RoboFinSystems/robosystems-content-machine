# Industry Classification

Reference data + the model for keying a **campaign** to an **industry**, and for
building a campaign's coverage universe by **classifying SEC-registered entities**
instead of hand-curating a ticker list.

This is a POC of the platform-level SEC industry-classification system. The
durable design lives in the platform repo's design vault
(`local/RoboSystems/specs/sec-industry-classification.md`); this folder is where
we prove the taxonomy and the classification method against a real campaign
(`campaigns/cannabis_coverage`) before it is built into the SEC data pipeline.

## The files

| File | What it is |
|---|---|
| `industry-classification.csv` | The **company** vocabulary: a 3-level `Sector > Subsector > Category` taxonomy (~189 leaves across 9 sectors). Bespoke, not GICS/NAICS - it carries finance-native buckets (Digital Assets, Defense Technology & Drones, mining producer tiers) and a `Consumer Goods > Cannabis` subsector. Depth varies: some leaves terminate at the subsector (Cannabis has no category breakout). |
| `sic-crosswalk.csv` | ~400 SIC codes mapped to a company-taxonomy node, with a `Match Quality` column (`exact` / `parent` / `review` / `approx`) and a `Notes` column. A routing hint, not the answer: `exact` full-leaf matches can be trusted; everything else needs judgment. |
| `etf-classifications.csv` | The **ETF / fund** vocabulary: a 4-level `Asset Class > Sector > Subsector > Category` taxonomy organized by investment STRUCTURE (Alternatives, Commodities, Crypto, Currencies, Equities, Fixed Income, Multi-Asset), not operating-company industry. A cannabis sector fund is `Equities > Industries > Cannabis`; a leveraged one is `Alternatives > Leveraged & Inverse > Index Leveraged`. |
| `keys.csv` | The **aggregate-key registry**: ticker-form keys (CANNABIS, CONSUMER) for the sector / industry coverage nodes, each mapped to a taxonomy node + its parent key. The aggregate counterpart to SEC's `company_tickers.json`. |

## Two entity types, two classification systems

Classification is entity-type-aware. Route first, then classify:

- **Operating companies** (they file 10-K / 20-F / 40-F financials) classify into the
  **company taxonomy** (`industry-classification.csv`), via the SIC crosswalk floor +
  recall. A cannabis MSO is `Consumer Goods > Cannabis`.
- **ETFs / funds** (they hold other companies) classify into the **ETF taxonomy**
  (`etf-classifications.csv`). A cannabis sector fund is `Equities > Industries >
  Cannabis`. Funds are not operating businesses, so the company taxonomy does not fit
  them - they are surfaced separately (a `funds` group), never as company members.

The two systems share a **Cannabis** label on purpose, so they bridge: the ETF node
`Equities > Industries > Cannabis` is the fund-side mirror of the company node
`Consumer Goods > Cannabis`. That bridge is what lets a cannabis campaign relate its
operators (`members`) to its sector-benchmark ETFs (`funds`, e.g. `$MSOS`).

**ETF identity is not the CIK.** ETFs in the same trust share one registrant CIK
(MSOS, MSOX, and YOLO are all AdvisorShares Trust, CIK `0001408970`), disambiguated by
SEC `seriesId` / `classId`. So for funds, key on ticker + seriesId, not CIK alone. ETFs
also do not file operating-company financial XBRL, so they are reference / benchmark
entities, not coverage targets with statements.

## The key model - one identity for companies and aggregates

Everything in the coverage graph is a **ticker-form key** that indexes
`projects/{KEY}/`. There are two kinds, in one namespace:

- **Company keys** are SEC tickers (GTBIF, TCNNF), backed by a CIK; their registry is
  SEC's own `company_tickers.json`.
- **Aggregate keys** are defined codes for sectors and industries (CANNABIS, CONSUMER),
  registered in `keys.csv`. A campaign declares one via `campaign.yml` (`key: CANNABIS`).

Sectors and industries are not different *kinds* of thing - each is just a key that
maps to a taxonomy node, and the **level is derived** from that node: a key resolving to
a `Sector` only is sector-level; one resolving to a subsector / category is
industry-level. So `keys.csv` holds both in one table:

| key | parent | taxonomy node | campaign |
|---|---|---|---|
| `CONSUMER` | | Consumer Goods | (rolls up child keys) |
| `CANNABIS` | `CONSUMER` | Consumer Goods > Cannabis | `cannabis_coverage` |

An industry key's universe is **derived**: the SEC entities that classify into its node
(written to the campaign's `universe.json`), joined on **CIK** - the only stable
identifier, since tickers churn (uplistings, reverse splits, the temporary post-split
"D" symbols; see `campaigns/cannabis_coverage/sources/ticker_crosswalk.md`). Pick
aggregate keys that do not collide with a real ticker - they share the `projects/`
namespace.

## The classification method

For each entity: `name`, `ticker`, `sic`, `sic_description`, and (where useful)
the 10-K business description from the SEC graph.

1. **Crosswalk floor.** Look up the SIC in `sic-crosswalk.csv`. An `exact`
   full-leaf match is the answer for the easy majority.
2. **Recall override.** For everything else - and whenever the SIC is coarse,
   catch-all, or simply wrong for the business - classify by recall of the actual
   company, using the crosswalk row's `Notes` as a hint but overriding it freely.
3. **Confidence gate + fallback.** Below the confidence threshold, or for a name
   the model does not recognize, fall back to the crosswalk's structural map.

**Cannabis is the textbook case for step 2.** There is no cannabis SIC code. MSOs
file under `2833` (Medicinal Chemicals, which crosswalks to Health Care > Drug
Manufacturers), agricultural SICs (`0100` / `0200`), drug retail, or "Services" -
so the crosswalk **cannot** find them and, worse, points them at the wrong sector.
Recall knows "Green Thumb / Trulieve / Canopy Growth = cannabis operator"
instantly. The classifier must override the SIC walk for the whole subsector.

## Structural vs thematic (why `adjacent` exists)

Industry classification asks where an **entity** primarily belongs, which is not
the same as a coverage **theme**. Plant-touching operators classify as
`Consumer Goods > Cannabis`. But a cannabis-focused REIT (IIPR) is Real Estate, a
cannabis lender (AFC Gamma) is Financials > Lending, an MSO ETF is a fund, a
hydroponics retailer (GrowGeneration) is ancillary retail. These are
cannabis-themed but classify **elsewhere** - so they are surfaced in `universe.json`
as `adjacent` (with their real node), never auto-folded into the coverage set.
This is also the anti-over-tagging guardrail: a psychedelics biotech (Compass
Pathways) or a tobacco company with a cannabis investment is **not** cannabis.

## Multi-industry

Default: exactly one primary classification per entity. A second is allowed only
when the entity draws material revenue from a genuinely distinct sector (SNDL is
cannabis + liquor retail; Village Farms is cannabis + produce). Hard cap of two.
Never add a secondary just because a company touches software or technology.

## Aggregation levels (rollup reports)

The taxonomy is not only how a campaign finds its universe - it is also the
**rollup lattice for aggregate research**. Each level synthesizes from the level
below, the same way financial facts roll up a calc hierarchy:

| Level | Key | Rolls up | Example |
|---|---|---|---|
| **company** | an SEC ticker | (leaf - individual coverage) | `GTBIF` -> `projects/GTBIF` |
| **industry** | an aggregate key on a leaf node | its `universe.json` members (companies) | `CANNABIS` = `Consumer Goods > Cannabis` |
| **sector** | an aggregate key on a `Sector` node | its child industry keys' reports | `CONSUMER` = Consumer Goods, over Cannabis, Beverages, ... |

It is hub-and-spoke at every level: a sector hub points to its industry hubs, an
industry hub points to its company spokes. The `CANNABIS` project is the working
industry-level proof - its `sources/_briefs/{TICKER}_brief.md` are the member
companies' published briefs, gathered so the aggregate can synthesize from them,
and its `_watchlist.md` is the coverage-status view of the universe (who is
DONE / READY vs BLOCKED-on-data).

**Classification feeds the rollup.** The members an industry report aggregates are
exactly the `universe.json` members with publishable coverage (`DONE` / `READY`);
the blocked names are the watchlist's "revisit on uplist" set. So it is one chain -
**classify -> universe -> rollup -> aggregate report** - applied recursively up the
taxonomy. A key's rung is derived from its `keys.csv` node; `tools/rollup_sources.py KEY`
walks it - a leaf key (CANNABIS) gathers member companies, a sector key (CONSUMER)
gathers its child industry reports, through the same code path.

Where a subsector has categories (e.g. `Financials > Banks > {Domestic, Foreign,
Savings & Thrifts}`), there is an intermediate subsector rollup between company and
sector. Cannabis has no category breakout, so it collapses to the clean three rungs:
company -> Cannabis (industry) -> Consumer Goods (sector).
