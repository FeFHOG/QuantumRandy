from __future__ import annotations

import numpy as np
import pandas as pd
from randyslab import metrics as strict_metrics
from randyslab.accounting import build_ledger, infer_bar_hours, legacy_funding_settled

from .config import CostConfig, ExecutionConfig
from .expression import evaluate_formula
from .stats import finite_float, pearson_corr, spearman_corr

SIGNAL_MODES = ("rolling_zscore", "legacy_tanh")
DEFAULT_SIGNAL_MODE = "rolling_zscore"
DEFAULT_SIGNAL_ZSCORE_WINDOW = 180


def factor_score(
    factor: pd.Series,
    *,
    mode: str = DEFAULT_SIGNAL_MODE,
    window: int = DEFAULT_SIGNAL_ZSCORE_WINDOW,
) -> pd.Series:
    """Causal score in (-1, 1) that drives both positions and predictive metrics.

    ``rolling_zscore`` standardizes the factor over its own trailing ``window`` bars (a quarter of the window must be
    available), so a formula whose raw level sits above zero does not become a permanent long. ``legacy_tanh`` applies
    tanh to the raw value, which made positions depend on each formula's arbitrary scale.
    """
    clean = factor.astype(float).replace([np.inf, -np.inf], np.nan)
    if mode == "legacy_tanh":
        return np.tanh(clean.fillna(0.0))
    if mode != "rolling_zscore":
        raise ValueError(f"signal_mode must be one of {SIGNAL_MODES}")
    window = int(window)
    min_periods = max(2, window // 4)
    mean = clean.rolling(window, min_periods=min_periods).mean()
    std = clean.rolling(window, min_periods=min_periods).std(ddof=0)
    return np.tanh((clean - mean) / std.replace(0.0, np.nan))


def signal_from_score(score: pd.Series, threshold: float) -> pd.Series:
    signal = pd.Series(0.0, index=score.index)
    signal[score > threshold] = 1.0
    signal[score < -threshold] = -1.0
    return signal


def signal_from_factor(
    factor: pd.Series,
    threshold: float,
    *,
    mode: str = DEFAULT_SIGNAL_MODE,
    window: int = DEFAULT_SIGNAL_ZSCORE_WINDOW,
) -> pd.Series:
    return signal_from_score(factor_score(factor, mode=mode, window=window), threshold)


def run_formula_backtest(
    data: pd.DataFrame,
    formula: str,
    costs: CostConfig,
    execution: ExecutionConfig,
    *,
    history: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Strict next-bar ledger for ``formula`` over the bars of ``data``.

    ``history`` is an optional longer frame containing ``data``. The factor, its normalization and the position entering
    ``data`` are computed on ``history`` up to the last bar of ``data`` (every DSL operator is causal), so evaluation
    windows do not start cold. Costs come from the shared RandysLab accounting core.
    """
    source = data if history is None or data.empty else history.loc[: data.index[-1]]
    factor_all = evaluate_formula(formula, source)
    score_all = factor_score(factor_all, mode=execution.signal_mode, window=execution.signal_zscore_window)
    signal_all = signal_from_score(score_all, execution.exposure_threshold)
    exposure_all = signal_all.shift(execution.delay_bars).fillna(0.0) * abs(execution.max_exposure_abs)

    index = data.index
    if "funding_settled" in data.columns:
        settled = data["funding_settled"]
    else:
        settled = legacy_funding_settled(data["funding_rate"], infer_bar_hours(index))
    ledger = build_ledger(data["close"], exposure_all.reindex(index).fillna(0.0), settled, costs)
    head = pd.DataFrame(
        {
            "close": data["close"].astype(float),
            "factor": factor_all.reindex(index),
            "score": score_all.reindex(index),
            "signal": signal_all.reindex(index).fillna(0.0),
        },
        index=index,
    )
    return pd.concat([head, ledger], axis=1)


def equity_curve(returns: pd.Series, initial: float = 1.0) -> pd.Series:
    return strict_metrics.equity_curve(returns, initial)


def max_drawdown(returns: pd.Series) -> float:
    return strict_metrics.max_drawdown(returns)


def sharpe(returns: pd.Series, bars_per_year: float, risk_free_rate: float = 0.03) -> float:
    return strict_metrics.sharpe(returns, risk_free_rate=risk_free_rate, bars_per_year=bars_per_year)


def cagr(returns: pd.Series, bars_per_year: float) -> float:
    return strict_metrics.cagr(returns, bars_per_year=bars_per_year)


def summarize_ledger(ledger: pd.DataFrame, bar_hours: int) -> dict[str, float]:
    """Ledger metrics. Predictive metrics use the normalized ``score`` that drives positions, so IC and Sharpe judge
    the same signal; ``rank_ic_raw`` keeps the raw-factor value for audit."""
    bars_per_year = 365.0 * 24.0 / bar_hours
    r = ledger["r_net"]
    future = ledger["r_mkt"].shift(-1)
    predictor = ledger["score"] if "score" in ledger.columns else ledger["factor"]
    ic, rank_ic, win_rate, observations = _predictive_metrics(predictor, future)
    _, rank_ic_raw, _, _ = _predictive_metrics(ledger["factor"], future)
    return {
        "bars": float(len(ledger)),
        "ic": ic,
        "rank_ic": rank_ic,
        "rank_ic_raw": rank_ic_raw,
        "directional_win_rate": win_rate,
        "predictive_observations": observations,
        "sharpe": sharpe(r, bars_per_year),
        "cagr": cagr(r, bars_per_year),
        "max_dd": max_drawdown(r),
        "turnover": float(ledger["delta_exposure"].abs().mean()),
        "trades": float((ledger["delta_exposure"].abs() > 0).sum()),
        "net_total": float(r.sum()),
        "final_equity": float(equity_curve(r).iloc[-1]) if len(r) else 1.0,
    }


def _predictive_metrics(predictor: pd.Series, future: pd.Series) -> tuple[float, float, float, float]:
    clean = predictor.astype(float).replace([np.inf, -np.inf], np.nan)
    valid = clean.notna() & future.notna()
    x = clean[valid]
    y = future[valid]
    varies = len(x) > 1 and x.std(ddof=0) > 0 and y.std(ddof=0) > 0
    ic = pearson_corr(x, y) if varies else 0.0
    rank_ic = spearman_corr(x, y) if varies else 0.0
    win_rate = float(((x * y) > 0).mean()) if len(x) else 0.0
    return finite_float(ic), finite_float(rank_ic), finite_float(win_rate), float(len(x))
