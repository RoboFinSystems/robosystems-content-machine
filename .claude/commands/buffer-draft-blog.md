Queue a blog post's **LinkedIn + X native cuts** to Buffer as **drafts** (draft-only, like `/buffer-draft`). These are the no-canonical, no-in-body-link short derivatives of a `blog/<slug>/` essay — the essay itself publishes via `just blog-publish`. You post the drafts from Buffer yourself.

## Arguments
- `$ARGUMENTS` — the blog slug (e.g. `the-coverage-machine`), plus optional `--linkedin-only` / `--x-only`.

## Model (shared with [[buffer-drafting]])
- **Draft-only, always** — `create_post(saveToDraft:true)`, never schedule/publish. You open Buffer and post.
- Channels: LinkedIn = the connected *personal* profile; X = `robofinsystems`. Resolve IDs live via `list_channels`, never hardcode.
- X requires `schedulingType:"automatic"` (it rejects `notification`); harmless for drafts.

## Steps

### 1. Locate the post + its cuts
```bash
SLUG={SLUG}; d=blog/$SLUG
ls -la $d/${SLUG}_linkedin.md $d/${SLUG}_x_post.txt 2>/dev/null
```
- The LinkedIn cut `blog/<slug>/<slug>_linkedin.md` = the post body verbatim (strip a leading blank line / any frontmatter).
- The X cut `blog/<slug>/<slug>_x_post.txt` = usually a **thread**, delimited by `**N/**` markers.
- If **neither** exists → the cuts aren't authored yet; tell the user to write them (or `just blog-social {SLUG}` once cuts exist) and stop. If only one exists, draft that one.

### 2. Parse the X thread
Split `_x_post.txt` on the `**N/**` markers into ordered items; **strip the `**N/**` markers** (they're delimiters, not tweet text). Each item's remaining text = one tweet. If there are no markers, treat the whole file as a single post. Keep any 🧵/emoji that are part of the copy.

### 3. Preview (no writes) → confirm
```
Blog → Buffer drafts: {SLUG}  (org: Harbinger FinLab, mode: draft)
  LinkedIn  1 post   {N} chars   "There are thousands of public companies…"
  X         thread   {k} tweets  1/ "There are thousands of public companies…"
Create these drafts? (y/n)
```

### 4. Create the drafts (on confirm)
`get_account` → org; `list_channels` → linkedin + twitter ids. Then:
- **LinkedIn** — `create_post(channelId=linkedin, schedulingType:"automatic", saveToDraft:true, text=<linkedin body>)`.
- **X thread** — `create_post(channelId=twitter, schedulingType:"automatic", saveToDraft:true, text=<item 1 text>, metadata:{twitter:{thread:[{text:item1},{text:item2},…]}})`. The outer `text` MUST equal the first thread item (Buffer requirement).

### 5. Report
```
✅ Drafted to Buffer (post them at https://publish.buffer.com):
   • LinkedIn — {SLUG}  (draft {id})
   • X thread — {SLUG}, {k} tweets  (draft {id})
Note: the blog essay itself goes live via `just blog-publish {SLUG}`. These social cuts carry no in-body blog link by design.
```

## Notes
- **Idempotency**: `list_posts(status:["draft"])` on each channel; if a draft with matching first line already exists, offer to skip or `edit_post` rather than duplicate.
- The narration → YouTube path (audio+cover video) is a separate, heavier build — not part of this skill (deferred pending a cover-card design).
