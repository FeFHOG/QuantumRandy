from __future__ import annotations

import json

import yaml

from quantumrandy.runtime_dashboard import HTML, build_dashboard_payload


def test_runtime_dashboard_payload_reads_monitor_outputs_and_baseline(tmp_path) -> None:
    out_dir = tmp_path / "runtime_live"
    out_dir.mkdir()
    latest = {
        "observed_at": "2026-06-30T00:00:00+00:00",
        "stale_bar": False,
        "health": {"status": "ok", "generation": 1, "stored_bars": 10},
        "snapshot": {
            "strategies": [{"strategy_id": "blend", "equity_usd": 1001.0}],
            "factors": [{"factor_id": "carry", "factor_value": 0.2}],
        },
    }
    (out_dir / "latest_snapshot.json").write_text(json.dumps(latest), encoding="utf-8")
    (out_dir / "snapshots.jsonl").write_text(json.dumps(latest) + "\n", encoding="utf-8")
    baseline = tmp_path / "baseline_summary.json"
    baseline.write_text(
        json.dumps(
            {
                "artifact_type": "randyslab_baseline_export",
                "symbol": "BTC/USDT:USDT",
                "window": {"name": "all"},
                "strategies": [{"strategy_id": "bb_breakout", "metrics": {"sharpe": 1.2}}],
            }
        ),
        encoding="utf-8",
    )
    monitor_config = tmp_path / "runtime_monitor.yaml"
    monitor_config.write_text(
        yaml.safe_dump(
            {
                "runtime": {"url": "http://127.0.0.1:8787"},
                "output": {"out_dir": str(out_dir)},
                "baseline": {"summary_path": str(baseline)},
            }
        ),
        encoding="utf-8",
    )

    payload = build_dashboard_payload(monitor_config)

    assert payload["latest"]["health"]["status"] == "ok"
    assert payload["history"][0]["snapshot"]["strategies"][0]["strategy_id"] == "blend"
    assert payload["baseline"]["artifact_type"] == "randyslab_baseline_export"
    assert payload["baseline"]["strategies"][0]["strategy_id"] == "bb_breakout"


def test_runtime_dashboard_html_is_read_only_surface() -> None:
    assert "QuantumRandy Paper Runtime" in HTML
    assert "/api/runtime" in HTML
    assert "/v1/admin" not in HTML
    assert "X-Admin-Token" not in HTML
