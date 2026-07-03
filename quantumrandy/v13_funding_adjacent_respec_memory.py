from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .failure_memory import write_failure_memory
from .io_utils import safe_write_csv

V13_FUNDING_ADJACENT_RESPEC_DESCRIPTION = "Research v1.3 funding-adjacent scoped re-spec robustness variant."
V13_FUNDING_ADJACENT_RESPEC_FAILURE_MODE = (
    "Funding-adjacent v1.3 robustness variants may fail through redundancy with the Research 1.0 survivor, "
    "blind-window weakness, fee or funding stress fragility, BTC scope weakness, crash-period drawdown, "
    "or diagnostic out-of-scope concentration."
)
V13_FAILURE_MEMORY_EXTRA_COLUMNS = [
    "funding_adjacent_status",
    "independence_claim",
    "source_robustness_dir",
    "stress_survival",
    "stress_survival_score",
    "blind_sharpe",
    "worst_max_dd",
]
V13_BOOKKEEPING_LABELS = {
    "funding_adjacent_respec",
    "funding_adjacent_family",
}


def build_v1_3_funding_adjacent_respec_memory_rows(
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
                "candidate_family": "research_v1_3_funding_adjacent_respec_variant",
                "funding_adjacent_status": "funding_adjacent_not_independent_non_funding",
                "independence_claim": "none_funding_adjacent_locality_probe",
                "description": V13_FUNDING_ADJACENT_RESPEC_DESCRIPTION,
                "hypothesis": f"{candidate_id} funding-adjacent v1.3 respec variant {variant_id}.",
                "expected_failure_mode": V13_FUNDING_ADJACENT_RESPEC_FAILURE_MODE,
                "intended_scope": raw.get("intended_scope", "BTCUSDT_4h") or "BTCUSDT_4h",
                "out_of_scope_policy": "diagnostic_only",
                "conservative_verdict": verdict,
                "passed": passed,
                "kill_reasons": [] if passed else _kill_reasons(raw),
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


def write_v1_3_funding_adjacent_respec_failure_memory(
    ranking_csv: str | Path,
    out_dir: str | Path,
    *,
    source_robustness_dir: str,
) -> dict[str, Any]:
    rows = build_v1_3_funding_adjacent_respec_memory_rows(
        ranking_csv,
        source_robustness_dir=source_robustness_dir,
    )
    manifest = write_failure_memory(rows, out_dir)
    _enrich_failure_memory_csv(rows, out_dir)
    return manifest


def _labels(row: dict[str, Any]) -> list[str]:
    labels = set(_split_labels(row.get("robustness_labels", "")))
    labels.update(_split_labels(row.get("failure_reasons", "")))
    labels.update(_split_labels(row.get("diagnostic_failure_reasons", "")))
    labels.add("funding_adjacent_respec")
    labels.add("funding_adjacent_family")
    stress_survival_score = _float(row.get("stress_survival_score", ""))
    if isinstance(stress_survival_score, float) and stress_survival_score < 1.0:
        labels.add("replication_stress_fragility")
    return sorted(label for label in labels if label)


def _kill_reasons(row: dict[str, Any]) -> list[str]:
    reasons = _without_bookkeeping(_split_labels(row.get("failure_reasons", "")))
    if reasons:
        return reasons
    reasons = _without_bookkeeping(_split_labels(row.get("diagnostic_failure_reasons", "")))
    reasons.extend(_without_bookkeeping(_split_labels(row.get("robustness_labels", "")), existing=reasons))
    if reasons:
        return reasons
    verdict = str(row.get("conservative_verdict", "")).strip()
    if verdict:
        return [verdict]
    return ["blocked_pending_new_hypotheses"]


def _enrich_failure_memory_csv(rows: list[dict[str, Any]], out_dir: str | Path) -> None:
    failed_rows = {str(row.get("candidate_id", "")): row for row in rows if row.get("passed") is False}
    if not failed_rows:
        return
    out = Path(out_dir)
    failure_path = out / "failure_memory.csv"
    failure_memory = pd.read_csv(failure_path)
    for column in V13_FAILURE_MEMORY_EXTRA_COLUMNS:
        failure_memory[column] = failure_memory["candidate_id"].map(
            lambda candidate_id, column=column: failed_rows.get(str(candidate_id), {}).get(column, "")
        )
    safe_write_csv(failure_path, failure_memory, out / "events.jsonl")


def _without_bookkeeping(labels: list[str], *, existing: list[str] | None = None) -> list[str]:
    seen = set(existing or [])
    real_labels = []
    for label in labels:
        if label in V13_BOOKKEEPING_LABELS or label in seen:
            continue
        real_labels.append(label)
        seen.add(label)
    return real_labels


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
