from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantumrandy.market_feeder import config_from_dict, run_feeder


def main() -> None:
    parser = argparse.ArgumentParser(description="Feed Binance USDT perpetual K-lines into QuantumRandy runtime.")
    parser.add_argument("--config", default="configs/binance_feeder.yaml")
    parser.add_argument("--once", action="store_true", help="Fetch and post once, then exit.")
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    run_feeder(config_from_dict(raw), once=args.once)


if __name__ == "__main__":
    main()
