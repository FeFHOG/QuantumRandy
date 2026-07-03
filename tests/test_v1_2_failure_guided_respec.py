from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from quantumrandy.expression import parse_formula
from quantumrandy.v12_failure_guided_respec_export import (
    V12_BUNDLE_CANDIDATES,
    V12_SINGLE_FACTOR_CANDIDATES,
    export_v1_2_failure_guided_scoped_respec,
)
from quantumrandy.v12_failure_guided_respec_memory import (
    build_v1_2_failure_guided_respec_memory_rows,
    write_v1_2_failure_guided_respec_failure_memory,
)


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_export_v1_2_failure_guided_candidates_are_scoped_and_non_funding(tmp_path) -> None:
    out = tmp_path / "v12_export"

    manifest = export_v1_2_failure_guided_scoped_respec(out)

    assert manifest["artifact_type"] == "quantumrandy_factor_candidate_export_manifest"
    assert manifest["research_checkpoint"] == "v1.2"
    assert manifest["candidate_family"] == "failure_guided_scoped_respec"
    assert manifest["scope_contract"]["intended_scope"] == "BTCUSDT_4h"
    assert manifest["scope_contract"]["out_of_scope_policy"] == "diagnostic_only"
    assert manifest["source"]["created_from_spec"] == (
        "docs/superpowers/specs/2026-07-03-research-v1-2-failure-guided-scoped-respec-design.md"
    )
    assert manifest["excluded_research10_survivor"] == {
        "candidate_id": "qr_v09d_funding_return_long_001",
        "variant_id": "thr_0p0_long_short_cap_0p5_none",
        "formula_family": "funding_return_long_horizon",
    }
    assert manifest["candidate_count"] == len(V12_SINGLE_FACTOR_CANDIDATES) + len(V12_BUNDLE_CANDIDATES)
    assert manifest["single_factor_count"] == 9
    assert manifest["bundle_count"] == 3
    assert manifest["safety"]["research_only"] is True
    assert manifest["safety"]["not_runtime_publish_payload"] is True
    assert manifest["safety"]["does_not_auto_admit_factors"] is True

    records = _jsonl(out / "factor_candidates.jsonl")
    bundle_records = _jsonl(out / "bundle_candidates.jsonl")
    assert len(records) == 12
    assert len(bundle_records) == 3

    disallowed_candidate_ids = {"qr_v09d_funding_return_long_001", "qr_v09d_bundle_funding_confirmation_001"}
    disallowed_formula_fragments = {"funding_rate"}
    required_families = {
        "volume_conviction_hardening",
        "trend_quality_simplification",
        "crash_resilient_participation",
        "failure_guided_equal_weight_bundle",
    }
    allowed_fields = {"open", "high", "low", "close", "volume"}
    observed_families = set()

    for record in records:
        assert record["artifact_type"] == "quantumrandy_factor_candidate_export"
        assert record["research_checkpoint"] == "v1.2"
        assert record["research_only"] is True
        assert record["not_runtime_publish_payload"] is True
        assert record["intended_scope"] == "BTCUSDT_4h"
        assert record["out_of_scope_policy"] == "diagnostic_only"
        assert record["candidate_id"] not in disallowed_candidate_ids
        assert record["candidate_tier"] in {"failure_guided_candidate", "failure_guided_bundle"}
        assert set(record["required_features"]).issubset(allowed_fields)
        observed_families.add(record["formula_family"])
        formulas = [record["formula"], *record.get("component_formulas", [])]
        for formula in formulas:
            parse_formula(formula)
            assert not any(fragment in formula for fragment in disallowed_formula_fragments)

    assert required_families.issubset(observed_families)

    csv = pd.read_csv(out / "factor_candidates.csv")
    assert len(csv) == 12
    assert set(csv["intended_scope"]) == {"BTCUSDT_4h"}
    assert set(csv["out_of_scope_policy"]) == {"diagnostic_only"}

    report = (out / "FACTOR_CANDIDATE_EXPORT.md").read_text(encoding="utf-8")
    assert "Research v1.2" in report
    assert "failure-guided scoped candidate re-spec" in report
    assert "not a runtime publish payload" in report


def test_v1_2_failure_memory_records_only_failed_rankings(tmp_path) -> None:
    source_robustness_dir = "reports/factor_candidate_robustness/research_v1_2_failure_guided_respec"
    ranking_csv = tmp_path / "watchlist_robustness_variant_ranking.csv"
    pd.DataFrame(
        [
            {
                "candidate_id": "qr_v12_failure",
                "variant_id": "blocked_variant",
                "formula": "sub(close, open)",
                "conservative_verdict": "blocked",
                "intended_scope": "BTCUSDT_4h",
                "robustness_labels": "weak_blind_window",
                "failure_reasons": "crash_drawdown",
                "diagnostic_failure_reasons": "cross_asset_concentration",
                "stress_survival_score": 0.5,
                "stress_survival_count": 1,
                "stress_count": 2,
                "mean_sharpe": 0.123456789,
                "validation_mean_sharpe": -0.2,
                "blind_mean_sharpe": -0.3,
                "mean_max_dd": -0.4,
                "worst_max_dd": -0.5,
            },
            {
                "candidate_id": "qr_v12_watchlist",
                "variant_id": "watchlist_variant",
                "formula": "add(close, volume)",
                "conservative_verdict": "research_watchlist",
                "intended_scope": "",
                "robustness_labels": "clean_watchlist",
                "failure_reasons": "",
                "diagnostic_failure_reasons": "",
                "stress_survival_count": 2,
                "stress_count": 2,
                "mean_sharpe": 1.0,
                "validation_mean_sharpe": 1.1,
                "blind_mean_sharpe": 1.2,
                "mean_max_dd": -0.1,
                "worst_max_dd": -0.2,
            },
        ]
    ).to_csv(ranking_csv, index=False)

    rows = build_v1_2_failure_guided_respec_memory_rows(
        ranking_csv,
        source_robustness_dir=source_robustness_dir,
    )
    manifest = write_v1_2_failure_guided_respec_failure_memory(
        ranking_csv,
        tmp_path / "failure_memory",
        source_robustness_dir=source_robustness_dir,
    )

    assert len(rows) == 2
    assert manifest["input_rows"] == 2
    assert manifest["failure_count"] == 1
    failed_row, survivor_row = rows
    assert failed_row["candidate_family"] == "research_v1_2_failure_guided_respec_variant"
    assert failed_row["intended_scope"] == "BTCUSDT_4h"
    assert failed_row["out_of_scope_policy"] == "diagnostic_only"
    assert failed_row["source_review_dir"] == source_robustness_dir
    assert failed_row["source_robustness_dir"] == source_robustness_dir
    assert failed_row["stress_survival"] == "1/2"
    assert failed_row["passed"] is False
    assert failed_row["sharpe"] == 0.12345679
    assert failed_row["validation_sharpe"] == -0.2
    assert failed_row["blind_sharpe"] == -0.3
    assert failed_row["max_dd"] == -0.4
    assert failed_row["worst_max_dd"] == -0.5
    assert survivor_row["passed"] is True
    assert survivor_row["intended_scope"] == "BTCUSDT_4h"
    assert survivor_row["stress_survival"] == "2/2"
    assert "replication_stress_fragility" not in set(str(survivor_row["failure_labels"]).split("|"))

    failure_memory = pd.read_csv(tmp_path / "failure_memory" / "failure_memory.csv")
    assert len(failure_memory) == 1
    failed = failure_memory.iloc[0]
    assert failed["candidate_id"] == "qr_v12_failure::blocked_variant"
    assert failed["candidate_family"] == "research_v1_2_failure_guided_respec_variant"
    assert failed["formula"] == "sub(close, open)"
    assert failed["intended_scope"] == "BTCUSDT_4h"
    assert failed["out_of_scope_policy"] == "diagnostic_only"
    assert failed["conservative_verdict"] == "blocked"
    assert failed["source_review_dir"] == source_robustness_dir
    assert failed["failed_gates"] == "crash_drawdown"
    assert failed["sharpe"] == 0.12345679
    assert failed["validation_sharpe"] == -0.2
    assert failed["max_dd"] == -0.4
    labels = set(str(failed["failure_labels"]).split("|"))
    assert {"failure_guided_respec", "non_funding_family", "replication_stress_fragility"}.issubset(labels)
