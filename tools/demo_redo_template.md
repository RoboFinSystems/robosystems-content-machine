# Redo: {EPISODE} v{NEXT}

This run remakes the episode from its outline. `just demo-redo` archived v{N} to
`.history/v{N}/`: its renders, audio, walkthrough specs and outline.

**Do not open anything in `.history/`.** A redo is built fresh against the current frame,
templates and motion rules, not edited from the old cut. Reading the old outline or specs
anchors the new one to their structure and phrasing.

**Take from v{N} only `LOVES-HATES.md`.** Every note in it is binding: keep what it says
works, fix what it says does not. If it is empty, stop and ask for the notes before writing
anything. If `.history/v{N}/REDO.md` exists, it was hand-written notes from the last run: ask
whether its lasting lessons belong in `LOVES-HATES.md` or `showcase/mcp_series/recording.md`,
and do not read it for structure.

## What you write, from scratch

1. `OUTLINE.md` from `template/SHOWCASE_OUTLINE.md`: the frame, the spine, and the narration
   beat by beat. Get the words approved read aloud before anything else.
2. The walkthrough spec(s) for the live beats, with a `cue` on every action the narration names.
3. The data for each motion shot (`just motion-template`).

Then:

1. `just demo-narrate`, then `just demo-align`.
2. `just demo-stills` for the fit check.
3. `just demo-pipeline` for the render.
4. `just demo-pops` on everything.

Hand over stills and a short note of what changed against LOVES-HATES before the full cut.
