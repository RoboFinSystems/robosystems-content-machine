Generate standalone social atoms for a subject, grounded in **where the system is now**, and write them to a queue that `/buffer-draft-li` schedules.

This is the piece that makes the volume cadence possible: at 1-2 items/day/channel nothing hand-written survives contact. See `content-engine.md` §5.6.

## The one thing this is NOT

**Not a splitter.** Do not chunk a blog post or a brief into pieces. The corpus (12 blog posts, ~20 ticker projects, 5 Medium essays) describes the **June** system; the product has moved a long way since. Shipping it faithfully broadcasts a stale picture.

The corpus is **voice reference and a repetition guard**. Every atom is written from current state.

## Arguments
- `$ARGUMENTS` - the subject. A feature area (`fpa`, `explorer`, `report-engine`, `mcp`, `close`), a consultancy theme (`teardown`, `messy-books`), or freeform.
- `--engine P|B` - which voice. **P** = Joey personal (education, thought leadership, consultancy). **B** = @RoboFinSystems (product, brand voice). Default `P`.
- `--count N` - how many atoms. Default 7 (one week of one channel).

## Step 1 - Ground in current state (do this before writing anything)

Read, in this order. Do not skip to writing.

| What | Where |
|---|---|
| What shipped and when | `/Users/french/Projects/robosystems/local/RoboSystems/roadmap.md` - §1 and the Appendix B ledger |
| The subject's spec | `.../specs/{fpa-operating-plan,report-engine,metrics-analytics}.md` |
| Durable design reasoning | `.../ref/{information-block,event-driven-ledger,reporting,taxonomy,ontology}.md` |
| The actual surfaces | `roboledger-app/README.md` (Core Features), `robosystems/README.md` |

**Anything you assert must be true today.** If the roadmap says a rung is deferred or parked, it does not go in an atom. When in doubt about whether something shipped, check Appendix B rather than inferring from a spec's existence.

## Step 2 - Check the corpus (repetition guard)

Skim `blog/*/post.md` titles + `drafts/thought-leadership/linkedin.md` for points already made. If an idea is already published, either skip it or **advance** it - "here is what changed since" is fine, restating is not.

Match the voice: `drafts/thought-leadership/BRIEF.md`.

## Step 3 - Write the atoms

**Every atom obeys the audience thesis** (`content-engine.md` §1):

1. **Consequence first, concept as punchline.** Open with a question or outcome the reader recognizes as real work. Name the mechanism in the *last* line, one term per atom. Never open with "Information Block", "knowledge graph", "semantic layer", "taxonomy block", "provenance", "MCP".
2. **Standalone.** Every atom works cold, for someone who has seen nothing else. **Never a numbered series.**
3. **One idea.** The hook earns the "see more" (LinkedIn truncates at ~2 lines).
4. **Agree, then upgrade.** "Claude in Excel" is the wedge, not the enemy.

**Hard formatting rules:**

- **No em-dashes or en-dashes.** Spaced hyphen or restructure. Repo-wide.
- **No outbound links in the body.** Measured suppression (median 106 impressions). Links go in a first comment.
- **No CTA, no promo code.** Engagement-question endings beat links. Soft brand mention at most, often none.
- **Never `<` or `>`** - X and YouTube reject the paste. Spell out "under"/"over".
- LinkedIn ~800-1400 chars. X punchier; Premium allows length but tighter wins.
- **The LinkedIn and X cuts are different writing, not a copy-paste.** Same idea, native cadence each.

**Engine B differences** (`--engine B`): product voice rather than first-person practitioner; may name the product directly; must not use Joey's consulting pitch. **If Engine P atoms exist on the same subject, the brand cut must be independently written** - identical text across accounts reads as a bot mirroring itself.

**Consider the Article format.** Measured 2026-07-26, native X Articles are the highest-reach format on the account (median 380 vs 272 text+video vs 112 text+self-link). If an atom is genuinely long-form, flag it `format: article` and it goes out via `just x-article` instead of as a post.

## Step 4 - Preview, then write the queue

Show the list (number, hook line, char counts) and confirm before writing.

Write to `drafts/atoms/{personal|brand}.md`, appending if it exists. Format - keep it exactly parseable, `/buffer-draft-li` reads it:

```
## N. <short title>  ·  source: <subject>  ·  status: ready

**LinkedIn**
​```
<body>
​```

**X**
​```
<body>
​```
```

Number continues from whatever is already in the file. Statuses: `ready → scheduled (date) → posted (date)`.

## Step 5 - Hand off

Report the count and the next command:

```
7 atoms → drafts/atoms/personal.md  (source: fpa, engine P)
Next:  /buffer-draft-li --schedule   (reads .claude/POSTING_TIMES.md)
```

Do **not** schedule from this skill. Generation and scheduling stay separate so a bad batch can be edited before it reaches a channel.

## Notes
- **Subjects with the most unwritten surface right now** (nothing published on any of them): the FP&A arc (scenario engine, three-statement articulation where the balance sheet balances by construction, live on a production tenant with 23 months restamped), the Block Explorer at `/explorer`, the report-engine validation spine, line assertions.
- The consultancy angle is under-served and is what Engine P actually sells: what a close teardown finds, what goes wrong in real books, what a controller should ask their software.
- If a subject yields fewer good atoms than `--count`, **write fewer.** Padding a batch to hit a number is how the cadence turns into noise.
