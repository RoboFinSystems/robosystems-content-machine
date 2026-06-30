---
name: robosystems-design
description: Use this skill to generate well-branded RoboSystems content — research video decks, YouTube thumbnails, blog essays, social/stat cards, and other financial-analysis artifacts — for production or throwaway prototypes/mocks. Contains the brand's colors, type, fonts, logo, voice/tone rules, and reusable content UI components.
user-invocable: true
---

# RoboSystems Content Design System

This skill dresses the **RoboSystems Content Machine** — the pipeline that turns SEC filings
into narrated videos, shorts, podcasts, blogs, and social posts. It is the *content* counterpart
to the RoboSystems app design system: dark-first, built for decks and stories, not app screens.

Read **`readme.md`** first — it carries the full brand guide:
- **CONTENT FUNDAMENTALS** — voice, tone, casing, person, the bull-AND-bear honesty rule, the
  spoken-form TTS rules. The voice is "the sharp equity analyst who shows their work."
- **VISUAL FOUNDATIONS** — the dark navy "stage," one brand blue, strict data-signal colors,
  graph teal accent, Orbitron + Space Grotesk, restrained motion, etched-panel cards.
- **ICONOGRAPHY** — the mark, Lucide line icons (substitution for the app's inline Flowbite
  SVGs), no emoji in published research.

Then explore:
- **`styles.css`** + **`tokens/`** — link `styles.css` for every CSS custom property.
- **`assets/`** — the RoboSystems mark (white + currentColor variants), lockups, partner logos.
- **`components/`** — reusable React content primitives (`Eyebrow`, `Badge`, `BrandMark`,
  `SourceFooter`, `MetricCard`, `Callout`, `BarChart`, `ComparisonTable`, `Button`).
- **`templates/`** — copy-ready content starting points: `video-deck`, `thumbnail`,
  `blog-post`, `social-card`.

## How to work

If you're creating **visual artifacts** (slides, thumbnails, mocks, throwaway prototypes): copy
the assets you need out of `assets/`, link `styles.css`, and produce static HTML — start from a
`templates/` folder. Keep every on-screen number verbatim; never fabricate data.

If you're working on **production code**: read the token files and component sources to design
fluently in the brand, and reuse the CSS custom properties rather than hard-coding values.

If the user invokes this skill with no other guidance, ask what they want to build (a video deck?
a thumbnail? a blog post? a social card?), ask a few questions about the ticker/topic and angle,
then act as an expert RoboSystems content designer who outputs HTML artifacts *or* production code.

**Non-negotiables:** RoboSystems house blue; Orbitron display + Space Grotesk body; dark stage
for video/decks (light surface only for blog/reports); accent color for the one thing that
matters per slide; eyebrow section labels; a source-attribution footer; and the standing
disclaimer — *"Not investment advice. No price targets. Every number from the filings."*
