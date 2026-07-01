from __future__ import annotations

import json

import pandas as pd

from quantumrandy.dashboard import build_research_review_payload


def test_research_review_payload_reads_artifact_summaries(tmp_path) -> None:
    reports = tmp_path / "reports"
    out = reports / "research_live"
    out.mkdir(parents=True)

    admission = reports / "admission"
    admission.mkdir()
    pd.DataFrame(
        [
            {"factor_id": "carry", "admission_status": "approve", "admission_score": 100.0, "failed_rules": ""},
            {"factor_id": "noisy", "admission_status": "reject", "admission_score": 40.0, "failed_rules": "brutal_pass"},
            {"factor_id": "mixed", "admission_status": "review", "admission_score": 80.0, "failed_rules": "validation_rank_ic"},
        ]
    ).to_csv(admission / "admission_decisions.csv", index=False)

    failure = reports / "failure_memory"
    failure.mkdir()
    pd.DataFrame(
        [
            {"formula": "zscore(ret(close,6),48)", "failed_gates": "predictive_power"},
            {"formula": "zscore(ret(close,12),48)", "failed_gates": "friction_audit"},
        ]
    ).to_csv(failure / "failure_memory.csv", index=False)
    pd.DataFrame(
        [
            {"subtree": "ret(close,6)", "count": 3, "failed_gates": "predictive_power"},
            {"subtree": "zscore(funding_rate,12)", "count": 1, "failed_gates": "homogeneity"},
        ]
    ).to_csv(failure / "failure_clusters.csv", index=False)

    portfolio = reports / "portfolio_walk_forward"
    portfolio.mkdir()
    pd.DataFrame(
        [
            {
                "portfolio_id": "equal_weight_accepted",
                "survival_rate": 0.75,
                "windows": 4,
                "test_sharpe_median": 0.4,
                "test_rank_ic_median": 0.02,
            },
            {
                "portfolio_id": "sharpe_weight_accepted",
                "survival_rate": 0.25,
                "windows": 4,
                "test_sharpe_median": -0.1,
                "test_rank_ic_median": 0.0,
            },
        ]
    ).to_csv(portfolio / "portfolio_walk_forward_summary.csv", index=False)

    data_readiness = reports / "data_quality"
    data_readiness.mkdir()
    pd.DataFrame(
        [
            {
                "symbol": "BTCUSDT",
                "status": "ready",
                "ready": True,
                "research_coverage_ratio": 1.0,
                "ohlcv_missing_bars": 0,
                "funding_alignment_coverage": 1.0,
                "funding_max_staleness_hours": 8.0,
            },
            {
                "symbol": "ETHUSDT",
                "status": "incomplete",
                "ready": False,
                "research_coverage_ratio": 0.8,
                "ohlcv_missing_bars": 12,
                "funding_alignment_coverage": 0.9,
                "funding_max_staleness_hours": 16.0,
            },
        ]
    ).to_csv(data_readiness / "data_readiness.csv", index=False)

    universe = reports / "universe_archive_eval"
    universe.mkdir()
    pd.DataFrame(
        [
            {
                "factor_id": "carry",
                "formula": "neg(zscore(funding_rate,42))",
                "asset_count": 5,
                "pass_rate": 0.6,
                "mean_sharpe": 0.4,
                "median_rank_ic": 0.02,
                "robustness_score": 1.2,
            },
            {
                "factor_id": "trend",
                "formula": "zscore(close,48)",
                "asset_count": 5,
                "pass_rate": 0.2,
                "mean_sharpe": 0.1,
                "median_rank_ic": 0.0,
                "robustness_score": -0.5,
            },
        ]
    ).to_csv(universe / "universe_summary.csv", index=False)

    portfolio_universe = reports / "portfolio_universe_archive_eval"
    portfolio_universe.mkdir()
    pd.DataFrame(
        [
            {
                "portfolio_id": "equal_weight_accepted",
                "asset_count": 5,
                "pass_rate": 0.4,
                "mean_sharpe": 0.2,
                "median_rank_ic": 0.01,
                "robustness_score": 0.5,
            },
            {
                "portfolio_id": "sharpe_weight_accepted",
                "asset_count": 5,
                "pass_rate": 0.0,
                "mean_sharpe": -0.1,
                "median_rank_ic": -0.01,
                "robustness_score": -1.0,
            },
        ]
    ).to_csv(portfolio_universe / "portfolio_universe_summary.csv", index=False)

    research = reports / "research_live"
    (research / "pareto_archive.json").write_text(
        json.dumps(
            {
                "artifact_type": "quantumrandy_pareto_mcts_archive",
                "alpha_count": 3,
                "front_count": 2,
                "objectives": ["rank_ic:max", "sharpe:max"],
                "front": [
                    {"formula": "strong", "rank_ic": 0.04, "sharpe": 1.0, "turnover": 0.1},
                    {"formula": "tradeoff", "rank_ic": 0.02, "sharpe": 1.2, "turnover": 0.05},
                ],
            }
        ),
        encoding="utf-8",
    )

    payload = build_research_review_payload(out)

    assert payload["available"] is True
    assert payload["admission"]["approved"] == 1
    assert payload["admission"]["review"] == 1
    assert payload["admission"]["rejected"] == 1
    assert payload["failure_memory"]["failures"] == 2
    assert payload["failure_memory"]["clusters"][0]["subtree"] == "ret(close,6)"
    assert payload["portfolio_walk_forward"]["best_survival"] == 0.75
    assert payload["portfolio_walk_forward"]["top"][0]["portfolio_id"] == "equal_weight_accepted"
    assert payload["pareto_archive"]["front_count"] == 2
    assert payload["pareto_archive"]["front"][0]["formula"] == "strong"
    assert payload["data_readiness"]["ready"] == 1
    assert payload["data_readiness"]["assets"] == 2
    assert payload["data_readiness"]["min_research_coverage"] == 0.8
    assert payload["data_readiness"]["max_missing_bars"] == 12
    assert payload["universe_robustness"]["formulas"] == 2
    assert payload["universe_robustness"]["best_pass_rate"] == 0.6
    assert payload["universe_robustness"]["max_pass_rate"] == 0.6
    assert payload["universe_robustness"]["top"][0]["factor_id"] == "carry"
    assert payload["portfolio_universe"]["portfolios"] == 2
    assert payload["portfolio_universe"]["best_pass_rate"] == 0.4
    assert payload["portfolio_universe"]["max_pass_rate"] == 0.4
    assert payload["portfolio_universe"]["top"][0]["portfolio_id"] == "equal_weight_accepted"


def test_research_review_payload_hides_when_no_artifacts(tmp_path) -> None:
    out = tmp_path / "reports" / "research_live"
    out.mkdir(parents=True)

    payload = build_research_review_payload(out)

    assert payload["available"] is False
