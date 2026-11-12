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
canonicalUrl: 'https://robosystems.ai/blog/from-numbers-to-narratives'
---

On June 22, 2025, we pointed Claude at a batch of new filings in the RoboSystems SEC repository and asked one open question: survey them and tell us the most interesting thing you find. [Here's the chat](https://claude.ai/share/2028a608-cae4-4edc-820b-0a6f2935b275). Nobody asked about geography. One of the five findings it came back with was a line in NVIDIA's revenue note: Singapore, $9.0 billion in a single quarter, 20% of NVIDIA's revenue billed to a city-state of six million people. Claude's read was that it was "likely reflecting major cloud provider and manufacturing partnerships."

The number was right. The why was a guess.

Seventeen months later, that line is the subject of a Wall Street Journal column.

## Update: November 11, 2026

I wrote this post in March 2026. This week the Singapore line became news, so I went back through it against the filings. The observation held up. Several of the details didn't, and I've corrected them below.

**What happened.** The Wall Street Journal's Jonathan Weil published ["Nvidia's Disappearing Singapore Sales Deepen Mystery Around Megaspeed"](https://www.wsj.com/business/earnings/nvidias-disappearing-singapore-sales-deepen-mystery-around-megaspeed-7d483180) on November 11. Megaspeed International is the Singapore-based cloud company tied to the investigation NVIDIA's board announced on November 8. An NVIDIA spokesman told the Journal the company put Megaspeed on an internal block list in June 2025. The last quarter NVIDIA reported a Singapore line ended in July 2025. The next quarter it changed how it assigns revenue to countries, and Singapore was gone. The Journal says it isn't clear whether the two are related, and NVIDIA declined to say. I don't know either.

**The timeline.**

- **June 2025:** NVIDIA stops selling to Megaspeed, by its own later account.
- **June 22, 2025:** Claude surfaces Singapore at 20% of NVIDIA's quarterly revenue in an open-ended survey of new filings.
- **August 27, 2025:** NVIDIA's 10-Q for the quarter ended July 27 reports Singapore at $10.2 billion, 22% of revenue. It's the last time the line appears.
- **Quarter ended October 2025:** NVIDIA switches from customer billing location to customer headquarters and recasts prior periods.
- **February 25, 2026:** the FY2026 10-K is filed with no Singapore line.
- **March 20, 2026:** this post.
- **November 11, 2026:** the Journal asks NVIDIA to explain.

**What I got wrong in March.**

- The table put billing-location years next to a headquarters-location year. That made the United States and China trends look like something they weren't. Both bases are below, side by side.
- I tied the Singapore line to the Super Micro indictment of March 19, 2026. That indictment describes a Southeast Asian intermediary and names no Singapore entity. The co-founder it charges has pleaded not guilty and Super Micro isn't charged. It doesn't explain the Singapore line, and I shouldn't have written it as if it did.
- I wrote that Claude flagged Singapore as the standout anomaly. It was one of five findings, and Claude didn't call it an anomaly. It reported the number and offered a benign explanation.
- I wrote that Singapore has no semiconductor fabs. It has several.
- The sample search result further down described an Arm goodwill impairment that never happened. It's been replaced with real text from NVIDIA's 10-K.

## The $23.7 Billion Geography That Appeared and Vanished

Here is the Singapore line as NVIDIA originally reported it, by customer billing location:

| Billing location     | FY2023 | FY2024 | FY2025     | Quarter ended Jul 2025 |
| -------------------- | ------ | ------ | ---------- | ---------------------- |
| **United States**    | $8.3B  | $27.0B | $61.3B     | $23.5B                 |
| **Singapore**        | $2.3B  | $6.8B  | **$23.7B** | **$10.2B**             |
| **Taiwan**           | $7.0B  | $13.4B | $20.6B     | $8.5B                  |
| **China (incl. HK)** | $5.8B  | $10.3B | $17.1B     | $2.8B                  |
| **Other**            | $3.6B  | $3.4B  | $7.9B      | $1.8B                  |
| **Total**            | $27.0B | $60.9B | $130.5B    | $46.7B                 |
| Singapore share      | 8%     | 11%    | 18%        | 22%                    |

Singapore goes from 8% of revenue to 22% in under three years. NVIDIA explained it in a footnote each time. From the [FY2025 10-K](https://www.sec.gov/Archives/edgar/data/1045810/000104581025000023/): "Customers use Singapore to centralize invoicing while our products are almost always shipped elsewhere. Shipments to Singapore were less than 2% of fiscal year 2025 total revenue." The [10-Q for the July 2025 quarter](https://www.sec.gov/Archives/edgar/data/1045810/000104581025000209/) added: "Over 99% of controlled Data Center compute revenue billed to Singapore was for orders from U.S.-based customers for the second quarter and first half of fiscal year 2026."

Then the basis changed. From the [FY2026 10-K](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/): "In the third quarter of fiscal year 2026, we changed to revenue based upon the location of our customers' headquarters as we believe it provides a better representation of the geographic profile of our revenue. Prior period information has been recast to reflect this change."

The same business, recast by customer headquarters:

| Customer headquarters | FY2024 | FY2025  | FY2026      |
| --------------------- | ------ | ------- | ----------- |
| **United States**     | $31.5B | $77.5B  | **$149.6B** |
| **Taiwan**            | $14.9B | $23.6B  | **$42.3B**  |
| **China (incl. HK)**  | $12.3B | $25.0B  | **$19.7B**  |
| **Other**             | $2.1B  | $4.4B   | **$4.3B**   |
| **Total**             | $60.9B | $130.5B | $215.9B     |

Because NVIDIA recast periods it had already reported, you can put the two bases next to each other and see where the Singapore line went:

| Change from billing basis to headquarters basis | FY2024 | FY2025  | Quarter ended Jul 2025 |
| ----------------------------------------------- | ------ | ------- | ---------------------- |
| Singapore, as billed                            | $6.8B  | $23.7B  | $10.2B                 |
| United States                                   | +$4.6B | +$16.2B | +$9.4B                 |
| China (incl. HK)                                | +$2.0B | +$7.9B  | +$1.2B                 |
| Taiwan                                          | +$1.5B | +$3.0B  | +$0.4B                 |
| Other                                           | -$1.3B | -$3.5B  | -$0.9B                 |

These are net changes in each line between the two bases, so they aren't a dollar-for-dollar trace of Singapore invoices. "Other" moved too. But the shape is clear. Most of Singapore became the United States. And in FY2025, customers headquartered in China were $25.0 billion, 19% of NVIDIA's revenue. On the billing view they were 13%.

What the filings can't tell you is anything about a single customer. On the new basis, a direct customer headquartered in Singapore sits in "Other", a line of about $4.3 billion a year. NVIDIA doesn't say what's in it, and it hasn't said where Megaspeed's purchases were classified on either basis. Much of NVIDIA's hardware also reaches buyers inside servers built by other companies, which the geographic note doesn't follow.

The structured data had the signal in June 2025. A model with no prompt about geography pulled it out of a batch of filings. What it couldn't do then was read the footnote next to the number, and the footnote is where the story changed. In March I had the footnote available and still built a table across the change without reading it closely. That's the argument of this post, made at my own expense.

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
  "section_label": "Segment Information",
  "content": "In the third quarter of fiscal year 2026, we changed to revenue based upon the location of our customers' headquarters as we believe it provides a better representation of the geographic profile of our revenue. Prior period information has been recast to reflect this change.",
  "xbrl_elements": ["us-gaap:Revenues", "srt:StatementGeographicalAxis"],
  "source_type": "ixbrl_disclosure"
}
```

From here, an AI agent can take those element qnames and query the graph for actual numbers across periods, companies, or segments. The narrative provides the _why_; the graph provides the _what_ and _how much_.

## What AI Can Do With This

With MCP tools that span both layers, an AI agent can execute multi-step reasoning chains that were previously impossible. Take the NVIDIA geographic revenue example:

**"Why did NVIDIA's Singapore revenue disappear?"**

1. Query the graph: `us-gaap:Revenues` by `srt:StatementGeographicalAxis`. Singapore grows from $2.3B in FY2023 to $23.7B in FY2025, and the member stops appearing after the July 2025 quarter
2. Search disclosures for "geographic" or "billing location" across NVDA's filings
3. Find the segment note where NVIDIA says it moved from billing location to customer headquarters and recast prior periods
4. Pull the recast years and compare them with the originals, line by line
5. Synthesize: a change of basis, a recast, and a question the filing doesn't answer

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
- **AI semantic memory**: Agents store observations via `remember` and recall them later via `recall`—semantic search by meaning, not just keywords. "What did we learn about NVIDIA's supply chain?" finds the note you saved three sessions ago about TSMC capacity constraints, even if those exact words don't match.

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

NVIDIA's Singapore line was a $23.7 billion number hiding in plain sight. The number was in the graph. The reason it stopped being reported was in a footnote. Whether there's more to it than that is NVIDIA's question to answer.

Numbers tell you what happened. Narratives tell you why. Now your AI has both.
