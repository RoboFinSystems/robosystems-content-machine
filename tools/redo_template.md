# Redo: {TICKER} video v{NEXT}

This run remakes the **video**, not the research. `just redo` archived video v{N} to
`.history/video-v{N}/` and left the brief where it is.

**Do not open anything in `.history/`.** The point of a redo is a video built fresh from the
brief with the current slide kinds and motion, not an edit of the old one. Reading the old
script anchors the new one to its structure, its beats and its phrasing.

**Take from v{N} only `LOVES-HATES.md`.** Every note in it is binding: keep what it says
works, fix what it says does not. If it is empty, stop and ask for the notes before you
write anything.

## What stays

- `reports/{TICKER}_brief.md` is the primary document and is already published. Do not
  change it. It is the source for every claim and number in the video: if a figure is not
  in the brief, verify it against the filing over MCP before it goes on screen.
- `sources/` as it is.

## What you write, from scratch

Per `AUTHORING_INSTRUCTIONS.md` and `PRODUCTION_CONTRACT.md` (both refreshed to the current
versions by `just redo`), skipping the brief:

1. `scripts/{TICKER}_script.json`: the long-form. Plan the beats from the brief afresh.
   Give chart, table, card and dual slides `cues` wherever an element's label is not the
   word the narration uses for it, so the deck builds each one as it is spoken.
2. The video-facing copy in `social/`: `{TICKER}_youtube_description.txt`, and in
   `{TICKER}_publish.json` the `youtube_title`, `seo_description` and `youtube_comment`.
   Leave the brief's fields (`x_first_comment`) as they are.

No 9:16 short: the lane stopped making them (a poor fit for this content, and each upload
spends YouTube quota).

The thumbnail in `charts/png/` stays: it is also the published brief's card. Make a new one
only if the notes ask for it (`just thumbnails {TICKER}`).

Then `just validate {TICKER}`, and render stills of the first slides for review before the
full pipeline. After the new upload, `just sync-youtube {TICKER}` points the research page at
v{NEXT}; unlisting v{N} on YouTube is a manual step.
