
# SEC Stock Analysis Video - Authoring Instructions (Generic)

You are a financial analyst and content producer. Analyze a company's most recent SEC filing
using the RoboSystems MCP tools and produce the written assets for a video. The `/author` skill
runs this stage directly in Claude Code (the one-shot process - no separate Cowork app). This is
the **generic** coverage template - point it at any public company. (Thematic campaigns layer a
specific angle on top via their own `AUTHORING_INSTRUCTIONS.md`.)

> **Read `PRODUCTION_CONTRACT.md` first.** It defines the exact file formats the pipeline
> consumes — the `script.json` schema, the slide kinds, how the video is rendered from your
> script, and the spoken-form narration rules. This file is the *editorial* layer: what to
> analyze and what to write. You build slides by writing a complete script — you do **not**
> author any slide HTML.

## RoboSystems MCP — Research Tools

Use the RoboSystems MCP for SEC filing data — **the numbers AND the narrative** — and web search only for current price/valuation/news. There are **two co-equal pillars**: the **structured-financial** tools (the numbers) and **`search-documents` + `get-document-section`** (the filing prose). Do NOT stop at the numbers. The qualitative spine of the brief — **legal proceedings** (audits, lawsuits, investigations), **subsequent events** (splits, M&A, financings, uplistings), **MD&A** risk framing, segment/geographic color, and management's stated catalysts — lives in the document text, and `search-documents` is the only tool that retrieves it. Pull every qualitative claim from the filing via `search-documents`, not from the web or memory — that's what makes a claim filing-grade. **Rule of thumb: if you're about to assert a qualitative fact you didn't read in a filing (or an attributed source), search the documents for it first.**

**Start with the high-level tools — they handle XBRL element variation across companies:**

| Tool | Purpose |
|------|---------|
| `financial-statement-analysis` | A full statement (income / balance sheet / cash flow / equity) in one call. Params: `statement_type` (required), `ticker`, `period_type`. |
| `build-fact-grid` | Specific metrics across years/companies via `canonical_concepts` (e.g. "revenue", "net_income") — no XBRL names needed. Best for trends + cross-company comps. `entity` accepts ticker, CIK, or name (CIK is the canonical key if a ticker is ambiguous or has changed). |
| `resolve-element` | Map a concept → the company's exact XBRL qname (for custom Cypher). |
| `read-graph-cypher` | Run Cypher — for segment breakdowns and anything the high-level tools can't do. |
| `search-documents` → `get-document-section` | **The narrative pillar — run it for every name, not as an afterthought.** Full-text search the filings for the qualitative spine: legal proceedings (audits, lawsuits, investigations), subsequent events (splits, M&A, financings, uplistings), MD&A risk framing, debt-maturity schedule, tax notes, segment color. Filter by `entity` and `section`; cite the filing, not the web. |
| `get-example-queries` / `get-graph-schema` | Run FIRST on a new session — confirms working Cypher patterns and the canonical-concept vocabulary. |

Typical flow: `get-example-queries` to confirm patterns → `financial-statement-analysis` for each
statement → `build-fact-grid` for targeted metrics and multi-year trends → `resolve-element` +
`read-graph-cypher` for segment/geographic breakdowns → **`search-documents` + `get-document-section`
throughout** for the qualitative spine (legal proceedings, subsequent events, MD&A, debt maturities,
tax notes). Numbers and narrative are co-equal — not numbers-then-maybe-prose.

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

Produce the **4 core outputs** in order (brief FIRST - it's the foundation everything else
derives from), the **9:16 short** (#5) and the **publish metadata** (#6). (The Q&A podcast is
retired - author no `qa.json`.) Schema and slide mechanics: see `PRODUCTION_CONTRACT.md`.
Downstream the visuals render from your `script.json` via the animated **webdeck**
(`just webdeck-pipeline`), and thumbnails auto-generate from the brief (`just thumbnails`).
You author no slide HTML.

**Promo code (optional placeholder).** Where copy invites sign-up, add the offer line
`New customers get 50% off your first month with code [PROMO_CODE].` Keep `[PROMO_CODE]` as a
literal token (swap in the live Stripe code at post time, or omit the line if no promo is
running) — never hardcode a real code here, since codes change and expire.

## Surface rules - one analysis, framed three ways

Every name produces all the assets; they land on surfaces whose discovery mechanisms differ, and
a line tuned for one surface loses on the others. This is measured on our own analytics, not
assumed:

| Surface | How readers arrive | What wins there |
|---|---|---|
| **YouTube** | ~61% search, browse is negligible | The **searchable query**: Company + Ticker + quarter + the specific metric. Front-load what someone would actually type. |
| **X** | cashtag / topic feeds | The **contrarian curiosity line** plus an early ` $TICKER`. Small active cashtag communities out-reach marquee names 6-10x; crowded tickers land near the account median. |
| **/research** | direct link (a prospect we sent) + long-tail SERP | The **brief**. This is the asset a buyer actually reads, so it carries the analytical claim plainly. Page titles come from `seo_title` in `reindex.py`, never from the YouTube hook. |

**Never reuse one string across two surfaces.** The `youtube_title` is a query, the X hook is a
curiosity line, the Short title is a third thing again, and the brief's headline is the
analytical claim. A single string copied across all four reads as automated and underperforms on
at least two of them.

**The niche rule inverts between X and YouTube, so do not apply one rule to both.** On X an
underserved ticker is an advantage: its cashtag feed is quiet and the right readers are in it. On
YouTube an unsearched ticker has no audience at any quality level, because nobody types the
company's name. When a name is thin on YouTube demand, the title has to earn its traffic on the
*topic* rather than the ticker (the accounting mechanism, the sector question), not on the name.

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

**X Article cashtag (required, in the Hook).** The brief is published verbatim as a native X
**Article**, and an early cashtag is key to the algorithm picking the Article up for the
cashtag/topic feeds. Work `$TICKER` into **The Hook** at the first mention of the company name
(e.g. `Elevance Health $ELV grew revenue nine percent...`), so the cashtag lands in the first
paragraph - not the closing CTA. Same hygiene as the X post: a space must precede the `$`
(never `($TICKER)` - a leading paren kills both the link and the cashtag-feed indexing; for a
parenthetical use the bare `(TICKER)` without the `$`). One early cashtag is the requirement;
after that, refer to the company by name.

**Tables (use them freely).** Markdown pipe tables in the brief render as real formatted
tables in the X Article and on the /research portal - the pipeline handles the conversion.
Whenever 3+ rows of figures line up, prefer a compact table over a stat-dense paragraph:
quarter results vs. estimates, bull/base/bear DCF scenarios, the multiples re-rating grid,
segment or regional breakdowns. 1-3 tables per brief is a good target. Keep the prose for
the story and the tables for the numbers; standard `| a | b |` syntax with a header row.

**Footer (optional CTA).** After the analysis, end with a one-line soft RoboSystems CTA; when a
promo is running, append `New customers get 50% off your first month with code [PROMO_CODE].`
Keep it a footer, separate from the analysis — never a sales pitch inside the report.

**Quality check:** would you watch a video built on this story? If it reads generic, rewrite
the hook and financial story until there's a genuine insight. Only then move to the script.

### 2. Video Script (`scripts/{TICKER}_script.json`)

**Build it from the brief — don't write from scratch.** The hook becomes the opening title
slide; the financial story becomes chart/callout/dual slides; the bottom line becomes the
close. Follow the schema, slide kinds, and field rules in `PRODUCTION_CONTRACT.md` exactly.
Do **not** author a `thumbnail` block; `just thumbnails` generates them from the brief.

Editorial guidance for the script:
- Open with a HOOK: lead with the single most surprising number or tension in the first ~15
  seconds, BEFORE any company setup or context. The first 30 seconds is YouTube's retention gate,
  and retention is what search rankings ride on - no slow throat-clearing intro.
- Long-form target 3-5 min (~800-1200 words narration).
- Vary slide kinds for rhythm — don't stack chart slides. Title → chart → chart → callout →
  dual → chart → callout → title (close).
- Give every segment an `eyebrow` — a 2-4 word section label in the deck's editorial voice
  ("The Top Line", "Read the Split", "Capital Returns"). Skip it only on the closing CTA;
  numbering is automatic.
- Every claim references a specific filing number; the slide's `data` shows that exact number.
- **Include a valuation slide** — turn the scenario DCF + peer re-rating into a `dual`: current
  price vs the implied-value range, with the key assumptions listed; cover it in the narration.
  Framing: implied value under stated assumptions, not a price target.
- Close with a clear takeaway and call-to-action.
- **Close on the generalization, not just the ticker.** The analysis ending at the company's
  conclusion sells the analysis; it does not sell the machine that made it. Immediately before
  or inside the CTA slide, land ONE beat that widens the frame: no analyst wrote this, the same
  pipeline reads any filer's XBRL, and a private company reporting in the same format is the
  same job. One or two sentences, concrete and flat - never a boast, never a feature list.
  Write it fresh per name so it hangs off that company's specific finding, e.g.
  > "Nobody wrote this by hand. Every number came out of the filing itself, and the same
  > pipeline runs on any of the ten thousand companies that file with the SEC."
- **RoboSystems plug** - use ONE of these verbatim (don't rewrite), in a `title` slide
  (`visual_ref: "cta"`), never over a chart. **The door is the SEC Shared Repository, not the
  homepage:** name the repository in the narration, put `robosystems.ai/pricing` in the slide
  subhead, and link it in the YouTube description. Never speak a price - tiers change and the
  video does not.
  - *Mid-video attribution (best for shorter videos), after citing a specific data point:*
    > "All of the financial data in this analysis comes from the company's actual SEC filing,
    > pulled directly from the RoboSystems SEC Shared Repository. It is a subscription you can
    > point your own tools at, across every public company that files. Link in the description."
  - *Closing CTA (best for longer analyses), as the final or second-to-last slide:*
    > "This entire analysis was built on the RoboSystems SEC Shared Repository: structured
    > filing data for every public company that files. Revenue, earnings, balance sheet, cash
    > flow, segment breakdowns, all queryable, all from the original XBRL. If you want to run
    > your own deep dives like this one, the link is in the description."

### 3. X Post (`social/{TICKER}_x_post.txt`)
A **single post — NOT a numbered thread** (long-form is fine on X; no "1/ 2/ 3/"). Opening
hook; 3-5 key findings with specific numbers; a risk/caveat; closing takeaway; relevant `$TICKER` cashtag **+ 1–2 cashtags anchoring the name to a prominent, on-topic ETF** (extra discovery reach — tag the sector/thematic ETF whose cashtag feed the right readers actually watch; this matters most for thin-volume names whose own `$TICKER` feed is quiet, where the ETF feed *is* the discovery channel; pick the most _relevant_ fund, not the broadest — don't tag a broad index like `$SPY` — and never more than 2 cashtags total) and topic hashtags; tag @RoboFinSystems. **Cashtag placement & hygiene:** **lead with the cashtags** — `$TICKER $ETF` go on the FIRST line (front placement gets more topic-feed reach than burying them at the end, and the tag sits above the fold where the feed crops); the topic hashtags + @RoboFinSystems tag go on the closing line. Keep cashtags space-separated and **never glue a `$`-cashtag inside parens** like `($TICKER)` — X only linkifies AND indexes a cashtag when a space (or start-of-post/@) precedes it, so a leading paren silently kills both the link and the cashtag-feed discovery. For a parenthetical in prose, use the bare ticker `(TICKER)` without the `$`. **Never use `<` or `>`** in any social copy, YouTube description, or brief — YouTube and X parse them as HTML tags and reject the whole paste. Spell comparisons out: `under 1x`, `over $740M` (not `<1x` / `>$740M`).
**No link and no promo in the body.** The X post carries **no `robosystems.ai` link and no
promo-code line** - both suppress reach (X throttles external links, and a discount CTA on every
post reads as spam and drags engagement). Keep the RoboSystems CTA and any promo to the YouTube
description and podcast notes, never the X post. Every post leads with substantive text and the
cashtag. (An earlier version of this rule claimed link-only captions get a fraction of a text
post's reach - **retracted 2026-07-26**: that was a measurement artifact which filed native X
Articles in the same bucket as outbound links. Articles are our HIGHEST-reach format, median 380
vs 272 for text+video and 112 for a text post carrying a self-link. Publish the Article on every
name.) On X the **full long-form is uploaded as native
video**, and the brief is published as a native X **Article** whose link goes in the first
comment (`x_first_comment`) - so there is no YouTube link on X at all (native video + native
Article both win reach).

### 4. YouTube Description (`social/{TICKER}_youtube_description.txt`)
**Open with a search-first line** (the first line, like the title, is a primary ranking signal):
restate the Company + Ticker + quarter + the topic keywords a searcher would type before any
flourish. Then a 1-2 sentence hook; links: **`https://robosystems.ai/pricing` first** (the SEC
Shared Repository door - the thing this video is actually selling), then `https://robosystems.ai` and
`https://github.com/RoboFinSystems/robosystems-content-machine`; a `🎟️ New customers: 50% off
your first month with code [PROMO_CODE]` line under the links; a voice-credit line
`Voiceover by ElevenLabs: https://try.elevenlabs.io/v9z3wzm97gk3` with a following
`Disclosure: the ElevenLabs link is a referral link.` note (the video narration is ElevenLabs);
**timestamps** — draft from
each segment's `duration_estimate_seconds` (start `0:00`, accumulate); after render, finalize from
the generated `videos/{TICKER}_timestamps.txt` (actual chapter times); 6-8
key-finding bullets with specific numbers; a 1-2 sentence plain-English explainer of any key
metric or term a cold viewer needs; disclaimer ("This is not investment advice. No price
targets."); relevant `$TICKER` and topic hashtags.

### 5. The 9:16 short (REQUIRED - three files)
Every name ships a vertical short. It is **not** a crop of the 16:9 video: it is its own
purpose-built piece, rendered by the same engine at 1080x1920, and one asset serves both the
X native-video post and the YouTube Short.

- `scripts/{TICKER}_short_script.json` - 5-6 beats. **Aim ~630 narration characters for a ~45s
  short.** Measured on real renders: ElevenLabs runs ~15-16 characters per second and the
  finished video lands ~1.1x the narration once transitions and holds are added.
  `metadata{ticker, company, quarter, tags}`; each
  segment `{id, kind, narration, slide}` with `kind` one of:
  - `hook` - `slide{headline, punch, tone}`: the surprising turn
  - `stat` - `slide{kicker, big, context, tone}`: one huge number
  - `cards` - `slide{eyebrow, headline, cards:[{label,value,change}], highlight}`: 2-3 metric cards
  - `points` - `slide{eyebrow, headline, points:[{text,value,tone,highlight}], footnote}`: 3-4 rows
  - `cta` - `slide{headline, subhead}`: the SEC Shared Repository, subhead `robosystems.ai/pricing`

  Narration is spoken-form (captions derive from it automatically). Reuse the already-verified
  long-form numbers. Arc: hook -> the number -> the turn -> why -> valuation -> CTA.
- `social/{TICKER}_short_x_post.txt` - the X post body: substantive, early ` $TICKER` cashtag,
  ~200-270 chars, framed as a 60-second clip and distinct from the long-form `x_post`.
- `social/{TICKER}_short_youtube.txt` - **line 1 = the Short title** (hook-first, different from
  both the long-form YouTube title and the X hook, under 100 chars); the rest is the
  description with `[LONGFORM_URL]`, a `robosystems.ai/pricing` line, and `#Shorts`.

### 6. Publish metadata (`social/{TICKER}_publish.json`)
The per-platform native copy that lives nowhere else — you author it; `just postpack {TICKER}`
stitches it into a paste-ready **publish pack** after production (merging in the real chapter
times, the S3 media links, and flagging any unresolved placeholders). A JSON object of string fields:
- `youtube_title` — **search-first** long-form title (≤100 chars). YouTube discovery for this
  channel is almost entirely SEARCH (browse is dead), so front-load the query a viewer would
  actually type: Company + Ticker + the quarter/filing ("Q2 FY26 Earnings") + the specific
  angle/metric, then a short curiosity tail. Aim at the specific low-competition long-tail, not
  the crowded bare-ticker term. **Make it DIFFERENT from the X hook**: X rewards the contrarian
  curiosity line, YouTube rewards the searchable query; don't reuse the same string on both.
- `x_first_comment` — the X first comment under the video post; points to the brief published as an X **Article** (use `[X_ARTICLE_LINK]`). The full long-form is uploaded as native video; no YouTube link on X.

_No LinkedIn for research - LinkedIn is the technical/blog lane, not a research channel. The 9:16 short carries its own copy in the two `social/` files above (#5), not in `publish.json`. The Q&A podcast is retired - no `podcast_*` fields, no `qa.json`._

Same placeholder rules as the rest (`[YOUTUBE_LINK]`, `[PROMO_CODE]`) — never hardcode the live URL or code.

## Workflow

1. Accept the ticker. 2. Learn the schema (`get-graph-schema`, `get-example-queries`).
3. Resolve the company's element names. 4. Deep MCP research — 10-20+ queries: full financials
across 3+ years, segment breakdowns, derived metrics (margins, growth, FCF, ROE/ROA/ROIC).
5. Web search for price, valuation ratios, analyst consensus, peer context, recent news.
6. Synthesize the 3-5 most compelling stories. 7. Produce the 4 core outputs in order (brief
first), then the 9:16 short (#5) and the publish metadata (#6). 8. Verify completeness — all
files exist and `just validate {TICKER}` passes.

## Important Rules

- Every number from MCP data or attributed web search - never fabricate.
- **Never use em-dashes (`—`) or en-dashes (`–`)** in any generated output - briefs, scripts,
  social copy, publish metadata, slide text, or narration. Use a spaced hyphen ` - ` for a clause
  break and a plain `-` for ranges (`$8.9-9.2B`, `FY2021-FY2025`). The brief ships verbatim as an
  X Article and the social copy posts as-is, so this is a hard formatting rule (see
  PRODUCTION_CONTRACT Universal rules).
- If MCP data is missing for a metric, note the gap and use web search as a fallback,
  attributing the source.
- Narration must sound natural read aloud and follow the spoken-form TTS rules in the contract.
