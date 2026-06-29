from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .backtest import run_formula_backtest, summarize_ledger
from .config import ProjectConfig
from .data import load_market_frame, slice_window
from .walk_forward import _median, _prefixed_metrics


@dataclass(frozen=True)
class AssetDataset:
    name: str
    cfg: ProjectConfig
    data: pd.DataFrame
    config_path: str = ""


def load_asset_dataset(config_path: str | Path, *, window: str = "validation") -> AssetDataset:
    from .config import load_config

    cfg = load_config(config_path)
    data = load_market_frame(cfg.ohlcv_csv, cfg.funding_csv)
    data = slice_asset_window(data, cfg, window)
    return AssetDataset(name=cfg.symbol, cfg=cfg, data=data, config_path=str(config_path))


def slice_asset_window(data: pd.DataFrame, cfg: ProjectConfig, window: str) -> pd.DataFrame:
    if window == "training":
        return slice_window(data, cfg.windows.training_start, cfg.windows.training_end)
    if window == "validation":
        return slice_window(data, cfg.windows.validation_start, cfg.windows.validation_end)
    if window == "all":
        return data.copy()
    raise ValueError("window must be one of: training, validation, all")


def run_universe_evaluation(
    assets: list[AssetDataset],
    entries: list[dict[str, object]],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    detail_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []

    for formula_index, entry in enumerate(entries, start=1):
        formula = str(entry["formula"])
        formula_rows: list[dict[str, object]] = []
        for asset in assets:
            row = {
                "formula_index": formula_index,
                "formula": formula,
                "description": entry.get("description", ""),
                "source": entry.get("source", ""),
                "input_passed": entry.get("passed"),
                "asset": asset.name,
                "config": asset.config_path,
                "bars": float(len(asset.data)),
            }
            try:
                ledger = run_formula_backtest(asset.data, formula, asset.cfg.costs, asset.cfg.execution)
                metrics = summarize_ledger(ledger, asset.cfg.bar_hours)
                row.update(_prefixed_metrics("", metrics))
                row["pass_basic"] = _passes_asset(metrics, asset.cfg)
            except Exception as exc:
                row["error"] = str(exc)
                row["pass_basic"] = False
            detail_rows.append(row)
            formula_rows.append(row)

        summary_rows.append(_summarize_formula(formula_index, entry, formula_rows))

    details = pd.DataFrame(detail_rows)
    summary = pd.DataFrame(summary_rows)
    return details, summary


def _passes_asset(metrics: dict[str, float], cfg: ProjectConfig) -> bool:
    return (
        metrics.get("rank_ic", 0.0) >= cfg.filter.min_rank_ic
        and metrics.get("directional_win_rate", 0.0) >= cfg.filter.min_directional_win_rate
        and metrics.get("sharpe", 0.0) >= cfg.filter.min_cost_sharpe
    )


def _summarize_formula(entry_index: int, entry: dict[str, object], rows: list[dict[str, object]]) -> dict[str, object]:
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
        "formula_index": entry_index,
        "formula": entry["formula"],
        "description": entry.get("description", ""),
        "source": entry.get("source", ""),
        "input_passed": entry.get("passed"),
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


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(float(pd.Series(values, dtype=float).mean()), 8)


def _ratio(num: int, den: int) -> float:
    if den <= 0:
        return 0.0
    return round(num / den, 6)
