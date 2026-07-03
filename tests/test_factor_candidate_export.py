from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from quantumrandy.factor_candidate_export import export_selector_v082_factor_candidates


def _write_summary(root: Path) -> None:
    root.mkdir(parents=True)
    pd.DataFrame(
        [
            {
                "factor_id": "qr_a2cd9fd69f",
                "parent_factor_id": "qr_7a765d304b",
                "rewrite_generation_source": "llm_rewrite",
                "formula": "zscore(ema(volume,48),120)",
                "highlight_count": 19,
                "llm_true_improved_count": 19,
                "coverage_only_trap_count": 0,
                "sharpe_improved_no_pass_lift_count": 0,
                "best_pass_rate_delta": 0.8,
                "best_mean_sharpe_delta": 0.44211152,
                "mean_pass_rate_delta": 0.8,
                "mean_sharpe_delta": 0.44211152,
                "failed_assets_examples": "BTCUSDT",
            },
            {
                "factor_id": "qr_a2cd9fd69f",
                "parent_factor_id": "qr_4a7fa246c2",
                "rewrite_generation_source": "llm_rewrite",
                "formula": "zscore(ema(volume,48),120)",
                "highlight_count": 5,
                "llm_true_improved_count": 5,
                "coverage_only_trap_count": 0,
                "sharpe_improved_no_pass_lift_count": 0,
                "best_pass_rate_delta": 0.6,
                "best_mean_sharpe_delta": 0.77176916,
                "mean_pass_rate_delta": 0.6,
                "mean_sharpe_delta": 0.77176916,
                "failed_assets_examples": "BTCUSDT",
            },
            {
                "factor_id": "qr_c3ccb8e228",
                "parent_factor_id": "qr_4a7fa246c2",
                "rewrite_generation_source": "llm_rewrite",
                "formula": "zscore(std(close,48),120)",
                "highlight_count": 5,
                "llm_true_improved_count": 5,
                "coverage_only_trap_count": 0,
                "sharpe_improved_no_pass_lift_count": 0,
                "best_pass_rate_delta": 0.6,
                "best_mean_sharpe_delta": 0.84810419,
                "mean_pass_rate_delta": 0.6,
                "mean_sharpe_delta": 0.84810419,
                "failed_assets_examples": "AVAXUSDT",
            },
            {
                "factor_id": "qr_unused",
                "parent_factor_id": "qr_7a765d304b",
                "rewrite_generation_source": "llm_rewrite",
                "formula": "zscore(delta(volume,48),120)",
                "highlight_count": 1,
                "llm_true_improved_count": 1,
                "coverage_only_trap_count": 0,
                "sharpe_improved_no_pass_lift_count": 0,
                "best_pass_rate_delta": 0.2,
                "best_mean_sharpe_delta": 0.1,
                "mean_pass_rate_delta": 0.2,
                "mean_sharpe_delta": 0.1,
                "failed_assets_examples": "BTCUSDT",
            },
        ]
    ).to_csv(root / "selector_pipeline_candidate_evidence_summary.csv", index=False)
    pd.DataFrame(
        [
            {
                "parent_formula_family": "price",
                "candidate_formula_family": "volume_liquidity",
                "negative_count": 19,
                "true_improved_count": 23,
            },
            {
                "parent_formula_family": "funding_interaction",
                "candidate_formula_family": "range_volatility",
                "negative_count": 19,
                "true_improved_count": 36,
            },
        ]
    ).to_csv(root / "selector_pipeline_negative_candidate_summary.csv", index=False)


def test_export_selector_v082_factor_candidates_is_research_only_and_deduplicates_formulas(tmp_path) -> None:
    summary = tmp_path / "summary"
    out = tmp_path / "export"
    _write_summary(summary)

    manifest = export_selector_v082_factor_candidates(
        summary,
        out,
        formulas=["zscore(ema(volume,48),120)", "zscore(std(close,48),120)"],
        created_from_report=summary / "SELECTOR_PIPELINE_EVIDENCE_SUMMARY.md",
    )

    assert manifest["artifact_type"] == "quantumrandy_factor_candidate_export_manifest"
    assert manifest["safety"]["research_only"] is True
    assert manifest["safety"]["not_runtime_publish_payload"] is True
    assert manifest["candidate_count"] == 2
    assert manifest["missing_formulas"] == []

    records = [
        json.loads(line)
        for line in (out / "factor_candidates.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    by_formula = {record["formula"]: record for record in records}
    volume = by_formula["zscore(ema(volume,48),120)"]
    assert volume["artifact_type"] == "quantumrandy_factor_candidate_export"
    assert volume["research_only"] is True
    assert volume["not_runtime_publish_payload"] is True
    assert volume["candidate_id"] == "qr_a2cd9fd69f"
    assert volume["llm_true_improved_count"] == 24
    assert volume["highlight_count"] == 24
    assert volume["parent_factor_id"] == "qr_7a765d304b"
    assert volume["parent_formula_family"] == "price"
    assert volume["formula_family"] == "volume_liquidity"
    assert volume["negative_family_conflict"] is True
    assert volume["required_features"] == ["volume"]
    assert volume["candidate_tier"] == "primary"
    assert "positive smoothed participation" in volume["conflict_notes"]
    assert volume["evidence_parent_factor_ids"] == "qr_4a7fa246c2|qr_7a765d304b"

    volatility = by_formula["zscore(std(close,48),120)"]
    assert volatility["required_features"] == ["close"]
    assert volatility["formula_family"] == "range_volatility"
    assert volatility["negative_family_conflict"] is True
    assert "positive realized-volatility" in volatility["conflict_notes"]

    csv = pd.read_csv(out / "factor_candidates.csv")
    assert set(csv["formula"]) == {"zscore(ema(volume,48),120)", "zscore(std(close,48),120)"}
    report = (out / "FACTOR_CANDIDATE_EXPORT.md").read_text(encoding="utf-8")
    assert "research-only factor-candidate export" in report
    assert "not a runtime publish payload" in report


def test_export_selector_v082_factor_candidates_declares_scope_and_future_portfolio_contract(tmp_path) -> None:
    summary = tmp_path / "summary"
    out = tmp_path / "export"
    _write_summary(summary)

    manifest = export_selector_v082_factor_candidates(
        summary,
        out,
        formulas=["zscore(ema(volume,48),120)"],
        intended_scope="BTCUSDT_4h",
        applicability_hypothesis="BTCUSDT 4h participation factor for scoped research only.",
        out_of_scope_policy="diagnostic_only",
        created_from_report=summary / "SELECTOR_PIPELINE_EVIDENCE_SUMMARY.md",
    )

    records = [
        json.loads(line)
        for line in (out / "factor_candidates.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    record = records[0]

    assert manifest["scope_contract"]["intended_scope"] == "BTCUSDT_4h"
    assert manifest["future_portfolio_interface"]["consumer_project"] == "RandyPortfolio"
    assert manifest["future_portfolio_interface"]["status"] == "interface_only_not_implemented"
    assert manifest["safety"]["does_not_create_portfolio_scheduler"] is True
    assert record["intended_scope"] == "BTCUSDT_4h"
    assert record["applicability_hypothesis"] == "BTCUSDT 4h participation factor for scoped research only."
    assert record["out_of_scope_policy"] == "diagnostic_only"
    assert record["portfolio_interface_contract"]["consumer_project"] == "RandyPortfolio"
    assert record["portfolio_interface_contract"]["allowed_use"] == "research_artifact_input"
    assert record["portfolio_interface_contract"]["forbidden_use"] == "runtime_allocation_or_live_execution"

    csv = pd.read_csv(out / "factor_candidates.csv")
    assert csv.iloc[0]["intended_scope"] == "BTCUSDT_4h"
    report = (out / "FACTOR_CANDIDATE_EXPORT.md").read_text(encoding="utf-8")
    assert "Intended scope" in report
    assert "RandyPortfolio interface contract" in report
