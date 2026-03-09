Scaffold all projects for a campaign at once. Reads the ticker list from the campaign's tickers.md and runs scout + scaffold for each.

## Arguments
- `$ARGUMENTS` — campaign name (e.g., cannabis_coverage)

## Steps

### 1. Read the campaign's ticker list
Read `campaigns/{CAMPAIGN}/tickers.md` and extract all tickers from the markdown tables.

### 2. Check which projects already exist
```bash
ls -1 projects/ 2>/dev/null
```

### 3. For each ticker, run scout and scaffold
For each ticker in the list:

1. **Check if project exists** — if `projects/{TICKER}/` already exists, skip with a note
2. **Quick scout** — check the SEC graph for entity and latest filing (just the MCP queries, skip web search for speed)
3. **Scaffold** — run `./tools/new_project.sh {TICKER} {CAMPAIGN}` for tickers that have data

### 4. Print summary
```
Batch scaffold: {CAMPAIGN}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  GTBIF    CREATED   10-K FY2025 available
  TCNNF    CREATED   10-K FY2025 available
  CURLF    CREATED   40-F FY2025 available
  VRNO     CREATED   10-K FY2024 (FY2025 not yet filed)
  CRLBF    CREATED   40-F FY2024
  TSNDF    CREATED   10-K FY2024
  CBSTF    CREATED   10-K FY2024

  7 projects created, 0 skipped, 0 failed
  Next: /collect {TICKER} for each project
```

### 5. Suggest next steps
Tell the user which tickers have the freshest data and should be prioritized for /collect.
