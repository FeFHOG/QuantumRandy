from __future__ import annotations

from pathlib import Path

import pandas as pd

from quantumrandy.data_readiness import (
    ReadinessPolicy,
    build_config_targets,
    readiness_manifest,
    readiness_report,
    run_data_readiness,
)


def _write_asset_config(base: Path, symbol: str, *, periods: int = 220, missing_bar: bool = False) -> Path:
    data_dir = base / "data"
    data_dir.mkdir()
    idx = pd.date_range("2024-01-01", periods=periods, freq="4h", tz="UTC")
    if missing_bar:
        idx = idx.delete(10)
    close = pd.Series(range(len(idx)), index=idx, dtype=float).add(100.0)
    pd.DataFrame(
        {
            "timestamp": idx,
            "open": close.values,
            "high": close.add(1.0).values,
            "low": close.sub(1.0).values,
            "close": close.values,
            "volume": 1000.0,
        }
    ).to_csv(data_dir / f"{symbol}_4h.csv", index=False)
    pd.DataFrame({"timestamp": idx[::2], "funding_rate": 0.0001}).to_csv(
        data_dir / f"{symbol}_funding.csv",
        index=False,
    )
    config = base / f"{symbol.lower()}.yaml"
    config.write_text(
        f"""
symbol: {symbol}
bar_hours: 4
ohlcv_csv: {data_dir / f"{symbol}_4h.csv"}
funding_csv: {data_dir / f"{symbol}_funding.csv"}
windows:
  training_start: "2024-01-01"
  training_end: "2024-01-20"
  validation_start: "2024-01-20"
  validation_end: "2024-02-06"
""",
        encoding="utf-8",
    )
    return config


def test_build_config_targets_defaults_to_universe_symbols() -> None:
    targets = build_config_targets(config_dir="configs")

    assert targets[0]["expected_symbol"] == "BTCUSDT"
    assert targets[0]["config_path"] == str(Path("configs") / "btcusdt.yaml")
    assert targets[-1]["expected_symbol"] == "AVAXUSDT"


def test_run_data_readiness_marks_complete_asset_ready(tmp_path: Path) -> None:
    config = _write_asset_config(tmp_path, "ETHUSDT", periods=216)

    frame = run_data_readiness(
        [{"expected_symbol": "ETHUSDT", "config_path": str(config)}],
        policy=ReadinessPolicy(min_total_bars=100, min_window_bars=20),
    )

    row = frame.iloc[0]
    assert bool(row["ready"]) is True
    assert row["status"] == "ready"
    assert row["symbol"] == "ETHUSDT"
    assert row["ohlcv_rows"] == 216
    assert bool(row["training_window_covered"]) is True
    assert bool(row["validation_window_covered"]) is True
    assert row["funding_alignment_coverage"] == 1.0


def test_run_data_readiness_reports_missing_config() -> None:
    frame = run_data_readiness([{"expected_symbol": "SOLUSDT", "config_path": "missing.yaml"}])

    row = frame.iloc[0]
    assert bool(row["ready"]) is False
    assert row["status"] == "missing_config"
    assert row["reasons"] == "config_missing"


def test_run_data_readiness_flags_gap_and_window_shortfall(tmp_path: Path) -> None:
    config = _write_asset_config(tmp_path, "BNBUSDT", periods=60, missing_bar=True)

    frame = run_data_readiness(
        [{"expected_symbol": "BNBUSDT", "config_path": str(config)}],
        policy=ReadinessPolicy(min_total_bars=100, min_window_bars=40),
    )

    reasons = str(frame.iloc[0]["reasons"])
    assert bool(frame.iloc[0]["ready"]) is False
    assert "ohlcv_interval_not_4h_regular" in reasons
    assert "ohlcv_too_few_bars" in reasons
    assert "validation_window_not_covered" in reasons


def test_readiness_manifest_and_report_are_research_only(tmp_path: Path) -> None:
    config = _write_asset_config(tmp_path, "BTCUSDT")
    policy = ReadinessPolicy(min_total_bars=100, min_window_bars=20)
    targets = [{"expected_symbol": "BTCUSDT", "config_path": str(config)}]
    frame = run_data_readiness(targets, policy=policy)

    manifest = readiness_manifest(frame, targets, policy)
    report = readiness_report(frame, policy)

    assert manifest["research_only"] is True
    assert manifest["ready_count"] == 1
    assert "does not download data" in report
    assert "DATA_READINESS_REPORT.md" in report
