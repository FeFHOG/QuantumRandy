from __future__ import annotations

import json
import sys

import pandas as pd

from scripts.run_paper_trial import main


def test_run_paper_trial_smoke_writes_report_without_mutating_source_manifest(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    idx = pd.date_range("2024-01-01", periods=80, freq="4h", tz="UTC")
    close = pd.Series(range(100, 180), index=idx, dtype=float)
    pd.DataFrame(
        {
            "timestamp": idx,
            "open": close - 0.2,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 1000.0,
        }
    ).to_csv(data_dir / "ohlcv.csv", index=False)
    pd.DataFrame({"timestamp": idx[::2], "funding_rate": 0.0001}).to_csv(data_dir / "funding.csv", index=False)

    research_config = tmp_path / "btcusdt.yaml"
    research_config.write_text(
        f"""
symbol: BTCUSDT
bar_hours: 4
ohlcv_csv: {data_dir / "ohlcv.csv"}
funding_csv: {data_dir / "funding.csv"}
costs:
  taker_bps: 0.0
  slippage_bps: 0.0
  funding_multiplier: 0.0
execution:
  delay_bars: 1
  max_exposure_abs: 1.0
  exposure_threshold: 0.0
mcts:
  seed_formulas: []
""".strip(),
        encoding="utf-8",
    )
    source_manifest = tmp_path / "runtime_factors.json"
    source_manifest.write_text(json.dumps({"generation": 2, "factors": [], "strategies": []}), encoding="utf-8")
    original_manifest = source_manifest.read_text(encoding="utf-8")
    runtime_config = tmp_path / "runtime_server.yaml"
    runtime_config.write_text(
        f"""
factors_file: {source_manifest}
bar_hours: 4
max_bars: 500
costs:
  taker_bps: 0.0
  slippage_bps: 0.0
  funding_multiplier: 0.0
execution:
  delay_bars: 1
  max_exposure_abs: 1.0
  exposure_threshold: 0.0
""".strip(),
        encoding="utf-8",
    )
    portfolio_manifest = tmp_path / "portfolio_manifest.json"
    portfolio_manifest.write_text(
        json.dumps(
            {
                "artifact_type": "quantumrandy_portfolio_research",
                "safety": {"requires_manual_review_before_runtime": True},
                "portfolios": [
                    {
                        "portfolio_id": "equal_weight_accepted",
                        "weighting": "equal_weight",
                        "weights": {"carry": 1.0},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    portfolio_factors = tmp_path / "portfolio_factors.csv"
    pd.DataFrame(
        [{"factor_id": "carry", "formula": "neg(zscore(funding_rate,12))", "description": "Funding reversal"}]
    ).to_csv(portfolio_factors, index=False)
    out = tmp_path / "trial"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_paper_trial.py",
            "--config",
            str(research_config),
            "--runtime-config",
            str(runtime_config),
            "--portfolio-manifest",
            str(portfolio_manifest),
            "--portfolio-factors",
            str(portfolio_factors),
            "--out",
            str(out),
            "--bars",
            "60",
        ],
    )

    main()

    summary = json.loads((out / "paper_trial_summary.json").read_text(encoding="utf-8"))
    assert summary["expected_generation"] == 2
    assert summary["submitted_strategy_count"] == 1
    assert summary["posted_bars"] == 60
    assert (out / "runtime_live" / "latest_snapshot.json").exists()
    assert source_manifest.read_text(encoding="utf-8") == original_manifest
