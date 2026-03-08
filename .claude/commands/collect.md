Collect source materials for a company coverage project. This is a tag-team process — automate what we can, tell the user what to get manually.

The user will provide a ticker and optionally a project path. If no project path, look for an existing project in `projects/` matching the ticker.

## Arguments
- `$ARGUMENTS` — ticker symbol (e.g., GTBIF) and optionally a project path

## Steps

### 1. Identify the company and project
- Parse the ticker from arguments
- Find the project directory (e.g., `projects/GTBIF/` or `projects/GTBIF_2025_10_K/`)
- If no project exists, tell the user to scaffold one first with `just campaign`
- Ensure `sources/` directory exists in the project

### 2. SEC Filing — Curated Narrative Extraction (automated)
- Look up CIK via RoboSystems MCP: `MATCH (e:Entity) WHERE e.ticker = '{TICKER}' RETURN e.cik, e.name`
- Look up latest filing via MCP: `MATCH (e:Entity)-[:ENTITY_HAS_REPORT]->(r:Report) WHERE e.ticker = '{TICKER}' RETURN r.form, r.filing_date, r.accession_number ORDER BY r.filing_date DESC LIMIT 5`
- List available ZIPs in S3:
  ```bash
  AWS_PROFILE=robosystems-sso aws s3 ls s3://robosystems-821526227241-shared-raw-prod/sec/year={YEAR}/{CIK}/
  ```
- Download the filing ZIP to `/tmp/{TICKER}/`
- Unzip and find the main HTML file (largest `.htm` file, usually `{ticker}-{date}.htm`)
- **Extract curated narrative sections** using the extraction tool:
  ```bash
  python3 tools/extract_10k_narrative.py /tmp/{TICKER}/{ticker}-{date}.htm {project}/sources/{TICKER}_10K_filing.txt --ticker {TICKER}
  ```
  This extracts only the qualitative content (Item 1: Business, Item 1A: Risk Factors, Item 1C: Cybersecurity, Item 2: Properties, Item 7: MD&A, Item 7A: Market Risk). Financial tables and XBRL data are excluded — those come from RoboSystems MCP.
- For 40-F filers, the same script should work but the section headings may differ. If extraction fails, fall back to manual curation.
- Keep the raw HTML in `/tmp/{TICKER}/` in case re-extraction is needed.

### 3. Earnings Release (automated attempt)
- Web search: `"{company name}" Q4 {year} earnings results press release site:globenewswire.com OR site:prnewswire.com OR site:businesswire.com`
- Also try: `"{company name}" investor relations earnings`
- If a free URL is found, fetch it and extract the text
- Save to: `{project}/sources/{TICKER}_earnings_release.txt`
- If not found, tell the user where to look

### 4. Earnings Transcript (tell user)
- Web search: `"{company name}" earnings call transcript Q4 {year}`
- Search for the transcript URL (company IR page, financial news sites, transcript services)
- Many transcript sites block automated access — if you can't fetch it, report the URL
- Tell the user: "I found the transcript at [URL]. Please copy/paste it into `sources/{TICKER}_earnings_transcript.txt`"

### 5. Market Context (automated)
- Web search: current stock price, market cap, 52-week range, recent news
- Web search: analyst commentary, rescheduling updates, state regulatory news
- Compile into a brief summary
- Save to: `{project}/sources/{TICKER}_market_context.txt`

### 6. Earnings Presentation (tell user)
- Web search: `"{company name}" investor presentation {year} site:{company IR domain}`
- Most cannabis companies publish investor decks as PDFs on their IR pages
- Tell the user: "Check the company's IR page for an investor presentation PDF"
- If the user provides a PDF:
  1. Convert to slide PNGs: `pdftoppm -png -r 200 "{pdf_path}" "{project}/sources/earnings_presentation_slides/slide"`
  2. Review slides and delete boilerplate (cover, disclaimers, section dividers, mission/values, team photos, closing slides)
  3. Keep substantive data slides (financials, charts, maps, metrics, reconciliations)
  4. Create a text summary: `{project}/sources/{TICKER}_earnings_presentation.txt` by reading each kept slide and transcribing the data
  5. Delete the original PDF after extraction

### 7. Campaign Shared Sources
- Check if `campaigns/{campaign_name}/sources/` has any files
- If files exist and aren't already in the project's `sources/`, copy them
- These are sector-level resources (e.g., `cannabis_comps_table.txt`) that apply to all projects in the campaign
- Note: `just campaign` now copies these automatically at scaffold time, but `/collect` should check for any new additions

### 8. Summary
Print what was collected and what the user needs to provide:
```
Collected for {TICKER}:
  OK    sources/{TICKER}_10K_filing.txt (XX,XXX words — curated narrative sections)
  OK    sources/{TICKER}_earnings_release.txt (X,XXX words)
  NEED  sources/{TICKER}_earnings_transcript.txt
        → Found at: [URL]
        → Please copy/paste the transcript into the file above
  OK    sources/{TICKER}_market_context.txt (XXX words)
  NEED  sources/{TICKER}_earnings_presentation.txt
        → Download the investor presentation PDF from the company's IR page
        → Provide the path and I'll extract slides + create the text summary
  OK    sources/cannabis_comps_table.txt (shared — campaign level)
```

## Source File Reference

The complete set of sources for a cannabis coverage project:

| File | How | Content |
|------|-----|---------|
| `{TICKER}_10K_filing.txt` | Automated (extract_10k_narrative.py) | Business overview, risk factors, MD&A — narrative only, no tables |
| `{TICKER}_earnings_release.txt` | Automated (web fetch) | Press release with headline numbers, management quotes |
| `{TICKER}_earnings_transcript.txt` | Manual (user pastes) | Earnings call Q&A, management commentary on catalysts |
| `{TICKER}_market_context.txt` | Automated (web search) | Stock price, valuation, analyst coverage, recent news |
| `{TICKER}_earnings_presentation.txt` | Semi-auto (user provides PDF) | Investor deck data — financials, charts, reconciliations |
| `earnings_presentation_slides/` | Semi-auto (pdftoppm + curation) | Substantive slide PNGs (boilerplate removed) |
| `cannabis_comps_table.txt` | Shared (campaign level) | Sector-wide valuation comps from SSC Advisors |
