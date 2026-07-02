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
    run_paths = [Path(path) for path in pipeline_dirs]
    rows = [_summarize_run(path) for path in run_paths]
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.sort_values(
            ["is_llm_true_improvement_evidence", "is_llm_policy_evidence", "llm_true_improved_count"],
            ascending=[False, False, False],
        ).reset_index(drop=True)
    candidate_frame = _summarize_highlight_candidates(run_paths)
    negative_frame = _summarize_negative_candidates(run_paths)
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
        "candidate_highlight_rows": int(candidate_frame["highlight_count"].sum()) if not candidate_frame.empty else 0,
        "candidate_summary_rows": len(candidate_frame),
        "negative_candidate_rows": int(negative_frame["negative_count"].sum()) if not negative_frame.empty else 0,
        "negative_family_rows": len(negative_frame),
        "source_run_dirs": [path.as_posix() for path in run_paths],
        "outputs": {
            "summary_csv": (out / "selector_pipeline_evidence_summary.csv").as_posix(),
            "candidate_summary_csv": (out / "selector_pipeline_candidate_evidence_summary.csv").as_posix(),
            "negative_candidate_summary_csv": (
                out / "selector_pipeline_negative_candidate_summary.csv"
            ).as_posix(),
            "summary_markdown": (out / "SELECTOR_PIPELINE_EVIDENCE_SUMMARY.md").as_posix(),
            "manifest": (out / "selector_pipeline_evidence_manifest.json").as_posix(),
        },
    }
    safe_write_csv(out / "selector_pipeline_evidence_summary.csv", frame, out / "events.jsonl")
    safe_write_csv(out / "selector_pipeline_candidate_evidence_summary.csv", candidate_frame, out / "events.jsonl")
    safe_write_csv(out / "selector_pipeline_negative_candidate_summary.csv", negative_frame, out / "events.jsonl")
    safe_write_json(out / "selector_pipeline_evidence_manifest.json", manifest, out / "events.jsonl")
    safe_write_text(
        out / "SELECTOR_PIPELINE_EVIDENCE_SUMMARY.md",
        render_selector_pipeline_evidence_summary(manifest, frame, candidate_frame, negative_frame),
        out / "events.jsonl",
    )
    return manifest


def load_selector_negative_prompt_context(
    path: str | Path | None,
    *,
    max_examples: int = 5,
    max_families: int = 5,
    max_disallowed_formulas: int = 20,
    max_blocked_family_pairs: int = 20,
    min_block_count: int = 3,
) -> dict[str, Any]:
    if not path:
        return {
            "available": False,
            "examples": [],
            "families": [],
            "disallowed_formulas": [],
            "blocked_family_pairs": [],
        }
    root = Path(path)
    negative_path = (
        root / "selector_pipeline_negative_candidate_summary.csv"
        if root.is_dir()
        else root
    )
    frame = _read_csv(negative_path)
    if frame.empty:
        return {
            "available": False,
            "source": root.as_posix(),
            "examples": [],
            "families": [],
            "disallowed_formulas": [],
            "blocked_family_pairs": [],
        }
    rows = frame.to_dict(orient="records")
    examples = [
        {
            "parent_formula_family": str(row.get("parent_formula_family", "")),
            "candidate_formula_family": str(row.get("candidate_formula_family", "")),
            "example_formula": str(row.get("example_formula", "")),
            "avg_pass_rate_delta": str(row.get("avg_pass_rate_delta", "")),
            "avg_mean_sharpe_delta": str(row.get("avg_mean_sharpe_delta", "")),
            "run_ids": str(row.get("run_ids", "")),
        }
        for row in rows[:max_examples]
    ]
    families = [
        {
            "parent_formula_family": str(row.get("parent_formula_family", "")),
            "candidate_formula_family": str(row.get("candidate_formula_family", "")),
            "negative_count": str(row.get("negative_count", "")),
            "true_improved_count": str(row.get("true_improved_count", "")),
            "avg_mean_sharpe_delta": str(row.get("avg_mean_sharpe_delta", "")),
            "worst_mean_sharpe_delta": str(row.get("worst_mean_sharpe_delta", "")),
        }
        for row in rows[:max_families]
    ]
    disallowed_formulas = _negative_disallowed_formula_rows(rows, max_items=max_disallowed_formulas)
    blocked_family_pairs = _negative_blocked_family_pair_rows(
        rows,
        max_items=max_blocked_family_pairs,
        min_count=min_block_count,
    )
    return {
        "available": bool(examples or families or disallowed_formulas or blocked_family_pairs),
        "source": root.as_posix(),
        "examples": examples,
        "families": families,
        "disallowed_formulas": disallowed_formulas,
        "blocked_family_pairs": blocked_family_pairs,
    }


def render_selector_pipeline_evidence_summary(
    manifest: dict[str, Any],
    summary: pd.DataFrame,
    candidate_summary: pd.DataFrame | None = None,
    negative_summary: pd.DataFrame | None = None,
) -> str:
    candidate_summary = candidate_summary if candidate_summary is not None else pd.DataFrame()
    negative_summary = negative_summary if negative_summary is not None else pd.DataFrame()
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
        f"- Highlighted candidate rows: `{manifest.get('candidate_highlight_rows', 0)}`",
        f"- Distinct highlighted candidates: `{manifest.get('candidate_summary_rows', 0)}`",
        f"- Negative candidate rows: `{manifest.get('negative_candidate_rows', 0)}`",
        f"- Negative candidate family rows: `{manifest.get('negative_family_rows', 0)}`",
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
    lines.extend(["", "## Highlighted Candidates Across Runs", ""])
    if candidate_summary.empty:
        lines.append("No highlighted selector candidates were summarized.")
    else:
        lines.append(
            "| Candidate | Source | Parent | Highlights | LLM True Improved | Coverage Traps | Runs | Best Delta | Formula |"
        )
        lines.append("|---|---|---|---:|---:|---:|---|---:|---|")
        for row in candidate_summary.head(12).to_dict(orient="records"):
            lines.append(
                "| "
                f"`{row.get('factor_id', '')}` | "
                f"`{row.get('rewrite_generation_source', '')}` | "
                f"`{row.get('parent_factor_id', '')}` | "
                f"{int(row.get('highlight_count', 0) or 0)} | "
                f"{int(row.get('llm_true_improved_count', 0) or 0)} | "
                f"{int(row.get('coverage_only_trap_count', 0) or 0)} | "
                f"`{row.get('run_ids', '')}` | "
                f"{_num(row.get('best_pass_rate_delta', 0.0)):.2f} | "
                f"`{_short_formula(row.get('formula', ''))}` |"
            )
    lines.extend(["", "## Negative Candidate Families", ""])
    if negative_summary.empty:
        lines.append("No negative selector candidate families were summarized.")
    else:
        lines.append(
            "| Parent Family | Candidate Family | Negatives | Sharpe Only | True Improved | Avg Pass Delta | Avg Sharpe Delta | Worst Sharpe Delta | Example |"
        )
        lines.append("|---|---|---:|---:|---:|---:|---:|---:|---|")
        for row in negative_summary.head(12).to_dict(orient="records"):
            lines.append(
                "| "
                f"`{row.get('parent_formula_family', '')}` | "
                f"`{row.get('candidate_formula_family', '')}` | "
                f"{int(row.get('negative_count', 0) or 0)} | "
                f"{int(row.get('sharpe_only_count', 0) or 0)} | "
                f"{int(row.get('true_improved_count', 0) or 0)} | "
                f"{_num(row.get('avg_pass_rate_delta', 0.0)):.2f} | "
                f"{_num(row.get('avg_mean_sharpe_delta', 0.0)):.2f} | "
                f"{_num(row.get('worst_mean_sharpe_delta', 0.0)):.2f} | "
                f"`{_short_formula(row.get('example_formula', ''))}` |"
            )
    lines.extend(
        [
            "",
            "## Files",
            "",
            "- `selector_pipeline_evidence_summary.csv`: one row per selector pipeline run.",
            "- `selector_pipeline_candidate_evidence_summary.csv`: highlighted candidate evidence aggregated across runs.",
            "- `selector_pipeline_negative_candidate_summary.csv`: not-improved LLM candidate families aggregated across runs.",
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


def _summarize_highlight_candidates(run_paths: list[Path]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for path in run_paths:
        highlights = _read_csv(path / "review" / "selector_pipeline_candidate_highlights.csv")
        if highlights.empty:
            continue
        for row in highlights.to_dict(orient="records"):
            rows.append(
                {
                    "run_id": path.name,
                    "parent_factor_id": row.get("parent_factor_id", ""),
                    "factor_id": row.get("factor_id", ""),
                    "rewrite_generation_source": row.get("rewrite_generation_source", ""),
                    "highlight_type": row.get("highlight_type", ""),
                    "pass_rate_delta": _num(row.get("pass_rate_delta", "")),
                    "mean_sharpe_delta": _num(row.get("mean_sharpe_delta", "")),
                    "candidate_mean_sharpe": _num(row.get("candidate_mean_sharpe", "")),
                    "candidate_failed_assets": row.get("candidate_failed_assets", ""),
                    "formula": row.get("formula", ""),
                }
            )
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows)
    grouped_rows: list[dict[str, Any]] = []
    group_columns = ["factor_id", "formula", "rewrite_generation_source", "parent_factor_id"]
    for group_key, group in frame.groupby(group_columns, dropna=False):
        factor_id, formula, source, parent_id = group_key
        highlight_types = group["highlight_type"].fillna("")
        run_ids = sorted(str(value) for value in group["run_id"].fillna("").unique() if str(value))
        llm_true_improved_count = int(
            ((highlight_types == "true_improved") & (group["rewrite_generation_source"] == "llm_rewrite")).sum()
        )
        grouped_rows.append(
            {
                "factor_id": factor_id,
                "parent_factor_id": parent_id,
                "rewrite_generation_source": source,
                "formula": formula,
                "highlight_count": int(len(group)),
                "true_improved_count": int((highlight_types == "true_improved").sum()),
                "llm_true_improved_count": llm_true_improved_count,
                "coverage_only_trap_count": int((highlight_types == "coverage_only_trap").sum()),
                "sharpe_improved_no_pass_lift_count": int(
                    (highlight_types == "sharpe_improved_no_pass_lift").sum()
                ),
                "run_count": len(run_ids),
                "run_ids": "|".join(run_ids),
                "best_pass_rate_delta": max(_num(value) for value in group["pass_rate_delta"]),
                "best_mean_sharpe_delta": max(_num(value) for value in group["mean_sharpe_delta"]),
                "mean_pass_rate_delta": round(float(group["pass_rate_delta"].mean()), 8),
                "mean_sharpe_delta": round(float(group["mean_sharpe_delta"].mean()), 8),
                "failed_assets_examples": "|".join(
                    sorted({str(value) for value in group["candidate_failed_assets"].fillna("") if str(value)})[:5]
                ),
            }
        )
    out = pd.DataFrame(grouped_rows)
    return out.sort_values(
        ["llm_true_improved_count", "true_improved_count", "coverage_only_trap_count", "best_pass_rate_delta"],
        ascending=[False, False, True, False],
    ).reset_index(drop=True)


def _summarize_negative_candidates(run_paths: list[Path]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    positive_rows: list[dict[str, Any]] = []
    for path in run_paths:
        review = _read_csv(path / "review" / "selector_pipeline_candidate_review.csv")
        if review.empty:
            continue
        for row in review.to_dict(orient="records"):
            if str(row.get("rewrite_generation_source", "")) != "llm_rewrite":
                continue
            verdict = str(row.get("candidate_review_verdict", ""))
            formula = str(row.get("formula", ""))
            parent_family = str(row.get("parent_formula_family", "")) or _formula_family(str(row.get("parent_formula", "")))
            candidate_family = _formula_family(formula)
            if verdict == "improved":
                positive_rows.append(
                    {
                        "run_id": path.name,
                        "parent_formula_family": parent_family,
                        "candidate_formula_family": candidate_family,
                        "pass_rate_delta": _num(row.get("pass_rate_delta", "")),
                        "mean_sharpe_delta": _num(row.get("mean_sharpe_delta", "")),
                    }
                )
                continue
            if verdict not in {"not_improved", "coverage_only", "mixed"}:
                continue
            rows.append(
                {
                    "run_id": path.name,
                    "parent_factor_id": row.get("parent_factor_id", ""),
                    "parent_formula_family": parent_family,
                    "candidate_formula_family": candidate_family,
                    "factor_id": row.get("factor_id", ""),
                    "formula": formula,
                    "candidate_review_verdict": verdict,
                    "pass_rate_delta": _num(row.get("pass_rate_delta", "")),
                    "mean_sharpe_delta": _num(row.get("mean_sharpe_delta", "")),
                    "candidate_mean_sharpe": _num(row.get("candidate_mean_sharpe", "")),
                    "candidate_failed_assets": row.get("candidate_failed_assets", ""),
                }
            )
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows)
    positive_by_family = _positive_family_evidence(positive_rows)
    grouped_rows: list[dict[str, Any]] = []
    group_columns = ["parent_formula_family", "candidate_formula_family"]
    for group_key, group in frame.groupby(group_columns, dropna=False):
        parent_family, candidate_family = group_key
        run_ids = sorted(str(value) for value in group["run_id"].fillna("").unique() if str(value))
        worst = group.sort_values(["mean_sharpe_delta", "pass_rate_delta"], ascending=[True, True]).iloc[0]
        positive = positive_by_family.get((str(parent_family), str(candidate_family)), {})
        grouped_rows.append(
            {
                "parent_formula_family": parent_family,
                "candidate_formula_family": candidate_family,
                "negative_count": int(len(group)),
                "not_improved_count": int((group["candidate_review_verdict"] == "not_improved").sum()),
                "coverage_only_count": int((group["candidate_review_verdict"] == "coverage_only").sum()),
                "sharpe_only_count": int((group["candidate_review_verdict"] == "mixed").sum()),
                "run_count": len(run_ids),
                "run_ids": "|".join(run_ids),
                "true_improved_count": int(positive.get("true_improved_count", 0)),
                "true_improved_run_ids": positive.get("true_improved_run_ids", ""),
                "best_true_improved_pass_rate_delta": positive.get("best_true_improved_pass_rate_delta", 0.0),
                "best_true_improved_mean_sharpe_delta": positive.get("best_true_improved_mean_sharpe_delta", 0.0),
                "avg_pass_rate_delta": round(float(group["pass_rate_delta"].mean()), 8),
                "avg_mean_sharpe_delta": round(float(group["mean_sharpe_delta"].mean()), 8),
                "worst_mean_sharpe_delta": round(float(group["mean_sharpe_delta"].min()), 8),
                "example_factor_id": worst.get("factor_id", ""),
                "example_formula": worst.get("formula", ""),
                "failed_assets_examples": "|".join(
                    sorted({str(value) for value in group["candidate_failed_assets"].fillna("") if str(value)})[:5]
                ),
            }
        )
    out = pd.DataFrame(grouped_rows)
    return out.sort_values(
        ["negative_count", "avg_mean_sharpe_delta", "worst_mean_sharpe_delta"],
        ascending=[False, True, True],
    ).reset_index(drop=True)


def _positive_family_evidence(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    if not rows:
        return {}
    frame = pd.DataFrame(rows)
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for group_key, group in frame.groupby(["parent_formula_family", "candidate_formula_family"], dropna=False):
        parent_family, candidate_family = group_key
        run_ids = sorted(str(value) for value in group["run_id"].fillna("").unique() if str(value))
        out[(str(parent_family), str(candidate_family))] = {
            "true_improved_count": int(len(group)),
            "true_improved_run_ids": "|".join(run_ids),
            "best_true_improved_pass_rate_delta": round(float(group["pass_rate_delta"].max()), 8),
            "best_true_improved_mean_sharpe_delta": round(float(group["mean_sharpe_delta"].max()), 8),
        }
    return out


def _negative_disallowed_formula_rows(rows: list[dict[str, Any]], *, max_items: int) -> list[str]:
    if max_items <= 0:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for row in rows:
        formula = str(row.get("example_formula", "")).strip()
        if not formula or formula in seen:
            continue
        seen.add(formula)
        out.append(formula)
        if len(out) >= max_items:
            break
    return out


def _negative_blocked_family_pair_rows(
    rows: list[dict[str, Any]],
    *,
    max_items: int,
    min_count: int,
) -> list[dict[str, str]]:
    if max_items <= 0 or min_count <= 0:
        return []
    out: list[dict[str, str]] = []
    for row in rows:
        parent_family = str(row.get("parent_formula_family", "")).strip()
        candidate_family = str(row.get("candidate_formula_family", "")).strip()
        if not parent_family or not candidate_family:
            continue
        negative_count = _num(row.get("negative_count", 0))
        avg_mean_sharpe_delta = _num(row.get("avg_mean_sharpe_delta", 0))
        true_improved_count = _num(row.get("true_improved_count", 0))
        if negative_count < min_count or avg_mean_sharpe_delta >= 0 or true_improved_count > 0:
            continue
        out.append(
            {
                "parent_formula_family": parent_family,
                "candidate_formula_family": candidate_family,
                "negative_count": str(int(negative_count)),
                "avg_mean_sharpe_delta": str(row.get("avg_mean_sharpe_delta", "")),
                "worst_mean_sharpe_delta": str(row.get("worst_mean_sharpe_delta", "")),
            }
        )
        if len(out) >= max_items:
            break
    return out


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
