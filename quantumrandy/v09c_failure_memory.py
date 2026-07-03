from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .failure_memory import write_failure_memory


def build_v0_9c_failure_memory_rows(
    review_csv: str | Path,
    *,
    correlation_csv: str | Path,
    source_review_dir: str,
    source_correlation_dir: str,
) -> list[dict[str, Any]]:
    review = pd.read_csv(review_csv).fillna("")
    redundancy = _redundancy_by_candidate(correlation_csv)
    rows: list[dict[str, Any]] = []
    for raw in review.to_dict(orient="records"):
        candidate_id = str(raw.get("candidate_id", ""))
        failures = _split_labels(raw.get("failure_reasons", ""))
        redundancy_row = redundancy.get(candidate_id, {})
        labels = _failure_labels(raw, failures, redundancy_row)
        kill_reasons = failures or (["bundle_redundancy"] if "bundle_redundancy" in labels else [])
        verdict = _conservative_verdict(str(raw.get("review_verdict", "")), redundancy_row)
        rows.append(
            {
                "candidate_id": candidate_id,
                "formula": raw.get("formula", ""),
                "candidate_family": _candidate_family(candidate_id),
                "description": "Research v0.9c BTCUSDT 4h scoped multi-factor bundle candidate.",
                "hypothesis": raw.get("applicability_hypothesis", ""),
                "expected_failure_mode": (
                    "v0.9c candidates may fail through weak validation, drawdown fragility, or bundle redundancy."
                ),
                "intended_scope": raw.get("intended_scope", "BTCUSDT_4h"),
                "out_of_scope_policy": raw.get("out_of_scope_policy", "diagnostic_only"),
                "conservative_verdict": verdict,
                "passed": verdict == "scoped_watchlist",
                "kill_reasons": kill_reasons,
                "failure_labels": "|".join(labels),
                "source_review_dir": source_review_dir,
                "source_correlation_dir": source_correlation_dir,
                "sharpe": _float(raw.get("mean_sharpe", "")),
                "validation_sharpe": _float(raw.get("validation_mean_sharpe", "")),
                "blind_sharpe": _float(raw.get("blind_mean_sharpe", "")),
                "max_dd": _float(raw.get("mean_max_dd", "")),
                "worst_max_dd": _float(raw.get("worst_max_dd", "")),
            }
        )
    return rows


def write_v0_9c_failure_memory(
    review_csv: str | Path,
    out_dir: str | Path,
    *,
    correlation_csv: str | Path,
    source_review_dir: str,
    source_correlation_dir: str,
) -> dict[str, Any]:
    rows = build_v0_9c_failure_memory_rows(
        review_csv,
        correlation_csv=correlation_csv,
        source_review_dir=source_review_dir,
        source_correlation_dir=source_correlation_dir,
    )
    return write_failure_memory(rows, out_dir)


def _redundancy_by_candidate(correlation_csv: str | Path) -> dict[str, dict[str, Any]]:
    frame = pd.read_csv(correlation_csv).fillna("")
    rows = {}
    for raw in frame.to_dict(orient="records"):
        candidate_id = str(raw.get("bundle_candidate_id", ""))
        if candidate_id:
            rows[candidate_id] = raw
    return rows


def _candidate_family(candidate_id: str) -> str:
    if "_bundle_" in candidate_id:
        return "scoped_multi_factor_bundle"
    return "scoped_multi_factor_component"


def _conservative_verdict(review_verdict: str, redundancy_row: dict[str, Any]) -> str:
    if redundancy_row.get("redundancy_verdict") == "redundant_research_memory_only":
        return "research_memory_only"
    if review_verdict == "research_watchlist":
        return "scoped_watchlist"
    return "blocked_pending_new_hypotheses"


def _failure_labels(row: dict[str, Any], failures: list[str], redundancy_row: dict[str, Any]) -> list[str]:
    labels = set(failures)
    candidate_id = str(row.get("candidate_id", ""))
    formula = str(row.get("formula", ""))
    if "_bundle_" in candidate_id:
        labels.add("multi_factor_bundle")
    if "weak_validation_window" in labels or _lt(row.get("validation_mean_sharpe", ""), 0.0):
        labels.add("validation_bundle_fragility")
    if "weak_blind_window" in labels or _lt(row.get("blind_mean_sharpe", ""), 0.0):
        labels.add("blind_bundle_fragility")
    if "high_mean_drawdown" in labels or "extreme_row_drawdown" in labels:
        labels.add("drawdown_fragility")
    if "funding" in formula:
        labels.add("funding_pressure_fragility")
    if "ret(close" in formula and "neg(zscore(ret" in formula:
        labels.add("trend_reversal_conflict")
    if redundancy_row.get("redundancy_verdict") == "redundant_research_memory_only":
        labels.add("bundle_redundancy")
        if _gte(redundancy_row.get("max_abs_component_corr", ""), 0.80):
            labels.add("component_crowding_overlap")
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


def _lt(value: Any, threshold: float) -> bool:
    parsed = _float(value)
    return isinstance(parsed, float) and parsed < threshold


def _gte(value: Any, threshold: float) -> bool:
    parsed = _float(value)
    return isinstance(parsed, float) and parsed >= threshold
