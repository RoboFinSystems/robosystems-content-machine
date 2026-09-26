# tools/motion

QA, voice and music scripts for motion work: the roboledger-app landing demos and the YouTube
episodes built from them. Vendored from [ferndesk/no-slop-motion](https://github.com/ferndesk/no-slop-motion)
at `dc4896d` under its MIT license (`LICENSE-no-slop-motion`). Local changes: ruff fixes and
formatting only. The upstream project also covers a HyperFrames/GSAP engine, Cartesia TTS and a
mascot lane; we use our own renderer (`renderer/`, `just render-motion`) and ElevenLabs instead.

| Recipe | Script | What it does |
| --- | --- | --- |
| `just motion-pops <video>` | `qa/pop-scan.py` | Pops, flashes and black dips that are not planned cuts (`--cuts 3.6,8.0`) |
| `just motion-sheet <video>` | `qa/contact_sheet.py` | Frame grid every N seconds, or densely around cuts, for review |
| `just motion-score-takes` | `audio/score_takes.py` | Rank voice takes by word accuracy, range and pace (emotion model skipped) |
| `just motion-split-takes` | `audio/split_takes.py` | Split the winning take into lines, only in real silences |
| - | `audio/check_vo_spacing.py` | Check the gaps between voice lines |
| `just motion-join-music` | `music/join_on_downbeats.py` | Join or shorten music takes on matching downbeats |
| `just motion-cue-sheet` | `music/cue_sheet.py` | Check every must-hit against the music's beats |

The recipes pull their dependencies per run with `uv run --with`, so librosa and faster-whisper stay
out of `pyproject.toml`. Every script prints its usage with `--help`.

## The rules we adopted

**For the narrated videos (YouTube, social):**

- **The voice sets the clock.** Record each act as one continuous take, pick the best reading with
  `motion-score-takes`, split it only in silences, and time the picture to it. Never stitch one-line
  TTS clips: that is the per-beat pattern `tools/demo_narrate.py` produces, and it sounds assembled.
- **Music comes last**, edited on downbeats so it still sounds like one performance, with the
  must-hits checked by `motion-cue-sheet`.
- **Gates before build:** brief, script read aloud, voice, five still frames, rough cut, then the
  build. Each is signed off before the next starts.
- **Keep a loves and hates file** next to each video (`LOVES-HATES.md`): every note from Joey, in
  his words, with the fix. Re-read it before every render.
- **Claims come from the product.** Every spoken or written line must match what the app and the
  docs say it does today. A motion scene is a drawing, so anything a viewer might doubt is shown as
  live footage instead.

**For every motion render, landing demos included:**

- No one- or two-frame pops: labels and badges change with a crossfade, never by swapping text.
- No black dips between shots; no CSS filters to fake a colour world (author the colours).
- No text parked at the top of the frame while the action happens below.
- No decorative glows, vignettes or drop shadows on containers. Brand gradients that the live site
  uses are allowed; they come from the brand, not from the agent.
- A screen with no camera move, build or morph is a slide: give it a slow push toward the action.
- Headlines enter blur to sharp, word by word. No overshoot on UI, no linear moves.
- Run `just motion-pops` on the render before anyone else watches it.
