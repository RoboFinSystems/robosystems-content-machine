---
title: 'From Numbers to Narratives: Bridging Structured Data and Document Search'
date: '2026-03-20'
author: 'Joey French'
excerpt: 'Financial analysis needs both the numbers and the story behind them. We built a platform that bridges structured XBRL facts in a knowledge graph with full-text search across SEC filing narratives—and lets AI chain both together.'
metaDescription: 'How RoboSystems bridges structured financial data in a knowledge graph with full-text document search across SEC filings, enabling AI to reason over both numbers and narratives.'
tags:
  ['document-search', 'architecture', 'opensearch', 'sec-filings', 'xbrl', 'ai']
keywords:
  [
    'financial document search',
    'SEC filing search',
    'knowledge graph document search',
    'XBRL text search',
    'structured unstructured data',
    'OpenSearch financial data',
    'iXBRL disclosure search',
    'AI financial analysis',
  ]
featured: true
canonicalUrl: 'https://robosystems.ai/blog/from-numbers-to-narratives'
---

Last June, we [queried NVIDIA's revenue by geography](https://claude.ai/share/2028a608-cae4-4edc-820b-0a6f2935b275) using the RoboSystems MCP prototype. We asked Claude to survey recent filings and flag the most interesting finding. Out of every metric across every company, it flagged NVIDIA's geographic revenue concentration as the standout anomaly: Singapore accounted for $9.0 billion in a single quarter — 20% of NVIDIA's revenue flowing through a city-state with no semiconductor fabs and no major hyperscaler headquarters. Something was fishy. Claude noted it "likely reflecting major cloud provider and manufacturing partnerships."

We were wrong about the why.

## The $23.7 Billion Geography That Appeared and Vanished

This week, with NVIDIA's FY2026 10-K now in the knowledge graph, we pulled the full annual picture. The trend is unmistakable:

| Geography            | FY2022 | FY2023 | FY2024 | FY2025     | FY2026      |
| -------------------- | ------ | ------ | ------ | ---------- | ----------- |
| **United States**    | $4.3B  | $8.3B  | $27.0B | $61.3B     | **$149.6B** |
| **Taiwan**           | $8.5B  | $7.0B  | $13.4B | $20.6B     | **$42.3B**  |
| **China (incl. HK)** | $7.1B  | $5.8B  | $10.3B | $17.1B     | **$19.7B**  |
| **Singapore**        | —      | $2.3B  | $6.8B  | **$23.7B** | —           |
| **Other**            | $6.9B  | $3.6B  | $2.1B  | $4.4B      | **$4.3B**   |

Singapore appears as a standalone geography in FY2023, rockets to $23.7 billion by FY2025, then vanishes entirely in FY2026. Meanwhile, US revenue explodes from 16% to 69% of total revenue over the same period.

On March 19, 2026, the rest of the story arrived — not in a filing, but in a [federal indictment](https://www.cnbc.com/2026/03/19/us-tech-execs-smuggled-nvidia-chips-to-china-prosecutors-say.html). Super Micro Computer's co-founder was charged with smuggling $2.5 billion in NVIDIA AI servers to China through Southeast Asian intermediaries. The servers were assembled in the US, shipped to Taiwan, routed through a Singapore-based entity, repackaged in unmarked boxes, and delivered to their true destination: China.

The structured data had the signal the entire time. Singapore's meteoric revenue rise and sudden disappearance was the breadcrumb trail. But you'd only connect the dots if you could read the narrative alongside the numbers — the methodology change disclosures, the risk factor updates about export controls, the footnotes about geographic revenue classification.

**This is the gap at the center of financial analysis: the numbers live in one system, and the story behind them lives in another.** Analysts toggle between XBRL fact tables and PDF filings. AI agents can query the graph or search documents, but never both in the same reasoning chain.

We decided to close that gap.

## Two Worlds, One Platform

RoboSystems started as a knowledge graph platform. Every SEC filing is parsed into structured XBRL facts—revenue, net income, total assets—stored as nodes and relationships in LadybugDB, queryable via Cypher. That's powerful for comparing numbers across companies and periods.

But filings contain far more than tagged numbers. They contain:

- **MD&A sections** where management explains what happened and why
- **Risk factors** that signal future threats (tariffs, regulation, supply chain)
- **Disclosure notes** that provide context for every material change
- **iXBRL markup** where structured tags are embedded directly in narrative text

This content is the connective tissue of financial analysis. Without it, you have data points without context.

Starting with v1.4.44, RoboSystems indexes all of it.

## How It Works

The platform now has two complementary data layers, unified by `graph_id`:

| Layer               | Engine     | Stores                                                                            | Query Method        |
| ------------------- | ---------- | --------------------------------------------------------------------------------- | ------------------- |
| **Knowledge Graph** | LadybugDB  | Structured XBRL facts (Revenue = $130B, Element: `us-gaap:Revenues`)              | Cypher queries      |
| **Document Index**  | OpenSearch | Filing narratives ("Revenue grew 23% YoY driven by data center demand for AI...") | BM25 keyword search |

**The bridge**: iXBRL element metadata. Every indexed document section carries the XBRL element qnames it contains (e.g., `[us-gaap:Revenues]`), enabling bidirectional navigation — from a number to the narrative that explains it, or from a disclosure to the structured facts it discusses.

AI chains both layers in a single reasoning flow: search narrative → find XBRL tags → query graph for actual numbers → build report.

### Three Source Types

We index SEC filings across three distinct content types, each optimized for different search patterns:

| Source Type            | Content                                              | Use Case                                           |
| ---------------------- | ---------------------------------------------------- | -------------------------------------------------- |
| **XBRL Text Blocks**   | Tagged narrative sections from XBRL filings          | Searching within structured disclosure areas       |
| **Narrative Sections** | MD&A, Risk Factors, Cybersecurity disclosures        | Broad thematic search across filing sections       |
| **iXBRL Disclosures**  | HTML disclosures with embedded XBRL element metadata | Bridging specific facts to their narrative context |

Each document is partitioned by `graph_id` for tenant isolation—the same security boundary that governs the knowledge graph.

### BM25 Keyword Search

We chose BM25 (via OpenSearch) over pure vector search for document retrieval, and the reasoning is practical:

**Financial text is precise.** When an analyst searches for "tariff risk" or "goodwill impairment," they mean exactly those words. BM25's term-frequency scoring handles this naturally. Vector search is better at fuzzy semantic matching ("things similar to revenue"), which we already handle in the knowledge graph layer via LanceDB embeddings on XBRL elements.

Each layer does what it's best at:

- **BM25 (OpenSearch)**: "Find every filing that discusses tariff exposure" → exact keyword matching across unstructured text
- **Vector search (LanceDB)**: "What XBRL element maps to revenue?" → semantic similarity across structured taxonomy elements
- **Graph queries (LadybugDB)**: "What was NVIDIA's revenue for Q4 2025?" → exact fact retrieval with dimensional context

## The Bridge: iXBRL Element Metadata

The real unlock isn't having both layers—it's connecting them.

When our iXBRL parser processes a filing, it doesn't just extract text. It resolves continuation chains (where disclosures span multiple HTML elements), identifies every XBRL element referenced within the narrative, and stores those element qnames as metadata on the indexed section.

This means a search result doesn't just return text. It returns text _annotated with the structured concepts it discusses_:

```json
{
  "section_label": "Goodwill and Intangible Assets",
  "content": "During Q3 2023, the Company recognized a goodwill impairment charge of $8.7B related to the Arm acquisition...",
  "xbrl_elements": [
    "us-gaap:Goodwill",
    "us-gaap:GoodwillImpairmentLoss",
    "us-gaap:BusinessAcquisitionNameOfAcquiredEntity"
  ],
  "source_type": "ixbrl_disclosure"
}
```

From here, an AI agent can take those element qnames and query the graph for actual numbers across periods, companies, or segments. The narrative provides the _why_; the graph provides the _what_ and _how much_.

## What AI Can Do With This

With MCP tools that span both layers, an AI agent can execute multi-step reasoning chains that were previously impossible. Take the NVIDIA geographic revenue example:

**"Why did NVIDIA's Singapore revenue disappear?"**

1. Query the graph: `us-gaap:Revenues` by `srt:StatementGeographicalAxis` — Singapore grows from $0 to $23.7B then vanishes
2. Search disclosures for "geographic" or "revenue methodology" across NVDA's filings
3. Find the MD&A section where NVIDIA explains the change in geographic classification
4. Cross-reference with risk factor disclosures mentioning "export controls" or "China"
5. Synthesize: methodology change + export control risk + geographic reclassification = a story the numbers alone couldn't tell

**"Which companies have the most export control exposure?"**

1. BM25 search for "export control" across all filings
2. Extract the `xbrl_elements` from matching disclosure sections
3. Pivot to the graph to pull actual revenue by geography for those entities
4. Rank by concentration in restricted geographies

**"Search 'tariff' across all filings, then show me actual revenue for those companies"**

1. Search across all indexed filings for "tariff"
2. Extract the `xbrl_elements` from matching sections
3. Pivot to the graph to pull revenue facts for those entities
4. Compare pre- and post-tariff periods

This is the kind of analysis that takes a human analyst hours of toggling between EDGAR, Excel, and filing PDFs. An AI agent with access to both layers can do it in seconds.

## Beyond SEC: The Document Platform

SEC filings proved the architecture. But the same pattern applies to any domain where structured data and unstructured content need to coexist:

- **Your own documents**: Upload markdown—board memos, research notes, due diligence reports—and search them alongside your graph data
- **Connected sources**: Sync Google Drive or Notion content into the same searchable index, partitioned by the same `graph_id`
- **AI semantic memory**: Agents store observations via `remember-text` and recall them later via `recall-text`—semantic search by meaning, not just keywords. "What did we learn about NVIDIA's supply chain?" finds the note you saved three sessions ago about TSMC capacity constraints, even if those exact words don't match.

This isn't keyword search bolted onto a database. It's three search modes working together—BM25 for exact terms, kNN for semantic similarity, and Cypher for structured traversal—unified under one `graph_id` and accessible through the same MCP tools.

We chose Markdown as the canonical format for unstructured content (just as Parquet is the canonical format for structured tabular data). Headings provide natural section boundaries. Every LLM speaks it natively. Conversion from PDF, DOCX, or Google Docs is straightforward.

The document search platform spec is finalized. SEC search is live today. User documents and third-party connections are next.

## The Three-Layer Architecture

What started as a knowledge graph platform is now a three-layer financial intelligence platform:

| Layer          | Engine     | What It Stores                                      | How AI Uses It                                  |
| -------------- | ---------- | --------------------------------------------------- | ----------------------------------------------- |
| **Structured** | LadybugDB  | XBRL facts, transactions, relationships             | Cypher queries for exact data retrieval         |
| **Documents**  | OpenSearch | Filing narratives, uploaded docs, connected sources | BM25 keyword search for context and explanation |
| **Vectors**    | LanceDB    | Element embeddings, semantic memory                 | Similarity search for concept resolution        |

All three layers are partitioned by `graph_id`. All three are accessible via MCP tools. AI agents chain across all three in a single reasoning flow.

The knowledge graph is still the foundation—it's where the structured, queryable, comparable facts live. But it's no longer the whole story. The document layer provides context. The vector layer provides semantic understanding. Together, they give AI everything it needs to not just answer "what happened" but "why it happened" and "what it means."

## Try It

The SEC shared repository is live with document search enabled. Subscribe and your AI agents can immediately:

- Search "supply chain disruption" across every public company's filings
- Find the XBRL elements in those disclosures
- Query the graph for the actual financial impact
- Build a comparative analysis in minutes

NVIDIA's Singapore revenue was a $23.7 billion signal hiding in plain sight. The numbers were in the graph. The explanation was in the disclosures. The full story took both — and a federal indictment — to understand.

Numbers tell you what happened. Narratives tell you why. Now your AI has both.
