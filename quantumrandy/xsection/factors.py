"""The Phase 2a factor family, exactly as fixed in docs/PHASE2A_CROSS_SECTIONAL_PROTOCOL.md (higher score = long)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .panel import Panel


@dataclass(frozen=True)
class Factor:
    name: str
    description: str
    compute: Callable[[Panel], pd.DataFrame]


def _ret(close: pd.DataFrame, days: int, skip: int = 0) -> pd.DataFrame:
    return close.shift(skip) / close.shift(skip + days) - 1.0


def _mean(frame: pd.DataFrame, days: int) -> pd.DataFrame:
    return frame.rolling(days, min_periods=days).mean()


FACTORS: dict[str, Factor] = {
    factor.name: factor
    for factor in (
        Factor("carry_3d", "minus 3-day mean funding (8h-equivalent)", lambda p: -_mean(p["funding_rate"], 3)),
        Factor("carry_7d", "minus 7-day mean funding (8h-equivalent)", lambda p: -_mean(p["funding_rate"], 7)),
        Factor("basis_1d", "minus latest premium-index close", lambda p: -p["premium"]),
        Factor("basis_7d", "minus 7-day mean premium-index close", lambda p: -_mean(p["premium"], 7)),
        Factor("mom_7d", "7-day return", lambda p: _ret(p["close"], 7)),
        Factor("mom_30d", "30-day return skipping the last day", lambda p: _ret(p["close"], 30, skip=1)),
        Factor("mom_90d", "90-day return skipping the last 7 days", lambda p: _ret(p["close"], 90, skip=7)),
        Factor("rev_1d", "minus 1-day return", lambda p: -_ret(p["close"], 1)),
        Factor(
            "taker_7d",
            "7-day mean taker-buy share of quote volume",
            lambda p: _mean(p["taker_buy_quote_volume"] / p["quote_volume"].replace(0.0, np.nan), 7) - 0.5,
        ),
        Factor(
            "lowvol_30d",
            "minus 30-day volatility of daily returns",
            lambda p: -p["close"].pct_change(fill_method=None).rolling(30, min_periods=20).std(),
        ),
        Factor(
            "size_small",
            "minus log 30-day median quote volume",
            lambda p: -np.log(p["quote_volume"].rolling(30, min_periods=15).median().replace(0.0, np.nan)),
        ),
    )
}
