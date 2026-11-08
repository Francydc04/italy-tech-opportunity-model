# Extraction protocol

How the 117 records in `data/raw/` were read out of the four reports by hand.

## Rules applied to every report

1. **One row per entity at the report's own grain**: a technology for WEF and ASPI, an occupation for Future of Jobs, a sector, stage or structural feature for the VC report.
2. **Use the report's own name** for `entity_name`, in full. Harmonisation happens later in the crosswalk, never in the source table, so the source stays checkable against the PDF.
3. **Every row carries `page_ref`**: the table, figure or page numbers where the evidence sits.
4. **Controlled vocabularies** for categorical signals (`low / medium / high`, `growing / declining`, `up / stable / down`), so values can be compared and constrained in SQL.
5. **Ordinal 1-5 scales** where the report gives intensity in prose. For reskilling and productivity need this produced three clear groups: fast-growing technology roles at 4 and 4-5, declining clerical roles at 5 reskilling and 2 productivity, and roles the report lists for volume rather than technology at 3 and 3.
6. **Short free-text fields are allowed only for context** a later reader needs (`capability_concentration_note`, `strategy_implication`, `notes`). Signals that feed the score are never free text.

## Report-specific choices

**WEF Top 10 Emerging Technologies 2025.** All ten technologies, with the "why now" rationale, maturity stage, applications, enablers and constraints. Maturity is later grouped into three bands (`data/crosswalk/wef_maturity_band.csv`): deployment, early commercial, pilot or clinical.

**ASPI Critical Technology Tracker.** All 44 technologies. `lead_country` and `monopoly_risk_level` come from ASPI's own technology monopoly risk ranking; the method (top 10% most-cited papers, 2018-2022) is recorded in `method_basis` so the signal's limits stay visible.

**WEF Future of Jobs 2025.** The fastest-growing and fastest-declining roles in the report's figures, plus the largest absolute movers: 48 occupations with outlook, macro-trends, workflows under pressure and the likely budget owner.

**State of Italian VC 2024.** Fifteen records at three grains: six sectors plus a deeptech aggregate, four funding stages, and structural features (LP base, ESG inflows, data-driven VC). Trend fields keep the report's figure in the note (for example `down (fundraising -30%)`); the loader extracts the direction.

## Known limitations

- Single reader: no second coder, so no inter-rater agreement measure.
- The VC report gives no breakdown inside deeptech, so quantum, semiconductors, materials and biotech share one aggregate record; the scoring halves its weight for that reason.
- The four reports cover different windows (2018-2022 for ASPI, 2024 for VC, 2025 onwards for WEF), so the model compares levels, not changes.
