from __future__ import annotations

import json

import pandas as pd

from quantumrandy.candidate_selector import (
    CandidateSelectorPolicy,
    load_candidate_selector_prompt_context,
    select_research_candidates,
    write_candidate_selector_report,
)
from quantumrandy.failure_memory import build_failure_memory


def test_select_research_candidates_combines_universe_and_portfolio_evidence() -> None:
    leaderboard = [
        {
            "factor_id": "btc_lucky",
            "formula": "zscore(ret(close,6),48)",
            "description": "BTC-only momentum.",
            "passed": True,
            "brutal_score": 70.0,
            "validation_sharpe": 0.5,
            "validation_rank_ic": 0.03,
        },
        {
            "factor_id": "portable_carry",
            "formula": "neg(zscore(funding_rate,42))",
            "description": "Funding carry reversal.",
            "passed": True,
            "brutal_score": 65.0,
            "validation_sharpe": 0.4,
            "validation_rank_ic": 0.02,
        },
    ]
    universe = pd.DataFrame(
        [
            {
                "factor_id": "btc_lucky",
                "formula": "zscore(ret(close,6),48)",
                "pass_rate": 0.2,
                "evaluated_assets": 5,
                "mean_sharpe": -0.1,
                "median_rank_ic": -0.01,
                "failed_assets": "ETHUSDT,SOLUSDT,BNBUSDT,AVAXUSDT",
            },
            {
                "factor_id": "portable_carry",
                "formula": "neg(zscore(funding_rate,42))",
                "pass_rate": 0.8,
                "evaluated_assets": 5,
                "mean_sharpe": 0.3,
                "median_rank_ic": 0.02,
                "failed_assets": "AVAXUSDT",
            },
        ]
    )
    portfolio_universe = pd.DataFrame(
        [
            {
                "portfolio_id": "equal_weight_accepted",
                "weights": "btc_lucky:0.500000,portable_carry:0.500000",
                "pass_rate": 0.4,
                "mean_sharpe": 0.1,
                "robustness_score": 0.2,
            }
        ]
    )

    candidates, clusters, rewrite_targets, manifest = select_research_candidates(
        leaderboard,
        universe_summary=universe,
        portfolio_universe_summary=portfolio_universe,
        policy=CandidateSelectorPolicy(min_cluster_size=1),
    )

    by_factor = {row["factor_id"]: row for row in candidates.to_dict(orient="records")}
    assert by_factor["btc_lucky"]["selector_verdict"] == "deprioritize"
    assert by_factor["btc_lucky"]["rewrite_focus"] == "abandon_or_change_economic_family"
    assert by_factor["portable_carry"]["selector_verdict"] == "keep_for_review"
    assert by_factor["portable_carry"]["portfolio_universe_best_portfolio"] == "equal_weight_accepted"
    assert not rewrite_targets.empty
    assert rewrite_targets.iloc[0]["factor_id"] == "btc_lucky"
    assert not clusters.empty
    assert manifest["safety"]["not_runtime_publish_payload"] is True
    assert manifest["rewrite_target_count"] == 1


def test_select_research_candidates_uses_failure_memory_subtree_hits() -> None:
    failures, failure_clusters, _ = build_failure_memory(
        [
            {"formula": "zscore(ret(close,6),48)", "passed": False, "kill_reasons": ["friction_audit"]},
            {"formula": "zscore(ret(close,12),48)", "passed": False, "kill_reasons": ["lifetime"]},
        ]
    )
    leaderboard = [
        {
            "factor_id": "momentum",
            "formula": "zscore(ret(close,6),48)",
            "passed": True,
            "brutal_score": 50.0,
        }
    ]
    universe = pd.DataFrame(
        [
            {
                "factor_id": "momentum",
                "formula": "zscore(ret(close,6),48)",
                "pass_rate": 0.2,
                "evaluated_assets": 5,
                "mean_sharpe": 0.1,
                "median_rank_ic": 0.0,
                "failed_assets": "ETHUSDT,SOLUSDT,BNBUSDT,AVAXUSDT",
            }
        ]
    )

    candidates, _, _, _ = select_research_candidates(
        leaderboard,
        universe_summary=universe,
        failure_memory=failures,
        failure_clusters=failure_clusters,
    )

    row = candidates.iloc[0].to_dict()
    assert row["selector_verdict"] == "deprioritize"
    assert row["rewrite_focus"] == "avoid_repeated_failed_subtrees"
    assert "zscore(ret(close,n),n)" in row["matched_failed_subtrees"]


def test_write_candidate_selector_report_outputs_files(tmp_path) -> None:
    leaderboard = [
        {
            "factor_id": "carry",
            "formula": "neg(zscore(funding_rate,42))",
            "passed": True,
            "brutal_score": 40.0,
        }
    ]
    universe = pd.DataFrame(
        [
            {
                "factor_id": "carry",
                "formula": "neg(zscore(funding_rate,42))",
                "pass_rate": 0.8,
                "evaluated_assets": 5,
                "mean_sharpe": 0.2,
                "median_rank_ic": 0.01,
                "failed_assets": "",
            }
        ]
    )

    manifest = write_candidate_selector_report(leaderboard, tmp_path, universe_summary=universe)

    assert manifest["artifact_type"] == "quantumrandy_research_candidate_selector"
    assert (tmp_path / "candidate_selector.csv").exists()
    assert (tmp_path / "multi_asset_failure_clusters.csv").exists()
    assert (tmp_path / "rewrite_targets.csv").exists()
    payload = json.loads((tmp_path / "candidate_selector_manifest.json").read_text(encoding="utf-8"))
    assert payload["safety"]["does_not_update_runtime"] is True
    report = (tmp_path / "CANDIDATE_SELECTOR_REPORT.md").read_text(encoding="utf-8")
    assert "research evidence artifact only" in report


def test_write_candidate_selector_report_tolerates_missing_universe_evidence(tmp_path) -> None:
    leaderboard = [
        {
            "factor_id": "unmatched",
            "formula": "zscore(volume,48)",
            "passed": True,
            "brutal_score": 20.0,
        }
    ]

    manifest = write_candidate_selector_report(leaderboard, tmp_path)

    assert manifest["candidate_count"] == 1
    assert manifest["rewrite_target_count"] == 0
    assert manifest["verdict_counts"] == {"needs_evidence": 1}
    rewrite_targets = pd.read_csv(tmp_path / "rewrite_targets.csv")
    assert rewrite_targets.empty
    report = (tmp_path / "CANDIDATE_SELECTOR_REPORT.md").read_text(encoding="utf-8")
    assert "unmatched" in report
    assert "Evidence Gaps" in report


def test_load_candidate_selector_prompt_context_reads_rewrite_targets_and_gaps(tmp_path) -> None:
    leaderboard = [
        {
            "factor_id": "weak",
            "formula": "zscore(ret(close,6),48)",
            "passed": True,
            "brutal_score": 70.0,
        },
        {
            "factor_id": "gap",
            "formula": "zscore(volume,48)",
            "passed": True,
            "brutal_score": 20.0,
        },
    ]
    universe = pd.DataFrame(
        [
            {
                "factor_id": "weak",
                "formula": "zscore(ret(close,6),48)",
                "pass_rate": 0.2,
                "evaluated_assets": 5,
                "mean_sharpe": 0.1,
                "median_rank_ic": 0.0,
                "failed_assets": "ETHUSDT,SOLUSDT",
            }
        ]
    )
    write_candidate_selector_report(leaderboard, tmp_path, universe_summary=universe)

    context = load_candidate_selector_prompt_context(tmp_path, max_rewrite_targets=1, max_evidence_gaps=1)

    assert context["available"] is True
    assert context["rewrite_targets"][0]["factor_id"] == "weak"
    assert context["rewrite_targets"][0]["rewrite_focus"] == "improve_cross_asset_robustness"
    assert context["evidence_gaps"][0]["factor_id"] == "gap"
