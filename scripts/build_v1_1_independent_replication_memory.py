from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantumrandy.v11_independent_replication_memory import write_v1_1_independent_replication_failure_memory


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Research v1.1 independent replication failure memory.")
    parser.add_argument("--ranking-csv", required=True)
    parser.add_argument("--source-robustness-dir", required=True)
    parser.add_argument("--out", default="reports/failure_memory/research_v1_1_independent_replication")
    args = parser.parse_args()
    manifest = write_v1_1_independent_replication_failure_memory(
        args.ranking_csv,
        args.out,
        source_robustness_dir=args.source_robustness_dir,
    )
    print(f"Failure rows: {manifest['failure_count']} / input rows: {manifest['input_rows']}")
    print(f"Output: {Path(args.out).resolve()}")


if __name__ == "__main__":
    main()
