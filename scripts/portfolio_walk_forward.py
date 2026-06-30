from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantumrandy.config import load_config
from quantumrandy.data import load_market_frame
from quantumrandy.portfolio_walk_forward import (
    load_portfolio_factor_rows,
    load_portfolio_manifest,
    run_portfolio_walk_forward,
    write_portfolio_walk_forward_report,
)
from quantumrandy.walk_forward import build_walk_forward_windows


def main() -> None:
    parser = argparse.ArgumentParser(description="Portfolio-level walk-forward validation for fixed QuantumRandy blends.")
    parser.add_argument("--config", default="configs/btcusdt.yaml", help="Path to config yaml")
    parser.add_argument("--portfolio-manifest", required=True, help="Path to portfolio_manifest.json")
    parser.add_argument("--portfolio-factors", required=True, help="Path to portfolio_factors.csv")
    parser.add_argument("--portfolio-id", action="append", default=[], help="Portfolio id to evaluate; can be repeated")
    parser.add_argument("--out", default="reports/portfolio_walk_forward", help="Output directory")
    parser.add_argument("--train-months", type=int, default=18)
    parser.add_argument("--validation-months", type=int, default=6)
    parser.add_argument("--test-months", type=int, default=3)
    parser.add_argument("--step-months", type=int, default=3)
    parser.add_argument("--start", help="Optional UTC start date, e.g. 2019-09-08")
    parser.add_argument("--end", help="Optional UTC exclusive end date, e.g. 2025-11-24")
    parser.add_argument("--min-bars", type=int, default=120, help="Minimum bars required per segment")
    args = parser.parse_args()

    cfg = load_config(args.config)
    data = load_market_frame(cfg.ohlcv_csv, cfg.funding_csv)
    manifest = load_portfolio_manifest(args.portfolio_manifest)
    factor_rows = load_portfolio_factor_rows(args.portfolio_factors)
    windows = build_walk_forward_windows(
        data,
        train_months=args.train_months,
        validation_months=args.validation_months,
        test_months=args.test_months,
        step_months=args.step_months,
        start=args.start or cfg.windows.training_start,
        end=args.end or cfg.windows.validation_end,
        min_bars=args.min_bars,
    )
    if not windows:
        raise SystemExit("No walk-forward windows produced. Try reducing --min-bars or using a wider date range.")

    print(f"Loaded {len(factor_rows)} factor rows and built {len(windows)} walk-forward windows")
    details, summary, output_manifest = run_portfolio_walk_forward(
        data,
        manifest,
        factor_rows,
        cfg,
        windows,
        portfolio_ids=args.portfolio_id or None,
    )
    output_manifest.update(
        {
            "config": str(Path(args.config)),
            "portfolio_manifest_path": str(Path(args.portfolio_manifest)),
            "portfolio_factors_path": str(Path(args.portfolio_factors)),
            "train_months": args.train_months,
            "validation_months": args.validation_months,
            "test_months": args.test_months,
            "step_months": args.step_months,
            "min_bars": args.min_bars,
        }
    )
    summary = summary.sort_values(
        ["survival_rate", "test_sharpe_median", "test_rank_ic_median"],
        ascending=[False, False, False],
    )
    write_portfolio_walk_forward_report(
        args.out,
        details=details,
        summary=summary,
        windows=windows,
        manifest=output_manifest,
    )

    print(f"Output: {Path(args.out).resolve()}")
    print("Portfolios:")
    for row in summary.to_dict(orient="records"):
        print(
            f"{row['portfolio_id']}: survival={row['survival_rate']:.2f} "
            f"test_sharpe_median={row['test_sharpe_median']:.2f} "
            f"test_rank_ic_median={row['test_rank_ic_median']:.4f}"
        )


if __name__ == "__main__":
    main()
