from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from quantumrandy.selector_evidence import load_selector_negative_prompt_context, summarize_selector_pipeline_runs


def _write_pipeline_run(
    root: Path,
    *,
    run_id: str,
    highlight_source: str,
    llm_true_improved_count: int,
    factor_id: str | None = None,
    formula: str = "zscore(corr(sub(close,open),volume,36),96)",
    highlight_type: str = "true_improved",
    review_verdict: str = "not_improved",
    pass_rate_delta: float = -0.2,
    mean_sharpe_delta: float = -0.4,
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
            "candidate_highlight_counts": {highlight_type: 1},
            "candidate_highlight_generation_source_counts": {highlight_source: 1},
            "llm_true_improved_count": llm_true_improved_count,
            "is_llm_true_improvement_evidence": is_llm_true,
        },
    }
    (out / "selector_rewrite_pipeline_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    pd.DataFrame(
        [
            {
                "highlight_type": highlight_type,
                "parent_factor_id": "parent_a",
                "factor_id": factor_id or f"{run_id}_candidate",
                "rewrite_generation_source": highlight_source,
                "pass_rate_delta": 0.2,
                "mean_sharpe_delta": 0.05,
                "candidate_mean_sharpe": 0.4,
                "candidate_failed_assets": "BTCUSDT,ETHUSDT",
                "formula": formula,
            }
        ]
    ).to_csv(review / "selector_pipeline_candidate_highlights.csv", index=False)
    pd.DataFrame(
        [
            {
                "factor_id": factor_id or f"{run_id}_candidate",
                "formula": formula,
                "rewrite_generation_source": highlight_source,
                "parent_factor_id": "parent_a",
                "parent_formula": "zscore(sub(sma(close,12),sma(close,48)),48)",
                "parent_formula_family": "price",
                "candidate_review_verdict": review_verdict,
                "pass_rate_delta": pass_rate_delta,
                "mean_sharpe_delta": mean_sharpe_delta,
                "candidate_mean_sharpe": -0.1,
                "candidate_failed_assets": "BTCUSDT,ETHUSDT",
            }
        ]
    ).to_csv(review / "selector_pipeline_candidate_review.csv", index=False)
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
        factor_id="stable_llm_candidate",
    )
    llm_repeat = _write_pipeline_run(
        tmp_path,
        run_id="llm_only_repeat",
        highlight_source="llm_rewrite",
        llm_true_improved_count=1,
        factor_id="stable_llm_candidate",
    )
    conflict_positive = _write_pipeline_run(
        tmp_path,
        run_id="llm_conflict_positive",
        highlight_source="llm_rewrite",
        llm_true_improved_count=1,
        factor_id="family_positive_candidate",
        review_verdict="improved",
        pass_rate_delta=0.4,
        mean_sharpe_delta=0.3,
    )
    llm_mixed = _write_pipeline_run(
        tmp_path,
        run_id="llm_mixed_rejected",
        highlight_source="llm_rewrite",
        llm_true_improved_count=0,
        factor_id="sharpe_only_candidate",
        formula="zscore(ret(close,48),120)",
        highlight_type="sharpe_improved_no_pass_lift",
        review_verdict="mixed",
        pass_rate_delta=-0.2,
        mean_sharpe_delta=0.05,
    )
    range_negative_1 = _write_pipeline_run(
        tmp_path,
        run_id="range_negative_1",
        highlight_source="llm_rewrite",
        llm_true_improved_count=0,
        factor_id="range_negative_1_candidate",
        formula="zscore(std(close,24),120)",
        highlight_type="not_improved_audit",
        review_verdict="not_improved",
        pass_rate_delta=-0.2,
        mean_sharpe_delta=-0.8,
    )
    range_negative_2 = _write_pipeline_run(
        tmp_path,
        run_id="range_negative_2",
        highlight_source="llm_rewrite",
        llm_true_improved_count=0,
        factor_id="range_negative_2_candidate",
        formula="neg(zscore(std(close,24),120))",
        highlight_type="not_improved_audit",
        review_verdict="not_improved",
        pass_rate_delta=-0.2,
        mean_sharpe_delta=-0.7,
    )

    manifest = summarize_selector_pipeline_runs(
        [
            local_highlight,
            llm_highlight,
            llm_repeat,
            conflict_positive,
            llm_mixed,
            range_negative_1,
            range_negative_2,
        ],
        tmp_path / "summary",
    )

    assert manifest["artifact_type"] == "quantumrandy_selector_pipeline_evidence_summary"
    assert manifest["safety"]["research_only"] is True
    assert manifest["run_count"] == 7
    assert manifest["llm_policy_evidence_runs"] == 7
    assert manifest["llm_true_improvement_evidence_runs"] == 3
    assert manifest["candidate_highlight_rows"] == 7
    assert manifest["candidate_summary_rows"] == 6
    assert manifest["negative_candidate_rows"] == 5
    assert manifest["negative_family_rows"] == 3
    summary = pd.read_csv(tmp_path / "summary" / "selector_pipeline_evidence_summary.csv")
    by_run = {row["run_id"]: row for row in summary.to_dict(orient="records")}
    assert by_run["mixed_source"]["is_llm_true_improvement_evidence"] is False
    assert by_run["mixed_source"]["best_llm_true_improved_factor_id"] != "mixed_source_candidate"
    assert by_run["llm_only_required"]["is_llm_true_improvement_evidence"] is True
    assert by_run["llm_only_required"]["best_llm_true_improved_factor_id"] == "stable_llm_candidate"
    candidates = pd.read_csv(tmp_path / "summary" / "selector_pipeline_candidate_evidence_summary.csv")
    by_candidate = {row["factor_id"]: row for row in candidates.to_dict(orient="records")}
    assert by_candidate["stable_llm_candidate"]["run_count"] == 2
    assert by_candidate["stable_llm_candidate"]["llm_true_improved_count"] == 2
    assert by_candidate["mixed_source_candidate"]["llm_true_improved_count"] == 0
    assert by_candidate["family_positive_candidate"]["llm_true_improved_count"] == 1
    negatives = pd.read_csv(tmp_path / "summary" / "selector_pipeline_negative_candidate_summary.csv")
    assert negatives.iloc[0]["parent_formula_family"] == "price"
    assert negatives.iloc[0]["candidate_formula_family"] == "range_volatility"
    assert negatives.iloc[0]["negative_count"] == 2
    by_family = {
        (row["parent_formula_family"], row["candidate_formula_family"]): row
        for row in negatives.to_dict(orient="records")
    }
    assert by_family[("price", "volume_liquidity")]["negative_count"] == 2
    assert by_family[("price", "volume_liquidity")]["true_improved_count"] == 1
    assert by_family[("price", "price")]["sharpe_only_count"] == 1
    assert by_family[("price", "price")]["example_formula"] == "zscore(ret(close,48),120)"
    context = load_selector_negative_prompt_context(
        tmp_path / "summary",
        max_examples=1,
        max_families=1,
        max_disallowed_formulas=3,
        max_blocked_family_pairs=3,
        min_block_count=2,
    )
    assert context["available"] is True
    assert context["examples"][0]["candidate_formula_family"] == "range_volatility"
    assert context["families"][0]["negative_count"] == "2"
    assert context["families"][0]["true_improved_count"] == "0"
    assert context["disallowed_formulas"][0] == "zscore(std(close,24),120)"
    assert "zscore(corr(sub(close,open),volume,36),96)" in context["disallowed_formulas"]
    assert context["blocked_family_pairs"] == [
        {
            "parent_formula_family": "price",
            "candidate_formula_family": "range_volatility",
            "negative_count": "2",
            "avg_mean_sharpe_delta": "-0.75",
            "worst_mean_sharpe_delta": "-0.8",
        }
    ]
    report = (tmp_path / "summary" / "SELECTOR_PIPELINE_EVIDENCE_SUMMARY.md").read_text(encoding="utf-8")
    assert "research audit artifact only" in report
    assert "LLM true-improvement evidence runs" in report
    assert "Highlighted Candidates Across Runs" in report
    assert "Negative Candidate Families" in report
    assert "`stable_llm_candidate`" in report
