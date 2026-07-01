from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantumrandy.candidate_selector import (
    CandidateSelectorPolicy,
    load_json_rows,
    load_optional_csv,
    write_candidate_selector_report,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build research-only candidate selection evidence from leaderboard and robustness artifacts."
    )
    parser.add_argument("--leaderboard", required=True, help="Path to leaderboard.json")
    parser.add_argument("--universe-summary", help="Path to universe_summary.csv")
    parser.add_argument("--portfolio-universe-summary", help="Path to portfolio_universe_summary.csv")
    parser.add_argument("--failure-memory", help="Path to failure_memory.csv")
    parser.add_argument("--failure-clusters", help="Path to failure_clusters.csv")
    parser.add_argument("--out", default="reports/candidate_selector", help="Output directory")
    parser.add_argument("--min-rewrite-universe-pass-rate", type=float, default=0.40)
    parser.add_argument("--min-keep-universe-pass-rate", type=float, default=0.60)
    parser.add_argument("--min-keep-mean-sharpe", type=float, default=0.0)
    parser.add_argument("--max-cluster-pass-rate", type=float, default=0.20)
    parser.add_argument("--min-cluster-size", type=int, default=2)
    args = parser.parse_args()

    policy = CandidateSelectorPolicy(
        min_rewrite_universe_pass_rate=args.min_rewrite_universe_pass_rate,
        min_keep_universe_pass_rate=args.min_keep_universe_pass_rate,
        min_keep_mean_sharpe=args.min_keep_mean_sharpe,
        max_cluster_pass_rate=args.max_cluster_pass_rate,
        min_cluster_size=args.min_cluster_size,
    )
    manifest = write_candidate_selector_report(
        load_json_rows(args.leaderboard),
        args.out,
        universe_summary=load_optional_csv(args.universe_summary),
        portfolio_universe_summary=load_optional_csv(args.portfolio_universe_summary),
        failure_memory=load_optional_csv(args.failure_memory),
        failure_clusters=load_optional_csv(args.failure_clusters),
        policy=policy,
    )
    print(
        f"Candidate selector: candidates={manifest['candidate_count']} "
        f"rewrite_targets={manifest['rewrite_target_count']} clusters={manifest['cluster_count']} "
        f"out={Path(args.out).resolve()}"
    )


if __name__ == "__main__":
    main()
