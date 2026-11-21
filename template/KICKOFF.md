# Kickoff — {TICKER}

The cold-start prompt for a coverage run. `/author {TICKER}` already does everything below, so
this file exists for the times you want to drive the run by hand, or hand it to a second session
working the same project folder. `just kickoff {TICKER}` prints it with the ticker filled in.

---

You're producing an equity research brief for **{TICKER}**; everything you need is in this folder.

1. **Read `TASK.md` if it exists** (a `/batch-research` run): the filing by accession, the research
   tier, the deliverables.
2. Then **`AUTHORING_INSTRUCTIONS.md`**, starting with "Research method". If a campaign overlay is
   present, also read **`CAMPAIGN_BRIEF.md`**. **`PRODUCTION_CONTRACT.md`** matters only for a
   video pick.
3. Read everything else in **`sources/`** except `_prior_coverage.md`, which stays closed until the
   brief is drafted.

Rules:
- The web pass first, written to `sources/_web_research.md`; then the filing, verified in xbrlkit
  by accession; then checks A to D. Every figure about the company comes from a filing; web
  material is named and dated in the sentence.
- Brief-only by default: the brief, the X post and `publish.json`.

When done: `just validate-brief {TICKER}`. A video pick also gets the script, then
`just validate {TICKER}` and `just webdeck-pipeline {TICKER}`.

---
## Run-specific flavor (optional)

<!-- Add any one-off direction for THIS run here, then it rides along when you paste the kickoff.
     Example: "This is continuing coverage: open with what changed."
     Leave blank for a standard run. -->
