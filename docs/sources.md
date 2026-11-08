# The four primary sources

The project is **data-first**: rather than scraping web signals (forum complaints, launch sites, search trends), it treats a small set of authoritative reports as the primary source of truth and asks four questions of each, the questions an AI venture studio needs answered before it trusts a dataset:

1. **What data do we need**, not what can we scrape?
2. **How often does it change?**
3. **How reliable is it**, and on what method does it rest?
4. **How can it be queried, compared and combined** with the other sources?

The first project blueprint (January 2026) followed the opposite route: scrape Reddit, Product Hunt and GitHub, cluster complaints with launches, score the clusters' velocity. It was dropped on my supervisor's direction: scraped signals are noisy, hard to verify and impossible to trace back to a citable page, while a report can be cited page by page.

## Source definitions

### 1. WEF, *Top 10 Emerging Technologies of 2025*

| | |
|---|---|
| What it is | Annual World Economic Forum shortlist of technologies judged to be at a turning point: past the lab, not yet mainstream |
| Format | 49-page narrative PDF, one chapter per technology |
| Method | Expert nomination and selection; qualitative assessment of readiness, applications and risks |
| Changes | Yearly, with a new list each edition |
| Reliability | High for direction ("this is becoming real"), low for quantities: the report gives no market sizes |
| Lens in this model | **Readiness**: is the technology real *now*? |
| Extracted | 10 records: turning-point rationale, maturity stage, applications, enablers, constraints, impact area |
| Join key | Technology, through the canonical taxonomy |

### 2. ASPI, *Critical Technology Tracker*

| | |
|---|---|
| What it is | Australian Strategic Policy Institute ranking of which countries and institutions lead research in critical technologies |
| Format | 84-page PDF with country and institution rankings per technology |
| Method | Bibliometrics: share of the top 10% most-cited papers, 2018-2022, with H-index as a secondary quality measure; a "technology monopoly risk" rating per technology |
| Changes | Updated roughly yearly; the research window lags publication by one to two years |
| Reliability | Transparent and reproducible, but it measures research output, not commercial capability |
| Lens in this model | **Capability**: who controls the know-how, and how concentrated is it? |
| Extracted | 44 records: lead country, monopoly risk level, top institutions, concentration note, strategic implication |
| Join key | Technology, through the canonical taxonomy |

### 3. WEF, *Future of Jobs Report 2025*

| | |
|---|---|
| What it is | World Economic Forum outlook on which jobs and skills grow or decline to 2030 |
| Format | 290-page PDF built on a large survey of employers across dozens of economies |
| Method | Employer survey combined with labour-market data; roles ranked by expected growth and decline |
| Changes | Every two to three years |
| Reliability | Good for direction and relative ranking of roles; employer expectations, not observed hiring |
| Lens in this model | **Talent**: where will organisations feel pressure and allocate budget? |
| Extracted | 48 occupations: outlook direction, macro-trends, workflows under pressure, likely budget owner, reskilling and productivity need (1-5) |
| Join key | Occupation, linked to technologies through `bridge_jobs` as *demand* (growing roles that build the technology) or *displacement* (declining roles the technology automates) |

### 4. *State of Italian Venture Capital 2024*

| | |
|---|---|
| What it is | Annual review of the Italian venture capital market: capital invested, deals, sectors, stages, investors and policy |
| Format | 116-page PDF with market tables and commentary |
| Method | Deal-level market data aggregated by sector and stage, compared with the previous year |
| Changes | Yearly |
| Reliability | High for Italy-level totals; thin inside sectors (deeptech has no sub-sector breakdown) |
| Lens in this model | **Capital**: will Italy fund it, and where are the gaps? |
| Extracted | 15 records at three grains: 7 sectors (including the deeptech aggregate), 4 funding stages, 4 market or structural features; capital and deal trend, funding-gap signal, investor mix, policy programmes |
| Join key | VC sector, through `bridge_vc` (direct, or aggregate for deeptech) |

## Why four tables, not one

Each report has its own grain: a technology, an occupation, a sector or a funding stage. Forcing them into one wide sheet would duplicate rows and hide where each number came from. Four tables with a shared provenance block (`record_id`, `source_id`, `time_id`, `geo_id`, `entity_type`, `entity_name`, `entity_domain`, `page_ref`) keep every value traceable to its page, and the crosswalk joins them only at the level they can honestly share: the technology.

## Extending the model

A new source is one more table with the same provenance block and one more bridge table. The 2025 Italian VC reports identified during the internship (Growth Capital's *Venture Capital Report Italy FY-25* and EY's *Venture Capital Barometer 2026*) would replace the 2024 capital lens directly; a second year of each report would let the model measure change instead of levels.
