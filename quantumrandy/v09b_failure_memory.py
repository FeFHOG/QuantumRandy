from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .factor_candidate_export import V09B_FUNDING_PRESSURE_FAILURE_MODE, V09B_FUNDING_PRESSURE_HYPOTHESIS
from .failure_memory import write_failure_memory


def build_v0_9b_failure_memory_rows(
    review_csv: str | Path,
    *,
    source_review_dir: str,
) -> list[dict[str, Any]]:
    review = pd.read_csv(review_csv).fillna("")
    rows: list[dict[str, Any]] = []
    for raw in review.to_dict(orient="records"):
        failure_reasons = _split_labels(raw.get("failure_reasons", ""))
        verdict = _conservative_verdict(str(raw.get("review_verdict", "")))
        rows.append(
            {
                "candidate_id": raw.get("candidate_id", ""),
                "formula": raw.get("formula", ""),
                "candidate_family": "funding_pressure_crowding_mean_reversion",
                "description": "Research v0.9b BTCUSDT 4h scoped funding-pressure candidate.",
                "hypothesis": raw.get("applicability_hypothesis", "") or V09B_FUNDING_PRESSURE_HYPOTHESIS,
                "expected_failure_mode": V09B_FUNDING_PRESSURE_FAILURE_MODE,
                "intended_scope": raw.get("intended_scope", "BTCUSDT_4h"),
                "out_of_scope_policy": raw.get("out_of_scope_policy", "diagnostic_only"),
                "conservative_verdict": verdict,
                "passed": verdict == "scoped_watchlist",
                "kill_reasons": failure_reasons,
                "failure_labels": "|".join(_failure_labels(raw, failure_reasons)),
                "source_review_dir": source_review_dir,
                "sharpe": _float(raw.get("mean_sharpe", "")),
                "validation_sharpe": _float(raw.get("validation_mean_sharpe", "")),
                "blind_sharpe": _float(raw.get("blind_mean_sharpe", "")),
                "max_dd": _float(raw.get("mean_max_dd", "")),
                "worst_max_dd": _float(raw.get("worst_max_dd", "")),
            }
        )
    return rows


def write_v0_9b_failure_memory(
    review_csv: str | Path,
    out_dir: str | Path,
    *,
    source_review_dir: str,
) -> dict[str, Any]:
    rows = build_v0_9b_failure_memory_rows(review_csv, source_review_dir=source_review_dir)
    return write_failure_memory(rows, out_dir)


def _conservative_verdict(review_verdict: str) -> str:
    if review_verdict == "research_watchlist":
        return "scoped_watchlist"
    return "blocked_pending_new_hypotheses"


def _failure_labels(row: dict[str, Any], failure_reasons: list[str]) -> list[str]:
    labels = set(failure_reasons)
    if any(reason in labels for reason in {"low_mean_sharpe", "low_median_sharpe", "low_positive_row_share"}):
        labels.add("weak_funding_pressure_edge")
    if any(reason in labels for reason in {"weak_validation_window", "weak_blind_window"}):
        labels.add("trend_persistence_risk")
    if "high_mean_drawdown" in labels or "extreme_row_drawdown" in labels:
        labels.add("drawdown_fragility")
    if _float(row.get("validation_mean_sharpe", "")) < 0.0:
        labels.add("weak_validation_window")
        labels.add("trend_persistence_risk")
    return sorted(label for label in labels if label)


def _split_labels(value: Any) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    return [part.strip() for part in text.replace(",", "|").split("|") if part.strip()]


def _float(value: Any) -> float | str:
    if value in (None, ""):
        return ""
    try:
        return round(float(value), 8)
    except (TypeError, ValueError):
        return ""
