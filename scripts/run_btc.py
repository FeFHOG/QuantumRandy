from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--iterations", type=int, default=30)
    ap.add_argument("--use-llm", action="store_true")
    ap.add_argument("--out", default="reports/btc_mcts")
    ap.add_argument("--save-every", type=int, default=1)
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    cmd = [
        sys.executable,
        str(root / "scripts" / "mine.py"),
        "--config",
        str(root / "configs" / "btcusdt.yaml"),
        "--iterations",
        str(args.iterations),
        "--out",
        args.out,
        "--save-every",
        str(args.save_every),
    ]
    if args.use_llm:
        cmd.append("--use-llm")
    subprocess.run(cmd, cwd=root, check=True)
    print(f"BTC run finished. Open {Path(args.out) / 'RUN_REPORT.md'}")


if __name__ == "__main__":
    main()
