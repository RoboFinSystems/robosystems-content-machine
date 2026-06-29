
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

## Continuing coverage (if `sources/_prior_coverage.md` exists)

If `sources/_prior_coverage.md` is present, this is **not a first look — it's the next chapter** in an ongoing, quarterly coverage thread. Read that card first, then:

- **Open on the thread.** The brief's Hook and the video's first lines should reference the prior coverage — what we said and the price/setup *then* — and immediately pivot to **what changed this quarter** (new filing, new catalyst, price move). Don't re-introduce the company from scratch.
- **Carry the thesis forward.** Explicitly contrast then vs now (e.g. "we covered this at $X last quarter; revenue has since re-accelerated to…"). Update every number; keep the narrative continuity.
- **Stamp the label.** Set `metadata.coverage_label` in `scripts/{TICKER}_script.json` to a human label for this update (e.g. `"Q2 FY2026 update"`). The quarter key itself (e.g. `2026-Q2`) is derived automatically at publish — you only author the label.
- Sources accumulate: the new quarter's filing sits alongside the prior ones in `sources/`; the full prior brief is in `.history/`.

If the card is absent, this is **initiating coverage** — introduce the company fresh.

## What You Produce

Produce these **4 core outputs** in order (brief FIRST — it's the foundation everything else
derives from), then the **2 companion formats** (#5–6) and the **publish metadata** (#7). (Schema and slide mechanics: see
`PRODUCTION_CONTRACT.md`.) The deck **and** the thumbnail are built in Claude Design from the
script — you author no HTML.

**Promo code (optional placeholder).** Where copy invites sign-up, add the offer line
`New customers get 50% off your first month with code [PROMO_CODE].` Keep `[PROMO_CODE]` as a
literal token (swap in the live Stripe code at post time, or omit the line if no promo is
running) — never hardcode a real code here, since codes change and expire.

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

**Footer (optional CTA).** After the analysis, end with a one-line soft RoboSystems CTA; when a
promo is running, append `New customers get 50% off your first month with code [PROMO_CODE].`
Keep it a footer, separate from the analysis — never a sales pitch inside the report.

**Quality check:** would you watch a video built on this story? If it reads generic, rewrite
the hook and financial story until there's a genuine insight. Only then move to the script.

### 2. Video Script (`scripts/{TICKER}_script.json`)

**Build it from the brief — don't write from scratch.** The hook becomes the opening title
slide; the financial story becomes chart/callout/dual slides; the bottom line becomes the
close. Follow the schema, slide kinds, and field rules in `PRODUCTION_CONTRACT.md` exactly.
Also fill the `thumbnail` block (hero metric, optional banner, 1–2 secondary metrics) — Claude
Design builds the YouTube thumbnail from it (see `DESIGN_INSTRUCTIONS.md`). Banner: "COVERAGE
UPDATE" if this name was covered before, else "INITIATING COVERAGE" (or omit).

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
A **single post — NOT a numbered thread** (long-form is fine on X; no "1/ 2/ 3/"). Opening
hook; 3-5 key findings with specific numbers; a risk/caveat; closing takeaway; a closing
RoboSystems CTA (`robosystems.ai`) + the promo line (`New customers get 50% off your first
month with code [PROMO_CODE].`); relevant `$TICKER` cashtag **+ 1–2 cashtags anchoring the name to a prominent, on-topic ETF** (extra discovery reach — tag the sector/thematic ETF whose cashtag feed the right readers actually watch; this matters most for thin-volume names whose own `$TICKER` feed is quiet, where the ETF feed *is* the discovery channel; pick the most _relevant_ fund, not the broadest — don't tag a broad index like `$SPY` — and never more than 2 cashtags total) and topic hashtags; tag @RoboFinSystems. **Cashtag hygiene:** put the cashtags on the closing line, space-separated (`$TICKER $ETF …`); **never glue a `$`-cashtag inside parens** like `($TICKER)` — X only linkifies AND indexes a cashtag when a space (or start-of-post/@) precedes it, so a leading paren silently kills both the link and the cashtag-feed discovery. For a parenthetical in prose, use the bare ticker `(TICKER)` without the `$`.
**No link in the body.** On X the **full long-form is uploaded as native video**, and the brief
is published as a native X **Article** whose link goes in the first comment (`x_first_comment`)
— so there is no YouTube link on X at all (X throttles external links; native video + native
Article both win reach).

### 4. YouTube Description (`social/{TICKER}_youtube_description.txt`)
Hook (1-2 sentences); links: `https://robosystems.ai` and
`https://github.com/RoboFinSystems/robosystems-content-machine`; a `🎟️ New customers: 50% off
your first month with code [PROMO_CODE]` line under the links; **timestamps** — draft from
each segment's `duration_estimate_seconds` (start `0:00`, accumulate); after render, finalize from
the generated `videos/{TICKER}_timestamps.txt` (actual chapter times); 6-8
key-finding bullets with specific numbers; a 1-2 sentence plain-English explainer of any key
metric or term a cold viewer needs; disclaimer ("This is not investment advice. No price
targets."); relevant `$TICKER` and topic hashtags.

### 5. Short — the `short` block in `scripts/{TICKER}_script.json`
A **self-contained** 9:16 piece (~20–45s) for YouTube Shorts — a complete
micro-story, NOT a trailer. Write a **fresh standalone script** for the ear (not a slice of the
main narration): hook, the key numbers, **the company name + ticker** (a brief mystery hook is
fine, but reveal it), and a payoff that ends on a question or takeaway (long-form link → pinned
comment, not a card). Pick b-roll `id`s from `assets/broll/manifest.json` (or set a `broll_theme`
of tags to auto-pick by theme), and write 4–8 caption cards that stand alone for muted viewers. Schema + rules: `PRODUCTION_CONTRACT.md` → "Companion
formats → A". Rendered by `just short {TICKER}`.

### 6. Q&A Podcast (`scripts/{TICKER}_qa.json`)
A CNBC-style two-voice conversation (host + analyst), ~5–8 min, written for audio. Cover the
deck's beats as dialogue, open with the host framing the name, close on the RoboSystems angle.
Schema + rules: `PRODUCTION_CONTRACT.md` → "Companion formats → B". Rendered by
`just podcast-qa {TICKER}` (MP3 for Spotify, MP4 for YouTube).

### 7. Publish metadata (`social/{TICKER}_publish.json`)
The per-platform native copy that lives nowhere else — you author it; `just postpack {TICKER}`
stitches it into a paste-ready **publish pack** after production (merging in the real chapter
times, the S3 media links, and flagging any unresolved placeholders). A JSON object of string fields:
- `youtube_title` — clickable long-form title (≤100 chars).
- `short_title` — the Short's title/caption. *(omit if no short)*
- `short_pinned_comment` — the Short's pinned comment; use `[YOUTUBE_LINK]`. *(omit if no short)*
- `x_first_comment` — the X first comment under the video post; points to the brief published as an X **Article** (use `[X_ARTICLE_LINK]`). The full long-form is uploaded as native video; no YouTube link on X.
- `podcast_episode_title` — the Q&A episode title.
- `podcast_show_notes` — episode description / show notes (+ RoboSystems CTA).

_No LinkedIn for research — LinkedIn is the technical/blog lane, not a research channel. The 9:16 Short also posts as a **separate native X video** (a second cashtag at-bat); the postpack adds that section automatically from `short_title`._

Same placeholder rules as the rest (`[YOUTUBE_LINK]`, `[PROMO_CODE]`) — never hardcode the live URL or code.

## Workflow

1. Accept the ticker. 2. Learn the schema (`get-graph-schema`, `get-example-queries`).
3. Resolve the company's element names. 4. Deep MCP research — 10-20+ queries: full financials
across 3+ years, segment breakdowns, derived metrics (margins, growth, FCF, ROE/ROA/ROIC).
5. Web search for price, valuation ratios, analyst consensus, peer context, recent news.
6. Synthesize the 3-5 most compelling stories. 7. Produce the 4 core outputs in order (brief
first), then the Short block, the Q&A script, and the publish metadata (#7). 8. Verify completeness — all files exist and
`script.json` validates (see contract).

## Important Rules

- Every number from MCP data or attributed web search — never fabricate.
- If MCP data is missing for a metric, note the gap and use web search as a fallback,
  attributing the source.
- Narration must sound natural read aloud and follow the spoken-form TTS rules in the contract.
