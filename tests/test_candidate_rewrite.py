from __future__ import annotations

import json

import pandas as pd

from quantumrandy.candidate_rewrite import (
    CandidateRewritePolicy,
    build_selector_rewrite_candidates,
    load_rewrite_targets,
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
    assert len(candidates) >= 1
    assert not events.empty
    row = candidates.iloc[0].to_dict()
    assert row["source"] == "candidate_selector_rewrite"
    assert row["parent_factor_id"] in {"weak_momentum", "weak_conviction"}
    assert row["hypothesis"]


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
    payload = json.loads((tmp_path / "rewrite" / "selector_rewrite_candidates.json").read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    assert payload[0]["formula"]
    assert payload[0]["factor_id"].startswith("qr_")
    assert (tmp_path / "rewrite" / "selector_rewrite_candidates.csv").exists()
    report = (tmp_path / "rewrite" / "SELECTOR_REWRITE_REPORT.md").read_text(encoding="utf-8")
    assert "research artifact only" in report
