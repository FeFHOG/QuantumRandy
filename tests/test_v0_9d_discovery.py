from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pandas as pd

from quantumrandy.expression import parse_formula
from quantumrandy.factor_candidate_export import PRIMARY_SELECTOR_V082_FORMULAS, V09B_FUNDING_PRESSURE_FORMULAS
from quantumrandy.v09c_bundle_export import V09C_SINGLE_FACTOR_CANDIDATES
from quantumrandy.v09d_discovery_export import (
    V09D_BUNDLE_CANDIDATES,
    V09D_SINGLE_FACTOR_CANDIDATES,
    export_v0_9d_strict_candidate_discovery,
)


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_export_v0_9d_strict_candidate_discovery_is_scoped_research_only(tmp_path) -> None:
    out = tmp_path / "v09d_export"

    manifest = export_v0_9d_strict_candidate_discovery(out)

    assert manifest["artifact_type"] == "quantumrandy_factor_candidate_export_manifest"
    assert manifest["research_checkpoint"] == "v0.9d"
    assert manifest["candidate_family"] == "strict_candidate_family_discovery"
    assert manifest["candidate_count"] == len(V09D_SINGLE_FACTOR_CANDIDATES) + len(V09D_BUNDLE_CANDIDATES)
    assert manifest["single_factor_count"] == 9
    assert manifest["bundle_count"] == 3
    assert manifest["scope_contract"]["intended_scope"] == "BTCUSDT_4h"
    assert manifest["scope_contract"]["out_of_scope_policy"] == "diagnostic_only"
    assert manifest["safety"]["research_only"] is True
    assert manifest["safety"]["not_runtime_publish_payload"] is True
    assert manifest["future_portfolio_interface"]["status"] == "interface_only_not_implemented"

    records = _jsonl(out / "factor_candidates.jsonl")
    bundle_records = _jsonl(out / "bundle_candidates.jsonl")
    assert len(records) == 12
    assert len(bundle_records) == 3

    single_records = [record for record in records if not record.get("component_formulas")]
    assert len(single_records) == 9
    single_formulas = {record["formula"] for record in single_records}
    assert single_formulas.isdisjoint(set(PRIMARY_SELECTOR_V082_FORMULAS))
    assert single_formulas.isdisjoint(set(V09B_FUNDING_PRESSURE_FORMULAS))
    assert single_formulas.isdisjoint({item["formula"] for item in V09C_SINGLE_FACTOR_CANDIDATES})

    allowed_fields = {"open", "high", "low", "close", "volume", "funding_rate"}
    disallowed_functions = {"rank", "skew", "kurtosis", "clip", "winsorize", "delay"}

    for record in records:
        assert record["artifact_type"] == "quantumrandy_factor_candidate_export"
        assert record["research_checkpoint"] == "v0.9d"
        assert record["research_only"] is True
        assert record["not_runtime_publish_payload"] is True
        assert record["intended_scope"] == "BTCUSDT_4h"
        assert record["out_of_scope_policy"] == "diagnostic_only"
        assert record["randyslab_eval_profile"] == "strict4h_v1"
        assert record["portfolio_interface_contract"]["forbidden_use"] == "runtime_allocation_or_live_execution"
        assert set(record["required_features"]).issubset(allowed_fields)
        assert record["hypothesis"]
        assert record["expected_failure_mode"]
        formulas = record.get("component_formulas") or [record["formula"]]
        for formula in formulas:
            parse_formula(formula)
            assert not any(f"{name}(" in formula for name in disallowed_functions)

    for record in bundle_records:
        assert record["candidate_id"].startswith("qr_v09d_bundle_")
        assert record["formula_family"] == "scoped_equal_weight_bundle"
        assert record["combination_method"] == "equal_weight_mean"
        assert len(record["component_formulas"]) == 3
        assert len(record["component_candidate_ids"]) == 3
        assert record["formula"].startswith("equal_weight_mean(")

    csv = pd.read_csv(out / "factor_candidates.csv")
    assert len(csv) == 12
    assert set(csv["intended_scope"]) == {"BTCUSDT_4h"}
    assert "component_formulas" in csv.columns

    report = (out / "FACTOR_CANDIDATE_EXPORT.md").read_text(encoding="utf-8")
    assert "Research v0.9d" in report
    assert "BTCUSDT_4h" in report
    assert "not a runtime publish payload" in report
