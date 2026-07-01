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
    parser.add_argument(
        "--llm-only",
        action="store_true",
        help="Do not fill missing LLM rewrite slots with local fallback candidates.",
    )
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
    parser.add_argument(
        "--require-llm-evidence",
        action="store_true",
        help="Exit non-zero unless --use-llm produced at least one accepted LLM rewrite.",
    )
    parser.add_argument(
        "--require-llm-true-improvement",
        action="store_true",
        help="Exit non-zero unless review highlights include a true_improved candidate from llm_rewrite.",
    )
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
        allow_local_fallback=not args.llm_only,
        run_universe=not args.skip_universe,
        run_portfolio_universe=not args.skip_portfolio_universe,
        max_corr=args.max_corr,
        min_portfolio_factors=args.min_portfolio_factors,
    )
    if args.require_llm_evidence and not manifest["rewrite"].get("is_llm_policy_evidence", False):
        print(
            "Selector rewrite pipeline did not produce LLM policy evidence: "
            f"use_llm={manifest['rewrite'].get('use_llm_requested')} "
            f"llm_accepted={manifest['rewrite'].get('llm_rewrite_accepted', 0)} "
            f"fallback_accepted={manifest['rewrite'].get('fallback_rewrite_accepted', 0)}",
            file=sys.stderr,
        )
        raise SystemExit(2)
    if args.require_llm_true_improvement and not manifest.get("review", {}).get(
        "is_llm_true_improvement_evidence", False
    ):
        review = manifest.get("review", {})
        print(
            "Selector rewrite pipeline did not produce LLM true-improvement evidence: "
            f"review_status={review.get('status')} "
            f"llm_true_improved={review.get('llm_true_improved_count', 0)} "
            f"highlight_sources={review.get('candidate_highlight_generation_source_counts', {})}",
            file=sys.stderr,
        )
        raise SystemExit(3)
    print(
        "Selector rewrite pipeline: "
        f"rewrite={manifest['rewrite']['candidate_count']} "
        f"llm_evidence={manifest['rewrite'].get('is_llm_policy_evidence', False)} "
        f"llm_true_improvement={manifest.get('review', {}).get('is_llm_true_improvement_evidence', False)} "
        f"universe={manifest['universe']['status']} "
        f"portfolio_universe={manifest['portfolio_universe']['status']} "
        f"out={Path(args.out).resolve()}"
    )


if __name__ == "__main__":
    main()
