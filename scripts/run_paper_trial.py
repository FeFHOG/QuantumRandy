from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import sys
import threading
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantumrandy.config import CostConfig, ExecutionConfig, load_config
from quantumrandy.data import load_market_frame
from quantumrandy.factor_publisher import (
    build_update_payload,
    current_generation_from_manifest,
    load_json,
    select_portfolio_runtime_config,
    submit_runtime_config,
    write_publish_artifacts,
)
from quantumrandy.market_feeder import post_bars
from quantumrandy.runtime import FactorRuntime
from quantumrandy.runtime_monitor import RuntimeMonitorConfig, run_monitor
from quantumrandy.runtime_server import FactorHTTPServer


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local end-to-end QuantumRandy paper trial smoke.")
    parser.add_argument("--config", default="configs/btcusdt.yaml", help="Research config used for local market data.")
    parser.add_argument("--runtime-config", default="configs/runtime_server.yaml")
    parser.add_argument("--portfolio-manifest", required=True)
    parser.add_argument("--portfolio-factors", required=True)
    parser.add_argument("--portfolio-id", default="equal_weight_accepted")
    parser.add_argument("--out", default="reports/paper_trial")
    parser.add_argument("--bars", type=int, default=240, help="Number of latest local bars to push to runtime.")
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    runtime_url, server, thread, trial_manifest = _start_trial_runtime(args, out)
    try:
        proposal_path = out / "runtime_portfolio_proposal.json"
        payload = _build_and_submit_portfolio_payload(args, runtime_url, trial_manifest, proposal_path)
        posted = _post_local_bars(args, runtime_url)
        monitor_dir = out / "runtime_live"
        run_monitor(RuntimeMonitorConfig(runtime_url=runtime_url, out_dir=monitor_dir), once=True)
        summary = {
            "runtime_url": runtime_url,
            "trial_manifest": str(trial_manifest),
            "proposal_path": str(proposal_path),
            "expected_generation": payload["expected_generation"],
            "submitted_strategy_count": len(payload["strategies"]),
            "submitted_factor_count": len(payload["factors"]),
            "posted_bars": posted.get("accepted"),
            "stored_bars": posted.get("stored_bars"),
            "latest_timestamp": posted.get("latest_timestamp"),
            "monitor_dir": str(monitor_dir),
        }
        (out / "paper_trial_summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(summary, indent=2))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _start_trial_runtime(args: argparse.Namespace, out: Path):
    runtime_config_path = Path(args.runtime_config).resolve()
    raw = yaml.safe_load(runtime_config_path.read_text(encoding="utf-8")) or {}
    source_manifest = Path(raw.get("factors_file", "runtime_factors.json"))
    if not source_manifest.is_absolute():
        source_manifest = (runtime_config_path.parent / source_manifest).resolve()
    trial_manifest = out / "trial_runtime_factors.json"
    shutil.copyfile(source_manifest, trial_manifest)

    runtime = FactorRuntime(
        trial_manifest,
        costs=CostConfig(**(raw.get("costs") or {})),
        execution=ExecutionConfig(**(raw.get("execution") or {})),
        bar_hours=int(raw.get("bar_hours", 4)),
        max_bars=int(raw.get("max_bars", 5_000)),
    )
    runtime.load()
    admin_token = f"trial-admin-{secrets.token_urlsafe(16)}"
    ingest_token = f"trial-ingest-{secrets.token_urlsafe(16)}"
    os.environ["QUANTUMRANDY_ADMIN_TOKEN"] = admin_token
    os.environ["QUANTUMRANDY_INGEST_TOKEN"] = ingest_token
    server = FactorHTTPServer(("127.0.0.1", 0), runtime, admin_token=admin_token, ingest_token=ingest_token)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    return f"http://{host}:{port}", server, thread, trial_manifest


def _build_and_submit_portfolio_payload(
    args: argparse.Namespace,
    runtime_url: str,
    trial_manifest: Path,
    proposal_path: Path,
) -> dict:
    manifest = load_json(args.portfolio_manifest)
    factor_rows = _load_records(args.portfolio_factors)
    selection = select_portfolio_runtime_config(
        manifest,
        factor_rows,
        portfolio_id=args.portfolio_id,
    )
    payload = build_update_payload(
        expected_generation=current_generation_from_manifest(trial_manifest),
        factors=selection.factors,
        strategies=selection.strategies,
    )
    write_publish_artifacts(proposal_path, payload, selection.selected_rows)
    submit_runtime_config(runtime_url, os.environ["QUANTUMRANDY_ADMIN_TOKEN"], payload)
    return payload


def _post_local_bars(args: argparse.Namespace, runtime_url: str) -> dict:
    cfg = load_config(args.config)
    data = load_market_frame(cfg.ohlcv_csv, cfg.funding_csv).tail(args.bars)
    bars = [
        {
            "timestamp": timestamp.isoformat(),
            "open": float(row.open),
            "high": float(row.high),
            "low": float(row.low),
            "close": float(row.close),
            "volume": float(row.volume),
            "funding_rate": float(row.funding_rate),
        }
        for timestamp, row in data.iterrows()
    ]
    return post_bars(runtime_url, os.environ["QUANTUMRANDY_INGEST_TOKEN"], bars, timeout=10.0)


def _load_records(path: str | Path) -> list[dict]:
    import pandas as pd

    path = Path(path)
    if path.suffix.lower() == ".json":
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError("JSON records must be a list")
        return raw
    frame = pd.read_csv(path)
    return frame.to_dict(orient="records")


if __name__ == "__main__":
    main()
