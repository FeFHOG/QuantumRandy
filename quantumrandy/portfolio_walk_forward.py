from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from .backtest import signal_from_factor, summarize_ledger
from .config import FilterConfig, ProjectConfig
from .data import slice_window
from .expression import evaluate_formula
from .io_utils import safe_write_csv, safe_write_json, safe_write_text
from .portfolio import PortfolioSpec, simulate_weighted_signal_portfolio
from .walk_forward import WalkForwardWindow


def load_portfolio_manifest(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("portfolio manifest must be a JSON object")
    if payload.get("artifact_type") != "quantumrandy_portfolio_research":
        raise ValueError("portfolio manifest is not a QuantumRandy portfolio research artifact")
    safety = payload.get("safety") or {}
    if not safety.get("research_only") or not safety.get("not_runtime_publish_payload"):
        raise ValueError("portfolio manifest does not carry the required research-only safety flags")
    return payload


def load_portfolio_factor_rows(path: str | Path) -> list[dict[str, Any]]:
    frame = pd.read_csv(path)
    if "factor_id" not in frame.columns or "formula" not in frame.columns:
        raise ValueError("portfolio_factors.csv must include factor_id and formula columns")
    rows = []
    for item in frame.to_dict(orient="records"):
        if item.get("factor_id") and item.get("formula"):
            rows.append(item)
    return rows


def portfolio_specs_from_manifest(
    manifest: dict[str, Any],
    *,
    portfolio_ids: list[str] | None = None,
) -> list[PortfolioSpec]:
    wanted = set(portfolio_ids or [])
    specs: list[PortfolioSpec] = []
    for item in manifest.get("portfolios") or []:
        portfolio_id = str(item.get("portfolio_id") or "")
        if not portfolio_id or (wanted and portfolio_id not in wanted):
            continue
        weights = item.get("weights") or {}
        if not isinstance(weights, dict) or not weights:
            continue
        specs.append(
            PortfolioSpec(
                portfolio_id=portfolio_id,
                weighting=str(item.get("weighting") or ""),
                weights={str(factor_id): float(weight) for factor_id, weight in weights.items()},
                description=str(item.get("description") or ""),
            )
        )
    if wanted and len(specs) != len(wanted):
        found = {spec.portfolio_id for spec in specs}
        missing = sorted(wanted - found)
        raise ValueError(f"Portfolio id not found in manifest: {', '.join(missing)}")
    if not specs:
        raise ValueError("No portfolio specs found in manifest")
    return specs


def run_portfolio_walk_forward(
    data: pd.DataFrame,
    manifest: dict[str, Any],
    factor_rows: list[dict[str, Any]],
    cfg: ProjectConfig,
    windows: list[WalkForwardWindow],
    *,
    portfolio_ids: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    specs = portfolio_specs_from_manifest(manifest, portfolio_ids=portfolio_ids)
    formulas_by_id = {str(row["factor_id"]): str(row["formula"]) for row in factor_rows if row.get("factor_id")}
    details: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []

    for spec in specs:
        portfolio_rows: list[dict[str, Any]] = []
        missing = [factor_id for factor_id in spec.weights if factor_id not in formulas_by_id]
        if missing:
            raise ValueError(f"Missing formula rows for portfolio factors: {', '.join(sorted(missing))}")

        for window in windows:
            for segment, start, end in (
                ("train", window.train_start, window.train_end),
                ("validation", window.validation_start, window.validation_end),
                ("test", window.test_start, window.test_end),
            ):
                segment_data = slice_window(data, str(start), str(end))
                row: dict[str, Any] = {
                    "portfolio_id": spec.portfolio_id,
                    "weighting": spec.weighting,
                    "factor_count": len(spec.weights),
                    "weights": _format_weights(spec.weights),
                    "window_id": window.window_id,
                    "segment": segment,
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                }
                try:
                    factor_signals = _evaluate_segment_signals(segment_data, spec, formulas_by_id, cfg)
                    ledger = simulate_weighted_signal_portfolio(
                        segment_data,
                        factor_signals,
                        spec,
                        cfg.costs,
                        cfg.execution,
                        cfg.bar_hours,
                    )
                    metrics = summarize_ledger(ledger, cfg.bar_hours)
                    row.update({key: round(float(value), 8) for key, value in metrics.items()})
                    row["pass_basic"] = _passes_portfolio_segment(metrics, cfg.filter)
                except Exception as exc:
                    row["error"] = str(exc)
                    row["pass_basic"] = False
                details.append(row)
                portfolio_rows.append(row)
        summary_rows.append(_summarize_portfolio(spec, portfolio_rows))

    summary = pd.DataFrame(summary_rows)
    details_frame = pd.DataFrame(details)
    output_manifest = {
        "artifact_type": "quantumrandy_portfolio_walk_forward",
        "schema_version": 1,
        "safety": {
            "research_only": True,
            "not_runtime_publish_payload": True,
            "does_not_update_runtime": True,
            "requires_manual_review_before_runtime": True,
        },
        "symbol": cfg.symbol,
        "bar_hours": cfg.bar_hours,
        "source_portfolio_manifest": manifest.get("artifact_type"),
        "portfolio_count": len(specs),
        "window_count": len(windows),
        "portfolio_ids": [spec.portfolio_id for spec in specs],
        "pass_rule": {
            "rank_ic_gte": cfg.filter.min_rank_ic,
            "directional_win_rate_gte": cfg.filter.min_directional_win_rate,
            "sharpe_gte": cfg.filter.min_validation_sharpe,
            "survived_window": "validation_pass_basic AND test_pass_basic",
        },
    }
    return details_frame, summary, output_manifest


def write_portfolio_walk_forward_report(
    out_dir: str | Path,
    *,
    details: pd.DataFrame,
    summary: pd.DataFrame,
    windows: list[WalkForwardWindow],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    safe_write_csv(out / "portfolio_walk_forward_details.csv", details, out / "events.jsonl")
    safe_write_csv(out / "portfolio_walk_forward_summary.csv", summary, out / "events.jsonl")
    safe_write_json(out / "portfolio_walk_forward_windows.json", [_window_dict(window) for window in windows], out / "events.jsonl")
    safe_write_json(out / "portfolio_walk_forward_manifest.json", manifest, out / "events.jsonl")
    safe_write_text(
        out / "PORTFOLIO_WALK_FORWARD_REPORT.md",
        render_portfolio_walk_forward_report(manifest, summary, windows),
        out / "events.jsonl",
    )
    return manifest


def render_portfolio_walk_forward_report(
    manifest: dict[str, Any],
    summary: pd.DataFrame,
    windows: list[WalkForwardWindow],
) -> str:
    lines = [
        "# QuantumRandy Portfolio Walk-Forward Report",
        "",
        "This is a research artifact only. It is not a runtime publish payload and does not update active strategies.",
        "",
        "## Run",
        "",
        f"- Symbol: `{manifest['symbol']}`",
        f"- Bar hours: `{manifest['bar_hours']}`",
        f"- Windows: `{len(windows)}`",
        f"- Portfolios: `{manifest['portfolio_count']}`",
        "",
        "## Pass Rule",
        "",
        f"- Segment pass: `rank_ic >= {manifest['pass_rule']['rank_ic_gte']}` AND "
        f"`directional_win_rate >= {manifest['pass_rule']['directional_win_rate_gte']}` AND "
        f"`sharpe >= {manifest['pass_rule']['sharpe_gte']}`",
        "- Window survival: validation segment passes AND test segment passes.",
        "",
        "## Portfolio Stability",
        "",
    ]
    if summary.empty:
        lines.append("No portfolios evaluated.")
    else:
        lines.append(
            "| Portfolio | Weighting | Factors | Survival | Test Pass | Median Test Sharpe | "
            "Median Test Rank IC | Worst Test Sharpe | Test DD Mean | Turnover Mean | Abs Sharpe Gap |"
        )
        lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for row in summary.to_dict(orient="records"):
            lines.append(
                "| {portfolio_id} | {weighting} | {factor_count} | {survival_rate:.2f} | {test_pass_rate:.2f} | "
                "{test_sharpe_median:.2f} | {test_rank_ic_median:.4f} | {test_sharpe_min:.2f} | "
                "{test_max_dd_mean:.4f} | {test_turnover_mean:.4f} | {validation_test_abs_sharpe_gap_mean:.2f} |".format(
                    **row
                )
            )
    lines.extend(
        [
            "",
            "## Files",
            "",
            "- `portfolio_walk_forward_details.csv`: every portfolio x window x segment metric row.",
            "- `portfolio_walk_forward_summary.csv`: portfolio-level survival and stability summary.",
            "- `portfolio_walk_forward_windows.json`: exact train/validation/test date boundaries.",
            "- `portfolio_walk_forward_manifest.json`: research-only run metadata.",
        ]
    )
    return "\n".join(lines) + "\n"


def _evaluate_segment_signals(
    data: pd.DataFrame,
    spec: PortfolioSpec,
    formulas_by_id: dict[str, str],
    cfg: ProjectConfig,
) -> dict[str, pd.Series]:
    signals = {}
    for factor_id in spec.weights:
        factor = evaluate_formula(formulas_by_id[factor_id], data)
        signals[factor_id] = signal_from_factor(factor, cfg.execution.exposure_threshold)
    return signals


def _summarize_portfolio(spec: PortfolioSpec, rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_window: dict[str, dict[str, dict[str, Any]]] = {}
    for row in rows:
        by_window.setdefault(str(row["window_id"]), {})[str(row["segment"])] = row

    complete_windows = 0
    validation_passes = 0
    test_passes = 0
    survived_windows = 0
    test_sharpes: list[float] = []
    test_rank_ics: list[float] = []
    test_max_dds: list[float] = []
    test_turnovers: list[float] = []
    validation_test_gaps: list[float] = []
    train_test_gaps: list[float] = []

    for segments in by_window.values():
        validation = segments.get("validation")
        test = segments.get("test")
        train = segments.get("train")
        if not validation or not test:
            continue
        complete_windows += 1
        validation_pass = bool(validation.get("pass_basic"))
        test_pass = bool(test.get("pass_basic"))
        validation_passes += int(validation_pass)
        test_passes += int(test_pass)
        survived_windows += int(validation_pass and test_pass)
        if "sharpe" in test:
            test_sharpes.append(float(test["sharpe"]))
        if "rank_ic" in test:
            test_rank_ics.append(float(test["rank_ic"]))
        if "max_dd" in test:
            test_max_dds.append(float(test["max_dd"]))
        if "turnover" in test:
            test_turnovers.append(float(test["turnover"]))
        if "sharpe" in validation and "sharpe" in test:
            validation_test_gaps.append(abs(float(validation["sharpe"]) - float(test["sharpe"])))
        if train and "sharpe" in train and "sharpe" in test:
            train_test_gaps.append(abs(float(train["sharpe"]) - float(test["sharpe"])))

    return {
        "portfolio_id": spec.portfolio_id,
        "weighting": spec.weighting,
        "factor_count": len(spec.weights),
        "weights": _format_weights(spec.weights),
        "windows": complete_windows,
        "survived_windows": survived_windows,
        "survival_rate": _ratio(survived_windows, complete_windows),
        "validation_pass_rate": _ratio(validation_passes, complete_windows),
        "test_pass_rate": _ratio(test_passes, complete_windows),
        "test_sharpe_mean": _mean(test_sharpes),
        "test_sharpe_median": _median(test_sharpes),
        "test_sharpe_min": min(test_sharpes) if test_sharpes else 0.0,
        "test_rank_ic_mean": _mean(test_rank_ics),
        "test_rank_ic_median": _median(test_rank_ics),
        "test_max_dd_mean": _mean(test_max_dds),
        "test_turnover_mean": _mean(test_turnovers),
        "validation_test_abs_sharpe_gap_mean": _mean(validation_test_gaps),
        "train_test_abs_sharpe_gap_mean": _mean(train_test_gaps),
    }


def _passes_portfolio_segment(metrics: dict[str, float], filters: FilterConfig) -> bool:
    return (
        metrics.get("rank_ic", 0.0) >= filters.min_rank_ic
        and metrics.get("directional_win_rate", 0.0) >= filters.min_directional_win_rate
        and metrics.get("sharpe", 0.0) >= filters.min_validation_sharpe
    )


def _window_dict(window: WalkForwardWindow) -> dict[str, str]:
    return {
        "window_id": window.window_id,
        "train_start": window.train_start.isoformat(),
        "train_end": window.train_end.isoformat(),
        "validation_start": window.validation_start.isoformat(),
        "validation_end": window.validation_end.isoformat(),
        "test_start": window.test_start.isoformat(),
        "test_end": window.test_end.isoformat(),
    }


def _format_weights(weights: dict[str, float]) -> str:
    return ",".join(f"{factor_id}:{weight:.6f}" for factor_id, weight in weights.items())


def _ratio(num: int, den: int) -> float:
    if den <= 0:
        return 0.0
    return round(num / den, 6)


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(float(pd.Series(values).mean()), 8)


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(float(pd.Series(values).median()), 8)
