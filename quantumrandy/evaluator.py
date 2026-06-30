from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from .backtest import run_formula_backtest, summarize_ledger
from .config import CostConfig, ExecutionConfig
from .expression import evaluate_formula, formula_complexity, formula_depth, parse_formula


@dataclass(frozen=True)
class AlphaResult:
    formula: str
    score: float
    dimensions: dict[str, float]
    metrics: dict[str, float]
    description: str = ""
    hypothesis: str = ""
    expected_edge: str = ""
    expected_failure_mode: str = ""
    rewrite_plan_if_killed: str = ""
    depth: int = 0
    operators: int = 0
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))


def evaluate_alpha(
    formula: str,
    data: pd.DataFrame,
    costs: CostConfig,
    execution: ExecutionConfig,
    bar_hours: int,
    zoo: list[AlphaResult] | None = None,
    description: str = "",
    hypothesis: str = "",
    expected_edge: str = "",
    expected_failure_mode: str = "",
    rewrite_plan_if_killed: str = "",
    complexity_penalty: float = 0.025,
) -> AlphaResult:
    canonical = parse_formula(formula).canonical()
    depth = formula_depth(canonical)
    operators = formula_complexity(canonical)
    ledger = run_formula_backtest(data, canonical, costs, execution)
    metrics = summarize_ledger(ledger, bar_hours)
    zoo = zoo or []
    factor = ledger["factor"].replace([np.inf, -np.inf], np.nan)
    dimensions = {
        "effectiveness": _percentile(metrics["rank_ic"], [a.metrics.get("rank_ic", a.metrics["ic"]) for a in zoo], higher_is_better=True),
        "stability": _stability_score(ledger["r_net"]),
        "turnover": _turnover_score(metrics["turnover"]),
        "diversity": _diversity_score(factor, data, [a.formula for a in zoo]),
        "overfit_risk": _overfit_proxy(canonical, metrics),
    }
    raw_score = float(np.mean(list(dimensions.values())))
    extra_ops = max(operators - 2, 0)
    penalty = complexity_penalty * (2 ** extra_ops - 1)
    score = float(np.clip(raw_score - penalty, 0.0, 1.0))
    dimensions["simplicity"] = float(np.clip(1.0 - penalty, 0.0, 1.0))
    return AlphaResult(
        formula=canonical,
        score=score,
        dimensions=dimensions,
        metrics=metrics,
        description=description,
        hypothesis=hypothesis,
        expected_edge=expected_edge,
        expected_failure_mode=expected_failure_mode,
        rewrite_plan_if_killed=rewrite_plan_if_killed,
        depth=depth,
        operators=operators,
    )


def _percentile(value: float, prior: list[float], higher_is_better: bool) -> float:
    if not prior:
        return 0.5 + 0.5 * np.tanh(abs(value) * 30.0)
    wins = sum(value >= x if higher_is_better else value <= x for x in prior)
    return wins / len(prior)


def _stability_score(returns: pd.Series) -> float:
    monthly = returns.resample("ME").sum().dropna()
    if len(monthly) < 4:
        return 0.5
    positive = float((monthly > 0).mean())
    volatility_penalty = float(np.tanh(monthly.std(ddof=0) * 15.0))
    return float(np.clip(0.75 * positive + 0.25 * (1.0 - volatility_penalty), 0.0, 1.0))


def _turnover_score(turnover: float) -> float:
    return float(np.clip(1.0 - turnover * 3.0, 0.0, 1.0))


def _diversity_score(factor: pd.Series, data: pd.DataFrame, prior_formulas: list[str]) -> float:
    if not prior_formulas:
        return 1.0
    max_corr = 0.0
    for other in prior_formulas:
        try:
            other_factor = evaluate_formula(other, data).reindex(factor.index)
            corr = abs(float(factor.corr(other_factor)))
            if not np.isnan(corr):
                max_corr = max(max_corr, corr)
        except Exception:
            continue
    return float(np.clip(1.0 - max_corr, 0.0, 1.0))


def _overfit_proxy(formula: str, metrics: dict[str, float]) -> float:
    complexity = formula.count("(") + formula.count(",")
    complexity_score = np.clip(1.0 - max(complexity - 10, 0) / 25.0, 0.0, 1.0)
    drawdown_score = np.clip(1.0 - metrics["max_dd"], 0.0, 1.0)
    return float(0.65 * complexity_score + 0.35 * drawdown_score)

