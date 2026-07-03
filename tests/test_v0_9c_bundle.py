from __future__ import annotations

import json

import pandas as pd

from quantumrandy.factor_candidate_export import PRIMARY_SELECTOR_V082_FORMULAS
from quantumrandy.v09c_bundle_export import (
    V09C_BUNDLE_CANDIDATES,
    V09C_SINGLE_FACTOR_CANDIDATES,
    export_v0_9c_multi_factor_bundle_candidates,
)


def _jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_export_v0_9c_multi_factor_bundle_candidates_is_scoped_research_only(tmp_path) -> None:
    out = tmp_path / "v09c_export"

    manifest = export_v0_9c_multi_factor_bundle_candidates(out)

    assert manifest["artifact_type"] == "quantumrandy_factor_candidate_export_manifest"
    assert manifest["research_checkpoint"] == "v0.9c"
    assert manifest["candidate_family"] == "scoped_multi_factor_bundle"
    assert manifest["candidate_count"] == len(V09C_SINGLE_FACTOR_CANDIDATES) + len(V09C_BUNDLE_CANDIDATES)
    assert manifest["single_factor_count"] == len(V09C_SINGLE_FACTOR_CANDIDATES)
    assert manifest["bundle_count"] == len(V09C_BUNDLE_CANDIDATES)
    assert manifest["scope_contract"]["intended_scope"] == "BTCUSDT_4h"
    assert manifest["scope_contract"]["out_of_scope_policy"] == "diagnostic_only"
    assert manifest["safety"]["research_only"] is True
    assert manifest["safety"]["not_runtime_publish_payload"] is True
    assert manifest["safety"]["no_live_execution"] is True
    assert manifest["future_portfolio_interface"]["status"] == "interface_only_not_implemented"

    records = _jsonl(out / "factor_candidates.jsonl")
    bundle_records = _jsonl(out / "bundle_candidates.jsonl")
    assert len(records) == manifest["candidate_count"]
    assert len(bundle_records) == manifest["bundle_count"]

    single_records = [record for record in records if not record.get("component_formulas")]
    assert len(single_records) == len(V09C_SINGLE_FACTOR_CANDIDATES)
    single_formulas = {record["formula"] for record in single_records}
    assert single_formulas.isdisjoint(set(PRIMARY_SELECTOR_V082_FORMULAS))

    for record in records:
        assert record["artifact_type"] == "quantumrandy_factor_candidate_export"
        assert record["research_checkpoint"] == "v0.9c"
        assert record["research_only"] is True
        assert record["not_runtime_publish_payload"] is True
        assert record["intended_scope"] == "BTCUSDT_4h"
        assert record["out_of_scope_policy"] == "diagnostic_only"
        assert record["randyslab_eval_profile"] == "strict4h_v1"
        assert record["portfolio_interface_contract"]["forbidden_use"] == "runtime_allocation_or_live_execution"
        assert record["hypothesis"]
        assert record["expected_failure_mode"]

    for record in bundle_records:
        assert record["candidate_id"].startswith("qr_v09c_bundle_")
        assert record["formula_family"] == "scoped_equal_weight_bundle"
        assert record["combination_method"] == "equal_weight_mean"
        assert len(record["component_formulas"]) >= 3
        assert len(record["component_candidate_ids"]) == len(record["component_formulas"])
        assert record["formula"].startswith("equal_weight_mean(")

    csv = pd.read_csv(out / "factor_candidates.csv")
    assert len(csv) == manifest["candidate_count"]
    assert set(csv["intended_scope"]) == {"BTCUSDT_4h"}
    assert "component_formulas" in csv.columns

    report = (out / "FACTOR_CANDIDATE_EXPORT.md").read_text(encoding="utf-8")
    assert "Research v0.9c" in report
    assert "BTCUSDT_4h" in report
    assert "not a runtime publish payload" in report


def test_v0_9c_failure_memory_maps_review_and_correlation_rows(tmp_path) -> None:
    from quantumrandy.v09c_failure_memory import build_v0_9c_failure_memory_rows, write_v0_9c_failure_memory

    review_csv = tmp_path / "factor_candidate_review.csv"
    pd.DataFrame(
        [
            {
                "candidate_id": "qr_v09c_bundle_diversified_001",
                "formula": "equal_weight_mean(a,b,c)",
                "variant_id": "default",
                "intended_scope": "BTCUSDT_4h",
                "applicability_hypothesis": "BTCUSDT 4h scoped multi-factor research.",
                "out_of_scope_policy": "diagnostic_only",
                "review_verdict": "blocked_by_conservative_rules",
                "failure_reasons": "weak_validation_window|high_mean_drawdown",
                "mean_sharpe": 0.2,
                "validation_mean_sharpe": -0.1,
                "blind_mean_sharpe": 0.4,
                "mean_max_dd": 0.5,
                "worst_max_dd": 0.75,
            }
        ]
    ).to_csv(review_csv, index=False)
    correlation_csv = tmp_path / "factor_candidate_bundle_redundancy.csv"
    pd.DataFrame(
        [
            {
                "bundle_candidate_id": "qr_v09c_bundle_diversified_001",
                "component_count": 4,
                "max_abs_component_corr": 0.86,
                "redundancy_verdict": "redundant_research_memory_only",
            }
        ]
    ).to_csv(correlation_csv, index=False)

    rows = build_v0_9c_failure_memory_rows(
        review_csv,
        correlation_csv=correlation_csv,
        source_review_dir="reports/factor_candidate_review/research_v0_9c_bundle_btc_declared",
        source_correlation_dir="reports/factor_candidate_correlation/research_v0_9c_bundle_btc",
    )

    assert len(rows) == 1
    row = rows[0]
    assert row["candidate_family"] == "scoped_multi_factor_bundle"
    assert row["intended_scope"] == "BTCUSDT_4h"
    assert row["conservative_verdict"] == "research_memory_only"
    assert "weak_validation_window" in row["failure_labels"]
    assert "validation_bundle_fragility" in row["failure_labels"]
    assert "bundle_redundancy" in row["failure_labels"]
    assert row["kill_reasons"] == ["weak_validation_window", "high_mean_drawdown"]

    out = tmp_path / "failure_memory"
    manifest = write_v0_9c_failure_memory(
        review_csv,
        out,
        correlation_csv=correlation_csv,
        source_review_dir="reports/factor_candidate_review/research_v0_9c_bundle_btc_declared",
        source_correlation_dir="reports/factor_candidate_correlation/research_v0_9c_bundle_btc",
    )
    assert manifest["artifact_type"] == "quantumrandy_failure_memory"
    assert manifest["failure_count"] == 1
    memory = pd.read_csv(out / "failure_memory.csv")
    assert memory.iloc[0]["conservative_verdict"] == "research_memory_only"
    report = (out / "FAILURE_MEMORY_REPORT.md").read_text(encoding="utf-8")
    assert "Failed formulas" in report
