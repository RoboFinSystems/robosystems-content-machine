Queue selected LinkedIn shorts from `drafts/thought-leadership/linkedin.md` to Buffer as **drafts** — LinkedIn plus a mirrored **X** cut. Draft-only (like `/buffer-draft`): you open Buffer and post, then mark the source post `posted`.

## Arguments
- `$ARGUMENTS` — optional selectors: post numbers (`1 3 8`), `all`, or a status (`ready`). Empty → list them and ask which.

## Model (shared with [[buffer-drafting]])
- **Draft-only, always** (`create_post(saveToDraft:true)`, `schedulingType:"automatic"`). Never schedule/publish.
- Channels: LinkedIn = connected *personal* profile; X = `robofinsystems` (X Premium, so long single posts are fine). Resolve IDs live via `list_channels`.
- Voice guardrail from the file's frontmatter: **no links, engagement-prompt endings, soft brand mention at most.** Preserve it — don't add blog/product links.

## Steps

### 1. Parse the queue
Read `drafts/thought-leadership/linkedin.md`. Each post is:
```
## N. <title>  ·  <Pillar>  ·  status: <drafting|ready|queued|posted (date)>
```
followed by a fenced ```` ``` ```` block = the post body. Extract `(N, title, pillar, status, body)` for each.

### 2. List + select
Show the queue; default candidates = status NOT in (`posted`, `queued`):
```
# · title                                   · pillar        · status    · chars
1   Events, not transactions                  2 Foundation    drafting    980
3   Information Blocks — pivot + author        2 Foundation    drafting    1120
6   Graph-native, AI-native close             1 Problem       posted      —      (skip)
…
```
Take the selection from `$ARGUMENTS`, else ask which numbers.

### 3. Build LinkedIn + X for each selected → PREVIEW (no writes)
- **LinkedIn** draft = the fenced body **verbatim**.
- **X** draft = author an X-native cut of the same idea: keep the hook first line, tighten to X cadence, drop LinkedIn-only scaffolding, keep the question ending. Single post (Premium, so length is flexible — but punchier is better). *(These queue posts have no `_x_post` cut, so we author one; if a sibling X cut ever exists, prefer it.)*

Show both per post and confirm before creating:
```
Post 1 — "Events, not transactions"
  LinkedIn (980):  Your general ledger isn't the source of truth. It's a derived artifact. …
  X (268):         Your GL isn't the source of truth — it's a derived artifact. …
Create LinkedIn + X drafts for the selected posts? (y/n)
```

### 4. Create the drafts (on confirm)
`get_account` → org; `list_channels` → linkedin + twitter ids. For each selected post create two drafts:
- LinkedIn: `create_post(channelId=linkedin, schedulingType:"automatic", saveToDraft:true, text=<body>)`
- X: `create_post(channelId=twitter, schedulingType:"automatic", saveToDraft:true, text=<x cut>)`

### 5. Mark the source as queued (offer)
So the same post isn't re-drafted next run, offer to update its heading in `linkedin.md`: `status: drafting` → `status: queued` for each drafted post (Edit the `## N.` line). The user marks `status: posted (date)` + drops the URL after they actually post from Buffer.

### 6. Report
```
✅ Drafted to Buffer (post at https://publish.buffer.com, then mark posted in linkedin.md):
   • Post 1 — LinkedIn + X  (drafts {id}, {id})
   • Post 3 — LinkedIn + X  (drafts {id}, {id})
```

## Notes
- **Idempotency**: `list_posts(status:["draft"])` per channel; skip/`edit_post` if a matching first line already exists.
- Same pattern works for the launch-era standalone posts in `drafts/archive/` if you ever want to re-run proven copy — point step 1 at that file instead.
