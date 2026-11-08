"""Python mirror of the SQL scoring rule, used for sensitivity analysis.

The SQL generated columns in sql/schema.sql are the source of truth; the test
suite checks that both give identical scores.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

LENSES = ["readiness", "capability_access", "talent_pull", "capital_gap"]
BASE_WEIGHTS = np.array([0.30, 0.20, 0.30, 0.20])
FLOOR = 0.7


def score(lenses: pd.DataFrame, weights: np.ndarray = BASE_WEIGHTS, floor: float = FLOOR,
          rule: str = "floor") -> pd.Series:
    """Opportunity score on 0-100.

    rule="floor":          100 * base * (floor + (1 - floor) * coverage)
    rule="multiplicative": 100 * base * coverage   (the original, over-penalising rule)
    """
    x = lenses[LENSES].to_numpy(dtype=float)
    present = ~np.isnan(x)
    w = np.broadcast_to(weights, x.shape) * present
    base = np.nansum(np.nan_to_num(x) * w, axis=1) / w.sum(axis=1)
    coverage = present.mean(axis=1)
    mult = coverage if rule == "multiplicative" else floor + (1 - floor) * coverage
    return pd.Series(np.round(100 * base * mult, 2), index=lenses.index)


def contributions(lenses: pd.DataFrame, weights: np.ndarray = BASE_WEIGHTS, floor: float = FLOOR) -> pd.DataFrame:
    """Split each score into additive per-lens contributions (sum = score)."""
    x = lenses[LENSES].to_numpy(dtype=float)
    present = ~np.isnan(x)
    w = np.broadcast_to(weights, x.shape) * present
    coverage = present.mean(axis=1)
    mult = floor + (1 - floor) * coverage
    contrib = 100 * np.nan_to_num(x) * w / w.sum(axis=1, keepdims=True) * mult[:, None]
    return pd.DataFrame(contrib, index=lenses.index, columns=LENSES)


def weight_sensitivity(lenses: pd.DataFrame, n_draws: int = 10_000, concentration: float = 20.0,
                       seed: int = 2026) -> pd.DataFrame:
    """Rank of every technology under random weight vectors.

    Weights are drawn from a Dirichlet centred on the base weights; the
    concentration controls how far they stray (20 gives each weight a standard
    deviation of roughly 0.08-0.10).
    """
    rng = np.random.default_rng(seed)
    draws = rng.dirichlet(BASE_WEIGHTS * concentration, size=n_draws)
    ranks = np.empty((n_draws, len(lenses)), dtype=int)
    for i, w in enumerate(draws):
        s = score(lenses, w).to_numpy()
        ranks[i] = (-s).argsort().argsort() + 1
    return pd.DataFrame(ranks, columns=lenses.index)
