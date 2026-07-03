from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .failure_memory import write_failure_memory

RESEARCH10_REPLICATION_DESCRIPTION = "Research 1.0 candidate replication robustness variant."
RESEARCH10_REPLICATION_FAILURE_MODE = (
    "Candidate variants may fail Research 1.0 replication through stress fragility, weak validation or blind windows, "
    "fee/funding sensitivity, crash drawdown, or out-of-scope asset concentration."
)


def build_research10_replication_failure_memory_rows(
    ranking_csv: str | Path,
    *,
    source_robustness_dir: str,
) -> list[dict[str, Any]]:
    ranking = pd.read_csv(ranking_csv).fillna("")
    rows: list[dict[str, Any]] = []
    for raw in ranking.to_dict(orient="records"):
        candidate_id = str(raw.get("candidate_id", ""))
        variant_id = str(raw.get("variant_id", "default") or "default")
        labels = _labels(raw)
        verdict = str(raw.get("conservative_verdict", ""))
        passed = verdict == "research_watchlist"
        rows.append(
            {
                "candidate_id": f"{candidate_id}::{variant_id}",
                "formula": raw.get("formula", ""),
                "candidate_family": "research_1_0_replication_variant",
                "description": RESEARCH10_REPLICATION_DESCRIPTION,
                "hypothesis": f"{candidate_id} replication variant {variant_id}.",
                "expected_failure_mode": RESEARCH10_REPLICATION_FAILURE_MODE,
                "intended_scope": "BTCUSDT_4h",
                "out_of_scope_policy": "diagnostic_only",
                "conservative_verdict": verdict,
                "passed": passed,
                "kill_reasons": [] if passed else _kill_reasons(raw, labels),
                "failure_labels": "|".join(labels),
                "source_review_dir": source_robustness_dir,
                "source_robustness_dir": source_robustness_dir,
                "stress_survival": _stress_survival(raw),
                "stress_survival_score": _float(raw.get("stress_survival_score", "")),
                "sharpe": _float(raw.get("mean_sharpe", "")),
                "validation_sharpe": _float(raw.get("validation_mean_sharpe", "")),
                "blind_sharpe": _float(raw.get("blind_mean_sharpe", "")),
                "max_dd": _float(raw.get("mean_max_dd", "")),
                "worst_max_dd": _float(raw.get("worst_max_dd", "")),
            }
        )
    return rows


def write_research10_replication_failure_memory(
    ranking_csv: str | Path,
    out_dir: str | Path,
    *,
    source_robustness_dir: str,
) -> dict[str, Any]:
    rows = build_research10_replication_failure_memory_rows(
        ranking_csv,
        source_robustness_dir=source_robustness_dir,
    )
    return write_failure_memory(rows, out_dir)


def _labels(row: dict[str, Any]) -> list[str]:
    labels = set(_split_labels(row.get("robustness_labels", "")))
    labels.update(_split_labels(row.get("failure_reasons", "")))
    if _float(row.get("stress_survival_score", "")) < 1.0:
        labels.add("replication_stress_fragility")
    return sorted(label for label in labels if label)


def _kill_reasons(row: dict[str, Any], labels: list[str]) -> list[str]:
    reasons = _split_labels(row.get("failure_reasons", ""))
    if reasons:
        return reasons
    return labels


def _stress_survival(row: dict[str, Any]) -> str:
    survived = _int(row.get("stress_survival_count", ""))
    total = _int(row.get("stress_count", ""))
    return f"{survived}/{total}"


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


def _int(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0
