---
title: 'The Future Data Stack for Finance AI: Why We Built RoboSystems'
date: '2026-1-12'
author: 'Joey French'
excerpt: 'A finance number that passes through a chain of tools before an AI reads it loses its lineage on the way. How RoboSystems is built instead: a ledger and a graph per tenant, one ontology, pipelines you can see, and a stack you can run yourself.'
metaDescription: 'How RoboSystems is built for finance AI that ties to the books: a per-tenant ledger and graph, one ontology, Dagster pipelines with lineage, MCP access, open source and self-hostable.'
tags: ['data-engineering', 'architecture', 'dagster', 'knowledge-graphs', 'open-source']
keywords:
  [
    'future data stack',
    'data stack for AI',
    'Dagster orchestration',
    'data lineage finance',
    'self-hosted data platform',
    'knowledge graph platform',
    'open source knowledge graph',
  ]
canonicalUrl: 'https://robosystems.ai/blog/the-future-data-stack'
---

Picture where a revenue number goes before an AI sees it. It starts in the ledger, gets pulled out by a sync tool, lands in a warehouse, is reshaped by transformation models, shows up in a BI dashboard, and is exported to a spreadsheet that someone pastes into a chat. Each hop is a vendor contract and a place to break. For finance, each hop also drops a little of what the number meant.

This post is for the people who would build or run the system: how RoboSystems is put together, and why we made the choices we did.

## Why does a long pipeline break finance AI?

Because lineage doesn't survive the trip. By the time a figure reaches the model, nobody can say which entries produced it, whether the period was closed, or which mapping put it on that line of the statement.

A data team can live with that for a dashboard. An agent drafting a journal entry or explaining a variance can't, because the person approving its work needs to tick the number back to support. Finance AI that ties to the books needs a stack where the path from statement line to entry is stored, not reconstructed after the fact.

## What did we build instead?

A short path that keeps the structure. For each tenant, ledger writes go through named operations into a dedicated PostgreSQL schema, then are materialized into a dedicated LadybugDB graph on its own instance. Transactional work gets a transactional database. Traversal and aggregation get a columnar graph engine. Both carry the same identifiers, so a number in the graph still opens to the entry that produced it.

Beside the tenant graphs sits a shared repository: the XBRL filings of 8,000+ SEC filers, loaded into the same schema as your ledger. An agent connects to both and reads them side by side.

That gives three kinds of graph on one platform: your ledger, the public filings, and graphs you model yourself, from your own schema, loaded from Parquet and queried with Cypher.

## Why one ontology under every graph?

So the same question works everywhere. The ontology is the RoboSystems graph model, labelled in XBRL's standard terms wherever XBRL has one. Every graph runs on it in LadybugDB, and reports leave as a holon (RDF), XBRL 2.1 or Tavi.

For a builder, that has two practical effects. The code that renders a balance sheet for your company renders one for a public filer, and the agent asks both the same questions. And because reports leave in open formats, what you build isn't trapped in ours.

## Why Dagster?

Because we wanted pipelines we could see. Dagster models the work as assets, such as filings fetched, data staged and a graph materialized, rather than scripts on a timer. Each run records what it produced, from which inputs, and what failed.

That's the same discipline the ledger asks for, applied to the plumbing. When someone asks where a fact in the SEC graph came from, the answer runs from the fact to the filing to the run that loaded it. In a production deployment Dagster runs the SEC filing pipeline, QuickBooks and bank-feed sync, graph backups, billing and routine cleanup, and every one of those runs is visible in its UI.

## How does an AI agent reach the data?

Through the same doors a developer uses. MCP for agents, GraphQL for typed reads, Cypher for graph queries, and named operations for every write. Every write is a named operation that accepts an idempotency key and is written to an audit log, whether a person, a script or an agent sent it.

That's also where the approval line lives. The AI drafts. Your people approve. Drafted entries wait for review, a period closes when a person closes it, and nothing writes to QuickBooks until you post an entry. Claude, ChatGPT or any MCP client connects the same way.

## Can you run it yourself?

Yes. RoboSystems is open source (Apache 2.0 and MIT). Run it on one server, in your own AWS account, or let us run it. The guides are [self-hosting on a server](https://robosystems.ai/docs/technical/self-hosting-on-a-server) and, for AWS, [the bootstrap guide](https://robosystems.ai/docs/technical/bootstrap-guide). In AWS, deployments authenticate through GitHub's OIDC federation, so no long-lived AWS keys sit in your CI.

When you host it yourself, you can point its AI at an open-weight model on your own hardware, as well as Claude, ChatGPT or any MCP client. Your data trains no one's model, and you keep the code and the data whatever happens to any vendor, including us.

## How do you extend it without fighting upstream?

It depends on what you're adding. For a new data source, the adapters directory reserves a custom namespace that upstream never writes to, so a fork pulls our updates without merge conflicts in your code.

For a new kind of data, you may not need code at all. Describe a graph in a schema file, load it from Parquet, and query it with Cypher. For example, a team could model contracts and their renewal dates beside the ledger and ask which renewals fall in a quarter where the books show a cash dip.

And an agent can extend a subgraph as it works. A subgraph is a separate workspace beside a graph, where the agent adds node and relationship types and writes Cypher over MCP, without touching the books themselves.

## Does it hold real books?

Ours. Our own companies' books are kept on RoboLedger, the general ledger built on RoboSystems, closed through September. RoboLedger is a full accounting system in its own right: close, consolidation, schedules, bank feeds, reconciliations and forecasting, every number traced to the entry. When you see Driftline in our screenshots, that's a demo company.

The platform and its documentation are at [robosystems.ai/docs](https://robosystems.ai/docs).

## What does the future data stack look like for finance?

Shorter, and with the meaning kept. I don't think the answer for finance AI is another tool in the chain. It's fewer hops, an ontology that travels with the data, lineage stored as relationships, and a deployment the company controls.

We're not claiming to have solved data engineering. We've made deliberate choices about the part of it finance AI depends on. The argument for why an agent needs the ledger's structure, and not an export of it, is in [Finance AI that ties to the books](https://robosystems.ai/blog/finance-ai-that-ties-to-the-books).

---

Built by an inactive CPA and ex-Workiva knowledge engineer.

**Book 20 minutes:** [robosystems.ai/book](https://robosystems.ai/book)

**Read the code:** [github.com/RoboFinSystems/robosystems](https://github.com/RoboFinSystems/robosystems)
