from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import yaml

from quantumrandy.candidate_selector import write_candidate_selector_report
from quantumrandy.selector_pipeline import run_selector_rewrite_pipeline


def _market(periods: int = 240, *, drift: float = 1.0) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=periods, freq="4h", tz="UTC")
    trend = pd.Series(range(periods), index=idx, dtype=float)
    close = 100.0 + drift * trend + 2.0 * ((trend % 12) / 12.0)
    return pd.DataFrame(
        {
            "timestamp": idx,
            "open": close - 0.2,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 1000.0 + trend,
        }
    )


def _funding(periods: int = 240) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=periods, freq="4h", tz="UTC")
    return pd.DataFrame({"timestamp": idx, "funding_rate": 0.0001})


def _write_config(tmp_path: Path, symbol: str, *, drift: float = 1.0) -> Path:
    root = tmp_path / symbol.lower()
    root.mkdir()
    ohlcv = root / "ohlcv.csv"
    funding = root / "funding.csv"
    config = root / "config.yaml"
    _market(drift=drift).to_csv(ohlcv, index=False)
    _funding().to_csv(funding, index=False)
    config.write_text(
        yaml.safe_dump(
            {
                "symbol": symbol,
                "bar_hours": 4,
                "ohlcv_csv": "ohlcv.csv",
                "funding_csv": "funding.csv",
                "costs": {"taker_bps": 0.0, "slippage_bps": 0.0, "funding_multiplier": 0.0},
                "execution": {"delay_bars": 1, "exposure_threshold": 0.0, "max_exposure_abs": 1.0},
                "windows": {
                    "training_start": "2024-01-01",
                    "training_end": "2024-01-15",
                    "validation_start": "2024-01-15",
                    "validation_end": "2024-02-01",
                },
                "mcts": {"seed_formulas": []},
                "filter": {"min_rank_ic": -1.0, "min_directional_win_rate": 0.0, "min_cost_sharpe": -99.0},
            }
        ),
        encoding="utf-8",
    )
    return config


def _selector_artifact(tmp_path: Path) -> Path:
    selector = tmp_path / "selector"
    leaderboard = [
        {
            "factor_id": "weak_momentum",
            "formula": "zscore(ret(close,6),48)",
            "passed": True,
            "brutal_score": 60.0,
        }
    ]
    universe = pd.DataFrame(
        [
            {
                "factor_id": "weak_momentum",
                "formula": "zscore(ret(close,6),48)",
                "pass_rate": 0.2,
                "evaluated_assets": 5,
                "mean_sharpe": 0.1,
                "median_rank_ic": 0.0,
                "failed_assets": "ETHUSDT,SOLUSDT",
            }
        ]
    )
    write_candidate_selector_report(leaderboard, selector, universe_summary=universe)
    return selector


def test_selector_rewrite_pipeline_runs_research_only_evidence_chain(tmp_path) -> None:
    selector = _selector_artifact(tmp_path)
    configs = [
        _write_config(tmp_path, "BTCUSDT"),
        _write_config(tmp_path, "ETHUSDT", drift=1.5),
    ]

    manifest = run_selector_rewrite_pipeline(
        selector_path=selector,
        out_dir=tmp_path / "pipeline",
        config_paths=configs,
        candidates_per_target=1,
    )

    assert manifest["artifact_type"] == "quantumrandy_selector_rewrite_research_pipeline"
    assert manifest["safety"]["not_runtime_publish_payload"] is True
    assert manifest["safety"]["does_not_update_runtime"] is True
    assert manifest["rewrite"]["candidate_count"] == 1
    assert manifest["universe"]["status"] == "completed"
    assert manifest["portfolio"]["status"] == "completed"
    assert manifest["portfolio_universe"]["status"] == "completed"
    assert (tmp_path / "pipeline" / "rewrite" / "selector_rewrite_candidates.json").exists()
    assert (tmp_path / "pipeline" / "universe" / "universe_summary.csv").exists()
    assert (tmp_path / "pipeline" / "portfolio" / "portfolio_manifest.json").exists()
    assert (tmp_path / "pipeline" / "portfolio_universe" / "portfolio_universe_summary.csv").exists()

    persisted = json.loads(
        (tmp_path / "pipeline" / "selector_rewrite_pipeline_manifest.json").read_text(encoding="utf-8")
    )
    assert persisted["portfolio_universe"]["status"] == "completed"
    report = (tmp_path / "pipeline" / "SELECTOR_REWRITE_PIPELINE_REPORT.md").read_text(encoding="utf-8")
    assert "research artifact only" in report


def test_selector_rewrite_pipeline_can_stop_after_rewrite_without_configs(tmp_path) -> None:
    manifest = run_selector_rewrite_pipeline(
        selector_path=_selector_artifact(tmp_path),
        out_dir=tmp_path / "pipeline",
        candidates_per_target=1,
        run_portfolio_universe=False,
    )

    assert manifest["rewrite"]["candidate_count"] == 1
    assert manifest["universe"]["status"] == "skipped"
    assert manifest["universe"]["reason"] == "no asset config paths provided"
    assert manifest["portfolio_universe"]["status"] == "skipped"
