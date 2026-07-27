Queue selected LinkedIn shorts from `drafts/thought-leadership/linkedin.md` to Buffer: a LinkedIn post plus an optional mirrored **X** text cut (posting X in parallel with LinkedIn is fine here, because these are text posts with no video and no Article).

**Two modes.** `--schedule` (the batch-day mode) drops the posts straight into Buffer's queue so the week ships without a second visit. Default is draft-only, which needs you to open Buffer and press post per item. See "Which mode" below - picking wrong is how this lane stalled in June.

LinkedIn is the primary channel for this content. The X mirror is a text cut only. Buffer cannot put long video or an X Article on X (those are native-only via `just x-post` / `x-short` / `x-article`). That never bites here because these posts are pure text. See [[buffer-drafting]] for the channel reality.

## Arguments
- `$ARGUMENTS` - optional selectors: post numbers (`1 3 8`), `all`, or a status (`ready`). Empty lists them and asks which.
- `--schedule` - add to the Buffer queue instead of saving drafts. **This is the batch-day default.**
- `--no-x` - LinkedIn only.

## Channels (verified live 2026-07-26)

Buffer org **Harbinger FinLab** (`6a4710d8f9144a22713ee87e`) has exactly two channels, **both personal**:

| Service | Account | Notes |
|---|---|---|
| `linkedin` | **Joseph French** (`josephtfrench`) | personal profile, posting goal 5/week |
| `twitter` | **@JosephTFrench** | personal, X Premium (long text OK) |

**@RoboFinSystems is NOT in Buffer.** It posts through the direct X API (`just x-post` / `x-short` / `x-article`). Earlier versions of this file wrongly named the Buffer X channel `robofinsystems`; anything drafted through it went to the personal account. Resolve IDs live via `list_channels` every run and never hardcode.

## Which mode

- **`--schedule`** for the pre-written, pre-reviewed, link-free shorts in `linkedin.md`. They already passed editorial review when they were written; a second gate just recreates the manual step that killed this lane (2 posts shipped out of 15 in June). One confirm inside the batch-day block, then it ships itself.
- **Draft-only (default)** for anything new, rewritten in this session, or where you want to eyeball the rendering in Buffer first.

**Plan cap: 10 scheduled posts.** A weekly batch of 3 to 5 per channel fits comfortably; you cannot queue a month ahead. Check headroom with `list_posts(status:["scheduled"])` before a large `--schedule` run and say so if the selection would exceed it.

## Model
- Voice guardrail from the file's frontmatter: **no links, engagement-prompt endings, soft brand mention at most.** Preserve it; do not add blog or product links.
- **No em-dashes** in any generated X cut (repo-wide rule). Use a spaced hyphen or restructure.
- `schedulingType: "automatic"` always. Never `shareNow`.

## Steps

### 1. Parse the queue
Read `drafts/thought-leadership/linkedin.md`. Each post is:
```
## N. <title>  ·  <Pillar>  ·  status: <drafting|ready|queued|scheduled|posted (date)>
```
followed by a fenced ```` ``` ```` block, the post body. Extract `(N, title, pillar, status, body)` for each.

### 2. List and select
Show the queue; default candidates = status NOT in (`posted`, `queued`, `scheduled`):
```
# · title                                   · pillar        · status    · chars
1   Events, not transactions                  2 Foundation    ready       980
3   Information Blocks, pivot + author         2 Foundation    ready      1120
6   Graph-native, AI-native close             1 Problem       posted      -      (skip)
```
Take the selection from `$ARGUMENTS`, else ask which numbers.

### 3. Build LinkedIn + X for each selected, then PREVIEW (no writes)
- **LinkedIn** = the fenced body **verbatim**.
- **X** (unless `--no-x`) = an X-native cut of the same idea: keep the hook first line, tighten to X cadence, drop LinkedIn-only scaffolding, keep the question ending. Single post; Premium allows length but punchier wins.

Show both per post, state the mode and where each will land, and confirm once:
```
Mode: SCHEDULE -> Buffer queue (LinkedIn 2 slots/day, X 4 slots/day)
Queue headroom: 4 scheduled of 10

Post 1, "Events, not transactions"
  LinkedIn (980):  Your general ledger isn't the source of truth. It's a derived artifact. ...
  X (268):         Your GL isn't the source of truth, it's a derived artifact. ...
Schedule 2 posts (4 items) to @JosephTFrench + Joseph French? (y/n)
```

### 4. Create (on confirm)
`get_account` for the org, `list_channels` for the linkedin + twitter ids, then per selected post:

- **`--schedule`**: `create_post(channelId=…, schedulingType:"automatic", mode:"addToQueue", text=…)`
- **default**: `create_post(channelId=…, schedulingType:"automatic", saveToDraft:true, text=…)`

Buffer fills queue slots from the channel's posting schedule in order, so a batch spreads itself across the week without any `dueAt` math. Only reach for `mode:"customScheduled"` + `dueAt` (ISO 8601 with the America/Chicago offset) when a post has to land on a specific day.

### 5. Mark the source
Update the `## N.` heading in `linkedin.md` so the same post is not re-queued next run:
- `--schedule` → `status: scheduled (YYYY-MM-DD)`
- draft mode → `status: queued`

You mark `status: posted (date)` and drop the URL once it actually goes out. `just insights` picks up the reach later.

### 6. Report
```
Scheduled to Buffer (spreads across the week's slots; nothing further to do):
   - Post 1: LinkedIn Mon 21:41 · X Mon 08:19  ({id}, {id})
   - Post 3: LinkedIn Tue 21:12 · X Tue 08:48  ({id}, {id})
Queue now 8 of 10.
```

## Notes
- **Idempotency**: `list_posts(status:["draft","scheduled"])` per channel; skip or `edit_post` if a matching first line already exists.
- **The LinkedIn slots are Buffer's random defaults and several are bad** - Mon 21:41, Tue 21:12, Sun 22:17 are dead air for B2B. Fix them in Buffer to weekday mid-morning / lunch, then this skill inherits the better times automatically. X (08:00-12:00 CT) is fine.
- Same pattern works for the launch-era standalone posts in `drafts/archive/` if you ever want to re-run proven copy: point step 1 at that file instead.
