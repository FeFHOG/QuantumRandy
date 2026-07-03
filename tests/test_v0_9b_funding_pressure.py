from __future__ import annotations

import json

import pandas as pd

from quantumrandy import factor_candidate_export as fce


def test_export_v0_9b_funding_pressure_candidates_is_scoped_and_outside_selector_v082(tmp_path) -> None:
    out = tmp_path / "funding_export"

    manifest = fce.export_v0_9b_funding_pressure_candidates(out)

    assert manifest["artifact_type"] == "quantumrandy_factor_candidate_export_manifest"
    assert manifest["candidate_family"] == "funding_pressure_crowding_mean_reversion"
    assert manifest["candidate_count"] == len(fce.V09B_FUNDING_PRESSURE_FORMULAS)
    assert manifest["scope_contract"]["intended_scope"] == "BTCUSDT_4h"
    assert manifest["scope_contract"]["out_of_scope_policy"] == "diagnostic_only"
    assert manifest["safety"]["research_only"] is True
    assert manifest["safety"]["not_runtime_publish_payload"] is True
    assert manifest["safety"]["no_live_execution"] is True
    assert manifest["future_portfolio_interface"]["status"] == "interface_only_not_implemented"

    records = [
        json.loads(line)
        for line in (out / "factor_candidates.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    formulas = {record["formula"] for record in records}
    assert formulas == set(fce.V09B_FUNDING_PRESSURE_FORMULAS)
    assert formulas.isdisjoint(set(fce.PRIMARY_SELECTOR_V082_FORMULAS))

    for record in records:
        assert record["artifact_type"] == "quantumrandy_factor_candidate_export"
        assert record["research_only"] is True
        assert record["not_runtime_publish_payload"] is True
        assert record["candidate_id"].startswith("qr_v09b_funding_")
        assert record["formula_family"] == "funding_pressure_crowding"
        assert record["intended_scope"] == "BTCUSDT_4h"
        assert "funding pressure" in record["applicability_hypothesis"].lower()
        assert record["out_of_scope_policy"] == "diagnostic_only"
        assert record["hypothesis"]
        assert "trend" in record["expected_failure_mode"].lower()
        assert "funding_rate" in record["required_features"]
        assert record["randyslab_eval_profile"] == "strict4h_v1"
        assert record["portfolio_interface_contract"]["forbidden_use"] == "runtime_allocation_or_live_execution"

    csv = pd.read_csv(out / "factor_candidates.csv")
    assert set(csv["formula"]) == formulas
    assert set(csv["intended_scope"]) == {"BTCUSDT_4h"}

    report = (out / "FACTOR_CANDIDATE_EXPORT.md").read_text(encoding="utf-8")
    assert "Funding Pressure" in report
    assert "BTCUSDT_4h" in report
    assert "not a runtime publish payload" in report


def test_v0_9b_failure_memory_maps_declared_review_rows(tmp_path) -> None:
    from quantumrandy.v09b_failure_memory import build_v0_9b_failure_memory_rows, write_v0_9b_failure_memory

    review_csv = tmp_path / "factor_candidate_review.csv"
    pd.DataFrame(
        [
            {
                "candidate_id": "qr_v09b_funding_001",
                "formula": "neg(zscore(funding_rate,72))",
                "intended_scope": "BTCUSDT_4h",
                "applicability_hypothesis": "BTCUSDT funding pressure can mark crowding.",
                "out_of_scope_policy": "diagnostic_only",
                "review_verdict": "blocked_by_conservative_rules",
                "failure_reasons": "weak_validation_window|high_mean_drawdown|low_positive_row_share",
                "mean_sharpe": 0.1,
                "validation_mean_sharpe": -0.2,
                "blind_mean_sharpe": 0.3,
                "mean_max_dd": 0.5,
                "worst_max_dd": 0.9,
            }
        ]
    ).to_csv(review_csv, index=False)

    rows = build_v0_9b_failure_memory_rows(
        review_csv,
        source_review_dir="reports/factor_candidate_review/research_v0_9b_funding_pressure_btc_declared",
    )

    assert len(rows) == 1
    row = rows[0]
    assert row["passed"] is False
    assert row["candidate_family"] == "funding_pressure_crowding_mean_reversion"
    assert row["intended_scope"] == "BTCUSDT_4h"
    assert row["conservative_verdict"] == "blocked_pending_new_hypotheses"
    assert "weak_validation_window" in row["failure_labels"]
    assert "trend_persistence_risk" in row["failure_labels"]
    assert row["kill_reasons"] == ["weak_validation_window", "high_mean_drawdown", "low_positive_row_share"]

    out = tmp_path / "failure_memory"
    manifest = write_v0_9b_failure_memory(
        review_csv,
        out,
        source_review_dir="reports/factor_candidate_review/research_v0_9b_funding_pressure_btc_declared",
    )
    assert manifest["artifact_type"] == "quantumrandy_failure_memory"
    assert manifest["failure_count"] == 1
    memory = pd.read_csv(out / "failure_memory.csv")
    assert memory.iloc[0]["candidate_family"] == "funding_pressure_crowding_mean_reversion"
    report = (out / "FAILURE_MEMORY_REPORT.md").read_text(encoding="utf-8")
    assert "Failed formulas" in report
