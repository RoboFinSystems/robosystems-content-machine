---
title: 'Information Blocks: Turning Transaction Line Items Into Financial Reports'
date: '2026-6-19'
author: 'Joey French'
excerpt: 'A ledger and a financial report are two shapes of the same truth. Here is the single primitive that connects them—and that lets you both pivot a statement out of your transactions and author a schedule into them.'
metaDescription: 'How Information Blocks turn transaction line items into financial statements and let you author schedules—one self-describing primitive behind every accounting artifact.'
tags:
  [
    'information block',
    'financial reporting',
    'accounting architecture',
    'XBRL',
    'graph database',
  ]
keywords:
  [
    'information block',
    'financial report architecture',
    'transaction line items',
    'depreciation schedule',
    'XBRL hypercube',
    'fact grid',
  ]
featured: false
canonicalUrl: 'https://robosystems.ai/blog/information-blocks'
---

# Information Blocks: Turning Transaction Line Items Into Financial Reports

A ledger and a financial report are two different shapes of the same truth.

The ledger is a long list: every journal entry, every line item, in the order it happened. A balance sheet is a compact, hierarchical thing: totals that roll up from subtotals that roll up from accounts, arranged the way a reader expects to see them. Getting from one to the other is the daily work of accounting—and most software treats it as a black box. Raw data goes in, a formatted statement comes out, and the relationship between them lives in code you can't see or check.

We took a different approach. The thing that connects a pile of line items to a finished report is a first-class object in our system. We call it an **Information Block**. Once you have it, two operations that usually feel like separate features—generating a statement from your ledger, and authoring a schedule like depreciation—turn out to be the same primitive, used in two directions.

## Atoms and molecules

Start with a distinction that does a lot of work.

**Atoms** are data that stands alone but means nothing in isolation: an _element_ (a concept like "Accumulated Depreciation"), an _association_ (a wire connecting two concepts), a _fact_ or a _line item_ (a number). On its own, a single fact—`$2,000`—tells you nothing. Two thousand dollars of what? When? For whom? Rolling up into which subtotal?

**Information** lives one level up. A _molecule_ is an assembly of atoms with enough context to be interpreted unambiguously: the number, plus the concept it instances, the period it covers, the entity it belongs to, the rule that says it should reconcile, and the pattern that says how it's arranged. That bundle is an Information Block.

The vocabulary here isn't ours. The _Information Block_, and the atomic-versus-molecular framing it rests on, come from Charlie Hoffman's **Seattle Method**—his body of work on the semantics of digital financial reporting. We've adapted its concepts to a property graph rather than adopting its XBRL machinery wholesale, but the intellectual debt is real, and worth naming up front.

One rule governs everything downstream:

> What crosses a system boundary is always a molecule, never an atom.

When an AI operator reads your books, when an auditor reviews them, when the SDK hands data to another application—they receive molecules, never bare rows. A number never travels without the context that makes it mean something. That's not a stylistic preference; it's the discipline that makes the data safe for an AI to reason over. A model can't misread a fact whose meaning travels with it.

A note on names: on screen, you still see "Depreciation Schedule" and "Balance Sheet." Underneath, both are an `InformationBlock` with a `block_type` tag that says which kind it is. The friendly noun is a display concern; the molecule is the engineering reality—and it's exactly why one set of machinery can serve every kind of accounting artifact instead of a bespoke pipeline per report.

## Direction one: pivoting line items into a statement

Here's the first use of the primitive.

Your ledger holds **line items**—the atomic rows of every journal entry. A financial statement holds **facts**—the atomic rows of a report. They're the same numbers in a different shape, and the transformation between them is a pivot.

A balance sheet's structure is a hierarchy. Leaf accounts roll up, through calculation relationships, into subtotals, into totals. That structure is _shared_—it comes from the taxonomy, the standardized vocabulary of concepts and how they aggregate. Your line items are the _content_. The statement is simply your content projected through the shared structure:

|                                            | Where it comes from                         | Whose it is          |
| ------------------------------------------ | ------------------------------------------- | -------------------- |
| **Structure** (concepts, roll-ups, layout) | the taxonomy / framework                    | shared, standardized |
| **Content** (which account, what amount)   | your ledger's line items                    | entirely yours       |
| **The statement**                          | the projection of content through structure | the result           |

Each line item lands on a leaf concept; the leaves roll up the calculation tree; the subtotals and totals are _derived_—computed from the leaves, then persisted as facts so they're as queryable as anything you posted by hand. The engine that does this is what we call the **fact grid**: it pivots your transactions across the dimensions of the report—concept, period, entity, segment—the way a spreadsheet pivot table reshapes rows into a cross-tab. The difference is that the "columns" here are an accounting taxonomy with real aggregation rules, not just labels.

One consequence catches people off guard: **you don't _create_ a balance sheet, you _render_ one.** A statement Information Block has no stored numbers of its own until you publish a report; ask for it beforehand and you get the structure with an empty fact set. The "what do my books look like _right now_?" view is computed on the fly from your current line items and handed back without being saved—a live pivot. The statement is always a _view_ of the ledger, never a second copy that can quietly drift out of sync with it.

This is also why "standardized reporting" never means "rigid." The structure is shared so your numbers stay comparable; the content stays entirely yours. Two companies can render the very same balance-sheet structure over completely different books, and both come out faithful.

## Direction two: authoring a schedule

The second use is the mirror image.

Some information isn't a pivot of what already happened—you _originate_ it. A depreciation schedule, a prepaid-expense amortization, a deferred-revenue waterfall: these are forward-looking plans. They say "here's how this balance unwinds over the next N periods, and here are the closing entries that make it happen." There are no line items to pivot yet. There's an intent.

So the same Information Block runs in reverse. Instead of materializing a view from atoms that already exist, you **declare** the molecular properties—the entry template, the start date, the term, the periodic amount—and the system **generates** the atoms: the forward facts for every period, the integrity rules that keep them honest, and a chain of pending obligations that feed each month's close.

This is the _authored, not derived_ case—and it's where the whole architecture actually came from. The schedule subsystem shipped first, built to handle closing entries, and it incidentally proved the three ideas the rest of the platform now rests on: that an AI can reason over an accounting molecule when that molecule carries its own production mechanics; that writes can be made idempotent when a molecule exposes its own state; and that a single addressable unit is enough context for most close-workflow operations. We reverse-engineered the Information Block from the shape the schedule had stumbled into.

A schedule carries its **rules as data**, riding along inside the molecule. For a depreciation schedule, those include things like _"the change in accumulated depreciation each period equals that period's depreciation expense"_ and _"historical periods never generate new closing entries."_ They aren't buried in application logic—they're rows attached to the block, evaluated every time the block is touched, producing pass/fail results an auditor can read directly. And when you edit the schedule—say you correct an amortization curve and rebuild it in place—the facts and the obligation chain regenerate from the corrected definition, and the rules re-run against the new state. The molecule is the unit of editing, not just the unit of display.

## Why one primitive instead of two

Pivoting a statement and authoring a schedule feel like different features. Modeling them as the _same_ primitive—a molecule with a typed mechanics recipe and rules carried as data—buys three things that matter:

- **Provenance.** Every fact records _how it came to exist_: pivoted from posted transactions, derived by a rule, or asserted as a forward plan. We treat that as mandatory, not optional metadata. A number you can't trace is a number you can't trust; here, every number knows its own origin.
- **One surface for many artifacts.** Statements, schedules, reconciliations, metrics—they all read out as the same envelope. An operator, the SDK, or the UI knows a block's shape from its type alone, with no runtime guessing. That's what keeps the system from sprouting a parallel toolset per report type.
- **Composability—notes are statements too.** An Information Block is a _holon_: a complete, self-verifiable whole at its own level, and simultaneously a part of the larger structure above it. A depreciation schedule explains a line on the balance sheet. "Note 6 — Property, Plant & Equipment" in a 10-K explains a line on the balance sheet. Architecturally, those are the _same kind of thing_—a supporting block attached to the figure it explains. A report's notes section is just the union of every supporting block reachable from its statements, organized by topic.

## The takeaway

The distance between your transactions and your financial statements shouldn't be a black box.

Modeled as Information Blocks, it's a pivot you can inspect in one direction and an authored plan you can declare in the other—both built from the same self-describing molecules, both carrying their own rules and provenance, both legible to a human, an auditor, or an AI. That legibility is the entire point. It's what lets an AI close your books _and_ lets you check its work, line by line, back to the source.

You can see it on your own numbers. Head to **[robosystems.ai](https://robosystems.ai)**—run a statement out of your ledger, author a schedule into it, and trace any figure back to where it came from. The platform is open source and self-hostable, so the machinery behind every block is yours to inspect.
