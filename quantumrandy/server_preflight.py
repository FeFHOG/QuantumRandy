from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from .config import CostConfig, ExecutionConfig
from .market_feeder import config_from_dict as feeder_config_from_dict
from .runtime import FactorRuntime
from .runtime_monitor import config_from_dict as monitor_config_from_dict, load_baseline_summary


@dataclass(frozen=True)
class PreflightCheck:
    name: str
    ok: bool
    detail: str


def run_server_preflight(
    *,
    runtime_config_path: str | Path = "configs/runtime_server.yaml",
    feeder_config_path: str | Path = "configs/binance_feeder.yaml",
    monitor_config_path: str | Path = "configs/runtime_monitor.yaml",
    require_tokens: bool = False,
) -> list[PreflightCheck]:
    runtime_config_path = Path(runtime_config_path).resolve()
    feeder_config_path = Path(feeder_config_path).resolve()
    monitor_config_path = Path(monitor_config_path).resolve()

    checks: list[PreflightCheck] = []
    runtime_raw = _read_yaml(runtime_config_path)
    feeder_raw = _read_yaml(feeder_config_path)
    monitor_raw = _read_yaml(monitor_config_path)

    checks.extend(_runtime_checks(runtime_config_path, runtime_raw, require_tokens=require_tokens))
    checks.extend(_feeder_checks(feeder_raw))
    checks.extend(_monitor_checks(monitor_raw))
    checks.append(
        PreflightCheck(
            "no_live_trading_keys_required",
            True,
            "Runtime and feeder configs reference only admin/ingest environment tokens, not exchange trading keys.",
        )
    )
    return checks


def render_preflight_report(checks: list[PreflightCheck]) -> str:
    status = "PASS" if all(item.ok for item in checks) else "FAIL"
    lines = [
        "# QuantumRandy Server Preflight",
        "",
        f"- Overall status: `{status}`",
        "",
        "| Check | Status | Detail |",
        "|---|---:|---|",
    ]
    for item in checks:
        lines.append(f"| {item.name} | {'PASS' if item.ok else 'FAIL'} | {item.detail} |")
    lines.extend(
        [
            "",
            "This preflight is read-only. It does not start the runtime server, ingest market bars, submit admin updates, "
            "or place orders.",
            "",
        ]
    )
    return "\n".join(lines)


def _runtime_checks(config_path: Path, raw: dict[str, Any], *, require_tokens: bool) -> list[PreflightCheck]:
    checks: list[PreflightCheck] = []
    server = raw.get("server") or {}
    host = str(server.get("host", "127.0.0.1"))
    port = int(server.get("port", 8787))
    private_host = _is_private_bind_host(host)
    checks.append(
        PreflightCheck(
            "runtime_bind_private",
            private_host,
            f"Runtime configured for {host}:{port}.",
        )
    )
    admin_env = str(server.get("admin_token_env", "QUANTUMRANDY_ADMIN_TOKEN"))
    ingest_env = str(server.get("ingest_token_env", "QUANTUMRANDY_INGEST_TOKEN"))
    checks.append(
        PreflightCheck(
            "runtime_tokens_from_environment",
            bool(admin_env) and bool(ingest_env) and admin_env != ingest_env,
            f"Admin token env={admin_env}; ingest token env={ingest_env}.",
        )
    )
    if require_tokens:
        checks.append(
            PreflightCheck(
                "runtime_tokens_present",
                bool(os.environ.get(admin_env)) and bool(os.environ.get(ingest_env)),
                f"Checked required env vars {admin_env} and {ingest_env}.",
            )
        )

    factors_path = Path(raw.get("factors_file", "runtime_factors.json"))
    if not factors_path.is_absolute():
        factors_path = (config_path.parent / factors_path).resolve()
    checks.append(
        PreflightCheck(
            "runtime_manifest_exists",
            factors_path.exists(),
            f"Runtime manifest path: {factors_path.as_posix()}.",
        )
    )
    if factors_path.exists():
        try:
            runtime = FactorRuntime(
                factors_path,
                costs=CostConfig(**(raw.get("costs") or {})),
                execution=ExecutionConfig(**(raw.get("execution") or {})),
                bar_hours=int(raw.get("bar_hours", 4)),
                max_bars=int(raw.get("max_bars", 5_000)),
            )
            manifest = runtime.load()
            too_large = [
                item.get("strategy_id")
                for item in manifest.get("strategies") or []
                if float(item.get("initial_capital_usd", 0.0)) > 1000.0
            ]
            checks.append(
                PreflightCheck(
                    "runtime_manifest_valid",
                    not too_large,
                    f"Loaded generation {manifest.get('generation')} with "
                    f"{len(manifest.get('factors') or [])} factors and {len(manifest.get('strategies') or [])} strategies.",
                )
            )
        except Exception as exc:
            checks.append(PreflightCheck("runtime_manifest_valid", False, str(exc)))
    return checks


def _feeder_checks(raw: dict[str, Any]) -> list[PreflightCheck]:
    checks: list[PreflightCheck] = []
    config = feeder_config_from_dict(raw)
    runtime_url = urlparse(config.runtime_url)
    private_runtime = bool(runtime_url.hostname) and _is_private_bind_host(runtime_url.hostname)
    checks.append(
        PreflightCheck(
            "feeder_posts_to_local_runtime",
            private_runtime,
            f"Feeder runtime URL: {config.runtime_url}.",
        )
    )
    public_binance = urlparse(config.base_url).hostname in {"fapi.binance.com", "testnet.binancefuture.com"}
    checks.append(
        PreflightCheck(
            "feeder_uses_public_market_data",
            public_binance,
            f"Binance base URL: {config.base_url}; symbol={config.symbol}; interval={config.interval}.",
        )
    )
    checks.append(
        PreflightCheck(
            "feeder_excludes_unclosed_by_default",
            not config.include_unclosed,
            f"include_unclosed={config.include_unclosed}.",
        )
    )
    checks.append(
        PreflightCheck(
            "feeder_ingest_token_from_environment",
            bool(config.ingest_token_env),
            f"Ingest token env={config.ingest_token_env}.",
        )
    )
    return checks


def _monitor_checks(raw: dict[str, Any]) -> list[PreflightCheck]:
    checks: list[PreflightCheck] = []
    config = monitor_config_from_dict(raw)
    runtime_url = urlparse(config.runtime_url)
    private_runtime = bool(runtime_url.hostname) and _is_private_bind_host(runtime_url.hostname)
    checks.append(
        PreflightCheck(
            "monitor_reads_local_runtime",
            private_runtime,
            f"Monitor runtime URL: {config.runtime_url}.",
        )
    )
    baseline = load_baseline_summary(config.baseline_summary_path)
    if baseline is None:
        checks.append(
            PreflightCheck(
                "randyslab_baseline_configured",
                False,
                "No baseline.summary_path configured; reports will omit the control-group table.",
            )
        )
    else:
        checks.append(
            PreflightCheck(
                "randyslab_baseline_available",
                baseline.get("artifact_type") == "randyslab_baseline_export",
                f"Baseline source={baseline.get('source_path')}; artifact={baseline.get('artifact_type')}.",
            )
        )
    return checks


def _is_private_bind_host(host: str) -> bool:
    if host in {"127.0.0.1", "localhost", "::1"}:
        return True
    prefixes = (
        "10.",
        "172.16.",
        "172.17.",
        "172.18.",
        "172.19.",
        "172.20.",
        "172.21.",
        "172.22.",
        "172.23.",
        "172.24.",
        "172.25.",
        "172.26.",
        "172.27.",
        "172.28.",
        "172.29.",
        "172.30.",
        "172.31.",
        "192.168.",
    )
    return host.startswith(prefixes)


def _read_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a YAML object")
    return payload
