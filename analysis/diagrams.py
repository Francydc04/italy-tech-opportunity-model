"""Draws the two architecture figures: the data-first pipeline and the crosswalk flow.

Usage (from the repository root, after analysis/run_analysis.py): python analysis/diagrams.py
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch, PathPatch
from matplotlib.path import Path as MPath

ROOT = Path(__file__).resolve().parents[1]
IMG = ROOT / "images"
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
INK, MUTED, GRID = "#1f2328", "#6b7280", "#d7dbe0"
SOURCE_COLOR = {"wef": BLUE, "aspi": AQUA, "jobs": ORANGE, "vc": YELLOW}
SOURCE_LABEL = {"wef": "WEF Emerging Tech 2025", "aspi": "ASPI Critical Tech Tracker",
                "jobs": "WEF Future of Jobs 2025", "vc": "State of Italian VC 2024"}


def box(ax, x, y, w, h, title, body="", face="white", edge=GRID, title_color=INK, lw=1.2):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.0,rounding_size=0.12",
                                facecolor=face, edgecolor=edge, linewidth=lw))
    ax.text(x + 0.18, y + h - 0.22, title, fontsize=9.6, weight="bold", color=title_color, va="top")
    if body:
        ax.text(x + 0.18, y + h - 0.62, body, fontsize=8.3, color=INK, va="top", linespacing=1.45)


def arrow(ax, x0, x1, y):
    ax.annotate("", xy=(x1, y), xytext=(x0, y),
                arrowprops=dict(arrowstyle="-|>", color=MUTED, lw=1.4, mutation_scale=14))


def pipeline():
    fig, ax = plt.subplots(figsize=(15, 6.6))
    ax.set_xlim(0, 32.4); ax.set_ylim(0, 13); ax.axis("off")
    ax.text(0, 12.6, "Data-first: from four narrative reports to a queryable opportunity model",
            fontsize=15, weight="bold", color=INK)
    ax.text(0, 12.0, "Authoritative sources read by hand into a relational model, instead of scraping noisy web signals",
            fontsize=10, color=MUTED)

    cols = [0, 6.6, 13.2, 19.8, 26.4]; w = 5.95
    heads = ["1  Primary sources", "2  Manual extraction", "3  Relational model", "4  Scoring", "5  Analysis"]
    for x, h in zip(cols, heads):
        ax.text(x, 11.0, h, fontsize=11, weight="bold", color=MUTED)

    pages = [("WEF Emerging Tech 2025", "49-page PDF · 10 technologies", "wef"),
             ("ASPI Critical Tech Tracker", "84-page PDF · 44 technologies", "aspi"),
             ("WEF Future of Jobs 2025", "290-page PDF · 48 occupations", "jobs"),
             ("State of Italian VC 2024", "116-page PDF · 15 market records", "vc")]
    for i, (t, b, k) in enumerate(pages):
        y = 8.4 - i * 2.35
        box(ax, cols[0], y, w, 2.0, t, b, face="#f7f9fc", edge=SOURCE_COLOR[k], lw=1.6)

    box(ax, cols[1], 1.35, w, 9.05, "117 structured records",
        "539 pages read by hand\n\nOne row per entity at the\nreport's own grain\n\nShared provenance block:\nrecord_id · source_id · time_id\ngeo_id · entity_name · page_ref\n\nControlled vocabularies\n(low/medium/high, up/down...)\n\nOrdinal 1-5 scales for\nintensity given in prose",
        face="#fdf1e9", edge=ORANGE, lw=1.6)

    box(ax, cols[2], 8.2, w, 2.2, "4 source tables", "Primary key record_id\nCHECK constraints on every signal")
    box(ax, cols[2], 5.65, w, 2.2, "13 canonical technologies", "Common vocabulary across reports")
    box(ax, cols[2], 2.75, w, 2.55, "4 bridge tables · 81 links", "Foreign key on record_id, not name\nRationale stored for every link",
        face="#fdf1e9", edge=ORANGE, lw=1.6)
    box(ax, cols[2], 0.2, w, 2.2, "9 documented exclusions", "Every record mapped or excluded")

    box(ax, cols[3], 8.2, w, 2.2, "fact_signal", "One row per evidence link,\nwith its page reference")
    box(ax, cols[3], 5.65, w, 2.2, "4 lens scores (0-1)", "Readiness · capability access\ntalent pull · capital gap")
    box(ax, cols[3], 2.75, w, 2.55, "score and tier", "Generated columns: cannot be\nedited, cannot drift\n70% coverage floor",
        face="#fdf1e9", edge=ORANGE, lw=1.6)

    box(ax, cols[4], 8.2, w, 2.2, "Opportunity ranking", "13 technologies, lens contributions")
    box(ax, cols[4], 5.65, w, 2.2, "Weight sensitivity", "10,000 Dirichlet weight draws")
    box(ax, cols[4], 2.75, w, 2.55, "Audit views", "Unmapped records, signal\npresence, concentration")
    box(ax, cols[4], 0.2, w, 2.2, "12 regression tests", "One per defect found in the\nprototype audit")

    for x in cols[:-1]:
        arrow(ax, x + w + 0.08, x + 6.6 - 0.08, 5.9)
    fig.savefig(IMG / "data_first_pipeline.png", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def band(ax, x0, y0a, y0b, x1, y1a, y1b, color):
    """Filled bezier band from interval [y0a, y0b] at x0 to [y1a, y1b] at x1."""
    xm = (x0 + x1) / 2
    verts = [(x0, y0a), (xm, y0a), (xm, y1a), (x1, y1a), (x1, y1b), (xm, y1b), (xm, y0b), (x0, y0b), (x0, y0a)]
    codes = [MPath.MOVETO, MPath.CURVE4, MPath.CURVE4, MPath.CURVE4, MPath.LINETO,
             MPath.CURVE4, MPath.CURVE4, MPath.CURVE4, MPath.CLOSEPOLY]
    ax.add_patch(PathPatch(MPath(verts, codes), facecolor=color, edgecolor="none", alpha=0.55))


def crosswalk_flow():
    con = sqlite3.connect(ROOT / "results" / "iis.db")
    links = {}
    for src, table in [("wef", "bridge_wef"), ("aspi", "bridge_aspi"), ("jobs", "bridge_jobs"), ("vc", "bridge_vc")]:
        for tech, n in con.execute(f"SELECT tech_code, COUNT(*) FROM {table} GROUP BY tech_code"):
            links[(src, tech)] = n
    names = dict(con.execute("SELECT tech_code, canonical_technology FROM canonical_technology"))
    order = [r[0] for r in con.execute("SELECT tech_code FROM vw_opportunity_ranking ORDER BY score DESC")]
    totals_src = {s: sum(v for (a, _), v in links.items() if a == s) for s in SOURCE_COLOR}
    totals_tech = {t: sum(v for (_, b), v in links.items() if b == t) for t in order}
    n_records = {"wef": 10, "aspi": 44, "jobs": 48, "vc": 15}

    unit, gap = 0.1, 0.35
    fig, ax = plt.subplots(figsize=(12, 8))
    xL, xR, wN = 0.0, 6.0, 0.18
    # right nodes
    y = 0.0; right = {}
    for t in reversed(order):
        h = totals_tech[t] * unit
        right[t] = [y, y + h]; y += h + gap
    H = y - gap
    # left nodes, vertically centred
    hl = sum(totals_src.values()) * unit + 3 * 1.2
    y = (H - hl) / 2 + hl; left = {}
    for s in ["wef", "aspi", "jobs", "vc"]:
        h = totals_src[s] * unit
        left[s] = [y - h, y]; y -= h + 1.2
    cur_l = {s: left[s][1] for s in left}; cur_r = {t: right[t][1] for t in right}
    for s in ["wef", "aspi", "jobs", "vc"]:
        for t in order:
            n = links.get((s, t), 0)
            if not n:
                continue
            h = n * unit
            band(ax, xL + wN, cur_l[s] - h, cur_l[s], xR, cur_r[t] - h, cur_r[t], SOURCE_COLOR[s])
            cur_l[s] -= h; cur_r[t] -= h
    for s, (a, b) in left.items():
        ax.add_patch(plt.Rectangle((xL, a), wN, b - a, color=SOURCE_COLOR[s]))
        ax.text(xL - 0.12, (a + b) / 2, f"{SOURCE_LABEL[s]}\n{n_records[s]} records · {totals_src[s]} links",
                ha="right", va="center", fontsize=9.5, color=INK)
    for t, (a, b) in right.items():
        ax.add_patch(plt.Rectangle((xR, a), wN, b - a, color="#4b5563"))
        ax.text(xR + wN + 0.12, (a + b) / 2, f"{names[t]}  ({totals_tech[t]})", va="center", fontsize=9.5, color=INK)
    ax.set_xlim(-3.2, 9.4); ax.set_ylim(-0.3, H + 0.3); ax.axis("off")
    ax.set_title("The crosswalk: how four reports' vocabularies meet in one taxonomy", loc="left",
                 fontsize=14, weight="bold", color=INK, pad=28)
    ax.text(-3.2, H + 0.75, "Each band is one or more bridge-table links (keyed on record_id); technologies ordered by opportunity score",
            fontsize=9.5, color=MUTED)
    fig.savefig(IMG / "crosswalk_flow.png", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    pipeline()
    crosswalk_flow()
