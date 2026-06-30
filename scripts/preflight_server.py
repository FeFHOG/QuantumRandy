from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantumrandy.server_preflight import render_preflight_report, run_server_preflight


def main() -> None:
    parser = argparse.ArgumentParser(description="Run read-only preflight checks for the server paper stack.")
    parser.add_argument("--runtime-config", default="configs/runtime_server.yaml")
    parser.add_argument("--feeder-config", default="configs/binance_feeder.yaml")
    parser.add_argument("--monitor-config", default="configs/runtime_monitor.yaml")
    parser.add_argument(
        "--require-tokens",
        action="store_true",
        help="Require configured admin and ingest token environment variables to be present.",
    )
    args = parser.parse_args()

    checks = run_server_preflight(
        runtime_config_path=args.runtime_config,
        feeder_config_path=args.feeder_config,
        monitor_config_path=args.monitor_config,
        require_tokens=args.require_tokens,
    )
    print(render_preflight_report(checks))
    if not all(item.ok for item in checks):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
