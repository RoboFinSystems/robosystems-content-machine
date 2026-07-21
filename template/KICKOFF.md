# Cowork Kickoff — {TICKER}

Paste this into a Claude Cowork session pointed at this project folder. (This is the **cold-start
for the Cowork stage** — the analog of pasting `DESIGN_INSTRUCTIONS.md` into Claude Design.)
Tip: `just kickoff {TICKER}` prints this with the ticker filled in, ready to copy.

---

You're producing equity-research coverage for **{TICKER}** — everything you need is in this folder.

1. **Read `sources/_SOURCE_NOTES.md` first** — the per-ticker angle, the verified anchor numbers,
   the coverage type (initiating vs. update), and exactly what to refresh live.
2. Then **`AUTHORING_INSTRUCTIONS.md`** (the editorial brief) and **`PRODUCTION_CONTRACT.md`** (the
   output schema, slide kinds, and spoken-form TTS rules). If a campaign overlay is present, also
   read **`CAMPAIGN_BRIEF.md`**.
3. Read everything else in **`sources/`** (filings, transcripts, comps, prior coverage).

Rules:
- **Verify every number live via the RoboSystems MCP** (keyed by CIK / legacy ticker — see
  `_SOURCE_NOTES.md`). Never reuse a stale figure; web-search the current price, valuation, and news.
- Produce the outputs `AUTHORING_INSTRUCTIONS.md` specifies, in order (brief first). Follow the schema
  in `PRODUCTION_CONTRACT.md` exactly — you author **no HTML**.
- Narration must be spoken-form (the TTS rules in the contract).

When done, I'll run `just validate {TICKER}` and the production pipeline.

---
## Run-specific flavor (optional)

<!-- Add any one-off direction for THIS run here, then it rides along when you paste the kickoff.
     Examples: "Skip the short block this run." · "Lead with the AI-capex angle." ·
     "Keep the long-form under 7 minutes." · "This is continuing coverage — open with what changed."
     Leave blank for a standard run (the angle already lives in _SOURCE_NOTES.md). -->
