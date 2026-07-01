# @robosystems/content-renderer

Playwright-based **local renderer** for the content machine — the sibling Node
package to `design-system/`. It does the two jobs the Python pipeline can't:

1. **`capture`** — drive the live **RoboLedger web UI** headlessly (login →
   navigate the demo's money screens → high-res stills/clips). This is the
   autonomous UI-capture track for the showcase series.
2. **`short`** — mount the **real design-system components** in a headless
   browser and shoot one screenshot per frame → a frame-accurate mp4 (9:16
   research shorts, 16:9 demo cutaways). This replaced the retired Pillow
   caption-card renderer: one brand source for both the deck and the short.

**Tool vs. product:** this package is the generalized, committed *tool*. The
per-episode scene specs are *products* — they live in the repo-root
**`showcase/<company>/`** (gitignored, authored via Claude Code; company folders
match the backend demo slugs, e.g. `coffee_roaster`, `saas_startup`), and render
outputs land in `renderer/out/` (gitignored). Nothing under `renderer/` except the
tool itself is committed.

**Division of labour:** this package emits the *silent visual layer only*. The
Python pipeline stays the orchestrator and owns **audio** (ElevenLabs VO +
ducked music) and the final mux. The **long-form deck is authored in Claude
Design** and is out of scope here — the renderer never touches it.

## Setup (once)

```bash
just render-setup           # npm install + playwright install chromium
```

Requires system `ffmpeg` (already a content-machine dependency).

## capture

```bash
# UI must be running (default http://localhost:3001); creds from a robosystems config.json
just render-capture /Users/you/Projects/robosystems/.local/config.json
# or a subset:
just render-capture <config> close,statements,reports
```

Scenes → routes (the demo beats):

| key | route | beat |
|---|---|---|
| `home` | `/home` | dashboard |
| `transactions` | `/ledger/transactions` | 1 — events / journal entries |
| `agents` | `/agents` | 1 — counterparties |
| `close` | `/ledger/close` | 2 — the AI close (Closing Book) |
| `statements` | `/ledger/statements` | 3 — financial statements |
| `reports` | `/reports` | 3 — the materialized report |

Stills land in `renderer/out/capture/<key>.png` (2× device scale).

Flags: `--base-url`, `--email`/`--password` (instead of `--config`),
`--theme dark|light|auto` (default `dark`), `--entity <name-prefix>` (e.g.
`Driftline` / `Cadence` — switches the active company, persists for the session),
`--viewport WxH`, `--full-page`, `--out DIR`.

## short

```bash
just render-short showcase/coffee_roaster/driftline.short.json   # 9:16 research short
just render-short showcase/coffee_roaster/driftline.demo.json     # 16:9 demo cutaway
```

Specs live in the repo-root `showcase/<company>/` (gitignored products). Output:
`renderer/out/<slug>.mp4` — silent, H.264, `yuv420p`. Add `--keep-frames`
to retain the PNG frames.

### Spec format

A spec is a JSON list of timed scenes (`showcase/coffee_roaster/driftline.short.json`
is the worked example, tied to the real validated Driftline numbers):

```jsonc
{
  "slug": "driftline_short", "width": 1080, "height": 1920, "fps": 30,
  "scenes": [
    { "kind": "hero", "eyebrow": "Net income · 16 months",
      "value": 185057, "format": "currency", "tone": "positive",
      "subline": "The P&L is winning.", "durationMs": 2400 },
    { "kind": "metrics", "heading": "Where the profit went",
      "cards": [
        { "label": "Receivables", "value": "$161,000", "change": "4× the cash",
          "changeTone": "negative", "highlight": true }
      ], "durationMs": 3600 }
  ]
}
```

- **`hero`** — an eyebrow + a big eased **count-up** (`value`+`format`) or a
  `title`, plus an optional `subline`. `tone`: positive|negative|warning|accent.
- **`metrics`** — a heading + staggered **`MetricCard`** grid (the real DS
  component; `highlight` rings the story card).

Determinism: the harness exposes `window.__renderFrame(i)` and we drive it
frame-by-frame (no wall-clock) — the same spec always renders the identical
video.

## How it fits together

```
design-system/  ──_ds_bundle.js + tokens + fonts──►  renderer (short)  ──►  silent mp4 ─┐
robosystems UI  ──login + routes──►  renderer (capture)  ──►  stills/clips ──────────────┤
                                                                                          ▼
                                                             Python pipeline: VO + music + mux
```

## Notes / next

- **Theme** ✅ — `--theme dark` (default). Forces the app's stored Flowbite theme
  (`flowbite-theme-mode` via an init script) + emulates `prefers-color-scheme`,
  so cutaways are on-brand dark and deterministic.
- **Entity** ✅ — `--entity Driftline` drives the header switcher; the selection
  is persisted server-side (JWT session), so every scene navigation reflects it.
- **Clips:** `capture` emits stills today; motion (scrolls, the draft-entry
  click) via frame sequence → ffmpeg is the same core as `short`. *(next)*
