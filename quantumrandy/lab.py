from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from .backtest import run_formula_backtest, summarize_ledger
from .config import CostConfig, ExecutionConfig, FilterConfig
from .evaluator import AlphaResult
from .expression import evaluate_formula


@dataclass(frozen=True)
class FilterThresholds:
    min_rank_ic: float = 0.01
    min_directional_win_rate: float = 0.49
    max_corr: float = 0.70
    min_cost_sharpe: float = 0.30
    min_validation_sharpe: float = 0.00
    min_halflife_bars: int = 1

    @classmethod
    def from_config(cls, cfg: FilterConfig | None) -> "FilterThresholds":
        if cfg is None:
            return cls()
        return cls(
            min_rank_ic=cfg.min_rank_ic,
            min_directional_win_rate=cfg.min_directional_win_rate,
            max_corr=cfg.max_corr,
            min_cost_sharpe=cfg.min_cost_sharpe,
            min_validation_sharpe=cfg.min_validation_sharpe,
            min_halflife_bars=cfg.min_halflife_bars,
        )


def run_brutal_filter(
    formula: str,
    train_data: pd.DataFrame,
    validation_data: pd.DataFrame,
    costs: CostConfig,
    execution: ExecutionConfig,
    bar_hours: int,
    accepted_formulas: list[str],
    thresholds: FilterThresholds | None = None,
) -> dict:
    thresholds = thresholds or FilterThresholds()
    train_ledger = run_formula_backtest(train_data, formula, costs, execution)
    validation_ledger = run_formula_backtest(validation_data, formula, costs, execution)
    train_metrics = summarize_ledger(train_ledger, bar_hours)
    validation_metrics = summarize_ledger(validation_ledger, bar_hours)
    factor = train_ledger["factor"].replace([np.inf, -np.inf], np.nan).fillna(0.0)

    pred_pass = (
        train_metrics["rank_ic"] >= thresholds.min_rank_ic
        and train_metrics["directional_win_rate"] >= thresholds.min_directional_win_rate
    )
    max_corr = max_factor_corr(factor, train_data, accepted_formulas, self_formula=formula)
    homo_pass = max_corr < thresholds.max_corr
    audit_pass = train_metrics["sharpe"] >= thresholds.min_cost_sharpe
    halflife = estimate_halflife_bars(factor, train_data["close"].pct_change().fillna(0.0), max_horizon=42)
    life_pass = validation_metrics["sharpe"] >= thresholds.min_validation_sharpe and halflife >= thresholds.min_halflife_bars

    gates = {
        "predictive_power": {
            "pass": pred_pass,
            "rank_ic": train_metrics["rank_ic"],
            "directional_win_rate": train_metrics["directional_win_rate"],
            "rule": f"rank_ic >= {thresholds.min_rank_ic} AND directional_win_rate >= {thresholds.min_directional_win_rate}",
        },
        "homogeneity": {
            "pass": homo_pass,
            "max_corr_to_library": max_corr,
            "rule": f"max_corr < {thresholds.max_corr}",
        },
        "autoquant_audit": {
            "pass": audit_pass,
            "cost_sharpe": train_metrics["sharpe"],
            "rule": f"cost_sharpe >= {thresholds.min_cost_sharpe}",
        },
        "lifetime": {
            "pass": life_pass,
            "halflife_bars": halflife,
            "validation_sharpe": validation_metrics["sharpe"],
            "rule": f"validation_sharpe >= {thresholds.min_validation_sharpe} AND halflife_bars >= {thresholds.min_halflife_bars}",
        },
    }
    passed = all(item["pass"] for item in gates.values())
    brutal_score = brutal_rank_score(gates, train_metrics, validation_metrics)
    return {
        "formula": formula,
        "passed": passed,
        "brutal_score": brutal_score,
        "gates": gates,
        "train": train_metrics,
        "validation": validation_metrics,
    }


def brutal_rank_score(gates: dict, train_metrics: dict, validation_metrics: dict) -> float:
    gate_score = sum(1.0 for gate in gates.values() if gate["pass"]) / max(len(gates), 1)
    rank_ic_score = np.clip(train_metrics["rank_ic"] / 0.05, -1.0, 1.0)
    sharpe_score = np.clip(train_metrics["sharpe"] / 2.0, -1.0, 1.0)
    validation_score = np.clip(validation_metrics["sharpe"] / 2.0, -1.0, 1.0)
    dd_score = np.clip(1.0 - train_metrics["max_dd"], 0.0, 1.0)
    return float(100.0 * (0.35 * gate_score + 0.25 * rank_ic_score + 0.20 * sharpe_score + 0.15 * validation_score + 0.05 * dd_score))


def max_factor_corr(factor: pd.Series, data: pd.DataFrame, accepted_formulas: list[str], *, self_formula: str = "") -> float:
    values = []
    for other in mature_factor_formulas() + accepted_formulas:
        if other == self_formula:
            continue
        try:
            other_factor = evaluate_formula(other, data).reindex(factor.index)
        except Exception:
            continue
        corr = factor.corr(other_factor)
        if not np.isnan(corr):
            values.append(abs(float(corr)))
    return max(values) if values else 0.0


def mature_factor_formulas() -> list[str]:
    return [
        "zscore(ret(close,6),48)",
        "zscore(sub(sma(close,12),sma(close,48)),48)",
        "neg(zscore(funding_rate,42))",
        "zscore(div(sub(close,sma(close,24)),std(close,24)),48)",
        "zscore(volume,48)",
    ]


def estimate_halflife_bars(factor: pd.Series, returns: pd.Series, max_horizon: int = 42) -> int:
    base = abs(float(factor.corr(returns.shift(-1), method="spearman")))
    if np.isnan(base) or base <= 1e-9:
        return 0
    for horizon in range(2, max_horizon + 1):
        corr = abs(float(factor.corr(returns.shift(-horizon), method="spearman")))
        if np.isnan(corr) or corr <= base * 0.5:
            return horizon
    return max_horizon


def kill_reasons(gates: dict) -> list[str]:
    """Return list of gate names that failed."""
    failed = []
    for name in ["predictive_power", "homogeneity", "autoquant_audit", "lifetime"]:
        if not gates.get(name, {}).get("pass", False):
            failed.append(name)
    return failed


def row_from_alpha(alpha: AlphaResult, brutal: dict | None = None) -> dict:
    row = {
        "formula": alpha.formula,
        "description": alpha.description,
        "depth": alpha.depth,
        "operators": alpha.operators,
        "mcts_score": alpha.score,
        "generated_at": getattr(alpha, 'generated_at', datetime.now(timezone.utc).isoformat(timespec="seconds")),
        **alpha.dimensions,
        **alpha.metrics,
    }
    if brutal:
        reasons = kill_reasons(brutal["gates"])
        row.update(
            {
                "brutal_score": brutal["brutal_score"],
                "passed": brutal["passed"],
                "kill_reasons": reasons,
                "gate_predictive_power": brutal["gates"]["predictive_power"]["pass"],
                "gate_homogeneity": brutal["gates"]["homogeneity"]["pass"],
                "gate_autoquant_audit": brutal["gates"]["autoquant_audit"]["pass"],
                "gate_lifetime": brutal["gates"]["lifetime"]["pass"],
                "max_corr_to_library": brutal["gates"]["homogeneity"]["max_corr_to_library"],
                "halflife_bars": brutal["gates"]["lifetime"]["halflife_bars"],
                "validation_sharpe": brutal["validation"]["sharpe"],
                "validation_rank_ic": brutal["validation"]["rank_ic"],
            }
        )
    return row
