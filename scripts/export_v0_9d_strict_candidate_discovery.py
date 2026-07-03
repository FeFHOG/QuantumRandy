from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantumrandy.v09d_discovery_export import export_v0_9d_strict_candidate_discovery


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Research v0.9d strict candidate-family discovery candidates.")
    parser.add_argument(
        "--out",
        default="reports/factor_candidate_exports/research_v0_9d_strict_candidate_discovery",
        help="Output directory for JSONL, bundle JSONL, CSV, manifest, and Markdown report.",
    )
    args = parser.parse_args()
    manifest = export_v0_9d_strict_candidate_discovery(args.out)
    print(
        "v0.9d strict candidate discovery export: "
        f"candidates={manifest['candidate_count']} "
        f"single_factors={manifest['single_factor_count']} "
        f"bundles={manifest['bundle_count']} "
        f"jsonl={Path(manifest['outputs']['jsonl']).resolve()}"
    )


if __name__ == "__main__":
    main()
