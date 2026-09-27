# {EPISODE}: outline

A showcase episode is a product film for the finance lead (CFO, fractional CFO, controller).
Fill this in, get the words approved read aloud, then build. Nothing is recorded before the
narration is approved.

## The frame (every episode)

**RoboLedger, powered by RoboSystems, connects your books to the AI you already use, over MCP,
so it can do X, Y and Z, and you get your time and money back.** One sentence, said once, early.

- **The app is the protagonist, not the company.** The demo company (Driftline, Cadence) is the
  data on screen: the company chip and the figures. The narration never tells its story; it
  says "you", "your books", "your biggest customer".
- **Each beat is a job:** ask, trace, discover, share, plan, compare, approve. Show the app doing
  the work, including at least one insight nobody asked for.
- **Savings are outcomes, never invented figures:** same-day answers, no spreadsheet to rebuild,
  no new tool (it runs on the AI you already pay for). No "hours, not days", no "faster close".
- **Clients:** "Claude, ChatGPT, or any MCP client". Name Grok only once a RoboLedger connection
  from Grok is confirmed and in the docs.
- **The close comes last**, as something the person approves.

## The spine

| Beat | Shot | Narration |
| --- | --- | --- |
| 1. Hook (~8s) | `just motion-template intro` + a slide | The finance lead's problem, in "you". |
| 2. What it is (~8s) | `slide` `flow`: QuickBooks → RoboLedger → your AI | The one sentence above. |
| 3. X (~15s) | Live: chat take, then the app | A job, done on screen. |
| 4. Y (~15s) | Live | A job, and the insight nobody asked for. |
| 5. Z (~15s) | Live | Turn it into work; the close, approved, if it belongs here. |
| 6. Payoff (~8s) | `slide` `compare` | Time and money, as outcomes. |
| 7. End card (~5s) | `just motion-template outro` | "RoboLedger. Powered by RoboSystems." |

Motion shots come from `motion/` (see `motion/README.md`). Live shots are walkthrough beats
(`renderer/README.md`, `just demo-pipeline`) or chat takes (`showcase/mcp_series/recording.md`).

## Rules

- The motion rules in `tools/motion/README.md` hold for every shot.
- Record the voice first. The picture follows it. In a walkthrough, put a `cue` on each
  action the narration names, so it happens on the word.
- Put on screen only what the narration is saying at that moment.
- Never show a feature the app lacks. Anything a viewer might doubt is shown live, not drawn.
- Keep `LOVES-HATES.md` beside this outline: every note from Joey, in his words, with the fix.
- Run `just demo-pops` on every render before anyone watches it.

## This episode

- **X, Y, Z:**
- **The insight nobody asked for:**
- **Data:** which demo company, which graph, which figures (and which are illustrative).
- **Narration, beat by beat:**
