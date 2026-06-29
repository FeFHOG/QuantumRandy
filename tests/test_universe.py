from __future__ import annotations

from pathlib import Path

import pandas as pd

from quantumrandy.config import (
    CostConfig,
    ExecutionConfig,
    FilterConfig,
    MCTSConfig,
    ProjectConfig,
    PromptConfig,
    WindowConfig,
)
from quantumrandy.universe import AssetDataset, run_universe_evaluation, slice_asset_window


def _data(periods: int = 220, *, drift: float = 1.0) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=periods, freq="4h", tz="UTC")
    close = pd.Series(range(periods), index=idx, dtype=float).mul(drift).add(100.0)
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


def _cfg(symbol: str) -> ProjectConfig:
    return ProjectConfig(
        symbol=symbol,
        bar_hours=4,
        ohlcv_csv=Path("ohlcv.csv"),
        funding_csv=Path("funding.csv"),
        costs=CostConfig(taker_bps=0.0, slippage_bps=0.0, funding_multiplier=0.0),
        execution=ExecutionConfig(delay_bars=1, exposure_threshold=0.0),
        windows=WindowConfig(
            training_start="2024-01-01",
            training_end="2024-01-15",
            validation_start="2024-01-15",
            validation_end="2024-02-01",
        ),
        mcts=MCTSConfig(seed_formulas=["zscore(close,12)"]),
        filter=FilterConfig(min_rank_ic=-1.0, min_directional_win_rate=0.0, min_cost_sharpe=-99.0),
        prompt=PromptConfig(),
    )


def test_run_universe_evaluation_returns_detail_and_summary_rows() -> None:
    assets = [
        AssetDataset("BTCUSDT", _cfg("BTCUSDT"), _data(), "btc.yaml"),
        AssetDataset("ETHUSDT", _cfg("ETHUSDT"), _data(drift=1.5), "eth.yaml"),
    ]
    entries = [{"formula": "zscore(close,12)", "description": "", "source": "test", "passed": None}]

    details, summary = run_universe_evaluation(assets, entries)

    assert len(details) == 2
    assert len(summary) == 1
    assert summary.iloc[0]["asset_count"] == 2
    assert summary.iloc[0]["evaluated_assets"] == 2
    assert "robustness_score" in summary.columns


def test_slice_asset_window_uses_project_windows() -> None:
    cfg = _cfg("BTCUSDT")
    sliced = slice_asset_window(_data(), cfg, "validation")

    assert sliced.index.min().isoformat() == "2024-01-15T00:00:00+00:00"
    assert sliced.index.max() < pd.Timestamp("2024-02-01", tz="UTC")
