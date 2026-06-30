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
from quantumrandy.portfolio import build_portfolio_research, render_portfolio_report


def _data(periods: int = 240) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=periods, freq="4h", tz="UTC")
    trend = pd.Series(range(periods), index=idx, dtype=float)
    close = 100.0 + trend + 5.0 * ((trend % 12) / 12.0)
    return pd.DataFrame(
        {
            "open": close - 0.2,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 1000.0 + trend,
            "funding_rate": 0.0001,
        },
        index=idx,
    )


def _cfg() -> ProjectConfig:
    return ProjectConfig(
        symbol="BTCUSDT",
        bar_hours=4,
        ohlcv_csv=Path("ohlcv.csv"),
        funding_csv=Path("funding.csv"),
        costs=CostConfig(taker_bps=0.0, slippage_bps=0.0, funding_multiplier=0.0),
        execution=ExecutionConfig(delay_bars=1, exposure_threshold=0.0, max_exposure_abs=1.0),
        windows=WindowConfig(),
        mcts=MCTSConfig(seed_formulas=[]),
        filter=FilterConfig(
            min_rank_ic=-1.0,
            min_directional_win_rate=0.0,
            min_cost_sharpe=-99.0,
            max_corr=0.5,
        ),
        prompt=PromptConfig(),
    )


def test_build_portfolio_research_outputs_research_only_artifacts() -> None:
    entries = [
        {"factor_id": "momentum", "formula": "zscore(close,12)", "passed": True},
        {"factor_id": "carry", "formula": "neg(zscore(funding_rate,12))", "passed": True},
        {"factor_id": "volume", "formula": "zscore(volume,12)", "passed": True},
    ]

    factors, selection, portfolios, contribution, manifest = build_portfolio_research(
        _data(),
        entries,
        _cfg(),
        min_factors=2,
    )

    assert len(factors) == 3
    assert len(selection[selection["selected"]]) >= 2
    assert set(portfolios["portfolio_id"]) == {
        "equal_weight_accepted",
        "ic_weight_accepted",
        "sharpe_weight_accepted",
    }
    assert manifest["artifact_type"] == "quantumrandy_portfolio_research"
    assert manifest["safety"]["not_runtime_publish_payload"] is True
    assert manifest["safety"]["requires_manual_review_before_runtime"] is True
    assert not contribution.empty
    assert {"portfolio_id", "factor_id", "delta_sharpe", "delta_net_total", "delta_max_dd"}.issubset(
        contribution.columns
    )

    report = render_portfolio_report(manifest, factors, selection, portfolios, contribution)
    assert "research artifact only" in report
    assert "equal_weight_accepted" in report
    assert "Factor Ablation" in report
