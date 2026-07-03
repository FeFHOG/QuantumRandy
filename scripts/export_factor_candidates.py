from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantumrandy.factor_candidate_export import export_selector_v082_factor_candidates


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export research-only factor candidates from selector v0.8.2 milestone evidence."
    )
    parser.add_argument(
        "--evidence-summary",
        default="reports/selector_pipeline_evidence_v082_summary",
        help="Selector evidence summary directory.",
    )
    parser.add_argument(
        "--out",
        default="reports/factor_candidate_exports/selector_v082_milestone_4_60",
        help="Output directory for JSONL, CSV, manifest, and Markdown report.",
    )
    parser.add_argument(
        "--window",
        default="attempts_4_60",
        help="Selector evidence window label to stamp into exported records.",
    )
    parser.add_argument(
        "--randyslab-profile",
        default="strict4h_v1",
        help="Suggested strict RandysLab evaluation profile label.",
    )
    parser.add_argument(
        "--intended-scope",
        default="multi_asset_crypto_4h_research",
        help="Declared asset/regime scope for downstream strict judging.",
    )
    parser.add_argument(
        "--applicability-hypothesis",
        default="Multi-asset 4h crypto perpetual research candidate.",
        help="Plain-English scope hypothesis for downstream review.",
    )
    parser.add_argument(
        "--out-of-scope-policy",
        default="diagnostic_only",
        help="How downstream judges should treat out-of-scope asset/regime rows.",
    )
    args = parser.parse_args()

    manifest = export_selector_v082_factor_candidates(
        args.evidence_summary,
        args.out,
        intended_scope=args.intended_scope,
        applicability_hypothesis=args.applicability_hypothesis,
        out_of_scope_policy=args.out_of_scope_policy,
        selector_evidence_window=args.window,
        randyslab_eval_profile=args.randyslab_profile,
    )
    print(
        "Factor candidate export: "
        f"candidates={manifest['candidate_count']} "
        f"jsonl={Path(manifest['outputs']['jsonl']).resolve()} "
        f"csv={Path(manifest['outputs']['csv']).resolve()}"
    )


if __name__ == "__main__":
    main()
