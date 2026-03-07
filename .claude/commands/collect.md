Collect source materials for a company coverage project. This is a tag-team process — automate what we can, tell the user what to get manually.

The user will provide a ticker and optionally a project path. If no project path, look for an existing project in `projects/` matching the ticker.

## Arguments
- `$ARGUMENTS` — ticker symbol (e.g., GTBIF) and optionally a project path

## Steps

### 1. Identify the company and project
- Parse the ticker from arguments
- Find the project directory (e.g., `projects/GTBIF_2025_10_K/` or `projects/GTBIF/`)
- If no project exists, tell the user to scaffold one first with `just campaign`
- Ensure `sources/` directory exists in the project

### 2. SEC Filing Extraction (automated)
- Look up CIK via RoboSystems MCP: `MATCH (e:Entity) WHERE e.ticker = '{TICKER}' RETURN e.cik, e.name`
- Look up latest filing via MCP: `MATCH (e:Entity)-[:ENTITY_HAS_REPORT]->(r:Report) WHERE e.ticker = '{TICKER}' RETURN r.form, r.filing_date, r.accession_number ORDER BY r.filing_date DESC LIMIT 5`
- List available ZIPs in S3:
  ```bash
  AWS_PROFILE=robosystems-sso aws s3 ls s3://robosystems-821526227241-shared-raw-prod/sec/year={YEAR}/{CIK}/
  ```
- Download the filing ZIP to `/tmp/{ticker}/`
- Unzip and find the main HTML file (largest `.htm` file, usually `{ticker}-{date}.htm`)
- Extract plain text from HTML using Python (strip tags, clean whitespace)
- Save to: `{project}/sources/{TICKER}_10K_filing.txt` (or `_40F_filing.txt`)

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

### 6. Summary
Print what was collected and what the user needs to provide:
```
Collected for {TICKER}:
  OK    sources/{TICKER}_10K_filing.txt (XX,XXX words)
  OK    sources/{TICKER}_earnings_release.txt (X,XXX words)
  NEED  sources/{TICKER}_earnings_transcript.txt
        → Found at: [URL]
        → Please log in, copy the transcript, and paste into the file above
  OK    sources/{TICKER}_market_context.txt (XXX words)
```
