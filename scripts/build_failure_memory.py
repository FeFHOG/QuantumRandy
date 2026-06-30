from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantumrandy.failure_memory import write_failure_memory


def main() -> None:
    parser = argparse.ArgumentParser(description="Build research-only failure memory from QuantumRandy factor rows.")
    parser.add_argument("--leaderboard", help="Path to leaderboard.json")
    parser.add_argument("--backtest", help="Path to all_factors_backtest.json")
    parser.add_argument("--out", default="reports/failure_memory", help="Output directory")
    args = parser.parse_args()

    rows = []
    for path in [args.leaderboard, args.backtest]:
        if not path:
            continue
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise SystemExit(f"Expected a JSON list: {path}")
        rows.extend(item for item in payload if isinstance(item, dict) and item.get("formula"))

    if not rows:
        raise SystemExit("Provide --leaderboard and/or --backtest with at least one factor row.")

    manifest = write_failure_memory(rows, args.out)
    print(f"Failure rows: {manifest['failure_count']} / input rows: {manifest['input_rows']}")
    print(f"Clusters: {manifest['cluster_count']}")
    print(f"Output: {Path(args.out).resolve()}")


if __name__ == "__main__":
    main()
