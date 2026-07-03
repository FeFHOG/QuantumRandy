from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from quantumrandy.expression import parse_formula
from quantumrandy.v11_independent_replication_export import (
    V11_BUNDLE_CANDIDATES,
    V11_SINGLE_FACTOR_CANDIDATES,
    export_v1_1_independent_scoped_candidates,
)


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_export_v1_1_independent_candidates_excludes_current_funding_survivor(tmp_path) -> None:
    out = tmp_path / "v11_export"

    manifest = export_v1_1_independent_scoped_candidates(out)

    assert manifest["artifact_type"] == "quantumrandy_factor_candidate_export_manifest"
    assert manifest["research_checkpoint"] == "v1.1"
    assert manifest["candidate_family"] == "independent_scoped_family_replication"
    assert manifest["scope_contract"]["intended_scope"] == "BTCUSDT_4h"
    assert manifest["scope_contract"]["out_of_scope_policy"] == "diagnostic_only"
    assert manifest["excluded_research10_survivor"] == {
        "candidate_id": "qr_v09d_funding_return_long_001",
        "variant_id": "thr_0p0_long_short_cap_0p5_none",
        "formula_family": "funding_return_long_horizon",
    }
    assert manifest["candidate_count"] == len(V11_SINGLE_FACTOR_CANDIDATES) + len(V11_BUNDLE_CANDIDATES)
    assert manifest["single_factor_count"] == 8
    assert manifest["bundle_count"] == 2
    assert manifest["safety"]["research_only"] is True
    assert manifest["safety"]["not_runtime_publish_payload"] is True
    assert manifest["safety"]["does_not_auto_admit_factors"] is True

    records = _jsonl(out / "factor_candidates.jsonl")
    bundle_records = _jsonl(out / "bundle_candidates.jsonl")
    assert len(records) == 10
    assert len(bundle_records) == 2

    disallowed_candidate_ids = {"qr_v09d_funding_return_long_001", "qr_v09d_bundle_funding_confirmation_001"}
    disallowed_formula_fragments = {"funding_rate"}
    allowed_fields = {"open", "high", "low", "close", "volume"}

    for record in records:
        assert record["artifact_type"] == "quantumrandy_factor_candidate_export"
        assert record["research_checkpoint"] == "v1.1"
        assert record["research_only"] is True
        assert record["not_runtime_publish_payload"] is True
        assert record["intended_scope"] == "BTCUSDT_4h"
        assert record["out_of_scope_policy"] == "diagnostic_only"
        assert record["candidate_id"] not in disallowed_candidate_ids
        assert record["candidate_tier"] in {"independent_candidate", "independent_bundle"}
        assert set(record["required_features"]).issubset(allowed_fields)
        formulas = [record["formula"], *record.get("component_formulas", [])]
        for formula in formulas:
            parse_formula(formula)
            assert not any(fragment in formula for fragment in disallowed_formula_fragments)

    csv = pd.read_csv(out / "factor_candidates.csv")
    assert len(csv) == 10
    assert set(csv["intended_scope"]) == {"BTCUSDT_4h"}
    assert set(csv["out_of_scope_policy"]) == {"diagnostic_only"}

    report = (out / "FACTOR_CANDIDATE_EXPORT.md").read_text(encoding="utf-8")
    assert "Research v1.1" in report
    assert "independent scoped family replication" in report
    assert "not a runtime publish payload" in report


def test_v1_1_failure_memory_records_only_failed_independent_rankings(tmp_path) -> None:
    from quantumrandy.v11_independent_replication_memory import (
        build_v1_1_independent_replication_memory_rows,
        write_v1_1_independent_replication_failure_memory,
    )

    ranking_csv = tmp_path / "watchlist_robustness_variant_ranking.csv"
    pd.DataFrame(
        [
            {
                "candidate_id": "qr_v11_volume_conviction_001",
                "formula": "zscore(corr(sub(close,open),volume,48),72)",
                "variant_id": "thr_0p0_long_flat_cap_0p5_none",
                "conservative_verdict": "blocked_pending_new_hypotheses",
                "failure_reasons": "weak_validation_window",
                "diagnostic_failure_reasons": "low_mean_sharpe",
                "robustness_labels": "fee_fragility|asset_exclusion_fragility",
                "stress_survival_count": 14,
                "stress_count": 15,
                "stress_survival_score": 0.93333333,
                "diagnostic_scenario_count": 1,
                "mean_sharpe": 0.8,
                "validation_mean_sharpe": -0.1,
                "blind_mean_sharpe": 0.5,
                "mean_max_dd": 0.2,
                "worst_max_dd": 0.4,
            },
            {
                "candidate_id": "qr_v11_range_position_001",
                "formula": "zscore(div(sub(close,sma(close,48)),sub(max(high,48),min(low,48))),96)",
                "variant_id": "thr_0p0_long_short_cap_0p5_none",
                "conservative_verdict": "research_watchlist",
                "failure_reasons": "",
                "diagnostic_failure_reasons": "low_mean_sharpe",
                "robustness_labels": "sol_avax_concentration",
                "stress_survival_count": 15,
                "stress_count": 15,
                "stress_survival_score": 1.0,
                "diagnostic_scenario_count": 1,
                "mean_sharpe": 0.7,
                "validation_mean_sharpe": 0.3,
                "blind_mean_sharpe": 0.4,
                "mean_max_dd": 0.2,
                "worst_max_dd": 0.3,
            },
        ]
    ).to_csv(ranking_csv, index=False)

    rows = build_v1_1_independent_replication_memory_rows(
        ranking_csv,
        source_robustness_dir="reports/factor_candidate_robustness/research_v1_1_independent_replication",
    )

    assert len(rows) == 2
    by_id = {row["candidate_id"]: row for row in rows}
    failed = by_id["qr_v11_volume_conviction_001::thr_0p0_long_flat_cap_0p5_none"]
    assert failed["passed"] is False
    assert failed["candidate_family"] == "research_v1_1_independent_replication_variant"
    assert failed["intended_scope"] == "BTCUSDT_4h"
    assert failed["out_of_scope_policy"] == "diagnostic_only"
    assert failed["stress_survival"] == "14/15"
    assert "independent_family_replication" in failed["failure_labels"]
    assert "replication_stress_fragility" in failed["failure_labels"]
    assert "weak_validation_window" in failed["failure_labels"]

    survivor = by_id["qr_v11_range_position_001::thr_0p0_long_short_cap_0p5_none"]
    assert survivor["passed"] is True
    assert "replication_stress_fragility" not in survivor["failure_labels"]

    out = tmp_path / "failure_memory"
    manifest = write_v1_1_independent_replication_failure_memory(
        ranking_csv,
        out,
        source_robustness_dir="reports/factor_candidate_robustness/research_v1_1_independent_replication",
    )

    assert manifest["artifact_type"] == "quantumrandy_failure_memory"
    assert manifest["input_rows"] == 2
    assert manifest["failure_count"] == 1
    memory = pd.read_csv(out / "failure_memory.csv")
    assert memory.iloc[0]["candidate_id"] == "qr_v11_volume_conviction_001::thr_0p0_long_flat_cap_0p5_none"
