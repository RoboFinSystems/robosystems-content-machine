---
description: Quality review of authored output before running the pipeline.
argument-hint: '[project...]'
---

Quality gate between authoring and rendering. Catch problems here, where a fix is an edit,
rather than after a 15-20 minute render.

## Arguments
- `$ARGUMENTS` — one or more ticker symbols (e.g. `STX`, or `FDXF PTON STX RELL`)

Run every step for each ticker. For a multi-ticker batch, prefer one consolidated table over
repeating the whole report per name.

## Steps

### 1. Run the validator
```bash
just validate {TICKER}
```
A thumbnail warning is expected before `just thumbnails` runs. Anything else needs explaining.

### 2. Read the brief
`projects/{TICKER}/reports/{TICKER}_brief.md` ships **verbatim as the X Article**, so it is the
highest-stakes artifact. Show at minimum the H1 and the hook. Check:
- Does the hook lead with a specific number and a real tension?
- Is the tone fact-based rather than promotional?
- Is every claim traceable to the filing, with nothing sourced from press coverage?
- Is the **generalization beat** present near the close (no analyst wrote this; the same pipeline
  runs on any SEC filer)? Ending at the ticker conclusion is the recurring miss.

### 3. Verify the load-bearing numbers against the filing (xbrlkit)

The validator cannot tell whether a number is *true*, only whether it looks suspicious. Do that
here, where the filing is one call away.

```
load_filing  {source: "{TICKER} 10-K"}     # a plain ticker resolves stale symbols on its own
fact_grid    {elements: [...], period_type: "duration"}
```

Confirm every figure that carries weight: whatever is in the hook, on a slide, or in the thesis.
Pull the whole set in ONE `fact_grid` call rather than one call per number.

**The tax pair is mandatory whenever tax is part of the story.** Pull
`us-gaap:IncomeTaxExpenseBenefit` (charged, an accrual) and `us-gaap:IncomeTaxesPaidNet` (paid,
cash) together, then check the brief uses the right word for each. This is the single most
repeated defect in published work: six names asserted "paid" over an expense figure and
overstated by up to 143x. Treat **"paid or accrued" as a failure, not a hedge** - it reads as
"paid" to a viewer.

Where the two diverge, find where the gap went: `us-gaap:UnrecognizedTaxBenefits` as an instant,
sized against the cash balance. Then run `disclosures {topic: "income tax"}` and check whether
the filer tagged a jurisdiction-level cash-tax table. If they did, read it: the consolidated
total hides which government actually got paid.

**Report each number as confirmed against the filing, or as a mismatch with the filing's value.
Never report a number as checked unless you actually queried it** - repeating the brief's own
figure back is how the original error survived review.

### 4. Mechanical checks (script these, do not eyeball)
| Check | Rule |
|---|---|
| Brief H1 length | **≤ 100 chars.** Over-long returns a valid-looking draft id that was never persisted, and fails later with a misleading "not found or not owned" |
| Cashtag in hook | space-preceded ` $TICKER`, never `($TICKER)` |
| Cashtags per X post | **exactly 1.** X allows one cashtag per post; demote any second ticker or ETF to a hashtag |
| Em/en dashes | **zero** in every deliverable. (`template/blog/post.md` has two in its placeholder text — scaffold, not authored, safe to ignore) |
| Duplicate `visual_ref` | none |
| `cta` segment | present |

### 5. Script and short summary
From `scripts/{TICKER}_script.json` and `scripts/{TICKER}_short_script.json`:
- segment count, narration word count, estimated duration (≈ narration chars ÷ 16)
- breakdown by `visual_type` (title / chart / callout / dual)
- short: beat count and estimated seconds (**target ~45s**)

Long-form running past the 3-5 minute guide is a judgment call, not an error. Say so and let the
user decide.

### 6. Narration TTS spot-check
Look for raw symbols (`$ % x /`) that should be spoken, numbers not rounded for speech, and
sentences over ~45 words.

**Do not flag spaced capitals as defects.** `S E C` and `X B R L` are deliberate TTS respellings
so ElevenLabs says the letters rather than "sek" and "ex-brl", the same convention as
`EBITDA → Ebit-dah`. Flagging these as errors is a false positive.

### 7. Print a summary and offer to fix
Report per ticker: validator, segments, duration, brief words, H1 length, X post chars, and the
count of real issues. Then:

```
Ready for pipeline?
→ just webdeck-pipeline {TICKER}     (long-form)
→ just webdeck-short-pipeline {TICKER}   (9:16 short)
```

Do **not** auto-fix. The user has creative discretion over content.

## After the render — the step that actually catches defects
`validate` is schema-level and has repeatedly passed decks that were visually broken. Multiple
defects have shipped past every automated gate and been caught only by extracting frames.

**Frame-check every slide via a contact sheet, never a sample.** A single-still fit-check takes
about ten seconds against a fifteen-minute render, so it is always worth it after any template
change.

Renders are local (puppeteer-core + ffmpeg) and cost nothing but wall clock. Run them detached
with `nohup … & disown`; the harness SIGTERMs foreground commands long before a render finishes,
and macOS has no `setsid`.
