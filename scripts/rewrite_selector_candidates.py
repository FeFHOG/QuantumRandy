from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantumrandy.candidate_rewrite import (
    CandidateRewritePolicy,
    load_rewrite_targets,
    load_selector_forbidden_subtrees,
    write_selector_rewrite_report,
)
from quantumrandy.config import PromptConfig
from quantumrandy.llm import FormulaGenerator, LLMSettings


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate research-only rewrite candidates from candidate selector rewrite targets."
    )
    parser.add_argument(
        "--selector",
        required=True,
        help="Path to candidate selector output directory or rewrite_targets.csv",
    )
    parser.add_argument("--out", default="reports/selector_rewrite", help="Output directory")
    parser.add_argument("--max-targets", type=int, default=5)
    parser.add_argument("--candidates-per-target", type=int, default=2)
    parser.add_argument("--use-llm", action="store_true", help="Call the configured LLM if LLM_API_KEY is configured")
    parser.add_argument(
        "--llm-only",
        action="store_true",
        help="Do not fill missing LLM rewrite slots with local fallback candidates.",
    )
    parser.add_argument("--candidate-selector-path", help="Optional selector artifact path to include in LLM prompt")
    parser.add_argument("--failure-memory-path", help="Optional failure memory artifact path to include in LLM prompt")
    parser.add_argument(
        "--no-selector-forbidden-subtrees",
        action="store_true",
        help="Do not convert selector weak clusters or matched failed subtrees into rewrite forbidden subtrees.",
    )
    parser.add_argument("--max-selector-forbidden-subtrees", type=int, default=8)
    parser.add_argument("--timeout-seconds", type=int, default=120)
    args = parser.parse_args()

    policy = CandidateRewritePolicy(
        max_targets=args.max_targets,
        candidates_per_target=args.candidates_per_target,
        avoid_selector_failed_subtrees=not args.no_selector_forbidden_subtrees,
        max_selector_forbidden_subtrees=args.max_selector_forbidden_subtrees,
        allow_local_fallback=not args.llm_only,
    )
    prompt = PromptConfig(
        candidate_selector_path=args.candidate_selector_path or args.selector,
        failure_memory_path=args.failure_memory_path,
    )
    generator = FormulaGenerator(
        use_llm=args.use_llm,
        settings=LLMSettings(timeout_seconds=args.timeout_seconds),
        prompt_config=prompt,
    )
    targets = load_rewrite_targets(args.selector, max_targets=args.max_targets)
    selector_forbidden = (
        load_selector_forbidden_subtrees(args.selector, max_subtrees=args.max_selector_forbidden_subtrees)
        if policy.avoid_selector_failed_subtrees
        else []
    )
    manifest = write_selector_rewrite_report(
        targets,
        generator,
        args.out,
        policy=policy,
        selector_forbidden_subtrees=selector_forbidden,
    )
    print(
        f"Selector rewrite: targets={manifest['target_count']} "
        f"candidates={manifest['candidate_count']} "
        f"selector_forbidden={manifest['selector_forbidden_subtree_count']} "
        f"out={Path(args.out).resolve()}"
    )


if __name__ == "__main__":
    main()
