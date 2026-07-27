Generate standalone social atoms, drawn from the area roster in [`.claude/CONTENT_AREAS.md`](../CONTENT_AREAS.md), grounded in **where the system is now**, and written to a queue that `/buffer-draft-li` schedules.

This is what makes the volume cadence possible: at 1-2 items/day/channel nothing hand-written survives contact.

## Two things this is NOT

**Not a splitter.** Never chunk a blog post, brief, or spec section into pieces. The existing corpus describes the **June** system and the product has moved a long way since. It is voice reference and a repetition guard, nothing more. Every atom is written from current state.

**Not a single-subject run.** One `/atomize fpa` call on 2026-07-26 produced 7 atoms, six of which were variations on "here's what's wrong with your spreadsheet." One rich source carried a whole week; four were cut. **The roster exists to make that structurally impossible.**

## Arguments
- *(no args)* - **the weekly pass**: pick the N stalest areas with good hooks left, one atom each. This is the batch-day default.
- `--area <name>` - one specific area from the roster.
- `--engine P|B` - **P** = Joey personal (education, thought leadership, consultancy voice, never tickers). **B** = @RoboFinSystems (product voice). Default `P`.
- `--count N` - how many areas to draw from. Default 7.

## Step 1 - Pick from the roster

Read `.claude/CONTENT_AREAS.md`. Each area carries a `last_used` date.

**Selection rule: stalest first, skipping any area whose good hooks are exhausted.** One atom per area - never two from the same area in one batch. If fewer areas have usable hooks than `--count` asks for, **write fewer**. Padding a batch to hit a number is how a cadence becomes noise.

Show the selection and why before writing anything:
```
Roster pass, engine P, 7 areas:
  Event-driven ledger      last_used never    hook: no POST /events endpoint
  Close lifecycle          last_used never    hook: blockers as structured array
  ...
```

## Step 2 - Ground in current state

For each selected area, read its **Grounding** paths. Then confirm against:

| What | Where |
|---|---|
| What shipped and when | `/Users/french/Projects/robosystems/local/RoboSystems/roadmap.md` §1 + Appendix B |
| The public source a reader could reach | the wiki at `/Users/french/Projects/robosystems.wiki`, and the app READMEs |

**Internal docs (`local/**`) tell you what is true. They are never a source you can point a reader at, and never quotable** - they contain real graph IDs, incident detail, pricing analysis, and customer names.

## Step 3 - THE GATE (blocking - run before writing a single line)

Read the **⛔ GLOBAL ACCURACY FLAGS** and **⛔ ADDITIONAL FLAGS** tables in `CONTENT_AREAS.md`. For every atom, answer these in order. A "no" at any step means rewrite or drop the atom.

1. **Does this atom make a product claim at all?**
   - **No** → it is *problem-space*. Safe. Skip to step 4. This is the default and preferred register for Engine P: "here is what breaks in normal systems, here is how I think about it." A reader cannot fact-check a claim you did not make.
   - **Yes** → continue.
2. **Is there a public source a reader could reach?** The wiki, a public README, the live API, a published package. If the only source is `local/**`, the claim is unverifiable to every reader - **rewrite it as problem-space.** FP&A, Metrics and the Block Explorer are genuinely shipped with *zero* public documentation and fail here.
3. **Does the claim touch anything in the flag tables?** Check every one. The recurring traps: SOC 2 wording, multi-entity consolidation (not built), "you can author any block type" (statements and metrics return 501), the `research`/`financial`/`rag` operators (don't exist), "2,000 GAAP concepts" (that's the library; a tenant gets ~143), AI memory (gated off by default), self-serve graph creation (approval-gated), RoboInvestor analytics (roadmap only).
4. **Is the state right?** Shipped, partial, or aspirational - and does the atom's phrasing match?

If an atom survives all four, note in the queue which flag entries it was checked against.

## Step 4 - Write

**Every atom obeys the audience thesis:**

1. **Consequence first, concept as punchline.** Open with a question or outcome the reader recognizes as real work. Name the mechanism in the **last line**, one term per atom. Never open with "Information Block", "knowledge graph", "semantic layer", "taxonomy block", "provenance", "MCP", "REA".
2. **Standalone.** Every atom works cold, for someone who has seen nothing else. **Never a numbered series.**
3. **One idea.** The hook earns the "see more" - LinkedIn truncates at ~2 lines.
4. **Agree, then upgrade.** "Claude in Excel" is the wedge, not the enemy.

**Hard formatting rules:**

- **No em-dashes or en-dashes.** Spaced hyphen or restructure. Repo-wide rule.
- **No outbound links in the body** - measured suppression, median 106 impressions. Links go in a first comment.
- **No CTA, no promo code.** Engagement-question endings beat links.
- **Never `<` or `>`** - X and YouTube reject the paste. Spell out "under"/"over".
- LinkedIn ~800-1400 chars. X punchier.
- **The LinkedIn and X cuts are different writing, not a copy-paste.**

**Engine B differences**: product voice rather than first-person practitioner; may name the product; never Joey's consulting pitch. **If a P atom exists on the same area, write the B cut independently** - identical text across accounts reads as a bot mirroring itself.

**Consider the Article format.** Native X Articles are the highest-reach format measured (median 380 vs 272 text+video vs 112 text+self-link). Genuinely long-form atoms get flagged `format: article` and go out via `just x-article`.

## Step 5 - Preview, then write the queue

Show the list (number, area, hook line, char counts, register) and confirm before writing.

Append to `drafts/atoms/{personal|brand}.md`, continuing the existing numbering:

```
## N. <short title>  ·  area: <area>  ·  register: <problem-space|product-claim>  ·  status: ready

**LinkedIn**
​```
<body>
​```

**X**
​```
<body>
​```
```

## Step 6 - Stamp the roster

Update `last_used: <today>` on every area drawn from, in `CONTENT_AREAS.md`. **This is what makes rotation work** - skip it and the next run picks the same areas.

If you burned an area's last good hook, note it so the next pass skips it.

## Step 7 - Hand off

```
7 atoms → drafts/atoms/personal.md   (areas: event-ledger, close, taxonomy, ...)
Roster stamped. Next:  /buffer-draft-li --schedule
```

Do **not** schedule from this skill. Generation and scheduling stay separate so a bad batch can be edited before it reaches a channel.

## Notes

- **Areas with the most unwritten surface**: the consultancy angle (what a close teardown finds, what goes wrong in real books) is the thinnest and is what Engine P actually sells. The external-proof area (22,288 GL lines reconciled against a published reference, with deltas classified by owner including "our bug") is the strongest credibility material and has never been used.
- **When analytics accumulate**, this roster becomes the unit of measurement - which areas pull and which don't. That is impossible when everything is undifferentiated "product content."
