from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .backtest import sharpe, signal_from_factor, summarize_ledger
from .config import CostConfig, ExecutionConfig, FilterConfig, ProjectConfig
from .expression import evaluate_formula


@dataclass(frozen=True)
class PortfolioSpec:
    portfolio_id: str
    weighting: str
    weights: dict[str, float]
    description: str


def build_portfolio_research(
    data: pd.DataFrame,
    entries: list[dict[str, object]],
    cfg: ProjectConfig,
    *,
    max_corr: float | None = None,
    min_factors: int = 1,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Evaluate accepted factors, apply correlation filtering, and backtest simple fixed-weight portfolios."""
    if not entries:
        raise ValueError("At least one formula entry is required")
    if min_factors <= 0:
        raise ValueError("min_factors must be positive")
    max_corr = cfg.filter.max_corr if max_corr is None else float(max_corr)
    if not 0.0 <= max_corr <= 1.0:
        raise ValueError("max_corr must be in [0, 1]")

    factor_rows, factor_values, factor_signals = _evaluate_factor_pool(data, entries, cfg)
    selected_ids, selection_rows = _select_low_correlation_pool(factor_rows, factor_values, max_corr, min_factors)
    specs = build_portfolio_specs(factor_rows, selected_ids)
    portfolio_rows: list[dict[str, Any]] = []
    contribution_rows: list[dict[str, Any]] = []

    for spec in specs:
        ledger = simulate_weighted_signal_portfolio(data, factor_signals, spec, cfg.costs, cfg.execution, cfg.bar_hours)
        metrics = summarize_ledger(ledger, cfg.bar_hours)
        portfolio_rows.append(
            {
                "portfolio_id": spec.portfolio_id,
                "weighting": spec.weighting,
                "factor_count": len(spec.weights),
                "weights": ",".join(f"{factor_id}:{weight:.6f}" for factor_id, weight in spec.weights.items()),
                **{key: round(float(value), 8) for key, value in metrics.items()},
            }
        )
        contribution_rows.extend(
            _portfolio_ablation_rows(data, factor_signals, spec, metrics, cfg.costs, cfg.execution, cfg.bar_hours)
        )

    manifest = {
        "artifact_type": "quantumrandy_portfolio_research",
        "schema_version": 1,
        "safety": {
            "research_only": True,
            "not_runtime_publish_payload": True,
            "requires_manual_review_before_runtime": True,
        },
        "symbol": cfg.symbol,
        "bar_hours": cfg.bar_hours,
        "max_corr": max_corr,
        "selected_factor_ids": selected_ids,
        "portfolios": [
            {
                "portfolio_id": spec.portfolio_id,
                "weighting": spec.weighting,
                "description": spec.description,
                "weights": spec.weights,
            }
            for spec in specs
        ],
    }
    return (
        pd.DataFrame(factor_rows),
        pd.DataFrame(selection_rows),
        pd.DataFrame(portfolio_rows),
        pd.DataFrame(contribution_rows),
        manifest,
    )


def build_portfolio_specs(factor_rows: list[dict[str, Any]], selected_ids: list[str]) -> list[PortfolioSpec]:
    rows_by_id = {str(row["factor_id"]): row for row in factor_rows}
    selected = [rows_by_id[factor_id] for factor_id in selected_ids if factor_id in rows_by_id]
    if not selected:
        return []
    return [
        PortfolioSpec(
            portfolio_id="equal_weight_accepted",
            weighting="equal_weight",
            weights=_normalize_positive({str(row["factor_id"]): 1.0 for row in selected}),
            description="Equal-weight blend of accepted factors after correlation filtering.",
        ),
        PortfolioSpec(
            portfolio_id="ic_weight_accepted",
            weighting="rank_ic_weight",
            weights=_metric_weights(selected, "rank_ic"),
            description="Rank-IC-weighted blend of accepted factors after correlation filtering.",
        ),
        PortfolioSpec(
            portfolio_id="sharpe_weight_accepted",
            weighting="sharpe_weight",
            weights=_metric_weights(selected, "sharpe"),
            description="Sharpe-weighted blend of accepted factors after correlation filtering.",
        ),
    ]


def simulate_weighted_signal_portfolio(
    data: pd.DataFrame,
    factor_signals: dict[str, pd.Series],
    spec: PortfolioSpec,
    costs: CostConfig,
    execution: ExecutionConfig,
    bar_hours: int,
) -> pd.DataFrame:
    if not spec.weights:
        raise ValueError("Portfolio spec must contain at least one factor weight")
    combined = pd.Series(0.0, index=data.index)
    has_signal = pd.Series(False, index=data.index)
    for factor_id, weight in spec.weights.items():
        if factor_id not in factor_signals:
            raise ValueError(f"Missing signal series for {factor_id}")
        signal = factor_signals[factor_id].reindex(data.index).fillna(0.0)
        combined += float(weight) * signal
        has_signal |= signal.notna()
    combined[~has_signal] = 0.0

    target = combined.copy()
    target[target.abs() < execution.exposure_threshold] = 0.0
    target = target.clip(-abs(execution.max_exposure_abs), abs(execution.max_exposure_abs))
    exposure = target.shift(execution.delay_bars).fillna(0.0)
    delta = exposure.diff().fillna(0.0)
    turnover = delta.abs()
    close = data["close"].astype(float)
    r_mkt = close.pct_change().fillna(0.0)
    r_raw = exposure * r_mkt
    c_fee = turnover * costs.taker_bps / 10_000.0
    c_slip = turnover * costs.slippage_bps / 10_000.0
    c_fund = exposure * data["funding_rate"].fillna(0.0) * 0.5 * costs.funding_multiplier
    r_net = (r_raw - c_fee - c_slip - c_fund).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    bars_per_year = 365.0 * 24.0 / bar_hours
    equity = (1.0 + r_net).cumprod()

    return pd.DataFrame(
        {
            "close": close,
            "factor": combined,
            "target_exposure": target,
            "exposure": exposure,
            "delta_exposure": delta,
            "r_mkt": r_mkt,
            "r_raw": r_raw,
            "c_fee": c_fee,
            "c_slip": c_slip,
            "c_fund": c_fund,
            "r_net": r_net,
            "equity": equity,
            "rolling_sharpe_90d": r_net.rolling(max(int(90 * 24 / bar_hours), 2)).apply(
                lambda x: sharpe(pd.Series(x), bars_per_year), raw=False
            ),
            "drawdown": equity / equity.cummax() - 1.0,
        },
        index=data.index,
    )


def render_portfolio_report(
    manifest: dict[str, Any],
    factor_frame: pd.DataFrame,
    selection_frame: pd.DataFrame,
    portfolio_frame: pd.DataFrame,
    contribution_frame: pd.DataFrame | None = None,
    baseline_summary: dict[str, Any] | None = None,
) -> str:
    lines = [
        "# QuantumRandy Portfolio Research Report",
        "",
        "This is a research artifact only. It is not a runtime publish payload.",
        "",
        "## Run",
        "",
        f"- Symbol: `{manifest['symbol']}`",
        f"- Bar hours: `{manifest['bar_hours']}`",
        f"- Correlation filter: `abs(corr) <= {manifest['max_corr']}`",
        f"- Selected factors: `{len(manifest['selected_factor_ids'])}`",
        "",
        "## Portfolio Summary",
        "",
        "| Portfolio | Weighting | Factors | Sharpe | Rank IC | Max DD | Turnover | Trades |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in portfolio_frame.to_dict(orient="records"):
        lines.append(
            "| {portfolio_id} | {weighting} | {factor_count} | {sharpe:.4f} | {rank_ic:.4f} | "
            "{max_dd:.4f} | {turnover:.4f} | {trades:.0f} |".format(**row)
        )
    lines.extend(_render_baseline_comparison(portfolio_frame, baseline_summary))

    lines.extend(
        [
            "",
            "## Selected Factors",
            "",
            "| Factor | Sharpe | Rank IC | Max Corr | Status |",
            "|---|---:|---:|---:|---|",
        ]
    )
    selected = selection_frame[selection_frame["selected"]] if not selection_frame.empty else selection_frame
    for row in selected.to_dict(orient="records"):
        factor = factor_frame[factor_frame["factor_id"] == row["factor_id"]].iloc[0].to_dict()
        lines.append(
            "| `{factor_id}` | {sharpe:.4f} | {rank_ic:.4f} | {max_abs_corr_to_selected:.4f} | {reason} |".format(
                factor_id=row["factor_id"],
                sharpe=float(factor.get("sharpe", 0.0)),
                rank_ic=float(factor.get("rank_ic", 0.0)),
                max_abs_corr_to_selected=float(row.get("max_abs_corr_to_selected", 0.0)),
                reason=row.get("reason", ""),
            )
        )
    if contribution_frame is not None and not contribution_frame.empty:
        lines.extend(
            [
                "",
                "## Factor Ablation",
                "",
                "| Portfolio | Removed Factor | Weight | Delta Sharpe | Delta Net Total | Delta Max DD |",
                "|---|---|---:|---:|---:|---:|",
            ]
        )
        for row in contribution_frame.to_dict(orient="records"):
            lines.append(
                "| `{portfolio_id}` | `{factor_id}` | {weight:.4f} | {delta_sharpe:.4f} | "
                "{delta_net_total:.4f} | {delta_max_dd:.4f} |".format(**row)
            )
    lines.extend(
        [
            "",
            "## Files",
            "",
            "- `portfolio_factors.csv`: evaluated factor metrics.",
            "- `portfolio_selection.csv`: correlation-filter decisions.",
            "- `portfolio_summary.csv`: portfolio-level metrics.",
            "- `portfolio_contribution.csv`: leave-one-factor-out contribution analysis.",
            "- `portfolio_manifest.json`: research-only portfolio components and weights.",
            "",
        ]
    )
    return "\n".join(lines)


def load_baseline_summary(path: str | Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    path = Path(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise RuntimeError("baseline summary must be a JSON object")
        return {**payload, "source_path": path.as_posix()}
    except Exception as exc:
        return {
            "artifact_type": "randyslab_baseline_export_error",
            "source_path": path.as_posix(),
            "load_error": str(exc),
        }


def _render_baseline_comparison(
    portfolio_frame: pd.DataFrame,
    baseline_summary: dict[str, Any] | None,
) -> list[str]:
    if not baseline_summary:
        return []
    lines = ["", "## RandysLab Baseline Comparison", ""]
    source_path = baseline_summary.get("source_path")
    if baseline_summary.get("load_error"):
        lines.extend(
            [
                "Configured RandysLab baseline export could not be loaded.",
                "",
                f"- Source: `{source_path}`",
                f"- Error: `{baseline_summary.get('load_error')}`",
            ]
        )
        return lines
    if baseline_summary.get("artifact_type") != "randyslab_baseline_export":
        lines.extend(
            [
                "Configured baseline summary is not a recognized RandysLab baseline export.",
                "",
                f"- Source: `{source_path}`",
                f"- Artifact type: `{baseline_summary.get('artifact_type')}`",
            ]
        )
        return lines

    window = baseline_summary.get("window") or {}
    lines.extend(
        [
            "Traditional-strategy control group only. These rows are not runtime publish payloads.",
            "",
            f"- Source: `{source_path}`",
            f"- Generated at: `{baseline_summary.get('generated_at')}`",
            f"- Symbol: `{baseline_summary.get('symbol')}`",
            f"- Window: `{window.get('name')}`",
            "",
            "| Candidate | Source | Sharpe | Max DD | Trades | Net Total |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for row in portfolio_frame.to_dict(orient="records"):
        lines.append(
            "| {portfolio_id} | QuantumRandy portfolio research | {sharpe:.4f} | {max_dd:.4f} | "
            "{trades:.0f} | {net_total:.4f} |".format(**row)
        )
    for item in baseline_summary.get("strategies") or []:
        metrics = item.get("metrics") or {}
        lines.append(
            "| "
            f"{item.get('strategy_id')} | RandysLab baseline | "
            f"{_fmt(metrics.get('sharpe'))} | "
            f"{_fmt(metrics.get('max_dd'))} | "
            f"{_fmt(metrics.get('trades'))} | "
            f"{_fmt(metrics.get('net_total'))} |"
        )
    return lines


def _evaluate_factor_pool(
    data: pd.DataFrame,
    entries: list[dict[str, object]],
    cfg: ProjectConfig,
) -> tuple[list[dict[str, Any]], dict[str, pd.Series], dict[str, pd.Series]]:
    from .backtest import run_formula_backtest

    rows: list[dict[str, Any]] = []
    values: dict[str, pd.Series] = {}
    signals: dict[str, pd.Series] = {}
    seen: set[str] = set()
    for index, entry in enumerate(entries, start=1):
        formula = str(entry["formula"])
        factor_id = _factor_id(entry, index)
        if factor_id in seen:
            factor_id = f"{factor_id}_{index}"
        seen.add(factor_id)
        row: dict[str, Any] = {
            "factor_id": factor_id,
            "formula": formula,
            "description": entry.get("description", ""),
            "source": entry.get("source", ""),
            "input_passed": entry.get("passed"),
        }
        try:
            factor = evaluate_formula(formula, data)
            ledger = run_formula_backtest(data, formula, cfg.costs, cfg.execution)
            metrics = summarize_ledger(ledger, cfg.bar_hours)
            values[factor_id] = factor
            signals[factor_id] = signal_from_factor(factor, cfg.execution.exposure_threshold)
            row.update({key: round(float(value), 8) for key, value in metrics.items()})
            row["pass_basic"] = _passes_basic(metrics, cfg.filter)
            row["admission_score"] = _admission_score(metrics)
        except Exception as exc:
            row["error"] = str(exc)
            row["pass_basic"] = False
            row["admission_score"] = -math.inf
        rows.append(row)
    return rows, values, signals


def _select_low_correlation_pool(
    factor_rows: list[dict[str, Any]],
    factor_values: dict[str, pd.Series],
    max_corr: float,
    min_factors: int,
) -> tuple[list[str], list[dict[str, Any]]]:
    candidates = [row for row in factor_rows if row.get("pass_basic") and str(row["factor_id"]) in factor_values]
    if len(candidates) < min_factors:
        candidates = [row for row in factor_rows if "error" not in row and str(row["factor_id"]) in factor_values]
    candidates = sorted(candidates, key=lambda row: float(row.get("admission_score", -math.inf)), reverse=True)

    selected: list[str] = []
    decisions: list[dict[str, Any]] = []
    for row in candidates:
        factor_id = str(row["factor_id"])
        corr_pairs = [_abs_corr(factor_values[factor_id], factor_values[other_id]) for other_id in selected]
        max_seen = max(corr_pairs) if corr_pairs else 0.0
        should_select = max_seen <= max_corr or len(selected) < min_factors
        decisions.append(
            {
                "factor_id": factor_id,
                "selected": should_select,
                "max_abs_corr_to_selected": round(float(max_seen), 8),
                "reason": "accepted" if should_select else "rejected_high_correlation",
            }
        )
        if should_select:
            selected.append(factor_id)
    return selected, decisions


def _portfolio_ablation_rows(
    data: pd.DataFrame,
    factor_signals: dict[str, pd.Series],
    spec: PortfolioSpec,
    full_metrics: dict[str, float],
    costs: CostConfig,
    execution: ExecutionConfig,
    bar_hours: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for factor_id, weight in spec.weights.items():
        without = {other_id: other_weight for other_id, other_weight in spec.weights.items() if other_id != factor_id}
        if without:
            ablated = PortfolioSpec(
                portfolio_id=f"{spec.portfolio_id}_without_{factor_id}",
                weighting=spec.weighting,
                weights=_normalize_positive(without),
                description=f"{spec.description} Without {factor_id}.",
            )
            ledger = simulate_weighted_signal_portfolio(data, factor_signals, ablated, costs, execution, bar_hours)
            removed_metrics = summarize_ledger(ledger, bar_hours)
        else:
            removed_metrics = {
                "sharpe": 0.0,
                "rank_ic": 0.0,
                "max_dd": 0.0,
                "turnover": 0.0,
                "trades": 0.0,
                "net_total": 0.0,
            }
        rows.append(
            {
                "portfolio_id": spec.portfolio_id,
                "factor_id": factor_id,
                "weight": round(float(weight), 8),
                "removed_sharpe": round(float(removed_metrics.get("sharpe", 0.0)), 8),
                "full_sharpe": round(float(full_metrics.get("sharpe", 0.0)), 8),
                "delta_sharpe": round(
                    float(full_metrics.get("sharpe", 0.0)) - float(removed_metrics.get("sharpe", 0.0)),
                    8,
                ),
                "removed_net_total": round(float(removed_metrics.get("net_total", 0.0)), 8),
                "full_net_total": round(float(full_metrics.get("net_total", 0.0)), 8),
                "delta_net_total": round(
                    float(full_metrics.get("net_total", 0.0)) - float(removed_metrics.get("net_total", 0.0)),
                    8,
                ),
                "removed_max_dd": round(float(removed_metrics.get("max_dd", 0.0)), 8),
                "full_max_dd": round(float(full_metrics.get("max_dd", 0.0)), 8),
                "delta_max_dd": round(
                    float(full_metrics.get("max_dd", 0.0)) - float(removed_metrics.get("max_dd", 0.0)),
                    8,
                ),
            }
        )
    return rows


def _passes_basic(metrics: dict[str, float], filters: FilterConfig) -> bool:
    return (
        metrics.get("rank_ic", 0.0) >= filters.min_rank_ic
        and metrics.get("directional_win_rate", 0.0) >= filters.min_directional_win_rate
        and metrics.get("sharpe", 0.0) >= filters.min_cost_sharpe
    )


def _admission_score(metrics: dict[str, float]) -> float:
    return (
        float(metrics.get("sharpe", 0.0))
        + 10.0 * float(metrics.get("rank_ic", 0.0))
        - float(metrics.get("max_dd", 0.0))
        - float(metrics.get("turnover", 0.0))
    )


def _metric_weights(rows: list[dict[str, Any]], metric: str) -> dict[str, float]:
    raw = {str(row["factor_id"]): max(float(row.get(metric, 0.0)), 0.0) for row in rows}
    if sum(raw.values()) <= 0.0:
        raw = {factor_id: 1.0 for factor_id in raw}
    return _normalize_positive(raw)


def _normalize_positive(raw: dict[str, float]) -> dict[str, float]:
    total = sum(abs(value) for value in raw.values())
    if total <= 0.0:
        raise ValueError("Cannot normalize empty or zero weights")
    return {key: float(value) / total for key, value in raw.items() if value != 0.0}


def _abs_corr(left: pd.Series, right: pd.Series) -> float:
    corr = left.replace([np.inf, -np.inf], np.nan).corr(right.replace([np.inf, -np.inf], np.nan))
    return 0.0 if pd.isna(corr) else abs(float(corr))


def _factor_id(entry: dict[str, object], index: int) -> str:
    raw = str(entry.get("factor_id") or f"factor_{index:03d}").strip()
    safe = "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in raw)
    if not safe or not safe[0].isalpha():
        safe = f"factor_{index:03d}"
    return safe[:64]


def _fmt(value: Any) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return str(value)
