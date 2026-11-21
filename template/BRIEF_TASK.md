# TASK - {TICKER} research brief ({TIER} tier)

Written by `/batch-research` on {WRITTEN}, batch `{BATCH}`. You are one subagent of a batch: you author **one**
brief, for **{TICKER}** ({COMPANY}), in `projects/{TICKER}/`. Other subagents are writing other
tickers at the same time.

## Scope
- Touch only files under `projects/{TICKER}/`. Never read or write another ticker's folder.
- Text only. Do not publish, post, push, upload, render or narrate; do not run `just publish*`,
  `just narrate`, or any git command that changes state.
- Do not read `.history/`, `.partial/`, any `_archive/` folder, `KICKOFF.md`, or any older brief,
  script, deck, webdeck or social copy for {TICKER}. Do not read the published page on
  roboinvestor.ai or its CDN copy.
- `sources/_prior_coverage.md`, when it exists, stays closed until your brief is drafted.

## The filing
- {FORM}, period ended {PERIOD_END}, filed {FILED}, accession `{ACCESSION}`, CIK `{CIK}`.
- In xbrlkit, load it as `{CIK}:{ACCESSION}` with `filing_id: "{TICKER_LOWER}-current"`, and confirm
  the period end in the receipt before reading a number.
- **The xbrlkit server is shared with the other subagents.** Pass `filing` on every call, and
  never unload a filing you did not load.
- Coverage: {COVERAGE}.

## What to do
Follow `projects/{TICKER}/AUTHORING_INSTRUCTIONS.md`, section "Research method" first, at the
**{TIER}** tier. In short:
1. The web pass, written to `sources/_web_research.md` before any drafting.
2. The filing research, with `robosystems-sec` to research and `xbrlkit` to verify.
3. Checks A to D (and E on the deep tier).
4. Name the coverage frame and lead with what the filing shows that it misses.

Deliverables, three only:
1. `reports/{TICKER}_brief.md`
2. `social/{TICKER}_x_post.txt`
3. `social/{TICKER}_publish.json` (with `company`, and `coverage_label` on continuing coverage)

No video script, short or YouTube description. Finish with `just validate-brief {TICKER}` and fix
until it passes.

## Hard rules
- Every number about {COMPANY}'s own results, balance sheet, commitments or segments comes from
  an SEC filing and is verified in xbrlkit before it goes in the Hook, a table or the Bottom Line.
- Web material appears only with its source named and dated in the sentence, never as the basis
  for a figure about the company's own financials.
- Charged is not paid: income tax expense is an accrual, income tax paid is cash.
- No em-dashes or en-dashes, and no `<` or `>`, anywhere.
- An early ` ${TICKER}` cashtag in the Hook, space-preceded, never `(${TICKER})`; exactly one
  cashtag in the X post.
- The generalization beat in the Bottom Line, then the `*Ask the filing yourself:*` line. Run the
  prompt's underlying query yourself and confirm it returns the number.
- No promo codes, no product price, never "free tier" or "free plan".

## Status: `projects/{TICKER}/STATUS.md`
Rewrite it at the start and at every stage change, in this shape:

```
ticker: {TICKER}
stage: research | drafting | validating | COMPLETE | stopped
tier: {TIER}
batch: {BATCH}
filing: {FORM} {PERIOD_END} {ACCESSION}
started: <date "+%Y-%m-%d %H:%M">
finished: <the same, at COMPLETE>
angle: <one line, once you have one>
validate: <the RESULT line>
blocked_on: none
```

At COMPLETE, add these sections below the lines above:
1. **Angle**: the coverage frame in one line, and what the filing shows that it misses.
2. **What each step added**: the web pass and checks A to D, one line each ("nothing" where true).
3. **Web claims in the brief**: each with source and date.
4. **Not verified**: any figure you could not check in xbrlkit, and why.
5. **Prior coverage** (continuing coverage only): a different story, or the same story with new
   numbers? Say which, honestly.
6. **Instruction problems**: anything unclear, stale or contradictory, with file and section.

The lead reads only `stage` and these sections, so keep them short.
