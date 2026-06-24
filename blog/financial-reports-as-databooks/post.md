---
title: 'Financial Reports as DataBooks: One Artifact for Humans, Machines, and LLMs'
date: '2026-6-19'
author: 'Joey French'
excerpt: 'A published financial report should be something you can read with your eyes, query with SPARQL, and validate with SHACL—without loading a single specialized tool. So we built a proof of concept: our reports, rendered as DataBooks.'
metaDescription: 'A proof of concept rendering published financial reports as DataBooks—human-readable Markdown plus addressable RDF/Turtle, with SHACL and XBRL validation evidence inlined. Queryable, verifiable, self-describing.'
tags: ['DataBook', 'semantic web', 'RDF', 'XBRL', 'JSON-LD', 'SHACL']
keywords:
  [
    'DataBook',
    'financial report RDF',
    'SPARQL financial data',
    'SHACL validation',
    'semantic financial reporting',
    'XBRL JSON-LD',
  ]
featured: true
canonicalUrl: 'https://robosystems.ai/blog/financial-reports-as-databooks'
---

# Financial Reports as DataBooks: One Artifact for Humans, Machines, and LLMs

A published financial report is usually a dead end.

It arrives as a PDF you can read but not compute, or as an XBRL instance you can compute but not read—and to do anything real with the XBRL, you load a validation stack and learn a toolchain most people will never touch. The information is all there. The _access_ is gated behind whichever skin the report happened to be poured into.

We think a report should be the opposite of a dead end: something you can read with your eyes, **query with SPARQL**, and **validate with SHACL**—from the same file, with no specialized tooling in between. So we built a proof of concept: our published reports, rendered as **DataBooks**.

## What a DataBook is

The DataBook pattern comes from [Kurt Cagle](https://ontologist.substack.com/p/databooks-markdown-as-semantic-infrastructure): a single Markdown document that is simultaneously human-readable prose, a typed data container, and a self-describing semantic artifact. YAML frontmatter carries the metadata, provenance, and a manifest; typed fenced blocks carry the payloads—Turtle, JSON-LD, SPARQL, SHACL. As Cagle puts it, a raw Turtle file is portable but _not self-describing_; a DataBook wraps the data in the interpretation it needs to stand on its own.

It's a pattern with unusual cross-aisle support. Charlie Hoffman—a pioneer in digital financial reporting—[recently called it](https://digitalfinancialreporting.blogspot.com/2026/06/databook.html) "a document a human can read, a data file that a computer can process, and a toolbox that carries its own instructions," and "a useful convention [that] might even be considered a best practice," noting that W3C standardization efforts are underway. When the leading voice of the semantic-web community and the inventor of XBRL are pointing at the same packaging idea, it's worth building on.

## What we built

A published RoboSystems report **is** a collection of Information Blocks—a balance sheet, an income statement, a cash flow statement, a statement of changes in equity. We already emit every report as a JSON-LD semantic graph; the proof of concept takes that bundle and renders it as a DataBook in which **each block appears twice**: once as a Markdown table a human can read, and once as an addressable Turtle block carrying the same facts as RDF, keyed by an id declared in the frontmatter manifest.

The human half looks like a financial statement:

| QName                      | Concept                | 2025-12-31 |
| -------------------------- | ---------------------- | ---------: |
| `rs-gaap:AssetsCurrent`    | **Assets, Current**    | $65,795.00 |
| `rs-gaap:AssetsNoncurrent` | **Assets, Noncurrent** |  $4,925.03 |
| `rs-gaap:Assets`           | **Assets**             | $70,720.03 |

The machine half, in the same file, is the same numbers as a graph:

```turtle
@prefix rs:      <https://robosystems.ai/vocab/> .
@prefix rs-gaap: <https://robosystems.ai/taxonomy/rs-gaap/v1/> .
@prefix skos:    <http://www.w3.org/2004/02/skos/core#> .

<.../ib/b6dfb8d2-…> a rs:InformationBlock ;
    skos:prefLabel "rs-gaap — Balance Sheet — Classified" ;
    rs:blockType "balance_sheet" ;
    rs:factSet <.../factset/fs_01KVF94CHNRJ4E25PMT7ZM6Y70> .

<.../fact/fact_…74> a rs:Fact ;
    rs:element     rs-gaap:Assets ;
    rs:numericValue 70720.03 ;
    rs:period      <.../period/p_1> ;
    rs:unit        <.../unit/u_USD> .

rs-gaap:Assets a rs:Element ;
    skos:prefLabel "Assets" ;
    xbrli:balance "debit" ;
    xbrli:periodType "instant" ;
    rs:source "rs-gaap" .
```

Every fact is an addressable resource. Every concept resolves to an element with its balance type, period type, and taxonomy source. The frameworks the report was rendered against—the `rs-gaap` presentation, calculation, label, and rules networks—are pinned by version in the frontmatter, so the report says exactly which rules it was built to. And the DataBook carries its own **SHACL and XBRL 2.1 validation evidence inlined**: it doesn't just assert the numbers, it ships the proof they're well-formed.

One line in the document says the whole thing: _"the bundle and this DataBook are two skins of one graph."_ The JSON-LD bundle and the human-readable DataBook are not two exports that might disagree—they're two projections of one underlying report graph. Render either; they reconcile by construction.

Two honest caveats. This is a **proof of concept**, not a product feature yet: the JSON-LD is what we emit for real, and the DataBook is a converter on top of it. And the format is brand new—the spec lives at `w3id.org/databook/ns#`—so rendering real, validated financial reports this way puts us among its first adopters. The direction we want is to offer DataBook as a **first-class serialization method**, the way we already treat XBRL and JSON-LD. We're not there yet; we wanted to build the smallest real version first.

## Why this form (and where XBRL still wins)

I want to be precise here, because it's easy to mistake this for an anti-XBRL argument. It isn't.

XBRL is the canonical serialization for a filed financial report, and **iXBRL has the higher immediate value** for anyone whose job is regulatory submission—that's the format regulators ingest, and it isn't going anywhere. We emit XBRL too; the World Online demo report ships with all three skins—Markdown, JSON-LD, and XBRL—side by side.

What the DataBook / JSON-LD form adds is _immediacy_. You can **query it with SPARQL** and **validate it with SHACL** the moment you have the file—no Arelle install, no validation add-ons, no taxonomy-loading ceremony. "What's total current assets, and which leaf facts roll into it?" is a query you write in thirty seconds against a file you already have open:

```sparql
SELECT ?label ?value WHERE {
  ?fact a rs:Fact ; rs:element ?el ; rs:numericValue ?value .
  ?el skos:prefLabel ?label .
}
```

So the honest framing is _complement, not replacement_: XBRL is the canonical, regulator-facing serialization; the DataBook is the immediately queryable, validatable, human-and-LLM-readable one. The thesis underneath—that a report is better as a self-describing semantic graph than as a flat document—doesn't require throwing away the standard. It just stops treating the standard as the only door into the data.

## The deeper reason: a report that carries its own meaning

For the semantic-web reader, here's the part that matters.

In our system, an **Information Block** is the molecular unit of accounting information—a bundle of atoms (facts, elements, connections) with the wiring that makes them mean something (the pattern, the rules, the provenance). The governing rule is that _what crosses a system boundary is always a molecule, never an atom_: a number never travels without the context that makes it interpretable.

A DataBook is the natural **external skin of that molecule**. It's an Information Block—or a whole report of them—given a portable, addressable, self-describing form. Cagle calls his underlying model _holonic_, and that's exactly the right word: each block is a complete, self-verifiable whole at its own level _and_ a part of the report above it. A DataBook is a holon you can email.

That self-describing property is also why Charlie flags databooks as **LLM-readable**—and it's where this stops being a packaging story and becomes the core of how the platform already works. An LLM doesn't need a bespoke API to consume a DataBook; the artifact explains itself. The "converse with the financial statement" half of the vision is already live for us: our MCP tools and AI Operators query these report graphs directly—it's how our SEC research pipeline produces fact-based company analysis today. Point that same capability at a DataBook and the report becomes something you can _ask questions of_, with every answer traceable back to an addressable fact.

## Where it's headed

The full vision is bigger than a file format, and I'd rather name it honestly than overclaim it.

The destination is **bidirectional drill-down across the whole stack**: from a dashboard, to a financial statement, to the working paper behind a line, to the transactions inside it, to the business event that caused them—and back up—with an LLM you can converse with at every level. The drill-_through_ half (an LLM reasoning over the report graph) is here. The full holonic drill-down—every line on a statement resolving to its supporting blocks, recursively, the way working papers actually stack—is a real build, and it deserves to be done properly rather than half-done as a demo. So for now it's a guiding principle we're building toward, with people from the XBRL and semantic-web worlds as design partners.

Charlie had a good phrase for the shape of it: a _semantic, model-driven report writer_—a report layer over a graph that actually knows what the numbers mean. That's the thing we're building, and the DataBook is what it hands you on the way out.

## Try one

The demo DataBooks are real artifacts, not mockups: a small advisory LLC, a Seattle Method reference case, and the 22,000-line World Online general ledger, each rendered as human tables plus addressable RDF, with SHACL and XBRL evidence inlined. Lift the Turtle out, run a SPARQL query against it, check the facts with your own SHACL shapes—it'll reconcile.

If a financial report you can actually query sounds like the right shape, that's the platform: open source, self-hostable, and built so every number is an addressable, verifiable resource. Start at **[robosystems.ai](https://robosystems.ai)**.
