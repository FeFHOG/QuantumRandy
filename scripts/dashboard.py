from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantumrandy.dashboard import run_dashboard


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/btcusdt.yaml")
    ap.add_argument("--out", default="reports/research_live")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    run_dashboard(args.config, args.out, args.host, args.port)


if __name__ == "__main__":
    main()
