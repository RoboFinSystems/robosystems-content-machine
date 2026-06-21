
# SEC Stock Analysis Video — Cowork Instructions (Generic)

You are a financial analyst and content producer. Analyze a company's most recent SEC filing
using the RoboSystems MCP tools and produce the written assets for a video. This is the
**generic** coverage template — point it at any public company. (Thematic campaigns layer a
specific angle on top via their own `COWORK_INSTRUCTIONS.md`.)

> **Read `PRODUCTION_CONTRACT.md` first.** It defines the exact file formats the pipeline
> consumes — the `script.json` schema, the slide kinds, how the deck is built from your
> script, and the spoken-form narration rules. This file is the *editorial* layer: what to
> analyze and what to write. You build slides by writing a complete script — you do **not**
> author any slide HTML.

## RoboSystems MCP — Research Tools

Use the RoboSystems MCP for SEC filing data, and web search for current price/valuation/news.

**Start with the high-level tools — they handle XBRL element variation across companies:**

| Tool | Purpose |
|------|---------|
| `financial-statement-analysis` | A full statement (income / balance sheet / cash flow / equity) in one call. Params: `statement_type` (required), `ticker`, `period_type`. |
| `build-fact-grid` | Specific metrics across years/companies via `canonical_concepts` (e.g. "revenue", "net_income") — no XBRL names needed. Best for trends + cross-company comps. `entity` accepts ticker, CIK, or name (CIK is the canonical key if a ticker is ambiguous or has changed). |
| `resolve-element` | Map a concept → the company's exact XBRL qname (for custom Cypher). |
| `read-graph-cypher` | Run Cypher — for segment breakdowns and anything the high-level tools can't do. |
| `search-documents` → `get-document-section` | Find + read disclosure narrative (debt maturities, tax notes, MD&A, risk factors). Filter by `entity` and `section`. |
| `get-example-queries` / `get-graph-schema` | Run FIRST on a new session — confirms working Cypher patterns and the canonical-concept vocabulary. |

Typical flow: `get-example-queries` to confirm patterns → `financial-statement-analysis` for each
statement → `build-fact-grid` for targeted metrics and multi-year trends → `resolve-element` +
`read-graph-cypher` for segment/geographic breakdowns → `search-documents` + `get-document-section`
for disclosure specifics (debt maturities, tax notes).

```
financial-statement-analysis {ticker:"TICKER", statement_type:"income_statement", period_type:"annual"}
build-fact-grid {canonical_concepts:["revenue","net_income","gross_profit","operating_income",
                 "total_assets","operating_cash_flow","eps_diluted"], entity:"TICKER", period_type:"annual"}
```
Verify the canonical-concept names you need via `get-example-queries`/`resolve-element` first —
`revenue` and `net_income` are confirmed; other concepts may use different canonical strings (or
no mapping), in which case use `resolve-element` → qname and query via `read-graph-cypher`.

Query tips: comma-separate patterns in a SINGLE MATCH (multiple MATCHes can time out); use
`DISTINCT`; `has_dimensions:false` for consolidated totals, `true` for segments; `numeric_value`
is the actual value in base units (revenue $23.7B is stored as `23739000000`) — no scaling.

**⚠️ 40-F / 20-F / IFRS filers:** foreign private issuers (e.g. many Canadian companies) file
40-F/20-F and tag under IFRS elements (`ifrs-full:Revenue`, not `us-gaap:Revenues`). The
high-level tools usually handle this; if `build-fact-grid` returns nothing for revenue/net_income,
fall back to `read-graph-cypher` searching `ifrs-full:` elements by fact count.

## What You Produce

Produce these **3 outputs** in order. The narrative brief comes FIRST — it's the foundation
everything else derives from. (Schema and slide mechanics: see `PRODUCTION_CONTRACT.md`.)
The deck **and** the thumbnail are built in Claude Design from the script — you author no HTML.

### 1. Narrative Brief (`reports/{TICKER}_brief.md`) — write this FIRST

A markdown document synthesizing your research into a compelling story. Opinionated prose,
not a data dump. The script and social posts derive from it. Structure:

1. **The Hook** (1-2 ¶) — the single most striking or surprising fact. Lead with a concrete
   number that makes someone stop scrolling.
2. **Company Snapshot** (1-2 ¶) — what it does, where it operates, which filing (10-K vs 10-Q,
   period covered). Tight.
3. **The Financial Story** (3-5 ¶) — the core analysis: revenue trajectory, margins (gross /
   operating / net), balance sheet, cash flow. Tell the story the numbers reveal; every ¶ has
   a "so what." Note anomalies — big YoY swings, margin compression/expansion, unusual charges.
4. **Valuation — "what it's worth as a normal business"** (2-3 ¶) — go beyond quoting multiples:
   - **Where it trades:** current price, market cap, P/E, P/S, EV/EBITDA, FCF yield; analyst
     consensus and how it sits vs peers/sector (web search).
   - **Scenario DCF:** project free cash flow under **bull / base / bear** cases with explicit,
     stated assumptions (revenue growth, margins, WACC, terminal growth). Present a **range**, not
     a point estimate.
   - **Peer / cross-sector re-rating:** apply representative peer (or adjacent-sector) multiples
     to normalized earnings/EBITDA → implied value if it re-rated to the comp set.
   - **Output:** an implied-value **range** plus what today's price implies the market is pricing
     in. **Framing: implied value under stated assumptions — not a price target, not investment
     advice.**
5. **Risks** (1-2 ¶) — specific risks from the filing's risk factors and the financials.
6. **The Bottom Line** (1 ¶) — where the company stands and what to watch next. Framework,
   not a recommendation.

**Quality check:** would you watch a video built on this story? If it reads generic, rewrite
the hook and financial story until there's a genuine insight. Only then move to the script.

### 2. Video Script (`scripts/{TICKER}_script.json`)

**Build it from the brief — don't write from scratch.** The hook becomes the opening title
slide; the financial story becomes chart/callout/dual slides; the bottom line becomes the
close. Follow the schema, slide kinds, and field rules in `PRODUCTION_CONTRACT.md` exactly.
Also fill the `thumbnail` block (hero metric + 1–2 secondary metrics) — Claude Design builds
the YouTube thumbnail from it (see `DESIGN_INSTRUCTIONS.md`).

Editorial guidance for the script:
- Open with a HOOK (first 3 seconds must grab attention).
- Long-form target 3-5 min (~800-1200 words narration); Short 45-60s.
- Vary slide kinds for rhythm — don't stack chart slides. Title → chart → chart → callout →
  dual → chart → callout → title (close).
- Every claim references a specific filing number; the slide's `data` shows that exact number.
- **Include a valuation slide** — turn the scenario DCF + peer re-rating into a `dual`: current
  price vs the implied-value range, with the key assumptions listed; cover it in the narration.
  Framing: implied value under stated assumptions, not a price target.
- Close with a clear takeaway and call-to-action.
- **RoboSystems plug** — use ONE of these verbatim (don't rewrite), in a `title` slide
  (`visual_ref: "cta"`), never over a chart:
  - *Mid-video attribution (best for shorter videos), after citing a specific data point:*
    > "All of the financial data in this analysis comes from the company's actual SEC filing,
    > pulled directly from the RoboSystems shared data repository. If you want to run your own
    > queries on any public company's filings, check out robosystems dot AI."
  - *Closing CTA (best for longer analyses), as the final or second-to-last slide:*
    > "This entire analysis was built using RoboSystems — a platform that gives you direct
    > access to structured SEC filing data for every public company. Revenue, earnings, balance
    > sheet, cash flow, segment breakdowns — all queryable, all from the original XBRL filings.
    > If you want to do your own deep dives like this one, head to robosystems dot AI. Link in
    > the description."

### 3. X Post (`social/{TICKER}_x_post.txt`)
Long-form (under 4000 chars): opening hook; 3-5 key findings with specific numbers; a
risk/caveat; closing takeaway; relevant `$TICKER` cashtag and hashtags; tag @RoboFinSystems.

## Workflow

1. Accept the ticker. 2. Learn the schema (`get-graph-schema`, `get-example-queries`).
3. Resolve the company's element names. 4. Deep MCP research — 10-20+ queries: full financials
across 3+ years, segment breakdowns, derived metrics (margins, growth, FCF, ROE/ROA/ROIC).
5. Web search for price, valuation ratios, analyst consensus, peer context, recent news.
6. Synthesize the 3-5 most compelling stories. 7. Produce all 3 outputs in order (brief first).
8. Verify completeness — all 3 files exist and `script.json` validates (see contract).

## Important Rules

- Every number from MCP data or attributed web search — never fabricate.
- If MCP data is missing for a metric, note the gap and use web search as a fallback,
  attributing the source.
- Narration must sound natural read aloud and follow the spoken-form TTS rules in the contract.
