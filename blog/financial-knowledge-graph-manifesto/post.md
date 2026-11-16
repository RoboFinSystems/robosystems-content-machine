---
title: 'The Knowledge Graph Manifesto: Finance AI That Ties to the Books'
date: '2025-9-1'
author: 'Joey French'
excerpt: "Seven things I believe about putting AI on a company's books: why an export isn't enough, why the graph needs an ontology, why every number should open to its entries, why people approve what the AI drafts, and why you should keep the code."
metaDescription: 'A manifesto for finance AI that ties to the books: a knowledge graph with an ontology underneath, every number traced to its entries, the AI drafting and people approving, open source.'
tags: ['manifesto', 'knowledge-graphs', 'ontology', 'finance-ai', 'open-source']
keywords:
  [
    'knowledge graph finance',
    'financial knowledge graph',
    'finance AI',
    'ontology',
    'general ledger AI',
    'MCP',
    'open source accounting',
  ]
canonicalUrl: 'https://robosystems.ai/blog/financial-knowledge-graph-manifesto'
---

An invoice in your accounting system is a row. It has an amount, a date and a customer ID. What it doesn't have is everything that makes the amount mean something: the contract it bills against, the period it belongs to, the account it posts to, the line on the income statement that account rolls up to, and the payment that will settle it. The people who keep the books carry that in their heads. An AI reading the row has to guess.

I've spent my career making reported numbers trace back to their source, as a CPA and then as a knowledge engineer at Workiva. RoboSystems is what I think finance AI needs underneath it. This is the argument, in seven beliefs, and then what we built on them.

## Why isn't an export enough for finance AI?

An export keeps the numbers and drops the structure. When a trial balance lands in a spreadsheet, 48,900 is a cell: it no longer says that it's receivables, that it's a balance at month end and not activity during the month, which postings produced it, or what it has to foot to.

Hand that file to a model and ask why margins moved. It will answer, fluently, from the cells it can see. Whether the answer ties to the books is something you find out later, by hand. The model isn't the weak link. The input is.

## Why a knowledge graph?

Because in finance the relationships are the data. A sale is an event. The event produces an entry, the entry posts to accounts, each account maps to a reporting concept, the concepts roll up through a calculation to a statement line, and the period it lands in is open or closed.

In a table, those links live in joins that someone has to know to write. In a knowledge graph they're stored as relationships an agent can follow. That's the difference between asking an AI to remember how your books fit together and handing it the books with the fitting already done.

## Why does the graph need an ontology?

A graph without an agreed vocabulary is a pile of labelled boxes. The ontology is what says a receivable is a receivable in every company's graph, that a balance is measured at an instant while revenue covers a duration, and how one line rolls into another.

Ours is the RoboSystems graph model, labelled in XBRL's standard terms wherever XBRL has one. Every graph runs on it in LadybugDB, and reports leave as a holon (RDF), XBRL 2.1 or Tavi. Because public companies already file in those terms, your ledger and the XBRL filings of 8,000+ SEC filers sit in the same schema. Your gross margin and a public company's can be read side by side without a mapping spreadsheet in between.

## Why should every number open to its entries?

Because that's how finance already checks work. A reviewer doesn't trust a number on a workpaper; they tick it back to support. An agent's answer deserves the same treatment, and it can get it when every figure carries its path back: statement line to accounts, accounts to entries, entries to the event that caused them.

On the graph that path is a query, not a reconstruction. Every number opens to the entries behind it.

## Why should the AI draft and people approve?

The close is a judgment with a signature on it. An AI is good at the mechanical part: checking what's blocking the period, drafting entries from schedules, matching bank lines to open invoices. It shouldn't be the one deciding the books are right.

So the line I hold is simple. The AI drafts. Your people approve. In RoboLedger, a drafted entry waits for review, a period closes when a person closes it, and nothing writes to QuickBooks until you post an entry.

## Why open source?

Finance infrastructure outlives vendors. If the system holding your books disappears, gets acquired or reprices, you still have to close next month.

RoboSystems is open source (Apache 2.0 and MIT). Run it in your cloud, on your own server, or let us run it. You keep the code and the data whatever happens to any vendor, including us. It also means anyone can read exactly what the software does to a number, which for accounting software seems like the minimum.

## Why should it run where the books are allowed to live?

Plenty of finance teams can't send the ledger to someone else's AI. Client confidentiality, data residency, or a legal team that says no. That shouldn't mean no AI.

Point its AI at the model you choose: Claude, ChatGPT or any MCP client, or, when you host it yourself, an open-weight model on your own hardware. Your data trains no one's model. And each tenant's graph is a dedicated database on its own instance, not a slice of a shared table.

## What have we built on these beliefs?

Three kinds of graph on one platform: your ledger, the public filings, and graphs you model yourself, from your own schema, loaded from Parquet and queried with Cypher. Beside any of them, a subgraph gives your agent a workspace it can extend over MCP, and semantic memory carries its work from one session to the next.

RoboLedger is the general ledger built on it, a full accounting system in its own right: close, consolidation, schedules, bank feeds, reconciliations and forecasting, every number traced to the entry. Our own companies' books are kept on it, closed through September. When you see Driftline in a screenshot from us, that's a demo company.

I wrote the longer version of this argument, about what an agent needs from the ledger and where it should run, as [Finance AI that ties to the books](https://robosystems.ai/blog/finance-ai-that-ties-to-the-books). The platform itself is at [robosystems.ai](https://robosystems.ai).

## How do you test a finance AI against these beliefs?

Ask it three questions. They take a minute, and the answers tell you more than a demo will.

When the AI gives you a number about your books, can you open it to the entries behind it? If the answer is a percentage with no path back, someone on your team will rebuild the support by hand before it can be used.

Does the AI read your chart of accounts, your fiscal calendar and your close rules, or a CSV someone exported last Tuesday? An agent can't respect a closed period it doesn't know is closed.

If the vendor went away tomorrow, would you still have the system, the data and the history of what the AI did? If the honest answer is no, the risk sits with you, not with them.

We built RoboSystems so all three answers are yes. The code is public, so you don't have to take my word for it.

---

Built by an inactive CPA and ex-Workiva knowledge engineer.

**Book 20 minutes:** [robosystems.ai/book](https://robosystems.ai/book)

**Read the code:** [github.com/RoboFinSystems/robosystems](https://github.com/RoboFinSystems/robosystems)
