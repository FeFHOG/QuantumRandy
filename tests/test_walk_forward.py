from __future__ import annotations

from pathlib import Path

import pandas as pd

from quantumrandy.config import CostConfig, ExecutionConfig, FilterConfig, MCTSConfig, ProjectConfig, PromptConfig, WindowConfig
from quantumrandy.walk_forward import build_walk_forward_windows, load_formula_entries, run_walk_forward


def _data(periods: int = 900) -> pd.DataFrame:
    idx = pd.date_range("2020-01-01", periods=periods, freq="4h", tz="UTC")
    close = pd.Series(range(periods), index=idx, dtype=float) + 100.0
    return pd.DataFrame(
        {
            "open": close,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 1000.0,
            "funding_rate": 0.0001,
        },
        index=idx,
    )


def _cfg() -> ProjectConfig:
    return ProjectConfig(
        symbol="TEST",
        bar_hours=4,
        ohlcv_csv=Path("ohlcv.csv"),
        funding_csv=Path("funding.csv"),
        costs=CostConfig(taker_bps=0.0, slippage_bps=0.0, funding_multiplier=0.0),
        execution=ExecutionConfig(delay_bars=1, exposure_threshold=0.0),
        windows=WindowConfig(training_start="2020-01-01", validation_end="2020-05-01"),
        mcts=MCTSConfig(seed_formulas=["zscore(close,12)"]),
        filter=FilterConfig(min_rank_ic=-1.0, min_directional_win_rate=0.0, min_validation_sharpe=-99.0),
        prompt=PromptConfig(),
    )


def test_build_walk_forward_windows_respects_segment_lengths() -> None:
    windows = build_walk_forward_windows(
        _data(),
        train_months=1,
        validation_months=1,
        test_months=1,
        step_months=1,
        start="2020-01-01",
        end="2020-05-01",
        min_bars=20,
    )

    assert len(windows) == 2
    assert windows[0].window_id == "wf_001"
    assert windows[0].train_start.isoformat() == "2020-01-01T00:00:00+00:00"


def test_run_walk_forward_returns_detail_and_summary_rows() -> None:
    data = _data()
    cfg = _cfg()
    windows = build_walk_forward_windows(
        data,
        train_months=1,
        validation_months=1,
        test_months=1,
        step_months=1,
        start="2020-01-01",
        end="2020-05-01",
        min_bars=20,
    )
    entries = load_formula_entries(formulas=["zscore(close,12)"])

    details, summary = run_walk_forward(data, entries, cfg, windows)

    assert len(details) == len(windows) * 3
    assert len(summary) == 1
    assert summary.iloc[0]["windows"] == len(windows)
    assert 0.0 <= summary.iloc[0]["survival_rate"] <= 1.0
