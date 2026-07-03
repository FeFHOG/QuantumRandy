from __future__ import annotations

import pandas as pd


def test_research10_replication_failure_memory_preserves_robustness_labels(tmp_path) -> None:
    from quantumrandy.research10_replication_memory import (
        build_research10_replication_failure_memory_rows,
        write_research10_replication_failure_memory,
    )

    ranking_csv = tmp_path / "watchlist_robustness_variant_ranking.csv"
    pd.DataFrame(
        [
            {
                "candidate_id": "qr_v09d_volume_conviction_001",
                "formula": "zscore(corr(sub(close,open),volume,48),72)",
                "variant_id": "thr_0p0_long_flat_cap_0p5_none",
                "conservative_verdict": "blocked_pending_new_hypotheses",
                "failure_reasons": "weak_blind_window|high_mean_drawdown",
                "robustness_labels": "blind_weakness|fee_fragility|funding_fragility",
                "stress_survival_count": 7,
                "stress_count": 16,
                "stress_survival_score": 0.4375,
                "mean_sharpe": 0.4,
                "validation_mean_sharpe": 0.5,
                "blind_mean_sharpe": -0.2,
                "mean_max_dd": 0.3,
                "worst_max_dd": 0.7,
            },
            {
                "candidate_id": "qr_v09d_funding_return_long_001",
                "formula": "zscore(corr(funding_rate,ret(close,42),120),72)",
                "variant_id": "thr_0p0_long_short_cap_0p5_none",
                "conservative_verdict": "research_watchlist",
                "failure_reasons": "",
                "robustness_labels": "",
                "stress_survival_count": 16,
                "stress_count": 16,
                "stress_survival_score": 1.0,
                "mean_sharpe": 0.7,
                "validation_mean_sharpe": 0.6,
                "blind_mean_sharpe": 0.4,
                "mean_max_dd": 0.2,
                "worst_max_dd": 0.4,
            },
        ]
    ).to_csv(ranking_csv, index=False)

    rows = build_research10_replication_failure_memory_rows(
        ranking_csv,
        source_robustness_dir="reports/factor_candidate_robustness/research_v0_9d_candidate_replication",
    )

    assert len(rows) == 2
    by_id = {row["candidate_id"]: row for row in rows}
    failed = by_id["qr_v09d_volume_conviction_001::thr_0p0_long_flat_cap_0p5_none"]
    assert failed["passed"] is False
    assert failed["candidate_family"] == "research_1_0_replication_variant"
    assert "blind_weakness" in failed["failure_labels"]
    assert "fee_fragility" in failed["failure_labels"]
    assert failed["stress_survival"] == "7/16"
    assert failed["source_robustness_dir"] == "reports/factor_candidate_robustness/research_v0_9d_candidate_replication"
    survivor = by_id["qr_v09d_funding_return_long_001::thr_0p0_long_short_cap_0p5_none"]
    assert survivor["passed"] is True

    out = tmp_path / "memory"
    manifest = write_research10_replication_failure_memory(
        ranking_csv,
        out,
        source_robustness_dir="reports/factor_candidate_robustness/research_v0_9d_candidate_replication",
    )

    assert manifest["artifact_type"] == "quantumrandy_failure_memory"
    assert manifest["input_rows"] == 2
    assert manifest["failure_count"] == 1
    memory = pd.read_csv(out / "failure_memory.csv")
    assert memory.iloc[0]["candidate_id"] == "qr_v09d_volume_conviction_001::thr_0p0_long_flat_cap_0p5_none"
