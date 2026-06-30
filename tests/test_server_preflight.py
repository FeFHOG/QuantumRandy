from __future__ import annotations

import json
from pathlib import Path

import yaml

from quantumrandy.server_preflight import render_preflight_report, run_server_preflight


def _write_configs(tmp_path: Path, *, host: str = "127.0.0.1") -> tuple[Path, Path, Path]:
    runtime_manifest = tmp_path / "runtime_factors.json"
    runtime_manifest.write_text(
        json.dumps(
            {
                "generation": 1,
                "factors": [{"factor_id": "carry", "formula": "neg(zscore(funding_rate,4))"}],
                "strategies": [
                    {
                        "strategy_id": "carry_single",
                        "components": [{"factor_id": "carry", "weight": 1.0}],
                        "initial_capital_usd": 1000.0,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    baseline_summary = tmp_path / "baseline_summary.json"
    baseline_summary.write_text(
        json.dumps({"artifact_type": "randyslab_baseline_export", "strategies": []}),
        encoding="utf-8",
    )
    runtime_config = tmp_path / "runtime_server.yaml"
    runtime_config.write_text(
        yaml.safe_dump(
            {
                "server": {
                    "host": host,
                    "port": 8787,
                    "admin_token_env": "QUANTUMRANDY_ADMIN_TOKEN",
                    "ingest_token_env": "QUANTUMRANDY_INGEST_TOKEN",
                },
                "factors_file": runtime_manifest.name,
                "bar_hours": 4,
                "max_bars": 5000,
            }
        ),
        encoding="utf-8",
    )
    feeder_config = tmp_path / "binance_feeder.yaml"
    feeder_config.write_text(
        yaml.safe_dump(
            {
                "runtime": {
                    "url": "http://127.0.0.1:8787",
                    "ingest_token_env": "QUANTUMRANDY_INGEST_TOKEN",
                },
                "binance": {
                    "base_url": "https://fapi.binance.com",
                    "symbol": "BTCUSDT",
                    "interval": "4h",
                    "include_unclosed": False,
                },
            }
        ),
        encoding="utf-8",
    )
    monitor_config = tmp_path / "runtime_monitor.yaml"
    monitor_config.write_text(
        yaml.safe_dump(
            {
                "runtime": {"url": "http://127.0.0.1:8787"},
                "baseline": {"summary_path": str(baseline_summary)},
            }
        ),
        encoding="utf-8",
    )
    return runtime_config, feeder_config, monitor_config


def test_server_preflight_passes_safe_local_configs(tmp_path) -> None:
    runtime_config, feeder_config, monitor_config = _write_configs(tmp_path)

    checks = run_server_preflight(
        runtime_config_path=runtime_config,
        feeder_config_path=feeder_config,
        monitor_config_path=monitor_config,
    )
    report = render_preflight_report(checks)

    assert all(item.ok for item in checks)
    assert "Overall status: `PASS`" in report
    assert "runtime_bind_private" in report
    assert "read-only" in report


def test_server_preflight_rejects_public_runtime_bind(tmp_path) -> None:
    runtime_config, feeder_config, monitor_config = _write_configs(tmp_path, host="0.0.0.0")

    checks = run_server_preflight(
        runtime_config_path=runtime_config,
        feeder_config_path=feeder_config,
        monitor_config_path=monitor_config,
    )

    by_name = {item.name: item for item in checks}
    assert by_name["runtime_bind_private"].ok is False
    assert not all(item.ok for item in checks)
