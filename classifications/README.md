# Industry Classification

Reference data + the model for keying a **campaign** to an **industry**, and for
building a campaign's coverage universe by **classifying SEC-registered entities**
instead of hand-curating a ticker list.

This is a POC of a platform-level SEC industry-classification system: this folder
is where the taxonomy and the classification method get proven against a real
campaign (`campaigns/cannabis_coverage`) before anything is built into the SEC
data pipeline.

## The files

| File | What it is |
|---|---|
| `industries.csv` | The **company** vocabulary, one row per node: `id`, `parent`, `level`, `label`, `carried`. Three guaranteed levels, `Sector > Subsector > Category` (9 sectors, 100 subsectors, 333 categories, 99 micro-industries), and open below that: a micro-industry is a new row under a category. Bespoke, not GICS/NAICS - it carries finance-native buckets (Digital Assets, Defense Technology & Drones, mining producer tiers) and a `Consumer Goods > Cannabis` subsector. The `id` is the slug path (`consumer-goods/cannabis/us-operators`), so a node's ancestors are its id's prefixes. |
| `companies.csv` | The **master list**: one row per company-industry pair - `key` (the `projects/` slug, or the ticker for a filer we have not covered), `cik`, `name`, `industry` (a node id), `primary`, `method`, `confidence`, `review`, `notes`. A company has exactly one `primary` row and any number of secondary rows. It holds every operating company, SPAC and shell in the public SEC filer index. |
| `funds.csv` | The filers that are **funds, not companies** (spot commodity and crypto trusts, futures pools, ETF series): `key`, `cik`, `name`, `holds`. They are kept out of `companies.csv` and wait for the ETF taxonomy. |
| `sic-crosswalk.csv` | ~400 SIC codes mapped to a company-taxonomy node, with a `Match Quality` column (`exact` / `parent` / `review` / `approx`) and a `Notes` column. A routing hint, not the answer: `exact` full-leaf matches can be trusted; everything else needs judgment. |
| `etf-classifications.csv` | The **ETF / fund** vocabulary: a 4-level `Asset Class > Sector > Subsector > Category` taxonomy organized by investment STRUCTURE (Alternatives, Commodities, Crypto, Currencies, Equities, Fixed Income, Multi-Asset), not operating-company industry. A cannabis sector fund is `Equities > Industries > Cannabis`; a leveraged one is `Alternatives > Leveraged & Inverse > Index Leveraged`. |
| `keys.csv` | The **aggregate-key registry**: ticker-form keys (CANNABIS, CONSUMER) for the sector / industry coverage nodes, each mapped to a taxonomy node + its parent key. The aggregate counterpart to SEC's `company_tickers.json`. |

## Levels, carried categories and growth

Every company has a sector, a subsector and a category. Not every subsector has been
divided into categories yet (32 of the 100 have not), so an undivided subsector carries
itself over as its one category, marked `carried = yes`: `Consumer Goods > Tobacco
Products > Tobacco Products`. Nothing downstream has to handle a missing level, and the flag is the list of
subsectors still waiting to be divided.

- **A carried name shows once.** Display paths drop the carried row: `Consumer Goods >
  Tobacco Products`, never with the name twice.
- **A split replaces the carried row.** When a subsector is divided, every member moves to
  a real category and the carried row is deleted. Left beside the new categories it would
  become a catch-all.
- **Attach a company at the deepest node that fits.** Its ancestors are derived from the
  id, so a group that is too small can fall back up the tree without a second column.
  Micro-industries are optional: a company that fits none of a category's micros stays
  at the category.
- **Thin industries are fine.** Two or three companies that an analyst would compare are
  a node; they still roll up into the category and subsector above them.
- **Add industries as they develop.** A new category or micro-industry is one row in
  `industries.csv` plus moving the members' rows in `companies.csv`.

`just classify` checks every rule above (and that `sic-crosswalk.csv` and `keys.csv`
still name real nodes); `just classify MSFT IREN` shows a company's industries.

## How a row was placed

`method` says what the placement rests on, and `confidence` how far to trust it:

| method | meaning |
|---|---|
| `filing` | Placed from the business description in the filer's own latest annual (or quarterly) report. |
| `recall` | Placed from knowledge of the company, without reading its filing. |
| `crosswalk` | The SIC baseline only. Nobody has judged it; it may sit at a subsector. |

Every `filing` row was read twice. Where the two readers chose different industries the
row carries `review = yes`, low confidence, and the other reader's node in `notes`. For a
`filing` or `recall` row placed by this pass, `notes` opens with what the company does.

To classify a new company: look up its SIC in `sic-crosswalk.csv` for a starting point,
read the business section of its latest annual report, and attach it at the deepest node
that fits. SIC is a hint, never the answer.

## The catalog field

`tools/reindex.py` writes each published item's memberships into the research catalog as
`industries`: a list of `{id, labels, primary}`, primary first, rebuilt from these tables
on every reindex. An aggregate key from `keys.csv` (CANNABIS) carries the node it is the
hub of, with `hub: true`. A published ticker with no row in `companies.csv` is named at
the end of the reindex. So classifying a company is one line in `companies.csv` before its
brief is published.

## Two entity types, two classification systems

Classification is entity-type-aware. Route first, then classify:

- **Operating companies** (they file 10-K / 20-F / 40-F financials) classify into the
  **company taxonomy** (`industries.csv`), via the SIC crosswalk floor +
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

A company can sit in more than one industry: one `primary` row and a row for each other
industry it draws **material revenue** from (Tilray is cannabis + brewing; IREN is cloud
infrastructure + bitcoin mining). There is no cap, but the materiality test holds: never
add an industry because a company touches software, technology or AI, or the groups stop
meaning anything.

Links and peer groups use every membership. A rollup uses the **primary only**, so a
sector aggregate never counts a two-industry company twice.

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

Where a subsector has categories (e.g. `Financials > Banks > {US Commercial, Foreign,
Savings & Thrifts}`), there is an intermediate rollup between company and subsector, and
again at each micro-industry. The CANNABIS key sits on the `Consumer Goods > Cannabis`
subsector, so it rolls up all three of its categories (US Operators, Canadian Producers,
Hemp & CBD).
