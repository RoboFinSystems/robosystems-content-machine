Quick recon on a company before initiating coverage. Check what data exists, what's ready, and whether it's worth covering.

## Arguments
- `$ARGUMENTS` — ticker symbol (e.g., GTBIF)

## Steps

### 1. Check the SEC graph
Run these MCP queries to understand data availability:

- Entity lookup: `MATCH (e:Entity) WHERE e.ticker = '{TICKER}' RETURN e.cik, e.name, e.sic_description`
- Filing history: `MATCH (e:Entity)-[:ENTITY_HAS_REPORT]->(r:Report) WHERE e.ticker = '{TICKER}' RETURN r.form, r.filing_date, r.report_date, r.fiscal_year_focus, r.accession_number ORDER BY r.filing_date DESC LIMIT 10`

If the entity doesn't exist in the graph, say so — the company may need to be loaded first.

### 2. Check S3 for raw filings
```bash
AWS_PROFILE=robosystems-sso aws s3 ls "s3://robosystems-821526227241-shared-raw-prod/sec/year=2026/{CIK}/"
AWS_PROFILE=robosystems-sso aws s3 ls "s3://robosystems-821526227241-shared-raw-prod/sec/year=2025/{CIK}/"
```

### 3. Quick financial snapshot
Pull the latest revenue and key metrics from the graph:
```
MATCH (f:Fact {has_dimensions: false})-[:FACT_HAS_ELEMENT]->(el:Element),
      (f)-[:FACT_HAS_PERIOD]->(p:Period),
      (f)-[:FACT_HAS_ENTITY]->(e:Entity {ticker: '{TICKER}'})
WHERE el.qname IN ['us-gaap:Revenues', 'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax', 'ifrs-full:Revenue']
AND f.numeric_value IS NOT NULL AND p.duration_type = 'annual'
RETURN DISTINCT el.qname, p.end_date, f.numeric_value
ORDER BY p.end_date DESC
LIMIT 5
```

### 4. Web search for current context
- Current stock price and market cap
- Any major recent news (30 seconds of searching, not deep research)

### 5. Check if project already exists
```bash
ls -la projects/{TICKER}/ 2>/dev/null
```

### 6. Print summary
```
Scout Report: {TICKER} ({company name})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Graph:     Loaded (CIK: {cik})
  Filings:   10-K FY2025 (filed 2026-02-25), 4x 10-Q, 10-K FY2024
  S3 Raw:    2 ZIPs available (2025, 2026)
  Revenue:   $1.18B (FY2025), $1.14B (FY2024), $1.05B (FY2023)
  Price:     $7.02 | Market Cap: ~$1.9B
  Project:   Not scaffolded

  Ready to cover: YES
  Next: just campaign {TICKER} cannabis_coverage
```

If the company is NOT in the graph or has no recent filings, say so clearly and suggest loading it.
