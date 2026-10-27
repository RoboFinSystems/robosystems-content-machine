---
title: 'Accounting Software for Multiple Businesses: Consolidation Is a Read, Not a Project'
date: '2026-10-27'
author: 'Joey French'
site: 'roboledger'
excerpt: 'Every guide to accounting software for multiple businesses asks you to choose: separate books for each company, or one consolidated set. Map each company to shared reporting concepts once and you get both, with the consolidation drafted from the books every month.'
metaDescription: 'Accounting software for multiple businesses: each company keeps its own books and close, and the group consolidates from shared reporting concepts.'
tags:
  [
    'multi-entity accounting',
    'consolidated financial statements',
    'intercompany eliminations',
    'noncontrolling interest',
    'MCP',
  ]
keywords:
  [
    'accounting software for multiple businesses',
    'multi entity accounting software',
    'multi-entity accounting',
    'combined vs consolidated financial statements',
    'intercompany eliminations',
    'consolidate financial statements',
  ]
canonicalUrl: 'https://roboledger.ai/blog/several-companies-one-ledger'
---

In August our demo group's four companies booked $176,829.98 of revenue between them, and $1,230 of it was money they'd paid each other.

That's the problem with a group of companies in one sentence. Add the books up and you get a number that's too big. The group charged itself a management fee, lent itself $5,000, and owns the companies whose equity you just added in. Every one of those has to come back out before the statements mean anything, and in most small groups the place it comes out is a workbook: a tab per company, a mapping tab that says which account in one chart is which account in another, and a column of eliminations someone types in by hand at month end.

Search "accounting software for multiple businesses" and the guides on the first page frame it as a choice. Keep separate books for each business, or consolidate everything into one set. Separate books keep each company clean and leave you the workbook. One set gets rid of the workbook and makes the companies hard to tell apart, which is a problem the first time a lender asks for one of them on its own.

You shouldn't have to pick. Here's why the choice exists, and what it looks like when it doesn't.

## Why consolidation is sold as the expensive tier

Consolidation is hard in software for one reason: every company's chart of accounts is different. The roaster has "Green Coffee" and "Bagged Coffee" inventory accounts. The cafés don't have inventory accounts at all. Their equity is members' equity because they're LLCs, and the roaster's is a corporation's. To add them up, something has to know which accounts mean the same thing, and the usual answer is a mapping that someone maintains, every month, for every company, forever. That's the project, and it's why the products that do it well charge for it as a premium tier.

The fix is to stop mapping charts to each other. Map each company's chart to shared reporting concepts once, the same concepts a public company's statements are tagged with, and the group becomes a read. Revenue is revenue in every company because every company says what its accounts are, not because someone lined them up in a tab. The roaster's coffee inventory lines still show up on the group's balance sheet under their own names, rolled up inside inventory, and nobody had to tell the cafés about them.

## One group, four companies, one August

The demo group is Driftline Coffee Roasters and the companies under it:

- **Driftline Café LLC**, owned outright.
- **Driftline Harbor Café LLC**, 70% owned. A hospitality partner holds the other 30%.
- **Pier Market Kiosk LLC**, 40% owned. Too small a share to control it, so it's on the equity method.
- **Consolidation Adjustments**, a fourth company that holds nothing but the consolidating entries.

Each company keeps its own chart, its own calendar and its own close. When August ends, each one closes on its own, and then your AI drafts the month's consolidating entries from what's in the books. Here's what it drafted for August, read off the worksheet:

- **The business they did with each other.** The cafés paid the roaster $1,230 during the month. That's $1,230 out of the group's revenue and $1,230 out of its expenses, so the group's profit doesn't move, but its revenue stops counting sales the group made to itself.
- **What they owe each other.** $1,255 still owed to the roaster at month end ($667 from one café, $588 from the other), and a $5,000 note from the roaster to the café with $25 of interest. All of it nets to zero on the group's balance sheet.
- **The parent's investment against the companies' equity.** The roaster carries $26,800 of investment in the cafés. The cafés carry $31,000 of members' equity. The $26,800 comes out against the parent's share of that equity, and the other $4,200 isn't the parent's at all.
- **The outside owners.** The partner's 30% of Harbor Café is $25,250.40 of noncontrolling interest on the balance sheet, beside the parent's equity, and $1,503.60 of the month's profit, which is 30% of Harbor's $5,012.
- **The kiosk.** It isn't added in. The group carries its 40% instead: $1,080 of the kiosk's $2,700 August profit, and an investment that's grown from the $2,080 the roaster paid to $17,200, 40% of the kiosk's equity.

Add it up and the combined books carry $621,847.73 of assets. Consolidated, it's $603,912.73. The $17,935 difference is the group owing itself and owning itself. Net income attributable to the roaster's owners goes from $25,861.89 combined to $25,438.29 consolidated.

Nothing in that list was typed into a cell. A person reviewed the drafts and the group close posted them, and the group's month didn't close until every company had closed, nothing was left unexplained, and the consolidated balance sheet tied.

## Combined vs consolidated financial statements

These two words get used as if they mean the same thing, and they don't.

A **combined** statement adds the companies up. It's the workbook's SUM, and it's the $621,847.73. It's useful for seeing the whole group's footprint, and it's wrong as a set of financial statements, because it counts the group's dealings with itself.

A **consolidated** statement adds them up and then takes out what the group owes and earns from itself, the parent's investment, and anything the parent doesn't own. It's the $603,912.73, and it's what a lender, an acquirer or an auditor means when they ask for the group's numbers.

On the worksheet you see both side by side. Every company in its own column, then combined, then the adjustments, then consolidated, with the kiosk sitting beside the sum instead of in it. On the consolidated statement, click a number and you see the accounts it came from.

## When the group changes

Groups don't sit still, and the workbook is at its worst the month a company joins or leaves.

Driftline bought a fourth café, Northside, in October 2025: 75% for $31,500, which put $9,000 of goodwill on the group's books. It bought another tenth in February and sold it back in April. Then it sold the café at the start of June for $62,000.

The roaster's own books show a $32,794.12 gain on that sale. The group's gain is $8,360. The difference is $24,434.12, and it's not an error. The group had already counted Northside's profits as its own income while it owned the café, so it can't count them again when it sells. That one adjustment is the kind of thing that eats a weekend in a workbook. Here your AI records the sale with the price, the drafts take Northside out of the group from the next month, and the café stays in the books as a former member, so its months in the group still read.

## What your assistant sees

One connector covers the whole group. Connect Claude, ChatGPT or any MCP client and it knows the companies before you ask it anything. The questions are the ones you'd ask a controller:

- "Draft August's consolidating entries and tell me what you couldn't explain."
- "Why is the elimination for Harbor Café held back?"
- "What's the group's gain on the Northside sale, and why is it smaller than ours?"

When the books don't explain something, it says so. If the parent's investment doesn't match its share of a company's equity, that elimination is held back and the difference is named with its likely cause. It isn't plugged.

## What it doesn't do yet

So you don't find these out later:

- **Only the parent's QuickBooks connects.** The other companies' books come in through a bank feed and an opening balance sheet, the API or a file. If every company in your group is its own QuickBooks file today, that's the gap.
- **One currency.** A company that keeps its books in another currency isn't translated.
- **Flat groups.** One parent and its companies. A group inside a group isn't modeled.
- **Your own call on profit sold within the group.** If one company sells inventory or equipment to another at a markup, the unrealized profit is an entry you make.

It costs $99 a month for the graph, and every company in the group shares it. It's open source with no outside investors, so the books, and the software that keeps them, are yours.

How to set a group up, what each month asks of you, and what changes when a company is bought or sold: https://roboledger.ai/docs/consolidate-a-group
