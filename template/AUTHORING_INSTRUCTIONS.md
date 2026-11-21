
# SEC Equity Research Brief - Authoring Instructions (Generic)

You are a financial analyst. Analyze a company's most recent SEC filing, read what the market
already says about it, and write a research brief that tells a reader something the existing
coverage does not, with every figure about the company traced to its filings. The brief
publishes to roboinvestor.ai/research and as an X Article. About one brief in five later gets a
video; only then is a script written. This is the **generic** coverage template: point it at any
public company. (Thematic campaigns layer a specific angle on top via their own
`AUTHORING_INSTRUCTIONS.md`.)

A run is started by `projects/{TICKER}/TASK.md` (written by `/batch-research`) or by `/author`.
The task names the filing by accession and the research tier (middle by default, deep for a
video pick). Where the task and this file differ, the task wins.

> **`PRODUCTION_CONTRACT.md` is for video picks.** It defines the `script.json` schema, the
> slide kinds and the spoken-form narration rules. A brief-only run needs none of it: the three
> deliverables and their fields are all below.

## Research method: the web, the filing, then four checks

Research runs in this order, and every step writes down what it found before the next starts.

**1. The web pass, before any drafting.** Write `sources/_web_research.md`, appending as you go.
Cover four things:
- **The coverage frame**: how the market read this filing's results, the earnings call's main
  themes, and the consensus narrative in one or two lines.
- **Events since the filing date, to today**: deals, financings, guidance changes, management
  changes, activist or M&A news, lawsuits, regulatory actions.
- **Context filings cannot give**: the current share price and market value (dated), consensus
  estimates and price targets, and two or three peer multiples. One source that carries price,
  consensus and peer multiples together (such as stockanalysis.com) saves searches.
- **Gaps**: what the coverage misses that a filing could answer.

For every item record the claim, the source, the URL, the date, and whether it is (a) verifiable
in a filing or (b) context only. End the file with two short lists: "What the market already
knows" and "What to look for in the filing". Budget: about 15 to 20 searches (`WebSearch`,
`mode: "standard"`, `"extended"` only where standard comes back thin) and a handful of full page
reads (`WebFetch`). Prefer the original report to a summary of it; when only a summary was
reachable, say so ("the Wall Street Journal, as summarized by ...").

**2. The filing.** The research below, with the two MCP servers.

**3. Four checks, every brief.** Each found something the pilots (2026-11-20) would otherwise
have missed:
- **A. Later filings.** `mcp__xbrlkit__search_filings` with the company's CIK, from the filing
  date to today. Read every 8-K and any other material filing. (BILL agreed to be sold two weeks
  after its 10-Q; only an 8-K said so.)
- **B. Wording changes.** Compare these sentences with the prior 10-K, using `search-text` on
  both: customer concentration (the "no single customer" line), related parties, segments, the
  business description, and significant accounting policies. A dropped or added phrase is a
  finding. (Microsoft's 10-Q dropped "customer or" from its 10% line in the quarter OpenAI
  reached 10.8% of revenue.) When the 10-Q's risk factors say only "no material changes", the
  business description is where the change shows.
- **C. Web leads in the filings.** For every (a) item in the notes, record the filing that
  confirms it, or "not in a filing". A web figure the filing contradicts is corrected from the
  filing. (A web source put Workiva's debt at $720M; the 10-Q says $702.0M of notes.)
- **D. Capital returns by quarter.** Buybacks, dividends and share counts by quarter, from the
  equity note and the cash flow statement: shares repurchased, the average price paid, the
  authorization left. (Workiva's sharpest detail, and no web source had it.)

**4. Choose the lead.** Name the coverage frame in one line in the notes, then lead with what the
filing shows that the frame misses. A brief that leads with the filing's biggest number when the
market already knows it has not done its job.

**The deep tier (video picks, when the task says `deep`).** The same steps with a much wider web
pass: use the `anthropic-skills:deep-research` skill if it is available, otherwise many extended
searches and full page reads across several angles. Add a fifth check: **E. Peers from their
filings**, the brief's key disclosure read from each main peer's latest 10-Q and verified in
xbrlkit, so the peer comparison is filing-grade.

**The line that does not move.** Every number about the company's own results, balance sheet,
commitments or segments comes from an SEC filing and is verified in xbrlkit before it goes in
the Hook, a table or the Bottom Line. Web material appears only with its source named and dated
in the sentence ("per Reuters on November 12"), and never as the basis for a figure about the
company's own financials. Prices, consensus and peer multiples are allowed on those terms. A web
claim no filing confirms is used only attributed, or not at all. (The rule exists because a
brief once shipped an unattributed claim lifted from a news summary and had to be corrected.)

## RoboSystems MCP - Research Tools

Use the RoboSystems MCP for SEC filing data — **the numbers AND the narrative** — and web search only for current price/valuation/news. There are **two co-equal pillars**: the **structured-financial** tools (the numbers) and **`search-documents` + `get-document-section`** (the filing prose). Do NOT stop at the numbers. The qualitative spine of the brief — **legal proceedings** (audits, lawsuits, investigations), **subsequent events** (splits, M&A, financings, uplistings), **MD&A** risk framing, segment/geographic color, and management's stated catalysts — lives in the document text, and `search-documents` is the only tool that retrieves it. Pull every qualitative claim from the filing via `search-documents`, not from the web or memory — that's what makes a claim filing-grade. **Rule of thumb: if you're about to assert a qualitative fact you didn't read in a filing (or an attributed source), search the documents for it first.**

**Start with the high-level tools — they handle XBRL element variation across companies:**

| Tool | Purpose |
|------|---------|
| `financial-statement-analysis` | A full statement (income / balance sheet / cash flow / equity) in one call. Params: `statement_type` (required), `ticker`, `period_type`. |
| `build-fact-grid` | Specific metrics across years/companies via `canonical_concepts` (e.g. "revenue", "net_income") — no XBRL names needed. Best for trends + cross-company comps. `entity` accepts ticker, CIK, or name (CIK is the canonical key if a ticker is ambiguous or has changed). |
| `resolve-element` | Map a concept → the company's exact XBRL qname (for custom Cypher). |
| `read-graph-cypher` | Run Cypher — for segment breakdowns and anything the high-level tools can't do. |
| `describe-filing` → `search-text` → `read-text` | **One filing's whole text**: its Items with offsets, every place it says something (cover page, footnotes, exhibits, an 8-K's press release), then the passage read in full. Takes `ticker` plus `accession`. Use it for check B (wording changes) and to read any Item whole. |
| `disclosures` → `information-block` | One note or table read whole: rows, breakdowns by its own axes, calculation footing, text blocks. `disclosures` first (cheap), then one block. |
| `search-documents` → `get-document-section` | **Across the corpus** - which filings discuss something. **The narrative pillar - run it for every name, not as an afterthought.** Full-text search the filings for the qualitative spine: legal proceedings (audits, lawsuits, investigations), subsequent events (splits, M&A, financings, uplistings), MD&A risk framing, debt-maturity schedule, tax notes, segment color. Filter by `entity` and `section`; cite the filing, not the web. |
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

### xbrlkit: the verification pillar (one filing, read from the source)

`mcp__xbrlkit__*` is a second, complementary MCP server. Use both; they are not interchangeable.

- **The graph is the corpus.** Indexed, curated, many filers and many periods. Right for
  discovery, multi-year trends and cross-company comps.
- **xbrlkit is one filing**, parsed in memory and read from the source. No index and no curation,
  so it sees everything the filer actually tagged, including their own extension concepts and the
  details tables a consolidated view never surfaces.

**Use xbrlkit whenever a number is load-bearing.** Anything that lands in the hook, on a slide, in
a headline claim or in the thesis gets confirmed against the filing before you write it down.

Loop: `load_filing` **by accession** (`cik:accession`, with an explicit `filing_id`), then
`describe_filing` for period keys and networks, then
`disclosures` with a topic for the cheap family index, then `information_block` on ONE block id for
the detail. `fact_grid` for values, `search_text` / `read_text` for prose. Never guess a concept
name, `resolve_element` first. `disclosures` before `information_block` always: the latter is the
expensive call and costs 15,000-30,000 characters.

**The xbrlkit server is shared** by every subagent of one session: pass `filing` on every call
once more than one filing is loaded, and never unload a filing you did not load. It reads
RoboSystems' published parse of a filing when one exists (the load receipt says so); for the
number the brief turns on, also find it in the primary document with `search_text`.

> **⚠️ Always `load_filing` by ACCESSION, not by ticker.** The ticker shorthand
> (`UNFI 10-K`) resolves through an index that can lag a day or two behind EDGAR, so for a filing
> that landed this week it may silently return **last year's** annual report. Confirmed on UNFI
> 2026-09-15: `UNFI 10-K` loaded FY2025, not the FY2026 filed the day before. Get the accession
> from `search_filings` and load `cik:accession`, then **check `period_end` and `fiscal_year` in
> the load receipt before using a single number.**

Two things it does that the graph cannot:

- `fact_grid` reports an **`excluded`** list naming concepts the filer *did* tag whose facts your
  filter dropped. "The filer never reported it" stops looking identical to "my query missed it".
- `information_block` returns the **calculation arcs with a per-period footing check**, so a
  subtotal that does not foot gets flagged instead of being copied into the brief.

**Charged is not paid.** Income tax *expense* (`us-gaap:IncomeTaxExpenseBenefit`) is an accrual.
Income tax *paid* (`us-gaap:IncomeTaxesPaidNet`) is cash. For any filer under a punitive or
disputed tax regime these diverge by orders of magnitude. Write "charged" or "taxed" over an
expense figure and reserve "paid" for the cash figure, and if the two differ materially, say so
and explain where the gap went. "Paid or accrued" is not an acceptable hedge.

## Prior coverage: draft first, then check (if `sources/_prior_coverage.md` exists)

A card at `sources/_prior_coverage.md` means we have covered this company before. **Do not open it until the brief is drafted.** The new brief is not a sequel:

- **Write from the current filing only**, as if covering the company for the first time. Find the story this filing tells. Do not look for last time's angle, structure or headline, and never open `.history/` or the published prior brief.
- **Then open the card.** It holds three facts: when we last covered the company, the filing it was on, and the one claim we made.
- **Add one short "since we last covered this" passage** where it fits: what we said then, and what the new filing shows now. If the new brief contradicts the old claim, say so plainly.
- **If the draft turned out to be the same story as last time**, that is a finding, not a default: say in one line that the thesis held and why, and check that the filing has nothing newer to lead with.
- **Stamp the label.** Set `coverage_label` in `social/{TICKER}_publish.json` to a human label for this update (e.g. `"Q2 FY2026 update"`); on a video pick, also `metadata.coverage_label` in the script. The quarter key itself (e.g. `2026-Q2`) is derived automatically at publish.
- **If our own prior angle is still the story,** lead with what changed since that filing, not with the level again.

If the card is absent, this is **initiating coverage**.

## What You Produce

**Brief-only is the default (reboot, 2026-11-16).** Research ships as a written brief: the brief
(#1), the X post (#3) and the publish metadata (#6), validated with `just validate-brief` and
published with `just publish-brief`. Author the video script (#2) and the YouTube description (#4)
only when the task names this ticker as the week's video. When it does, produce the **4 core
outputs** in order (brief FIRST - it's the foundation everything else derives from) and the
**publish metadata** (#6). (The 9:16 short and the Q&A podcast are
retired - author no `short_script.json` and no `qa.json`.) Schema and slide mechanics: see `PRODUCTION_CONTRACT.md`.
Downstream the visuals render from your `script.json` via the animated **webdeck**
(`just webdeck-pipeline`), and thumbnails auto-generate from the brief (`just thumbnails`).
You author no slide HTML.

**The door is the SEC trial, and the bridge is the prompt (2026-11-16).** Promo codes are
retired: write no `[PROMO_CODE]` line anywhere. A research reader's next step is to ask the filing
the same question themselves, so every piece carries **the prompt**: one exact question, written
the way a reader would type it into Claude, ChatGPT or any MCP client connected to the SEC Shared
Repository, that reproduces the piece's most interesting number (e.g. *"What share of Trulieve's
2025 revenue went to income tax, and how does that compare with 2024?"*). It goes at the end of
the brief's Bottom Line, introduced as *Ask the filing yourself:*, and on the closing line of the
X post. The door itself, the 14-day free trial (`robosystems.ai/pricing`), is a link and goes
only where links belong: the X first comment and the YouTube description, never the brief or the
X post body. Every such link carries tracking so trials can be traced to research:
`https://robosystems.ai/pricing?utm_source={x|youtube}&utm_medium=research&utm_campaign={TICKER}`.
Never name a price.

## Surface rules - one analysis, framed three ways

Every name produces all the assets; they land on surfaces whose discovery mechanisms differ, and
a line tuned for one surface loses on the others. This is measured on our own analytics, not
assumed:

| Surface | How readers arrive | What wins there |
|---|---|---|
| **YouTube** | ~61% search, browse is negligible | The **searchable query**: Company + Ticker + quarter + the specific metric. Front-load what someone would actually type. |
| **X** | cashtag / topic feeds | The **contrarian curiosity line** plus an early ` $TICKER`. Small active cashtag communities out-reach marquee names 6-10x; crowded tickers land near the account median. |
| **/research** | direct link (a prospect we sent) + long-tail SERP | The **brief**. This is the asset a buyer actually reads, so it carries the analytical claim plainly. **The page `<title>` is the `youtube_title`** (since 2026-09-02, `reindex.py` `seo_fields`): it is reused there because a search-first title is what a SERP needs too. If the `youtube_title` does not name the ticker or company AND a period token (Q2 2026 / FY2026 / 10-K / 10-Q / Earnings), the page falls back to a composed "Company (TICK) YEAR Earnings: brief hook" title, which is weaker. Set `seo_title` in publish.json only to override deliberately. |

**Never reuse one string across two surfaces.** The `youtube_title` is a query, the X hook is a
curiosity line, and the brief's headline is the analytical claim. A single string copied
across all three reads as automated and underperforms on
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
     consensus and how it sits vs peers/sector (from the web pass, each attributed and dated).
     Compute market value from the filing's cover-page share count where sources disagree.
   - **Scenario DCF:** project free cash flow under **bull / base / bear** cases with explicit,
     stated assumptions (revenue growth, margins, WACC, terminal growth). Present a **range**, not
     a point estimate.
   - **Peer / cross-sector re-rating:** apply representative peer (or adjacent-sector) multiples
     to normalized earnings/EBITDA → implied value if it re-rated to the comp set.
   - **Output:** an implied-value **range** plus what today's price implies the market is pricing
     in. **Framing: implied value under stated assumptions - not a price target, not investment
     advice.**
   - **House defaults:** a 9% discount rate and 3% terminal growth unless the company's risk
     argues otherwise; state both, and say why when you move them, so briefs stay comparable.
   - **A signed deal changes the question.** When a definitive merger agreement exists (check A),
     value against the deal price: what the offer assumes about the quarter, not a DCF range.
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

**Footer (attribution only — NOT a door).** After the analysis, end with a one-line
attribution: the numbers came out of the filing itself, via RoboSystems. Keep it a footer,
separate from the analysis, and **do not close the brief with an offer or a promo code.**
The research page now carries the offer in its own shell, immediately below the brief
("Compare your company to {Company}" → roboledger.ai), so a second close inside the markdown
competes with it and dates the page: a promo code outlives the campaign that minted it, and a
price named here outlives the price. Say where the numbers came from and stop. (The prompt, *Ask the filing yourself:*, sits above
the footer as the last line of the Bottom Line; it is a question, not an offer.)

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
  **The brief carries this beat too**, as a short paragraph in its Bottom Line: the brief ships
  verbatim as the X Article, and a beat that lives only in the script never reaches it.
- **RoboSystems plug** - use ONE of these verbatim (don't rewrite), in a `title` slide
  (`visual_ref: "cta"`), never over a chart. Never speak a price - tiers change and the video
  does not. The two have different jobs and different doors:
  - the **mid-video attribution** says where the data came from. Its door is the SEC Shared
    Repository: name it in the narration, `robosystems.ai/pricing` in the slide subhead.
  - the **closing CTA** asks the viewer to do something: ask the filing themselves. Speak the
    piece's prompt, then the door: the 14-day free trial of the SEC Shared Repository,
    `robosystems.ai/pricing` in the slide subhead and the tracked link in the YouTube
    description. (Before 2026-11-16 the door was `roboinvestor.ai/research/{TICKER}`; the SEC
    repository became the lane's lead magnet on 11-11.)
  - *Mid-video attribution (best for shorter videos), after citing a specific data point:*
    > "All of the financial data in this analysis comes from the company's actual SEC filing,
    > pulled directly from the RoboSystems SEC Shared Repository. It is a subscription you can
    > point your own tools at, across every public company that files. Link in the description."
  - *Closing CTA (best for longer analyses), as the final or second-to-last slide:*
    > "Every number here came out of the filing itself, and you can ask it the same questions.
    > Connect the SEC repository to Claude or ChatGPT, it's a fourteen day free trial, and start
    > with this one: {the prompt}. The link is in the description."

### 3. X Post (`social/{TICKER}_x_post.txt`)
A **single post — NOT a numbered thread** (long-form is fine on X; no "1/ 2/ 3/"). Opening
hook; 3-5 key findings with specific numbers; a risk/caveat; closing takeaway; relevant `$TICKER` cashtag **and EXACTLY ONE cashtag total** (X rejects a post carrying two or more with HTTP 403: *"Posts are limited to a maximum of one cashtag ($SYMBOL)"* - verified 2026-07-30 when AEHR's short failed on ` $AEHR $SOXX`. The old guidance here asked for a sector/thematic ETF cashtag alongside the ticker for extra discovery reach; that is no longer possible. Keep the company's own ` $TICKER` and demote the ETF to a **hashtag** (`#SOXX`, `#JETS`, `#XBI`), which still carries a topical signal and is not rate-limited) and topic hashtags; tag @RoboFinSystems. **Cashtag placement & hygiene:** **lead with the cashtag** - ` $TICKER` goes on the FIRST line (front placement gets more topic-feed reach than burying them at the end, and the tag sits above the fold where the feed crops); the topic hashtags + @RoboFinSystems tag go on the closing line. Keep cashtags space-separated and **never glue a `$`-cashtag inside parens** like `($TICKER)`: X only linkifies AND indexes a cashtag when a space (or start-of-post/@) precedes it, so a leading paren silently kills both the link and the cashtag-feed discovery. For a parenthetical in prose, use the bare ticker `(TICKER)` without the `$`. **Never use `<` or `>`** in any social copy, YouTube description, or brief: YouTube and X parse them as HTML tags and reject the whole paste. Spell comparisons out: `under 1x`, `over $740M` (not `<1x` / `>$740M`).
**The prompt closes the post (2026-11-16):** the last line before the hashtags is *Ask the
filing yourself:* and the piece's prompt, with no link. The trial link goes in the first comment
(`x_first_comment`), tracked as above.
**No link and no promo in the body.** The X post carries **no `robosystems.ai` link and no
promo-code line** - both suppress reach (X throttles external links, and a discount CTA on every
post reads as spam and drags engagement). The trial link goes in `x_first_comment` (and the YouTube
description on a video pick), never the X post body. Every post leads with substantive text and the
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
`https://github.com/RoboFinSystems/robosystems-content-machine`; under the links, the trial line
`Ask the filing yourself, free for 14 days in Claude, ChatGPT or any MCP client:` followed by the
tracked pricing link (`utm_source=youtube`) and the piece's prompt; a voice-credit line
`Voiceover by ElevenLabs: https://try.elevenlabs.io/v9z3wzm97gk3` with a following
`Disclosure: the ElevenLabs link is a referral link.` note (the video narration is ElevenLabs);
**timestamps** — draft from
each segment's `duration_estimate_seconds` (start `0:00`, accumulate); after render, finalize from
the generated `videos/{TICKER}_timestamps.txt` (actual chapter times); 6-8
key-finding bullets with specific numbers; a 1-2 sentence plain-English explainer of any key
metric or term a cold viewer needs; disclaimer ("This is not investment advice. No price
targets."); relevant `$TICKER` and topic hashtags.

### 5. The 9:16 short (RETIRED 2026-09-26)
Author no short. Measured over 365 days, the Shorts feed brought 17% of the channel's views
but 0.5% of its watch time (27 minutes all year, about 3 seconds a view), 2 subscribers, and
no measurable traffic to the long-form, while each short spent the same YouTube upload quota
as a long-form video. The channel grows on search to the long-form. The short tooling
(`webdeck-short-*`) still runs for a one-off if one is ever wanted.

### 6. Publish metadata (`social/{TICKER}_publish.json`)
The per-platform native copy that lives nowhere else — you author it; `just postpack {TICKER}`
stitches it into a paste-ready **publish pack** after production (merging in the real chapter
times, the S3 media links, and flagging any unresolved placeholders). A JSON object of string fields:
- `company` - the company's legal name as filed (e.g. `"Workiva Inc."`). The /research page shows it; a brief-only project has no script to read it from, so without it the page shows the ticker.
- `coverage_label` - continuing coverage only (see "Prior coverage").
- `youtube_title` - **the /research page `<title>`**, and the video title on a video pick. **Search-first** (≤100 chars). YouTube discovery for this
  channel is almost entirely SEARCH (browse is dead), so front-load the query a viewer would
  actually type: Company + Ticker + the quarter/filing ("Q2 FY26 Earnings") + the specific
  angle/metric, then a short curiosity tail. Aim at the specific low-competition long-tail, not
  the crowded bare-ticker term. **Make it DIFFERENT from the X hook**: X rewards the contrarian
  curiosity line, YouTube rewards the searchable query; don't reuse the same string on both.
  **It is also the `/research` page `<title>`** (Google prints it with " | RoboSystems Research"
  appended and truncates around 60 characters, so the company/ticker + period must sit in the
  first ~55). Hard requirements, checked by `just validate`: the string names the **ticker or
  company** AND carries a **period token** (`Q1`..`Q4`, `FY2026`, `10-K`, `10-Q`, or `Earnings`).
  A topic-led title for a thin-demand name still satisfies this by closing with the ticker and
  period in parentheses: "Fastenal: A Double-Digit Comeback the Market Sold (FAST Q2 2026)".
  Without both, the page gets a composed fallback ("Company (TICK) 2026 Earnings: brief hook"),
  which is honest but weaker. Why: the old template title ("MGP Ingredients, Inc. (MGPI) SEC
  Filing Analysis") sat at position 10 for "mgp whiskey q2 sales" with 212 impressions and 0
  clicks (Search Console, 3 months to 2026-09-02).
- `seo_title` / `seo_description` (optional) — explicit overrides for the `/research` page
  `<title>` and meta description. Leave them out unless the `youtube_title` genuinely should
  differ from the page title; `reindex.py` composes both otherwise.
- `x_first_comment` — the X first comment; points to the brief published as an X **Article** (use `[X_ARTICLE_LINK]`), then one line with the trial: `Ask the filing yourself, free for 14 days:` and the tracked link (`utm_source=x`). The full long-form is uploaded as native video when there is one; no YouTube link on X.
- `youtube_comment` (optional) — the YouTube first comment, posted automatically at `yt-publish`. Omit it and the tool posts the default written-brief line pointing at the ticker's `/research` page (`[RESEARCH_URL]` resolves to it). Write one only when a bespoke line beats "here is the full written brief" - e.g. a question that invites replies.

_No LinkedIn for research - LinkedIn is the technical/blog lane, not a research channel. The 9:16 short is retired (#5) - no `short_*` social files. The Q&A podcast is retired - no `podcast_*` fields, no `qa.json`._

Same placeholder rules as the rest (`[YOUTUBE_LINK]`) — never hardcode the live URL. `[PROMO_CODE]` is retired (2026-11-16); write no promo line.

## Workflow

1. Read `TASK.md` (when there is one) and this file. 2. The web pass: `sources/_web_research.md`.
3. Learn the schema (`get-example-queries`) and resolve the company's element names. 4. Filing
research, 10-20+ queries: the statements across 3+ periods, segment breakdowns, derived metrics,
and the narrative pillar. 5. Checks A to D (and E on the deep tier). 6. Name the coverage frame
and choose the lead. 7. Write the brief, then the X post and `publish.json`. 8. Open
`sources/_prior_coverage.md` if it exists, and add the "since we last covered this" passage.
9. `just validate-brief {TICKER}` until it passes (`just validate {TICKER}` on a video pick).

## Important Rules

- Every number from MCP data or attributed web search - never fabricate.
- **Never use em-dashes (`—`) or en-dashes (`–`)** in any generated output - briefs, scripts,
  social copy, publish metadata, slide text, or narration. Use a spaced hyphen ` - ` for a clause
  break and a plain `-` for ranges (`$8.9-9.2B`, `FY2021-FY2025`). The brief ships verbatim as an
  X Article and the social copy posts as-is, so this is a hard formatting rule (see
  PRODUCTION_CONTRACT Universal rules).
- If a figure about the company is not in its filings, say so; never fill it from the web.
  Web figures are context about the market (price, consensus, peers), each attributed and dated.
- Narration must sound natural read aloud and follow the spoken-form TTS rules in the contract.
