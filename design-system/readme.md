# RoboSystems Content Design System

A brand + content design system for **RoboSystems** — purpose-built for the
**RoboSystems Content Machine**: the automated pipeline that turns a company's SEC
filings into narrated research **videos**, vertical **shorts**, two-voice **podcasts**,
**blog essays**, and **social posts**.

The base [RoboSystems app design system](#sources) is engineered for a web product
(Flowbite + Tailwind, app chrome, settings forms). **This system is different**: it
re-frames the same brand for *content production* — 16:9 decks, 9:16 shorts, YouTube
thumbnails, long-form blog posts, and X/social cards. Same fonts, same blue, same logo;
a vocabulary aimed at slides and stories instead of app screens.

> **House brand: RoboSystems (blue). Dark-first. Orbitron display + Space Grotesk body.**
> Accent color for the one thing that matters per slide. Eyebrow section labels
> (`01 / THE PAIN`). Subtle source-attribution footers. Every number verbatim from filings.

---

## Sources

This system was reverse-engineered from materials the user provided. You may not have
access, but they are recorded here so you (or a teammate who does) can go deeper:

- **`robosystems-app/`** (codebase) — the production Next.js app. The brand truth lives in
  `src/app/globals.css` (the `@theme` primary-blue override + `@font-face` rules) and
  `src/lib/core/.ds-compiled.css` (the full Flowbite/Tailwind palette + `--blue-*`, `--gray-*`
  tokens). A pre-built design-system bundle sits in `ds-bundle/` (Orbitron + Space Grotesk
  TTFs, app component previews).
- **`robosystems-content-machine/`** (codebase) — the content pipeline this system serves.
  Key reads: `template/DESIGN_INSTRUCTIONS.md` (how decks + thumbnails are built),
  `template/PRODUCTION_CONTRACT.md` (the script → deck → video contract, TTS rules, slide
  kinds), `blog/*/post.md` (published essays), and `projects/<TICKER>/deck/*_deck_brief.md`
  (real per-video briefs, e.g. `GTBIF`).
- **GitHub:** [RoboFinSystems/robosystems-content-machine](https://github.com/RoboFinSystems/robosystems-content-machine)
  — the open pipeline (MIT). Explore it to understand how these artifacts are produced and
  assembled. Related: [RoboSystems platform](https://github.com/RoboFinSystems/robosystems),
  product site [robosystems.ai](https://robosystems.ai).

**Font substitution flag:** Orbitron + Space Grotesk are the real brand TTFs (bundled here,
OFL). The brand's monospace (`JetBrains Mono`, used for code/tickers) was **not** shipped as a
file in the codebase — it is loaded from Google Fonts via `fonts.css`. Swap in the licensed
file if you have it.

---

## What RoboSystems is

RoboSystems is an **open-source financial knowledge-graph platform**. It ingests SEC XBRL
filings for every public company into per-company graph databases (LadybugDB), then exposes
them to AI agents via MCP tools — so an analyst (or Claude) can query revenue, margins,
balance-sheet, and segment data straight from the source filings. Products in the family:
**RoboLedger** (AI controller over QuickBooks), **RoboInvestor**, and the **Content Machine**
that this design system dresses.

The throughline of all RoboSystems content: **structure beats spreadsheets.** Money flows
through networks, not rows; the brand's job is to make that argument credibly, with every
number traceable to a filing.

---

## CONTENT FUNDAMENTALS — how RoboSystems writes

The voice is **the sharp equity analyst who shows their work** — confident, contrarian,
numerate, and scrupulously honest about what is and isn't a recommendation. Two registers
share one brand voice:

**1. Research / video / social (punchy, declarative).**
- **Hooks are confrontational and specific.** Real openers: *"Every Financial System Today Is
  Built on a Lie."* · *"We covered it. Here's what changed."* · *"Nobody covers this $1.2B company."*
- **The number is the protagonist.** Lead with the cognitive-dissonance figure (a 76% tax
  rate, an 8x adjusted P/E, $92M/yr penalty), then explain it. Never bury the metric.
- **Honest framing, always.** Bull case *and* bear case. Explicit disclaimers: *"Not investment
  advice. No price targets. Every number from the filings."* — this is non-negotiable and part
  of the brand's credibility.
- **Person:** "we" for RoboSystems' own conviction ("We covered Green Thumb at $6.67"); "you"
  to challenge the reader ("try answering it. You'll need data from five systems").
- **Casing:** Title Case or Sentence case for headlines; **eyebrow labels are UPPERCASE**
  (`COVERAGE UPDATE`, `01 / THE PAIN`). Tickers always `$GTBIF` / `NYSE: TRLV`.
- **Em-dashes and colons** drive the rhythm. Short sentences. Then a longer one that lands the
  point. Bulleted metric stacks (`• FY2025 revenue $1.18B (+3.4%)`).

**2. Long-form blog (essayistic, still bold).**
- Bigger ideas, manifesto energy: *"This Is Not a Pitch. It's a Warning."* Section headers
  are full sentences. Argues from first principles, then drives to the product.
- Closes on a turn — a takeaway or a dare, often two short bold lines:
  *"The future of finance isn't in better spreadsheets. / It's in understanding relationships."*

**Vibe:** technical credibility meets editorial swagger. Think a top-tier equity research note
crossed with a confident product manifesto. **No emoji** in the analysis itself (an occasional
🎙️/📊 appears in pipeline READMEs, never in published research). No hype words without a number
behind them. Precision is the flex.

**Spoken-form rule (narration only):** anything narrated by TTS spells symbols out — `$1.2B` →
"one point two billion dollars", `76%` → "76 percent", `P/E` → "price to earnings", `SEC` →
"S E C", and `AI` stays `AI` (never spaced). See `PRODUCTION_CONTRACT.md`. On-screen text keeps
the symbols; only the voice track is respelled.

---

## VISUAL FOUNDATIONS

**The signature look: a dark navy "stage."** RoboSystems content lives on a near-black,
blue-tinted canvas (`--ink-900` #0a0e1a) — the backdrop for decks, thumbnails, shorts, and
video frames. It reads as a Bloomberg-terminal-meets-spacecraft surface: serious, technical,
high-contrast. A light surface (`[data-surface="light"]`) exists for blog posts and written
reports.

- **Color.** One brand **blue** (`--blue-500` #3b7af5, hover #2563eb), a deep navy ink
  (`#1b3a57` / `#172e47`), and a cool gray ramp. Data uses a strict signal language: **green =
  positive, red = negative, brand-blue = neutral/current, amber = warning.** A **graph teal**
  (`#00d4aa`) is the one non-blue accent, reserved for "structure"/knowledge-graph moments,
  code, and prose links. Color is rationed — most of a slide is ink + white text; the accent
  marks the single thing that matters.
- **Type.** **Orbitron** (geometric, techy, wide) for display headlines, eyebrow labels, and
  big numbers — it *is* the "machine" in RoboSystems. **Space Grotesk** for everything else
  (body, captions, tabular data). **JetBrains Mono** for tickers, code, and query snippets.
  Eyebrows are UPPERCASE Orbitron with wide `0.22em` tracking; hero numbers are Orbitron 700–900.
- **Backgrounds.** Not flat — a restrained **radial brand glow** anchored top-center
  (`--bg-stage-glow`), and a faint **dot-grid lattice** (`--bg-grid`, knowledge-graph texture)
  on some surfaces. No photographic imagery in research decks (data is the hero); blog covers
  may use abstract renders. Graph-teal corner washes mark structure slides. Never busy — the
  glow is felt, not seen.
- **Animation.** Restrained and confident — **no bounce on content**. Slide reveals fade-and-rise
  ~16px on a signature `cubic-bezier(0.16, 1, 0.3, 1)` ease over ~640ms. The app's marketing
  uses slow floating ambient shapes (6–10s) and a pulsing gradient text; content keeps motion
  to entrance reveals. Always degrade to the end-state for print/PDF/reduced-motion.
- **Hover / press.** Interactive UI: hover lifts to the lighter accent (`--accent-hover`) or
  raises a card's elevation + inset ring; press shifts to the darker accent (`--accent-press`)
  with a tiny 1px settle (no large scale). Links underline on hover.
- **Borders & cards.** Cards on dark are `--surface-card` (#131b30) with a **1px hairline**
  (`--ink-700`) *and* a subtle inset white ring (`--ring-inset`) — the "etched panel" look,
  not a drop-shadow card. Radii are moderate: 10–20px for cards, pill for tags/badges. Shadows
  on dark are deep + soft (never harsh); light surfaces use soft `rgba(16,24,40,…)` shadows.
- **Transparency & blur.** Used sparingly — overlay scrims and the occasional frosted header.
  Eyebrow numerals and watermarks sit at low-opacity (`--text-faint`).
- **Layout.** 16:9 1920×1080 slides with a generous safe margin (`--slide-pad-x` 140px); 9:16
  1080×1920 shorts. Lots of negative space on title slides; data slides use a clear headline →
  eyebrow → data → source-footer stack. A persistent small RoboSystems mark + source line
  anchors the corner.
- **Imagery vibe.** Cool, dark, technical. When imagery appears, it's abstract/structural
  (graph lattices, data viz) rather than people or stock photos — the numbers carry the story.

---

## ICONOGRAPHY

- **The brand mark.** An abstract glyph (`assets/robosystems_mark.svg`, white variant
  `robosystems_mark_white.svg`, PNG `robosystems_logo_72.png`): a **trio of connected graph
  nodes** above a **ledger/∞ form** — the knowledge-graph-over-the-books idea. The SVG uses
  `fill="currentColor"`, so it recolors to any token (`color: var(--accent)` or white on dark).
  Always give it clear space; never stretch or recolor into a gradient.
- **UI icons.** The base app uses **Flowbite's icon set** (and `flowbite-react`) — thin,
  rounded-join, ~1.5–2px stroke line icons. There is **no bundled brand icon font**. For
  content work, match that weight with **[Lucide](https://lucide.dev)** (CDN), which is
  stroke-compatible (2px, round caps/joins) — used in this system's components. *This is a
  documented substitution:* the app ships Flowbite SVGs inline rather than a font; Lucide is the
  closest freely-CDN-available match for new content. Keep icons monochrome (`currentColor`),
  sized 16/20/24, and decorative-only in decks (the data leads).
- **Emoji.** **Not used in published research or on slides.** Pipeline/tooling READMEs use a few
  (🎙️ 📊) as wayfinding; published content does not. Don't add emoji to brand artifacts.
- **Partner / source logos.** `assets/sec.png`, `quickbooks.svg`, `claude.svg` — used in
  "built with / sourced from" footers. Product sub-brand logos: `roboledger.png`,
  `roboinvestor.png`.
- **No hand-drawn SVG illustration.** The brand doesn't use decorative spot illustrations in
  research; structure (grids, nodes, charts) is the visual language. Don't invent iconography —
  reuse the mark and Lucide line icons.

---

## Foundations at a glance

| Concern | Token file | Highlights |
|---|---|---|
| Color | `tokens/colors.css` | `--blue-500` #3b7af5, navy `--ink-900`, signal greens/reds, graph teal #00d4aa |
| Type | `tokens/typography.css` | Orbitron display / Space Grotesk body / JetBrains mono; 2xs→8xl scale |
| Spacing | `tokens/spacing.css` | 4px unit; slide + short stage geometry; radii |
| Effects | `tokens/effects.css` | Deep soft shadows, inset rings, signature ease, stage glow + grid |
| Semantic | `tokens/semantic.css` | `--stage-bg`, `--surface-card`, `--text-*`, `--data-*`, `[data-surface="light"]` |

---

## Index — what's in this system

The Design System tab shows every registered specimen, component, and template card. Map of the
repository:

- **`styles.css`** — global entry point (link this one file). `@import`s fonts + all tokens.
- **`fonts.css`** — `@font-face` for Orbitron + Space Grotesk; JetBrains Mono via Google Fonts CDN.
- **`tokens/`** — `colors.css`, `typography.css`, `spacing.css`, `effects.css`, `semantic.css`.
- **`assets/`** — `robosystems_mark.svg` (currentColor) + `robosystems_mark_white.svg`,
  `robosystems_logo_72.png`, lockups, sub-brand logos (`roboledger.png`, `roboinvestor.png`),
  partner/source logos (`sec.png`, `quickbooks.svg`, `claude.svg`), `grid.svg` texture.
- **`guidelines/`** — foundation specimen cards (Colors, Type, Spacing, Brand groups).
- **`components/`** — reusable React content primitives:
  - `brand/` — **Eyebrow**, **Badge**, **BrandMark**, **SourceFooter**
  - `data/` — **MetricCard**, **Callout**, **BarChart**, **ComparisonTable**
  - `controls/` — **Button**
- **`templates/`** — copy-ready content starting points (each a `.dc.html` consuming projects
  can adopt):
  - `video-deck/` — **Video Deck** (title / metric-cards / bar / callout / bull-vs-bear / CTA)
  - `thumbnail/` — **YouTube Thumbnail** (hero metric + banner + secondary stats)
  - `blog-post/` — **Blog Post** (light-surface long-form essay)
  - `social-card/` — **Social Card** (1080-square stat card for X / LinkedIn)
- **`SKILL.md`** — Agent-Skill manifest for using this system in Claude Code.

> **Component namespace:** in card/template HTML, read components via
> `const { Eyebrow, MetricCard, … } = window.RoboSystemsContentDesignSystem_746ae7`.
