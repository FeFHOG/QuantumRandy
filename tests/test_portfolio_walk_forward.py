from __future__ import annotations

import json
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
from quantumrandy.portfolio_walk_forward import (
    load_portfolio_manifest,
    run_portfolio_walk_forward,
    write_portfolio_walk_forward_report,
)
from quantumrandy.walk_forward import build_walk_forward_windows


def _data(periods: int = 900) -> pd.DataFrame:
    idx = pd.date_range("2020-01-01", periods=periods, freq="4h", tz="UTC")
    trend = pd.Series(range(periods), index=idx, dtype=float)
    close = 100.0 + trend + 2.0 * ((trend % 18) / 18.0)
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
        symbol="TEST",
        bar_hours=4,
        ohlcv_csv=Path("ohlcv.csv"),
        funding_csv=Path("funding.csv"),
        costs=CostConfig(taker_bps=0.0, slippage_bps=0.0, funding_multiplier=0.0),
        execution=ExecutionConfig(delay_bars=1, exposure_threshold=0.0, max_exposure_abs=1.0),
        windows=WindowConfig(training_start="2020-01-01", validation_end="2020-05-01"),
        mcts=MCTSConfig(seed_formulas=[]),
        filter=FilterConfig(min_rank_ic=-1.0, min_directional_win_rate=0.0, min_validation_sharpe=-99.0),
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
        "symbol": "TEST",
        "bar_hours": 4,
        "selected_factor_ids": ["momentum", "carry"],
        "portfolios": [
            {
                "portfolio_id": "equal_weight_accepted",
                "weighting": "equal_weight",
                "description": "Equal-weight test blend.",
                "weights": {"momentum": 0.5, "carry": 0.5},
            }
        ],
    }


def _factor_rows() -> list[dict]:
    return [
        {"factor_id": "momentum", "formula": "zscore(close,12)"},
        {"factor_id": "carry", "formula": "neg(zscore(funding_rate,12))"},
    ]


def test_portfolio_walk_forward_outputs_fixed_blend_stability(tmp_path) -> None:
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

    details, summary, manifest = run_portfolio_walk_forward(data, _manifest(), _factor_rows(), cfg, windows)

    assert len(details) == len(windows) * 3
    assert len(summary) == 1
    row = summary.iloc[0]
    assert row["portfolio_id"] == "equal_weight_accepted"
    assert row["windows"] == len(windows)
    assert 0.0 <= row["survival_rate"] <= 1.0
    assert "validation_test_abs_sharpe_gap_mean" in summary.columns
    assert manifest["artifact_type"] == "quantumrandy_portfolio_walk_forward"
    assert manifest["safety"]["does_not_update_runtime"] is True

    write_portfolio_walk_forward_report(
        tmp_path,
        details=details,
        summary=summary,
        windows=windows,
        manifest=manifest,
    )

    assert (tmp_path / "portfolio_walk_forward_details.csv").exists()
    assert (tmp_path / "portfolio_walk_forward_summary.csv").exists()
    assert (tmp_path / "portfolio_walk_forward_manifest.json").exists()
    report = (tmp_path / "PORTFOLIO_WALK_FORWARD_REPORT.md").read_text(encoding="utf-8")
    assert "research artifact only" in report
    assert "does not update active strategies" in report


def test_load_portfolio_manifest_rejects_missing_research_only_flags(tmp_path) -> None:
    path = tmp_path / "portfolio_manifest.json"
    payload = _manifest()
    payload["safety"] = {"research_only": False, "not_runtime_publish_payload": True}
    path.write_text(json.dumps(payload), encoding="utf-8")

    try:
        load_portfolio_manifest(path)
    except ValueError as exc:
        assert "research-only safety flags" in str(exc)
    else:
        raise AssertionError("Expected unsafe manifest to be rejected")
