---
title: 'Knowledge Graphs and Ontology for Finance: Architecture and Use Cases'
date: '2026-1-12'
author: 'Joey French'
excerpt: "What a knowledge graph for finance is, why it needs an ontology underneath, the architecture that lets an AI agent trace every number to its entries, and what it's used for in financial services."
metaDescription: 'A knowledge graph for finance with an ontology underneath: what it is, the architecture that makes it work for AI agents, and its use cases in financial services.'
tags: ['knowledge-graphs', 'ontology', 'ai', 'xbrl', 'open-source']
keywords:
  [
    'knowledge graph finance',
    'financial knowledge graph',
    'knowledge graph architecture',
    'knowledge graph use cases financial services',
    'financial ontology',
    'ontology',
    'context graph',
    'open source knowledge graph',
    'XBRL',
    'MCP',
    'Cypher',
  ]
canonicalUrl: 'https://robosystems.ai/blog/building-financial-context-graphs'
---

Ask an AI about a company's financial position and it usually works from fragments: an export here, a PDF there, a few numbers pasted into a chat. It can retrieve. What it can't do from fragments is tell you where a number came from, or whether it ties to the books.

A knowledge graph with an ontology underneath is how we close that gap at RoboSystems. This post covers what one is, the architecture we run, how it compares with retrieval over documents, and what it's used for.

## What is a knowledge graph for finance?

A knowledge graph stores entities and the relationships between them as data. For finance, the entities are companies, accounts, entries, events, periods, reporting concepts and filings, and the relationships say things like "this entry posts to this account" and "this account rolls up to this statement line."

Some people search for this idea as a context graph. The substance is the same: relationships that carry meaning, so an agent can follow them instead of guessing at them. A table can hold the amount on an invoice. A graph holds the invoice, the customer, the entry it produced, the account that entry hit, and the period it belongs to, all connected.

## Why does a finance knowledge graph need an ontology?

The graph holds the links; the ontology says what the things are. Without one, "Revenue" in one company's graph and "Sales" in another are two unrelated labels, and a balance looks no different from a flow.

Ours is the RoboSystems graph model, labelled in XBRL's standard terms wherever XBRL has one. Every graph runs on it in LadybugDB, and reports leave as a holon (RDF), XBRL 2.1 or Tavi. In practice that means a receivable is a receivable in every graph, a balance at an instant is kept apart from activity over a duration, and the calculation that rolls lines into a total is stored with the facts. It's also why your ledger and the XBRL filings of 8,000+ SEC filers sit in the same schema.

We use the word precisely: the ontology is a shared model and vocabulary, written out as RDF when a report leaves.

## What does the architecture look like?

Five layers, from the storage up to what leaves the system.

**Storage.** Every graph runs in LadybugDB, an embedded columnar graph database, and each tenant gets a dedicated graph database on its own instance. Ledger writes land in a per-tenant PostgreSQL schema and are materialized into the graph for analysis, so transactional work and analytical work each run on an engine built for it.

**Three kinds of graph.** Your ledger, the public filings, and graphs you model yourself, from your own schema, loaded from Parquet and queried with Cypher. Ledger graphs are RoboLedger's books, mapped onto the ontology with their fiscal calendar and close rules. The public filings are a shared repository of 8,000+ SEC filers. Generic graphs are whatever you need beside them: units shipped, headcount, contracts.

**Workspaces and memory.** Beside any graph, a subgraph is a separate workspace where your AI adds node and relationship types and writes Cypher over MCP, without touching the books. Semantic memory lets an agent keep what was decided and recall it in the next session.

**Access.** MCP for agents, GraphQL for typed reads, Cypher for graph queries, and named operations for every write, each one logged. Claude, ChatGPT or any MCP client connects the same way.

**Output.** Statements are rendered from the ledger through the account mapping and checked as they're built. Reports leave as a holon (RDF), XBRL 2.1 or Tavi, so what you build isn't locked into our format.

## How is a knowledge graph different from retrieval over documents?

Retrieval hands a model passages of text. A knowledge graph hands it facts with their relationships, periods and sources attached.

Both matter, and we've measured where each helps. In our Filing Ladder benchmark on SEC filings, every representation that carried the filing's text, including the plain text read whole, landed within a few points of the others on accuracy. What the graph's tools changed was the cost per correct answer, which fell across versions while accuracy held, and a bare search tool over the text was cheaper still. The full results, including the findings that cut against us, are in [Same answers, cheaper](https://robosystems.ai/blog/filing-ladder-same-answers-cheaper).

So the case for a knowledge graph in finance isn't that it reads better than the text. It's that the answer comes back traced, to the tagged fact on a filing or to the entries in your ledger, where a reviewer can check it.

## What are the use cases in financial services?

Six of them, from the books outward.

**AI on your own books, traced.** An agent answers a variance question from the ledger, and every number opens to the entries behind it. A reviewer can tick the answer back to support instead of rebuilding it.

**Your numbers beside public companies'.** Add the SEC graph as a second connection, and your gross margin, R&D intensity or working capital sits next to a public filer's, in the same concepts.

**The month-end close.** An agent checks what's blocking the period, drafts entries from depreciation, amortization and prepaid schedules, and lines up reconciliations. The AI drafts. Your people approve. Nothing writes to QuickBooks until you post an entry.

**Consolidation.** Several entities kept as one group, each with its own books, chart and calendar, closed and consolidated rather than combined.

**Your own data beside the books.** Model operational data from your own schema, load it from Parquet, and query it with Cypher next to the ledger. Picture revenue per unit shipped, where revenue comes from the closed books and units come from your warehouse export.

**Research on public companies.** RoboInvestor runs on the same graph: equity research on public companies, your fund's positions with their terms, and the reports your portfolio companies share from RoboLedger.

## Where does it run?

Where your data is allowed to live. Use the managed platform, a Dedicated deployment, or host it yourself [on one server](https://robosystems.ai/docs/technical/self-hosting-on-a-server) or [in your own AWS account](https://robosystems.ai/docs/technical/bootstrap-guide).

Point its AI at the model you choose: Claude, ChatGPT or any MCP client, or, when you host it yourself, an open-weight model on your own hardware. Your data trains no one's model. RoboSystems is open source (Apache 2.0 and MIT): you keep the code and the data whatever happens to any vendor, including us.

## How do you start?

Pick the graph closest to your problem. The [documentation](https://robosystems.ai/docs) covers the platform, the SEC repository (with a 14-day trial) and custom schemas. RoboLedger connects to QuickBooks directly, and any other ledger comes in through the API or a file.

The argument for why an agent needs the ledger's structure, and not an export of it, is in [Finance AI that ties to the books](https://robosystems.ai/blog/finance-ai-that-ties-to-the-books). Our own companies' books are kept on RoboLedger, closed through September, so the architecture above is the one holding real books today.

---

Built by an inactive CPA and ex-Workiva knowledge engineer.

**Book 20 minutes:** [robosystems.ai/book](https://robosystems.ai/book)

**Read the code:** [github.com/RoboFinSystems/robosystems](https://github.com/RoboFinSystems/robosystems)
