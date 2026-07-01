from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantumrandy.selector_pipeline import run_selector_rewrite_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the research-only selector rewrite -> universe -> portfolio-universe evidence pipeline."
    )
    parser.add_argument("--selector", required=True, help="Path to candidate selector output dir or rewrite_targets.csv")
    parser.add_argument("--out", default="reports/selector_rewrite_pipeline", help="Output directory")
    parser.add_argument("--config", action="append", default=[], help="Asset config yaml; repeat for each asset")
    parser.add_argument("--window", choices=["training", "validation", "all"], default="validation")
    parser.add_argument("--max-targets", type=int, default=5)
    parser.add_argument("--candidates-per-target", type=int, default=2)
    parser.add_argument("--use-llm", action="store_true", help="Call the configured LLM if LLM_API_KEY is configured")
    parser.add_argument("--failure-memory-path", help="Optional failure memory artifact path for prompt context")
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("--skip-universe", action="store_true", help="Generate rewrite candidates without universe eval")
    parser.add_argument(
        "--skip-portfolio-universe",
        action="store_true",
        help="Skip fixed-blend portfolio and portfolio-universe evaluation.",
    )
    parser.add_argument("--max-corr", type=float, help="Portfolio factor correlation cap")
    parser.add_argument("--min-portfolio-factors", type=int, default=1)
    args = parser.parse_args()

    manifest = run_selector_rewrite_pipeline(
        selector_path=args.selector,
        out_dir=args.out,
        config_paths=args.config,
        window=args.window,
        max_targets=args.max_targets,
        candidates_per_target=args.candidates_per_target,
        use_llm=args.use_llm,
        failure_memory_path=args.failure_memory_path,
        timeout_seconds=args.timeout_seconds,
        run_universe=not args.skip_universe,
        run_portfolio_universe=not args.skip_portfolio_universe,
        max_corr=args.max_corr,
        min_portfolio_factors=args.min_portfolio_factors,
    )
    print(
        "Selector rewrite pipeline: "
        f"rewrite={manifest['rewrite']['candidate_count']} "
        f"universe={manifest['universe']['status']} "
        f"portfolio_universe={manifest['portfolio_universe']['status']} "
        f"out={Path(args.out).resolve()}"
    )


if __name__ == "__main__":
    main()
