from __future__ import annotations

import numpy as np
import pandas as pd


def finite_float(value: object, default: float = 0.0) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if np.isfinite(out) else default


def pearson_corr(left: pd.Series, right: pd.Series) -> float:
    frame = pd.concat([left, right], axis=1).replace([np.inf, -np.inf], np.nan).dropna()
    if len(frame) < 2:
        return 0.0
    first = frame.iloc[:, 0].astype(float)
    second = frame.iloc[:, 1].astype(float)
    if float(first.std(ddof=0)) <= 0.0 or float(second.std(ddof=0)) <= 0.0:
        return 0.0
    return finite_float(first.corr(second))


def spearman_corr(left: pd.Series, right: pd.Series) -> float:
    frame = pd.concat([left, right], axis=1).replace([np.inf, -np.inf], np.nan).dropna()
    if len(frame) < 2:
        return 0.0
    left_rank = frame.iloc[:, 0].astype(float).rank(method="average")
    right_rank = frame.iloc[:, 1].astype(float).rank(method="average")
    return pearson_corr(left_rank, right_rank)
