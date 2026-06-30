from __future__ import annotations

import json

import pandas as pd

from quantumrandy.factor_publisher import (
    factor_id_for_formula,
    publish_from_files,
    publish_portfolio_from_files,
    select_portfolio_runtime_config,
    select_runtime_factors,
)


def test_select_runtime_factors_uses_passed_rows_and_stable_ids() -> None:
    leaderboard = [
        {"formula": "zscore(close,48)", "passed": False, "brutal_score": 99.0},
        {"formula": "neg(zscore(funding_rate,42))", "passed": True, "brutal_score": 10.0},
        {"formula": "zscore(ret(close,6),48)", "passed": True, "brutal_score": 20.0},
    ]

    selection = select_runtime_factors(leaderboard, max_factors=2)

    assert [item["formula"] for item in selection.factors] == [
        "zscore(ret(close,6),48)",
        "neg(zscore(funding_rate,42))",
    ]
    assert selection.factors[0]["factor_id"] == factor_id_for_formula("zscore(ret(close,6),48)")
    assert selection.strategies[0]["components"] == [
        {"factor_id": selection.factors[0]["factor_id"], "weight": 1.0},
        {"factor_id": selection.factors[1]["factor_id"], "weight": 1.0},
    ]


def test_publish_from_files_writes_payload_and_audit(tmp_path) -> None:
    leaderboard_path = tmp_path / "leaderboard.json"
    manifest_path = tmp_path / "runtime_factors.json"
    out_path = tmp_path / "proposal.json"
    leaderboard_path.write_text(
        json.dumps(
            [
                {
                    "formula": "neg(zscore(funding_rate,42))",
                    "description": "Funding pressure reversal.",
                    "passed": True,
                    "brutal_score": 42.0,
                    "rank_ic": 0.02,
                    "sharpe": 0.5,
                }
            ]
        ),
        encoding="utf-8",
    )
    manifest_path.write_text(json.dumps({"generation": 7, "factors": [], "strategies": []}), encoding="utf-8")

    result = publish_from_files(
        leaderboard_path=leaderboard_path,
        runtime_manifest_path=manifest_path,
        out_path=out_path,
        max_factors=1,
    )

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert result["selected_count"] == 1
    assert payload["expected_generation"] == 7
    assert payload["factors"][0]["formula"] == "neg(zscore(funding_rate,42))"
    assert (tmp_path / "proposal_audit.md").exists()


def test_select_portfolio_runtime_config_preserves_reviewed_weights() -> None:
    formula_a = "neg(zscore(funding_rate,42))"
    formula_b = "zscore(ret(close,6),48)"
    manifest = {
        "artifact_type": "quantumrandy_portfolio_research",
        "safety": {"requires_manual_review_before_runtime": True},
        "portfolios": [
            {
                "portfolio_id": "ic_weight_accepted",
                "weighting": "rank_ic_weight",
                "weights": {"carry": 0.7, "momentum": 0.3},
            }
        ],
    }
    factor_rows = [
        {"factor_id": "carry", "formula": formula_a, "description": "Funding reversal"},
        {"factor_id": "momentum", "formula": formula_b, "description": "Price momentum"},
    ]

    selection = select_portfolio_runtime_config(manifest, factor_rows)

    assert [item["formula"] for item in selection.factors] == [formula_a, formula_b]
    assert selection.strategies[0]["strategy_id"] == "ic_weight_accepted"
    assert selection.strategies[0]["components"] == [
        {"factor_id": factor_id_for_formula(formula_a), "weight": 0.7},
        {"factor_id": factor_id_for_formula(formula_b), "weight": 0.3},
    ]
    assert selection.selected_rows[0]["portfolio_weight"] == 0.7


def test_publish_portfolio_from_files_writes_reviewable_payload(tmp_path) -> None:
    manifest_path = tmp_path / "portfolio_manifest.json"
    factors_path = tmp_path / "portfolio_factors.csv"
    runtime_path = tmp_path / "runtime_factors.json"
    out_path = tmp_path / "portfolio_proposal.json"
    formula = "neg(zscore(funding_rate,42))"
    manifest_path.write_text(
        json.dumps(
            {
                "artifact_type": "quantumrandy_portfolio_research",
                "safety": {"requires_manual_review_before_runtime": True},
                "portfolios": [
                    {
                        "portfolio_id": "equal_weight_accepted",
                        "weighting": "equal_weight",
                        "weights": {"carry": 1.0},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    pd.DataFrame([{"factor_id": "carry", "formula": formula, "description": "Funding reversal"}]).to_csv(
        factors_path,
        index=False,
    )
    runtime_path.write_text(json.dumps({"generation": 4, "factors": [], "strategies": []}), encoding="utf-8")

    result = publish_portfolio_from_files(
        portfolio_manifest_path=manifest_path,
        portfolio_factors_path=factors_path,
        runtime_manifest_path=runtime_path,
        out_path=out_path,
    )

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert result["selected_count"] == 1
    assert payload["expected_generation"] == 4
    assert payload["strategies"][0]["components"] == [{"factor_id": factor_id_for_formula(formula), "weight": 1.0}]
    assert (tmp_path / "portfolio_proposal_audit.md").exists()
