from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantumrandy.selector_evidence import summarize_selector_pipeline_runs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Summarize research-only selector rewrite pipeline evidence across multiple runs."
    )
    parser.add_argument("pipeline_run", nargs="+", help="Selector rewrite pipeline output directory")
    parser.add_argument("--out", default="reports/selector_pipeline_evidence_summary", help="Output directory")
    args = parser.parse_args()

    manifest = summarize_selector_pipeline_runs(args.pipeline_run, args.out)
    print(
        "Selector pipeline evidence summary: "
        f"runs={manifest['run_count']} "
        f"llm_true_improvement_runs={manifest['llm_true_improvement_evidence_runs']} "
        f"out={Path(manifest['outputs']['summary_markdown']).resolve()}"
    )


if __name__ == "__main__":
    main()
