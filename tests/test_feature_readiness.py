from __future__ import annotations

from pathlib import Path

import pandas as pd

from quantumrandy.feature_readiness import (
    CRYPTO_FEATURE_SPECS,
    feature_readiness_manifest,
    feature_readiness_report,
    run_crypto_feature_readiness,
)


def test_crypto_feature_readiness_marks_missing_sources(tmp_path: Path) -> None:
    frame = run_crypto_feature_readiness([tmp_path])

    assert set(frame["feature"]) == {spec.feature for spec in CRYPTO_FEATURE_SPECS}
    assert set(frame["status"]) == {"missing_source"}
    assert set(frame["point_in_time_ready"]) == {False}
    assert set(frame["formula_profile_action"]) == {"do_not_admit"}
    assert "no local source file matched" in set(frame["reason"]).pop()


def test_crypto_feature_readiness_reports_incomplete_and_complete_schema(tmp_path: Path) -> None:
    pd.DataFrame({"timestamp": ["2024-01-01T00:00:00Z"], "value": [1.0]}).to_csv(
        tmp_path / "BTCUSDT_open_interest.csv",
        index=False,
    )
    pd.DataFrame(
        {
            "timestamp": ["2024-01-01T00:00:00Z"],
            "taker_buy_volume": [10.0],
            "taker_sell_volume": [8.0],
        }
    ).to_csv(tmp_path / "BTCUSDT_taker_imbalance.csv", index=False)

    frame = run_crypto_feature_readiness([tmp_path])
    rows = {row["feature"]: row for row in frame.to_dict(orient="records")}

    assert rows["open_interest"]["status"] == "present_schema_incomplete"
    assert rows["open_interest"]["point_in_time_ready"] is False
    assert "open_interest" in rows["open_interest"]["missing_columns"]
    assert rows["taker_buy_sell_imbalance"]["status"] == "eligible_for_candidate_design"
    assert rows["taker_buy_sell_imbalance"]["point_in_time_ready"] is True
    assert rows["taker_buy_sell_imbalance"]["formula_profile_action"] == "requires_separate_profile_admission"


def test_feature_readiness_manifest_and_report_are_research_only(tmp_path: Path) -> None:
    frame = run_crypto_feature_readiness([tmp_path])

    manifest = feature_readiness_manifest(frame, [tmp_path])
    report = feature_readiness_report(frame, manifest)

    assert manifest["artifact"] == "crypto_feature_readiness"
    assert manifest["research_only"] is True
    assert manifest["ready_for_formula_profile_admission"] is False
    assert "does not download data" in report
    assert "No new base fields are admitted" in report
