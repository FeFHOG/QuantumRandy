from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantumrandy.v12_failure_guided_respec_export import export_v1_2_failure_guided_scoped_respec


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Research v1.2 failure-guided scoped re-spec candidates.")
    parser.add_argument(
        "--out",
        default="reports/factor_candidate_exports/research_v1_2_failure_guided_scoped_respec",
        help="Output directory for JSONL, bundle JSONL, CSV, manifest, events, and Markdown report.",
    )
    args = parser.parse_args()
    manifest = export_v1_2_failure_guided_scoped_respec(args.out)
    print(
        "v1.2 failure-guided scoped re-spec export: "
        f"candidates={manifest['candidate_count']} "
        f"single_factors={manifest['single_factor_count']} "
        f"bundles={manifest['bundle_count']} "
        f"jsonl={Path(manifest['outputs']['jsonl']).resolve()}"
    )


if __name__ == "__main__":
    main()
