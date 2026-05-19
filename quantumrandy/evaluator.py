from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from .backtest import run_formula_backtest, summarize_ledger
from .config import CostConfig, ExecutionConfig
from .expression import formula_complexity, formula_depth, parse_formula


@dataclass(frozen=True)
class AlphaResult:
    formula: str
    score: float
    dimensions: dict[str, float]
    metrics: dict[str, float]
    description: str = ""
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
    complexity_penalty: float = 0.025,
) -> AlphaResult:
    canonical = parse_formula(formula).canonical()
    depth = formula_depth(canonical)
    operators = formula_complexity(canonical)
    ledger = run_formula_backtest(data, canonical, costs, execution)
    metrics = summarize_ledger(ledger, bar_hours)
    zoo = zoo or []
    dimensions = {
        "effectiveness": _percentile(metrics["rank_ic"], [a.metrics.get("rank_ic", a.metrics["ic"]) for a in zoo], higher_is_better=True),
        "stability": _stability_score(ledger["r_net"]),
        "turnover": _turnover_score(metrics["turnover"]),
        "diversity": _diversity_score(canonical, [a.formula for a in zoo]),
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


def _diversity_score(formula: str, prior: list[str]) -> float:
    if not prior:
        return 1.0
    tokens = set(_tokens(formula))
    sims = []
    for other in prior:
        other_tokens = set(_tokens(other))
        union = tokens | other_tokens
        sims.append(len(tokens & other_tokens) / max(len(union), 1))
    return float(np.clip(1.0 - max(sims), 0.0, 1.0))


def _overfit_proxy(formula: str, metrics: dict[str, float]) -> float:
    complexity = formula.count("(") + formula.count(",")
    complexity_score = np.clip(1.0 - max(complexity - 10, 0) / 25.0, 0.0, 1.0)
    drawdown_score = np.clip(1.0 - metrics["max_dd"], 0.0, 1.0)
    return float(0.65 * complexity_score + 0.35 * drawdown_score)


def _tokens(formula: str) -> list[str]:
    for char in "(),":
        formula = formula.replace(char, " ")
    return [x for x in formula.split() if x]
