"""The Phase 2b trial family, exactly as fixed in docs/PHASE2B_CROSS_SECTIONAL_PROTOCOL.md (higher score = long)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .evaluate import basket_weights, buffered_weights, quantile_weights
from .factors import FACTORS, _mean
from .panel import Panel

OI_START = pd.Timestamp("2022-01-01", tz="UTC")


@dataclass(frozen=True)
class Trial:
    name: str
    description: str
    compute: Callable[[Panel], pd.DataFrame]
    weights: Callable[[pd.DataFrame, pd.DataFrame], pd.DataFrame]
    start: pd.Timestamp | None = None  # when its data starts after the development window does


def _taker(days: int) -> Callable[[Panel], pd.DataFrame]:
    return lambda p: _mean(p["taker_buy_quote_volume"] / p["quote_volume"].replace(0.0, np.nan), days) - 0.5


def _log(frame: pd.DataFrame) -> pd.DataFrame:
    return np.log(frame.where(frame > 0.0))


def _oi_growth(p: Panel) -> pd.DataFrame:
    log_oi = _log(p["open_interest"])
    return -(log_oi - log_oi.shift(7))


TRIALS: dict[str, Trial] = {
    trial.name: trial
    for trial in (
        Trial("taker_3d", "3-day mean taker-buy share of quote volume minus 0.5", _taker(3), quantile_weights),
        Trial("taker_14d", "14-day mean taker-buy share of quote volume minus 0.5", _taker(14), quantile_weights),
        Trial("taker_30d", "30-day mean taker-buy share of quote volume minus 0.5", _taker(30), quantile_weights),
        Trial(
            "lowvol_30d_vs_universe",
            "minus 30-day volatility of daily returns; top quintile vs universe basket",
            FACTORS["lowvol_30d"].compute,
            basket_weights,
        ),
        Trial(
            "basis_1d_buffered",
            "minus latest premium-index close; buffered quintile book (hold within the outer 40%)",
            FACTORS["basis_1d"].compute,
            buffered_weights,
        ),
        Trial(
            "oi_growth_7d",
            "minus 7-day change in log open interest (contracts)",
            _oi_growth,
            quantile_weights,
            OI_START,
        ),
        Trial(
            "smart_minus_retail_7d",
            "7-day mean of log top-trader long/short position ratio minus log all-account long/short ratio",
            lambda p: _mean(_log(p["toptrader_ls_position"]) - _log(p["global_ls_accounts"]), 7),
            quantile_weights,
            OI_START,
        ),
    )
}
