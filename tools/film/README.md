# The film kit

What every video built on the brand film's form shares. The kit knows nothing about any one
film: a lane brings its words and its scenes, the kit times them to a voice, fits the music,
and assembles the picture.

Two lanes build on it today.

| Lane | Its own | Builds with |
| --- | --- | --- |
| The brand film and its short cuts | `tools/ad/`: the approved acts in `film.py`, the specs in `films/`, its Blender shots, its page `renderer/templates/ad.html` | `just ad-film <name>` |
| Research films | `tools/research_film/build.py`, the kit's page `renderer/templates/film.html`, a spec per ticker in `projects/<TICKER>/film/` | `just research-film <TICKER>` |

## What the kit holds

| Part | File | Does |
| --- | --- | --- |
| Timing | `timing.py` | One voice take per act, word timings, the music fitted so its hit lands on the turn, and `timeline.json` |
| Assembly | `assemble.py` | Screens each plate under its window of the type layer, cuts a plate back around the type where asked, mixes voice over ducked music at -14 LUFS |
| The graph ident | `blender/graph_ident.py` | The sphere of facts. The brand film's hero and the filing ident research opens on (`just film-ident`) are both cut from it |
| The stage | `renderer/templates/film_stage.js`, `film_stage.css` | The renderer, lens, bloom, dust, graph, floor, backgrounds, fonts and the easing a page's scenes use |
| The page | `renderer/templates/film.html` | The type layer of any film whose scenes are data: a spec lists its scenes and each names a kind (figures: `stat`, `number`, `rows`, `cards`; charts: `columns`, `line`, `table`; words: `title`, `points`, `dual`, `quote`, `change`; the rest: `ident`, `capture`, `ask`, `end`). What each kind takes is listed at the top of the page |
| The guard | `check.py` | `just film-check`: recomputes the brand films' timelines and compares them with the tracked copies |

The look itself (colours, type) is `design-system/tokens/film.css`.

## What a lane supplies

1. **Its acts.** `{ id: { lead, text, cues, scenes } }`, in the shape `timing.py` documents. Where
   they live is the lane's business: the ad keeps them in code because its words are approved
   once and reused; research carries them in each ticker's spec.
2. **A spec per film**: which acts, in what order, the turn, the frame shape, and any `data`
   the page should be handed. The kit copies `data` into the timeline untouched.
3. **A page.** A lane whose scenes are data uses the kit's page, `film.html`, and adds a kind there
   when it needs one no film has had (a kind belongs to no lane: a product capture serves a
   research film's close, a product film's body and an ad's proof shot alike). A lane whose
   scenes are drawn by hand, as the brand film's are, keeps a page of its own. Either way it is a page that fetches the film's `timeline.json` and honours the seek contract:
   `window.__init()` (async, sets `window.__READY`), `window.__total()` in seconds, and
   `window.__seek(t)` drawing the frame at `t`. It imports the stage and adds only its own
   scenes. It draws type on black wherever a plate will be screened under it.
4. **Its plates**, as a map from scene to footage, passed to `timing.build`. Footage rendered
   to the scene's own length needs only a file. Footage shared between films (the filing ident)
   names a cue and its own mark, and the kit skips into it so the two meet.
5. **Where it writes.** A film folder gets `timeline.json`, `voice.wav`, `music.wav` and
   `renders/`. Nothing a build writes is tracked.

A lane does not add its acts, scenes or figures to another lane's files, and does not put
anything of its own in the kit. If two lanes need the same thing, it moves here.

## A long film

A film of several minutes is the same thing with more acts. Two things differ. Its spec names a
second bed (`"bed": { "file", "from": act, "gain" }`): the scored bed carries the opening and its
hit, then hands over at that act to a quieter one that loops under the rest. And a long film is
laid out before it is voiced: a lane's dry build times it from word counts, so the picture and
the words can be read and approved before a take is paid for.

## Changing the kit

- **Timing.** Run `just film-check`. It needs the brand films' voice takes cached on the
  machine (they are not tracked), and it checks timings only. After a change that is meant to
  move a cue, `just film-check --save` and commit the new copies.
- **The stage, the assembler or the ident.** The guard does not render. Build `just ad-film main`
  and compare it with the last render (`ffmpeg -lavfi psnr`); the films are seeded, so an
  unchanged picture compares at infinite PSNR.
- **A research film** checks its own figures before it builds: every figure on screen is
  listed in its spec with the filing it was read from.

Nobody building these can hear them. A mix is finished when a person has listened to it.
