from __future__ import annotations

from pathlib import Path

import pandas as pd

from quantumrandy.data_readiness import (
    ReadinessPolicy,
    build_config_targets,
    data_fetch_plan,
    data_fetch_runbook,
    readiness_manifest,
    readiness_report,
    run_data_readiness,
    scaffold_asset_configs,
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
    assert row["research_bars"] == 216
    assert row["research_expected_bars"] == 216
    assert row["research_coverage_ratio"] == 1.0
    assert row["training_expected_bars"] == 114
    assert row["validation_expected_bars"] == 102
    assert row["training_missing_bars"] == 0
    assert bool(row["training_window_covered"]) is True
    assert bool(row["validation_window_covered"]) is True
    assert row["funding_alignment_coverage"] == 1.0
    assert row["funding_expected_observations"] == 108
    assert row["funding_observations_in_window"] == 108
    assert row["funding_raw_coverage"] == 1.0
    assert row["funding_max_staleness_hours"] == 4.0
    assert row["ohlcv_file_size_bytes"] > 0
    assert len(row["ohlcv_sha256_16"]) == 16


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


def test_readiness_interval_check_uses_configured_research_window(tmp_path: Path) -> None:
    config = _write_asset_config(tmp_path, "SOLUSDT", periods=260, missing_bar=True)
    text = config.read_text(encoding="utf-8")
    text = text.replace('training_start: "2024-01-01"', 'training_start: "2024-01-10"')
    config.write_text(text, encoding="utf-8")

    frame = run_data_readiness(
        [{"expected_symbol": "SOLUSDT", "config_path": str(config)}],
        policy=ReadinessPolicy(min_total_bars=100, min_window_bars=20),
    )

    assert bool(frame.iloc[0]["ready"]) is True


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


def test_scaffold_asset_configs_uses_reference_template(tmp_path: Path) -> None:
    reference = _write_asset_config(tmp_path, "BTCUSDT")
    out_dir = tmp_path / "configs"

    rows = scaffold_asset_configs(
        ["ETHUSDT"],
        config_dir=out_dir,
        reference_config=reference,
        data_root=Path("../data"),
    )

    written = out_dir / "ethusdt.yaml"
    text = written.read_text(encoding="utf-8")
    assert rows == [
        {
            "symbol": "ETHUSDT",
            "config_path": str(written),
            "existed": False,
            "written": True,
            "overwrite": False,
        }
    ]
    assert "symbol: ETHUSDT" in text
    assert "ohlcv_csv: ../data/ETHUSDT_4h.csv" in text
    assert "funding_csv: ../data/ETHUSDT_funding.csv" in text
    assert "training_start: '2024-01-01'" in text


def test_scaffold_asset_configs_skips_existing_config(tmp_path: Path) -> None:
    reference = _write_asset_config(tmp_path, "BTCUSDT")
    out_dir = tmp_path / "configs"

    first = scaffold_asset_configs(["ETHUSDT"], config_dir=out_dir, reference_config=reference)
    second = scaffold_asset_configs(["ETHUSDT"], config_dir=out_dir, reference_config=reference)

    assert first[0]["written"] is True
    assert second[0]["existed"] is True
    assert second[0]["written"] is False


def test_data_fetch_plan_lists_missing_asset_csv_commands(tmp_path: Path) -> None:
    reference = _write_asset_config(tmp_path, "BTCUSDT")
    out_dir = tmp_path / "configs"
    scaffold_asset_configs(["AVAXUSDT"], config_dir=out_dir, reference_config=reference)
    frame = run_data_readiness(
        [{"expected_symbol": "AVAXUSDT", "config_path": str(out_dir / "avaxusdt.yaml")}],
        policy=ReadinessPolicy(min_total_bars=100, min_window_bars=20),
    )

    plan = data_fetch_plan(frame, randyslab_dir="../RandysLab-STRICT4H")
    runbook = data_fetch_runbook(plan)

    assert len(plan) == 1
    assert plan[0]["symbol"] == "AVAXUSDT"
    assert plan[0]["market_symbol"] == "AVAX/USDT:USDT"
    assert plan[0]["incomplete_window"] is True
    assert "--file-prefix AVAXUSDT" in plan[0]["command"]
    assert "--start 2024-01-01 --end 2024-02-06" in plan[0]["command"]
    assert "--method archive" in plan[0]["command"]
    assert "does not download data" in runbook
    assert "python scripts/fetch_binance.py" in runbook


def test_data_fetch_plan_includes_existing_files_with_incomplete_windows(tmp_path: Path) -> None:
    config = _write_asset_config(tmp_path, "BTCUSDT", periods=60)
    frame = run_data_readiness(
        [{"expected_symbol": "BTCUSDT", "config_path": str(config)}],
        policy=ReadinessPolicy(min_total_bars=10, min_window_bars=20),
    )

    plan = data_fetch_plan(frame)

    assert len(plan) == 1
    assert plan[0]["missing_ohlcv"] is False
    assert plan[0]["missing_funding"] is False
    assert plan[0]["incomplete_window"] is True
