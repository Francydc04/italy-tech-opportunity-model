"""Tests for the relational model.

Several of them are regression tests for the failure modes found while
auditing the first prototype: silently broken joins, tiers that disagree with
scores, an over-aggressive coverage penalty and dashboards skewed by row counts.
"""
import sqlite3

import numpy as np
import pandas as pd
import pytest

from iis.build import build, load_frames, repair_wef
from iis.scoring import LENSES, score


@pytest.fixture(scope="module")
def con(tmp_path_factory):
    c = build(tmp_path_factory.mktemp("db") / "iis.db")
    yield c
    c.close()


def one(con, sql, *args):
    return con.execute(sql, args).fetchone()[0]


# --- extraction ------------------------------------------------------------

def test_all_117_hand_extracted_records_load(con):
    counts = [one(con, f"SELECT COUNT(*) FROM {t}")
              for t in ("wef_emerging_tech", "aspi_critical_tech", "wef_jobs", "italian_vc")]
    assert counts == [10, 44, 48, 15]


def test_every_record_keeps_its_page_reference(con):
    for t in ("wef_emerging_tech", "aspi_critical_tech", "wef_jobs", "italian_vc"):
        assert one(con, f"SELECT COUNT(*) FROM {t} WHERE page_ref IS NULL OR page_ref = ''") == 0


def test_split_wef_row_is_repaired():
    raw = pd.DataFrame({"record_id": ["A", "B", None], "entity_name": ["x", None, "y"]})
    fixed = repair_wef(raw)
    assert fixed["entity_name"].tolist() == ["x", "y"]


def test_vc_trend_text_is_normalised():
    vc = load_frames()["vc"]
    assert set(vc["capital_trend"].dropna()) <= {"up", "down", "stable", "emerging"}
    lp = vc.loc[vc["entity_name"] == "LP Structure"].iloc[0]
    assert lp["capital_trend"] == "down" and "-30%" in lp["capital_trend_note"]


# --- integrity: the join failures cannot happen ------------------------------

def test_bridge_rejects_a_truncated_record_id(con):
    """The prototype joined on free-text names, so 'Machine learning' silently
    failed to match 'Machine learning incl. neural networks...'. Bridges now
    reference record_id with a foreign key: a bad key is an error, not a NULL."""
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("INSERT INTO bridge_aspi VALUES ('ASPI_CTT_2023_QC_01', 'AI', 'typo')")


def test_every_source_record_is_mapped_or_explicitly_excluded(con):
    assert one(con, "SELECT COUNT(*) FROM vw_unmapped_records") == 0


def test_check_constraints_reject_out_of_range_values(con):
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("UPDATE aspi_critical_tech SET monopoly_risk_level = 'severe' WHERE record_id = 'ASPI_CTT_2023_QC_001'")
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("UPDATE wef_jobs SET reskilling_need_level = 7 WHERE record_id = 'WEFJ25_0001'")


# --- scoring -----------------------------------------------------------------

def test_tier_always_agrees_with_score(con):
    """In the prototype 72 of 92 rows had a hand-entered tier contradicting the
    computed score. Tier is now a generated column."""
    bad = one(con, """SELECT COUNT(*) FROM tech_opportunity WHERE tier !=
                      CASE WHEN score >= 70 THEN 'High' WHEN score >= 50 THEN 'Medium' ELSE 'Low' END""")
    assert bad == 0
    with pytest.raises(sqlite3.OperationalError):
        con.execute("UPDATE tech_opportunity SET tier = 'High' WHERE tech_code = 'BIO'")


def test_score_follows_lens_updates(con):
    before = one(con, "SELECT score FROM tech_opportunity WHERE tech_code = 'ROB'")
    con.execute("UPDATE tech_opportunity SET talent_pull = 1.0 WHERE tech_code = 'ROB'")
    after = one(con, "SELECT score FROM tech_opportunity WHERE tech_code = 'ROB'")
    con.rollback()
    assert after > before


def test_coverage_floor_bounds_the_penalty():
    """A technology with perfect evidence on half the lenses keeps 85% of its
    base score, not 50% as under the multiplicative rule."""
    x = pd.DataFrame([[1.0, 1.0, np.nan, np.nan]], columns=LENSES)
    assert score(x).iloc[0] == pytest.approx(85.0)
    assert score(x, rule="multiplicative").iloc[0] == pytest.approx(50.0)


def test_python_scoring_matches_sql(con):
    df = pd.read_sql("SELECT * FROM tech_opportunity", con).set_index("tech_code")
    assert np.allclose(score(df[LENSES]), df["score"], atol=0.01)


def test_one_row_per_technology_in_dashboard_views(con):
    """The prototype charted raw fact rows, 56 of 92 of which were Clean Energy.
    Every dashboard view now returns exactly one row per canonical technology."""
    n_tech = one(con, "SELECT COUNT(*) FROM canonical_technology")
    for view in ("vw_tech_lenses", "vw_signal_presence", "vw_opportunity_ranking"):
        assert one(con, f"SELECT COUNT(*) FROM {view}") == n_tech
