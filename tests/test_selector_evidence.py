from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from quantumrandy.selector_evidence import summarize_selector_pipeline_runs


def _write_pipeline_run(
    root: Path,
    *,
    run_id: str,
    highlight_source: str,
    llm_true_improved_count: int,
) -> Path:
    out = root / run_id
    review = out / "review"
    review.mkdir(parents=True)
    is_llm_true = llm_true_improved_count > 0
    manifest = {
        "artifact_type": "quantumrandy_selector_rewrite_research_pipeline",
        "selector_path": "reports/candidate_selector_archive_eval",
        "window": "validation",
        "rewrite": {
            "candidate_count": 2,
            "llm_rewrite_accepted": 2,
            "fallback_rewrite_accepted": 0 if highlight_source == "llm_rewrite" else 1,
            "allow_local_fallback": highlight_source != "llm_rewrite",
            "is_llm_policy_evidence": True,
            "llm_error_count": 0,
        },
        "universe": {"status": "completed"},
        "portfolio_universe": {"status": "completed"},
        "review": {
            "status": "completed",
            "candidate_review_rows": 2,
            "candidate_verdict_counts": {"improved": 1, "not_improved": 1},
            "candidate_generation_source_counts": {highlight_source: 1, "llm_rewrite": 1},
            "candidate_highlight_counts": {"true_improved": 1},
            "candidate_highlight_generation_source_counts": {highlight_source: 1},
            "llm_true_improved_count": llm_true_improved_count,
            "is_llm_true_improvement_evidence": is_llm_true,
        },
    }
    (out / "selector_rewrite_pipeline_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    pd.DataFrame(
        [
            {
                "highlight_type": "true_improved",
                "parent_factor_id": "parent_a",
                "factor_id": f"{run_id}_candidate",
                "rewrite_generation_source": highlight_source,
                "pass_rate_delta": 0.2,
                "mean_sharpe_delta": 0.05,
                "candidate_mean_sharpe": 0.4,
                "candidate_failed_assets": "BTCUSDT,ETHUSDT",
                "formula": "zscore(corr(sub(close,open),volume,36),96)",
            }
        ]
    ).to_csv(review / "selector_pipeline_candidate_highlights.csv", index=False)
    return out


def test_summarize_selector_pipeline_runs_preserves_llm_true_improvement_source(tmp_path) -> None:
    local_highlight = _write_pipeline_run(
        tmp_path,
        run_id="mixed_source",
        highlight_source="local_rewrite",
        llm_true_improved_count=0,
    )
    llm_highlight = _write_pipeline_run(
        tmp_path,
        run_id="llm_only_required",
        highlight_source="llm_rewrite",
        llm_true_improved_count=1,
    )

    manifest = summarize_selector_pipeline_runs([local_highlight, llm_highlight], tmp_path / "summary")

    assert manifest["artifact_type"] == "quantumrandy_selector_pipeline_evidence_summary"
    assert manifest["safety"]["research_only"] is True
    assert manifest["run_count"] == 2
    assert manifest["llm_policy_evidence_runs"] == 2
    assert manifest["llm_true_improvement_evidence_runs"] == 1
    summary = pd.read_csv(tmp_path / "summary" / "selector_pipeline_evidence_summary.csv")
    by_run = {row["run_id"]: row for row in summary.to_dict(orient="records")}
    assert by_run["mixed_source"]["is_llm_true_improvement_evidence"] is False
    assert by_run["mixed_source"]["best_llm_true_improved_factor_id"] != "mixed_source_candidate"
    assert by_run["llm_only_required"]["is_llm_true_improvement_evidence"] is True
    assert by_run["llm_only_required"]["best_llm_true_improved_factor_id"] == "llm_only_required_candidate"
    report = (tmp_path / "summary" / "SELECTOR_PIPELINE_EVIDENCE_SUMMARY.md").read_text(encoding="utf-8")
    assert "research audit artifact only" in report
    assert "LLM true-improvement evidence runs" in report
    assert "`llm_only_required_candidate`" in report
