from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .backtest import run_formula_backtest, summarize_ledger
from .config import FilterConfig, ProjectConfig
from .data import slice_window


@dataclass(frozen=True)
class WalkForwardWindow:
    window_id: str
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    validation_start: pd.Timestamp
    validation_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp


def load_formula_entries(
    leaderboard_path: str | Path | None = None,
    formulas: Iterable[str] | None = None,
    *,
    passed_only: bool = False,
    top: int | None = None,
) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    seen: set[str] = set()

    if leaderboard_path:
        raw = json.loads(Path(leaderboard_path).read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError("leaderboard JSON must contain a list of factor rows")
        for item in raw:
            if not isinstance(item, dict) or "formula" not in item:
                continue
            if passed_only and item.get("passed") is False:
                continue
            formula = str(item["formula"])
            if formula in seen:
                continue
            seen.add(formula)
            entries.append(
                {
                    "factor_id": item.get("factor_id", ""),
                    "formula": formula,
                    "description": item.get("description", ""),
                    "source": "leaderboard",
                    "passed": item.get("passed"),
                    "mcts_score": item.get("mcts_score", item.get("score", "")),
                    "brutal_score": item.get("brutal_score", ""),
                }
            )

    for formula in formulas or []:
        if formula in seen:
            continue
        seen.add(formula)
        entries.append({"formula": formula, "description": "", "source": "cli", "passed": None})

    if top is not None and top > 0:
        entries = entries[:top]
    return entries


def build_walk_forward_windows(
    data: pd.DataFrame,
    *,
    train_months: int = 18,
    validation_months: int = 6,
    test_months: int = 3,
    step_months: int = 3,
    start: str | None = None,
    end: str | None = None,
    min_bars: int = 120,
) -> list[WalkForwardWindow]:
    if data.empty:
        return []
    if train_months <= 0 or validation_months <= 0 or test_months <= 0 or step_months <= 0:
        raise ValueError("walk-forward month values must be positive")

    data_start = data.index.min()
    data_end = data.index.max() + pd.Timedelta(nanoseconds=1)
    cursor = pd.Timestamp(start, tz="UTC") if start else data_start
    limit = pd.Timestamp(end, tz="UTC") if end else data_end

    windows: list[WalkForwardWindow] = []
    idx = 1
    while True:
        train_start = cursor
        train_end = train_start + pd.DateOffset(months=train_months)
        validation_start = train_end
        validation_end = validation_start + pd.DateOffset(months=validation_months)
        test_start = validation_end
        test_end = test_start + pd.DateOffset(months=test_months)
        if test_end > limit:
            break

        train = slice_window(data, str(train_start), str(train_end))
        validation = slice_window(data, str(validation_start), str(validation_end))
        test = slice_window(data, str(test_start), str(test_end))
        if len(train) >= min_bars and len(validation) >= min_bars and len(test) >= min_bars:
            windows.append(
                WalkForwardWindow(
                    window_id=f"wf_{idx:03d}",
                    train_start=train_start,
                    train_end=train_end,
                    validation_start=validation_start,
                    validation_end=validation_end,
                    test_start=test_start,
                    test_end=test_end,
                )
            )
            idx += 1
        cursor = cursor + pd.DateOffset(months=step_months)
    return windows


def run_walk_forward(
    data: pd.DataFrame,
    entries: list[dict[str, object]],
    cfg: ProjectConfig,
    windows: list[WalkForwardWindow],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []

    for entry_index, entry in enumerate(entries, start=1):
        formula = str(entry["formula"])
        formula_rows: list[dict[str, object]] = []
        for window in windows:
            for segment, start, end in (
                ("train", window.train_start, window.train_end),
                ("validation", window.validation_start, window.validation_end),
                ("test", window.test_start, window.test_end),
            ):
                segment_data = slice_window(data, str(start), str(end))
                row = {
                    "formula_index": entry_index,
                    "formula": formula,
                    "description": entry.get("description", ""),
                    "source": entry.get("source", ""),
                    "window_id": window.window_id,
                    "segment": segment,
                    "start": _iso(start),
                    "end": _iso(end),
                }
                try:
                    ledger = run_formula_backtest(segment_data, formula, cfg.costs, cfg.execution)
                    metrics = summarize_ledger(ledger, cfg.bar_hours)
                    row.update(_prefixed_metrics("", metrics))
                    row["pass_basic"] = _passes_basic(metrics, cfg.filter)
                except Exception as exc:
                    row["error"] = str(exc)
                    row["pass_basic"] = False
                rows.append(row)
                formula_rows.append(row)

        summary_rows.append(_summarize_formula(entry_index, entry, formula_rows))

    details = pd.DataFrame(rows)
    summary = pd.DataFrame(summary_rows)
    return details, summary


def _summarize_formula(entry_index: int, entry: dict[str, object], rows: list[dict[str, object]]) -> dict[str, object]:
    by_window: dict[str, dict[str, dict[str, object]]] = {}
    for row in rows:
        by_window.setdefault(str(row["window_id"]), {})[str(row["segment"])] = row

    survived = 0
    validation_passes = 0
    test_passes = 0
    complete_windows = 0
    test_sharpes: list[float] = []
    test_rank_ics: list[float] = []
    test_max_dds: list[float] = []
    test_turnovers: list[float] = []

    for segments in by_window.values():
        validation = segments.get("validation")
        test = segments.get("test")
        if not validation or not test:
            continue
        complete_windows += 1
        validation_pass = bool(validation.get("pass_basic"))
        test_pass = bool(test.get("pass_basic"))
        validation_passes += int(validation_pass)
        test_passes += int(test_pass)
        survived += int(validation_pass and test_pass)
        if "sharpe" in test:
            test_sharpes.append(float(test["sharpe"]))
        if "rank_ic" in test:
            test_rank_ics.append(float(test["rank_ic"]))
        if "max_dd" in test:
            test_max_dds.append(float(test["max_dd"]))
        if "turnover" in test:
            test_turnovers.append(float(test["turnover"]))

    return {
        "formula_index": entry_index,
        "formula": entry["formula"],
        "description": entry.get("description", ""),
        "source": entry.get("source", ""),
        "input_passed": entry.get("passed"),
        "mcts_score": entry.get("mcts_score", ""),
        "brutal_score": entry.get("brutal_score", ""),
        "windows": complete_windows,
        "survived_windows": survived,
        "survival_rate": _ratio(survived, complete_windows),
        "validation_pass_rate": _ratio(validation_passes, complete_windows),
        "test_pass_rate": _ratio(test_passes, complete_windows),
        "test_sharpe_mean": _mean(test_sharpes),
        "test_sharpe_median": _median(test_sharpes),
        "test_sharpe_min": min(test_sharpes) if test_sharpes else 0.0,
        "test_rank_ic_mean": _mean(test_rank_ics),
        "test_rank_ic_median": _median(test_rank_ics),
        "test_max_dd_mean": _mean(test_max_dds),
        "test_turnover_mean": _mean(test_turnovers),
    }


def _passes_basic(metrics: dict[str, float], filters: FilterConfig) -> bool:
    return (
        metrics.get("rank_ic", 0.0) >= filters.min_rank_ic
        and metrics.get("directional_win_rate", 0.0) >= filters.min_directional_win_rate
        and metrics.get("sharpe", 0.0) >= filters.min_validation_sharpe
    )


def _prefixed_metrics(prefix: str, metrics: dict[str, float]) -> dict[str, float]:
    return {f"{prefix}{key}": round(float(value), 8) for key, value in metrics.items()}


def _iso(ts: pd.Timestamp) -> str:
    return ts.isoformat()


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

