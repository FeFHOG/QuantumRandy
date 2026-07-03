from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .failure_memory import write_failure_memory

V09D_DESCRIPTION = "Research v0.9d BTCUSDT 4h strict candidate-family discovery candidate."
V09D_EXPECTED_FAILURE_MODE = (
    "v0.9d candidates may fail through low strict-grid Sharpe, validation or blind weakness, drawdown fragility, "
    "ETH diagnostic weakness, or bundle component redundancy."
)


def build_v0_9d_failure_memory_rows(
    review_csv: str | Path,
    *,
    source_review_dir: str,
    diagnostic_review_csv: str | Path | None = None,
    source_diagnostic_dir: str = "",
    correlation_csv: str | Path | None = None,
    source_correlation_dir: str = "",
) -> list[dict[str, Any]]:
    review = pd.read_csv(review_csv).fillna("")
    diagnostic = _diagnostic_by_candidate_variant(diagnostic_review_csv)
    redundancy = _redundancy_by_candidate(correlation_csv)
    rows: list[dict[str, Any]] = []
    for raw in review.to_dict(orient="records"):
        candidate_id = str(raw.get("candidate_id", ""))
        failures = _split_labels(raw.get("failure_reasons", ""))
        diagnostic_row = diagnostic.get(_candidate_variant_key(raw), {})
        redundancy_row = redundancy.get(candidate_id, {})
        labels = _failure_labels(raw, failures, diagnostic_row, redundancy_row)
        verdict = _conservative_verdict(str(raw.get("review_verdict", "")), labels, redundancy_row)
        rows.append(
            {
                "candidate_id": candidate_id,
                "variant_id": _variant_id(raw),
                "formula": raw.get("formula", ""),
                "candidate_family": _candidate_family(raw),
                "description": V09D_DESCRIPTION,
                "hypothesis": raw.get("applicability_hypothesis", ""),
                "expected_failure_mode": V09D_EXPECTED_FAILURE_MODE,
                "intended_scope": raw.get("intended_scope", "BTCUSDT_4h"),
                "out_of_scope_policy": raw.get("out_of_scope_policy", "diagnostic_only"),
                "conservative_verdict": verdict,
                "passed": verdict == "research_1_0_candidate_pending_replication",
                "kill_reasons": _kill_reasons(failures, labels, verdict),
                "failure_labels": "|".join(labels),
                "source_review_dir": source_review_dir,
                "source_diagnostic_dir": source_diagnostic_dir,
                "source_correlation_dir": source_correlation_dir,
                "sharpe": _float(raw.get("mean_sharpe", "")),
                "validation_sharpe": _float(raw.get("validation_mean_sharpe", "")),
                "blind_sharpe": _float(raw.get("blind_mean_sharpe", "")),
                "max_dd": _float(raw.get("mean_max_dd", "")),
                "worst_max_dd": _float(raw.get("worst_max_dd", "")),
            }
        )
    return rows


def write_v0_9d_failure_memory(
    review_csv: str | Path,
    out_dir: str | Path,
    *,
    source_review_dir: str,
    diagnostic_review_csv: str | Path | None = None,
    source_diagnostic_dir: str = "",
    correlation_csv: str | Path | None = None,
    source_correlation_dir: str = "",
) -> dict[str, Any]:
    rows = build_v0_9d_failure_memory_rows(
        review_csv,
        source_review_dir=source_review_dir,
        diagnostic_review_csv=diagnostic_review_csv,
        source_diagnostic_dir=source_diagnostic_dir,
        correlation_csv=correlation_csv,
        source_correlation_dir=source_correlation_dir,
    )
    return write_failure_memory(rows, out_dir)


def _diagnostic_by_candidate_variant(path: str | Path | None) -> dict[tuple[str, str], dict[str, Any]]:
    frame = _read_optional_csv(path)
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    for raw in frame.to_dict(orient="records"):
        key = _candidate_variant_key(raw)
        if key[0]:
            rows[key] = raw
    return rows


def _redundancy_by_candidate(path: str | Path | None) -> dict[str, dict[str, Any]]:
    frame = _read_optional_csv(path)
    rows: dict[str, dict[str, Any]] = {}
    for raw in frame.to_dict(orient="records"):
        candidate_id = str(raw.get("bundle_candidate_id", "")) or str(raw.get("candidate_id", ""))
        if candidate_id:
            rows[candidate_id] = raw
    return rows


def _read_optional_csv(path: str | Path | None) -> pd.DataFrame:
    if not path:
        return pd.DataFrame()
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    return pd.read_csv(csv_path).fillna("")


def _candidate_family(row: dict[str, Any]) -> str:
    explicit = str(row.get("formula_family", "") or row.get("source_formula_family", "")).strip()
    if explicit:
        return explicit
    candidate_id = str(row.get("candidate_id", ""))
    if "_bundle_" in candidate_id:
        return "scoped_equal_weight_bundle"
    if "funding_return" in candidate_id:
        return "funding_return_long_horizon"
    if "liquidity" in candidate_id:
        return "liquidity_adjusted_momentum"
    if "intrabar" in candidate_id:
        return "intrabar_conviction"
    if "trend" in candidate_id:
        return "trend_quality"
    return "strict_candidate_family_discovery"


def _candidate_variant_key(row: dict[str, Any]) -> tuple[str, str]:
    return str(row.get("candidate_id", "")), _variant_id(row)


def _variant_id(row: dict[str, Any]) -> str:
    return str(row.get("variant_id", "default") or "default")


def _conservative_verdict(review_verdict: str, labels: list[str], redundancy_row: dict[str, Any]) -> str:
    if redundancy_row.get("redundancy_verdict") == "redundant_research_memory_only":
        return "research_memory_only"
    if review_verdict == "research_watchlist" and "eth_diagnostic_weakness" in labels:
        return "scoped_watchlist_needs_replication"
    if review_verdict == "research_watchlist":
        return "research_1_0_candidate_pending_replication"
    return "blocked_pending_new_hypotheses"


def _failure_labels(
    row: dict[str, Any],
    failures: list[str],
    diagnostic_row: dict[str, Any],
    redundancy_row: dict[str, Any],
) -> list[str]:
    labels = set(failures)
    candidate_id = str(row.get("candidate_id", ""))
    formula = str(row.get("formula", ""))
    family = _candidate_family(row)
    identity = f"{candidate_id}|{family}|{formula}"

    if "high_mean_drawdown" in labels or "extreme_row_drawdown" in labels:
        labels.add("drawdown_fragility")
    if _lt(row.get("validation_mean_sharpe", ""), 0.0):
        labels.add("weak_validation_window")
    if _lt(row.get("blind_mean_sharpe", ""), 0.0):
        labels.add("weak_blind_window")
    if _diagnostic_is_weak(diagnostic_row):
        labels.add("eth_diagnostic_weakness")
    if "funding_return" in identity or "funding" in identity:
        labels.add("funding_confirmation_fragility")
    if "trend" in identity:
        labels.add("trend_quality_fragility")
    if "liquidity" in identity:
        labels.add("liquidity_adjusted_momentum_fragility")
    if "intrabar" in identity:
        labels.add("intrabar_conviction_fragility")
    if redundancy_row.get("redundancy_verdict") == "redundant_research_memory_only":
        labels.add("bundle_redundancy")
    if _gte(redundancy_row.get("max_abs_component_corr", ""), 0.80):
        labels.add("component_overlap")
    return sorted(label for label in labels if label)


def _diagnostic_is_weak(row: dict[str, Any]) -> bool:
    if not row:
        return False
    if str(row.get("review_verdict", "")) and str(row.get("review_verdict", "")) != "research_watchlist":
        return True
    if _split_labels(row.get("failure_reasons", "")):
        return True
    return _lt(row.get("validation_mean_sharpe", ""), 0.0) or _lt(row.get("blind_mean_sharpe", ""), 0.0)


def _kill_reasons(failures: list[str], labels: list[str], verdict: str) -> list[str]:
    if verdict == "research_1_0_candidate_pending_replication":
        return []
    if failures:
        return failures
    priority = [
        "eth_diagnostic_weakness",
        "bundle_redundancy",
        "component_overlap",
        "drawdown_fragility",
        "weak_validation_window",
        "weak_blind_window",
    ]
    return [label for label in priority if label in labels]


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
