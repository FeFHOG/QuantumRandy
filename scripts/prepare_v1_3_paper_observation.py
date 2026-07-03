from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantumrandy.v13_paper_observation import write_v1_3_paper_observation_packet


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare the Research v1.3 paper-observation starter packet.")
    parser.add_argument(
        "--export-manifest",
        default="reports/factor_candidate_exports/research_v1_3_funding_adjacent_scoped_respec/"
        "factor_candidate_export_manifest.json",
    )
    parser.add_argument(
        "--ranking-csv",
        default="../RandysLab-STRICT4H/reports/factor_candidate_robustness/"
        "research_v1_3_funding_adjacent_respec/watchlist_robustness_variant_ranking.csv",
    )
    parser.add_argument(
        "--out",
        default="reports/paper_observation/research_v1_3_funding_adjacent",
    )
    args = parser.parse_args()

    manifest = write_v1_3_paper_observation_packet(
        export_manifest_path=args.export_manifest,
        ranking_csv_path=args.ranking_csv,
        out_dir=args.out,
    )
    print(
        json.dumps(
            {
                "artifact_type": manifest["artifact_type"],
                "status": manifest["status"],
                "observation_id": manifest["observation_id"],
                "candidate_count": len(manifest["candidates"]),
                "out": str(Path(args.out).resolve()),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
