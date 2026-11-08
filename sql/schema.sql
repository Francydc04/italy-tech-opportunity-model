-- Relational model for four institutional reports, one lens each.
-- SQLite dialect (3.31+ for generated columns). Foreign keys must be enabled
-- per connection: PRAGMA foreign_keys = ON.

-- ---------------------------------------------------------------------------
-- Provenance
-- ---------------------------------------------------------------------------
CREATE TABLE source_report (
    source_id     TEXT PRIMARY KEY,
    title         TEXT NOT NULL,
    publisher     TEXT NOT NULL,
    lens          TEXT NOT NULL CHECK (lens IN ('readiness', 'capability', 'talent', 'capital')),
    evidence_window TEXT NOT NULL
);

-- ---------------------------------------------------------------------------
-- Source tables: one row per entity extracted by hand from each report.
-- Every row keeps the page reference it was read from.
-- ---------------------------------------------------------------------------
CREATE TABLE wef_emerging_tech (
    record_id            TEXT PRIMARY KEY,
    source_id            TEXT NOT NULL REFERENCES source_report(source_id),
    entity_name          TEXT NOT NULL,
    entity_domain        TEXT NOT NULL,
    page_ref             TEXT NOT NULL,
    turning_point_reason TEXT NOT NULL,
    maturity_stage       TEXT NOT NULL,
    maturity_score       REAL NOT NULL CHECK (maturity_score BETWEEN 0 AND 1),
    key_applications     TEXT,
    key_enablers         TEXT,
    constraints          TEXT,
    impact_area          TEXT
);

CREATE TABLE aspi_critical_tech (
    record_id                     TEXT PRIMARY KEY,
    source_id                     TEXT NOT NULL REFERENCES source_report(source_id),
    entity_name                   TEXT NOT NULL UNIQUE,
    entity_domain                 TEXT NOT NULL,
    page_ref                      TEXT NOT NULL,
    lead_country                  TEXT NOT NULL,
    monopoly_risk_level           TEXT NOT NULL CHECK (monopoly_risk_level IN ('low', 'medium', 'high')),
    top_institutions              TEXT,
    capability_concentration_note TEXT,
    strategy_implication          TEXT
);

CREATE TABLE wef_jobs (
    record_id                 TEXT PRIMARY KEY,
    source_id                 TEXT NOT NULL REFERENCES source_report(source_id),
    entity_name               TEXT NOT NULL UNIQUE,
    page_ref                  TEXT NOT NULL,
    outlook_direction         TEXT NOT NULL CHECK (outlook_direction IN ('growing', 'declining')),
    macrotrends_driving_change TEXT,
    workflows_under_pressure  TEXT,
    likely_budget_owner       TEXT,
    reskilling_need_level     INTEGER NOT NULL CHECK (reskilling_need_level BETWEEN 1 AND 5),
    productivity_need_level   INTEGER NOT NULL CHECK (productivity_need_level BETWEEN 1 AND 5)
);

CREATE TABLE italian_vc (
    record_id               TEXT PRIMARY KEY,
    source_id               TEXT NOT NULL REFERENCES source_report(source_id),
    entity_type             TEXT NOT NULL CHECK (entity_type IN ('market_overview', 'sector', 'stage', 'structural')),
    entity_name             TEXT NOT NULL,
    page_ref                TEXT NOT NULL,
    capital_trend           TEXT CHECK (capital_trend IN ('up', 'stable', 'down', 'emerging')),
    capital_trend_note      TEXT,
    deal_trend              TEXT CHECK (deal_trend IN ('up', 'stable', 'down')),
    funding_gap_signal      TEXT,
    investor_mix_signal     TEXT,
    policy_tailwind         INTEGER NOT NULL CHECK (policy_tailwind IN (0, 1)),
    policy_programs         TEXT
);

-- ---------------------------------------------------------------------------
-- Canonical taxonomy and bridge tables.
-- Bridges key on record_id, never on free-text names, so a truncated or
-- mistyped name cannot silently drop a join: the insert fails instead.
-- ---------------------------------------------------------------------------
CREATE TABLE canonical_technology (
    tech_code            TEXT PRIMARY KEY,
    canonical_technology TEXT NOT NULL UNIQUE,
    description          TEXT
);

CREATE TABLE bridge_wef (
    record_id TEXT NOT NULL REFERENCES wef_emerging_tech(record_id),
    tech_code TEXT NOT NULL REFERENCES canonical_technology(tech_code),
    rationale TEXT NOT NULL,
    PRIMARY KEY (record_id, tech_code)
);

CREATE TABLE bridge_aspi (
    record_id TEXT NOT NULL REFERENCES aspi_critical_tech(record_id),
    tech_code TEXT NOT NULL REFERENCES canonical_technology(tech_code),
    rationale TEXT NOT NULL,
    PRIMARY KEY (record_id, tech_code)
);

CREATE TABLE bridge_jobs (
    record_id   TEXT NOT NULL REFERENCES wef_jobs(record_id),
    tech_code   TEXT NOT NULL REFERENCES canonical_technology(tech_code),
    signal_role TEXT NOT NULL CHECK (signal_role IN ('demand', 'displacement')),
    rationale   TEXT NOT NULL,
    PRIMARY KEY (record_id, tech_code)
);

CREATE TABLE bridge_vc (
    record_id   TEXT NOT NULL REFERENCES italian_vc(record_id),
    tech_code   TEXT NOT NULL REFERENCES canonical_technology(tech_code),
    granularity TEXT NOT NULL CHECK (granularity IN ('direct', 'aggregate')),
    rationale   TEXT NOT NULL,
    PRIMARY KEY (record_id, tech_code)
);

-- Records deliberately left out of the taxonomy, with the reason.
-- Together with the bridges this makes coverage auditable: every record is
-- either mapped or explicitly excluded (see vw_unmapped_records).
CREATE TABLE source_exclusion (
    source    TEXT NOT NULL CHECK (source IN ('wef', 'aspi', 'jobs', 'vc')),
    record_id TEXT NOT NULL,
    reason    TEXT NOT NULL,
    PRIMARY KEY (source, record_id)
);

-- ---------------------------------------------------------------------------
-- Long fact table: one row per (technology, source record) signal.
-- ---------------------------------------------------------------------------
CREATE VIEW fact_signal AS
SELECT b.tech_code, 'readiness' AS lens, w.record_id, w.entity_name,
       w.maturity_score AS signal_value, NULL AS signal_role, w.page_ref
FROM bridge_wef b JOIN wef_emerging_tech w USING (record_id)
UNION ALL
SELECT b.tech_code, 'capability', a.record_id, a.entity_name,
       CASE a.monopoly_risk_level WHEN 'low' THEN 0.0 WHEN 'medium' THEN 0.5 ELSE 1.0 END,
       a.lead_country, a.page_ref
FROM bridge_aspi b JOIN aspi_critical_tech a USING (record_id)
UNION ALL
SELECT b.tech_code, 'talent', j.record_id, j.entity_name,
       CASE b.signal_role WHEN 'demand' THEN j.productivity_need_level / 5.0
                          ELSE j.reskilling_need_level / 5.0 END,
       b.signal_role, j.page_ref
FROM bridge_jobs b JOIN wef_jobs j USING (record_id)
UNION ALL
SELECT b.tech_code, 'capital', v.record_id, v.entity_name,
       -- capital gap: weak or falling capital leaves room for new ventures
       (CASE v.capital_trend WHEN 'up' THEN 0.2 WHEN 'stable' THEN 0.5 ELSE 0.8 END
        - 0.5) * CASE b.granularity WHEN 'direct' THEN 1.0 ELSE 0.5 END + 0.5,
       b.granularity, v.page_ref
FROM bridge_vc b JOIN italian_vc v USING (record_id);

-- One row per technology with one value per lens (NULL when the lens is silent).
CREATE VIEW vw_tech_lenses AS
SELECT c.tech_code,
       c.canonical_technology,
       (SELECT MAX(signal_value) FROM fact_signal f WHERE f.tech_code = c.tech_code AND lens = 'readiness')  AS readiness,
       (SELECT 1 - AVG(signal_value) FROM fact_signal f WHERE f.tech_code = c.tech_code AND lens = 'capability') AS capability_access,
       (SELECT AVG(signal_value) FROM fact_signal f WHERE f.tech_code = c.tech_code AND lens = 'talent')     AS talent_pull,
       (SELECT AVG(signal_value) FROM fact_signal f WHERE f.tech_code = c.tech_code AND lens = 'capital')    AS capital_gap,
       (SELECT COUNT(*) FROM fact_signal f WHERE f.tech_code = c.tech_code) AS n_signals
FROM canonical_technology c;

-- ---------------------------------------------------------------------------
-- Opportunity score. Score, coverage and tier are generated columns: they
-- cannot be written by hand and cannot drift away from the lens values.
--
--   base  = weighted mean of the available lenses (weights renormalised)
--   score = 100 * base * (0.7 + 0.3 * coverage)
--
-- The 70% floor keeps a technology with strong but partial evidence from
-- being ranked below one with weak but complete evidence.
-- ---------------------------------------------------------------------------
CREATE TABLE tech_opportunity (
    tech_code         TEXT PRIMARY KEY REFERENCES canonical_technology(tech_code),
    readiness         REAL CHECK (readiness BETWEEN 0 AND 1),
    capability_access REAL CHECK (capability_access BETWEEN 0 AND 1),
    talent_pull       REAL CHECK (talent_pull BETWEEN 0 AND 1),
    capital_gap       REAL CHECK (capital_gap BETWEEN 0 AND 1),
    coverage REAL GENERATED ALWAYS AS (
        ((readiness IS NOT NULL) + (capability_access IS NOT NULL)
         + (talent_pull IS NOT NULL) + (capital_gap IS NOT NULL)) / 4.0) STORED,
    base_score REAL GENERATED ALWAYS AS (
        (0.30 * COALESCE(readiness, 0) + 0.20 * COALESCE(capability_access, 0)
         + 0.30 * COALESCE(talent_pull, 0) + 0.20 * COALESCE(capital_gap, 0))
        / NULLIF(0.30 * (readiness IS NOT NULL) + 0.20 * (capability_access IS NOT NULL)
                 + 0.30 * (talent_pull IS NOT NULL) + 0.20 * (capital_gap IS NOT NULL), 0)) STORED,
    score REAL GENERATED ALWAYS AS (
        ROUND(100 * base_score * (0.7 + 0.3 * coverage), 2)) STORED,
    tier TEXT GENERATED ALWAYS AS (
        CASE WHEN score >= 70 THEN 'High' WHEN score >= 50 THEN 'Medium' ELSE 'Low' END) STORED
);

-- ---------------------------------------------------------------------------
-- Audit and analysis views
-- ---------------------------------------------------------------------------
CREATE VIEW vw_unmapped_records AS
SELECT 'wef' AS source, record_id, entity_name FROM wef_emerging_tech
WHERE record_id NOT IN (SELECT record_id FROM bridge_wef)
  AND record_id NOT IN (SELECT record_id FROM source_exclusion WHERE source = 'wef')
UNION ALL
SELECT 'aspi', record_id, entity_name FROM aspi_critical_tech
WHERE record_id NOT IN (SELECT record_id FROM bridge_aspi)
  AND record_id NOT IN (SELECT record_id FROM source_exclusion WHERE source = 'aspi')
UNION ALL
SELECT 'vc', record_id, entity_name FROM italian_vc
WHERE entity_type = 'sector'
  AND record_id NOT IN (SELECT record_id FROM bridge_vc)
  AND record_id NOT IN (SELECT record_id FROM source_exclusion WHERE source = 'vc');

CREATE VIEW vw_signal_presence AS
SELECT c.tech_code, c.canonical_technology,
       SUM(f.lens = 'readiness')  AS n_readiness,
       SUM(f.lens = 'capability') AS n_capability,
       SUM(f.lens = 'talent')     AS n_talent,
       SUM(f.lens = 'capital')    AS n_capital
FROM canonical_technology c LEFT JOIN fact_signal f USING (tech_code)
GROUP BY c.tech_code, c.canonical_technology;

CREATE VIEW vw_geopolitical_concentration AS
SELECT c.canonical_technology, a.lead_country, a.monopoly_risk_level, COUNT(*) AS n_technologies
FROM bridge_aspi b
JOIN aspi_critical_tech a USING (record_id)
JOIN canonical_technology c USING (tech_code)
GROUP BY c.canonical_technology, a.lead_country, a.monopoly_risk_level;

CREATE VIEW vw_opportunity_ranking AS
SELECT c.canonical_technology, o.*,
       RANK() OVER (ORDER BY o.score DESC) AS score_rank
FROM tech_opportunity o JOIN canonical_technology c USING (tech_code);
