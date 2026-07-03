from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantumrandy.v09d_failure_memory import write_v0_9d_failure_memory


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Research v0.9d strict candidate discovery failure memory.")
    parser.add_argument("--review-csv", required=True)
    parser.add_argument("--source-review-dir", required=True)
    parser.add_argument("--diagnostic-review-csv", default="")
    parser.add_argument("--source-diagnostic-dir", default="")
    parser.add_argument("--correlation-csv", default="")
    parser.add_argument("--source-correlation-dir", default="")
    parser.add_argument("--out", default="reports/failure_memory/research_v0_9d_strict_candidate_discovery")
    args = parser.parse_args()
    manifest = write_v0_9d_failure_memory(
        args.review_csv,
        args.out,
        source_review_dir=args.source_review_dir,
        diagnostic_review_csv=args.diagnostic_review_csv or None,
        source_diagnostic_dir=args.source_diagnostic_dir,
        correlation_csv=args.correlation_csv or None,
        source_correlation_dir=args.source_correlation_dir,
    )
    print(f"Failure rows: {manifest['failure_count']} / input rows: {manifest['input_rows']}")
    print(f"Output: {Path(args.out).resolve()}")


if __name__ == "__main__":
    main()
