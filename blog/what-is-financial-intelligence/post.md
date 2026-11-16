---
title: 'What Is Financial Intelligence? For AI, It Means Tying to the Books'
date: '2026-09-21'
author: 'Joey French'
site: 'robosystems'
excerpt: "Financial intelligence usually means a person's skill with financial statements, or a government unit that tracks money laundering. For AI working on a company's books, what matters is narrower and easier to test: every number opens to the entries behind it. Shown on a 3M filing anyone can check."
metaDescription: 'What is financial intelligence? The usual definitions, and what finance AI needs instead: a knowledge graph of the books and the filings, with every number traced to its entries.'
tags: ['finance AI', 'XBRL', 'SEC filings', 'MCP']
keywords:
  [
    'what is financial intelligence',
    'financial intelligence',
    'finance AI',
    'machine readable financial data',
    'XBRL AI',
    'AI SEC filings',
  ]
canonicalUrl: 'https://robosystems.ai/blog/what-is-financial-intelligence'
---

Search "financial intelligence" and you get two meanings. One is a skill: a person's ability to read financial statements and understand the context behind the numbers. The other is a government function: financial intelligence units, such as FinCEN in the United States, that collect and analyze reports of suspected money laundering.

Neither is quite what a finance team means when it asks for AI on its books. What it needs is narrower and easier to test: finance AI that ties to the books. Every number the AI gives you opens to the entries behind it, the AI drafts, and your people approve. This post explains why that takes more than a machine-readable file, using one public filing anyone can check.

## Why isn't machine-readable financial data enough?

Because the context gets lost between the file and the answer. Public companies have filed their statements in XBRL, a machine-readable format, since the SEC began phasing it in during 2009, and the data still isn't machine usable.

Take one report, 3M's 10-K for fiscal 2024. As a PDF it runs to 189 pages, and a frontier model can now read the whole thing inside a million-token context window. Almost nobody works that way, though. You don't re-read 189 pages for every question about every company, so the numbers get pulled out into a table, an API or a search index. That trip is where the context goes missing. Here are three ways it happened on this one filing.

**One number, reported twice.** The income statement shows research, development and related expenses of 1,085, in millions. The accounting policy note says the same expense "totaled $1.1 billion." Same element, same period, two facts, each marked with its precision. Neither is wrong, and XBRL's own guidance says to keep the more precise one. But a table with one row per company, concept and period has to drop one, and without a rule for choosing, row order decides.

**The statement line isn't in the SEC's own API.** That R&D line uses an element 3M defined for itself, because it includes related costs such as technical support and patents, and the SEC's XBRL APIs aggregate standard taxonomies. Ask the API for 3M's research and development expense and you get 700,000,000, the narrower standard concept. Ask for 3M's own element and you get a 404. You can check it in a browser at this address:

```
https://data.sec.gov/api/xbrl/companyconcept/CIK0000066740/us-gaap/ResearchAndDevelopmentExpense.json
```

The API is right about what it carries. What it doesn't include, or reconcile, is the broader line on the face of the income statement.

**A note that crosses a page break is a chain, and we dropped it.** This one is ours. 3M's Note 19 runs from page 83 to page 105 of the filing, and it's where the PFAS and Combat Arms Earplugs litigation is disclosed. In inline XBRL, a block that crosses a page break is stored as a chain of fragments, and our parser followed one link and stopped. Of the note's 130,272 characters, we kept 570. We caught it in September by asking our own tools questions we already knew the answers to, and fixed it that week (RoboSystems #1348). Every file had parsed without an error the whole time.

## What's the difference between machine readable and machine usable?

Machine readable means a parser can open it. Machine usable means the context survives the trip.

In all three cases above, the context was in the filing. The precision is on the fact. The element says whose vocabulary it's in. The continuation chain points to the rest of the note. It got lost on the way to the answer.

Your own books lose it the same way. The trial balance gets exported, and an export keeps the numbers and drops the rest. When 161,432 lands in a spreadsheet cell, what's gone is that it's receivables, that it's a balance on March 31 and not something that happened during March, which postings it came from, and what it has to foot to. A CSV is as machine readable as a file gets, and you can't run a company's books on it. I wrote that half of the argument up as [a chain of exports](https://roboledger.ai/blog/ai-native-accounting).

## What does finance AI need instead?

A system it can query, so the context an analyst carries in their head is written down where a model can reach it. In RoboSystems that system has three parts, each behind a defined tool.

**A knowledge graph, queried with Cypher.** Every fact stays attached to its element, its period, its precision, its entity and its place in a calculation. On the SEC graph, that's 3M's two R&D lines living as two different things. On your own graph, it's every account mapped to a reporting concept, so receivables is receivables and not a cell.

**A knowledge base, searched by keyword or by meaning.** On the SEC graph, the filing narratives, Note 19 included, all of it. On your own graph, your policies and your close procedures.

**Memory, recalled by meaning.** On your own graph: what was decided and why. How an account maps, how you treat a vendor, a note about last month's close. It's there at the start of the next conversation, and a person can edit it.

Underneath is one ontology: the RoboSystems graph model, labelled in XBRL's standard terms wherever XBRL has one. That's why your ledger and the XBRL filings of 8,000+ SEC filers sit in the same schema, and why every answer traces back to a query you can read, a passage you can open, or a memory you can edit.

Here it is working. Ask RoboSystems for 3M's research and development and two rows come back: 3M's own line at 1,085,000,000 and the standard concept at 700,000,000, each with its precision. The rounded 1,100 isn't there, because the more precise duplicate wins by rule. Those rules are written down in the [SEC filings guide](https://robosystems.ai/docs/guides/sec-filings), along with how to connect Claude, ChatGPT or any MCP client.

## What does that look like on your own books?

It looks like RoboLedger, the general ledger built on RoboSystems: a full accounting system in its own right, with close, consolidation, schedules, bank feeds, reconciliations and forecasting, every number traced to the entry. QuickBooks connects directly, any other ledger comes in through the API or a file, and nothing writes to QuickBooks until you post an entry.

You can ask about your books, and the AI reads the ledger, not an export of it. It renders the balance sheet, income statement and cash flow from the ledger through the mapping, checked as they're built. Add the SEC graph as a second connection and your gross margin sits beside a public company's, in the same concepts.

At month end, the AI checks what's blocking the close and drafts entries from your depreciation, amortization and prepaid schedules. Then it waits. The AI drafts. Your people approve. When a draft entry shows up, the schedule it came from is a query away, and so is the note from last month that explains the exception. Our own companies' books are kept on it, closed through September.

## Why did we build on SEC filings before the ledger?

Because they're public, structured and large, which makes them a fair place to find out whether the approach holds up, in a setting where anyone can check the work. The 3M example above is checkable by anyone with a browser.

The filings also do a second job. RoboInvestor runs on the same graph: equity research on public companies, your fund's positions with their terms, and the reports your portfolio companies share from RoboLedger. Its research briefs, more than seventy of them, are [in the open](https://roboinvestor.ai/research), each figure traceable to an SEC filing.

## So should you call it financial intelligence?

Call it whatever your team searches for. When we describe what we build, we say finance AI that ties to the books, on the open-source knowledge graph for finance. RoboSystems is open source (Apache 2.0 and MIT), runs on your infrastructure or ours, and works with the model you choose.

The test is the same whatever the label. When an AI hands you a number, can you open it to the entries behind it? I wrote the full argument as [Finance AI that ties to the books](https://robosystems.ai/blog/finance-ai-that-ties-to-the-books). The parser that dropped the note, and the fix that restored it, are both in the open.

---

Built by an inactive CPA and ex-Workiva knowledge engineer.

**Book 20 minutes:** [robosystems.ai/book](https://robosystems.ai/book)

**Read the code:** [github.com/RoboFinSystems/robosystems](https://github.com/RoboFinSystems/robosystems)
