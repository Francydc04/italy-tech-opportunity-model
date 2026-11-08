-- Example analytical queries against results/iis.db.

-- 1. Ranking with the evidence behind every score.
SELECT r.canonical_technology, r.score, r.tier, r.coverage,
       p.n_readiness, p.n_capability, p.n_talent, p.n_capital
FROM vw_opportunity_ranking r
JOIN vw_signal_presence p USING (tech_code)
ORDER BY r.score DESC;

-- 2. Trace one score back to the pages it came from.
SELECT lens, entity_name, ROUND(signal_value, 2) AS signal_value, signal_role, page_ref
FROM fact_signal
WHERE tech_code = 'AI'
ORDER BY lens, signal_value DESC;

-- 3. Talent pressure without matching Italian capital: the venture-studio thesis.
SELECT canonical_technology, ROUND(talent_pull, 2) AS talent_pull, ROUND(capital_gap, 2) AS capital_gap, score
FROM vw_opportunity_ranking
WHERE talent_pull >= 0.8 AND capital_gap >= 0.5
ORDER BY score DESC;

-- 4. Strategic dependency: high-monopoly-risk technologies and who leads them.
SELECT c.canonical_technology, a.entity_name, a.lead_country, a.page_ref
FROM aspi_critical_tech a
JOIN bridge_aspi b USING (record_id)
JOIN canonical_technology c USING (tech_code)
WHERE a.monopoly_risk_level = 'high'
ORDER BY c.canonical_technology;

-- 5. Coverage audit: what was deliberately left out, and why.
SELECT source, record_id, reason FROM source_exclusion ORDER BY source, record_id;

-- 6. Italian funding by stage: where the funnel narrows.
SELECT entity_name, capital_trend, deal_trend, funding_gap_signal
FROM italian_vc
WHERE entity_type = 'stage'
ORDER BY record_id;
