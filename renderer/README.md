# @robosystems/content-renderer

Playwright-based **local renderer** for the content machine — the sibling Node
package to `design-system/`. It does the jobs the Python pipeline can't:

1. **`capture`** — drive the live **RoboLedger web UI** headlessly (login →
   navigate the demo's money screens → high-res stills/clips). This is the
   autonomous UI-capture track for the showcase series.
2. **`short`** — mount the **real design-system components** in a headless
   browser and shoot one screenshot per frame → a frame-accurate mp4 (9:16
   research shorts, 16:9 demo cutaways). This replaced the retired Pillow
   caption-card renderer: one brand source for both the deck and the short.
3. **`demo`** — record a scripted **walkthrough of the live product**: a pointer
   travels, hovers, clicks and scrolls, and the UI responds, because the drawn
   cursor and the real mouse are the same mouse. Zoom is a camera over the live
   page aimed at a named component. This is the replacement for the old
   still-plus-Ken-Burns demo cut.
4. **`probe`** — list the anchors a walkthrough can actually aim at, read off the
   running app.

**Tool vs. product:** this package is the generalized, committed *tool*. Everything
per-episode is a *product* and lives together under the repo-root
**`showcase/<company>/`** (gitignored, authored via Claude Code; folders match the
backend demo slugs, e.g. `coffee_roaster`, `saas_startup`):

```
showcase/coffee_roaster/
  driftline.demo.json      # spec
  captures/*.png           # UI stills from `capture`
  renders/*.mp4            # rendered output
```

Outputs self-locate next to their spec, so nothing under `renderer/` is written to
or committed except the tool itself.

**Division of labour:** this package emits the *silent visual layer only*. The
Python pipeline stays the orchestrator and owns **audio** (ElevenLabs VO +
ducked music) and the final mux. The **long-form research deck is the webdeck**
(`just webdeck-pipeline`) and is out of scope here: the renderer never touches it.

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

Stills land in `showcase/<company>/captures/<key>.png` (2× device scale) — via the
`just render-capture <config> <company> <entity>` recipe.

Flags: `--base-url`, `--email`/`--password` (instead of `--config`),
`--theme dark|light|auto` (default `dark`), `--entity <name-prefix>` (e.g.
`Driftline` / `Cadence` — switches the active company, persists for the session),
`--viewport WxH`, `--full-page`, `--out DIR`.

## short

```bash
just render-short showcase/coffee_roaster/driftline.short.json   # 9:16 research short
just render-short showcase/coffee_roaster/driftline.demo.json     # 16:9 demo cutaway
```

Specs live in the repo-root `showcase/<company>/` (gitignored products). Output
self-locates to `showcase/<company>/renders/<slug>.mp4` — silent, H.264, `yuv420p`.
`image` scenes read `/cap/*.png` from `showcase/<company>/captures/`. Add
`--keep-frames` to retain the PNG frames.

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

## demo — the live product walkthrough

```bash
just demo-probe    <config> Driftline "/ledger/close,/reports,/plan"   # what can I aim at?
just demo-stills   showcase/coffee_roaster/driftline.walkthrough.json <config>   # ~15s fit check
just demo-pipeline showcase/coffee_roaster/driftline.walkthrough.json <config>   # narrate -> record -> mux
```

Needs the RoboLedger UI running (default `http://localhost:3001`); `--base-url`
points it at prod instead. Renders at roughly **2x realtime** - a 90-second demo
takes about three minutes.

**Two rules hold it together.**

*Voiceover owns the clock.* `tools/demo_narrate.py` synthesises one mp3 per beat,
measures it, and writes `durationMs` back into the spec. The renderer then fits
that beat's choreography into exactly that many frames. Audio and video cannot
drift, however long a sentence turns out to be.

*Waiting happens off camera.* Navigations, network settles and entrance
animations run to completion **between** frames, never during them. Every frame
is shot of a settled UI, so the recording has no dead air and the product looks
as fast as it is.

**Zoom is sharp because the browser does the work.** The page renders at
`deviceScaleFactor: 2` and each frame is a screenshot `clip` of the camera rect,
downsampled to 1920x1080. At 1x that is a supersampled frame; at the 2x cap it is
pixel-for-pixel. Nothing is ever upsampled - which is the whole difference from
Ken-Burns-ing a PNG. `maxZoom` is clamped to the device scale factor for that
reason. A zoom target already wider than the viewport correctly resolves to 1x:
there is nothing to zoom into.

### Spec format

`showcase/<company>/<name>.walkthrough.json` is a list of **beats**; each beat is
one narration line plus the **actions** performed while it plays.

```jsonc
{
  "slug": "driftline_walkthrough", "width": 1920, "height": 1080, "fps": 30,
  "theme": "dark", "entity": "Driftline", "graph": "coffee_roaster", "maxZoom": 2,
  "beats": [
    { "id": "close-detail",
      "narration": "Claude drafts every entry, and each one carries its evidence.",
      "actions": [
        { "kind": "goto", "route": "/ledger/close", "ms": 700 },
        { "kind": "zoom", "target": "[data-testid=\"period-close-panel\"]", "ms": 1300 },
        { "kind": "dwell" }
      ] }
  ]
}
```

| action | does | notes |
|---|---|---|
| `goto` | navigate, settle off camera, hold | resets the camera unless `keepZoom` |
| `move` / `hover` | pointer travels along a bowed path | the real mouse moves too, so hover styles fire |
| `click` | press, click for real, ride the ripple out | settles the consequence off camera |
| `scroll` | eases the element's own scroll container | finds the scroller rather than assuming the document |
| `zoom` | animates the camera to a component | no `target` means back to full frame |
| `type` / `key` | keyboard input | |
| `dwell` | hold | **elastic**: with no `ms`, absorbs the beat's remaining time |
| `wait` | `waitForSelector`, emits no frames | |
| `select` | picks a native `<select>` option | `value`, `label` or `option`; moves the cursor there first |
| `overlay` | a fixed chat bubble, bottom right | `role: human\|agent` + `text`; for narrating an ask and its answer |
| `overlay-clear` | removes the bubble | |
| `api` | calls the product API off camera | **emits no frames**; needs `--config`. See below |

`target` is a **raw Playwright selector** (`[data-testid="x"]`,
`button:has-text("Close")`, `text=Deferred revenue`), or `[x, y]`, or
`{ selector, offset, nth, timeout }`. Raw selectors on purpose: the app's
`data-testid` vocabulary is thin, so specs need `text=` and `:has-text()` as
first-class options.

Add `"optional": true` to an action to degrade a missing target into a hold plus
a warning instead of killing the render. A missing target otherwise fails with
the closest matching anchors on that page listed for you. `scroll` and `select`
honour it for their own failures too, not just a missing target.

**`api` drives the product directly** when a beat needs state the UI can't reach
in the time available, or when a UI quirk would otherwise block the shot. Named
ops: `promote-obligations` (then clicks Refresh so the Closing Book sees the
cleared gate), `update-forecast-assert` and `compute-forecast`. Anything else is
a raw call, so a new capability demo doesn't need a change to this tool:

```jsonc
{ "kind": "api", "op": "update-forecast-assert", "structure_name": "FY27 Operating Budget",
  "qname": "rs-gaap:RevenueFromContractWithCustomerExcludingAssessedTax", "value": 150000 }
{ "kind": "api", "path": "/extensions/roboledger/{graphId}/operations/whatever",
  "method": "POST", "body": { "...": "..." }, "refresh": true }
```

`{graphId}` interpolates. `"refresh": true` clicks the page's Refresh afterwards
so the change lands on camera (on by default for `promote-obligations`;
`"refresh": false` opts out). `"optional": true` degrades a failed call to a
warning, same as everywhere else.

**Every spec that uses `api` must name its graph**: `"graph": "<key from the
config's graphs>"`, or `"graphId"` for a literal, at spec level or per action.
There is deliberately no default. The camera picks its tenant by `entity` name
and the API picks its own by graph id, so a guess here does not fail the render,
it quietly drives one company while filming another. Same reasoning for `qname`,
`value` and `structure_name`, which are required rather than defaulted, and for
forecast blocks, which are matched by exact name.

Two more things follow. `api` **writes to whatever environment `--config` points
at**, so aim it at local. And `just demo-stills` runs `api` actions like any
other, which is deliberate (the still has to show the post-mutation UI) but
means the 15-second fit check is *not* read-only.

### One tool, many demos

A demo is a folder under `showcase/`, and nothing about it lives in `renderer/`.
Different scenario, different capability, different tenant: all of it is spec.

| what varies | where it goes |
|---|---|
| which company is on camera | `entity` (the UI switcher) |
| which graph the `api` actions hit | `graph` / `graphId` |
| which surfaces, in what order | the beats |
| which numbers get asserted | `qname` / `value` on the action |
| a capability with no named op yet | `path` + `body` |

`entity` and `graph` are two handles on the same tenant and the tool cannot
check that they agree, so set them together. `showcase/DEMO_DATA_REQUIREMENTS.md`
is the contract with the `robosystems` repo for provisioning a new demo graph.

**Always run `just demo-stills` first.** It walks the entire choreography and
writes one framed still per beat in ~15 seconds, reporting the zoom level each
beat settled at. Catching a zoom aimed at the wrong element there costs seconds;
catching it after a full render costs minutes.

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
- **Clips** ✅ — shipped as `demo`: real cursor, real clicks, component-targeted
  zoom, VO-locked timing. Supersedes the still-plus-Ken-Burns demo cut.
