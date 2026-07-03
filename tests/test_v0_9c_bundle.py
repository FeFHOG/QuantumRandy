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
