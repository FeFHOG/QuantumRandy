from __future__ import annotations

import json

import pandas as pd

from quantumrandy.admission import AdmissionPolicy, evaluate_admission, write_admission_report


def test_evaluate_admission_combines_evidence_sources() -> None:
    leaderboard = [
        {
            "factor_id": "carry",
            "formula": "neg(zscore(funding_rate,42))",
            "description": "Funding reversal",
            "passed": True,
            "brutal_score": 80.0,
            "turnover": 0.1,
            "max_dd": 0.1,
            "validation_sharpe": 0.4,
            "validation_rank_ic": 0.02,
        },
        {
            "factor_id": "noisy",
            "formula": "zscore(ret(close,3),12)",
            "passed": False,
            "brutal_score": 10.0,
            "turnover": 1.2,
            "max_dd": 0.7,
            "validation_sharpe": -0.2,
            "validation_rank_ic": -0.01,
        },
    ]
    wf = pd.DataFrame(
        [
            {"formula": "neg(zscore(funding_rate,42))", "survival_rate": 0.75, "windows": 4},
            {"formula": "zscore(ret(close,3),12)", "survival_rate": 0.0, "windows": 4},
        ]
    )
    universe = pd.DataFrame(
        [
            {"formula": "neg(zscore(funding_rate,42))", "pass_rate": 0.8, "evaluated_assets": 5},
            {"formula": "zscore(ret(close,3),12)", "pass_rate": 0.2, "evaluated_assets": 5},
        ]
    )
    portfolio = pd.DataFrame(
        [
            {"factor_id": "carry", "selected": True, "max_abs_corr_to_selected": 0.2},
            {"factor_id": "noisy", "selected": False, "max_abs_corr_to_selected": 0.9},
        ]
    )
    portfolio_wf = pd.DataFrame(
        [
            {
                "portfolio_id": "equal_weight_accepted",
                "weights": "carry:0.500000,other:0.500000",
                "survival_rate": 0.75,
                "windows": 4,
                "test_sharpe_median": 0.5,
                "test_rank_ic_median": 0.02,
            },
            {
                "portfolio_id": "high_turnover_blend",
                "weights": "noisy:1.000000",
                "survival_rate": 0.0,
                "windows": 4,
                "test_sharpe_median": -0.5,
                "test_rank_ic_median": -0.02,
            },
        ]
    )

    decisions, manifest = evaluate_admission(
        leaderboard,
        walk_forward_summary=wf,
        universe_summary=universe,
        portfolio_selection=portfolio,
        portfolio_walk_forward_summary=portfolio_wf,
        policy=AdmissionPolicy(require_portfolio_selected=True),
    )

    by_factor = {row["factor_id"]: row for row in decisions.to_dict(orient="records")}
    assert by_factor["carry"]["admission_status"] == "approve"
    assert by_factor["carry"]["admission_pass"] is True
    assert by_factor["carry"]["portfolio_walk_forward_best_survival_rate"] == 0.75
    assert by_factor["noisy"]["admission_status"] == "reject"
    assert "brutal_pass" in by_factor["noisy"]["failed_rules"]
    assert "portfolio_walk_forward_survival" in by_factor["noisy"]["failed_rules"]
    assert manifest["approved_count"] == 1
    assert manifest["rejected_count"] == 1


def test_evaluate_admission_marks_partial_evidence_for_review() -> None:
    decisions, _ = evaluate_admission(
        [
            {
                "factor_id": "mixed",
                "formula": "zscore(close,48)",
                "passed": True,
                "brutal_score": 20.0,
                "turnover": 0.2,
                "max_dd": 0.2,
                "validation_sharpe": 0.2,
                "validation_rank_ic": -0.01,
            }
        ],
        policy=AdmissionPolicy(min_validation_rank_ic=0.0),
    )

    row = decisions.iloc[0].to_dict()
    assert row["admission_status"] == "review"
    assert row["admission_pass"] is False
    assert row["failed_rules"] == "validation_rank_ic"


def test_write_admission_report_outputs_files(tmp_path) -> None:
    leaderboard = [
        {
            "factor_id": "carry",
            "formula": "neg(zscore(funding_rate,42))",
            "passed": True,
            "brutal_score": 1.0,
            "turnover": 0.1,
            "max_dd": 0.1,
            "validation_sharpe": 0.1,
            "validation_rank_ic": 0.01,
        }
    ]

    manifest = write_admission_report(leaderboard, tmp_path)

    assert manifest["artifact_type"] == "quantumrandy_factor_admission"
    assert (tmp_path / "admission_decisions.csv").exists()
    payload = json.loads((tmp_path / "admission_manifest.json").read_text(encoding="utf-8"))
    assert payload["safety"]["not_runtime_publish_payload"] is True
    assert "research governance artifact" in (tmp_path / "ADMISSION_REPORT.md").read_text(encoding="utf-8")
