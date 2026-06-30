from __future__ import annotations

from quantumrandy.runtime_monitor import config_from_dict, load_baseline_summary, render_report


def test_monitor_config_defaults_and_paths() -> None:
    cfg = config_from_dict(
        {
            "runtime": {"url": "http://127.0.0.1:8787/"},
            "output": {"out_dir": "reports/x"},
            "baseline": {"summary_path": "../RandysLab-STRICT4H/reports/quantumrandy_baselines/baseline_summary.json"},
        }
    )

    assert cfg.runtime_url == "http://127.0.0.1:8787"
    assert cfg.out_dir.as_posix() == "reports/x"
    assert cfg.stale_after_minutes == 300.0
    assert cfg.baseline_summary_path is not None
    assert cfg.baseline_summary_path.as_posix().endswith("baseline_summary.json")


def test_render_report_includes_strategy_and_factor_rows() -> None:
    report = render_report(
        {
            "observed_at": "2026-06-30T00:00:00+00:00",
            "stale_bar": False,
            "minutes_since_latest_bar": 12.5,
            "health": {
                "status": "ok",
                "generation": 2,
                "stored_bars": 120,
                "latest_timestamp": "2026-06-30T00:00:00+00:00",
            },
            "snapshot": {
                "factors": [
                    {
                        "factor_id": "carry",
                        "factor_value": 0.5,
                        "target_signal": 1.0,
                        "executed_exposure": 0.0,
                        "close": 60000.0,
                        "metrics": {"sharpe": 0.4, "rank_ic": 0.02},
                    }
                ],
                "strategies": [
                    {
                        "strategy_id": "blend",
                        "mode": "multi_factor",
                        "equity_usd": 1005.0,
                        "return_pct": 0.5,
                        "executed_exposure": 0.75,
                        "metrics": {"sharpe": 0.8, "max_dd": 0.03},
                    }
                ],
            },
        }
    )

    assert "QuantumRandy Runtime Paper Report" in report
    assert "blend" in report
    assert "carry" in report


def test_render_report_includes_randyslab_baseline_rows() -> None:
    report = render_report(
        {
            "observed_at": "2026-06-30T00:00:00+00:00",
            "stale_bar": False,
            "minutes_since_latest_bar": 12.5,
            "health": {
                "status": "ok",
                "generation": 2,
                "stored_bars": 120,
                "latest_timestamp": "2026-06-30T00:00:00+00:00",
            },
            "snapshot": {"factors": [], "strategies": []},
        },
        baseline_summary={
            "artifact_type": "randyslab_baseline_export",
            "source_path": "../RandysLab-STRICT4H/reports/quantumrandy_baselines/baseline_summary.json",
            "generated_at": "2026-06-30T12:00:00+00:00",
            "symbol": "BTC/USDT:USDT",
            "window": {"name": "all"},
            "strategies": [
                {
                    "strategy_id": "bb_breakout",
                    "metrics": {
                        "sharpe": 1.4,
                        "cagr": 0.5,
                        "max_dd": 0.08,
                        "trades": 30,
                        "net_total": 0.09,
                    },
                    "final_equity": 1.08,
                }
            ],
        },
    )

    assert "RandysLab Baseline Comparison" in report
    assert "not QuantumRandy runtime publish payloads" in report
    assert "bb_breakout" in report


def test_load_baseline_summary_returns_error_payload_for_missing_file(tmp_path) -> None:
    payload = load_baseline_summary(tmp_path / "missing.json")

    assert payload is not None
    assert payload["artifact_type"] == "randyslab_baseline_export_error"
    assert "missing.json" in payload["source_path"]
