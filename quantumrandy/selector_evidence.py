from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from .io_utils import safe_write_csv, safe_write_json, safe_write_text


def summarize_selector_pipeline_runs(
    pipeline_dirs: list[str | Path],
    out_dir: str | Path,
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows = [_summarize_run(Path(path)) for path in pipeline_dirs]
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.sort_values(
            ["is_llm_true_improvement_evidence", "is_llm_policy_evidence", "llm_true_improved_count"],
            ascending=[False, False, False],
        ).reset_index(drop=True)
    manifest = {
        "artifact_type": "quantumrandy_selector_pipeline_evidence_summary",
        "schema_version": 1,
        "safety": {
            "research_only": True,
            "not_runtime_publish_payload": True,
            "does_not_update_runtime": True,
            "does_not_auto_admit_factors": True,
        },
        "run_count": len(rows),
        "llm_policy_evidence_runs": _count_true(rows, "is_llm_policy_evidence"),
        "llm_true_improvement_evidence_runs": _count_true(rows, "is_llm_true_improvement_evidence"),
        "coverage_only_trap_runs": sum(1 for row in rows if int(row.get("coverage_only_trap_count", 0)) > 0),
        "source_run_dirs": [Path(path).as_posix() for path in pipeline_dirs],
        "outputs": {
            "summary_csv": (out / "selector_pipeline_evidence_summary.csv").as_posix(),
            "summary_markdown": (out / "SELECTOR_PIPELINE_EVIDENCE_SUMMARY.md").as_posix(),
            "manifest": (out / "selector_pipeline_evidence_manifest.json").as_posix(),
        },
    }
    safe_write_csv(out / "selector_pipeline_evidence_summary.csv", frame, out / "events.jsonl")
    safe_write_json(out / "selector_pipeline_evidence_manifest.json", manifest, out / "events.jsonl")
    safe_write_text(
        out / "SELECTOR_PIPELINE_EVIDENCE_SUMMARY.md",
        render_selector_pipeline_evidence_summary(manifest, frame),
        out / "events.jsonl",
    )
    return manifest


def render_selector_pipeline_evidence_summary(manifest: dict[str, Any], summary: pd.DataFrame) -> str:
    lines = [
        "# QuantumRandy Selector Pipeline Evidence Summary",
        "",
        "This is a research audit artifact only. It is not an admission decision or runtime publish payload.",
        "",
        "## Summary",
        "",
        f"- Runs: `{manifest.get('run_count', 0)}`",
        f"- LLM policy evidence runs: `{manifest.get('llm_policy_evidence_runs', 0)}`",
        f"- LLM true-improvement evidence runs: `{manifest.get('llm_true_improvement_evidence_runs', 0)}`",
        f"- Runs with coverage-only traps: `{manifest.get('coverage_only_trap_runs', 0)}`",
        "",
        "## Runs",
        "",
    ]
    if summary.empty:
        lines.append("No selector pipeline runs were summarized.")
    else:
        lines.append(
            "| Run | LLM Evidence | LLM True Improvement | LLM True Improved | Coverage Traps | "
            "Candidate Sources | Highlight Sources | Best LLM True Improved |"
        )
        lines.append("|---|---:|---:|---:|---:|---|---|---|")
        for row in summary.to_dict(orient="records"):
            best = row.get("best_llm_true_improved_factor_id", "")
            formula = row.get("best_llm_true_improved_formula", "")
            best_cell = "`none`" if not best else f"`{best}` `{_short_formula(formula)}`"
            lines.append(
                "| "
                f"`{row.get('run_id', '')}` | "
                f"`{row.get('is_llm_policy_evidence', False)}` | "
                f"`{row.get('is_llm_true_improvement_evidence', False)}` | "
                f"{int(row.get('llm_true_improved_count', 0) or 0)} | "
                f"{int(row.get('coverage_only_trap_count', 0) or 0)} | "
                f"`{row.get('candidate_source_mix', '') or 'none'}` | "
                f"`{row.get('candidate_highlight_source_mix', '') or 'none'}` | "
                f"{best_cell} |"
            )
    lines.extend(
        [
            "",
            "## Files",
            "",
            "- `selector_pipeline_evidence_summary.csv`: one row per selector pipeline run.",
            "- `selector_pipeline_evidence_manifest.json`: machine-readable aggregate metadata.",
            "- `SELECTOR_PIPELINE_EVIDENCE_SUMMARY.md`: this human-readable audit summary.",
        ]
    )
    return "\n".join(lines) + "\n"


def _summarize_run(path: Path) -> dict[str, Any]:
    manifest = _read_json(path / "selector_rewrite_pipeline_manifest.json")
    rewrite = manifest.get("rewrite", {}) if isinstance(manifest, dict) else {}
    review = manifest.get("review", {}) if isinstance(manifest, dict) else {}
    highlights = _read_csv(path / "review" / "selector_pipeline_candidate_highlights.csv")
    llm_true_improved = _filter_highlights(
        highlights,
        highlight_type="true_improved",
        generation_source="llm_rewrite",
    )
    coverage_only = _filter_highlights(highlights, highlight_type="coverage_only_trap")
    best = _best_highlight(llm_true_improved)
    llm_true_improved_count = int(review.get("llm_true_improved_count") or len(llm_true_improved))
    is_llm_true_improvement = bool(
        review.get("is_llm_true_improvement_evidence", False) or llm_true_improved_count > 0
    )
    return {
        "run_id": path.name,
        "run_dir": path.as_posix(),
        "selector_path": manifest.get("selector_path", ""),
        "window": manifest.get("window", ""),
        "rewrite_candidate_count": int(rewrite.get("candidate_count", 0) or 0),
        "llm_rewrite_accepted": int(rewrite.get("llm_rewrite_accepted", 0) or 0),
        "fallback_rewrite_accepted": int(rewrite.get("fallback_rewrite_accepted", 0) or 0),
        "allow_local_fallback": bool(rewrite.get("allow_local_fallback", True)),
        "is_llm_policy_evidence": bool(rewrite.get("is_llm_policy_evidence", False)),
        "llm_error_count": int(rewrite.get("llm_error_count", 0) or 0),
        "review_status": review.get("status", ""),
        "universe_status": (manifest.get("universe", {}) or {}).get("status", ""),
        "portfolio_universe_status": (manifest.get("portfolio_universe", {}) or {}).get("status", ""),
        "candidate_review_rows": int(review.get("candidate_review_rows", 0) or 0),
        "candidate_verdict_mix": _format_counts(review.get("candidate_verdict_counts", {})),
        "candidate_source_mix": _format_counts(review.get("candidate_generation_source_counts", {})),
        "candidate_highlight_mix": _format_counts(review.get("candidate_highlight_counts", {})),
        "candidate_highlight_source_mix": _format_counts(
            review.get("candidate_highlight_generation_source_counts", {})
        ),
        "llm_true_improved_count": llm_true_improved_count,
        "is_llm_true_improvement_evidence": is_llm_true_improvement,
        "coverage_only_trap_count": len(coverage_only),
        "best_llm_true_improved_factor_id": best.get("factor_id", ""),
        "best_llm_true_improved_parent_id": best.get("parent_factor_id", ""),
        "best_llm_true_improved_pass_rate_delta": _num(best.get("pass_rate_delta", "")),
        "best_llm_true_improved_mean_sharpe_delta": _num(best.get("mean_sharpe_delta", "")),
        "best_llm_true_improved_failed_assets": best.get("candidate_failed_assets", ""),
        "best_llm_true_improved_formula": best.get("formula", ""),
    }


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path).fillna("")
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def _filter_highlights(
    frame: pd.DataFrame,
    *,
    highlight_type: str,
    generation_source: str | None = None,
) -> pd.DataFrame:
    if frame.empty or "highlight_type" not in frame.columns:
        return pd.DataFrame()
    rows = frame[frame["highlight_type"].fillna("") == highlight_type].copy()
    if generation_source is not None:
        if "rewrite_generation_source" not in rows.columns:
            return pd.DataFrame()
        rows = rows[rows["rewrite_generation_source"].fillna("") == generation_source].copy()
    return rows


def _best_highlight(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {}
    for column in ("pass_rate_delta", "mean_sharpe_delta", "candidate_mean_sharpe"):
        if column not in frame.columns:
            frame[column] = 0.0
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0.0)
    frame = frame.sort_values(
        ["pass_rate_delta", "mean_sharpe_delta", "candidate_mean_sharpe"],
        ascending=[False, False, False],
    )
    return frame.iloc[0].to_dict()


def _format_counts(counts: Any) -> str:
    if not isinstance(counts, dict) or not counts:
        return ""
    return "|".join(f"{key}:{value}" for key, value in counts.items() if value)


def _count_true(rows: list[dict[str, Any]], key: str) -> int:
    return sum(1 for row in rows if bool(row.get(key, False)))


def _num(value: Any) -> float:
    try:
        if value == "":
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _short_formula(value: Any, *, max_len: int = 72) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."
