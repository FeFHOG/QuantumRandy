from __future__ import annotations

import numpy as np
import pandas as pd

from .config import CostConfig, ExecutionConfig
from .expression import evaluate_formula


def signal_from_factor(factor: pd.Series, threshold: float) -> pd.Series:
    score = np.tanh(factor.replace([np.inf, -np.inf], np.nan).fillna(0.0))
    signal = pd.Series(0.0, index=factor.index)
    signal[score > threshold] = 1.0
    signal[score < -threshold] = -1.0
    return signal


def run_formula_backtest(
    data: pd.DataFrame,
    formula: str,
    costs: CostConfig,
    execution: ExecutionConfig,
) -> pd.DataFrame:
    factor = evaluate_formula(formula, data)
    signal = signal_from_factor(factor, execution.exposure_threshold)
    exposure = signal.shift(execution.delay_bars).fillna(0.0)
    exposure = exposure.clip(-abs(execution.max_exposure_abs), abs(execution.max_exposure_abs))

    close = data["close"].astype(float)
    r_mkt = close.pct_change().fillna(0.0)
    r_raw = exposure * r_mkt
    delta = exposure.diff().fillna(0.0)
    turnover = delta.abs()
    c_fee = turnover * costs.taker_bps / 10_000.0
    c_slip = turnover * costs.slippage_bps / 10_000.0
    c_fund = exposure * data["funding_rate"].fillna(0.0) * 0.5 * costs.funding_multiplier
    r_net = (r_raw - c_fee - c_slip - c_fund).replace([np.inf, -np.inf], 0.0).fillna(0.0)

    return pd.DataFrame(
        {
            "close": close,
            "factor": factor,
            "signal": signal,
            "exposure": exposure,
            "delta_exposure": delta,
            "r_mkt": r_mkt,
            "r_raw": r_raw,
            "c_fee": c_fee,
            "c_slip": c_slip,
            "c_fund": c_fund,
            "r_net": r_net,
        },
        index=data.index,
    )


def equity_curve(returns: pd.Series, initial: float = 1.0) -> pd.Series:
    return initial * (1.0 + returns.fillna(0.0)).cumprod()


def max_drawdown(returns: pd.Series) -> float:
    eq = equity_curve(returns)
    dd = eq / eq.cummax() - 1.0
    return float(-dd.min())


def sharpe(returns: pd.Series, bars_per_year: float, risk_free_rate: float = 0.03) -> float:
    r = returns.fillna(0.0)
    excess = r - risk_free_rate / bars_per_year
    std = float(excess.std(ddof=0))
    if std == 0:
        return 0.0
    return float(excess.mean() / std * np.sqrt(bars_per_year))


def cagr(returns: pd.Series, bars_per_year: float) -> float:
    if returns.empty:
        return 0.0
    total = float((1.0 + returns.fillna(0.0)).prod())
    years = len(returns) / bars_per_year
    if years <= 0 or total <= 0:
        return -0.9999
    return total ** (1.0 / years) - 1.0


def summarize_ledger(ledger: pd.DataFrame, bar_hours: int) -> dict[str, float]:
    bars_per_year = 365.0 * 24.0 / bar_hours
    r = ledger["r_net"]
    future = ledger["r_mkt"].shift(-1)
    factor = ledger["factor"].replace([np.inf, -np.inf], np.nan)
    valid = factor.notna() & future.notna()
    predictive_factor = factor[valid]
    predictive_return = future[valid]
    has_variation = len(predictive_factor) > 1 and predictive_factor.std(ddof=0) > 0
    ic = float(predictive_factor.corr(predictive_return)) if has_variation else 0.0
    rank_ic = float(predictive_factor.corr(predictive_return, method="spearman")) if has_variation else 0.0
    directional_win_rate = (
        float(((predictive_factor * predictive_return) > 0).mean())
        if len(predictive_factor)
        else 0.0
    )
    return {
        "bars": float(len(ledger)),
        "ic": 0.0 if np.isnan(ic) else ic,
        "rank_ic": 0.0 if np.isnan(rank_ic) else rank_ic,
        "directional_win_rate": 0.0 if np.isnan(directional_win_rate) else directional_win_rate,
        "predictive_observations": float(len(predictive_factor)),
        "sharpe": sharpe(r, bars_per_year),
        "cagr": cagr(r, bars_per_year),
        "max_dd": max_drawdown(r),
        "turnover": float(ledger["delta_exposure"].abs().mean()),
        "trades": float((ledger["delta_exposure"].abs() > 0).sum()),
        "net_total": float(r.sum()),
    }
