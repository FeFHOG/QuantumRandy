from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantumrandy.portfolio_universe import run_portfolio_universe_evaluation, write_portfolio_universe_report
from quantumrandy.portfolio_walk_forward import load_portfolio_factor_rows, load_portfolio_manifest
from quantumrandy.universe import load_asset_dataset


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate fixed QuantumRandy portfolio blends across multiple asset configs."
    )
    parser.add_argument("--config", action="append", default=[], help="Asset config yaml; repeat for BTC/ETH/SOL/etc.")
    parser.add_argument("--portfolio-manifest", required=True, help="Path to portfolio_manifest.json")
    parser.add_argument("--portfolio-factors", required=True, help="Path to portfolio_factors.csv")
    parser.add_argument("--portfolio-id", action="append", default=[], help="Portfolio id to evaluate; can be repeated")
    parser.add_argument("--window", choices=["training", "validation", "all"], default="validation")
    parser.add_argument("--out", default="reports/portfolio_universe_eval", help="Output directory")
    args = parser.parse_args()

    config_paths = args.config or ["configs/btcusdt.yaml"]
    assets = [load_asset_dataset(path, window=args.window) for path in config_paths]
    manifest = load_portfolio_manifest(args.portfolio_manifest)
    factor_rows = load_portfolio_factor_rows(args.portfolio_factors)

    details, summary, output_manifest = run_portfolio_universe_evaluation(
        assets,
        manifest,
        factor_rows,
        portfolio_ids=args.portfolio_id or None,
    )
    summary = summary.sort_values(
        ["robustness_score", "pass_rate", "mean_sharpe", "median_rank_ic"],
        ascending=[False, False, False, False],
    )
    output_manifest.update(
        {
            "window": args.window,
            "portfolio_manifest_path": str(Path(args.portfolio_manifest)),
            "portfolio_factors_path": str(Path(args.portfolio_factors)),
        }
    )
    write_portfolio_universe_report(args.out, details=details, summary=summary, manifest=output_manifest)

    print(f"Loaded {len(factor_rows)} factor rows across {len(assets)} asset configs")
    print(f"Output: {Path(args.out).resolve()}")
    for row in summary.to_dict(orient="records"):
        print(
            f"{row['portfolio_id']}: score={row['robustness_score']:.2f} "
            f"pass_rate={row['pass_rate']:.2f} mean_sharpe={row['mean_sharpe']:.2f} "
            f"median_rank_ic={row['median_rank_ic']:.4f}"
        )


if __name__ == "__main__":
    main()
