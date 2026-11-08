"""Build the SQLite database from the hand-extracted report datasets.

Usage: python -m iis.build [--db results/iis.db]
"""
from __future__ import annotations

import argparse
import re
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
XWALK = ROOT / "data" / "crosswalk"
SCHEMA = ROOT / "sql" / "schema.sql"

SOURCES = [
    ("SRC_WEF_TOP10_2025", "Top 10 Emerging Technologies of 2025", "World Economic Forum", "readiness", "2025"),
    ("ASPI_CTT_2023", "Critical Technology Tracker", "Australian Strategic Policy Institute", "capability", "2018-2022"),
    ("WEF_FOJ_2025", "Future of Jobs Report 2025", "World Economic Forum", "talent", "2025-2030"),
    ("src_state_italian_vc_2024", "State of Italian Venture Capital 2024", "Italian VC industry report", "capital", "2024"),
]
MATURITY_SCORE = {"deployment": 1.0, "early_commercial": 0.75, "pilot_clinical": 0.5}


def read_raw(name: str) -> pd.DataFrame:
    """Raw files are semicolon-separated UTF-8 with BOM, as exported from Excel."""
    df = pd.read_csv(RAW / name, sep=";", encoding="utf-8-sig", dtype=str)
    return df.apply(lambda s: s.str.strip() if s.dtype == object else s)


def repair_wef(df: pd.DataFrame) -> pd.DataFrame:
    """The Excel export split the tenth record across two lines: the entity
    name landed on an orphan line with every other field empty. Re-attach it."""
    orphans = df[df["record_id"].isna() & df["entity_name"].notna()]
    missing = df[df["record_id"].notna() & df["entity_name"].isna()]
    if len(orphans) != len(missing):
        raise ValueError("cannot pair orphan WEF lines with their records")
    df = df.copy()
    for (_, orphan), (idx, _) in zip(orphans.iterrows(), missing.iterrows()):
        df.loc[idx, "entity_name"] = orphan["entity_name"]
    return df[df["record_id"].notna()].reset_index(drop=True)


def first_word_trend(value: str | float) -> str | None:
    """'down (fundraising -30%)' -> 'down'; keeps the note separately."""
    if not isinstance(value, str):
        return None
    m = re.match(r"\s*(up|down|stable|emerging)\b", value, flags=re.I)
    return m.group(1).lower() if m else None


def load_frames() -> dict[str, pd.DataFrame]:
    wef = repair_wef(read_raw("wef_emerging_tech_2025.csv"))
    bands = pd.read_csv(XWALK / "wef_maturity_band.csv")
    wef = wef.merge(bands[["record_id", "maturity_band"]], on="record_id", how="left", validate="1:1")
    if wef["maturity_band"].isna().any():
        raise ValueError("every WEF record needs a maturity band")
    wef["maturity_score"] = wef["maturity_band"].map(MATURITY_SCORE)

    aspi = read_raw("aspi_critical_tech_tracker.csv")
    aspi["monopoly_risk_level"] = aspi["monopoly_risk_level"].str.lower()

    jobs = read_raw("wef_future_of_jobs_2025.csv")
    for col in ("reskilling_need_level", "productivity_need_level"):
        jobs[col] = jobs[col].astype(int)

    vc = read_raw("italian_vc_2024.csv")
    vc["capital_trend"] = vc["capital_trend_direction"].map(first_word_trend)
    vc["capital_trend_note"] = vc["capital_trend_direction"]
    vc["deal_trend"] = vc["deal_trend_direction"].map(first_word_trend)
    vc["policy_tailwind"] = vc["policy_tailwind_flag"].str.upper().eq("TRUE").astype(int)
    return {"wef": wef, "aspi": aspi, "jobs": jobs, "vc": vc}


def build(db_path: Path | str = ROOT / "results" / "iis.db") -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text())

    con.executemany("INSERT INTO source_report VALUES (?, ?, ?, ?, ?)", SOURCES)
    f = load_frames()

    def insert(table: str, df: pd.DataFrame, cols: list[str]) -> None:
        rows = df[cols].astype(object).where(df[cols].notna(), None).values.tolist()
        con.executemany(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", rows)

    insert("wef_emerging_tech", f["wef"], [
        "record_id", "source_id", "entity_name", "entity_domain", "page_ref", "turning_point_reason",
        "maturity_stage", "maturity_score", "key_applications", "key_enablers", "constraints", "impact_area"])
    insert("aspi_critical_tech", f["aspi"], [
        "record_id", "source_id", "entity_name", "entity_domain", "page_ref", "lead_country",
        "monopoly_risk_level", "top_institutions", "capability_concentration_note", "strategy_implication"])
    insert("wef_jobs", f["jobs"], [
        "record_id", "source_id", "entity_name", "page_ref", "outlook_direction", "macrotrends_driving_change",
        "workflows_under_pressure", "likely_budget_owner", "reskilling_need_level", "productivity_need_level"])
    insert("italian_vc", f["vc"], [
        "record_id", "source_id", "entity_type", "entity_name", "page_ref", "capital_trend", "capital_trend_note",
        "deal_trend", "funding_gap_signal", "investor_mix_signal", "policy_tailwind", "policy_programs"])

    insert("canonical_technology", pd.read_csv(XWALK / "canonical_technology.csv"),
           ["tech_code", "canonical_technology", "description"])
    insert("bridge_wef", pd.read_csv(XWALK / "map_wef_tech.csv"), ["record_id", "tech_code", "rationale"])
    insert("bridge_aspi", pd.read_csv(XWALK / "map_aspi_tech.csv"), ["record_id", "tech_code", "rationale"])
    insert("bridge_jobs", pd.read_csv(XWALK / "map_jobs_tech.csv"), ["record_id", "tech_code", "signal_role", "rationale"])
    insert("bridge_vc", pd.read_csv(XWALK / "map_vc_tech.csv"), ["record_id", "tech_code", "granularity", "rationale"])
    insert("source_exclusion", pd.read_csv(XWALK / "exclusions.csv"), ["source", "record_id", "reason"])

    con.execute("""
        INSERT INTO tech_opportunity (tech_code, readiness, capability_access, talent_pull, capital_gap)
        SELECT tech_code, readiness, capability_access, talent_pull, capital_gap FROM vw_tech_lenses""")
    con.commit()
    return con


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", default=str(ROOT / "results" / "iis.db"))
    con = build(p.parse_args().db)
    n = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
         for t in ("wef_emerging_tech", "aspi_critical_tech", "wef_jobs", "italian_vc")}
    print("source records:", n, "total", sum(n.values()))
    print("unmapped records:", con.execute("SELECT COUNT(*) FROM vw_unmapped_records").fetchone()[0])


if __name__ == "__main__":
    main()
