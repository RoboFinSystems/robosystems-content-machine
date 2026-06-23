# 9:16 Short — visual template

The reusable design system for vertical (9:16) Shorts. Designed once in Claude Design,
then codified into the automated renderer (`tools/assemble_short.py` v2) so each Short is
generated per company from the `short` block — no per-episode design step.

- **`short_9x16_template.pdf`** — the Claude Design export: one page per frame archetype
  (hook, hero-number, paradox, identity, two chart styles, bull/bear, running-caption
  style, end/CTA, safe-zone reference), with tokens + motion intent annotated.
- Brief that produced it: `local/short_9x16_design_brief.md`.

Frame archetypes map to render-time tokens (`{{HOOK_LINE}}`, `{{HERO_NUMBER}}`,
`{{FACT_A/B}}`, `{{COMPANY}}/{{TICKER}}/{{EXCHANGE}}`, `{{SERIES[]}}`, `{{BULL[]}}/{{BEAR[]}}`,
`{{CAPTION_TEXT}}`, `{{CTA_LINE}}`, `{{HANDLE}}`) that v2 fills from the script's `short` block.
