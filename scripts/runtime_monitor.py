from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantumrandy.runtime_monitor import config_from_dict, run_monitor


def main() -> None:
    parser = argparse.ArgumentParser(description="Poll QuantumRandy runtime snapshots and write paper reports.")
    parser.add_argument("--config", default="configs/runtime_monitor.yaml")
    parser.add_argument("--once", action="store_true", help="Poll once, then exit.")
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    run_monitor(config_from_dict(raw), once=args.once)


if __name__ == "__main__":
    main()
