---
name: batch-research
description: "Set up a batch of research briefs and print the lead prompt for a second machine: look up each ticker's latest filing, scaffold or recover each project, write each ticker's TASK.md, then end with one prompt to /copy and paste into the lead session there. Use for \"batch-research\", \"batch research TICKER ...\", \"set up a research batch\", or \"queue briefs for the second Mac\"."
argument-hint: '[TICKER ...] [--deep TICKER ...] [--parallel N]'
metadata:
  lane: gtm
---

Prepare a batch of brief-only research runs, then hand the batch to a **lead session** on another
machine (or this one) that runs one subagent per ticker. `projects/` is synced between machines,
so the task files written here reach the lead, and the lead's progress comes back the same way.
This skill writes nothing but project files; it never publishes.

## Arguments
- `$ARGUMENTS`: tickers, space-separated. With none, use the list agreed in this conversation;
  if there is none, ask for it.
- `--deep TICKER ...`: tickers to run at the deep tier (video picks). The rest run middle tier.
- `--parallel N`: subagents the lead runs at once (default 4).

## Steps

### 1. Look up each ticker's latest filing (SEC graph)
One query for the whole list, with the `robosystems-sec` MCP:

```cypher
MATCH (e:Entity)-[:ENTITY_HAS_REPORT]->(r:Report)
WHERE e.ticker IN ['WK', 'BILL'] AND r.fiscal_year_focus >= 2025
RETURN DISTINCT e.ticker, e.cik, e.name, r.form, r.filing_date, r.report_date, r.accession_number
ORDER BY r.filing_date DESC LIMIT 200
```

For each ticker take the newest 10-K, 10-Q, 20-F or 40-F. Drop, with a one-line reason:
- a ticker the graph does not hold;
- a ticker whose `projects/{T}/STATUS.md` already reads `stage: COMPLETE` for the same accession.

Flag, but keep, a filing more than 30 days old: the brief will read stale.

### 2. Get each project ready
- **No project**: `just new {T}`.
- **A project holding an older quarter's brief in `reports/`**: `just recover {T}`. It sets the old
  outputs aside and writes `sources/_prior_coverage.md`.
- **A project already prepared** (empty `reports/`): nothing to do.
- **Stale instructions**: if `projects/{T}/AUTHORING_INSTRUCTIONS.md` differs from
  `template/AUTHORING_INSTRUCTIONS.md` and the project is not in a campaign, copy the template in.
  A campaign project keeps its campaign's instructions; say so in the summary.

### 3. Write each task
Choose the batch id first: the date and a short label (`2026-11-23-software`).

```bash
uv run python tools/write_task.py {T} --cik {CIK} --accession {ACCESSION} --form {FORM} \
  --period-end {REPORT_DATE} --filed {FILING_DATE} --company "{NAME}" --batch {BATCH_ID} [--tier deep]
```

It writes `projects/{T}/TASK.md` from `template/BRIEF_TASK.md` and resets `projects/{T}/STATUS.md`
to `stage: queued`. It refuses when the project already holds this cohort's outputs. Re-run with
`--redo` only when told to redo that ticker; it moves the old outputs to `.partial/`.

Use the company name as the graph gives it, in title case (`WORKIVA INC` becomes `Workiva Inc.`).

### 4. Summarize, then print the lead prompt LAST
First a short table: ticker, company, form, filed, tier, and initiating or continuing coverage,
plus anything dropped or flagged. Then the lead prompt below, filled in, as the **final** thing
in the reply, with nothing after it, so `/copy` takes exactly the prompt.

If the session running this skill keeps a pipeline record elsewhere (a vault, a tracker), update it
from the task files before printing the prompt: the prompt must be the last thing in the reply.

```
You are the lead for a research batch in this repository (robosystems-content-machine).
Batch {BATCH_ID}. Tickers ({N}): {T1}, {T2}, ...
Run at most {P} subagents at a time.

Before starting, confirm template/BRIEF_TASK.md and tools/write_task.py exist. If either is
missing, stop and say: "Pull main first."

For each ticker, read projects/{T}/STATUS.md:
- stage COMPLETE: skip it.
- stage queued: start it.
- any other stage (an interrupted run): move its outputs aside first,
    d=projects/{T}/.partial/$(date +%Y%m%d-%H%M); mkdir -p $d; for f in reports/{T}_brief.md social/{T}_x_post.txt social/{T}_publish.json; do [ -f projects/{T}/$f ] && mkdir -p $d/$(dirname $f) && mv projects/{T}/$f $d/$f; done
  then set its STATUS.md stage to queued and start it.

Start each ticker as one general-purpose subagent, in the background, with this prompt:
  "Read projects/{T}/TASK.md and do exactly what it says. When you are done, reply with three
  lines only: stage, angle, and the validate RESULT line."
When one finishes, start the next until all are done.

Rules for you, the lead:
- Never write or edit a brief yourself. If a subagent ends without stage COMPLETE, start it once
  more; if it fails again, set its stage to stopped with the reason and move on.
- No publishing, posting, pushing, rendering or narrating, and no git command that changes state.
- If you hit a usage limit, stop starting subagents and print the table. The batch resumes when
  this prompt is pasted again: COMPLETE tickers are skipped.
- Keep a table (ticker, stage, angle, validate). At the end, print it and write it to
  projects/.batch/{BATCH_ID}.md.
```

## After the batch
`/status` on this machine reads every `projects/{T}/STATUS.md` as it syncs. Each finished brief
then goes to `/review {T}` and Joey's read before anything publishes.
