# RoboSystems content brand source

The one place the content machine reads the RoboSystems brand from: **tokens, fonts and
logos**. Nothing here is built or installed. A page links a token file, mounts the fonts and
uses the marks.

It holds two surfaces of one brand:

- **The film** (`tokens/film.css`): the look of the brand film and of every video built on its
  form. Light on near-black, cyan for structure, a blue to indigo field for the turn.
- **The deck** (`tokens/colors.css` and the rest): the research webdeck, thumbnails, article
  covers and the light surface for written reports. Brand blue on a navy stage.

New video work takes the film surface. The deck surface stays for the research long cut until
that is rebuilt on the film's form.

## Who reads it

| Consumer | Reads |
| --- | --- |
| `renderer/templates/ad.html` (the brand film's type layer; `just ad-film`) | `tokens/film.css`, `fonts/`, `assets/robosystems_icon.png` |
| `renderer/templates/research_film.html` (a research film's type layer; `just research-film`) | `tokens/film.css`, `fonts/`, `assets/robosystems_icon.png` |
| `tools/build_webdeck.py`, `tools/build_webdeck_short.py` | `tokens/*.css` (deck), `fonts/`, the lockup and the white mark |
| `tools/gen_article_cover.py` | `fonts/` |

The RoboLedger video templates (`renderer/templates/intro.js`, `outro.js`, `slide.js`) and the
post stills take the product's own chrome and fonts from the app checkouts, not from here:
they are meant to match the product's landing pages.

## The film surface

The house form for video. A film is a spec (`tools/ad/films/<name>.json`) over a set of acts;
the look is fixed here so every film, short cut, research film and demo wrapper matches.

- **Stage.** Near-black (`--film-black` #04070c). Never a flat colour for long: a slow 3D plate
  (the graph sphere, a trace, a report as an object) sits under the type.
- **Structure is cyan.** Nodes are near-white (`--film-node`), links and labels cyan-300
  (#67e8f9), dust and the key light cyan-400 (#22d3ee). The rim light is indigo (#6366f1), the
  fill blue (#2563eb).
- **The field.** A blue to indigo gradient is held back for the turn of a film and for the
  line that states what the product is. It is the only time the frame leaves black.
- **Alarm red** (`--film-alarm` #f87171) belongs to the problem act and nowhere else.
- **Type.** Orbitron for headlines, figures and uppercase labels (wide tracking, .24em to
  .34em); Space Grotesk for captions and anything read as a sentence. One idea per shot.
  Figures are 2D and flat: perspective distorts magnitude.
- **Motion.** Words blur in; a slow push runs under every shot; shots dissolve through the
  stage, never through a dip to black that was not planned (`just motion-pops` checks).
- **Sound.** One voice per film, one scored bed, the music's hit on the film's turn.
- **End card.** The icon and the wordmark over the graph, the site under them.

`film.css` is read by CSS. three.js and Blender cannot read it, so the same values are written
out in `renderer/templates/film_stage.js` (the stage every film page imports) and in the Blender files (`tools/film/blender/`, `tools/ad/blender/`). Change a value here and change it
there, then re-render (`just ad-film main`) and compare.

## The deck surface

- **Stage.** A blue-tinted near-black (`--ink-900` #0a0e1a) with a restrained radial glow and,
  on some slides, a faint dot grid. A light surface (`[data-surface="light"]`) exists for
  written reports.
- **Colour.** One brand blue (`--blue-500` #3b7af5), a navy ink, a cool gray ramp. Data uses a
  fixed signal language: green positive, red negative, brand blue neutral or current, amber
  warning. Graph teal (#00d4aa) is the one non-blue accent, for structure.
- **Type.** Orbitron display, Space Grotesk body, JetBrains Mono for tickers and code (loaded
  from Google Fonts by `fonts.css`, not bundled).
- **Cards.** A 1px hairline with a subtle inset ring, not a drop shadow. Radii 10 to 20px.
- **Layout.** 1920x1080 slides with a 140px side margin; headline, eyebrow, data, then a
  source footer. Every number verbatim from the filing it cites.

| Concern | Token file |
| --- | --- |
| Film | `tokens/film.css` |
| Colour | `tokens/colors.css` |
| Type | `tokens/typography.css` |
| Spacing and stage geometry | `tokens/spacing.css` |
| Shadows, rings, easing, glow and grid | `tokens/effects.css` |
| Semantic aliases and the light surface | `tokens/semantic.css` |

`styles.css` imports the fonts and every token file, for a page that wants them all.

## Marks

- **`assets/robosystems_icon.png`**: the icon the film's end card uses.
- **`assets/robosystems_mark.svg`** (`currentColor`) and **`robosystems_mark_white.svg`**: the
  mark for decks and covers. Give it clear space; never stretch it or fill it with a gradient.
- **`assets/robosystems_lockup.png`**, **`robosystems_lockup_black.png`**: mark and wordmark.
- **Product marks:** `roboledger.png`, `roboinvestor.png`.
- **Source and partner marks:** `sec.png`, `quickbooks.svg`, `claude.svg`, for "sourced from"
  and "works with" lines.
- **`assets/grid.svg`**: the deck's grid texture.

No emoji and no decorative illustration on a brand artifact. Structure (graphs, grids, charts)
is the visual language.

## Fonts

Orbitron and Space Grotesk are bundled as TTFs under the SIL Open Font License. The static
weights serve the deck; `Orbitron-VariableFont_wght.ttf` serves the film.

## Words

How RoboSystems content is written is not set here. Research briefs follow
`template/AUTHORING_INSTRUCTIONS.md`; narration follows the spoken-form rules in
`template/PRODUCTION_CONTRACT.md`.
