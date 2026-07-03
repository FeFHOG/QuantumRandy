from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantumrandy.v11_independent_replication_export import export_v1_1_independent_scoped_candidates


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Research v1.1 independent scoped family replication candidates.")
    parser.add_argument(
        "--out",
        default="reports/factor_candidate_exports/research_v1_1_independent_scoped_family_replication",
        help="Output directory for JSONL, bundle JSONL, CSV, manifest, and Markdown report.",
    )
    args = parser.parse_args()
    manifest = export_v1_1_independent_scoped_candidates(args.out)
    print(
        "v1.1 independent scoped family replication export: "
        f"candidates={manifest['candidate_count']} "
        f"single_factors={manifest['single_factor_count']} "
        f"bundles={manifest['bundle_count']} "
        f"jsonl={Path(manifest['outputs']['jsonl']).resolve()}"
    )


if __name__ == "__main__":
    main()
