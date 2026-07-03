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


def test_v0_9d_failure_memory_maps_btc_eth_and_redundancy_rows(tmp_path) -> None:
    from quantumrandy.v09d_failure_memory import build_v0_9d_failure_memory_rows, write_v0_9d_failure_memory

    review_csv = tmp_path / "factor_candidate_review.csv"
    pd.DataFrame(
        [
            {
                "candidate_id": "qr_v09d_bundle_trend_quality_001",
                "formula": "equal_weight_mean(a,b,c)",
                "formula_family": "scoped_equal_weight_bundle",
                "variant_id": "default",
                "intended_scope": "BTCUSDT_4h",
                "applicability_hypothesis": "BTCUSDT 4h scoped strict candidate-family discovery.",
                "out_of_scope_policy": "diagnostic_only",
                "review_verdict": "blocked_by_conservative_rules",
                "failure_reasons": "weak_validation_window|high_mean_drawdown",
                "mean_sharpe": 0.2,
                "validation_mean_sharpe": -0.1,
                "blind_mean_sharpe": 0.4,
                "mean_max_dd": 0.5,
                "worst_max_dd": 0.75,
            },
            {
                "candidate_id": "qr_v09d_funding_return_long_001",
                "formula": "zscore(corr(funding_rate,ret(close,42),120),72)",
                "formula_family": "funding_return_long_horizon",
                "variant_id": "default",
                "intended_scope": "BTCUSDT_4h",
                "applicability_hypothesis": "BTCUSDT 4h scoped strict candidate-family discovery.",
                "out_of_scope_policy": "diagnostic_only",
                "review_verdict": "research_watchlist",
                "failure_reasons": "",
                "mean_sharpe": 0.7,
                "validation_mean_sharpe": 0.2,
                "blind_mean_sharpe": 0.3,
                "mean_max_dd": 0.2,
                "worst_max_dd": 0.3,
            },
        ]
    ).to_csv(review_csv, index=False)
    diagnostic_csv = tmp_path / "eth_factor_candidate_review.csv"
    pd.DataFrame(
        [
            {
                "candidate_id": "qr_v09d_funding_return_long_001",
                "review_verdict": "blocked_by_conservative_rules",
                "failure_reasons": "weak_blind_window",
                "validation_mean_sharpe": 0.1,
                "blind_mean_sharpe": -0.4,
            }
        ]
    ).to_csv(diagnostic_csv, index=False)
    correlation_csv = tmp_path / "factor_candidate_bundle_redundancy.csv"
    pd.DataFrame(
        [
            {
                "bundle_candidate_id": "qr_v09d_bundle_trend_quality_001",
                "component_count": 3,
                "max_abs_component_corr": 0.88,
                "redundancy_verdict": "redundant_research_memory_only",
            }
        ]
    ).to_csv(correlation_csv, index=False)

    rows = build_v0_9d_failure_memory_rows(
        review_csv,
        source_review_dir="reports/factor_candidate_review/research_v0_9d_btc_primary",
        diagnostic_review_csv=diagnostic_csv,
        source_diagnostic_dir="reports/factor_candidate_review/research_v0_9d_eth_diagnostic",
        correlation_csv=correlation_csv,
        source_correlation_dir="reports/factor_candidate_correlation/research_v0_9d_btc",
    )

    assert len(rows) == 2
    by_id = {row["candidate_id"]: row for row in rows}
    bundle = by_id["qr_v09d_bundle_trend_quality_001"]
    assert bundle["candidate_family"] == "scoped_equal_weight_bundle"
    assert bundle["conservative_verdict"] == "research_memory_only"
    assert "weak_validation_window" in bundle["failure_labels"]
    assert "drawdown_fragility" in bundle["failure_labels"]
    assert "trend_quality_fragility" in bundle["failure_labels"]
    assert "bundle_redundancy" in bundle["failure_labels"]
    assert "component_overlap" in bundle["failure_labels"]

    funding = by_id["qr_v09d_funding_return_long_001"]
    assert funding["conservative_verdict"] == "scoped_watchlist_needs_replication"
    assert funding["passed"] is False
    assert "eth_diagnostic_weakness" in funding["failure_labels"]
    assert "funding_confirmation_fragility" in funding["failure_labels"]

    out = tmp_path / "failure_memory"
    manifest = write_v0_9d_failure_memory(
        review_csv,
        out,
        source_review_dir="reports/factor_candidate_review/research_v0_9d_btc_primary",
        diagnostic_review_csv=diagnostic_csv,
        source_diagnostic_dir="reports/factor_candidate_review/research_v0_9d_eth_diagnostic",
        correlation_csv=correlation_csv,
        source_correlation_dir="reports/factor_candidate_correlation/research_v0_9d_btc",
    )
    assert manifest["artifact_type"] == "quantumrandy_failure_memory"
    assert manifest["failure_count"] == 2
    memory = pd.read_csv(out / "failure_memory.csv")
    assert set(memory["candidate_id"]) == {
        "qr_v09d_bundle_trend_quality_001",
        "qr_v09d_funding_return_long_001",
    }


def test_v0_9d_report_renderer_states_readiness_outcomes() -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "render_v0_9d_report.py"
    spec = importlib.util.spec_from_file_location("render_v0_9d_report", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    review = pd.DataFrame(
        [
            {
                "candidate_id": "qr_v09d_bundle_trend_quality_001",
                "review_verdict": "research_watchlist",
                "intended_scope": "BTCUSDT_4h",
                "mean_sharpe": 0.5,
                "validation_mean_sharpe": 0.2,
                "blind_mean_sharpe": 0.1,
                "failure_reasons": "",
            }
        ]
    )
    diagnostic = pd.DataFrame(
        [
            {
                "candidate_id": "qr_v09d_bundle_trend_quality_001",
                "review_verdict": "blocked_by_conservative_rules",
                "blind_mean_sharpe": -0.2,
                "failure_reasons": "weak_blind_window",
            }
        ]
    )
    redundancy = pd.DataFrame(
        [
            {
                "bundle_candidate_id": "qr_v09d_bundle_trend_quality_001",
                "redundancy_verdict": "diversified_enough_for_research",
                "max_abs_component_corr": 0.4,
                "high_corr_pair_count": 0,
            }
        ]
    )

    assert module._readiness_verdict(review, pd.DataFrame(), redundancy) == "research_1_0_candidate_pending_replication"
    assert module._readiness_verdict(review, diagnostic, redundancy) == "scoped_watchlist_needs_replication"
    assert (
        module._readiness_verdict(
            review.assign(review_verdict="blocked_by_conservative_rules"),
            pd.DataFrame(),
            redundancy,
        )
        == "not_ready_for_research_1_0"
    )

    report = module._render(
        export_manifest={
            "candidate_count": 12,
            "single_factor_count": 9,
            "bundle_count": 3,
            "scope_contract": {"intended_scope": "BTCUSDT_4h", "out_of_scope_policy": "diagnostic_only"},
        },
        candidates=[
            {
                "candidate_id": "qr_v09d_trend_efficiency_001",
                "formula_family": "trend_quality_efficiency",
                "formula": "zscore(div(ret(close,24),div(sub(max(high,48),min(low,48)),close)),96)",
            },
            {
                "candidate_id": "qr_v09d_bundle_trend_quality_001",
                "formula_family": "scoped_equal_weight_bundle",
                "component_candidate_ids": ["qr_v09d_trend_efficiency_001"],
                "combination_method": "equal_weight_mean",
                "formula": "equal_weight_mean(zscore(ret(close,24),96))",
            },
        ],
        btc_sensitivity_summary={"run_count": 240, "candidate_row_count": 2880},
        btc_review_summary={
            "candidate_count": 12,
            "rules": {"scope_mode": "declared"},
            "verdict_counts": {"research_watchlist": 1},
        },
        btc_review=review,
        eth_sensitivity_summary={"run_count": 240, "candidate_row_count": 2880},
        eth_review_summary={
            "candidate_count": 12,
            "rules": {"scope_mode": "declared"},
            "verdict_counts": {"blocked_by_conservative_rules": 12},
        },
        eth_review=diagnostic,
        correlation_summary={
            "high_corr_threshold": 0.8,
            "pairwise_row_count": 66,
            "bundle_verdict_counts": {"diversified_enough_for_research": 1},
        },
        redundancy=redundancy,
        wider_summaries={},
        memory_manifest={"failure_count": 12, "cluster_count": 4},
        memory=pd.DataFrame(
            [{"conservative_verdict": "scoped_watchlist_needs_replication", "failure_labels": "eth_diagnostic_weakness"}]
        ),
        readiness="scoped_watchlist_needs_replication",
    )

    assert "Research v0.9d Strict Candidate-Family Discovery Report" in report
    assert "BTCUSDT_4h" in report
    assert "ETH Diagnostic Review" in report
    assert "Declared Review Mechanics Audit" in report
    assert "`scoped_watchlist_needs_replication`" in report
    assert "No RandyPortfolio implementation" in report
