from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import request

import pandas as pd


@dataclass(frozen=True)
class RuntimeMonitorConfig:
    runtime_url: str = "http://127.0.0.1:8787"
    out_dir: Path = Path("reports/runtime_live")
    poll_seconds: float = 300.0
    request_timeout_seconds: float = 10.0
    stale_after_minutes: float = 300.0


def config_from_dict(raw: dict[str, Any]) -> RuntimeMonitorConfig:
    runtime = raw.get("runtime") or {}
    output = raw.get("output") or {}
    polling = raw.get("polling") or {}
    return RuntimeMonitorConfig(
        runtime_url=str(runtime.get("url", "http://127.0.0.1:8787")).rstrip("/"),
        out_dir=Path(output.get("out_dir", "reports/runtime_live")),
        poll_seconds=float(polling.get("poll_seconds", 300.0)),
        request_timeout_seconds=float(polling.get("request_timeout_seconds", 10.0)),
        stale_after_minutes=float(polling.get("stale_after_minutes", 300.0)),
    )


def run_monitor(config: RuntimeMonitorConfig, *, once: bool = False) -> None:
    config.out_dir.mkdir(parents=True, exist_ok=True)
    while True:
        record = collect_runtime_record(config)
        append_jsonl(config.out_dir / "snapshots.jsonl", record)
        write_latest_json(config.out_dir / "latest_snapshot.json", record)
        write_daily_report(config.out_dir, record)
        print(
            f"runtime snapshot stored; status={record['health'].get('status')} "
            f"latest={record['health'].get('latest_timestamp')} stale={record['stale_bar']}",
            flush=True,
        )
        if once:
            return
        time.sleep(config.poll_seconds)


def collect_runtime_record(config: RuntimeMonitorConfig) -> dict[str, Any]:
    observed_at = pd.Timestamp.utcnow()
    health = get_json(config.runtime_url, "/health", timeout=config.request_timeout_seconds)
    snapshot = get_json(config.runtime_url, "/v1/snapshot", timeout=config.request_timeout_seconds)
    latest = health.get("latest_timestamp")
    stale_bar = False
    minutes_since_latest = None
    if latest:
        latest_ts = pd.Timestamp(latest)
        if latest_ts.tzinfo is None:
            latest_ts = latest_ts.tz_localize("UTC")
        minutes_since_latest = (observed_at - latest_ts).total_seconds() / 60.0
        stale_bar = minutes_since_latest > config.stale_after_minutes
    return {
        "observed_at": observed_at.isoformat(),
        "stale_bar": stale_bar,
        "minutes_since_latest_bar": minutes_since_latest,
        "health": health,
        "snapshot": snapshot,
    }


def get_json(runtime_url: str, path: str, *, timeout: float) -> dict[str, Any]:
    with request.urlopen(f"{runtime_url.rstrip('/')}{path}", timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path} returned a non-object JSON payload")
    return payload


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=True, allow_nan=False) + "\n")


def write_latest_json(path: Path, record: dict[str, Any]) -> None:
    path.write_text(json.dumps(record, indent=2, ensure_ascii=True, allow_nan=False) + "\n", encoding="utf-8")


def write_daily_report(out_dir: Path, record: dict[str, Any]) -> Path:
    observed = pd.Timestamp(record["observed_at"])
    report_path = out_dir / f"runtime_report_{observed.strftime('%Y%m%d')}.md"
    report_path.write_text(render_report(record), encoding="utf-8")
    return report_path


def render_report(record: dict[str, Any]) -> str:
    health = record.get("health") or {}
    snapshot = record.get("snapshot") or {}
    factors = snapshot.get("factors") or []
    strategies = snapshot.get("strategies") or []
    lines = [
        "# QuantumRandy Runtime Paper Report",
        "",
        f"- Observed at: `{record.get('observed_at')}`",
        f"- Runtime status: `{health.get('status')}`",
        f"- Generation: `{health.get('generation')}`",
        f"- Stored bars: `{health.get('stored_bars')}`",
        f"- Latest bar: `{health.get('latest_timestamp')}`",
        f"- Minutes since latest bar: `{_fmt(record.get('minutes_since_latest_bar'))}`",
        f"- Stale bar: `{record.get('stale_bar')}`",
        "",
        "## Strategies",
        "",
    ]
    if strategies:
        lines.extend(
            [
                "| Strategy | Mode | Equity USD | Return % | Exposure | Sharpe | Max DD |",
                "|---|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for item in strategies:
            metrics = item.get("metrics") or {}
            lines.append(
                "| "
                f"{item.get('strategy_id')} | "
                f"{item.get('mode')} | "
                f"{_fmt(item.get('equity_usd'))} | "
                f"{_fmt(item.get('return_pct'))} | "
                f"{_fmt(item.get('executed_exposure'))} | "
                f"{_fmt(metrics.get('sharpe'))} | "
                f"{_fmt(metrics.get('max_dd'))} |"
            )
    else:
        lines.append("No active strategy rows.")
    lines.extend(["", "## Factors", ""])
    if factors:
        lines.extend(
            [
                "| Factor | Value | Target | Exposure | Close | Sharpe | Rank IC |",
                "|---|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for item in factors:
            metrics = item.get("metrics") or {}
            lines.append(
                "| "
                f"{item.get('factor_id')} | "
                f"{_fmt(item.get('factor_value'))} | "
                f"{_fmt(item.get('target_signal'))} | "
                f"{_fmt(item.get('executed_exposure'))} | "
                f"{_fmt(item.get('close'))} | "
                f"{_fmt(metrics.get('sharpe'))} | "
                f"{_fmt(metrics.get('rank_ic'))} |"
            )
    else:
        lines.append("No active factor rows.")
    return "\n".join(lines) + "\n"


def _fmt(value: Any) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return str(value)
