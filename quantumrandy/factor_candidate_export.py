from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from .io_utils import safe_write_csv, safe_write_json, safe_write_text

PRIMARY_SELECTOR_V082_FORMULAS = [
    "zscore(ema(volume,48),120)",
    "zscore(ema(volume,24),96)",
    "zscore(ema(volume,24),120)",
    "zscore(ema(volume,36),144)",
    "zscore(std(close,48),120)",
    "zscore(std(close,48),144)",
    "zscore(std(close,36),144)",
]

SELECTOR_V082_PARENT_FORMULAS = {
    "qr_7a765d304b": "zscore(sub(sma(close,12),sma(close,48)),48)",
    "qr_4a7fa246c2": "neg(zscore(div(funding_rate,std(close,48)),120))",
    "qr_ccda5f2f68": "zscore(corr(funding_rate,volume,48),96)",
}

CONFLICT_AWARE_FAMILY_PAIRS = {
    ("funding_interaction", "volume_liquidity"),
    ("funding_interaction", "range_volatility"),
    ("price", "volume_liquidity"),
}


def export_selector_v082_factor_candidates(
    evidence_summary_dir: str | Path,
    out_dir: str | Path,
    *,
    formulas: list[str] | None = None,
    intended_scope: str = "multi_asset_crypto_4h_research",
    applicability_hypothesis: str = "Multi-asset 4h crypto perpetual research candidate.",
    out_of_scope_policy: str = "diagnostic_only",
    selector_evidence_window: str = "attempts_4_60",
    randyslab_eval_profile: str = "strict4h_v1",
    created_from_report: str | Path | None = None,
) -> dict[str, Any]:
    summary_root = Path(evidence_summary_dir)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    formulas = formulas or PRIMARY_SELECTOR_V082_FORMULAS
    created_from_report = created_from_report or summary_root.as_posix()

    candidates = _read_csv(summary_root / "selector_pipeline_candidate_evidence_summary.csv")
    negatives = _read_csv(summary_root / "selector_pipeline_negative_candidate_summary.csv")
    records = _build_export_records(
        candidates,
        negatives,
        formulas=formulas,
        intended_scope=intended_scope,
        applicability_hypothesis=applicability_hypothesis,
        out_of_scope_policy=out_of_scope_policy,
        selector_evidence_window=selector_evidence_window,
        randyslab_eval_profile=randyslab_eval_profile,
        created_from_report=Path(created_from_report).as_posix(),
    )

    jsonl_path = out / "factor_candidates.jsonl"
    csv_path = out / "factor_candidates.csv"
    manifest_path = out / "factor_candidate_export_manifest.json"
    report_path = out / "FACTOR_CANDIDATE_EXPORT.md"
    events_path = out / "events.jsonl"

    safe_write_text(
        jsonl_path,
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        events_path,
    )
    safe_write_csv(csv_path, _records_to_csv_frame(records), events_path)
    manifest = {
        "artifact_type": "quantumrandy_factor_candidate_export_manifest",
        "schema_version": 1,
        "safety": {
            "research_only": True,
            "not_runtime_publish_payload": True,
            "does_not_update_runtime": True,
            "does_not_auto_admit_factors": True,
            "no_live_execution": True,
            "does_not_create_portfolio_scheduler": True,
        },
        "scope_contract": {
            "intended_scope": intended_scope,
            "applicability_hypothesis": applicability_hypothesis,
            "out_of_scope_policy": out_of_scope_policy,
        },
        "future_portfolio_interface": {
            "consumer_project": "RandyPortfolio",
            "status": "interface_only_not_implemented",
            "allowed_use": "research_artifact_input",
            "forbidden_use": "runtime_allocation_or_live_execution",
        },
        "source": {
            "evidence_summary_dir": summary_root.as_posix(),
            "selector_evidence_window": selector_evidence_window,
            "created_from_report": Path(created_from_report).as_posix(),
        },
        "candidate_count": len(records),
        "formula_count_requested": len(formulas),
        "missing_formulas": [formula for formula in formulas if formula not in {r["formula"] for r in records}],
        "outputs": {
            "jsonl": jsonl_path.as_posix(),
            "csv": csv_path.as_posix(),
            "markdown": report_path.as_posix(),
            "manifest": manifest_path.as_posix(),
        },
    }
    safe_write_json(manifest_path, manifest, events_path)
    safe_write_text(report_path, render_factor_candidate_export_report(manifest, records), events_path)
    return manifest


def render_factor_candidate_export_report(manifest: dict[str, Any], records: list[dict[str, Any]]) -> str:
    lines = [
        "# QuantumRandy Factor Candidate Export",
        "",
        "This is a research-only factor-candidate export. It is not a runtime publish payload, admission decision,",
        "portfolio construction step, or live execution plan.",
        "",
        "## Summary",
        "",
        f"- Candidate rows: `{manifest.get('candidate_count', 0)}`",
        f"- Evidence window: `{(manifest.get('source') or {}).get('selector_evidence_window', '')}`",
        f"- RandysLab evaluation profile: `{_report_eval_profile(records)}`",
        f"- Intended scope: `{(manifest.get('scope_contract') or {}).get('intended_scope', '')}`",
        f"- Out-of-scope policy: `{(manifest.get('scope_contract') or {}).get('out_of_scope_policy', '')}`",
        f"- JSONL: `{(manifest.get('outputs') or {}).get('jsonl', '')}`",
        f"- CSV mirror: `{(manifest.get('outputs') or {}).get('csv', '')}`",
        "- RandyPortfolio interface contract: `"
        f"{(manifest.get('future_portfolio_interface') or {}).get('status', '')}`",
        "",
        "## Candidates",
        "",
    ]
    if not records:
        lines.append("No candidates were exported.")
    else:
        lines.append(
            "| Candidate | Tier | Family | LLM true-improved | Best pass delta | Best Sharpe delta | "
            "Conflict | Formula |"
        )
        lines.append("|---|---|---|---:|---:|---:|---|---|")
        for record in records:
            lines.append(
                "| "
                f"`{record['candidate_id']}` | "
                f"`{record['candidate_tier']}` | "
                f"`{record['formula_family']}` | "
                f"{record['llm_true_improved_count']} | "
                f"{float(record['best_pass_rate_delta']):.2f} | "
                f"{float(record['best_mean_sharpe_delta']):.2f} | "
                f"`{record['negative_family_conflict']}` | "
                f"`{record['formula']}` |"
            )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- Exported formulas require strict RandysLab judging before any downstream decision.",
            "- The export does not modify runtime strategies or publish factors.",
            "- Conflict flags are sign/window/family cautions, not global family bans.",
        ]
    )
    return "\n".join(lines) + "\n"


def _build_export_records(
    candidates: pd.DataFrame,
    negatives: pd.DataFrame,
    *,
    formulas: list[str],
    intended_scope: str,
    applicability_hypothesis: str,
    out_of_scope_policy: str,
    selector_evidence_window: str,
    randyslab_eval_profile: str,
    created_from_report: str,
) -> list[dict[str, Any]]:
    if candidates.empty:
        return []
    records: list[dict[str, Any]] = []
    for formula in formulas:
        rows = candidates[candidates["formula"].fillna("") == formula].copy()
        if rows.empty:
            continue
        rows["_llm_true_improved_count"] = _numeric_column(rows, "llm_true_improved_count")
        rows["_highlight_count"] = _numeric_column(rows, "highlight_count")
        rows["_best_pass_rate_delta"] = _numeric_column(rows, "best_pass_rate_delta")
        rows["_best_mean_sharpe_delta"] = _numeric_column(rows, "best_mean_sharpe_delta")
        rows = rows.sort_values(
            ["_llm_true_improved_count", "_highlight_count", "_best_pass_rate_delta", "_best_mean_sharpe_delta"],
            ascending=[False, False, False, False],
        )
        best = rows.iloc[0].to_dict()
        parent_id = str(best.get("parent_factor_id", ""))
        parent_formula = SELECTOR_V082_PARENT_FORMULAS.get(parent_id, "")
        formula_family = _formula_family(formula)
        parent_family = _formula_family(parent_formula)
        negative_conflict = _has_negative_family_conflict(negatives, parent_family, formula_family)
        llm_true_count = int(rows["_llm_true_improved_count"].sum())
        highlight_count = int(_numeric_column(rows, "highlight_count").sum())
        records.append(
            {
                "artifact_type": "quantumrandy_factor_candidate_export",
                "schema_version": 1,
                "research_only": True,
                "not_runtime_publish_payload": True,
                "candidate_id": str(best.get("factor_id", "")),
                "formula": formula,
                "formula_family": formula_family,
                "intended_scope": intended_scope,
                "applicability_hypothesis": applicability_hypothesis,
                "out_of_scope_policy": out_of_scope_policy,
                "portfolio_interface_contract": {
                    "consumer_project": "RandyPortfolio",
                    "status": "interface_only_not_implemented",
                    "allowed_use": "research_artifact_input",
                    "forbidden_use": "runtime_allocation_or_live_execution",
                },
                "generation_source": str(best.get("rewrite_generation_source", "")),
                "selector_evidence_window": selector_evidence_window,
                "parent_factor_id": parent_id,
                "parent_formula": parent_formula,
                "parent_formula_family": parent_family,
                "evidence_parent_factor_ids": "|".join(_unique_sorted(rows.get("parent_factor_id", []))),
                "llm_true_improved_count": llm_true_count,
                "highlight_count": highlight_count,
                "coverage_only_trap_count": int(
                    _numeric_column(rows, "coverage_only_trap_count").sum()
                ),
                "sharpe_improved_no_pass_lift_count": int(
                    _numeric_column(rows, "sharpe_improved_no_pass_lift_count").sum()
                ),
                "best_pass_rate_delta": float(rows["_best_pass_rate_delta"].max()),
                "best_mean_sharpe_delta": float(rows["_best_mean_sharpe_delta"].max()),
                "mean_pass_rate_delta": float(
                    _numeric_column(rows, "mean_pass_rate_delta").mean()
                ),
                "mean_sharpe_delta": float(
                    _numeric_column(rows, "mean_sharpe_delta").mean()
                ),
                "failed_assets_examples": "|".join(_unique_sorted(rows.get("failed_assets_examples", []))),
                "negative_family_conflict": negative_conflict,
                "conflict_notes": _conflict_notes(parent_family, formula_family, formula, negative_conflict),
                "required_features": _required_features(formula),
                "candidate_tier": _candidate_tier(llm_true_count, highlight_count),
                "randyslab_eval_profile": randyslab_eval_profile,
                "created_from_report": created_from_report,
            }
        )
    return sorted(
        records,
        key=lambda row: (
            -int(row["llm_true_improved_count"]),
            -int(row["highlight_count"]),
            str(row["formula"]),
        ),
    )


def _records_to_csv_frame(records: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for record in records:
        row = dict(record)
        row["required_features"] = "|".join(record.get("required_features", []))
        if isinstance(row.get("portfolio_interface_contract"), dict):
            row["portfolio_interface_contract"] = json.dumps(
                row["portfolio_interface_contract"], ensure_ascii=True, sort_keys=True
            )
        rows.append(row)
    return pd.DataFrame(rows)


def _report_eval_profile(records: list[dict[str, Any]]) -> str:
    profiles = _unique_sorted(record.get("randyslab_eval_profile", "") for record in records)
    return "|".join(profiles) if profiles else ""


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path).fillna("")
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def _numeric_column(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series([0] * len(frame), index=frame.index, dtype="float64")
    return pd.to_numeric(frame[column], errors="coerce").fillna(0)


def _formula_family(formula: str) -> str:
    text = str(formula)
    has_funding = "funding_rate" in text
    has_price = any(field in text for field in ("open", "high", "low", "close"))
    has_volume = "volume" in text
    if has_funding and not has_price and not has_volume:
        return "pure_funding"
    if has_funding:
        return "funding_interaction"
    if "std(" in text or "sub(high,low)" in text:
        return "range_volatility"
    if has_volume:
        return "volume_liquidity"
    if has_price:
        return "price"
    return "other"


def _required_features(formula: str) -> list[str]:
    fields = ["open", "high", "low", "close", "volume", "funding_rate"]
    found = [field for field in fields if re.search(rf"\b{re.escape(field)}\b", formula)]
    return found


def _candidate_tier(llm_true_improved_count: int, highlight_count: int) -> str:
    if llm_true_improved_count >= 4 and highlight_count >= 4:
        return "primary"
    if llm_true_improved_count >= 2:
        return "secondary"
    return "exploratory"


def _has_negative_family_conflict(negatives: pd.DataFrame, parent_family: str, candidate_family: str) -> bool:
    if negatives.empty:
        return (parent_family, candidate_family) in CONFLICT_AWARE_FAMILY_PAIRS
    rows = negatives[
        (negatives["parent_formula_family"].fillna("") == parent_family)
        & (negatives["candidate_formula_family"].fillna("") == candidate_family)
    ].copy()
    if rows.empty:
        return False
    negative_count = _numeric_column(rows, "negative_count").max()
    true_count = _numeric_column(rows, "true_improved_count").max()
    return bool(negative_count > 0 and true_count > 0)


def _conflict_notes(parent_family: str, formula_family: str, formula: str, has_conflict: bool) -> str:
    if not has_conflict:
        return (
            "No family-level positive/negative conflict flagged in evidence60 summary; still requires strict judging."
        )
    if formula_family == "volume_liquidity" and "ema(volume" in formula and "neg(" not in formula:
        return (
            "Family has mixed evidence, but this candidate is a positive smoothed participation shape; avoid raw, "
            "delta, and negative-volume variants."
        )
    if formula_family == "range_volatility" and "std(close" in formula and "neg(" not in formula:
        return (
            "Family has mixed evidence, but this candidate is a positive realized-volatility state; avoid negative "
            "range/volatility signs."
        )
    return "Family has mixed positive and negative selector evidence; treat shape, sign, and window as decisive."


def _unique_sorted(values: Any) -> list[str]:
    out: set[str] = set()
    for value in values:
        text = str(value).strip()
        if text:
            out.add(text)
    return sorted(out)
