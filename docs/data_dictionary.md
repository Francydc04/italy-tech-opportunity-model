# Data dictionary

The full schema with constraints is `sql/schema.sql`; the diagram is `images/er_diagram.png`.

## Shared provenance fields (all four source tables)

| Field | Meaning |
|---|---|
| `record_id` | Stable key, prefixed by source (e.g. `ASPI_CTT_2023_QC_010`) |
| `source_id` | Report, references `source_report` |
| `entity_name` | Name exactly as written in the report |
| `entity_domain` | Report's own grouping (e.g. "Quantum", "Jobs outlook") |
| `page_ref` | Pages, tables or figures the row was read from |

## Lens-specific fields

| Table | Field | Values | Used for |
|---|---|---|---|
| `wef_emerging_tech` | `turning_point_reason` | text | context |
| | `maturity_stage` / `maturity_score` | text / 0.5, 0.75, 1.0 | readiness |
| | `key_applications`, `key_enablers`, `constraints`, `impact_area` | text | context, filtering |
| `aspi_critical_tech` | `lead_country` | country | concentration analysis |
| | `monopoly_risk_level` | low, medium, high | capability access |
| | `top_institutions`, `strategy_implication` | text | context |
| `wef_jobs` | `outlook_direction` | growing, declining | demand vs displacement |
| | `reskilling_need_level`, `productivity_need_level` | 1-5 | talent pull |
| | `workflows_under_pressure`, `likely_budget_owner` | text | who pays |
| `italian_vc` | `entity_type` | market_overview, sector, stage, structural | grain |
| | `capital_trend`, `deal_trend` | up, stable, down, emerging | capital gap |
| | `funding_gap_signal`, `policy_tailwind`, `policy_programs` | text, 0/1, text | context |

## Lens scores (0-1, NULL when the lens has no evidence)

| Lens | Definition |
|---|---|
| Readiness | Highest maturity score among the technology's WEF turning-point entries |
| Capability access | 1 − mean ASPI monopoly risk (low 0, medium 0.5, high 1) |
| Talent pull | Mean over linked occupations of productivity need / 5 (growing roles) or reskilling need / 5 (declining roles exposed to the technology) |
| Capital gap | 0.8 if Italian capital is falling, 0.5 stable, 0.2 rising; pulled halfway to 0.5 when the only evidence is the deeptech aggregate |

## Score

`base` = weighted mean of the available lenses, weights 0.30 readiness, 0.20 capability, 0.30 talent, 0.20 capital, renormalised over the lenses present.
`score` = 100 × base × (0.7 + 0.3 × coverage), where coverage is the share of lenses with evidence.
`tier` = High from 70, Medium from 50, otherwise Low.
