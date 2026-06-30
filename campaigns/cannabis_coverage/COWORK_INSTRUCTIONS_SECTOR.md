# RoboSystems Coverage: Cannabis SECTOR Report — Cowork Instructions (sector mode)

You are a financial analyst and content producer. This is a **sector report** — a single piece that
analyzes the **whole U.S. cannabis multi-state-operator (MSO) group at once**, not one company. It is
the *hub* that ties together our individual `/research/{TICKER}` coverage of the nine names.

> **The seed report is your validated spine — then do a per-company SECOND PASS.** The cross-company
> analysis lives in **`sources/_sector_report.md`** (every FY2025 figure already pulled from SEC XBRL via
> the RoboSystems graph). Cross-company grid queries on these nine are flaky — they time out — so **go one
> company at a time** with `financial-statement-analysis` to **validate every scorecard number and surface
> additional insights** the aggregate missed, then turn it all into the **video assets** (script, brief,
> short, podcast, social). See "The per-company second pass" below.

> **Read `PRODUCTION_CONTRACT.md` first.** It defines the exact file formats the pipeline consumes —
> the `script.json` schema, the slide kinds (`title | chart | callout | dual`), the `short`/`qa` blocks,
> and the spoken-form TTS rules. This file is the *editorial* layer. You author **no HTML** — you build
> slides by writing a complete script.

## What is different from a single-ticker run

| Single-ticker run | This sector run |
|---|---|
| Analyze ONE company's filing via MCP | Validate + deepen all nine (per-company second pass), then synthesize the seed report |
| Slug = a real ticker | Slug = **`CANNABIS`** (a generic sector slug; every output file is `CANNABIS_*`) |
| Story = one company's arc | Story = the **sector arc**: a real industry, taxed into losses by one statute |
| Thumbnail hero = one P/E | Hero = the **sector paradox** number ($4.7B revenue / $606M tax / a loss) |
| Drives to the video | Also a **hub** — explicitly points viewers to all nine `/research/{TICKER}` pages |

## The per-company second pass (do this BEFORE writing)

Cross-company grid queries time out — **and so does `financial-statement-analysis` (25s) on these names.**
Use **raw Cypher via `read-graph-cypher`** (it returns in ~2s). The seed report's scorecard is your
reference, and each name's **published brief is in `sources/_briefs/`** (start from it for the qualitative
read, then verify the numbers live). For **each of the nine** (key by legacy ticker / CIK — see
`sources/ticker_crosswalk.md`; e.g. Trulieve = **TCNNF**, Verano = **VRNO**), run these two proven queries
(swap the `e.ticker` value), then `search-documents`:

**(a) Income statement + cash flow (annual, FY2025):**
```cypher
MATCH (f:Fact)-[:FACT_HAS_ELEMENT]->(el:Element),
      (f)-[:FACT_HAS_PERIOD]->(p:Period),
      (f)-[:FACT_HAS_ENTITY]->(e:Entity)
WHERE e.ticker = 'TCNNF'
  AND el.qname IN ['us-gaap:Revenues','us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax',
    'us-gaap:GrossProfit','us-gaap:OperatingIncomeLoss','us-gaap:IncomeTaxExpenseBenefit',
    'us-gaap:NetIncomeLoss','us-gaap:NetCashProvidedByUsedInOperatingActivities',
    'us-gaap:IncomeTaxesPaidNet','us-gaap:IncomeTaxesPaid','us-gaap:InterestPaidNet']
  AND f.has_dimensions = false AND p.duration_type = 'annual'
  AND p.end_date >= '2025-06-30' AND p.end_date <= '2026-02-28'
RETURN el.qname AS element, f.numeric_value AS value, p.end_date AS period_end ORDER BY element
```

**(b) Balance sheet (instant, 12/31/2025):**
```cypher
MATCH (f:Fact)-[:FACT_HAS_ELEMENT]->(el:Element),
      (f)-[:FACT_HAS_PERIOD]->(p:Period),
      (f)-[:FACT_HAS_ENTITY]->(e:Entity)
WHERE e.ticker = 'TCNNF'
  AND el.qname IN ['us-gaap:CashAndCashEquivalentsAtCarryingValue','us-gaap:Assets','us-gaap:Liabilities',
    'us-gaap:Goodwill','us-gaap:StockholdersEquity',
    'us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',
    'us-gaap:LongTermDebt','us-gaap:LongTermDebtNoncurrent','us-gaap:UnrecognizedTaxBenefits']
  AND f.has_dimensions = false AND p.period_type = 'instant' AND p.end_date = '2025-12-31'
RETURN el.qname AS element, f.numeric_value AS value ORDER BY element
```

Values are base units (revenue $1.18B = `1181180000`); `has_dimensions=false` = consolidated totals; all
nine report calendar FY2025 ending 12/31/2025. If an element returns nothing for a name, `resolve-element`
→ its exact qname. **(c)** Then `search-documents` + `get-document-section` (this tool works fine) for the
qualitative spine the aggregate can't see: the **uncertain-tax-position / 280E dispute** language, the
**debt-maturity schedule**, **legal proceedings** (IRS audits, the TerrAscend clawback suit), **subsequent
events** (uplistings, reverse splits, the Vireo–Fluent deal), and **segment / state revenue** mix.

Then **surface what the aggregate missed** and fold it into the brief and a slide or two: the per-company
cash-tax-vs-accrued gap, interest coverage and who's closest to a maturity wall, and who runs positive OCF
despite GAAP losses. **Validated cross-company already (use these):** 8 of 9 ran positive operating cash
flow (only Planet 13 negative); the nine accrued $606M of income-tax *expense* but paid only ~$127M in
cash (Trulieve accrued $208M, paid $1.5M; Planet 13 paid $0; Verano the exception at $78M of $92M) — the
~$479M gap is the reserve build. Correct any seed-report number the live statements move.
**Update the scorecard to the validated figures**, and note any discrepancy in the brief. Finish with a
light web refresh: current group price action and the latest catalyst news (the June 2026 broad DEA
hearing outcome, any uplisting).

## Read before starting
- **`sources/_sector_report.md`** — THE source of truth (the nine-company analysis + every number).
- **`CAMPAIGN_BRIEF.md`** — the cannabis macro thesis: 280E mechanics, the April 28 2026 medical-only
  Schedule III order, the contested broad DEA hearing, uplisting, the IRS clawback / TerrAscend suit.
- **`sources/_briefs/{TICKER}_brief.md`** — the nine published per-ticker reports (the qualitative spine:
  each company's thesis, catalyst nuance, footprint, management commentary). Synthesize from these and
  cross-check them against the live per-company statements.
- **`PRODUCTION_CONTRACT.md`** — schema + slide kinds + TTS rules.

## The anchor numbers (graph-sourced, FY2025 — the reference to validate against)

The nine operators, period ending 12/31/2025, every figure from SEC XBRL via the RoboSystems graph:

- **Aggregate:** revenue **$4.73B**, gross profit **$2.34B** (≈49.5% blended margin), income tax
  **$606M**, net income **−$675M**, combined pre-tax ≈ **−$69M**, unrecognized tax benefits **≈$2.1B**.
- **The punchline:** **8 of 9 paid income tax while posting a net loss.** The only GAAP-profitable
  name, **Green Thumb (+$114M)**, paid **$147M in tax — more than its $138M operating income.**
- **Per-company table is in `sources/_sector_report.md`** (revenue, gross profit/margin, operating
  income, income tax, net income, cash, equity, goodwill, unrecognized tax benefits, adj. EBITDA,
  net debt, maturity wall, revenue mix, re-rating band, tier).
- **The nine (with their published coverage slugs):** Trulieve (TRLV), Green Thumb (GTBIF), Verano
  (VRNOF), Ascend Wellness (AAWH), Vireo Growth (VREOF), Jushi (JUSHF), TerrAscend (TSNDF), MariMed
  (MRMD), Planet 13 (PLNH). Each has a full report at `robosystems.ai/research/{TICKER}`.

**Stance (unchanged):** fact-based reference report, not advice, no price targets. Implied values are
**scenario ranges** (a re-rating toward CPG multiples if 280E lifts), never targets.

## What You Produce

Same 7 outputs as a ticker run, adapted for the sector. **Brief first** (it's the foundation), then the
script, then the companions and publish metadata. Schema lives in `PRODUCTION_CONTRACT.md`.

### 1. Sector Brief (`reports/CANNABIS_brief.md`) — write FIRST
`sources/_sector_report.md` is already a strong brief. **Adopt and tighten it** into
`reports/CANNABIS_brief.md` — keep the structure (hook → "this is a real industry" → the 280E squeeze →
survival → the catalyst → the tiers → bottom line), keep every number, keep the scenario-band framing
and the disclaimer. Make the hook land harder if you can. Keep the methodology note (built via the
RoboSystems graph) — it's the product proof. End with the soft RoboSystems CTA (+ `[PROMO_CODE]` line
if a promo runs) and a pointer to the nine individual reports.

### 2. Video Script (`scripts/CANNABIS_script.json`) — build from the brief
A ~3–5 min sector narrative (~800–1200 words narration). Suggested arc (~12–13 slides — vary the kinds
for rhythm, fill exact numbers in every `slide.data`):

1. `title` **hook** — the paradox: "Nine companies. 4.7 billion dollars in revenue. A 675 million dollar loss." (`visual_ref: hook`)
2. `callout` **tax_paradox** — "606 million dollars in tax — on a pre-tax LOSS." `tone: negative`. (the 280E signature)
3. `dual` **what_280e** — what Section 280E does (taxed on gross profit, not net income; only COGS deductible).
4. `chart` **scorecard_ops** — `chart_type: table` — the operators: Revenue, Gross margin, Adj. EBITDA across the nine.
5. `chart` **scorecard_tax** — `chart_type: table` — the squeeze: Income tax, Net income, Tax as % of gross profit.
6. `callout` **reserves** — "≈2.1 billion dollars of disputed taxes on their balance sheets" (the gambit + the IRS clawing it back; TerrAscend sued May 2026).
7. `chart` **survival** — `chart_type: table` — who can wait: Cash, Equity (flag Ascend −$47M / Jushi −$115M negative equity), Maturity wall.
8. `dual` **catalyst** — the switch, half-flipped: Stage 1 medical-only relief (April 2026, done) vs Stage 2 broad DEA order (contested).
9. `chart` **rerating** — `metric_cards` or `table` — 280E-normalized EBITDA × CPG multiples (≈10–14×) → implied re-rating; framed as scenario bands.
10. `dual` **tiers** — the three tiers: Survivors (GTBIF, TRLV) / Operating machines (VRNOF, TSNDF, JUSHF) / High-beta options (AAWH, VREOF, MRMD, PLNH).
11. `title`/`callout` **bottom_line** — "Strip out one line of the tax code and these nine earn 2.3 billion dollars of gross profit a year…"
12. `title` **cta** — the RoboSystems plug (verbatim, below).
13. `title` **coverage** — "Full coverage on all nine — robosystems dot AI slash research." (the hub→spoke close)

- **metadata:** `ticker: "CANNABIS"`, `company: "U.S. Cannabis Sector"`, `filing_type: "Sector report (9 issuers, FY2025)"`, a sector `video_title` (≤70 chars, e.g. "Nine Cannabis Companies, One Tax Code: The 280E Scorecard"), keyword `tags`, `campaign: "Cannabis Coverage"`.
- **thumbnail block:** `hero` = the dissonance number ("$606M TAX / $0 PROFIT" or "$4.7B → A LOSS"); `banner: "THE 280E SCORECARD"`; `secondary` = 1–2 of ["9 operators", "$2.1B disputed tax", "49% gross margin"].
- **RoboSystems plug (verbatim, as the CTA slide):**
  > "This entire analysis was built using RoboSystems — an open source platform that gives you direct access to structured SEC filing data for every public company. Revenue, earnings, balance sheet, cash flow, segment breakdowns — all queryable, all from the original XBRL filings. You can set up the same tools I just used in about five minutes. Head to robosystems dot AI to get started — link in the description."

### 3. X Post (`social/CANNABIS_x_post.txt`)
A single post (NOT a thread). **Lead the first line with the sector cashtag `$MSOS`** (this *is* the
sector piece — `$MSOS` is the channel; `$MSOX` optional as a 2nd, never more than 2). Hook on the
paradox; 3–5 findings with numbers (the $606M tax on a loss, $2.1B reserves, 8-of-9 taxed while losing
money, the re-rating math); the catalyst; a risk; closing takeaway; robosystems.ai + the promo line.
Closing line = `#Cannabis #MSO #280E #Rescheduling` + tag `@RoboFinSystems`. **No link in the body.**
**Never use `<` or `>`** anywhere (spell out "under"/"over") — X and YouTube reject the paste. Don't glue
a cashtag inside parens. The brief publishes as a native X Article (linked in `x_first_comment`).

### 4. YouTube Description (`social/CANNABIS_youtube_description.txt`)
Hook; links (robosystems.ai + the repo); promo line; timestamps (draft from `duration_estimate_seconds`,
finalize from `videos/CANNABIS_timestamps.txt` after render); 6–8 finding bullets with numbers; a 2–3
sentence 280E explainer; **a "Full coverage on each operator" list linking all nine
`https://robosystems.ai/research/{TICKER}` pages** (the hub→spoke payoff); disclaimer; hashtags.

### 5. Short — the `short` block in `scripts/CANNABIS_script.json`
A self-contained 9:16 (~20–45s): open on the paradox (nine companies, $4.7B revenue, $606M tax, still
a loss), name it as the U.S. cannabis sector, land the "taxed into losses by one statute" payoff, end on
a question ("What happens when the tax lifts?"). 4–8 caption cards carry it for muted viewers
(e.g. "9 OPERATORS · $4.7B REVENUE" → "$606M TAX" → "ON A $675M LOSS" → "ONE LINE OF THE TAX CODE" →
"$2.1B DISPUTED" → "WHAT IF IT LIFTS?"). Pick `broll_theme` tags (e.g. ["cultivation","markets","policy"])
and a `music_mood`. The long-form link goes in the pinned comment, not a card.

### 6. Q&A Podcast (`scripts/CANNABIS_qa.json`)
A CNBC-style two-voice conversation (host + analyst), ~5–8 min, about the **sector**: the 280E paradox,
the scorecard, the gambit/reserves and the IRS clawback, the half-flipped catalyst, the tiers, the
honest bull/bear, closing on the RoboSystems angle. Written for the ear; same TTS rules.

### 7. Publish metadata (`social/CANNABIS_publish.json`)
`youtube_title`, `short_title`, `short_pinned_comment` (`[YOUTUBE_LINK]`), `x_first_comment`
(`[X_ARTICLE_LINK]`), `podcast_episode_title`, `podcast_show_notes` (+ CTA / `[PROMO_CODE]`). Sector
framing throughout. (No LinkedIn for research.)

## Domain narration hints (spoken-form — on top of the contract's TTS rules)
- `280E` → "section two eighty E"; `Schedule I` → "schedule one"; `Schedule III` → "schedule three"
- `MSO` → "multi-state operator"; `EBITDA` → "Ebit-dah"; `OTC` → "over the counter"
- Agencies: `DEA` → "Drug Enforcement Administration"; `IRS` → "I R S"; `SEC` → "S E C"
- Cashtags/hashtags (`$MSOS`, `#Cannabis`) are for social text only — **never** in narration.
- Big numbers as words, one decimal ("four point seven billion dollars"); never `$ % x /` in narration.
- Company names: `Trulieve` reads "true-leave"; `Jushi` → "joo-shee"; `Vireo` → "veer-ee-oh"; phrase to avoid mis-say.

## Important rules
- Every number traces to the seed report (graph-sourced) or an attributed refresh. Never fabricate.
- Data on a slide must match the narration. Slide and words are one unit.
- This is a **hub** — the brief, the description, and the closing slide must point to the nine
  individual `/research/{TICKER}` reports.
- Completeness check: `scripts/CANNABIS_script.json` validates (`deck.slide_count` == segment count,
  unique ordered `visual_ref`s) and every output above exists before you finish.
