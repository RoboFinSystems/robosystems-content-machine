---
title: 'What Is Financial Intelligence? The Layer AI Needs Before It Touches a Number'
date: '2026-09-21'
author: 'Joey French'
site: 'robosystems'
excerpt: "Financial intelligence is the layer AI needs before it can work on a company's books: a knowledge graph, a knowledge base and memory, behind defined tools, with a person approving the work. We proved it on public filings at scale. RoboLedger is where it works on yours."
metaDescription: 'What is financial intelligence? The layer AI needs before it can work on the books: a knowledge graph, a knowledge base and memory, with a person in the loop.'
tags: ['financial intelligence', 'XBRL', 'SEC filings', 'MCP']
keywords:
  [
    'what is financial intelligence',
    'financial intelligence',
    'financial intelligence platform',
    'machine readable financial data',
    'XBRL AI',
    'AI SEC filings',
  ]
canonicalUrl: 'https://robosystems.ai/blog/what-is-financial-intelligence'
---

Public companies have filed their financial statements in a machine-readable format for fifteen years. The data still isn't machine usable, and the format was never the problem.

What's missing is a layer. I call it financial intelligence. It's what anything has to know before it touches a number: what the number measures, what period it covers, how precise it is, what the documents around it say, and what was already decided about it. People who do this work carry that in their heads. If an AI is going to work on a company's books, and not just talk about them, the layer has to be built: a knowledge graph for the numbers, a knowledge base for the documents, a memory for the decisions, and a small set of defined tools to reach each one.

I build RoboSystems, an open-source platform that is that layer. We proved it out on SEC filings, then put it to work. This is the first of eight lessons on what it's made of, and it starts with why a file isn't enough.

## Why we started with SEC filings

The SEC began phasing in XBRL requirements in 2009, starting with the largest companies. We load the recent filings into a graph: 77,228 annual and quarterly reports from 8,555 companies today, about 287 million nodes. It's public, it's structured and it's large, which makes it a good place to find out whether a layer holds up. It also means you can check what I say next.

Take one report, 3M's 10-K for fiscal 2024. As a PDF it's 189 pages and 513,102 tokens on Claude Sonnet 5's tokenizer, which fits inside a million-token context window. A frontier model can read every page, so the old objection, that machines can't read this data, is out of date.

Almost nobody works that way, though. You don't re-read 189 pages for every question about every company. The numbers get pulled out first, into a table, an API, a search index, and that trip is where the context goes missing. Three ways, on this one filing.

**One number, reported twice.** The income statement shows research, development and related expenses of 1,085, in millions. The accounting policy note says the same expense "totaled $1.1 billion." Same element, same period, two facts, each marked with its precision. Neither is wrong, and XBRL's own guidance says to keep the more precise one. But a table with one row per company, concept and period has to drop one, and without a rule for choosing, row order decides.

**The statement line isn't in the SEC's own API.** That R&D line uses an element 3M defined for itself, because it includes related costs like technical support and patents, and the SEC's XBRL APIs only aggregate standard taxonomies. Ask the API for 3M's research and development expense and you get 700,000,000, the narrower standard concept. Ask for 3M's own element and you get a 404. You can check it in a browser:

```
https://data.sec.gov/api/xbrl/companyconcept/CIK0000066740/us-gaap/ResearchAndDevelopmentExpense.json
```

The API is right about what it carries. What it doesn't include, or reconcile, is the broader line on the face of the income statement.

**A note that crosses a page break is a chain, and we dropped it.** This one is ours. 3M's Note 19 runs from page 83 to page 105 of the filing, and it's where the PFAS and Combat Arms Earplugs litigation is disclosed. In inline XBRL, a block that crosses a page break is stored as a chain of fragments, and our parser followed one link and stopped. Of the note's 130,272 characters, we kept 570. We caught it in early September by asking our own tools questions we already knew the answers to, and fixed it that week (RoboSystems #1348). Every file had parsed without an error the whole time.

## Readable and usable are two different jobs

In all three cases the context was in the filing. The precision is on the fact. The element says whose vocabulary it's in. The continuation chain points to the rest of the note. It got lost on the way to the answer.

Machine readable means a parser can open it. Machine usable means the context survives the trip.

Your own books lose it the same way. The trial balance gets exported, and an export keeps the numbers and drops the rest. When 161,432 lands in a spreadsheet cell, what's gone is that it's receivables, that it's a balance on March 31 and not something that happened during March, which postings it came from, and what it has to foot to. A CSV is as machine readable as a file gets, and you can't run a company's books on it. I wrote that half of the argument up as [a chain of exports](https://roboledger.ai/blog/ai-native-accounting).

## So what is financial intelligence?

Search the phrase and the first page agrees with itself. Intuit's definition is "the ability to analyze financial data and understand the context behind it." The reference entries and the best-known book on the subject say much the same: it's a skill a person learns.

I think that's right, and it's the bar a machine has to clear too. What changes is where the context lives. An analyst carries it in their head. A model starts every conversation with nothing. So for a machine the context has to be a system it can query. In RoboSystems that system has three parts, each with a defined tool, which is why the homepage says financial intelligence platform.

**A knowledge graph, queried with Cypher.** Every fact stays attached to its element, its period, its precision, its entity and its place in a calculation tree. On the SEC graph, that's 3M's two R&D lines living as two different things. On your own graph, it's every account mapped to a reporting concept, so receivables is receivables and not a cell.

**A knowledge base, searched by keyword or by meaning.** On the SEC graph, the filing narratives, Note 19 included, all of it. On your own graph, your policies and your close procedures.

**Memory, recalled by meaning.** On your own graph only: what was decided and why. How an account maps, how you treat a vendor, a note about last month's close. It's there at the start of the next conversation.

The list is short on purpose. Every answer traces back to a query you can read, a passage you can open, or a memory you can edit.

Here it is working. Ask RoboSystems for 3M's research and development today and two rows come back: 3M's own line at 1,085,000,000 and the standard concept at 700,000,000, each with its precision. The rounded 1,100 isn't there, because the more precise duplicate wins by rule. Those rules are written down in the [SEC filings guide](https://robosystems.ai/docs/guides/sec-filings), along with how to connect Claude, ChatGPT or any MCP client.

## The first work we gave it was research

A layer is only worth building if work gets done on it. The first work we gave ours was equity research. RoboInvestor publishes research on more than seventy public companies, as written briefs and videos, one company per report, with every figure traceable to an SEC filing. They're written through the same tools anyone can connect to, and they're [all in the open](https://roboinvestor.ai/research).

That's what the filings were for. They let us prove the layer at scale, in public, where anyone can check the work.

## Where the work gets done now: RoboLedger

The SEC graph is the side of the platform you can check. RoboLedger is the side that does the work: your own books on the same model, with the same three parts underneath and the same tools on top.

The books sync in from QuickBooks, which stays the source of record, and nothing is written back until you post an entry. Each account maps to a reporting concept, and the mapping is validated data instead of a workbook. From there the AI has something to work on.

You can ask about your books, and the AI reads the ledger, not an export of it. You can build reports: the balance sheet, income statement and cash flow, rolled up from the ledger through the mapping, checked as they're built, and shared as a statement without sharing the ledger. You can plan. A forecast is a scenario that projects all three statements forward from your last closed month, one month at a time, and every month has to balance. It's calculated, not generated, so the same assumptions always give the same numbers.

And you can compare your company with public ones. Add the SEC graph beside your books as a second connection, and your gross margin sits next to a public company's, in the same kind of concepts. The graph covers more than 8,000 of them. That's the second job the filings do.

When you trust it, it drafts the close. Depreciation, amortization and prepaids are schedules. At month end the AI checks what's blocking the close, drafts the entries from the schedules, and shows you every debit and credit and which ones will be written to QuickBooks. Then it waits. The period closes when you approve it.

A person stays in that loop on purpose, and the layer is what makes their job possible. When a draft entry shows up, the schedule it came from is a query away. So is the policy it follows, and so is the note from last month that explains the exception. Without the layer the AI is guessing and you're redoing the work to check it. With it you're approving work you can trace.

## What the series covers

The first half covers the data: why the substrate is a graph, why a number on its own means nothing, why a chart of accounts is a vocabulary. The second half covers running a ledger on it: why events come before balances, why you author a schedule and render a statement, and where the line sits between what a model may decide and what it may not.

One more number before lesson two. Loading that 3M PDF into a model costs about a dollar at list price, and with prompt caching each question after that costs cents. For one filing, that's a perfectly good answer. The trouble starts at the second filing, when the dollar gets paid again. That's why the numbers get pulled out in the first place, and it's where lesson two picks up.

An earlier take on this, from the tools side, is [AI Agents for Financial Analysis: Beyond ChatGPT](https://robosystems.ai/blog/ai-agents-financial-analysis). The platform itself is at [robosystems.ai/platform](https://robosystems.ai/platform).

The parser that dropped the note and the fix that restored it are both in the open: [github.com/RoboFinSystems/robosystems](https://github.com/RoboFinSystems/robosystems).
