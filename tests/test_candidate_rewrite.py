from __future__ import annotations

import json

import pandas as pd

from quantumrandy.candidate_rewrite import (
    CandidateRewritePolicy,
    build_selector_rewrite_candidates,
    load_rewrite_targets,
    load_selector_forbidden_subtrees,
    write_selector_rewrite_report,
)
from quantumrandy.candidate_selector import write_candidate_selector_report
from quantumrandy.llm import FormulaGenerator


def _selector_artifact(tmp_path) -> None:
    leaderboard = [
        {
            "factor_id": "weak_momentum",
            "formula": "zscore(ret(close,6),48)",
            "passed": True,
            "brutal_score": 60.0,
        },
        {
            "factor_id": "weak_conviction",
            "formula": "zscore(corr(sub(close,open),volume,48),72)",
            "passed": True,
            "brutal_score": 40.0,
        },
    ]
    universe = pd.DataFrame(
        [
            {
                "factor_id": "weak_momentum",
                "formula": "zscore(ret(close,6),48)",
                "pass_rate": 0.2,
                "evaluated_assets": 5,
                "mean_sharpe": 0.1,
                "median_rank_ic": 0.0,
                "failed_assets": "ETHUSDT,SOLUSDT",
            },
            {
                "factor_id": "weak_conviction",
                "formula": "zscore(corr(sub(close,open),volume,48),72)",
                "pass_rate": 0.0,
                "evaluated_assets": 5,
                "mean_sharpe": -0.2,
                "median_rank_ic": -0.01,
                "failed_assets": "BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,AVAXUSDT",
            },
        ]
    )
    write_candidate_selector_report(leaderboard, tmp_path, universe_summary=universe)


def test_load_rewrite_targets_reads_selector_directory(tmp_path) -> None:
    _selector_artifact(tmp_path)

    targets = load_rewrite_targets(tmp_path, max_targets=1)

    assert len(targets) == 1
    assert targets[0]["factor_id"] == "weak_momentum"
    assert targets[0]["selector_verdict"] == "rewrite"


def test_build_selector_rewrite_candidates_uses_local_generator(tmp_path) -> None:
    _selector_artifact(tmp_path)
    targets = load_rewrite_targets(tmp_path, max_targets=2)
    generator = FormulaGenerator(use_llm=False)

    candidates, events, manifest = build_selector_rewrite_candidates(
        targets,
        generator,
        policy=CandidateRewritePolicy(max_targets=2, candidates_per_target=2),
    )

    assert manifest["artifact_type"] == "quantumrandy_selector_rewrite_candidates"
    assert manifest["safety"]["not_runtime_publish_payload"] is True
    assert manifest["llm_rewrite_accepted"] == 0
    assert manifest["fallback_rewrite_accepted"] >= 1
    assert manifest["event_source_counts"]
    assert manifest["candidate_generation_source_counts"].get("local_rewrite", 0) >= 1
    assert len(candidates) >= 1
    assert not events.empty
    row = candidates.iloc[0].to_dict()
    assert row["source"] == "candidate_selector_rewrite"
    assert row["rewrite_generation_source"] == "local_rewrite"
    assert row["parent_factor_id"] in {"weak_momentum", "weak_conviction"}
    assert row["hypothesis"]


def test_load_selector_forbidden_subtrees_reads_clusters_and_matched_failures(tmp_path) -> None:
    _selector_artifact(tmp_path)
    pd.DataFrame(
        [
            {
                "subtree": "zscore(ret(close,6),48)",
                "count": 3,
                "avg_universe_pass_rate": 0.0,
                "avg_universe_mean_sharpe": -0.1,
            }
        ]
    ).to_csv(tmp_path / "multi_asset_failure_clusters.csv", index=False)
    targets = pd.read_csv(tmp_path / "rewrite_targets.csv")
    targets["matched_failed_subtrees"] = "corr(sub(close,open),volume,48)|zscore(ret(close,6),48)"
    targets.to_csv(tmp_path / "rewrite_targets.csv", index=False)

    forbidden = load_selector_forbidden_subtrees(tmp_path, max_subtrees=3)

    assert forbidden == [
        "zscore(ret(close,6),48)",
        "corr(sub(close,open),volume,48)",
    ]


class _RecordingRewriteGenerator(FormulaGenerator):
    def __init__(self) -> None:
        super().__init__(use_llm=False)
        self.last_forbidden: list[str] = []
        self.last_disallowed: list[str] = []
        self.last_allow_local_fallback = True
        self.last_failure_detail = {}

    def rewrite(
        self,
        formula,
        failed_gates,
        failure_detail,
        count,
        forbidden,
        disallowed_formulas=None,
        allow_local_fallback=True,
    ):
        self.last_forbidden = list(forbidden)
        self.last_disallowed = list(disallowed_formulas or [])
        self.last_allow_local_fallback = allow_local_fallback
        self.last_failure_detail = failure_detail
        proposal = "neg(zscore(funding_rate,42))"
        self.descriptions[proposal] = "Funding pressure rewrite for broad cross-asset carry regime evidence."
        self.proposal_metadata[proposal] = {
            "hypothesis": "Funding crowding can reverse across major perpetual markets.",
            "expected_edge": "Funding extremes can flag crowded carry that unwinds across assets.",
            "expected_failure_mode": "Persistent trend regimes may overwhelm funding mean reversion.",
            "rewrite_plan_if_killed": "Blend with volatility or liquidity regime evidence.",
        }
        self.events.append({"source": "recording_rewrite", "requested": count, "accepted": 1, "error": None})
        return [proposal]


class _FailingThenLocalRewriteGenerator(FormulaGenerator):
    def __init__(self) -> None:
        super().__init__(use_llm=False)

    def rewrite(
        self,
        formula,
        failed_gates,
        failure_detail,
        count,
        forbidden,
        disallowed_formulas=None,
        allow_local_fallback=True,
    ):
        proposal = "neg(zscore(funding_rate,42))"
        self.descriptions[proposal] = "Funding pressure rewrite for broad cross-asset carry regime evidence."
        self.proposal_metadata[proposal] = {
            "hypothesis": "Funding crowding can reverse across major perpetual markets.",
            "expected_edge": "Funding extremes can flag crowded carry that unwinds across assets.",
            "expected_failure_mode": "Persistent trend regimes may overwhelm funding mean reversion.",
            "rewrite_plan_if_killed": "Blend with volatility or liquidity regime evidence.",
        }
        self.events.extend(
            [
                {
                    "source": "rewrite_fallback",
                    "requested": count,
                    "accepted": 0,
                    "error": "LLM request failed after 3 attempts: proxy connection blocked by sandbox",
                },
                {"source": "local_rewrite", "requested": count, "accepted": 1, "error": ""},
            ]
        )
        return [proposal]


class _RejectedThenAcceptedRewriteGenerator(FormulaGenerator):
    def __init__(self) -> None:
        super().__init__(use_llm=False)

    def rewrite(
        self,
        formula,
        failed_gates,
        failure_detail,
        count,
        forbidden,
        disallowed_formulas=None,
        allow_local_fallback=True,
    ):
        proposal = "zscore(ret(close,24),96)"
        self.descriptions[proposal] = "Slower price pressure rewrite with cross-asset momentum rationale."
        self.proposal_metadata[proposal] = {
            "hypothesis": "Smoother price pressure can transfer better across liquid crypto perpetuals.",
            "expected_edge": "A slower return horizon can reduce noisy short-term reversals.",
            "expected_failure_mode": "It may fail in mean-reverting chop.",
            "rewrite_plan_if_killed": "Test a sign flip or abandon price-only momentum.",
        }
        self.events.extend(
            [
                {
                    "source": "rewrite_validator",
                    "accepted": 1,
                    "rejected": [
                        {
                            "formula": "zscore(volume,96)",
                            "reason": "candidate family is blocked by negative selector memory (price->volume_liquidity)",
                        },
                        {
                            "formula": "zscore(volume,120)",
                            "reason": "candidate family is blocked by negative selector memory (price->volume_liquidity)",
                        },
                        {
                            "formula": "neg(zscore(std(close,24),120))",
                            "reason": "copies disallowed failed formula",
                        },
                    ],
                },
                {"source": "llm_rewrite", "requested": count, "accepted": 1, "error": ""},
            ]
        )
        return [proposal]


def test_selector_rewrite_merges_selector_forbidden_subtrees_into_generation(tmp_path) -> None:
    targets = [
        {
            "factor_id": "weak_price",
            "formula": "zscore(ret(close,6),48)",
            "selector_verdict": "rewrite",
            "rewrite_focus": "improve_cross_asset_robustness",
            "universe_pass_rate": 0.2,
            "universe_mean_sharpe": 0.3,
            "failed_assets": "BTCUSDT,ETHUSDT",
            "matched_failed_subtrees": "zscore(ret(close,6),48)",
        }
    ]
    generator = _RecordingRewriteGenerator()

    candidates, events, manifest = build_selector_rewrite_candidates(
        targets,
        generator,
        policy=CandidateRewritePolicy(max_targets=1, candidates_per_target=1),
        forbidden=["zscore(close,48)"],
        selector_forbidden_subtrees=["corr(funding_rate,volume,72)"],
    )

    assert generator.last_forbidden == [
        "zscore(close,48)",
        "corr(funding_rate,volume,72)",
        "zscore(ret(close,6),48)",
    ]
    assert generator.last_disallowed == ["zscore(ret(close,6),48)"]
    assert manifest["selector_forbidden_subtree_count"] == 1
    assert manifest["known_selector_formula_count"] == 1
    assert candidates.iloc[0]["selector_forbidden_subtree_count"] == 3
    assert candidates.iloc[0]["known_selector_formula_count"] == 1
    assert "corr(funding_rate,volume,72)" in candidates.iloc[0]["selector_forbidden_subtrees"]
    assert "zscore(ret(close,6),48)" in candidates.iloc[0]["parent_matched_failed_subtrees"]
    assert events.iloc[0]["selector_forbidden_subtree_count"] == 3
    assert candidates.iloc[0]["rewrite_failed_gates"] == (
        "cross_asset_profitability,cross_asset_robustness,lifetime"
    )
    assert generator.last_failure_detail["universe"]["mean_sharpe"] == 0.3
    assert generator.last_failure_detail["rewrite_objective"]["target_pass_rate_delta"] == "> 0"
    assert generator.last_failure_detail["rewrite_objective"]["target_mean_sharpe_delta"] == ">= 0"
    assert generator.last_failure_detail["rewrite_objective"]["parent_formula_family"] == "price"
    assert generator.last_failure_detail["rewrite_objective"]["max_pure_funding_candidates"] == 0
    assert "Pure funding-rate-only rewrites are disallowed" in (
        generator.last_failure_detail["rewrite_objective"]["formula_family_constraint"]
    )
    assert "BTCUSDT,ETHUSDT" in generator.last_failure_detail["rewrite_objective"]["failed_assets_instruction"]
    assert candidates.iloc[0]["parent_formula_family"] == "price"
    assert candidates.iloc[0]["max_pure_funding_candidates"] == 0
    assert events.iloc[0]["parent_formula_family"] == "price"
    assert events.iloc[0]["max_pure_funding_candidates"] == 0


def test_selector_rewrite_events_summarize_rejected_candidates(tmp_path) -> None:
    targets = [
        {
            "factor_id": "weak_price",
            "formula": "zscore(ret(close,6),48)",
            "selector_verdict": "rewrite",
            "rewrite_focus": "improve_cross_asset_robustness",
            "universe_pass_rate": 0.2,
            "universe_mean_sharpe": 0.3,
        }
    ]
    generator = _RejectedThenAcceptedRewriteGenerator()

    candidates, events, manifest = build_selector_rewrite_candidates(
        targets,
        generator,
        policy=CandidateRewritePolicy(max_targets=1, candidates_per_target=1, allow_local_fallback=False),
    )

    validator = events[events["source"] == "rewrite_validator"].iloc[0]
    assert validator["rejected_count"] == 3
    assert (
        "candidate family is blocked by negative selector memory (price->volume_liquidity):2"
        in validator["rejected_reason_mix"]
    )
    assert "copies disallowed failed formula:1" in validator["rejected_reason_mix"]
    assert "zscore(volume,96): candidate family is blocked" in validator["rejected_formula_examples"]
    assert len(candidates) == 1
    assert manifest["llm_rewrite_accepted"] == 1


def test_selector_rewrite_allows_one_pure_funding_rewrite_for_funding_parent(tmp_path) -> None:
    targets = [
        {
            "factor_id": "weak_funding",
            "formula": "neg(zscore(sma(funding_rate,48),120))",
            "selector_verdict": "rewrite",
            "rewrite_focus": "improve_cross_asset_robustness",
            "universe_pass_rate": 0.2,
            "universe_mean_sharpe": 0.3,
            "failed_assets": "BTCUSDT,ETHUSDT",
        }
    ]
    generator = _RecordingRewriteGenerator()

    candidates, events, _ = build_selector_rewrite_candidates(
        targets,
        generator,
        policy=CandidateRewritePolicy(max_targets=1, candidates_per_target=1),
    )

    assert generator.last_failure_detail["rewrite_objective"]["parent_formula_family"] == "pure_funding"
    assert generator.last_failure_detail["rewrite_objective"]["max_pure_funding_candidates"] == 1
    assert candidates.iloc[0]["parent_formula_family"] == "pure_funding"
    assert events.iloc[0]["max_pure_funding_candidates"] == 1


def test_selector_rewrite_policy_can_disable_local_fallback(tmp_path) -> None:
    targets = [
        {
            "factor_id": "weak_price",
            "formula": "zscore(ret(close,6),48)",
            "selector_verdict": "rewrite",
            "rewrite_focus": "improve_cross_asset_robustness",
            "universe_pass_rate": 0.2,
            "universe_mean_sharpe": 0.3,
        }
    ]
    generator = _RecordingRewriteGenerator()

    candidates, _, manifest = build_selector_rewrite_candidates(
        targets,
        generator,
        policy=CandidateRewritePolicy(max_targets=1, candidates_per_target=1, allow_local_fallback=False),
    )

    assert generator.last_allow_local_fallback is False
    assert manifest["policy"]["allow_local_fallback"] is False
    assert manifest["allow_local_fallback"] is False
    assert candidates.iloc[0]["rewrite_generation_source"] == ""


def test_write_selector_rewrite_report_outputs_leaderboard_style_json(tmp_path) -> None:
    _selector_artifact(tmp_path / "selector")
    targets = load_rewrite_targets(tmp_path / "selector", max_targets=1)
    generator = FormulaGenerator(use_llm=False)

    manifest = write_selector_rewrite_report(
        targets,
        generator,
        tmp_path / "rewrite",
        policy=CandidateRewritePolicy(max_targets=1, candidates_per_target=1),
    )

    assert manifest["candidate_count"] == 1
    assert manifest["llm_rewrite_accepted"] == 0
    assert manifest["fallback_rewrite_accepted"] == 1
    assert manifest["candidate_generation_source_counts"] == {"local_rewrite": 1}
    payload = json.loads((tmp_path / "rewrite" / "selector_rewrite_candidates.json").read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    assert payload[0]["formula"]
    assert payload[0]["factor_id"].startswith("qr_")
    assert (tmp_path / "rewrite" / "selector_rewrite_candidates.csv").exists()
    report = (tmp_path / "rewrite" / "SELECTOR_REWRITE_REPORT.md").read_text(encoding="utf-8")
    assert "research artifact only" in report
    assert "LLM rewrite accepted" in report


def test_selector_rewrite_manifest_summarizes_llm_errors(tmp_path) -> None:
    _selector_artifact(tmp_path / "selector")
    targets = load_rewrite_targets(tmp_path / "selector", max_targets=1)
    generator = _FailingThenLocalRewriteGenerator()

    manifest = write_selector_rewrite_report(
        targets,
        generator,
        tmp_path / "rewrite",
        policy=CandidateRewritePolicy(max_targets=1, candidates_per_target=1),
    )

    assert manifest["llm_error_count"] == 1
    assert manifest["llm_error_summary"] == [
        "LLM request failed after 3 attempts: proxy connection blocked by sandbox"
    ]
    report = (tmp_path / "rewrite" / "SELECTOR_REWRITE_REPORT.md").read_text(encoding="utf-8")
    assert "LLM Error Summary" in report
    assert "proxy connection blocked by sandbox" in report


def test_selector_rewrite_disallows_known_selector_parent_formulas(tmp_path) -> None:
    targets = [
        {
            "factor_id": "weak_price",
            "formula": "zscore(ret(close,6),48)",
            "selector_verdict": "rewrite",
            "rewrite_focus": "improve_cross_asset_robustness",
            "universe_pass_rate": 0.2,
            "universe_mean_sharpe": 0.1,
        },
        {
            "factor_id": "weak_volume",
            "formula": "zscore(corr(sub(close,open),volume,48),72)",
            "selector_verdict": "rewrite",
            "rewrite_focus": "improve_cross_asset_robustness",
            "universe_pass_rate": 0.2,
            "universe_mean_sharpe": 0.3,
        },
    ]
    generator = FormulaGenerator(use_llm=False)

    candidates, events, manifest = build_selector_rewrite_candidates(
        targets,
        generator,
        policy=CandidateRewritePolicy(max_targets=1, candidates_per_target=1),
    )

    assert manifest["known_selector_formula_count"] == 2
    assert events.iloc[0]["known_selector_formula_count"] == 2
    assert events.iloc[0]["disallowed_formula_count"] == 2
    assert candidates.iloc[0]["formula"] not in manifest["known_selector_formulas"]
