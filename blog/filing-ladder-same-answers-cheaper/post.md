---
title: 'Same Answers, Cheaper: Four Versions of a Benchmark on One SEC Filing'
date: '2026-11-10'
author: 'Joey French'
site: 'robosystems'
excerpt: 'On one SEC filing, every representation that carries the text reads the same, and the facts without it score 15 to 53%. What the tools buy is cost: the hosted knowledge graph went from 9.1 to 5.4 cents per correct lookup across three versions while the plain text read whole went from 13.9 to 12.4, and accuracy did not move. The three findings that cut against us come first.'
metaDescription: 'A public benchmark on SEC filings, four versions in: tools match the document on accuracy and halve the cost per correct answer. The parts that cut against the author, first.'
tags: ['filing ladder', 'benchmark', 'knowledge graph', 'SEC filings', 'MCP', 'XBRL']
keywords: ['sec filing benchmark', 'knowledge graph financial data', 'cost per correct answer', 'xbrl ai benchmark', 'mcp tools financial analysis']
canonicalUrl: 'https://robosystems.ai/blog/filing-ladder-same-answers-cheaper'
youtube: 'jopPbAMS2co'
---

# Same answers, cheaper: four versions of a benchmark on one SEC filing

On one SEC filing, every representation that carries the document reads the same. The plain text in context, the whole document behind a search tool, the SEC filing's facts as a property graph with the document beside it, and the hosted knowledge graph's tools all land within a few points of one another on lookups, and all stall at the same place on derived questions. The facts without the text, in any structured form we built, score 15 to 53%. What the tools buy is cost. Across three versions of the benchmark the hosted graph's cost per correct lookup fell from 9.1 cents to 5.4, while the plain text read whole fell from 13.9 to 12.4. Accuracy didn't move.

That is the whole result. The rest of this post is the part a vendor usually leaves out, because a benchmark run by an interested author is only worth reading for the parts that cut against the author.

## What the ladder is

The Filing Ladder is a public benchmark: one SEC filing handed to one model in every representation we could build, the same 38 questions, the same judge, scored with cost. Twenty-six SEC filings, twenty lookup questions and eighteen derived ones, three runs each. The protocol is pre-registered and tagged before each run, every transcript and every judgment is published, and a published number is never re-run in place. Four versions have run since September. The first two were on one frontier model, the second two on its successor (Anthropic's Sonnet 5 and then Sonnet 5.5, named in the protocol as the lock they are). One row runs in every version with no tools at all: the plain text of the SEC filing read whole. It is the anchor. Whatever it moves between versions is the model. Whatever a tool row moves beyond that is the tools.

## Three things first

**A bare search tool over the plain text was cheaper still.** In the version that held the document constant across every tool, the cheapest row was the document's text behind one search tool and nothing else: 88% on lookups at 2.5 cents per correct answer. The knowledge graph's advantage is over the document in context and over the structured forms on their own, not over retrieval as such. On one SEC filing, retrieval is what did the work. We wrote that in September, and the two versions since haven't changed it. The controls say the same thing from the other side. With its search limited to the SEC filing's tagged text, the knowledge graph's own tools scored 48% on lookups; what carried it was the untagged text in its index. And any structured form with the document's text beside it landed in the same place: the SEC's own companyfacts API plus the document scored 90% at 3.1 cents, and a raw property graph plus the document scored 93% at 5.9 cents on the newer model. On one SEC filing, the text does the work, and the shape of the facts barely matters.

**Derived questions are unsolved, for every form, in every version.** Lookups land between 85 and 93%. Questions that need two numbers and an operation land between 54 and 63% for every form that carries the text, in every version, with 22 to 39% of all those answers given confidently and wrong. Nobody's form has moved that ceiling, ours included. Part of the ceiling is our own question set: the human review of the latest version found that three of the eighteen derived questions can't score for any row, because the answer key asks for something the SEC filing doesn't carry or doesn't say. On the fifteen that can, the same rows land between 73 and 76%. That still leaves one answer in four wrong, and the published scores stay as they are. When a vendor claims 90% on financial analysis, ask which tier the questions were.

**Our own harness handed our open-source row empty tool schemas through a published run.** We found it the day after publication, while testing a guard for the next version. Every tool the open-source package served had reached the model as a name, a description and an empty argument schema, because the capture read the wrong attribute and silently defaulted. No score changed, since the judge scores answers. The row's cost and error counts carried a handicap, the results README says so with the record scan, and the fix is one line plus a test that asserts the schema. A benchmark that can't say this out loud shouldn't be trusted on the rest.

## The numbers

Judge-scored, except the hosted graph's derived column, which the protocol's cross-filing rule marks down (more on that below). Cost is at the model vendor's list price, with the cache reads the run had.

| Row | Version | Model | Lookups | Derived | ¢ per correct lookup | ¢ per correct derived |
|---|---|---|---|---|---|---|
| Plain text in context (the anchor) | v0.1 | Sonnet 5 | 93% | 61% | 13.9 | 26.7 |
| Plain text in context (the anchor) | v0.2 | Sonnet 5.5 | 93% | 63% | 12.4 | 23.1 |
| Plain text behind a search tool | v0.1.1 | Sonnet 5 | 88% | 61% | 2.5 | 7.7 |
| Hosted knowledge graph, shaped tools | v0.1 | Sonnet 5 | 85% | 59% | 9.1 | 20.4 |
| Hosted knowledge graph, shaped tools | v0.2 | Sonnet 5.5 | 90% | 61% | 6.2 | 17.2 |
| Hosted knowledge graph, first step re-pointed | v0.2.1 | Sonnet 5.5 | 88% | 61% | 5.4 | 15.8 |
| Open-source package, shaped tools | v0.2 | Sonnet 5.5 | 90% | 63% | 6.1 | 15.9 |
| Open-source package, schemas handed over | v0.2.1 | Sonnet 5.5 | 92% | 63% | 7.6 | 15.7 |

In words, because the table is the easy part to skip: the anchor fell 11% per correct lookup across the model change. The hosted graph fell 41%. The difference is the tools and the prompt that drives them, not the model, read from one anchor row at three runs a question, so take it as a direction, not a measurement. Every paired change in accuracy between a row and the row before it sits inside one standard error. Same answers, cheaper.

## What the two cheapest fixes did

The last version added two rows, each its predecessor with one friction removed that the published transcripts showed. Both were pre-registered with expectations, and one expectation failed.

The hosted graph's prompt had carried a two-month-old first step telling the model to fetch Cypher example queries before anything else. In the run before, 46 of 114 records opened with a 6,718-character fetch that led to a Cypher query in 9. Pointing the first step at the tools the row actually has removed every fetch, cut tool calls by 13%, and brought cost per correct answer down on both tiers with no change in accuracy. That one worked as written.

The open-source package's row got its real tool schemas back. Refusals fell from 44 to 4. Turns per record didn't fall at all: the model spent the turns it no longer lost to refusals on reading more, and the schemas now ride along as tokens on every turn. The row got one more lookup right in sixty and 25% dearer per correct lookup. We had pre-registered that it would get cheaper. It didn't, and the results README scores that expectation as contradicted. The next friction on that row is an orientation payload of about 25,000 characters that the model reads first in two records out of three, which is a product finding, not a model one.

## What this does and doesn't say

It says that on one SEC filing a frontier model over MCP tools answers as well as the same model reading the document whole, at less than half the cost per correct lookup. It says the open-source package you can run on your own machine, with no account and no network, matches the hosted knowledge graph on accuracy for free, at about 1.4 times its cost per correct lookup, for a reason we can name.

It doesn't say the graph is more accurate than the document. No paired change clears the noise, and the plain-text search tool is cheaper than either. It doesn't say the graph's structure is what matched the document, either: the text in its index did. It doesn't say anything about derived questions, which nobody has solved. And it doesn't measure the thing a knowledge graph exists for: the corpus. Two derived questions in the set ask for a figure the named SEC filing doesn't carry. Every single-filing row abstained, correctly. The hosted graph went to the filer's earlier annual report, found the figure, and gave the right number, and the protocol scored that as wrong, by a rule we wrote before the run, because the question named one SEC filing. That is the one place in four versions where corpus access answered what no single document could, and it is unmeasured on purpose. Measuring it is the next tier, with questions that span SEC filings and the public record around them, and with search over every SEC filing's text as a row of its own. Indexing all the text is the obvious alternative to a knowledge graph, we run that index ourselves, and a corpus tier without it would answer the wrong question.

The hosted graph is the [SEC repository on RoboSystems](https://robosystems.ai/docs/guides/sec-filings), reachable from Claude, ChatGPT or any MCP client. The open-source package is [xbrlkit](https://github.com/RoboFinSystems/xbrlkit). The protocol, every transcript, every judgment and [the one table of every published row](https://github.com/HarbingerFinLab/filing-ladder/blob/main/results/README.md) are in the Filing Ladder repository, with the [v0.2.1 results](https://github.com/HarbingerFinLab/filing-ladder/blob/main/results/v0.2.1-sonnet-5-5/README.md) and the [disclosure](https://github.com/HarbingerFinLab/filing-ladder/blob/main/PROTOCOL.md#9-errata-and-amendments-after-the-freeze) beside them.

## Try it

xbrlkit is free, needs no account, and runs on your own machine. It serves one SEC filing at a time to Claude, ChatGPT, or any MCP client:

```bash
SEC_GOV_USER_AGENT="Your Name you@example.com" uvx --from "xbrlkit[mcp]@latest" xbrlkit serve
```

The corpus tier is next, and this blog is where it lands.
