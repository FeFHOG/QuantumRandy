from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

import quantumrandy.v13_funding_adjacent_respec_export as v13_export
from quantumrandy.expression import parse_formula
from quantumrandy.v13_funding_adjacent_respec_export import (
    V13_BUNDLE_CANDIDATES,
    V13_EXCLUDED_RESEARCH10_SURVIVOR,
    V13_SINGLE_FACTOR_CANDIDATES,
    export_v1_3_funding_adjacent_scoped_respec,
)


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _candidate(candidate_id: str, formula: str = "neg(zscore(funding_rate,96))") -> dict:
    return {
        "candidate_id": candidate_id,
        "formula_family": "funding_pressure_normalization",
        "formula": formula,
        "hypothesis": "Test candidate.",
        "expected_failure_mode": "Test failure mode.",
    }


def _bundle(candidate_id: str, component_candidate_ids: list[str]) -> dict:
    return {
        "candidate_id": candidate_id,
        "formula_family": "funding_adjacent_equal_weight_bundle",
        "component_candidate_ids": component_candidate_ids,
        "hypothesis": "Test bundle.",
    }


def test_export_v1_3_funding_adjacent_candidates_are_scoped_and_nonduplicative(tmp_path) -> None:
    out = tmp_path / "v13_export"

    manifest = export_v1_3_funding_adjacent_scoped_respec(out)

    assert manifest["artifact_type"] == "quantumrandy_factor_candidate_export_manifest"
    assert manifest["research_checkpoint"] == "v1.3"
    assert manifest["candidate_family"] == "funding_adjacent_scoped_respec"
    assert manifest["funding_adjacent_status"] == "funding_adjacent_not_independent_non_funding"
    assert manifest["scope_contract"]["intended_scope"] == "BTCUSDT_4h"
    assert manifest["scope_contract"]["out_of_scope_policy"] == "diagnostic_only"
    assert manifest["source"]["created_from_spec"] == (
        "docs/superpowers/specs/2026-07-03-research-v1-3-funding-adjacent-scoped-respec-design.md"
    )
    assert manifest["excluded_research10_survivor"] == V13_EXCLUDED_RESEARCH10_SURVIVOR
    assert manifest["candidate_count"] == len(V13_SINGLE_FACTOR_CANDIDATES) + len(V13_BUNDLE_CANDIDATES)
    assert manifest["single_factor_count"] == 12
    assert manifest["bundle_count"] == 4
    assert manifest["safety"]["research_only"] is True
    assert manifest["safety"]["not_runtime_publish_payload"] is True
    assert manifest["safety"]["does_not_auto_admit_factors"] is True

    records = _jsonl(out / "factor_candidates.jsonl")
    bundle_records = _jsonl(out / "bundle_candidates.jsonl")
    assert len(records) == 16
    assert len(bundle_records) == 4

    excluded_id = V13_EXCLUDED_RESEARCH10_SURVIVOR["candidate_id"]
    excluded_formula = V13_EXCLUDED_RESEARCH10_SURVIVOR["formula"]
    required_families = {
        "funding_pressure_normalization",
        "funding_return_interaction",
        "cost_aware_carry_filter",
        "funding_regime_transition",
        "funding_adjacent_equal_weight_bundle",
    }
    allowed_fields = {"open", "high", "low", "close", "volume", "funding_rate"}
    observed_families = set()

    for record in records:
        assert record["artifact_type"] == "quantumrandy_factor_candidate_export"
        assert record["research_checkpoint"] == "v1.3"
        assert record["research_only"] is True
        assert record["not_runtime_publish_payload"] is True
        assert record["candidate_id"] != excluded_id
        assert record["formula"] != excluded_formula
        assert record["candidate_tier"] in {"funding_adjacent_candidate", "funding_adjacent_bundle"}
        assert record["funding_adjacent_status"] == "funding_adjacent_not_independent_non_funding"
        assert record["independence_claim"] == "none_funding_adjacent_locality_probe"
        assert record["excluded_research10_survivor"] == V13_EXCLUDED_RESEARCH10_SURVIVOR
        assert record["source"] == manifest["source"]
        assert record["safety"] == manifest["safety"]
        assert record["intended_scope"] == "BTCUSDT_4h"
        assert record["out_of_scope_policy"] == "diagnostic_only"
        assert set(record["required_features"]).issubset(allowed_fields)
        assert "funding_rate" in record["required_features"]
        observed_families.add(record["formula_family"])
        formulas = [record["formula"], *record.get("component_formulas", [])]
        assert excluded_formula not in formulas
        for formula in formulas:
            parse_formula(formula)
            assert "funding_rate" in formula
            assert formula != excluded_formula

    for bundle in bundle_records:
        assert excluded_id not in bundle["component_candidate_ids"]
        assert excluded_formula not in bundle["component_formulas"]

    assert required_families.issubset(observed_families)

    csv = pd.read_csv(out / "factor_candidates.csv")
    assert len(csv) == 16
    assert set(csv["intended_scope"]) == {"BTCUSDT_4h"}
    assert set(csv["out_of_scope_policy"]) == {"diagnostic_only"}
    assert set(csv["funding_adjacent_status"]) == {"funding_adjacent_not_independent_non_funding"}
    first_row = csv.iloc[0]
    assert json.loads(first_row["component_formulas"]) == []
    assert json.loads(first_row["component_candidate_ids"]) == []
    assert "funding_rate" in json.loads(first_row["required_features"])
    assert json.loads(first_row["excluded_research10_survivor"]) == V13_EXCLUDED_RESEARCH10_SURVIVOR
    assert json.loads(first_row["source"]) == manifest["source"]
    assert json.loads(first_row["safety"]) == manifest["safety"]
    bundle_row = csv[csv["candidate_tier"] == "funding_adjacent_bundle"].iloc[0]
    assert len(json.loads(bundle_row["component_formulas"])) == 3
    assert len(json.loads(bundle_row["component_candidate_ids"])) == 3

    report = (out / "FACTOR_CANDIDATE_EXPORT.md").read_text(encoding="utf-8")
    assert "Research v1.3" in report
    assert "funding-adjacent scoped re-spec" in report
    assert "not a runtime publish payload" in report
    assert "not independent non-funding replication" in report


def test_export_v1_3_rejects_excluded_survivor_id(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        v13_export,
        "V13_SINGLE_FACTOR_CANDIDATES",
        [_candidate(V13_EXCLUDED_RESEARCH10_SURVIVOR["candidate_id"])],
    )
    monkeypatch.setattr(v13_export, "V13_BUNDLE_CANDIDATES", [])

    with pytest.raises(ValueError, match="survivor ID"):
        export_v1_3_funding_adjacent_scoped_respec(tmp_path / "export")


def test_export_v1_3_rejects_canonical_equivalent_survivor_formula(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        v13_export,
        "V13_SINGLE_FACTOR_CANDIDATES",
        [
            _candidate(
                "qr_v13_bad_survivor_formula_001",
                " zscore( corr( funding_rate, ret( close, 42 ), 120 ), 72 ) ",
            )
        ],
    )
    monkeypatch.setattr(v13_export, "V13_BUNDLE_CANDIDATES", [])

    with pytest.raises(ValueError, match="survivor formula"):
        export_v1_3_funding_adjacent_scoped_respec(tmp_path / "export")


def test_export_v1_3_rejects_missing_funding_rate(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        v13_export,
        "V13_SINGLE_FACTOR_CANDIDATES",
        [_candidate("qr_v13_missing_funding_001", "zscore(ret(close,12),72)")],
    )
    monkeypatch.setattr(v13_export, "V13_BUNDLE_CANDIDATES", [])

    with pytest.raises(ValueError, match="requires funding_rate"):
        export_v1_3_funding_adjacent_scoped_respec(tmp_path / "export")


def test_export_v1_3_rejects_bundle_containing_survivor_id(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        v13_export,
        "V13_SINGLE_FACTOR_CANDIDATES",
        [
            _candidate("qr_v13_component_001"),
            _candidate("qr_v13_component_002"),
            _candidate("qr_v13_component_003"),
        ],
    )
    monkeypatch.setattr(
        v13_export,
        "V13_BUNDLE_CANDIDATES",
        [
            _bundle(
                "qr_v13_bad_survivor_id_bundle_001",
                [
                    "qr_v13_component_001",
                    V13_EXCLUDED_RESEARCH10_SURVIVOR["candidate_id"],
                    "qr_v13_component_003",
                ],
            )
        ],
    )

    with pytest.raises(ValueError, match="survivor bundle member"):
        export_v1_3_funding_adjacent_scoped_respec(tmp_path / "export")


def test_export_v1_3_rejects_bundle_containing_survivor_formula(monkeypatch) -> None:
    monkeypatch.setattr(
        v13_export,
        "V13_BUNDLE_CANDIDATES",
        [_bundle("qr_v13_bad_survivor_formula_bundle_001", ["c1", "c2", "c3"])],
    )
    single_records = [
        {"candidate_id": "c1", "formula": "neg(zscore(funding_rate,96))"},
        {"candidate_id": "c2", "formula": "zscore( corr( funding_rate, ret( close, 42 ), 120 ), 72 )"},
        {"candidate_id": "c3", "formula": "zscore(delta(funding_rate,12),96)"},
    ]

    with pytest.raises(ValueError, match="survivor formula"):
        v13_export._bundle_records(
            single_records,
            intended_scope=v13_export.V13_SCOPE,
            applicability_hypothesis=v13_export.V13_APPLICABILITY_HYPOTHESIS,
            out_of_scope_policy=v13_export.V13_OUT_OF_SCOPE_POLICY,
            randyslab_eval_profile="strict4h_v1",
        )


def test_export_v1_3_rejects_bad_bundle_component_lookup(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        v13_export,
        "V13_SINGLE_FACTOR_CANDIDATES",
        [
            _candidate("qr_v13_component_001"),
            _candidate("qr_v13_component_002"),
            _candidate("qr_v13_component_003"),
        ],
    )
    monkeypatch.setattr(
        v13_export,
        "V13_BUNDLE_CANDIDATES",
        [
            _bundle(
                "qr_v13_bad_unknown_component_bundle_001",
                ["qr_v13_component_001", "qr_v13_component_002", "qr_v13_unknown_component"],
            )
        ],
    )

    with pytest.raises(ValueError, match="unknown component qr_v13_unknown_component"):
        export_v1_3_funding_adjacent_scoped_respec(tmp_path / "export")


def test_export_v1_3_rejects_duplicate_or_wrong_sized_bundle_components(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        v13_export,
        "V13_SINGLE_FACTOR_CANDIDATES",
        [
            _candidate("qr_v13_component_001"),
            _candidate("qr_v13_component_002"),
            _candidate("qr_v13_component_003"),
        ],
    )
    monkeypatch.setattr(
        v13_export,
        "V13_BUNDLE_CANDIDATES",
        [
            _bundle(
                "qr_v13_bad_duplicate_bundle_001",
                ["qr_v13_component_001", "qr_v13_component_001", "qr_v13_component_003"],
            )
        ],
    )
    with pytest.raises(ValueError, match="unique components"):
        export_v1_3_funding_adjacent_scoped_respec(tmp_path / "duplicate_export")

    monkeypatch.setattr(
        v13_export,
        "V13_BUNDLE_CANDIDATES",
        [_bundle("qr_v13_bad_size_bundle_001", ["qr_v13_component_001", "qr_v13_component_002"])],
    )
    with pytest.raises(ValueError, match="exactly 3 components"):
        export_v1_3_funding_adjacent_scoped_respec(tmp_path / "size_export")


def test_v1_3_failure_memory_records_only_failed_rankings(tmp_path) -> None:
    from quantumrandy.v13_funding_adjacent_respec_memory import (
        build_v1_3_funding_adjacent_respec_memory_rows,
        write_v1_3_funding_adjacent_respec_failure_memory,
    )

    source_robustness_dir = "reports/factor_candidate_robustness/research_v1_3_funding_adjacent_respec"
    ranking_csv = tmp_path / "watchlist_robustness_variant_ranking.csv"
    pd.DataFrame(
        [
            {
                "candidate_id": "qr_v13_funding_return_short_corr_001",
                "variant_id": "thr_0p0_long_flat_cap_0p5_calm_vol_lte_1p5",
                "formula": "zscore(corr(funding_rate,ret(close,12),72),120)",
                "conservative_verdict": "blocked_pending_new_hypotheses",
                "intended_scope": "BTCUSDT_4h",
                "failure_reasons": "weak_blind_window",
                "diagnostic_failure_reasons": "sol_avax_concentration",
                "robustness_labels": "fee_fragility|btc_weakness",
                "stress_survival_score": 0.8,
                "stress_survival_count": 12,
                "stress_count": 15,
                "mean_sharpe": 0.6,
                "validation_mean_sharpe": 0.2,
                "blind_mean_sharpe": 0.1,
                "mean_max_dd": 0.2,
                "worst_max_dd": 0.45,
            },
            {
                "candidate_id": "qr_v13_funding_ema_shift_001",
                "variant_id": "thr_0p0_long_short_cap_0p5_calm_vol_lte_1p5",
                "formula": "zscore(sub(ema(funding_rate,12),ema(funding_rate,48)),120)",
                "conservative_verdict": "research_watchlist",
                "intended_scope": "",
                "failure_reasons": "",
                "diagnostic_failure_reasons": "",
                "robustness_labels": "funding_adjacent_locality",
                "stress_survival_count": 15,
                "stress_count": 15,
                "mean_sharpe": 0.7,
                "validation_mean_sharpe": 0.4,
                "blind_mean_sharpe": 0.5,
                "mean_max_dd": 0.2,
                "worst_max_dd": 0.3,
            },
        ]
    ).to_csv(ranking_csv, index=False)

    rows = build_v1_3_funding_adjacent_respec_memory_rows(
        ranking_csv,
        source_robustness_dir=source_robustness_dir,
    )
    manifest = write_v1_3_funding_adjacent_respec_failure_memory(
        ranking_csv,
        tmp_path / "failure_memory",
        source_robustness_dir=source_robustness_dir,
    )

    assert len(rows) == 2
    assert manifest["input_rows"] == 2
    assert manifest["failure_count"] == 1
    failed_row, survivor_row = rows
    assert failed_row["candidate_family"] == "research_v1_3_funding_adjacent_respec_variant"
    assert failed_row["funding_adjacent_status"] == "funding_adjacent_not_independent_non_funding"
    assert failed_row["independence_claim"] == "none_funding_adjacent_locality_probe"
    assert failed_row["intended_scope"] == "BTCUSDT_4h"
    assert failed_row["out_of_scope_policy"] == "diagnostic_only"
    assert failed_row["source_review_dir"] == source_robustness_dir
    assert failed_row["source_robustness_dir"] == source_robustness_dir
    assert failed_row["stress_survival"] == "12/15"
    assert failed_row["passed"] is False
    assert "funding_adjacent_respec" in failed_row["failure_labels"]
    assert "funding_adjacent_family" in failed_row["failure_labels"]
    assert "replication_stress_fragility" in failed_row["failure_labels"]
    assert survivor_row["passed"] is True
    assert survivor_row["intended_scope"] == "BTCUSDT_4h"
    assert "replication_stress_fragility" not in set(str(survivor_row["failure_labels"]).split("|"))

    failure_memory = pd.read_csv(tmp_path / "failure_memory" / "failure_memory.csv")
    assert len(failure_memory) == 1
    failed = failure_memory.iloc[0]
    assert failed["candidate_id"] == "qr_v13_funding_return_short_corr_001::thr_0p0_long_flat_cap_0p5_calm_vol_lte_1p5"
    assert failed["candidate_family"] == "research_v1_3_funding_adjacent_respec_variant"
    assert failed["failed_gates"] == "weak_blind_window"
