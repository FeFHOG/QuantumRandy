from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from quantumrandy.expression import parse_formula
from quantumrandy.v13_funding_adjacent_respec_export import (
    V13_BUNDLE_CANDIDATES,
    V13_EXCLUDED_RESEARCH10_SURVIVOR,
    V13_SINGLE_FACTOR_CANDIDATES,
    export_v1_3_funding_adjacent_scoped_respec,
)


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


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

    report = (out / "FACTOR_CANDIDATE_EXPORT.md").read_text(encoding="utf-8")
    assert "Research v1.3" in report
    assert "funding-adjacent scoped re-spec" in report
    assert "not a runtime publish payload" in report
    assert "not independent non-funding replication" in report
