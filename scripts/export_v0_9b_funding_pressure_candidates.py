from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantumrandy.factor_candidate_export import export_v0_9b_funding_pressure_candidates


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export Research v0.9b BTCUSDT scoped funding-pressure factor candidates."
    )
    parser.add_argument(
        "--out",
        default="reports/factor_candidate_exports/research_v0_9b_funding_pressure",
        help="Output directory for JSONL, CSV, manifest, and Markdown report.",
    )
    args = parser.parse_args()
    manifest = export_v0_9b_funding_pressure_candidates(args.out)
    print(
        "Funding-pressure candidate export: "
        f"candidates={manifest['candidate_count']} "
        f"jsonl={Path(manifest['outputs']['jsonl']).resolve()} "
        f"csv={Path(manifest['outputs']['csv']).resolve()}"
    )


if __name__ == "__main__":
    main()
