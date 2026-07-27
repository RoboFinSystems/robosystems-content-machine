Queue selected atoms from `drafts/atoms/personal.md` (or any `--source` queue) to Buffer: a LinkedIn post plus an optional mirrored **X** text cut (posting X in parallel with LinkedIn is fine here, because these are text posts with no video and no Article).

**Two modes.** `--schedule` (the batch-day mode) places each post at an explicit time from [`.claude/POSTING_TIMES.md`](../POSTING_TIMES.md), so the week ships without a second visit. Default is draft-only, which needs you to open Buffer and press post per item. See "Which mode" below - picking wrong is how this lane stalled in June.

LinkedIn is the primary channel for this content. The X mirror is a text cut only. Buffer cannot put long video or an X Article on X (those are native-only via `just x-post` / `x-short` / `x-article`). That never bites here because these posts are pure text. See [[buffer-drafting]] for the channel reality.

## Arguments
- `$ARGUMENTS` - optional selectors: post numbers (`1 3 8`), `all`, or a status (`ready`). Empty lists them and asks which.
- `--schedule` - schedule at explicit times instead of saving drafts. **This is the batch-day default.**
- `--source <path>` - which queue to read. Default `drafts/atoms/personal.md` (what `/atomize` writes). The legacy `drafts/thought-leadership/linkedin.md` still parses.
- `--no-x` - LinkedIn only.

## Channels (verified live 2026-07-26)

Buffer org **Harbinger FinLab** (`6a4710d8f9144a22713ee87e`) has exactly two channels, **both personal**:

| Service | Account | Notes |
|---|---|---|
| `linkedin` | **Joseph French** (`josephtfrench`) | personal profile, posting goal 5/week |
| `twitter` | **@JosephTFrench** | personal, X Premium (long text OK) |

**@RoboFinSystems is NOT in Buffer.** It posts through the direct X API (`just x-post` / `x-short` / `x-article`). Earlier versions of this file wrongly named the Buffer X channel `robofinsystems`; anything drafted through it went to the personal account. Resolve IDs live via `list_channels` every run and never hardcode.

## Which mode

- **`--schedule`** for the pre-written, pre-reviewed, link-free atoms in the queue. `/atomize` already applied the voice and format rules when it wrote them; a second gate just recreates the manual step that killed this lane (2 posts shipped out of 15 in June). One confirm inside the batch-day block, then it ships itself.
- **Draft-only (default)** for anything new, rewritten in this session, or where you want to eyeball the rendering in Buffer first.

**Plan cap: 10 scheduled posts** (org-level, checked live 2026-07-26). Check headroom with `list_posts(status:["scheduled"])` before a large `--schedule` run and refuse to exceed it. Daily limits are not a constraint (LinkedIn 50/day, X 100/day).

## Model
- Voice guardrail: **no links in the body** (measured suppression - the URL goes in the first comment instead), engagement-prompt endings. **"Soft brand mention at most" is retired as of 2026-07-26** - it produced 13 consecutive atoms in which neither RoboLedger nor RoboSystems was ever named, including product posts that said "our system" and gave the reader nothing to reach. Name the product when the post is about the product, and say it is open source.
- **No em-dashes** in any generated X cut (repo-wide rule). Use a spaced hyphen or restructure.
- `schedulingType: "automatic"` always. Never `shareNow`.

## Steps

### 1. Parse the queue

Two formats. Both key off a `## N. <title> … status: <state>` heading; they differ in what follows.

**Atom format** (default, `drafts/atoms/personal.md` - written by `/atomize`). Carries a purpose-written cut per platform:
```
## N. <title>  ·  source: <subject>  ·  status: ready

**LinkedIn**
<fenced block = the LinkedIn body>

**X**
<fenced block = the X body>
```
Use each body **verbatim**. They were written natively per platform; do not regenerate the X cut from the LinkedIn one.

**Legacy format** (`drafts/thought-leadership/linkedin.md`): one fenced block after the heading, which is the LinkedIn body. The X cut has to be authored (step 3).

Extract `(N, title, status, linkedin_body, x_body_or_None)` either way.

### 2. List and select
Show the queue; default candidates = status NOT in (`posted`, `queued`, `scheduled`):
```
 # · title                                  · source · status   · LI/X chars
 1   The 14 rows that are actually decisions    fpa      ready      1106 / 307
 2   The check row that never stopped anything  fpa      ready      1109 / 337
 5   The line between actual and forecast       fpa      scheduled  -          (skip)
```
Take the selection from `$ARGUMENTS`, else ask which numbers.

### 3. Build LinkedIn + X for each selected, then PREVIEW (no writes)
- **LinkedIn** = the fenced body **verbatim**.
- **X** (unless `--no-x`): atom format already has one, use it verbatim. Legacy format needs one authored - keep the hook first line, tighten to X cadence, drop LinkedIn-only scaffolding, keep the question ending. Single post; Premium allows length but punchier wins.

Show both per post, state the mode and where each will land, and confirm once:
```
Mode: SCHEDULE -> explicit dueAt from POSTING_TIMES.md
Queue headroom: 4 scheduled of 10

Post 1, "The 14 rows that are actually decisions"
  LinkedIn (1106):  I counted the rows in our financial operating plan last week. 178. ...
  X (307):          I counted the rows in our operating plan. 178. ...
Schedule 2 atoms (4 items) to Joseph French + @JosephTFrench? (y/n)
```

### 4. Create (on confirm)
`get_account` for the org, `list_channels` for the linkedin + twitter ids, then per selected post:

- **`--schedule`**: `create_post(channelId=…, schedulingType:"automatic", mode:"customScheduled", dueAt=<computed>, text=…)`
- **default**: `create_post(channelId=…, schedulingType:"automatic", saveToDraft:true, text=…)`

**Never use `mode:"addToQueue"`.** Buffer's built-in slot grid cannot be edited through the API (no mutation exists) and its generated defaults are bad - LinkedIn at Mon 21:41 and Sun 22:17. Compute `dueAt` from **[`.claude/POSTING_TIMES.md`](../POSTING_TIMES.md)** instead: read the table, take the next unfilled slot per channel, and build ISO 8601 with the America/Chicago offset. That table is the single source of truth for timing and is tuned from `just insights` as data accumulates.

### 5. Mark the source
Update the `## N.` heading in the source queue so the same atom is not re-queued next run:
- `--schedule` → `status: scheduled (YYYY-MM-DD)`
- draft mode → `status: queued`

You mark `status: posted (date)` and drop the URL once it actually goes out. `just insights` picks up the reach later.

### 6. Report
```
Scheduled to Buffer (explicit times; nothing further to do):
   - Post 1: LinkedIn Mon 07:00 CT · X Mon 07:30 CT  ({id}, {id})
   - Post 3: LinkedIn Tue 07:00 CT · X Tue 07:30 CT  ({id}, {id})
Queue now 8 of 10.
```

## Notes
- **Idempotency**: `list_posts(status:["draft","scheduled"])` per channel; skip or `edit_post` if a matching first line already exists.
- **Do not mirror the same idea to both channels in the same slot.** Offset the X cut by at least a few hours, or run it the next day - the overlap in followers is real and simultaneous duplicates read as broadcast spam.
- Same pattern works for the launch-era standalone posts in `drafts/archive/` if you ever want to re-run proven copy: point step 1 at that file instead.
