---
title: 'QuickBooks MCP: Three Doors, and What Each One Is Actually For'
date: '2026-09-22'
author: 'Joey French'
site: 'roboledger'
excerpt: 'Intuit ships an official QuickBooks MCP server and an official Claude connector, and both are better at running the business than anything we build. What neither does is map your accounts to a reporting framework, and that is the whole difference between an assistant that works your books and one that reports on them.'
metaDescription: 'QuickBooks MCP compared: Intuit official MCP server, the Intuit Claude connector, and RoboLedger. What each one can do, what it writes, and which job it is for.'
tags:
  [
    'quickbooks mcp',
    'claude quickbooks',
    'MCP',
    'ai accounting',
    'chart of accounts',
  ]
keywords:
  [
    'quickbooks mcp',
    'quickbooks mcp server',
    'claude quickbooks connector',
    'claude quickbooks integration',
    'quickbooks claude',
    'connect quickbooks to claude',
  ]
canonicalUrl: 'https://roboledger.ai/blog/quickbooks-mcp'
---

A year ago, connecting QuickBooks to an AI assistant meant exporting a report and pasting it into a chat. Today there are at least three ways to do it properly, two of them built by Intuit. They do genuinely different jobs, and the guides that rank for "QuickBooks MCP" mostly don't say which.

So here is the honest version, including the parts where we lose.

## The three doors

**Intuit's official QuickBooks Online MCP server.** It lives at [github.com/intuit/quickbooks-online-mcp-server](https://github.com/intuit/quickbooks-online-mcp-server) and it is not small: 145 tools across 29 entity types, plus 11 financial reports. Full create, read, update and delete, with environment variables to switch the write paths off if you want it read-only. It runs as a local subprocess on your own machine, which means it is a developer's tool: you register an app on the Intuit Developer Portal, you supply OAuth credentials as environment variables, and production needs a public HTTPS callback for the first handshake.

**Intuit's Claude connector.** Hosted, consumer-ready, and around 74 tools. This is the one most people mean. It creates, updates, sends, duplicates and schedules invoices and estimates. It adds customers, products and employees, sets base pay, sends payment links and reminders, and imports transactions from a CSV, a PDF or a photograph. It reads out a profit and loss, a cash flow, a balance sheet, A/R aging, and sales broken down by customer or product. It benchmarks you against similar businesses in your industry and region. It asks before it sends or changes anything.

**RoboLedger**, which is ours. One MCP endpoint, OAuth, and your books sit in a knowledge graph on the other side of it.

## What Intuit is better at, and it isn't close

If your question is "chase the invoice, bill the customer, pay the person, tell me who owes me money," use Intuit's connector. It is built on QuickBooks' own objects by the company that defines them, it writes back without a sync step, and it does things we have no answer to at all: payment links, payroll, lending.

We do not compete there and it would be silly to pretend otherwise. An accounting assistant that can raise an invoice in the chat is a genuinely useful thing, and Intuit shipped it first and shipped it well.

The interesting question is not which tool is better. It is what happens when you stop asking the books to *do* something and start asking them what they *say*.

## Where every one of these answers comes from

Ask any of the three for a profit and loss and you get one. The difference is what the numbers are grouped by.

QuickBooks classifies each of your accounts by its own account types: income, cost of goods sold, expense, other income, and so on. That classification is what produces a QuickBooks P&L, and it is why the report comes back with your account names on it, in your numbering, in whatever structure the business grew into. "Marketing - contractors (old)" is a line on your income statement because at some point somebody made it a line on your income statement.

For running a business that is completely fine. It is your chart of accounts and it is supposed to be yours.

It stops being fine the moment the answer has to mean the same thing to somebody outside. A lender, an investor, a board, an acquirer, or a benchmark. All of them need to know that what you call revenue is revenue in the sense they mean, and QuickBooks' account types do not carry that, because they were never meant to.

## The mapping layer

RoboLedger's answer is a mapping. Every account in your chart is tied to a standard reporting concept drawn from US GAAP: cash, accounts receivable, cost of revenue. That mapping is data in the system, not a tab in a workbook, and it is what tells the platform where an account belongs on the balance sheet, income statement, cash flow and statement of equity.

The first QuickBooks sync maps your chart with AI. Confident matches are applied, uncertain ones are applied and flagged for you to check, and anything it can't place is left unmapped rather than guessed. You can see the whole thing, and the coverage, on one page, and change any of it.

Everything downstream stands on that one layer. Live statements. The statements saved at each close. Forecasts. And comparisons against public companies, which work at all only because both sides are expressed in the same kind of concepts.

That last one is worth sitting with, because Intuit benchmarks too. Its comparison set is other QuickBooks businesses in your industry and region, aggregated and anonymised. That is a real dataset and in some ways a closer one, since those are companies your size. But you cannot see who is in it, you cannot choose them, and you cannot check the arithmetic. Ours is the public filings: statements those companies had to file, that you can open and read. Which of those you want depends on the question, and neither is strictly better. They are different in a way worth knowing before you quote a number to a board.

## So which door

- **You want to transact.** Invoices, estimates, payments, payroll, chasing receivables. Intuit's Claude connector. It is the best thing available and it is free with your subscription.
- **You are building software on QuickBooks.** Intuit's MCP server, locally. 145 tools and full CRUD is a lot of surface, and it is the right primitive for an application.
- **You want the books to report.** Statements built from a mapping rather than from account names, forecasts that run off your actuals, a comparison against filers in the same concepts, and a month end that can tell you what is blocking it. That is what we built.

Plenty of people will want two of these at once, and that is fine. They are MCP servers. A single chat can hold more than one.

## One thing worth checking before you connect anything

Whichever you pick, ask it the question you already know the answer to. Pull last month's gross margin and check it against the statement you already closed. Then ask it *why* the number is what it is, and see whether the answer traces to something you can open.

That is the test that actually separates these tools, and it takes about four minutes.

If you want the RoboLedger side of it, the setup is in [connect your books to your AI assistant](https://roboledger.ai/docs/connect-your-books), and the argument underneath all of this is [Accounting Runs on a Chain of Exports](https://roboledger.ai/blog/ai-native-accounting).
