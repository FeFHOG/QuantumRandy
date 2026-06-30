from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantumrandy.admission import AdmissionPolicy, load_json_rows, load_optional_csv, write_admission_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Build research-only QuantumRandy factor admission decisions.")
    parser.add_argument("--leaderboard", required=True, help="Path to leaderboard.json")
    parser.add_argument("--walk-forward-summary", help="Path to walk_forward_summary.csv")
    parser.add_argument("--universe-summary", help="Path to universe_summary.csv")
    parser.add_argument("--portfolio-selection", help="Path to portfolio_selection.csv")
    parser.add_argument("--portfolio-walk-forward-summary", help="Path to portfolio_walk_forward_summary.csv")
    parser.add_argument("--out", default="reports/admission", help="Output directory")
    parser.add_argument("--min-brutal-score", type=float, default=0.0)
    parser.add_argument("--max-turnover", type=float, default=0.60)
    parser.add_argument("--max-drawdown", type=float, default=0.50)
    parser.add_argument("--min-validation-sharpe", type=float, default=0.0)
    parser.add_argument("--min-validation-rank-ic", type=float, default=0.0)
    parser.add_argument("--min-walk-forward-survival-rate", type=float, default=0.50)
    parser.add_argument("--min-universe-pass-rate", type=float, default=0.50)
    parser.add_argument("--require-portfolio-selected", action="store_true")
    parser.add_argument("--min-portfolio-walk-forward-survival-rate", type=float, default=0.50)
    args = parser.parse_args()

    policy = AdmissionPolicy(
        min_brutal_score=args.min_brutal_score,
        max_turnover=args.max_turnover,
        max_drawdown=args.max_drawdown,
        min_validation_sharpe=args.min_validation_sharpe,
        min_validation_rank_ic=args.min_validation_rank_ic,
        min_walk_forward_survival_rate=args.min_walk_forward_survival_rate,
        min_universe_pass_rate=args.min_universe_pass_rate,
        require_portfolio_selected=args.require_portfolio_selected,
        min_portfolio_walk_forward_survival_rate=args.min_portfolio_walk_forward_survival_rate,
    )
    manifest = write_admission_report(
        load_json_rows(args.leaderboard),
        args.out,
        walk_forward_summary=load_optional_csv(args.walk_forward_summary),
        universe_summary=load_optional_csv(args.universe_summary),
        portfolio_selection=load_optional_csv(args.portfolio_selection),
        portfolio_walk_forward_summary=load_optional_csv(args.portfolio_walk_forward_summary),
        policy=policy,
    )
    print(
        f"Admission: approved={manifest['approved_count']} "
        f"review={manifest['review_count']} rejected={manifest['rejected_count']} "
        f"out={Path(args.out).resolve()}"
    )


if __name__ == "__main__":
    main()
