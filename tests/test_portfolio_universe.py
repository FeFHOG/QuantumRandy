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
from quantumrandy.portfolio_universe import run_portfolio_universe_evaluation, write_portfolio_universe_report
from quantumrandy.universe import AssetDataset


def _data(periods: int = 240, *, drift: float = 1.0) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=periods, freq="4h", tz="UTC")
    trend = pd.Series(range(periods), index=idx, dtype=float)
    close = 100.0 + drift * trend + 2.0 * ((trend % 12) / 12.0)
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


def _cfg(symbol: str) -> ProjectConfig:
    return ProjectConfig(
        symbol=symbol,
        bar_hours=4,
        ohlcv_csv=Path("ohlcv.csv"),
        funding_csv=Path("funding.csv"),
        costs=CostConfig(taker_bps=0.0, slippage_bps=0.0, funding_multiplier=0.0),
        execution=ExecutionConfig(delay_bars=1, exposure_threshold=0.0, max_exposure_abs=1.0),
        windows=WindowConfig(),
        mcts=MCTSConfig(seed_formulas=[]),
        filter=FilterConfig(min_rank_ic=-1.0, min_directional_win_rate=0.0, min_cost_sharpe=-99.0),
        prompt=PromptConfig(),
    )


def _manifest() -> dict:
    return {
        "artifact_type": "quantumrandy_portfolio_research",
        "schema_version": 1,
        "safety": {
            "research_only": True,
            "not_runtime_publish_payload": True,
            "requires_manual_review_before_runtime": True,
        },
        "symbol": "BTCUSDT",
        "bar_hours": 4,
        "portfolios": [
            {
                "portfolio_id": "equal_weight_accepted",
                "weighting": "equal_weight",
                "description": "Equal-weight test blend.",
                "weights": {"momentum": 0.5, "carry": 0.5},
            }
        ],
    }


def test_portfolio_universe_evaluates_fixed_blend_across_assets(tmp_path) -> None:
    assets = [
        AssetDataset("BTCUSDT", _cfg("BTCUSDT"), _data(), "btc.yaml"),
        AssetDataset("ETHUSDT", _cfg("ETHUSDT"), _data(drift=1.5), "eth.yaml"),
    ]
    factor_rows = [
        {"factor_id": "momentum", "formula": "zscore(close,12)"},
        {"factor_id": "carry", "formula": "neg(zscore(funding_rate,12))"},
    ]

    details, summary, manifest = run_portfolio_universe_evaluation(assets, _manifest(), factor_rows)

    assert len(details) == 2
    assert len(summary) == 1
    row = summary.iloc[0]
    assert row["portfolio_id"] == "equal_weight_accepted"
    assert row["asset_count"] == 2
    assert row["evaluated_assets"] == 2
    assert "robustness_score" in summary.columns
    assert manifest["artifact_type"] == "quantumrandy_portfolio_universe_robustness"
    assert manifest["safety"]["does_not_update_runtime"] is True

    write_portfolio_universe_report(tmp_path, details=details, summary=summary, manifest=manifest)

    assert (tmp_path / "portfolio_universe_details.csv").exists()
    assert (tmp_path / "portfolio_universe_summary.csv").exists()
    assert (tmp_path / "portfolio_universe_manifest.json").exists()
    report = (tmp_path / "PORTFOLIO_UNIVERSE_REPORT.md").read_text(encoding="utf-8")
    assert "research artifact only" in report
    assert "does not update active strategies" in report
