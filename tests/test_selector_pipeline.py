from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import yaml

from quantumrandy.candidate_selector import write_candidate_selector_report
from quantumrandy.selector_pipeline import (
    build_selector_pipeline_candidate_review,
    build_selector_pipeline_candidate_highlights,
    build_selector_pipeline_review,
    render_review_report,
    run_selector_rewrite_pipeline,
    write_selector_candidate_highlight_summary,
)


def _market(periods: int = 240, *, drift: float = 1.0) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=periods, freq="4h", tz="UTC")
    trend = pd.Series(range(periods), index=idx, dtype=float)
    close = 100.0 + drift * trend + 2.0 * ((trend % 12) / 12.0)
    return pd.DataFrame(
        {
            "timestamp": idx,
            "open": close - 0.2,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 1000.0 + trend,
        }
    )


def _funding(periods: int = 240) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=periods, freq="4h", tz="UTC")
    return pd.DataFrame({"timestamp": idx, "funding_rate": 0.0001})


def _write_config(tmp_path: Path, symbol: str, *, drift: float = 1.0) -> Path:
    root = tmp_path / symbol.lower()
    root.mkdir()
    ohlcv = root / "ohlcv.csv"
    funding = root / "funding.csv"
    config = root / "config.yaml"
    _market(drift=drift).to_csv(ohlcv, index=False)
    _funding().to_csv(funding, index=False)
    config.write_text(
        yaml.safe_dump(
            {
                "symbol": symbol,
                "bar_hours": 4,
                "ohlcv_csv": "ohlcv.csv",
                "funding_csv": "funding.csv",
                "costs": {"taker_bps": 0.0, "slippage_bps": 0.0, "funding_multiplier": 0.0},
                "execution": {"delay_bars": 1, "exposure_threshold": 0.0, "max_exposure_abs": 1.0},
                "windows": {
                    "training_start": "2024-01-01",
                    "training_end": "2024-01-15",
                    "validation_start": "2024-01-15",
                    "validation_end": "2024-02-01",
                },
                "mcts": {"seed_formulas": []},
                "filter": {"min_rank_ic": -1.0, "min_directional_win_rate": 0.0, "min_cost_sharpe": -99.0},
            }
        ),
        encoding="utf-8",
    )
    return config


def _selector_artifact(tmp_path: Path) -> Path:
    selector = tmp_path / "selector"
    leaderboard = [
        {
            "factor_id": "weak_momentum",
            "formula": "zscore(ret(close,6),48)",
            "passed": True,
            "brutal_score": 60.0,
        }
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
            }
        ]
    )
    write_candidate_selector_report(leaderboard, selector, universe_summary=universe)
    return selector


def test_selector_rewrite_pipeline_runs_research_only_evidence_chain(tmp_path) -> None:
    selector = _selector_artifact(tmp_path)
    configs = [
        _write_config(tmp_path, "BTCUSDT"),
        _write_config(tmp_path, "ETHUSDT", drift=1.5),
    ]

    manifest = run_selector_rewrite_pipeline(
        selector_path=selector,
        out_dir=tmp_path / "pipeline",
        config_paths=configs,
        candidates_per_target=1,
    )

    assert manifest["artifact_type"] == "quantumrandy_selector_rewrite_research_pipeline"
    assert manifest["safety"]["not_runtime_publish_payload"] is True
    assert manifest["safety"]["does_not_update_runtime"] is True
    assert manifest["rewrite"]["candidate_count"] == 1
    assert manifest["rewrite"]["use_llm_requested"] is False
    assert manifest["rewrite"]["is_llm_policy_evidence"] is False
    assert manifest["rewrite"]["llm_rewrite_accepted"] == 0
    assert manifest["rewrite"]["fallback_rewrite_accepted"] >= 1
    assert manifest["universe"]["status"] == "completed"
    assert manifest["portfolio"]["status"] == "completed"
    assert manifest["portfolio_universe"]["status"] == "completed"
    assert manifest["review"]["status"] == "completed"
    assert (tmp_path / "pipeline" / "rewrite" / "selector_rewrite_candidates.json").exists()
    assert (tmp_path / "pipeline" / "universe" / "universe_summary.csv").exists()
    assert (tmp_path / "pipeline" / "portfolio" / "portfolio_manifest.json").exists()
    assert (tmp_path / "pipeline" / "portfolio_universe" / "portfolio_universe_summary.csv").exists()
    assert (tmp_path / "pipeline" / "review" / "selector_pipeline_review.csv").exists()
    assert (tmp_path / "pipeline" / "review" / "selector_pipeline_candidate_review.csv").exists()
    assert (tmp_path / "pipeline" / "review" / "selector_pipeline_candidate_highlights.csv").exists()
    assert (tmp_path / "pipeline" / "review" / "SELECTOR_CANDIDATE_HIGHLIGHTS.md").exists()
    assert (tmp_path / "pipeline" / "review" / "selector_candidate_highlight_summary_manifest.json").exists()

    persisted = json.loads(
        (tmp_path / "pipeline" / "selector_rewrite_pipeline_manifest.json").read_text(encoding="utf-8")
    )
    assert persisted["portfolio_universe"]["status"] == "completed"
    assert persisted["rewrite"]["is_llm_policy_evidence"] is False
    assert persisted["review"]["status"] == "completed"
    assert persisted["review"]["candidate_review_rows"] >= persisted["review"]["review_rows"]
    assert "candidate_verdict_counts" in persisted["review"]
    assert "candidate_highlight_counts" in persisted["review"]
    assert "pipeline_candidate_review" in persisted["outputs"]
    assert "pipeline_candidate_highlights" in persisted["outputs"]
    assert "pipeline_candidate_highlight_summary" in persisted["outputs"]
    assert "pipeline_candidate_highlight_summary_manifest" in persisted["outputs"]
    report = (tmp_path / "pipeline" / "SELECTOR_REWRITE_PIPELINE_REPORT.md").read_text(encoding="utf-8")
    assert "research artifact only" in report
    assert "LLM policy evidence" in report
    assert "Reviewed candidates" in report
    assert "Candidate highlight mix" in report
    review_report = (tmp_path / "pipeline" / "review" / "SELECTOR_PIPELINE_REVIEW.md").read_text(encoding="utf-8")
    assert "research comparison artifact only" in review_report
    assert "Candidate Verdict Counts" in review_report
    assert "Candidate-Level Highlights" in review_report
    review_manifest = json.loads(
        (tmp_path / "pipeline" / "review" / "selector_pipeline_review_manifest.json").read_text(encoding="utf-8")
    )
    assert review_manifest["candidate_review_rows"] >= review_manifest["review_rows"]
    assert "candidate_highlight_rows" in review_manifest
    assert "candidate_highlight_summary" in review_manifest["outputs"]


def test_selector_rewrite_pipeline_can_stop_after_rewrite_without_configs(tmp_path) -> None:
    manifest = run_selector_rewrite_pipeline(
        selector_path=_selector_artifact(tmp_path),
        out_dir=tmp_path / "pipeline",
        candidates_per_target=1,
        run_portfolio_universe=False,
    )

    assert manifest["rewrite"]["candidate_count"] == 1
    assert manifest["universe"]["status"] == "skipped"
    assert manifest["universe"]["reason"] == "no asset config paths provided"
    assert manifest["review"]["status"] == "skipped"
    assert manifest["portfolio_universe"]["status"] == "skipped"


def test_selector_pipeline_review_compares_parent_and_rewrite_evidence(tmp_path) -> None:
    candidates = pd.DataFrame(
        [
            {
                "factor_id": "rewrite_a",
                "formula": "neg(zscore(funding_rate,42))",
                "parent_factor_id": "parent_a",
                "parent_formula": "zscore(ret(close,6),48)",
                "parent_rewrite_focus": "improve_cross_asset_robustness",
                "parent_universe_pass_rate": 0.2,
                "parent_universe_mean_sharpe": -0.1,
            },
            {
                "factor_id": "rewrite_b",
                "formula": "zscore(volume,48)",
                "parent_factor_id": "parent_a",
                "parent_formula": "zscore(ret(close,6),48)",
                "parent_rewrite_focus": "improve_cross_asset_robustness",
                "parent_universe_pass_rate": 0.2,
                "parent_universe_mean_sharpe": -0.1,
            },
            {
                "factor_id": "rewrite_c",
                "formula": "zscore(close,48)",
                "parent_factor_id": "parent_b",
                "parent_formula": "zscore(close,12)",
                "parent_rewrite_focus": "improve_cross_asset_profitability",
                "parent_universe_pass_rate": 0.6,
                "parent_universe_mean_sharpe": 0.4,
            },
            {
                "factor_id": "rewrite_d",
                "formula": "zscore(div(sub(high,low),close),168)",
                "parent_factor_id": "parent_c",
                "parent_formula": "zscore(corr(sub(close,open),volume,48),72)",
                "parent_rewrite_focus": "improve_cross_asset_robustness",
                "parent_universe_pass_rate": 0.2,
                "parent_universe_mean_sharpe": 0.3,
            },
            {
                "factor_id": "rewrite_e",
                "formula": "zscore(volume,120)",
                "parent_factor_id": "parent_d",
                "parent_formula": "zscore(volume,48)",
                "parent_rewrite_focus": "improve_cross_asset_profitability",
                "parent_universe_pass_rate": 0.2,
                "parent_universe_mean_sharpe": -0.3,
            },
            {
                "factor_id": "rewrite_f",
                "formula": "zscore(volume,72)",
                "parent_factor_id": "parent_e",
                "parent_formula": "zscore(volume,24)",
                "parent_rewrite_focus": "improve_cross_asset_robustness",
                "parent_universe_pass_rate": 0.2,
                "parent_universe_mean_sharpe": 0.1,
            },
            {
                "factor_id": "rewrite_g",
                "formula": "zscore(volume,96)",
                "parent_factor_id": "parent_e",
                "parent_formula": "zscore(volume,24)",
                "parent_rewrite_focus": "improve_cross_asset_robustness",
                "parent_universe_pass_rate": 0.2,
                "parent_universe_mean_sharpe": 0.1,
            },
        ]
    )
    candidate_path = tmp_path / "selector_rewrite_candidates.csv"
    candidates.to_csv(candidate_path, index=False)
    universe_summary = pd.DataFrame(
        [
            {
                "factor_id": "rewrite_a",
                "pass_rate": 0.6,
                "mean_sharpe": 0.2,
                "median_rank_ic": 0.01,
                "robustness_score": 1.2,
                "failed_assets": "SOLUSDT",
                "evaluated_assets": 5,
            },
            {
                "factor_id": "rewrite_b",
                "pass_rate": 0.4,
                "mean_sharpe": -0.2,
                "median_rank_ic": 0.0,
                "robustness_score": 0.1,
                "failed_assets": "ETHUSDT,SOLUSDT",
                "evaluated_assets": 5,
            },
            {
                "factor_id": "rewrite_c",
                "pass_rate": 0.4,
                "mean_sharpe": 0.1,
                "median_rank_ic": 0.0,
                "robustness_score": 0.2,
                "failed_assets": "ETHUSDT,SOLUSDT",
                "evaluated_assets": 5,
            },
            {
                "factor_id": "rewrite_d",
                "pass_rate": 0.6,
                "mean_sharpe": 0.1,
                "median_rank_ic": 0.01,
                "robustness_score": 0.6,
                "failed_assets": "BTCUSDT,ETHUSDT",
                "evaluated_assets": 5,
            },
            {
                "factor_id": "rewrite_e",
                "pass_rate": 0.2,
                "mean_sharpe": -0.1,
                "median_rank_ic": 0.01,
                "robustness_score": 0.4,
                "failed_assets": "BTCUSDT",
                "evaluated_assets": 5,
            },
            {
                "factor_id": "rewrite_f",
                "pass_rate": 0.6,
                "mean_sharpe": -0.1,
                "median_rank_ic": 0.02,
                "robustness_score": 0.8,
                "failed_assets": "BTCUSDT",
                "evaluated_assets": 5,
            },
            {
                "factor_id": "rewrite_g",
                "pass_rate": 0.4,
                "mean_sharpe": 0.2,
                "median_rank_ic": 0.01,
                "robustness_score": 0.5,
                "failed_assets": "ETHUSDT",
                "evaluated_assets": 5,
            },
        ]
    )

    review = build_selector_pipeline_review(candidate_path, universe_summary)
    candidate_review = build_selector_pipeline_candidate_review(candidate_path, universe_summary)

    by_parent = {row["parent_factor_id"]: row for row in review.to_dict(orient="records")}
    assert by_parent["parent_a"]["best_candidate_factor_id"] == "rewrite_a"
    assert by_parent["parent_a"]["review_verdict"] == "improved"
    assert by_parent["parent_a"]["pass_rate_delta"] == 0.4
    assert by_parent["parent_a"]["improvement_gate"] == "pass_rate_delta > 0 and mean_sharpe_delta >= 0"
    assert by_parent["parent_a"]["candidate_verdict_counts"] == "improved:1|coverage_only:1"
    assert "verdict_rank=4" in by_parent["parent_a"]["best_candidate_rank_reason"]
    assert by_parent["parent_b"]["review_verdict"] == "not_improved"
    assert by_parent["parent_c"]["review_verdict"] == "coverage_only"
    assert by_parent["parent_c"]["pass_rate_delta"] == 0.4
    assert by_parent["parent_c"]["mean_sharpe_delta"] == -0.2
    assert by_parent["parent_d"]["review_verdict"] == "mixed"
    assert by_parent["parent_e"]["best_candidate_factor_id"] == "rewrite_g"
    assert by_parent["parent_e"]["review_verdict"] == "improved"
    assert by_parent["parent_e"]["candidate_verdict_counts"] == "improved:1|coverage_only:1"
    assert review.iloc[0]["review_verdict"] == "improved"
    by_candidate = {row["factor_id"]: row for row in candidate_review.to_dict(orient="records")}
    assert by_candidate["rewrite_f"]["candidate_review_verdict"] == "coverage_only"
    assert by_candidate["rewrite_g"]["candidate_review_verdict"] == "improved"
    assert by_candidate["rewrite_g"]["pass_rate_delta"] == 0.2
    assert by_candidate["rewrite_g"]["mean_sharpe_delta"] == 0.1

    highlights = build_selector_pipeline_candidate_highlights(candidate_review)
    by_highlight = {row["factor_id"]: row for row in highlights.to_dict(orient="records")}
    assert by_highlight["rewrite_a"]["highlight_type"] == "true_improved"
    assert by_highlight["rewrite_f"]["highlight_type"] == "coverage_only_trap"
    assert by_highlight["rewrite_e"]["highlight_type"] == "sharpe_improved_no_pass_lift"
    assert by_highlight["rewrite_g"]["candidate_failed_assets"] == "ETHUSDT"

    report = render_review_report(
        {
            "review_rows": len(review),
            "candidate_review_rows": len(candidate_review),
            "verdict_counts": {"improved": 2},
            "candidate_verdict_counts": {"improved": 2, "coverage_only": 2, "mixed": 1},
        },
        review,
        candidate_review=candidate_review,
    )
    assert "True Improved Candidates" in report
    assert "`rewrite_g`" in report
    assert "ETHUSDT" in report
    assert "Coverage-Only Traps" in report
    assert "`rewrite_f`" in report
    assert "Sharpe-Improved Without Pass-Rate Lift" in report
    assert "`rewrite_e`" in report

    review_dir = tmp_path / "review_summary"
    review_dir.mkdir()
    candidate_review.to_csv(review_dir / "selector_pipeline_candidate_review.csv", index=False)
    highlights.to_csv(review_dir / "selector_pipeline_candidate_highlights.csv", index=False)
    summary_manifest = write_selector_candidate_highlight_summary(review_dir)
    summary_report = (review_dir / "SELECTOR_CANDIDATE_HIGHLIGHTS.md").read_text(encoding="utf-8")
    assert summary_manifest["safety"]["does_not_auto_admit_factors"] is True
    assert summary_manifest["highlight_rows"] == len(highlights)
    assert "true_improved" in summary_manifest["highlight_counts"]
    assert "Selector Candidate Highlights" in summary_report
    assert "Coverage-Only Traps" in summary_report
    assert "`rewrite_f`" in summary_report
