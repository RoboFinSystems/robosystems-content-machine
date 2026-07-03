Queue selected LinkedIn shorts from `drafts/thought-leadership/linkedin.md` to Buffer as **drafts**: LinkedIn plus an optional mirrored **X** text cut (posting X in parallel with LinkedIn is fine here, because these are text posts with no video and no Article). Draft-only: you open Buffer and post, then mark the source post `posted`.

LinkedIn is the primary channel for this content. The X mirror is a text cut only. Buffer cannot put long video or an X Article on X (those are native-only), but that never bites here because these posts are pure text. See [[buffer-drafting]] for the channel reality.

## Arguments
- `$ARGUMENTS` - optional selectors: post numbers (`1 3 8`), `all`, or a status (`ready`). Empty lists them and asks which. Add `--no-x` to draft LinkedIn only.

## Model
- **Draft-only, always** (`create_post(saveToDraft:true)`, `schedulingType:"automatic"`). Never schedule/publish.
- Channels: LinkedIn = connected personal profile; X = `robofinsystems`. Resolve IDs live via `list_channels`.
- Voice guardrail from the file's frontmatter: **no links, engagement-prompt endings, soft brand mention at most.** Preserve it, do not add blog/product links.

## Steps

### 1. Parse the queue
Read `drafts/thought-leadership/linkedin.md`. Each post is:
```
## N. <title>  ·  <Pillar>  ·  status: <drafting|ready|queued|posted (date)>
```
followed by a fenced ```` ``` ```` block, the post body. Extract `(N, title, pillar, status, body)` for each.

### 2. List and select
Show the queue; default candidates = status NOT in (`posted`, `queued`):
```
# · title                                   · pillar        · status    · chars
1   Events, not transactions                  2 Foundation    drafting    980
3   Information Blocks, pivot + author         2 Foundation    drafting    1120
6   Graph-native, AI-native close             1 Problem       posted      -      (skip)
...
```
Take the selection from `$ARGUMENTS`, else ask which numbers.

### 3. Build LinkedIn + X for each selected, then PREVIEW (no writes)
- **LinkedIn** draft = the fenced body **verbatim**.
- **X** draft (unless `--no-x`) = author an X-native text cut of the same idea: keep the hook first line, tighten to X cadence, drop LinkedIn-only scaffolding, keep the question ending. Single post (the account is X Premium, so length is flexible, but punchier is better).

Show both per post and confirm before creating:
```
Post 1, "Events, not transactions"
  LinkedIn (980):  Your general ledger isn't the source of truth. It's a derived artifact. ...
  X (268):         Your GL isn't the source of truth, it's a derived artifact. ...
Create LinkedIn + X drafts for the selected posts? (y/n)
```

### 4. Create the drafts (on confirm)
`get_account` for the org, `list_channels` for the linkedin + twitter ids. For each selected post create the drafts:
- LinkedIn: `create_post(channelId=linkedin, schedulingType:"automatic", saveToDraft:true, text=<body>)`
- X: `create_post(channelId=twitter, schedulingType:"automatic", saveToDraft:true, text=<x cut>)`

### 5. Mark the source as queued (offer)
So the same post is not re-drafted next run, offer to update its heading in `linkedin.md`: `status: drafting` -> `status: queued` for each drafted post (Edit the `## N.` line). The user marks `status: posted (date)` and drops the URL after they actually post from Buffer.

### 6. Report
```
Drafted to Buffer (post at https://publish.buffer.com, then mark posted in linkedin.md):
   - Post 1: LinkedIn + X  (drafts {id}, {id})
   - Post 3: LinkedIn + X  (drafts {id}, {id})
```

## Notes
- **Idempotency**: `list_posts(status:["draft"])` per channel; skip or `edit_post` if a matching first line already exists.
- Same pattern works for the launch-era standalone posts in `drafts/archive/` if you ever want to re-run proven copy: point step 1 at that file instead.
