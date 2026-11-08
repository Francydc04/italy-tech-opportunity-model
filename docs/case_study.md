# Case study: from four PDF reports to a scored opportunity database

Internship at Venture Bottega (venture studio, Rome), December 2025 to April 2026. I worked in a team of two interns and acted as the team's *workflow and understanding lead*: translating what the system did into clear documentation and keeping track of what it was for from an investment point of view. This page describes the project and my part of it. The code in this repository is an independent reimplementation written after the internship; the original prototype and its code belong to Venture Bottega and are not included.

## Timeline

| Date | Step |
|---|---|
| Dec 2025 | Kickoff. First brief: document the studio's AI-assisted research and idea-generation workflow. |
| Jan 2026 | Blueprint for a scraping-based trend tracker (Reddit, Product Hunt, Google Trends). |
| 28 Jan | Change of direction from my supervisor: stop scraping, work **data-first** from four authoritative reports treated as primary sources, and design the database an AI could reason on. |
| 5 Feb | I delivered the data model (four lenses, shared provenance fields) and row-level examples to test it. |
| 26 Feb | I delivered the four datasets, filled by hand from the reports: 117 records, each with its page reference. |
| 5 Mar | Integrated prototype: canonical taxonomy, bridge tables, fact table, scoring and dashboards, reviewed with my supervisor. |
| 12-20 Mar | Audit with my supervisor: seven issues identified, the main ones below, and fixed. |
| 23 Mar | Sourced 2025 replacements for the Italian VC report (Growth Capital, EY barometer) on a finance professor's advice. |
| 8 Apr | Demo Day at LUISS; code and documentation handed over. |

## 1. The question

Four reports each describe innovation from one angle and none of them talk to each other:

| Report | Lens | Question it answers |
|---|---|---|
| WEF, Top 10 Emerging Technologies 2025 | Readiness | Is the technology at a turning point now? |
| ASPI, Critical Technology Tracker | Capability | Who leads the research, and how concentrated is it? |
| WEF, Future of Jobs 2025 | Talent | Where will organisations feel pressure and spend money? |
| State of Italian VC 2024 | Capital | Will Italy fund it, and where is the funding gap? |

A venture idea should pass all four checks. The thesis we wanted the data to surface: **strong technology signal + strong talent demand + weak Italian capital = room for a new venture**, and **strong geopolitical concentration = strategic risk**.

## 2. Data model

Each report became its own table rather than one wide merged sheet, because each has a different grain (a technology, an occupation, a VC sector or stage). Every table carries the same provenance block, so any number can be traced back to a page:

`record_id · source_id · time_id · geo_id · entity_type · entity_name · entity_domain · page_ref`

and then only the fields that carry that report's signal, for example `monopoly_risk_level` and `lead_country` for ASPI, `outlook_direction` and the reskilling and productivity need levels for Future of Jobs, `capital_trend_direction` and `funding_gap_signal` for the VC report. The full field list is in [data_dictionary.md](data_dictionary.md).

## 3. Manual extraction

The reports are narrative PDFs mixing tables, figures and prose, and several fields need judgement (is this technology at a turning point, or only mentioned?). I read the reports and filled the tables by hand following the protocol in [extraction_protocol.md](extraction_protocol.md): one row per entity, controlled vocabularies for categorical fields, ordinal 1-5 scales anchored to the report's wording, and a page reference on every row. Result: 10 + 44 + 48 + 15 = 117 records.

## 4. Integration

The reports name the same technology differently ("Machine learning incl. neural networks and deep learning" in ASPI, "AI and Machine Learning Specialists" in Future of Jobs, "AI ML" in the VC report). A canonical taxonomy of 13 technologies sits in the middle, with one bridge table per source. The first version stored the mappings as semicolon-separated lists matched by string similarity; normalising them into bridge tables turned every link into an equality join.

## 5. Audit: what went wrong in the prototype

The prototype ran, but its dashboards were not saying anything useful. Tracing that back through the data gave the main issues:

| Defect | Effect | Fix in this repository |
|---|---|---|
| Six ASPI names truncated in the crosswalk ("Machine learning" vs the full ASPI name) | Joins returned NULL without error; AI & ML lost all its ASPI evidence | Bridges reference `record_id` with a foreign key; a bad key fails the insert |
| 17 ASPI technologies not mapped at all | Silent coverage gaps | Every record is either mapped or listed in `source_exclusion` with a reason; `vw_unmapped_records` must be empty |
| Tier column filled by hand | 72 of 92 rows had a tier contradicting the score | `score` and `tier` are generated columns and cannot be written |
| Multiplicative coverage penalty (score × coverage) | AI & ML fell from a baseline of 82 to 49.8 | Floor at 70%: score × (0.7 + 0.3 × coverage) |
| Dashboards plotted raw fact rows | 56 of 92 rows were Clean Energy, so every chart looked like a clean-energy report | Every dashboard view returns one row per technology |

Each of these is now a regression test in `tests/test_database.py`.

## 6. What I would do next

- Replace the 2024 VC report with the 2025 sources already identified, and add a second year to every lens so the model can say what is changing, not just what is.
- Map the remaining Future of Jobs occupations (only 14 of 48 are technology-linked today).
- Calibrate the weights against outcomes, for example Italian rounds closed in 2026 by technology, instead of setting them by judgement.
