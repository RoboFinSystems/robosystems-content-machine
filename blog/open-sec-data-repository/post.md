---
title: 'The Open SEC Data Repository: Every Filing as a Queryable Graph'
date: '2026-6-19'
author: 'Joey French'
excerpt: "Every public company's financials are already public—and almost nobody can actually use them. Here's the open, queryable graph we built on top of SEC XBRL, and what it unlocks."
metaDescription: 'The RoboSystems SEC repository turns every XBRL filing into a queryable financial graph—provenance to the source, open source, and self-hostable. Run your own analysis on any public company.'
tags: ['SEC data', 'XBRL', 'knowledge graph', 'open source', 'financial data']
keywords:
  [
    'SEC XBRL data',
    'queryable SEC filings',
    'open financial data',
    'SEC financial graph',
    'XBRL knowledge graph',
    'cannabis MSO financials',
  ]
canonicalUrl: 'https://robosystems.ai/blog/open-sec-data-repository'
---

# The Open SEC Data Repository: Every Filing as a Queryable Graph

The most valuable financial dataset in the world is already free. Every U.S. public company files with the SEC, and since the early 2010s those filings have carried XBRL—machine-readable tags on every reported number. Revenue, net income, segment breakdowns, the full balance sheet: all of it, structured at the source, for thousands of companies, going back years.

The promise of XBRL was that financial data would finally be _computable_. You wouldn't re-key numbers out of a PDF; you'd query them.

More than a decade later, that promise is mostly unkept. Doing real cross-company analysis still means one of two things: scraping hundred-thousand-row filings by hand, or paying a data vendor to do it for you and renting access to the result. The information is public. **Usable access to it isn't.**

We kept running into that wall—on our own research, and every time we wanted to show what the platform could do. So we built the piece we wished existed: an open, queryable graph of SEC financial data. We call it the **SEC shared repository**, and it's the same data layer that powers everything from our internal analysis to the company-coverage videos we publish.

## The data is public. Using it isn't.

Pull up a 10-K on EDGAR and the problem is obvious. The human-readable document is a hundred-plus pages of prose and tables. The XBRL underneath it is technically complete and practically inert—thousands of tagged facts wired together by linkbases most people have never heard of, in a format designed for machines but not for _your_ machine.

To answer a question as basic as "how has this company's effective tax rate moved over four years, and how does that compare to its peers?" you have to: locate each year's filing, parse the XBRL, reconcile concept names that drift between filers and periods, line up the dimensions, and only then do the arithmetic. Multiply that by a dozen companies and you've spent a week building a spreadsheet that's stale the moment the next 10-Q drops.

That friction is why financial data feels expensive even though it's free. The cost was never the data. It's the work of making the data _answerable_.

## What it is

The SEC shared repository takes that work off the table. Every XBRL filing is parsed into a graph:

- Each reported number becomes a **fact** node, tied to its **concept** (`us-gaap:Revenues`), the **period** it covers, the **entity** that reported it, and any **dimensions** (segment, geography, product line).
- The **calculation relationships**—how line items roll up into subtotals and subtotals into totals—are preserved as edges, not flattened away.
- The full filing narrative is indexed for **full-text search**, so the numbers and the words that explain them live in the same place.

And it's queryable two ways, depending on who's asking:

| Surface    | For                               | Example question                                                                  |
| ---------- | --------------------------------- | --------------------------------------------------------------------------------- |
| **Cypher** | Analysts who want graph traversal | "Compare `us-gaap:Revenues` across these 8 companies for the last 4 fiscal years" |
| **MCP**    | AI agents                         | "Pull NVIDIA's segment revenue and explain the year-over-year shift"              |

That last one matters more than it looks. Because the repository speaks MCP, an AI assistant can query SEC data _directly_—not summarize a stale article about a company, but pull the actual filed numbers and reason over them. That's the difference between an AI that sounds informed and one that is.

A query that would be a week of spreadsheet work looks, schematically, like this:

```cypher
MATCH (e:Entity)-[:REPORTED]->(f:Fact)-[:OF_CONCEPT]->(c:Concept {name: 'us-gaap:Revenues'})
MATCH (f)-[:FOR_PERIOD]->(p:Period)
WHERE e.ticker IN ['GTBIF', 'TCNNF', 'VRNO'] AND p.fiscal_year >= 2022
RETURN e.ticker, p.fiscal_year, f.value
ORDER BY e.ticker, p.fiscal_year
```

One question, every company, every year, straight from the filings.

## Why a graph, not a table

It would have been simpler to dump everything into a giant table. We didn't, because **XBRL isn't tabular—it's dimensional and hierarchical by design.**

A single revenue figure isn't just a number. It belongs to a concept, sits in a period, rolls up through a calculation tree, and may be cut by segment or geography. When you flatten a filing into rows, you throw away exactly the relationships that make the number mean something. You're left with values that have lost their context.

A graph keeps the context. You can:

- **Traverse across companies and periods**—follow one concept through every entity that reports it, instead of joining a dozen tables.
- **Walk the calculation tree**—see how a reported subtotal was actually built from its components, the way the filer wired it.
- **Bridge numbers and narrative**—jump from a fact to the language in the filing that explains it. (We wrote about that bridge in [From Numbers to Narratives](https://robosystems.ai/blog/from-numbers-to-narratives)—a graph for the _what_, full-text search for the _why_.)

The shape of the data should match the shape of the questions. Financial questions are relationship questions, so the store is a graph.

## Every number traces to its source

There's a quieter feature that, for anyone who's been burned by a black-box data feed, is the most important one: **provenance.**

Every fact in the repository points back to the exact value in the original XBRL filing it came from. Nothing is "adjusted," "normalized," or "estimated" out of view. If a number looks surprising, you can follow it all the way back to the as-filed source and see for yourself. There's no proprietary transformation in the middle that you have to take on faith.

That's the standard we hold ourselves to everywhere: a number you can't trace is a number you can't trust. With public filings as the substrate, every answer the repository gives is auditable down to the filing.

## What open data unlocks: coverage where there is none

The cleanest proof of why this matters isn't a benchmark—it's a market that the existing system ignores.

U.S. cannabis operators (the multi-state operators, or MSOs) generate **more than \$30B in combined annual revenue** and have essentially **zero Wall Street coverage.** Because cannabis is still federally Schedule I, these companies can't list on major exchanges, can't attract most institutional capital, and don't get sell-side analyst research. A multi-billion-dollar industry, operating in plain sight, with almost no one structuring its numbers.

But the numbers are right there—in the same 10-Ks every other public company files. Nobody had put them in a usable form. So we did.

Take Green Thumb Industries (GTBIF): a company doing over **\$1.2B in revenue**, GAAP-profitable, yet carrying an effective tax rate north of **50%**—not because it's mismanaged, but because IRS §280E denies cannabis businesses ordinary deductions. That single fact reframes the entire investment case, and it falls straight out of the filing once the data is structured. That's not a hot take. It's what the 10-K says, made legible.

We've been publishing exactly this kind of fact-based coverage, every number sourced to the filing, for companies the rest of the market has left dark. It's the same pattern over and over: **open, structured financial data democratizes coverage of under-served markets.** Cannabis today; tomorrow any corner of the market that's too small, too new, or too unglamorous for traditional coverage to bother with.

## Open, and yours

Two things about the repository matter as much as the data itself.

**It's open source.** The pipeline that turns raw filings into structured coverage—the same one we use to publish our research—is [public on GitHub](https://github.com/RoboFinSystems/robosystems-content-machine). We're not hiding the methodology. The data is public, the transformations are inspectable, and the analysis is reproducible. That's the only honest way to build a data source people are meant to trust.

**It's yours to run.** The repository can run in our cloud or in your own AWS account. Your queries, your data, no lock-in, no metered drip of someone else's API. The platform was built fork-friendly from day one, because financial infrastructure you don't control isn't really infrastructure—it's a dependency.

## Run your own queries

The fastest way to understand the SEC shared repository is to ask it something only you care about.

Head to **[robosystems.ai](https://robosystems.ai)** and run your own analysis on any public company—revenue trends, segment breakdowns, peer comparisons, the full balance sheet—all queryable, all sourced to the original XBRL filings. Use code **LAUNCH** for 50% off your first month. The pipeline behind our published coverage is [open source on GitHub](https://github.com/RoboFinSystems/robosystems-content-machine) if you'd rather start from the code.

The data was always public. Now it's finally usable.
