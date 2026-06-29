from __future__ import annotations

import http.client
import json
import threading

import pytest

from quantumrandy.runtime import FactorRuntime, RuntimeConflictError
from quantumrandy.runtime_server import FactorHTTPServer


def _factor_file(tmp_path):
    path = tmp_path / "factors.json"
    path.write_text(
        json.dumps(
            {
                "generation": 3,
                "factors": [
                    {
                        "factor_id": "momentum",
                        "formula": "zscore(ret(close,2),4)",
                        "description": "Short-horizon normalized momentum.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def _bars(count: int = 20) -> list[dict]:
    rows = []
    for index in range(count):
        close = 100.0 + index + (0.25 if index % 3 == 0 else 0.0)
        rows.append(
            {
                "timestamp": f"2024-01-{1 + index // 6:02d}T{(index % 6) * 4:02d}:00:00Z",
                "open": close - 0.2,
                "high": close + 1.0,
                "low": close - 1.0,
                "close": close,
                "volume": 1_000.0 + index,
                "funding_rate": 0.0001,
            }
        )
    return rows


def test_runtime_ingests_bars_and_produces_deterministic_snapshot(tmp_path) -> None:
    runtime = FactorRuntime(_factor_file(tmp_path), max_bars=100)
    runtime.load()
    result = runtime.ingest(_bars())
    snapshot = runtime.snapshot()

    assert result["stored_bars"] == 20
    assert snapshot["generation"] == 3
    assert snapshot["stored_bars"] == 20
    assert len(snapshot["factors"]) == 1
    factor = snapshot["factors"][0]
    assert factor["factor_id"] == "momentum"
    assert factor["factor_value"] is not None
    assert factor["target_signal"] in {-1.0, 0.0, 1.0}
    assert factor["executed_exposure"] in {-1.0, 0.0, 1.0}
    assert factor["metrics"]["predictive_observations"] > 0


def test_hot_update_is_atomic_and_generation_guarded(tmp_path) -> None:
    path = _factor_file(tmp_path)
    runtime = FactorRuntime(path, max_bars=100)
    runtime.load()
    original = path.read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="expects 2 arguments"):
        runtime.replace_factors(
            [{"factor_id": "broken", "formula": "sma(close)"}],
            expected_generation=3,
        )
    assert runtime.generation == 3
    assert path.read_text(encoding="utf-8") == original

    manifest = runtime.replace_factors(
        [{"factor_id": "carry", "formula": "neg(zscore(funding_rate,4))"}],
        expected_generation=3,
    )
    assert manifest["generation"] == 4
    assert json.loads(path.read_text(encoding="utf-8"))["generation"] == 4

    with pytest.raises(RuntimeConflictError, match="current 4"):
        runtime.replace_factors(
            [{"factor_id": "other", "formula": "zscore(close,4)"}],
            expected_generation=3,
        )
    assert runtime.factor_manifest() == manifest


def test_single_and_multi_factor_strategies_enforce_small_capital_limit(tmp_path) -> None:
    path = tmp_path / "strategies.json"
    factors = [
        {"factor_id": "momentum", "formula": "zscore(ret(close,2),4)"},
        {"factor_id": "carry", "formula": "neg(zscore(funding_rate,4))"},
    ]
    strategies = [
        {
            "strategy_id": "single",
            "components": [{"factor_id": "momentum", "weight": 1.0}],
            "initial_capital_usd": 500.0,
        },
        {
            "strategy_id": "blend",
            "components": [
                {"factor_id": "momentum", "weight": 0.6},
                {"factor_id": "carry", "weight": 0.4},
            ],
            "initial_capital_usd": 1000.0,
            "execution_model": {
                "latency_bars": 2,
                "slippage_jitter_bps": 4.0,
                "adverse_slippage_bps": 6.0,
                "signal_noise_std": 0.1,
                "fill_probability": 0.8,
                "seed": 17,
            },
        },
    ]
    path.write_text(json.dumps({"generation": 1, "factors": factors, "strategies": strategies}), encoding="utf-8")
    runtime = FactorRuntime(path, max_bars=100)
    runtime.load()
    runtime.ingest(_bars())

    snapshots = {item["strategy_id"]: item for item in runtime.snapshot()["strategies"]}
    assert snapshots["single"]["mode"] == "single_factor"
    assert snapshots["single"]["initial_capital_usd"] == 500.0
    assert snapshots["blend"]["mode"] == "multi_factor"
    assert snapshots["blend"]["initial_capital_usd"] == 1000.0
    assert snapshots["blend"]["execution_model"]["latency_bars"] == 2
    assert snapshots["blend"]["execution_cost_usd"] >= 0.0

    invalid = strategies + [
        {
            "strategy_id": "too_large",
            "components": [{"factor_id": "momentum"}],
            "initial_capital_usd": 1000.01,
        }
    ]
    with pytest.raises(ValueError, match=r"initial_capital_usd must be in \(0, 1000\]"):
        runtime.replace_config(factors, invalid, expected_generation=1)
    assert runtime.generation == 1


def test_http_server_requires_ingest_token(tmp_path) -> None:
    runtime = FactorRuntime(_factor_file(tmp_path), max_bars=100)
    runtime.load()
    server = FactorHTTPServer(("127.0.0.1", 0), runtime, admin_token="admin-secret", ingest_token="ingest-secret")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    connection = http.client.HTTPConnection(host, port, timeout=5)
    body = json.dumps(_bars(1))
    try:
        connection.request("POST", "/v1/market/bars", body=body, headers={"Content-Type": "application/json"})
        unauthorized = connection.getresponse()
        assert unauthorized.status == 401
        unauthorized.read()

        connection.request(
            "POST",
            "/v1/market/bars",
            body=body,
            headers={"Content-Type": "application/json", "X-Ingest-Token": "ingest-secret"},
        )
        accepted = connection.getresponse()
        assert accepted.status == 200
        payload = json.loads(accepted.read())
        assert payload["stored_bars"] == 1

        connection.request("GET", "/health")
        health = connection.getresponse()
        assert health.status == 200
        assert json.loads(health.read())["status"] == "ok"

        update = json.dumps(
            {
                "expected_generation": 3,
                "factors": [{"factor_id": "carry", "formula": "neg(zscore(funding_rate,4))"}],
                "strategies": [
                    {
                        "strategy_id": "carry_single",
                        "components": [{"factor_id": "carry", "weight": 1.0}],
                        "initial_capital_usd": 1000.0,
                    }
                ],
            }
        )
        connection.request(
            "PUT",
            "/v1/admin/config",
            body=update,
            headers={"Content-Type": "application/json", "X-Admin-Token": "admin-secret"},
        )
        updated = connection.getresponse()
        assert updated.status == 200
        assert json.loads(updated.read())["generation"] == 4

        connection.request(
            "PUT",
            "/v1/admin/config",
            body=update,
            headers={"Content-Type": "application/json", "X-Admin-Token": "admin-secret"},
        )
        stale = connection.getresponse()
        assert stale.status == 409
        assert json.loads(stale.read())["error"] == "generation_conflict"
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
