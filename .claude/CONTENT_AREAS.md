# Content Areas - the catalog we pick from

**Date**: 2026-07-26 · Built by surveying the codebases directly. Read by `/atomize`.

## How this works

**The roster is the cadence.** One piece per area per channel per week. That is the whole scheduling model - diversity comes from the structure, not from remembering to vary. With ~10-12 areas across two personal channels it lands on the 1-2/day/channel volume target on its own.

The failure this exists to prevent: on 2026-07-26 a single `/atomize fpa` run produced 7 atoms, six of which were variations on "here's what's wrong with your spreadsheet." One rich spec section carried a whole week. Four were cut. Rotating areas makes that structurally impossible.

**Each area carries a `last_used` date.** Pick the stalest area with good hooks left. When analytics accumulate, this file becomes the unit of measurement - you will be able to see that close and mapping pull while serialization doesn't, which is impossible when everything is undifferentiated "product content."

## Rules that bind every atom drawn from here

- **Verify before publishing.** Each area lists grounding paths. Anything marked ⚠️ ASPIRATIONAL must never appear in a claim.
- **Internal docs are background, not source.** `local/RoboSystems/**` (specs, archive, parking lot) informs what is true; it is not quotable. It contains real graph IDs, incident detail, and customer specifics.
- **Consequence first, concept as punchline.** The hooks below are written concept-first for *your* comprehension. Invert them when writing.
- **Two registers, and one of them is always safe.**
  - **Problem-space** ("here is what breaks in normal systems, here is how I think about it") needs no public documentation. It is first-person, it is thought leadership, and a reader cannot fact-check a claim you did not make. This is the default register for Engine P.
  - **Product-claim** ("our system does X") requires a public source a reader could reach. Several genuinely shipped capabilities - FP&A, Metrics, the Block Explorer - have **zero public documentation**, so a product claim about them is unverifiable by anyone reading it. Write the problem-space cut instead, or publish public docs first.
  - The three atoms scheduled 2026-07-26 are all problem-space, which is why they survive flag 14 unharmed.

---

## AREA: Generic graph - one platform, many domains

**What it is**: the same graph engine that closes the books also runs completely unrelated domains. Define a schema in JSON, upload parquet, query it, point an AI at it.

**State**: **shipped and in production**, with a second company consuming it over HTTP as a versioned SDK. Exercised by `just demo-custom-graph`, unit-tested.

**last_used**: never

**Hooks**

1. **A hospital procurement catalog runs on the accounting platform, and the platform has no supply-chain code in it.** `RoboSCM` is explicitly listed as planned-but-unbuilt in `robosystems/schemas/README.md`, yet a Product / Manufacturer / Distributor graph runs in production on the same LadybugDB instances as XBRL facts. The generic graph is what makes a domain possible without an extension existing for it.
2. **One request field forks the entire product.** Send `custom_schema` and you get a generic graph; send `initial_entity` and you get an accounting entity graph. Same endpoint, same tiers, same billing, same MCP. The validator enforcing it is six lines.
3. **The AI surface auto-shrinks to the domain.** An accounting graph's MCP handshake talks about close playbooks and fact grids. A custom graph's says "Connected to a custom property graph. No financial schema extension is installed" and hands the agent exactly two tools. Generated from the resolved tool set, so it can never advertise a tool the graph doesn't have.
4. **Vector search came free with the domain switch.** Put `{"name": "embedding", "type": "FLOAT[384]"}` in a schema JSON, materialize with embeddings on, and semantic search works on a non-financial node type. A nurse types "something for vomit" and gets emesis basins. No platform change was required.
5. **A second company ships zero database infrastructure.** Its entire analytical layer is `robosystems-client` from PyPI plus two JSON files and one Dagster resource. Postgres holds only tenant bookkeeping. That is the platform-as-product proof.
6. **Domain-specific MCP layered on generic MCP.** Rather than handing agents Cypher, the vertical wraps the graph in `search-products` / `get-supplier-info` and ships its own npm MCP server. Stack: Claude → vertical MCP → vertical API → RoboSystems → LadybugDB. A worked example of building your vertical's agent surface on someone else's graph.
7. **The honest one: generic graphs rebuild destructively in place.** Entity graphs get blue-green (WIP database, atomic swap). Generic graphs delete and recreate under the same ID - an empty window of seconds to minutes. Found by dogfooding, worked around with replicas behind a round-robin load balancer, and the fix spec names the single missing passthrough. Still unbuilt. This is a *good* post: dated, specific, verifiable, and it buys credibility that feature copy cannot.

**Lands with**: technical/AI-native tail primarily; the "one platform" angle also reaches buyers evaluating lock-in.

**SupplyFlow positioning constraint**: Joey is CTO of SupplyFlow QC, so it is legitimately part of his profile - but it is **one focal point among many, never the subject**. Use it as evidence that the platform generalizes, not as a product being marketed.

⚠️ **ASPIRATIONAL - never claim**: per-tenant hospital graphs (`hospital_inventory.json` + `create_company_graph` exist but are called from nowhere); Oracle Health / GHX / EDI / Epic / SAP integrations; the upload sensor ships stopped by default.

**Grounding**: `robosystems/schemas/runtime/custom.py` (valid types, reserved names, validation) · `robosystems/models/api/graphs/core.py:262-268` (the entity-vs-generic fork) · `robosystems/middleware/mcp/tools/instructions.py:66-72` (the handshake) · `robosystems/schemas/README.md` (RoboSCM unbuilt) · `examples/custom_graph_demo/` (the runnable loop) · `robosystems/config/graph_tier.py` + `config/constants.py:33-34` (real limits)

---

<!-- AREAS FROM THE REMAINING SURVEYS APPEND BELOW -->
## AREA: MCP + the free-tool economics

**What it is**: `npx -y @robosystems/mcp` drops ~13 financial-graph tools into Claude Desktop / Code / Cursor, pointed at 274M nodes of public SEC data with a BYO key.

**State**: **shipped and live**. Verified against `api.robosystems.ai` during the survey.

**last_used**: never

**Hooks**

1. **274,777,192 nodes.** `get-graph-info` on the `sec` graph, verified live: 14 node labels, 22 relationship types, 8,458 entities and 71,697 reports in the recent graph alone.
2. **Every non-AI operation costs literally zero.** `CreditConfig.OPERATION_COSTS` has ~22 entries and every one is `Decimal("0")` - `mcp_call`, `query`, `cypher_query`, `database_write`, `backup`, `data_transfer_out`. The only pricing that exists is 3 credits per 1K input tokens and 15 per 1K output. You are billed for the model's thinking, never for touching your own data.
3. **Operators cannot forget to bill.** Every Bedrock call goes through a wrapper that consumes credits inline. There is no untracked path, because the tracked client *is* the only client.
4. **The embedding model is free by construction** - runs locally via fastembed, baked into the image, no external API call.
5. **The tool list is not in the client.** It is fetched from the API at startup and gated server-side on schema extensions, read-only status, and feature flags. Connect to SEC and you get analytical tools; connect to a tenant and `close-period` appears.
6. **The server writes the agent's own instructions**, generated from the resolved tool set, so guidance can never reference a tool the graph doesn't expose.
7. **A blocked tool returns a typed reason, not a 404** - stable codes like `repository_write_forbidden`, `extension_not_provisioned`.

**Lands with**: AI-native tail hardest; the credit-model hook also lands with buyers who have been burned by per-seat or per-query pricing.

⚠️ **ASPIRATIONAL - never claim**: `research` / `financial` / `rag` operators (only `cypher` and `mapping` are registered, despite the API docs); per-mode credit costs "quick 5-10, standard 15-25"; the MCP client README's tool table (lists 6 tools that don't exist server-side).

**Grounding**: `robosystems/config/credits.py` · `config/billing/ai.py` · `operations/operators/tracked_ai.py` · `middleware/mcp/tools/manager.py` · `middleware/mcp/tools/instructions.py` · `robosystems-mcp-client/index.js`

---

## AREA: Cross-filer fact grids - the XBRL tagging problem

**What it is**: map a plain-English concept to the XBRL tags companies actually use, then pivot facts across companies and periods regardless of which tag each filer chose.

**State**: **shipped and live**, verified.

**last_used**: never

**Hooks** - *this is the strongest demo asset in the entire catalog*

1. **Verified live: three companies, two different tags, 9.28 milliseconds.** `build-fact-grid` across NVDA / AAPL / MSFT resolved that NVIDIA tags revenue `us-gaap:Revenues` while Apple and Microsoft use `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax` - and reconciled them into one grid. That is the single most annoying problem in XBRL analysis, solved by one parameter.
2. **Real numbers it returned**: NVDA $26.9B (FY2022) → $215.9B (FY2026), an 8x run across four filings. AAPL $394.3B → $416.2B. MSFT $198.3B → $281.7B.
3. **Dimensional facts are filtered out by default** - consolidated totals only, so you cannot accidentally double-count segment breakdowns. The classic XBRL rookie error, prevented by default.
4. **`resolve-element` hands back the query, not just the answer.** Asking for "revenue" on NVDA returns the qname, 0.95 confidence, the filing's own label, fact_count 31, *and* a ready-to-paste Cypher string with params. The agent doesn't have to write the query.
5. **`financial-statement-analysis` finds the latest filing itself** from ticker plus form code, and dedupes facts that appear in multiple filings as comparative periods.

**Demo script** (30-60s, public data, all verified): ask for the three-company revenue comparison → say out loud "notice NVIDIA tags revenue differently than Apple, it handled that" → ask what element NVIDIA actually uses → ask for the latest 10-K balance sheet with no report ID.

**Lands with**: analysts, the AI-native tail, and anyone who has hand-reconciled a comp set.

**Grounding**: `middleware/mcp/tools/fact_grid_tool.py` · `resolve_element_tool.py` · `financial_statement_tools.py` · `adapters/sec/mcp/element_resolver.py`

---

## AREA: Semantic search over filings - narrative to numbers

**What it is**: hybrid keyword + vector search across 10-K/10-Q narratives, risk factors and disclosures, that bridges back to the structured facts.

**State**: **shipped and live**, on by default. Verified.

**last_used**: never

**Hooks**

1. **Verified live**: searching "tariff exposure supply chain risk" over risk-factor sections returned 10,000 matches, top hits Rocket Lab, Extreme Networks, Precision Optics - each with the actual paragraph. The surprise is that it surfaces *small caps nobody covers*, by meaning.
2. **The hybrid weights are explicit**: min-max normalize both score sets, then weighted mean at 0.4 keyword / 0.6 vector. Default is keyword-only because it is faster - hybrid is opt-in.
3. **Tenant isolation forced an architectural workaround worth telling.** The search engine could not filter hybrid queries at the top level, so filters are pushed inside each sub-query. Without that, vector search would rank across all tenants first and filter after, letting one tenant's documents push another's out of the top-K.
4. **Narrative connects to numbers.** Disclosure hits carry the XBRL tags in that section, so you go from "what management said" to "what they reported" in the same conversation.
5. **A performance war story sitting in a constant**: embedding threads pinned to 1, because letting the runtime auto-size its pool on CPU-limited containers oversubscribed the quota - 1,280ms per section versus 240ms, five times slower.

**Grounding**: `middleware/mcp/tools/search_tools.py` · `operations/search/client.py:408-512` · `operations/search/embeddings.py`

---

## AREA: The AI mapping operator - an AI that refuses to guess

**What it is**: bulk CoA-to-GAAP mapping that confidence-tiers its own output and hands back three piles instead of one answer.

**State**: **shipped**. One of exactly two registered operators.

**last_used**: never

**Hooks**

1. **Three piles, not a mapping**: auto-approve at 0.90+, map at 0.70+, otherwise flag for a human. The value is not the accounts it mapped - anyone can map the obvious ones. It is that it separated what it was sure about from what it wasn't, and said which.
2. **It knows where AI is wrong about accounting.** Deterministic regex overrides hard-code certain concepts like accumulated depreciation, because the account name is a stronger signal than the model's semantic match, which otherwise collapses the contra into its net parent.
3. **Bounded by credit balance, checked before each pass**, up to 6 passes, each re-fetching only still-unmapped elements and persisting as it goes - so a pass killed by a worker timeout just continues on the next one.
4. **It stops early when a pass maps nothing new** rather than burning the budget.
5. **The tool loop shows the model its own errors.** The design note is explicit: the old pipeline called fixed tools and the model never saw a query error, so it failed on basic questions. Now every tool error comes back as an error result it can react to.
6. **Tool results are capped at 12,000 characters** fed back to the model so a large result cannot blow the context or run up spend - while the full result set is captured separately for the UI to paginate.

**Grounding**: `operations/operators/implementations/mapping/operator.py` · `operations/operators/tool_loop.py` · `operations/operators/README.md`

---

## AREA: One kernel, three transports

**What it is**: an MCP tool call, a REST operation and a GraphQL resolver all invoke the same function - so an agent closing the books runs byte-identical logic to a human clicking the button.

**State**: **shipped** for tenant graphs.

**last_used**: never

**Hooks**

1. **The rule is written down as a rule**: never add business logic to an MCP tool file. Tools are transport shims - parse, call the ops function, translate domain errors, return. An information block created by an agent goes through the identical function as one created through the API.
2. **An agent can close a fiscal period over MCP** - same balance gates, same draft-entry validation, same idempotency as the UI. Not a parallel "AI path" with different rules.
3. **`list-period-drafts` surfaces the QuickBooks blast radius before you close** - per-draft, whether it will publish to QBO, so the agent can tell you exactly what closing will write to your accounting system.
4. **`get-close-playbook` is a tool whose only output is instructions.** No data, no side effects, version-locked to the build so it never drifts from the actual tools. It also tells the agent to go read the tenant's own close-procedures document for company-specific quirks.
5. **Naming discipline worth its own post**: "Operator" is the AI executor; "Agent" is the REA counterparty - customers, vendors, employees. Two different things, deliberately disambiguated.

**Grounding**: `middleware/mcp/README.md` · `middleware/mcp/tools/fiscal_calendar_tools.py` · `playbook_tools.py` · `schedule_tools.py`

---

## AREA: XBRL Holon - a filing as one portable file

**What it is**: `holon fetch --ticker NVDA` produces a single self-describing file that renders a complete financial report in any browser, with no backend.

**State**: **shipped and live**. CLI on PyPI, hosted viewer, both MIT.

**last_used**: never

**Hooks**

1. **Three commands is the whole product**: build from a filing, fetch by ticker, query an element. The query runs in-memory over a local file - no server, no API key.
2. **The AI in the viewer runs its queries client-side.** Claude answers questions about the loaded report by querying it in your own browser tab. Bring your own key, stored in localStorage, never sent to an app backend - because there isn't one.
3. **The lossless refactor is a good engineering story**: the old export was numeric-only, four statements, dimensions dropped. It now projects every numeric and text fact, concept, network and dimensional coordinate.
4. **Two modes, one static app**: drag-drop a file offline, or search any public company live with your own key.
5. It positions itself as the analog of Arelle's iXBRL viewer - a credible comparison for an XBRL-literate audience.

**Lands with**: the RDF / XBRL / semantic-web community (the Cagle + Hoffman adjacency), and developers.

**Grounding**: `robosystems-xbrl-holon/README.md` · `serialize/holon.py` · `robosystems-holon-viewer/README.md`

---

## ⚠️ AREA: AI memory - BUILT BUT DARK. Do not write "try it".

**What it is**: remember / recall / update / forget - durable semantically-searchable memory scoped to one graph.

**State**: **built, shipped, and gated OFF by default.** Both `SEMANTIC_MEMORY_ENABLED` and `MCP_SEMANTIC_MEMORY_ENABLED` default to `false`, and memory is hard-blocked on shared repositories by design. The live SEC session exposes no memory tools and never would.

**Correct framing if used at all**: "built, off by default, unavailable on public graphs." A demo requires a private tenant with both flags flipped. **Never** imply a reader can go try it.

**Hooks (design-story only, not product claims)**

1. `update-memory` exists specifically to preserve identity - its own description argues against forgetting and re-remembering, which would mint a new id and drop its history.
2. Recall predicates are built server-side from an allowlist; callers never pass raw filter strings. Anti-injection by construction.
3. Memory lives only on the writer, not in replica sync - a constraint most vector-memory demos never confront.
4. Memory and document search share one vector space, so a memory and a filing paragraph are comparable.

**Grounding**: `middleware/mcp/tools/semantic_memory_tools.py` · `operations/memory/service.py` · `config/env.py:592-608`

---
## AREA: Event-driven ledger - the GL is derived, not entered

**State**: shipped. **last_used**: never

1. **There is no `POST /events` endpoint and no journal-posting API.** QuickBooks, bank feeds, AI, and the UI all go through one validated write path.
2. **There is no `accounts` table.** A line item points at an Element - the same node type that holds US GAAP concepts. Mapping your CoA to GAAP is a typed row, not a subsystem.
3. **Built on REA**, McCarthy's 1982 accounting ontology, later ISO 15944-4. The graph edge is literally named `EVENT_TRIGGERS_TRANSACTION` - the McCarthy bridge.
4. **Three levels, not two**: Transaction (what happened) → Entry (the accounting interpretation, which must balance) → LineItem. Business event and accounting interpretation are separate first-class objects.
5. **`preview-event-block`** takes the identical body, writes nothing, returns the planned debits and credits plus `would_succeed`. An AI can show you the entry before it posts.
6. **Handler-not-found is a loud error**, never a silent capture. Unrecognized event types fail rather than storing garbage.
7. **Dedupe is a partial unique index on (source, external_id)** - supply one and adapter retries can never double-post. Omit it and you explicitly give up the guarantee.
8. Tenants add new debit/credit patterns **without code** via a template DSL. 19 fixed action verbs, aligned with Valueflows.

**Grounding**: wiki `Event-Driven-Ledger.md` · `robosystems/schemas/README.md`

---

## AREA: Close lifecycle

**State**: shipped, running on a production tenant across 23 months. **last_used**: never

1. **Two cursors, not one**: `closed_through` (actually locked) and `close_target` (what you are working toward). Setting a target closes nothing - intent separated from action.
2. **Blockers are a structured array, not an error string.** Six codes: `sequence_violation`, `period_incomplete`, `sync_stale`, `calendar_not_initialized`, `period_already_closed`, `pending_obligations` - some carrying detail like `sync_stale_days`.
3. **It refuses to close on stale accounting data** and tells you how many days stale. Override exists, is explicit, is logged, and is named `allow_stale_sync`.
4. **Strictly sequential.** Close March before February and you get a 422. The period must equal `closed_through + 1`.
5. **Posted entries are immutable.** Update and delete work on drafts only. To fix a posted entry you record a reversal - there is no edit path.
6. Closing runs the full rule engine inline: the response carries `rule_summary: {pass: 38, fail: 0}` alongside `entries_posted`.

**Grounding**: wiki `RoboLedger-Operations.md` (worked example + gotchas) · `RoboLedger-Demo-Walkthrough.md`

---

## AREA: Statement rendering - the roll-up engine

**State**: shipped. **last_used**: never

1. **Your chart of accounts maps only to leaves.** Subtotals are always derived and can never be a mapping target - because two sources of truth for one number can disagree.
2. **The corollary is a real diagnosable bug**: map an account to a subtotal and it lands on a dead branch and *silently never renders*.
3. **Retained earnings is recomputed on every render**, never posted as a closing entry. Which is why backdating is safe - there is no stored balance to go stale.
4. **One renderer, three sources.** The same algorithm renders SEC filings, materialized client graphs, and live ledgers. Dashboard, AI, and SDK provably agree because none of them do the math.
5. **Presentation is a four-segment code** (`BSC-CORP-IS02-CF1`). Change the code, the same facts re-render in a different shape, zero data changes.
6. **Banking and insurance are reporting styles, not separate frameworks** - the rule is explicit: framework = recognition changes; style = layout only.
7. The diagnostic rule of thumb, straight from the docs: *"if a number is wrong, the fix is almost never in the renderer."*

**Grounding**: wiki `Reporting-and-Rendering.md`

---

## AREA: Information Blocks - nothing crosses a boundary as a bare row

**State**: **shipped for read, PARTIAL for write.** Eight block types registered; only `schedule` and `rollforward` have create/update/delete. The five statements and `metric` return **HTTP 501**. **last_used**: never

1. The governing rule in one sentence: **"what crosses a system boundary is always a molecule, never a bare atom."**
2. **You author a Schedule; you render a Balance Sheet.** Calling create on a statement returns 501 deliberately - statements are assembled from facts, not authored.
3. **Amounts are integer cents everywhere.** `83333` is $833.33. Listed as the single most common integration mistake.
4. **Six views of one block, and only one is computed server-side** - the other five are projections of data the bundle already carries, so switching views is client-side with no round trip.
5. A block separates a permanent skeleton from per-period contents: one "Office Building Depreciation" structure accumulates a new fact set every month.

⚠️ **Do not claim you can author any block type.** Statements and metrics are 501.

**Grounding**: wiki `Information-Blocks.md` · `operations/information_block/README.md`

---

## AREA: Verification - rules as data

**State**: shipped with named gaps. **last_used**: never

1. **Six evaluating patterns** (EqualTo, RollUp, RollForward, SumEquals, Exists, CoExists). Anything else returns **`skipped`** - the engine never fakes a pass.
2. **Structural rules are auto-generated, not authored.** Users can only author arithmetic rules.
3. **Guard rails and verification are deliberately not the same thing**: guard rails answer "does this balance right now, at render time"; verification is a separate persisted audit outcome. Same equation, different question, different time.
4. **`verification_summary` is null until you run the rules, and the UI hides the panel rather than rendering zeros.** Absence of evidence displayed as absence, not as a pass.
5. **Expressions are parsed, never `eval()`'d** - rewritten, parsed to an AST, walked through a whitelist.

**Grounding**: `operations/information_block/README.md` · wiki `Reporting-and-Rendering.md`

---

## AREA: External proof - reconciling against a published reference

**State**: shipped, two runnable demos with committed output. **last_used**: never · **STRONGEST CREDIBILITY ASSET**

1. **22,288 general-ledger lines, 3,389 journal entries, a real 239-account chart of accounts** - Charlie Hoffman's "World Online" dataset.
2. **Trial balance: $17,217,503.20 debits, $17,217,503.20 credits.** Balanced to the cent, published in the repo.
3. **7 of 7 statement anchor totals tie exactly** to the published reference, $0.00 deltas across both periods.
4. **The most quotable design decision in the whole codebase: every reconciliation delta is classified by owner** - Matching, Methodology gap, **Our bug**, or Their data quality. And then: *"a report with mixed categories is more informative than an all-green one."* A vendor publishing its own bug list.
5. **An honest negative finding, published**: the cash flow renders operating only and is short ~$23K, and the docs walk through why - the source data tags debt repayments with an operating concept, so an indirect method mathematically cannot reconstruct financing.
6. Opening balances are ingested as **ordinary transactions**, not synthesized - 98 "beginning balance forward" lines flowing through the same path as everything else.

**Grounding**: `examples/seattle_method_world_online/README.md` + `sample_output/*.md` · `examples/seattle_method_demo/README.md`

---

## AREA: Serialization - one report, two formats, externally validated

**State**: shipped. **last_used**: never

1. **Neither encoder touches the database.** Both walk one in-memory bundle - which is *why* the two formats provably cannot drift apart.
2. **Externally checked, receipts committed to the repo**: validates in **Arelle**, the same processor SEC EDGAR uses, with **0 load errors, 0 validation errors**; the JSON-LD passes pySHACL with **0 violations across 3,204 triples**.
3. **Fail-loud publishing**: the artifact is uploaded inside the publish transaction. There is no such thing as a published report without a stored artifact.
4. **Every regeneration writes a new generation.** Old ones are never overwritten - an immutable history of every projection ever published.
5. **The JSON-LD deliberately kills XBRL's context indirection**: period, unit and entity attach directly to each fact. No `contextRef`.

**Grounding**: wiki `Serialization-and-Export.md` · `examples/seattle_method_world_online/sample_output/`

---

## AREA: Taxonomy as data - GAAP you can diff

**State**: shipped (`fac` + `rs-gaap` only). **last_used**: never

1. **"Adding a new accounting framework is a content change, not a code change."** Frameworks are JSON-LD packages a migration walks automatically.
2. **Everything is an Element** - your CoA lines, GAAP concepts, abstract headers, dimension axes. They differ by provenance and role, not structure.
3. **Library rows are immutable inside every tenant, enforced by database triggers.** You extend alongside; you can never edit in place.
4. **26 trait categories** carry per-element accounting meaning - 24 FASB metamodel axes plus cash-flow classification plus a recurrence axis.
5. **"One ledger, many filings"** as a frame: a public bank runs GAAP, call report, and tax simultaneously. Schedule M-1 exists *because* book and tax are deliberately different frameworks over one ledger.

⚠️ **Precision required**: "~2,000 concepts" describes the **public library** (~2,155). A **tenant graph receives ~143** curated concepts. Never conflate.
⚠️ IFRS / call report / tax / FERC / statutory are **directory-ready but unbuilt**.

**Grounding**: `frameworks/README.md` · wiki `Taxonomy-and-Frameworks.md`

---

## AREA: One database per company

**State**: shipped. **last_used**: never

1. Most accounting SaaS puts every client in one table filtered by customer ID. **Here each client is a physically separate database on a dedicated instance** - the wrong-client bug class designed out at the storage layer.
2. **The tenant ID lives in the URL path, never the request body**, and queries are rejected if you try to pass it as an argument. You cannot query the wrong client even deliberately.
3. **Tier names are the literal AWS instance you get.** No Professional/Enterprise/Premium - the docs say "do not use marketing names."
4. **Isolation was load-tested, not just reviewed**: 200 interleaved concurrent requests across two graphs in one org, zero bleed.
5. **The analytical graph is read-only over query.** You cannot write to a client's database with a query; data enters only through a staging pipeline.

**Grounding**: wiki `Graphs-and-Multi-Tenancy.md` · `Core-Concepts.md` · `SECURITY.md`

---

## AREA: Security posture - unusually blunt

**State**: controls shipped; compliance stacks off by default; **SOC 2 NOT attested**. **last_used**: never

1. The most quotable paragraph in the repo: **"a SOC 2 report attests to an organization operating a system over time - it is not a property of the source code."** And: *"you inherit the control design, you do not inherit operating evidence."*
2. **The admin surface is not reachable from the internet at all** - the load balancer 403s it. SSO or tunnel only.
3. **The query analyzer fails closed**: 44 write keywords detected after stripping comments and strings, and if analysis itself fails the query is treated as a write and blocked.
4. **The raw API key is returned exactly once, at creation.** The server can never show it again, only an 8-character prefix.
5. Blunt operational advice: *"turn the technical controls on before engaging a CPA firm, because the observation window only counts time the controls were actually running."*

⚠️ **Never imply SOC 2 attestation.**

**Grounding**: `SECURITY.md` · wiki `Security-and-Compliance.md`

---

## AREA: QuickBooks - the friction nobody documents

**State**: shipped with caveats (see flag 4). **last_used**: never

1. The tutorial's most valuable content is **the friction it admits**: connecting your own QuickBooks needs a one-time Intuit app assessment (~20-30 min plus review), a public EULA URL, and a privacy policy URL. Sandbox keys work instantly; production keys do not.
2. **The disambiguation nobody publishes**: connecting your own books needs production keys only. Listing on the QuickBooks App Store is a separate path with a ~20-day technical review that you do not need.
3. **The honest comparison table**: synthetic demo data is "clean, 100% mappable, balanced"; real QuickBooks is "real-world messy, partial mapping coverage, edge-case transaction types." A vendor stating its demo is easier than your books.
4. The close panel shows **which drafts publish to QuickBooks vs post locally** before you close - from the same function that does the actual write, so preview and reality cannot diverge.

**Grounding**: wiki `Connecting-QuickBooks-Locally.md` · `RoboLedger-Demo-Walkthrough.md`

---

## AREA: Open source and self-host

**State**: shipped. **last_used**: never

1. **Apache-2.0, the entire backend.** An accounting platform whose ledger logic you can read, fork, and audit line by line.
2. **No proprietary database anywhere** - PostgreSQL, LadybugDB, DuckDB, LanceDB, OpenSearch, Valkey. An explicit design goal.
3. **Zero AWS credentials stored in GitHub** - OIDC federation, 1-hour sessions, role restricted to specific branches and tags.
4. Custom adapters live in a **reserved namespace upstream never touches**, so a fork pulls updates without merge conflicts on its own integrations.
5. Minimum to run the whole platform locally: Docker, 8 GB RAM, 20 GB disk, one command.

**Grounding**: `README.md` · wiki `Bootstrap-Guide.md` · `LICENSE`

---

## AREA: The operation envelope

**State**: shipped. **last_used**: never

1. **Every write is a named business operation, not CRUD** - `close-period`, `file-report`, `promote-obligations`.
2. **Retry safety with teeth**: same key + same body within 24h replays the cached result; same key + *different* body returns **409**. The key is bound to the first body it ever saw.
3. **`idempotentReplay` is in every response** - a boolean telling you whether the command actually ran or was served from cache.
4. **A backup is either restorable or downloadable, never both.** Encrypted restores but cannot be downloaded; unencrypted downloads but cannot restore. Decide at creation.
5. **Feature flags gate at schema-construction time, not request time** - a disabled field does not exist in introspection at all.

**Grounding**: wiki `Graph-Operations.md` · `Extensions-Surface-Overview.md`

---

# ⛔ GLOBAL ACCURACY FLAGS - verify before any claim

| # | Do not publish | Why |
|---|---|---|
| 1 | `resolve-element` semantic/vector search ("~5ms over millions of elements") | README says yes, SEC adapter README says that tier was **retired**. Contradictory. |
| 2 | "~2,000 GAAP concepts" as a customer-facing number | That is the public library. A **tenant gets ~143**. |
| 3 | SEC relationship-type count | 22 vs 24 across two docs. |
| 4 | QuickBooks maturity | Pipeline guide says "In Development"; everything else implies live. |
| 5 | Metric blocks working | Code README says the evaluator is unimplemented (501); roadmap says shipped. |
| 6 | RoboSCM / RoboFO / RoboEPM / RoboHRM / RoboReport | README sections are stale; placeholder schemas were deleted. |
| 7 | "You can author any block type" | Statements + metrics return **501**. |
| 8 | **SOC 2 attestation** | Explicitly **not attested**. Control-design alignment only. |
| 9 | Multi-user organizations / teams | **Do not exist.** One org per user. |
| 10 | Storage billing | **Not live.** One dashboard figure is still a heuristic. |
| 11 | IFRS / tax / call-report / FERC frameworks | Directory-ready, **unbuilt**. |
| 12 | Neo4j backend | Experimental, disabled by default. |
| 13 | Production text search | Local complete; **prod infrastructure pending**. |
| 14 | **FP&A / scenarios / Metrics / Block Explorer** | Shipped internally, **zero public documentation**. A reader cannot verify any of it. Write about the *problem space* (safe) or publish public docs first. |
| 15 | Anything sourced from `local/` | Internal: pricing analyses, roadmap, security reviews, customer names. Never a public source. |
| 16 | AI memory as available | Built but **gated off by default**, blocked on public graphs. |
| 17 | `research` / `financial` / `rag` operators | **Do not exist.** Only `cypher` + `mapping`. |

---

## AREA: Demo-able surfaces - what to actually film

**State**: all shipped, verified by route + real content component (not README claims). **last_used**: never

**Ranked film list, effort to impact:**

1. **Holon Viewer, File Mode** (~30s, zero auth) - drag one `.jsonld` onto a page, a complete financial report renders offline. No backend, no key, no signup. A sample file ships in the repo. **The single highest-leverage top-of-funnel asset in the portfolio - film this first.**
2. **Inbox → "Preview - what would post" → Approve** (~45s) - click an event, see the **matched handler name**, the **planned debit/credit rows**, and `would_succeed: false` with the reason if it wouldn't post. Approve is one click. The strongest controller hook anywhere in the product.
3. **Close blockers in plain English** (~60s) - the messages are written for humans, verbatim in the code: *"QuickBooks hasn't synced through this period - run a sync before closing (or use 'Close with stale sync')."* Plus the unbalanced-draft gate, and **reopen requires a written reason** (placeholder: *"e.g., Missed expense reimbursement from Vendor X"*). Audit trail as a required field.
4. **Plan grid** (~45s) - income statement, balance sheet and cash flow stacked in one monthly grid running straight across the actuals/forecast seam, with the scenario's assumptions rendered underneath. Flip the scenario dropdown and only the forward columns change. `?scenario=` is in the URL, so you can send a CFO the exact view.
5. **Block Explorer six-view cycle** (~60s) - Rendered → Chart → Facts → Elements → Validation → Rules on one object. Validation groups Pass/Fail/Error/**Skipped** with failures sorted to the top. Then compute a metric live and watch the series gain a column, with skips carrying their reason.
6. **Chart of Accounts auto-map** (~30s) - coverage bar at 46%, click Auto-map, bar jumps past 90%. Candidate suggestions exclude subtotals so the dropdown only offers concepts that will actually render.
7. **Console on the SEC graph** (~45s, no customer data) - *"Compare gross margin for NVIDIA, AMD, and Intel over the last three years"* → narrative streams → **expand the generated Cypher** → one-click re-run → Download CSV. The AI shows its work.
8. **FactInspector** (~20s) - click a subtotal and see **the calculation rule it foots, computed live in the browser**. Controller catnip.

**Also strong**: Live Statements (subtitle is literally *"no close required"*), Trial Balance account-vs-GAAP rollup toggle, AI Memory (read, edit, and **delete** what the AI remembers about your business - a rare trust artifact), encrypted backup + verify-first restore.

⚠️ **Do not film**: graph creation inside RoboLedger or RoboInvestor (both are redirect stubs), the SEC CIK setup (validation is hardcoded), anything Plaid/bank-feed (orphaned stub).

**Grounding**: `roboledger-app/src/app/(app)/ledger/inbox/EventBlockDetailModal.tsx` · `.../close/components/PeriodClosePanel.tsx` (BLOCKER_MESSAGES:56-65) · `.../plan/` · `.../explorer/` · `.../chart-of-accounts/content.tsx` · `robosystems-holon-viewer/src/modes/FileMode.tsx` · `robosystems-report-components/src/components/FactInspector.tsx`

---

## AREA: The consultancy angle (Harbinger FinLab) - Engine P's conversion lane

**What it is**: the positioning and offer that Engine P's education content is ultimately selling into.

**State**: **landing page only - there is no app.** Auth routes removed, NextAuth unused. The working backend is a contact form.

**last_used**: never

**The positioning, verbatim**

- Category: **Co-sourced AI Controllership**
- H1: **"Great books drive great decisions."**
- **"We sell outcomes, not hours."** · *"Pricing is transparent and aligned to the outcome - never billable hours."*
- Trust line: Powered by Claude · Apache-2.0 platform · Human-in-the-loop · Open and yours

**The ladder**: 01 Teardown (diagnostic of your current close) → 02 Pilot (we run one real close) → 03 Managed (ongoing on an outcome-based retainer) → 04 Build (custom adapters, frameworks, deployment).

**Three tracks**: Companies (start here) · Accounting firms and fractional CFOs (scale - white-labeled, your clients stay yours) · Funds (enterprise - LP-ready packs deployed in your VPC).

**The five principles - the best raw material for Engine P atoms in the whole catalog:**

1. **No black box** - "the platform is open source. Read the code."
2. **No lock-in** - "take it in-house and self-host whenever you like. You will never be stranded by a vendor shutting down."
3. **No overpromise** - "AI generates, humans approve. We sell a reviewed, signed-off close, not an autonomous accountant that quietly breaks on the hard cases."
4. **Your infra or ours**
5. **Advice first, software second** - **"If targeted tooling solves it, we won't sell you a platform. We're accountants who deploy AI to fit the problem, and we'll tell you what you don't need."**

Framing: *"Most AI-accounting firms sell a black box and promise autonomy they can't deliver. We do the opposite - because when it's your books, trust is the product."*

**Two service descriptions map 1:1 onto footage** - film the surface, caption with the copy:
- *"Every transaction lands in an inbox pre-classified, with the exact entries shown before anything posts, so approval is a real decision rather than a rubber stamp"* → that is the **Inbox preview** clip, verbatim.
- *"Monthly statements and your scenario's assumptions in one grid, so the forecast is driven by the ledger you just closed, not a spreadsheet copied out of it"* → that is the **Plan grid** clip, verbatim.

⚠️ **UNRESOLVED COPY CONFLICT - fix before writing any teardown offer.** The ladder and the Companies card say **fixed-fee** teardown; the hero modal and closing CTA say **free**. Pick one.

⚠️ **NEVER claim multi-entity consolidation, consolidated statements, or eliminations.** Explicitly not built; `parent_entity_id` is a placeholder and bundling asserts a single entity. A commit on 2026-07-24 deliberately removed consolidation claims. Safe phrasing: **"side-by-side per-entity comparison."**

**Grounding**: `harbinger-finlab-app/src/app/(landing)/content.tsx` (claim-discipline note at :23-29, ladder :162-183, audiences :36-84, principles :134-160)

---

# ⛔ ADDITIONAL FLAGS - frontend surfaces

| Do not publish | Reality |
|---|---|
| **Multi-entity consolidation / eliminations** | Explicitly not built. Say "side-by-side per-entity comparison." |
| "Agents = AI agent management with conversation history" | README is **wrong**. `/agents` is a counterparty browser: customers, vendors, employees. |
| "Mapping Workbench" as a named surface | No such route. The capability is real but lives **inside Chart of Accounts**. |
| Report "templates" | Do not exist. They are **period presets**. |
| SEC CIK validation | **Faked** - hardcoded `{valid: true, company_name: 'Company Name'}`. |
| Bank feeds / Plaid | Orphaned stub, nothing links to it. |
| Asset allocation, risk analytics, dividend tracking, TWR/IRR | RoboInvestor **roadmap**, not built. |
| Real-time portfolio market values | `current_value_dollars` is nullable. Cost basis is guaranteed; current value is not. |
| Self-serve graph creation | **Gated** - `max_graphs === 0` returns "requires approval." |
| RoboLedger landing screenshots as product shots | They are **hand-built HTML mockups**. The `screenshot?` field is never populated. |
| Harbinger having a product or app | It does not. Landing page plus a contact form. |
| report-components as a stable API | **Pre-1.0**, API may evolve between minors. |

**Standing opportunity**: the RoboLedger landing page has six finished, claim-disciplined marketing spotlights (Inbox, Close, Reporting/XBRL, Plan, Block Explorer, Console) whose screenshots are placeholders - and every one has a real working screen behind it. Capturing them is shovel-ready and the copy is already approved.
