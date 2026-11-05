"""Cross-sectional factor evaluation: rank IC per day and dollar-neutral quantile books on the shared ledger."""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd
from randyslab import metrics as strict_metrics
from randyslab.accounting import CostRates, build_portfolio_ledger
from randyslab.regimes import outside_regimes
from randyslab.stats import newey_west_tstat

from .panel import Panel

DAYS_PER_YEAR = 365.0
MIN_NAMES = 10


def forward_returns(panel: Panel) -> pd.DataFrame:
    """Return earned during day t+1 by a position set at the close of day t."""
    return panel["close"].pct_change(fill_method=None).shift(-1)


def cross_sectional_ic(scores: pd.DataFrame, forward: pd.DataFrame, mask: pd.DataFrame) -> pd.Series:
    """Spearman correlation across universe members of each day's scores with the next day's returns."""
    valid = mask & scores.notna() & forward.notna()
    rank_score = scores.where(valid).rank(axis=1)
    rank_forward = forward.where(valid).rank(axis=1)
    centred_score = rank_score.sub(rank_score.mean(axis=1), axis=0)
    centred_forward = rank_forward.sub(rank_forward.mean(axis=1), axis=0)
    numerator = (centred_score * centred_forward).sum(axis=1)
    denominator = np.sqrt((centred_score**2).sum(axis=1) * (centred_forward**2).sum(axis=1))
    ic = numerator / denominator.replace(0.0, np.nan)
    return ic.where(valid.sum(axis=1) >= MIN_NAMES)


def quantile_weights(scores: pd.DataFrame, mask: pd.DataFrame, quantile: float = 0.2) -> pd.DataFrame:
    """Long the top and short the bottom ``quantile`` of each day's universe, equal weight, gross exposure 1."""
    ranked = scores.where(mask & scores.notna())
    count = ranked.notna().sum(axis=1)
    legs = np.floor(count * quantile).clip(lower=1)
    order = ranked.rank(axis=1, method="first")
    long = order.gt(count - legs, axis=0) & ranked.notna()
    short = order.le(legs, axis=0) & ranked.notna()
    size = (0.5 / legs).where(count >= MIN_NAMES, 0.0)
    return long.astype(float).mul(size, axis=0) - short.astype(float).mul(size, axis=0)


def basket_weights(scores: pd.DataFrame, mask: pd.DataFrame, quantile: float = 0.2) -> pd.DataFrame:
    """Long the top ``quantile`` equally against an equal-weight short of every scored universe member.

    Weights are netted per name and scaled to gross exposure 1, so no single coin carries a concentrated short.
    """
    ranked = scores.where(mask & scores.notna())
    count = ranked.notna().sum(axis=1)
    legs = np.floor(count * quantile).clip(lower=1)
    order = ranked.rank(axis=1, method="first")
    long = (order.gt(count - legs, axis=0) & ranked.notna()).astype(float).div(legs, axis=0)
    basket = ranked.notna().astype(float).div(count.replace(0, np.nan), axis=0)
    netted = (long - basket).fillna(0.0)
    gross = netted.abs().sum(axis=1)
    scale = (1.0 / gross.replace(0.0, np.nan)).where(count >= MIN_NAMES, 0.0).fillna(0.0)
    return netted.mul(scale, axis=0)


def buffered_weights(
    scores: pd.DataFrame, mask: pd.DataFrame, quantile: float = 0.2, buffer: float = 2.0
) -> pd.DataFrame:
    """Quantile long-short book that keeps a held name while it stays within ``buffer`` times its leg's size.

    Each leg holds k = floor(quantile x scored names) at weight 0.5 / k. A held long stays while its rank is within the
    top ``buffer`` x k (shorts mirror at the bottom); vacancies go to the best-ranked names not held.
    """
    ranked = scores.where(mask & scores.notna())
    out = np.zeros(ranked.shape)
    longs: set[str] = set()
    shorts: set[str] = set()
    for row, (_, day) in enumerate(ranked.iterrows()):
        day = day.dropna()
        if len(day) < MIN_NAMES:
            longs, shorts = set(), set()
            continue
        k = max(int(np.floor(len(day) * quantile)), 1)
        reach = int(np.floor(buffer * k))
        best = list(day.sort_values(ascending=False, kind="stable").index)
        longs = _refill(longs, best, k, reach)
        shorts = _refill(shorts, best[::-1], k, reach)
        for names, sign in ((longs, 1.0), (shorts, -1.0)):
            out[row, ranked.columns.get_indexer(sorted(names))] = sign * 0.5 / k
    return pd.DataFrame(out, index=ranked.index, columns=ranked.columns)


def _refill(held: set[str], order: list[str], k: int, reach: int) -> set[str]:
    """Keep held names ranked within ``reach`` (best k of them at most), then fill to k from the top of ``order``."""
    kept = [name for name in order[:reach] if name in held][:k]
    fill = [name for name in order if name not in kept][: k - len(kept)]
    return set(kept + fill)


def held_weights(target: pd.DataFrame, panel: Panel) -> pd.DataFrame:
    """Weights set at each close and held during the next day; a contract without a price that day is flat."""
    return target.shift(1).fillna(0.0).where(panel["close"].notna(), 0.0)


def evaluate_book(weights: pd.DataFrame, panel: Panel, costs: CostRates, start: pd.Timestamp) -> dict[str, Any]:
    ledger = build_portfolio_ledger(weights, panel["close"], panel["funding_settled"], costs)
    returns = ledger["r_net"].loc[start:]
    return {
        "sharpe": strict_metrics.sharpe(returns, 0.03, DAYS_PER_YEAR),
        "sharpe_ex_regimes": strict_metrics.sharpe(returns[outside_regimes(returns.index)], 0.03, DAYS_PER_YEAR),
        "cagr": strict_metrics.cagr(returns, DAYS_PER_YEAR),
        "max_dd": strict_metrics.max_drawdown(returns),
        "turnover": float(ledger["turnover"].loc[start:].mean()),
        "funding_cost_annual": float(ledger["c_fund"].loc[start:].mean() * DAYS_PER_YEAR),
        "returns": returns,
    }


def evaluate_factor(
    scores: pd.DataFrame,
    panel: Panel,
    mask: pd.DataFrame,
    costs: CostRates,
    start: pd.Timestamp,
    weights: Callable[[pd.DataFrame, pd.DataFrame], pd.DataFrame] = quantile_weights,
) -> dict[str, Any]:
    """IC statistics and net metrics of the ``weights`` book at 1x and 2x costs from ``start`` onwards."""
    ic = cross_sectional_ic(scores, forward_returns(panel), mask).loc[start:].dropna()
    by_year = ic.groupby(ic.index.year).mean()
    book = held_weights(weights(scores, mask), panel)
    base = evaluate_book(book, panel, costs, start)
    stressed = evaluate_book(
        book,
        panel,
        CostRates(costs.fee_bps * 2.0, costs.slippage_bps * 2.0, costs.funding_multiplier),
        start,
    )
    tstat = newey_west_tstat(ic.to_numpy())
    return {
        "ic_mean": float(ic.mean()) if len(ic) else math.nan,
        "ic_tstat": tstat,
        "ic_days": int(len(ic)),
        "ic_by_year": {int(year): float(value) for year, value in by_year.items()},
        "sharpe": base["sharpe"],
        "sharpe_2x_costs": stressed["sharpe"],
        "sharpe_ex_regimes": base["sharpe_ex_regimes"],
        "cagr": base["cagr"],
        "max_dd": base["max_dd"],
        "turnover": base["turnover"],
        "funding_cost_annual": base["funding_cost_annual"],
        "returns": base["returns"],
    }
