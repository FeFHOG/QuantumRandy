from __future__ import annotations

import json

from quantumrandy.factor_publisher import factor_id_for_formula, publish_from_files, select_runtime_factors


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
