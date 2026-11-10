---
title: 'Month-End Close Checklist for QuickBooks: Who Does Each Step'
date: '2026-11-10'
author: 'Joey French'
site: 'roboledger'
excerpt: 'Every month-end close checklist that ranks is published by a company selling the software that ticks its boxes, and none of them says which steps still need a person. This one marks each step with who does it: the ledger, the assistant, or a person who signs.'
metaDescription: 'Month end close checklist for QuickBooks Online, marked step by step: what the ledger does, what the assistant does, and what still needs a person.'
tags:
  [
    'month-end close',
    'quickbooks',
    'checklist',
    'ai accounting',
    'MCP',
  ]
keywords:
  [
    'month end close checklist',
    'month end close checklist quickbooks',
    'month-end close checklist',
    'quickbooks month end close',
    'month end close steps',
  ]
canonicalUrl: 'https://roboledger.ai/blog/month-end-close-checklist'
---

Every month-end close checklist that ranks is published by a company selling the software that ticks its boxes. Ours is too. The difference is a column none of them carries: who does each step.

Three answers go in that column. **The ledger** is RoboLedger itself, the code that posts an entry, refuses a close and keeps the audit note. **The assistant** is whatever you talk to the ledger through: Claude, ChatGPT or any MCP client. **A person** is you, or whoever signs. My own company's books close on this, and the person column is the one I read.

The steps follow the close guide's phases and stay QuickBooks Online specific where the guide is: the sync, the transactions that change after they synced, the entries written back. Where the column says "a person", that's the product's rule and not a courtesy. A bank line never posts unclassified. A draft posts when a person approves it, and not before. A sign-off carries a name. A closed month reopens with a reason or stays closed.

## The checklist

| Step | Who does it | What "done" looks like |
| --- | --- | --- |
| **Before the close** | | |
| Connect QuickBooks Online and sync | a person | The connection is live and the last sync is current. |
| Map the chart of accounts | a person | Each account sits on a reporting concept. A close still posts without this, but it can't save the month's statements. |
| Set up recurring entries as schedules | the assistant | Depreciation, amortization and prepaids that roll off each have a schedule, set up once. The assistant reads a past month's entries for the amounts, asks you for what history can't tell it (an asset's cost, its useful life, the method) and shows the period-by-period run with `preview-schedule` before anything is kept. |
| Write down your close procedures | a person | Saved as a close procedures document. The assistant looks for it before every close and follows it. |
| **Clearing the blockers** | | |
| Read the playbook and find where you stand | the assistant | `get-close-playbook` for the sequence, `get-fiscal-calendar` for the last closed month, the close target and what's blocking, `get-period-close-status` for each schedule's entry and its status. Months close in order, one at a time, and a month can't close until it's over. |
| Refuse the close while anything blocks it | the ledger | The close comes back with the blockers named, not a warning. |
| Catch up a stale sync | the assistant | Runs a fresh sync and waits for it. |
| Settle transactions that changed in QuickBooks after they synced | a person | The assistant shows you each one. You choose: restate the month it belongs to, post the difference in an open month, or mark it already handled. |
| End a schedule that ends this month | a person | An asset sold or a policy cancelled has its schedule ended before the month's entries are drafted. |
| Clear the inbox of events dated in the month | a person | In Ledger → Inbox, every event dated in the month under Captured or Classified is approved or rejected. Once the month closes they could never post into it. |
| Hold an unclassified bank line | the ledger | A bank line with no account on it is refused at posting, whoever asks. |
| Run the reconciliations again | the assistant | `preview-reconciliations` sets the ledger's balances at the period end beside QuickBooks' own trial balance, or beside what the schedules say an account holds, and shows what's different. |
| Sign off a reconciliation | a person | A period that reconciles gets your name on it. The assistant records it with `sign-off-reconciliation`, and the record says who ran the comparison and who reviewed it. |
| **Drafting** | | |
| Draft the month's entries | the assistant | Every active schedule gets its entry for the month, plus any one-off adjustment you ask for. |
| Keep the drafts as drafts | the ledger | Nothing posts and nothing is written to QuickBooks until a person approves. |
| **Review and approval** | | |
| Show every draft | the assistant | Each entry with its debits and credits, whether they balance, and which ones will be written to QuickBooks. |
| Approve the drafts | a person | Your explicit approval, in the conversation. The playbook makes the assistant wait for it, and your MCP client may ask you to allow the call as well. |
| Decide any override | a person | Allow stale sync, close without the undrafted entries, close without reconciling: each happens on your say-so, and each is kept in the close's audit note. |
| Close the month | the assistant | `close-period`, once you've approved. Posting the entries, checking that the balance sheet balances and marking the month closed happen in one step. |
| Save the month's statements | the ledger | The balance sheet, income statement and cash flow for the month are saved, and they don't move when the live ledger does. |
| Read the receipt | the assistant | How many entries posted, how many went to QuickBooks, and whether the statements were saved and passed their checks. |
| **After the close** | | |
| Run the forecasts again | the assistant | The closed month is an actual, and each scenario picks up from its real closing balances. |
| Create the report | the assistant | If the statements go to anyone outside the conversation. |
| Reopen a closed month | a person | `reopen-period`, with a reason that's kept in the audit trail. Reopening works backwards one month at a time from the most recent. |
| Keep posted entries posted | the ledger | A reopened month's entries stay posted. A wrong one is undone with a reversing entry, then the month closes again and its statements are saved fresh. |

## What the column tells you

Count the rows. The assistant and the person split them evenly, ten each, and the ledger holds five. The assistant's ten are all legwork: reading where you stand, running a sync, running a comparison, drafting, showing, reading the receipt back. The ledger's five are the ones nobody talks their way past. They're code, and you can read it: the close engine is Apache 2.0 in the RoboFinSystems/robosystems repository, under `robosystems/operations/roboledger/fiscal_calendar/`, where `FiscalCalendarService` and `PeriodCloseService` are the refusal.

The person's ten are the ones with a name on them: a choice about a changed transaction, an approval, a sign-off, a reason to reopen. That column is the whole arrangement: the books closed every month, with a person approving what the assistant drafts.

## What is on a month-end close checklist?

The same things on every version: the books synced and the chart mapped, the recurring entries drafted (depreciation, amortization, prepaids that roll off), the accounts reconciled and signed off, the inbox cleared of anything dated in the month, the entries reviewed and approved, the month locked, and the statements saved. The version above adds the column that says who does each of those, because the list of steps was never the hard part.

## Which steps can the assistant do, and which need a person?

The assistant does the reading and the running: where you stand, the sync, the comparisons, the drafts, the receipt. A person does everything with a judgment or a name in it: deciding what to do with a transaction that changed after it synced, approving or rejecting inbox events, signing off a reconciliation, approving the drafts, deciding an override, giving the reason for a reopen. The ledger holds the line between the two. It won't post an unclassified bank line, won't post a draft nobody approved, and won't close over a blocker without an override it then writes into the audit note.

## How long should a small company's close take?

There's no number of days on this checklist, and I won't put one on it. What it does show is where the time goes: into the blockers, and a blocker cleared during the month (an inbox kept current, a reconciliation run when the statement arrives) is one the close never meets. With the blockers gone, the close itself is a conversation: what's blocking, show me the drafts, close it, with one approval in the middle. A busy month can run longer than the assistant's call waits, and the close keeps running until the receipt is ready; it never needs starting twice.

## What do I do first if my close is late?

Ask what's blocking it, and nothing else yet: "What's blocking the October close?" The assistant reads the calendar and comes back with the list: the sync behind, transactions changed in QuickBooks since they synced, a schedule that ends this month, a schedule's entry not yet drafted, events dated in the month that never posted, a reconciliation that doesn't tie or isn't signed off. Work down that list and the close stops being late on its own. The overrides are there for the month you have to close over a problem, and a month closed over a problem keeps it, so clearing the blocker is nearly always the shorter route.

The full guide, with the close recorded on a demo company's books: [Close the month with your AI assistant](https://roboledger.ai/docs/month-end-close)
