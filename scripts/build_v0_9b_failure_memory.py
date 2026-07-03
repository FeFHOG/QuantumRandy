from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantumrandy.v09b_failure_memory import write_v0_9b_failure_memory


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Research v0.9b funding-pressure failure memory.")
    parser.add_argument("--review-csv", required=True)
    parser.add_argument("--source-review-dir", required=True)
    parser.add_argument("--out", default="reports/failure_memory/research_v0_9b_funding_pressure")
    args = parser.parse_args()
    manifest = write_v0_9b_failure_memory(
        args.review_csv,
        args.out,
        source_review_dir=args.source_review_dir,
    )
    print(f"Failure rows: {manifest['failure_count']} / input rows: {manifest['input_rows']}")
    print(f"Output: {Path(args.out).resolve()}")


if __name__ == "__main__":
    main()
