# Cannabis Coverage — Ticker List

Companies with structured SEC filing data available in RoboSystems, ranked by priority.

**Strategy:** Turn around coverage reports the night each FY2025 10-K drops. Huge cluster week of Mar 11-16, 2026.

## Earnings Calendar — FY2025 Annual Filings

```
Mar 11  MRMD     Post-Market    10-K
Mar 12  VRNO     Pre-Market     10-K    ← top priority
Mar 12  TSNDF    Post-Market    10-K    ← top priority
Mar 12  AAWH     Post-Market    10-K
Mar 12  VREOF    During-Market  10-K
Mar 12  GLASF    Post-Market    40-F    (blocked — no MCP data)
Mar 13  PLNH     Post-Market    10-K
Mar 16  CBSTF    During-Market  10-K
---
May 6   GTBIF    Post-Market    Q1 FY2026 (annual already done)
May 8   TCNNF    During-Market  Q1 FY2026 (annual already done)
May 8   CURLF    Post-Market    quarterly (40-F blocked)
```

CRLBF last reported 3/5/2026 — FY2025 annual may already be filed. No upcoming date listed.
JUSHF, GRUSF, CXXIF — no upcoming date listed.

## Coverage Status

| Status | Ticker | Company | CIK | Filing Type | MCP Data | FY | Earnings | Notes |
|--------|--------|---------|-----|-------------|----------|----|----------|-------|
| DONE | GTBIF | Green Thumb Industries | 0001795139 | 10-K | FY2025 (4yr) | 2025 | 5/6 Q1 | Video published. Most profitable MSO. |
| DONE | TCNNF | Trulieve Cannabis | 0001754195 | 10-K | FY2025 (4yr) | 2025 | 5/8 Q1 | Video published. 60% gross margin, record FCF. |
| READY | VRNO | Verano Holdings | 0001848416 | 10-K | FY2021-2024 (4yr) | 2024 | 3/12 Pre | Solid data. FY2025 10-K night-of target. |
| READY | TSNDF | TerrAscend | 0001778129 | 10-K | FY2021-2024 (4yr) | 2024 | 3/12 Post | Solid data. NJ/PA growth story. |
| READY | AAWH | Ascend Wellness | 0001756390 | 10-K | FY2021-2024 (4yr) | 2024 | 3/12 Post | Solid data. IL/NJ/MA focused. |
| READY | CBSTF | Cannabist (fka Columbia Care) | 0001776738 | 10-K | FY2021-2024 (4yr) | 2024 | 3/16 | Solid data. Revenue declining. |
| READY | MRMD | MariMed | 0001522767 | 10-K | FY2022-2024 (3yr) | 2024 | 3/11 Post | Solid data. Small-cap. |
| READY | PLNH | Planet 13 Holdings | 0001813452 | 10-K | FY2022-2024 (3yr) | 2024 | 3/13 Post | Solid data. Entertainment dispensary. |
| READY | JUSHF | Jushi Holdings | 0001909747 | 10-K | FY2021-2024 (4yr) | 2024 | TBD | Solid data. PA/VA focused. No date yet. |
| READY | GRUSF | Grown Rogue International | 0001463000 | 20-F | FY2021-2024 (5 periods) | 2024 | TBD | Solid data. Changed FY end (Oct to Dec). Micro-cap. |
| READY | CXXIF | C21 Investments | 0000831609 | 20-F | FY2023-2025 (3yr) | 2025 | TBD | Solid data. Non-standard FY (Jan/Mar end). Micro-cap. |
| BLOCKED | CURLF | Curaleaf Holdings | 0001756770 | 40-F | FY2022-2023 only | 2025 | 5/8 Q | 40-F XBRL not loaded for FY2024/2025. Largest MSO by revenue. |
| BLOCKED | CRLBF | Cresco Labs | 0001832928 | 40-F | FY2022-2023 only | 2024 | filed? | 40-F XBRL not loaded for FY2024. Last reported 3/5/2026. |
| BLOCKED | GLASF | Glass House Brands | 0001848731 | 40-F | No data | 2024 | 3/12 Post | Zero XBRL facts loaded. 40-F/IFRS filer. |
| STALE | VREOF | Vireo Growth | 0001771706 | 10-K | FY2022-2023 only | 2024 | 3/12 | FY2024 10-K filed but not loaded. Needs data refresh. |

## Not in RoboSystems (no data available)

| Ticker | Company | Reason |
|--------|---------|--------|
| VEXTF | Vext Science | Not in SEC graph — may file in Canada only |
| CNTMF | Fluent Corp | Not in SEC graph — may file under different entity or Canada only |

## Production Priority — Night-of Turnaround Plan

**Week of Mar 11-16, 2026 — BLITZ WEEK (7 tickers in 6 days)**

| Date | Ticker | Time | Revenue Est. | Plan |
|------|--------|------|-------------|------|
| Mar 11 | MRMD | Post | $40.8M | Scaffold day-of, publish overnight |
| Mar 12 | VRNO | Pre | $205.9M | **Priority.** Scaffold ahead, data loads AM, publish by evening |
| Mar 12 | TSNDF | Post | $64.7M | **Priority.** Scaffold ahead, data loads PM, publish overnight |
| Mar 12 | AAWH | Post | $120.0M | Scaffold ahead, publish overnight or next AM |
| Mar 12 | VREOF | During | $94.2M | Blocked — needs data refresh first |
| Mar 13 | PLNH | Post | $22.8M | Publish overnight |
| Mar 16 | CBSTF | During | — | Catch-up day |

**Prep work before blitz week:**
- Scaffold all Tier 1 projects ahead of time (`just campaign TICKER cannabis_coverage`)
- Pre-collect sources (comps table, earnings presentations if available)
- Ensure RoboSystems data pipeline auto-ingests new 10-Ks within hours of filing

**No date yet (produce when filing drops):**
- **JUSHF** — PA/VA focused, 4yr data depth, strong candidate
- **GRUSF** — Micro-cap, non-standard FY
- **CXXIF** — Micro-cap, already has FY2025 data

**Blocked — needs RoboSystems 40-F pipeline fix:**
- **CURLF** — Would be #1 priority if data loads (largest MSO, $317M rev est.)
- **CRLBF** — May have already filed FY2025 (last reported 3/5/2026)
- **GLASF** — Reports 3/12 but zero XBRL data, can't produce
- **VREOF** — 10-K filer but FY2024 not loaded, needs data refresh

## Reference — ETF

| Ticker | Name | Notes |
|--------|------|-------|
| MSOS | AdvisorShares Pure US Cannabis ETF | Benchmark for the sector |
