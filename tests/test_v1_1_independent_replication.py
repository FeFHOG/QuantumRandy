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
