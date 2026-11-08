"""Builds the database, runs the analysis and writes every figure and table.

Usage (from the repository root): python analysis/run_analysis.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from iis.build import build  # noqa: E402
from iis.scoring import LENSES, contributions, score, weight_sensitivity  # noqa: E402

IMG = ROOT / "images"; RES = ROOT / "results"
IMG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)

BLUE, ORANGE, AQUA, YELLOW, MAGENTA = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"
INK, MUTED, GRID, NEUTRAL = "#1f2328", "#6b7280", "#e6e8eb", "#c4c9d0"
LENS_COLOR = {"readiness": BLUE, "capability_access": AQUA, "talent_pull": ORANGE, "capital_gap": YELLOW}
LENS_LABEL = {"readiness": "Technology readiness (WEF)", "capability_access": "Capability access (ASPI)",
              "talent_pull": "Talent pull (Future of Jobs)", "capital_gap": "Capital gap (Italian VC)"}

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": MUTED,
    "xtick.color": MUTED, "ytick.color": INK, "axes.titlesize": 13, "axes.titleweight": "bold",
    "axes.titlecolor": INK, "axes.titlelocation": "left", "axes.spines.top": False,
    "axes.spines.right": False, "figure.facecolor": "white", "savefig.dpi": 200, "savefig.bbox": "tight",
})


def subtitle(ax, text):
    ax.text(0, 1.02, text, transform=ax.transAxes, color=MUTED, fontsize=9.5, va="bottom")


def main() -> None:
    con = build(RES / "iis.db")
    q = lambda sql: pd.read_sql(sql, con)
    ranking = q("SELECT * FROM vw_opportunity_ranking ORDER BY score DESC").set_index("canonical_technology")
    ranking.to_csv(RES / "opportunity_ranking.csv")
    lenses = ranking[LENSES]

    # Python mirror must agree with the SQL generated columns.
    assert np.allclose(score(lenses), ranking["score"], atol=0.01)

    # 1. Ranking with additive lens contributions -------------------------------------------
    c = contributions(lenses).iloc[::-1]
    fig, ax = plt.subplots(figsize=(10, 6.2))
    left = np.zeros(len(c))
    for lens in LENSES:
        ax.barh(c.index, c[lens], left=left, color=LENS_COLOR[lens], height=0.62,
                edgecolor="white", linewidth=1.5, label=LENS_LABEL[lens])
        left += c[lens].to_numpy()
    for y, (tech, row) in enumerate(ranking.iloc[::-1].iterrows()):
        ax.text(row["score"] + 1, y, f"{row['score']:.0f}  {row['tier']}", va="center", fontsize=9, color=INK)
    ax.set_xlim(0, 105); ax.set_xlabel("Opportunity score (0-100)")
    ax.grid(axis="x", color=GRID, linewidth=0.6); ax.set_axisbelow(True); ax.tick_params(axis="y", length=0)
    ax.set_title("Where four institutional reports agree: opportunity score by technology", pad=26)
    subtitle(ax, "Bar segments = each lens's contribution; missing lenses lower the score through a 70% coverage floor")
    ax.legend(loc="lower right", frameon=False, fontsize=8.5)
    fig.savefig(IMG / "opportunity_ranking.png"); plt.close(fig)

    # 2. Evidence coverage heatmap ---------------------------------------------------------
    pres = q("SELECT * FROM vw_signal_presence").set_index("canonical_technology").loc[ranking.index]
    m = pres[["n_readiness", "n_capability", "n_talent", "n_capital"]].to_numpy()
    fig, ax = plt.subplots(figsize=(7.6, 6.4))
    cmap = plt.matplotlib.colors.LinearSegmentedColormap.from_list("b", ["#f3f6fa", "#9ec2ee", BLUE, "#174f94"])
    ax.imshow(np.where(m == 0, np.nan, m), cmap=cmap, vmin=0, vmax=m.max(), aspect="auto")
    for (i, j), v in np.ndenumerate(m):
        ax.add_patch(plt.Rectangle((j - .5, i - .5), 1, 1, fill=v == 0, color="#f6f7f9", ec="white", lw=2))
        ax.text(j, i, "none" if v == 0 else str(v), ha="center", va="center",
                color=MUTED if v == 0 else ("white" if v >= 3 else INK), fontsize=9)
    ax.set_xticks(range(4), ["WEF\nEmerging Tech", "ASPI\nCritical Tech", "WEF Future\nof Jobs", "State of\nItalian VC"])
    ax.set_yticks(range(len(pres)), pres.index); ax.tick_params(length=0)
    for s in ax.spines.values(): s.set_visible(False)
    ax.set_title("Evidence behind each score", pad=26)
    subtitle(ax, "Number of source records mapped to each canonical technology")
    fig.savefig(IMG / "signal_coverage.png"); plt.close(fig)

    # 3. The coverage-penalty bug: multiplicative vs floored ----------------------------------
    s_mult = score(lenses, rule="multiplicative"); s_floor = ranking["score"]
    r_mult = s_mult.rank(ascending=False, method="min"); r_floor = s_floor.rank(ascending=False, method="min")
    fig, ax = plt.subplots(figsize=(8.4, 6.4))
    label_y = s_floor.sort_values().copy()
    for i in range(1, len(label_y)):  # keep labels at least 2.4 points apart
        label_y.iloc[i] = max(label_y.iloc[i], label_y.iloc[i - 1] + 2.4)
    tier = lambda v: "High" if v >= 70 else ("Medium" if v >= 50 else "Low")
    for tech in ranking.index:
        col = ORANGE if lenses.loc[tech].isna().any() else NEUTRAL
        ax.plot([0, 1], [s_mult[tech], s_floor[tech]], color=col, lw=1.8, marker="o", ms=5)
        flip = "" if tier(s_mult[tech]) == tier(s_floor[tech]) else f"  ({tier(s_mult[tech])} -> {tier(s_floor[tech])})"
        ax.text(1.04, label_y[tech], tech + flip, va="center", fontsize=8.5, color=INK)
    ax.set_xticks([0, 1], ["Multiplicative penalty\nbase x coverage", "70% floor\nbase x (0.7 + 0.3 x coverage)"])
    ax.set_xlim(-0.15, 2.0); ax.set_ylabel("Opportunity score")
    ax.grid(axis="y", color=GRID, linewidth=0.6); ax.spines["bottom"].set_visible(False)
    ax.set_title("How the coverage penalty was distorting the ranking", pad=26)
    subtitle(ax, "Orange = missing at least one lens. Brackets: tier under the multiplicative rule -> tier under the floor")
    fig.savefig(IMG / "coverage_penalty.png"); plt.close(fig)
    pd.DataFrame({"score_multiplicative": s_mult, "rank_multiplicative": r_mult,
                  "score_floor": s_floor, "rank_floor": r_floor}).to_csv(RES / "coverage_penalty.csv")

    # 4. Weight sensitivity -----------------------------------------------------------------
    ranks = weight_sensitivity(lenses)
    summ = pd.DataFrame({"median_rank": ranks.median(), "p05": ranks.quantile(0.05), "p95": ranks.quantile(0.95),
                         "p_top3": (ranks <= 3).mean(), "p_top5": (ranks <= 5).mean()}).loc[ranking.index]
    summ.to_csv(RES / "weight_sensitivity.csv")
    fig, ax = plt.subplots(figsize=(9.2, 6.2))
    y = np.arange(len(summ))[::-1]
    ax.hlines(y, summ["p05"], summ["p95"], color=BLUE, lw=6, alpha=0.3)
    ax.plot(summ["median_rank"], y, "o", color=BLUE, ms=7)
    for yi, (tech, r) in zip(y, summ.iterrows()):
        ax.text(1.03, yi, f"{100 * r['p_top3']:.0f}%", va="center", ha="left", fontsize=9, color=INK,
                transform=ax.get_yaxis_transform())
    ax.text(1.03, len(summ) - 0.3, "P(top 3)", ha="left", fontsize=9, color=MUTED, weight="bold",
            transform=ax.get_yaxis_transform())
    ax.set_yticks(y, summ.index); ax.set_xlim(0.5, 13.5); ax.set_xticks(range(1, 14))
    ax.set_xlabel("Rank (1 = best)"); ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", color=GRID, linewidth=0.6); ax.set_axisbelow(True)
    ax.set_title("Is the ranking an artefact of the weights?", pad=26)
    subtitle(ax, "10,000 weight vectors from a Dirichlet centred on (0.3, 0.2, 0.3, 0.2); dot = median rank, bar = 5th-95th percentile")
    fig.savefig(IMG / "weight_sensitivity.png"); plt.close(fig)

    # 6. Geopolitical concentration -------------------------------------------------------
    g = q("SELECT * FROM vw_geopolitical_concentration")
    order = g.groupby("canonical_technology")["n_technologies"].sum().sort_values().index
    risk_cols = {"low": "#cfe0f6", "medium": "#7fb0ea", "high": BLUE}
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 5.6), sharey=True, sharex=True)
    for ax, country in zip(axes, ["China", "USA"]):
        sub = g[g["lead_country"] == country].pivot_table(index="canonical_technology", columns="monopoly_risk_level",
                                                           values="n_technologies", aggfunc="sum").reindex(order).fillna(0)
        left = np.zeros(len(order))
        for lvl in ["low", "medium", "high"]:
            v = sub.get(lvl, pd.Series(0, index=order)).to_numpy()
            ax.barh(order, v, left=left, color=risk_cols[lvl], edgecolor="white", linewidth=1.5, label=f"{lvl} monopoly risk")
            left += v
        ax.set_title(f"Research led by {country}", fontsize=11); ax.tick_params(axis="y", length=0)
        ax.grid(axis="x", color=GRID, linewidth=0.6); ax.set_axisbelow(True); ax.set_xlabel("ASPI technologies")
        ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
    axes[1].legend(frameon=False, fontsize=8.5, loc="lower right")
    fig.suptitle("Who leads the research behind each technology", x=0.01, ha="left", fontsize=13, weight="bold", color=INK)
    n_ch = g.loc[g.lead_country == "China", "n_technologies"].sum(); n_all = g["n_technologies"].sum()
    fig.text(0.01, 0.905, f"ASPI Critical Technology Tracker, 2018-2022 high-impact research: China leads {n_ch} of {n_all} mapped technology links",
             color=MUTED, fontsize=9.5)
    fig.subplots_adjust(top=0.82)
    fig.savefig(IMG / "geopolitical_concentration.png"); plt.close(fig)

    print(ranking[["score", "tier", "coverage"]].to_string())
    print(summ.round(2).to_string())


if __name__ == "__main__":
    main()
