from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantumrandy.candidate_rewrite import (
    CandidateRewritePolicy,
    load_rewrite_targets,
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
    parser.add_argument("--use-llm", action="store_true", help="Call DeepSeek if DEEPSEEK_API_KEY is configured")
    parser.add_argument("--candidate-selector-path", help="Optional selector artifact path to include in LLM prompt")
    parser.add_argument("--failure-memory-path", help="Optional failure memory artifact path to include in LLM prompt")
    parser.add_argument("--timeout-seconds", type=int, default=120)
    args = parser.parse_args()

    policy = CandidateRewritePolicy(
        max_targets=args.max_targets,
        candidates_per_target=args.candidates_per_target,
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
    manifest = write_selector_rewrite_report(targets, generator, args.out, policy=policy)
    print(
        f"Selector rewrite: targets={manifest['target_count']} "
        f"candidates={manifest['candidate_count']} out={Path(args.out).resolve()}"
    )


if __name__ == "__main__":
    main()
