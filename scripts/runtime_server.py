from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantumrandy.config import CostConfig, ExecutionConfig
from quantumrandy.runtime import FactorRuntime
from quantumrandy.runtime_server import FactorHTTPServer


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the deterministic QuantumRandy factor execution server.")
    parser.add_argument("--config", default="configs/runtime_server.yaml")
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    server_config = raw.get("server") or {}
    factors_path = Path(raw.get("factors_file", "runtime_factors.json"))
    if not factors_path.is_absolute():
        factors_path = (config_path.parent / factors_path).resolve()

    admin_env = str(server_config.get("admin_token_env", "QUANTUMRANDY_ADMIN_TOKEN"))
    ingest_env = str(server_config.get("ingest_token_env", "QUANTUMRANDY_INGEST_TOKEN"))
    admin_token = os.environ.get(admin_env, "")
    ingest_token = os.environ.get(ingest_env, "")
    if not admin_token or not ingest_token:
        raise SystemExit(f"Set non-empty {admin_env} and {ingest_env} environment variables before startup")

    runtime = FactorRuntime(
        factors_path,
        costs=CostConfig(**(raw.get("costs") or {})),
        execution=ExecutionConfig(**(raw.get("execution") or {})),
        bar_hours=int(raw.get("bar_hours", 4)),
        max_bars=int(raw.get("max_bars", 5_000)),
    )
    runtime.load()
    address = (str(server_config.get("host", "127.0.0.1")), int(server_config.get("port", 8787)))
    httpd = FactorHTTPServer(address, runtime, admin_token=admin_token, ingest_token=ingest_token)
    print(f"QuantumRandy runtime server listening on http://{address[0]}:{address[1]}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
