from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .backtest import signal_from_factor, summarize_ledger
from .expression import evaluate_formula
from .io_utils import safe_write_csv, safe_write_json, safe_write_text
from .portfolio import PortfolioSpec, simulate_weighted_signal_portfolio
from .portfolio_walk_forward import portfolio_specs_from_manifest
from .universe import AssetDataset
from .walk_forward import _median


def run_portfolio_universe_evaluation(
    assets: list[AssetDataset],
    manifest: dict[str, Any],
    factor_rows: list[dict[str, Any]],
    *,
    portfolio_ids: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    specs = portfolio_specs_from_manifest(manifest, portfolio_ids=portfolio_ids)
    formulas_by_id = {str(row["factor_id"]): str(row["formula"]) for row in factor_rows if row.get("factor_id")}
    detail_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []

    for spec in specs:
        missing = [factor_id for factor_id in spec.weights if factor_id not in formulas_by_id]
        if missing:
            raise ValueError(f"Missing formula rows for portfolio factors: {', '.join(sorted(missing))}")

        portfolio_rows: list[dict[str, Any]] = []
        for asset in assets:
            row: dict[str, Any] = {
                "portfolio_id": spec.portfolio_id,
                "weighting": spec.weighting,
                "factor_count": len(spec.weights),
                "weights": _format_weights(spec.weights),
                "asset": asset.name,
                "config": asset.config_path,
                "bars": float(len(asset.data)),
            }
            try:
                factor_signals = _evaluate_asset_signals(asset.data, spec, formulas_by_id, asset.cfg.execution.exposure_threshold)
                ledger = simulate_weighted_signal_portfolio(
                    asset.data,
                    factor_signals,
                    spec,
                    asset.cfg.costs,
                    asset.cfg.execution,
                    asset.cfg.bar_hours,
                )
                metrics = summarize_ledger(ledger, asset.cfg.bar_hours)
                row.update({key: round(float(value), 8) for key, value in metrics.items()})
                row["pass_basic"] = _passes_asset(metrics, asset.cfg)
            except Exception as exc:
                row["error"] = str(exc)
                row["pass_basic"] = False
            detail_rows.append(row)
            portfolio_rows.append(row)
        summary_rows.append(_summarize_portfolio_universe(spec, portfolio_rows))

    details = pd.DataFrame(detail_rows)
    summary = pd.DataFrame(summary_rows)
    output_manifest = {
        "artifact_type": "quantumrandy_portfolio_universe_robustness",
        "schema_version": 1,
        "safety": {
            "research_only": True,
            "not_runtime_publish_payload": True,
            "does_not_update_runtime": True,
            "requires_manual_review_before_runtime": True,
        },
        "source_portfolio_manifest": manifest.get("artifact_type"),
        "portfolio_count": len(specs),
        "portfolio_ids": [spec.portfolio_id for spec in specs],
        "asset_count": len(assets),
        "assets": [
            {
                "symbol": asset.name,
                "config": asset.config_path,
                "bars": len(asset.data),
                "ohlcv_csv": str(asset.cfg.ohlcv_csv),
                "funding_csv": str(asset.cfg.funding_csv),
            }
            for asset in assets
        ],
        "score": "mean_sharpe + 10*median_rank_ic + pass_rate - sharpe_variance - worst_max_dd",
    }
    return details, summary, output_manifest


def write_portfolio_universe_report(
    out_dir: str | Path,
    *,
    details: pd.DataFrame,
    summary: pd.DataFrame,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    safe_write_csv(out / "portfolio_universe_details.csv", details, out / "events.jsonl")
    safe_write_csv(out / "portfolio_universe_summary.csv", summary, out / "events.jsonl")
    safe_write_json(out / "portfolio_universe_manifest.json", manifest, out / "events.jsonl")
    safe_write_text(
        out / "PORTFOLIO_UNIVERSE_REPORT.md",
        render_portfolio_universe_report(manifest, summary),
        out / "events.jsonl",
    )
    return manifest


def render_portfolio_universe_report(manifest: dict[str, Any], summary: pd.DataFrame) -> str:
    lines = [
        "# QuantumRandy Portfolio Universe Robustness Report",
        "",
        "This is a research artifact only. It is not a runtime publish payload and does not update active strategies.",
        "",
        "## Run",
        "",
        f"- Asset configs: `{manifest['asset_count']}`",
        f"- Portfolios: `{manifest['portfolio_count']}`",
        f"- Robustness score: `{manifest['score']}`",
        "",
        "## Portfolio Robustness",
        "",
    ]
    if summary.empty:
        lines.append("No portfolios evaluated.")
    else:
        lines.append(
            "| Portfolio | Score | Pass Rate | Passed Assets | Mean Sharpe | Median Rank IC | Worst Max DD | Mean Turnover |"
        )
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
        for row in summary.to_dict(orient="records"):
            lines.append(
                "| {portfolio_id} | {robustness_score:.2f} | {pass_rate:.2f} | "
                "{passed_assets}/{asset_count} | {mean_sharpe:.2f} | {median_rank_ic:.4f} | "
                "{worst_max_dd:.4f} | {mean_turnover:.4f} |".format(**row)
            )
    lines.extend(
        [
            "",
            "## Files",
            "",
            "- `portfolio_universe_details.csv`: every portfolio x asset metric row.",
            "- `portfolio_universe_summary.csv`: portfolio-level cross-asset robustness summary.",
            "- `portfolio_universe_manifest.json`: research-only run metadata.",
        ]
    )
    return "\n".join(lines) + "\n"


def _evaluate_asset_signals(
    data: pd.DataFrame,
    spec: PortfolioSpec,
    formulas_by_id: dict[str, str],
    exposure_threshold: float,
) -> dict[str, pd.Series]:
    signals = {}
    for factor_id in spec.weights:
        factor = evaluate_formula(formulas_by_id[factor_id], data)
        signals[factor_id] = signal_from_factor(factor, exposure_threshold)
    return signals


def _passes_asset(metrics: dict[str, float], cfg) -> bool:
    return (
        metrics.get("rank_ic", 0.0) >= cfg.filter.min_rank_ic
        and metrics.get("directional_win_rate", 0.0) >= cfg.filter.min_directional_win_rate
        and metrics.get("sharpe", 0.0) >= cfg.filter.min_cost_sharpe
    )


def _summarize_portfolio_universe(spec: PortfolioSpec, rows: list[dict[str, Any]]) -> dict[str, Any]:
    valid_rows = [row for row in rows if "error" not in row]
    asset_count = len(rows)
    evaluated_assets = len(valid_rows)
    passed_assets = sum(1 for row in valid_rows if bool(row.get("pass_basic")))
    sharpes = [float(row["sharpe"]) for row in valid_rows if "sharpe" in row]
    rank_ics = [float(row["rank_ic"]) for row in valid_rows if "rank_ic" in row]
    max_dds = [float(row["max_dd"]) for row in valid_rows if "max_dd" in row]
    turnovers = [float(row["turnover"]) for row in valid_rows if "turnover" in row]

    sharpe_series = pd.Series(sharpes, dtype=float)
    sharpe_variance = float(sharpe_series.var(ddof=0)) if len(sharpe_series) > 1 else 0.0
    mean_sharpe = _mean(sharpes)
    median_rank_ic = _median(rank_ics)
    worst_max_dd = max(max_dds) if max_dds else 0.0
    pass_rate = _ratio(passed_assets, asset_count)
    robustness_score = round(mean_sharpe + 10.0 * median_rank_ic + pass_rate - sharpe_variance - worst_max_dd, 8)

    return {
        "portfolio_id": spec.portfolio_id,
        "weighting": spec.weighting,
        "factor_count": len(spec.weights),
        "weights": _format_weights(spec.weights),
        "asset_count": asset_count,
        "evaluated_assets": evaluated_assets,
        "passed_assets": passed_assets,
        "pass_rate": pass_rate,
        "mean_sharpe": mean_sharpe,
        "median_sharpe": _median(sharpes),
        "min_sharpe": min(sharpes) if sharpes else 0.0,
        "sharpe_variance": round(sharpe_variance, 8),
        "median_rank_ic": median_rank_ic,
        "mean_rank_ic": _mean(rank_ics),
        "worst_max_dd": round(float(worst_max_dd), 8),
        "mean_turnover": _mean(turnovers),
        "robustness_score": robustness_score,
        "failed_assets": ",".join(str(row["asset"]) for row in rows if not bool(row.get("pass_basic"))),
    }


def _format_weights(weights: dict[str, float]) -> str:
    return ",".join(f"{factor_id}:{weight:.6f}" for factor_id, weight in weights.items())


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(float(pd.Series(values, dtype=float).mean()), 8)


def _ratio(num: int, den: int) -> float:
    if den <= 0:
        return 0.0
    return round(num / den, 6)
