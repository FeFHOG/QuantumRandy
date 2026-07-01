from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .candidate_rewrite import (
    CandidateRewritePolicy,
    load_rewrite_targets,
    load_selector_forbidden_subtrees,
    write_selector_rewrite_report,
)
from .config import PromptConfig
from .io_utils import safe_write_csv, safe_write_json, safe_write_text
from .llm import FormulaGenerator, LLMSettings
from .portfolio import build_portfolio_research, render_portfolio_report
from .portfolio_universe import run_portfolio_universe_evaluation, write_portfolio_universe_report
from .universe import AssetDataset, load_asset_dataset, run_universe_evaluation
from .walk_forward import load_formula_entries


def run_selector_rewrite_pipeline(
    *,
    selector_path: str | Path,
    out_dir: str | Path,
    config_paths: list[str | Path] | None = None,
    window: str = "validation",
    max_targets: int = 5,
    candidates_per_target: int = 2,
    use_llm: bool = False,
    failure_memory_path: str | Path | None = None,
    timeout_seconds: int = 120,
    allow_local_fallback: bool = True,
    run_universe: bool = True,
    run_portfolio_universe: bool = True,
    max_corr: float | None = None,
    min_portfolio_factors: int = 1,
) -> dict[str, Any]:
    selector = Path(selector_path)
    out = Path(out_dir)
    rewrite_out = out / "rewrite"
    universe_out = out / "universe"
    portfolio_out = out / "portfolio"
    portfolio_universe_out = out / "portfolio_universe"
    out.mkdir(parents=True, exist_ok=True)

    policy = CandidateRewritePolicy(
        max_targets=max_targets,
        candidates_per_target=candidates_per_target,
        allow_local_fallback=allow_local_fallback,
    )
    targets = load_rewrite_targets(selector, max_targets=max_targets)
    selector_forbidden = load_selector_forbidden_subtrees(
        selector,
        max_subtrees=policy.max_selector_forbidden_subtrees,
    )
    generator = FormulaGenerator(
        use_llm=use_llm,
        settings=LLMSettings(timeout_seconds=timeout_seconds),
        prompt_config=PromptConfig(
            candidate_selector_path=str(selector),
            failure_memory_path=str(failure_memory_path) if failure_memory_path else None,
        ),
    )
    rewrite_manifest = write_selector_rewrite_report(
        targets,
        generator,
        rewrite_out,
        policy=policy,
        selector_forbidden_subtrees=selector_forbidden,
    )

    candidate_path = rewrite_out / "selector_rewrite_candidates.json"
    candidates = load_formula_entries(candidate_path)
    manifest: dict[str, Any] = {
        "artifact_type": "quantumrandy_selector_rewrite_research_pipeline",
        "schema_version": 1,
        "safety": {
            "research_only": True,
            "not_runtime_publish_payload": True,
            "does_not_update_runtime": True,
            "does_not_auto_admit_factors": True,
            "requires_manual_review_before_runtime": True,
        },
        "selector_path": selector.as_posix(),
        "window": window,
        "config_paths": [Path(path).as_posix() for path in config_paths or []],
        "rewrite": {
            "status": "completed",
            "out_dir": rewrite_out.as_posix(),
            "candidate_path": candidate_path.as_posix(),
            "target_count": rewrite_manifest.get("target_count", 0),
            "candidate_count": rewrite_manifest.get("candidate_count", 0),
            "selector_forbidden_subtree_count": rewrite_manifest.get("selector_forbidden_subtree_count", 0),
            "use_llm_requested": bool(use_llm),
            "event_source_counts": rewrite_manifest.get("event_source_counts", {}),
            "llm_error_count": rewrite_manifest.get("llm_error_count", 0),
            "llm_error_summary": rewrite_manifest.get("llm_error_summary", []),
            "llm_rewrite_accepted": rewrite_manifest.get("llm_rewrite_accepted", 0),
            "fallback_rewrite_accepted": rewrite_manifest.get("fallback_rewrite_accepted", 0),
            "allow_local_fallback": rewrite_manifest.get("allow_local_fallback", True),
            "is_llm_policy_evidence": bool(use_llm and rewrite_manifest.get("llm_rewrite_accepted", 0) > 0),
        },
        "universe": {"status": "skipped", "reason": ""},
        "portfolio": {"status": "skipped", "reason": ""},
        "portfolio_universe": {"status": "skipped", "reason": ""},
        "review": {"status": "skipped", "reason": ""},
        "outputs": {
            "rewrite_candidates": (rewrite_out / "selector_rewrite_candidates.json").as_posix(),
            "manifest": (out / "selector_rewrite_pipeline_manifest.json").as_posix(),
        },
    }

    assets = _load_assets(config_paths or [], window=window)
    if not candidates:
        reason = "selector rewrite produced no candidate formulas"
        manifest["universe"] = {"status": "skipped", "reason": reason}
        manifest["portfolio"] = {"status": "skipped", "reason": reason}
        manifest["portfolio_universe"] = {"status": "skipped", "reason": reason}
    elif run_universe and assets:
        details, summary = run_universe_evaluation(assets, candidates)
        summary = summary.sort_values(
            ["robustness_score", "pass_rate", "mean_sharpe", "median_rank_ic"],
            ascending=[False, False, False, False],
        )
        _write_universe_outputs(universe_out, details=details, summary=summary, assets=assets, window=window)
        candidate_review = build_selector_pipeline_candidate_review(
            rewrite_out / "selector_rewrite_candidates.csv",
            summary,
        )
        review = build_selector_pipeline_review_from_candidates(candidate_review)
        _write_review_outputs(out / "review", review=review, candidate_review=candidate_review)
        candidate_highlights = build_selector_pipeline_candidate_highlights(candidate_review)
        manifest["universe"] = {
            "status": "completed",
            "out_dir": universe_out.as_posix(),
            "summary_rows": len(summary),
            "top_factor_ids": [str(row.get("factor_id", "")) for row in summary.head(10).to_dict(orient="records")],
        }
        manifest["review"] = {
            "status": "completed",
            "out_dir": (out / "review").as_posix(),
            "review_rows": len(review),
            "verdict_counts": _value_counts(review, "review_verdict"),
            "candidate_review_rows": len(candidate_review),
            "candidate_verdict_counts": _value_counts(candidate_review, "candidate_review_verdict"),
            "candidate_generation_source_counts": _value_counts(candidate_review, "rewrite_generation_source"),
            "candidate_highlight_rows": len(candidate_highlights),
            "candidate_highlight_counts": _value_counts(candidate_highlights, "highlight_type"),
            "candidate_highlight_generation_source_counts": _value_counts(
                candidate_highlights,
                "rewrite_generation_source",
            ),
        }
        manifest["outputs"]["universe_summary"] = (universe_out / "universe_summary.csv").as_posix()
        manifest["outputs"]["pipeline_review"] = (out / "review" / "selector_pipeline_review.csv").as_posix()
        manifest["outputs"]["pipeline_candidate_review"] = (
            out / "review" / "selector_pipeline_candidate_review.csv"
        ).as_posix()
        manifest["outputs"]["pipeline_candidate_highlights"] = (
            out / "review" / "selector_pipeline_candidate_highlights.csv"
        ).as_posix()
        manifest["outputs"]["pipeline_candidate_highlight_summary"] = (
            out / "review" / "SELECTOR_CANDIDATE_HIGHLIGHTS.md"
        ).as_posix()
        manifest["outputs"]["pipeline_candidate_highlight_summary_manifest"] = (
            out / "review" / "selector_candidate_highlight_summary_manifest.json"
        ).as_posix()
    elif run_universe:
        manifest["universe"] = {"status": "skipped", "reason": "no asset config paths provided"}
        manifest["review"] = {"status": "skipped", "reason": "no universe evaluation"}
    else:
        manifest["universe"] = {"status": "skipped", "reason": "disabled by caller"}
        manifest["review"] = {"status": "skipped", "reason": "universe evaluation disabled"}

    if candidates and run_portfolio_universe and assets:
        factors, selection, portfolios, contribution, portfolio_manifest = build_portfolio_research(
            assets[0].data,
            candidates,
            assets[0].cfg,
            max_corr=max_corr,
            min_factors=min_portfolio_factors,
        )
        portfolio_manifest["window"] = window
        portfolio_manifest["source_selector_rewrite_candidates"] = candidate_path.as_posix()
        _write_portfolio_outputs(
            portfolio_out,
            factors=factors,
            selection=selection,
            portfolios=portfolios,
            contribution=contribution,
            manifest=portfolio_manifest,
        )
        manifest["portfolio"] = {
            "status": "completed",
            "out_dir": portfolio_out.as_posix(),
            "portfolio_count": len(portfolios),
            "selected_factor_ids": portfolio_manifest.get("selected_factor_ids", []),
        }
        manifest["outputs"]["portfolio_manifest"] = (portfolio_out / "portfolio_manifest.json").as_posix()

        details, summary, portfolio_universe_manifest = run_portfolio_universe_evaluation(
            assets,
            portfolio_manifest,
            factors.to_dict(orient="records"),
        )
        summary = summary.sort_values(
            ["robustness_score", "pass_rate", "mean_sharpe", "median_rank_ic"],
            ascending=[False, False, False, False],
        )
        portfolio_universe_manifest.update(
            {
                "window": window,
                "source_selector_rewrite_candidates": candidate_path.as_posix(),
                "source_portfolio_manifest_path": (portfolio_out / "portfolio_manifest.json").as_posix(),
            }
        )
        write_portfolio_universe_report(
            portfolio_universe_out,
            details=details,
            summary=summary,
            manifest=portfolio_universe_manifest,
        )
        manifest["portfolio_universe"] = {
            "status": "completed",
            "out_dir": portfolio_universe_out.as_posix(),
            "summary_rows": len(summary),
            "portfolio_ids": [str(row.get("portfolio_id", "")) for row in summary.to_dict(orient="records")],
        }
        manifest["outputs"]["portfolio_universe_summary"] = (
            portfolio_universe_out / "portfolio_universe_summary.csv"
        ).as_posix()
    elif candidates and run_portfolio_universe:
        manifest["portfolio"] = {"status": "skipped", "reason": "no asset config paths provided"}
        manifest["portfolio_universe"] = {"status": "skipped", "reason": "no asset config paths provided"}
    elif not run_portfolio_universe:
        manifest["portfolio"] = {"status": "skipped", "reason": "disabled by caller"}
        manifest["portfolio_universe"] = {"status": "skipped", "reason": "disabled by caller"}

    if manifest["review"]["status"] == "skipped" and not candidates:
        manifest["review"] = {"status": "skipped", "reason": "selector rewrite produced no candidate formulas"}

    safe_write_json(out / "selector_rewrite_pipeline_manifest.json", manifest, out / "events.jsonl")
    safe_write_text(out / "SELECTOR_REWRITE_PIPELINE_REPORT.md", render_pipeline_report(manifest), out / "events.jsonl")
    return manifest


def render_pipeline_report(manifest: dict[str, Any]) -> str:
    lines = [
        "# QuantumRandy Selector Rewrite Research Pipeline",
        "",
        "This is a research artifact only. It is not a runtime publish payload and does not admit factors.",
        "",
        "## Summary",
        "",
        f"- Selector: `{manifest['selector_path']}`",
        f"- Window: `{manifest['window']}`",
        f"- Rewrite candidates: `{manifest['rewrite']['candidate_count']}`",
        f"- Selector forbidden subtrees: `{manifest['rewrite']['selector_forbidden_subtree_count']}`",
        f"- LLM requested: `{manifest['rewrite'].get('use_llm_requested', False)}`",
        f"- Local fallback allowed: `{manifest['rewrite'].get('allow_local_fallback', True)}`",
        f"- LLM rewrite accepted: `{manifest['rewrite'].get('llm_rewrite_accepted', 0)}`",
        f"- Fallback/local accepted: `{manifest['rewrite'].get('fallback_rewrite_accepted', 0)}`",
        f"- LLM policy evidence: `{manifest['rewrite'].get('is_llm_policy_evidence', False)}`",
    ]
    error_summary = manifest["rewrite"].get("llm_error_summary") or []
    if error_summary:
        lines.append(f"- LLM rewrite errors: `{manifest['rewrite'].get('llm_error_count', len(error_summary))}`")
    review = manifest.get("review", {})
    if review.get("status") == "completed":
        lines.extend(
            [
                f"- Reviewed parents: `{review.get('review_rows', 0)}`",
                f"- Reviewed candidates: `{review.get('candidate_review_rows', 0)}`",
                f"- Candidate highlights: `{review.get('candidate_highlight_rows', 0)}`",
            ]
        )
        candidate_counts = review.get("candidate_verdict_counts") or {}
        source_counts = review.get("candidate_generation_source_counts") or {}
        highlight_counts = review.get("candidate_highlight_counts") or {}
        highlight_source_counts = review.get("candidate_highlight_generation_source_counts") or {}
        if candidate_counts:
            lines.append(f"- Candidate verdict mix: `{_format_counts(candidate_counts)}`")
        if source_counts:
            lines.append(f"- Candidate source mix: `{_format_counts(source_counts)}`")
        if highlight_counts:
            lines.append(f"- Candidate highlight mix: `{_format_counts(highlight_counts)}`")
        if highlight_source_counts:
            lines.append(f"- Candidate highlight source mix: `{_format_counts(highlight_source_counts)}`")
    if error_summary:
        lines.extend(["", "## LLM Error Summary", ""])
        for error in error_summary[:5]:
            lines.append(f"- {error}")
    lines.extend(["", "## Stages", "", "| Stage | Status | Detail |", "|---|---|---|"])
    for stage in ["rewrite", "universe", "portfolio", "portfolio_universe"]:
        payload = manifest.get(stage, {})
        detail = payload.get("out_dir") or payload.get("reason") or ""
        lines.append(f"| `{stage}` | `{payload.get('status', '')}` | `{detail}` |")
    lines.append(f"| `review` | `{review.get('status', '')}` | `{review.get('out_dir') or review.get('reason') or ''}` |")
    lines.extend(
        [
            "",
            "## Files",
            "",
            "- `rewrite/selector_rewrite_candidates.json`: leaderboard-style research candidates.",
            "- `universe/universe_summary.csv`: formula-level multi-asset evidence when configs are provided.",
            "- `portfolio/portfolio_manifest.json`: fixed-blend research portfolio when configs are provided.",
            "- `portfolio_universe/portfolio_universe_summary.csv`: portfolio-level multi-asset evidence.",
            "- `review/selector_pipeline_review.csv`: parent-vs-rewrite evidence comparison.",
            "- `review/selector_pipeline_candidate_review.csv`: candidate-level parent-vs-rewrite verdicts and deltas.",
            "- `review/selector_pipeline_candidate_highlights.csv`: compact candidate-level audit queues.",
            "- `review/SELECTOR_CANDIDATE_HIGHLIGHTS.md`: standalone candidate highlight handoff summary.",
            "- `selector_rewrite_pipeline_manifest.json`: machine-readable stage provenance and safety metadata.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_selector_pipeline_review(
    rewrite_candidates_path: str | Path,
    universe_summary: pd.DataFrame,
) -> pd.DataFrame:
    candidate_review = build_selector_pipeline_candidate_review(rewrite_candidates_path, universe_summary)
    return build_selector_pipeline_review_from_candidates(candidate_review)


def build_selector_pipeline_review_from_candidates(candidate_review: pd.DataFrame) -> pd.DataFrame:
    if candidate_review.empty:
        return pd.DataFrame()

    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in candidate_review.to_dict(orient="records"):
        grouped.setdefault(str(row.get("parent_factor_id", "")), []).append(row)

    review_rows: list[dict[str, Any]] = []
    for parent_factor_id, rows in grouped.items():
        parent_pass_rate = _num(rows[0].get("parent_universe_pass_rate"))
        parent_mean_sharpe = _num(rows[0].get("parent_universe_mean_sharpe"))
        candidate_verdict_counts = _candidate_verdict_counts(rows, parent_pass_rate, parent_mean_sharpe)
        ranked = sorted(
            rows,
            key=lambda row: _candidate_review_rank(row, parent_pass_rate, parent_mean_sharpe),
            reverse=True,
        )
        best = ranked[0]
        review_rows.append(
            {
                "parent_factor_id": parent_factor_id,
                "parent_formula": best.get("parent_formula", ""),
                "parent_rewrite_focus": best.get("parent_rewrite_focus", ""),
                "parent_universe_pass_rate": parent_pass_rate,
                "parent_universe_mean_sharpe": parent_mean_sharpe,
                "candidate_count": len(rows),
                "evaluated_candidate_count": sum(1 for row in rows if int(row.get("candidate_evaluated_assets", 0)) > 0),
                "best_candidate_factor_id": best.get("factor_id", ""),
                "best_candidate_formula": best.get("formula", ""),
                "best_candidate_generation_source": best.get("rewrite_generation_source", ""),
                "best_candidate_pass_rate": _num(best.get("candidate_pass_rate")),
                "best_candidate_mean_sharpe": _num(best.get("candidate_mean_sharpe")),
                "best_candidate_median_rank_ic": _num(best.get("candidate_median_rank_ic")),
                "best_candidate_robustness_score": _num(best.get("candidate_robustness_score")),
                "best_candidate_failed_assets": best.get("candidate_failed_assets", ""),
                "best_candidate_rank_reason": best.get("candidate_rank_reason", ""),
                "candidate_verdict_counts": _format_verdict_counts(candidate_verdict_counts),
                "pass_rate_delta": _num(best.get("pass_rate_delta")),
                "mean_sharpe_delta": _num(best.get("mean_sharpe_delta")),
                "improvement_gate": "pass_rate_delta > 0 and mean_sharpe_delta >= 0",
                "review_verdict": best.get("candidate_review_verdict", ""),
            }
        )

    frame = pd.DataFrame(review_rows)
    if frame.empty:
        return frame
    frame["review_verdict_rank"] = frame["review_verdict"].map(_VERDICT_RANK).fillna(0).astype(int)
    return frame.sort_values(
        ["review_verdict_rank", "pass_rate_delta", "mean_sharpe_delta"],
        ascending=[False, False, False],
    ).reset_index(drop=True)


def build_selector_pipeline_candidate_review(
    rewrite_candidates_path: str | Path,
    universe_summary: pd.DataFrame,
) -> pd.DataFrame:
    candidates = _read_csv(rewrite_candidates_path)
    if candidates.empty:
        return pd.DataFrame()
    if universe_summary is None or universe_summary.empty:
        summary_by_factor: dict[str, dict[str, Any]] = {}
    else:
        summary_by_factor = {
            str(row.get("factor_id", "")): row for row in universe_summary.fillna("").to_dict(orient="records")
        }

    candidate_rows: list[dict[str, Any]] = []
    for row in candidates.fillna("").to_dict(orient="records"):
        factor_id = str(row.get("factor_id", ""))
        evidence = summary_by_factor.get(factor_id, {})
        parent_pass_rate = _num(row.get("parent_universe_pass_rate"))
        parent_mean_sharpe = _num(row.get("parent_universe_mean_sharpe"))
        candidate_pass_rate = _num(evidence.get("pass_rate"))
        candidate_mean_sharpe = _num(evidence.get("mean_sharpe"))
        pass_rate_delta = round(candidate_pass_rate - parent_pass_rate, 8)
        mean_sharpe_delta = round(candidate_mean_sharpe - parent_mean_sharpe, 8)
        evaluated_assets = int(_num(evidence.get("evaluated_assets")))
        enriched = {
            **row,
            "candidate_pass_rate": candidate_pass_rate,
            "candidate_mean_sharpe": candidate_mean_sharpe,
            "candidate_median_rank_ic": _num(evidence.get("median_rank_ic")),
            "candidate_robustness_score": _num(evidence.get("robustness_score")),
            "candidate_failed_assets": str(evidence.get("failed_assets", "")),
            "candidate_evaluated_assets": evaluated_assets,
            "pass_rate_delta": pass_rate_delta,
            "mean_sharpe_delta": mean_sharpe_delta,
            "candidate_review_verdict": _review_verdict(
                evaluated=evaluated_assets,
                pass_rate_delta=pass_rate_delta,
                mean_sharpe_delta=mean_sharpe_delta,
            ),
        }
        enriched["candidate_verdict_rank"] = _VERDICT_RANK.get(str(enriched["candidate_review_verdict"]), 0)
        enriched["candidate_rank_reason"] = _candidate_rank_reason(
            enriched,
            parent_pass_rate,
            parent_mean_sharpe,
        )
        candidate_rows.append(enriched)

    frame = pd.DataFrame(candidate_rows)
    if frame.empty:
        return frame
    return frame.sort_values(
        ["parent_factor_id", "candidate_verdict_rank", "pass_rate_delta", "mean_sharpe_delta"],
        ascending=[True, False, False, False],
    ).reset_index(drop=True)


def build_selector_pipeline_candidate_highlights(candidate_review: pd.DataFrame) -> pd.DataFrame:
    if candidate_review.empty or "candidate_review_verdict" not in candidate_review.columns:
        return pd.DataFrame()

    highlight_labels = {
        "improved": "true_improved",
        "coverage_only": "coverage_only_trap",
        "mixed": "sharpe_improved_no_pass_lift",
    }
    rows: list[dict[str, Any]] = []
    for row in candidate_review.fillna("").to_dict(orient="records"):
        verdict = str(row.get("candidate_review_verdict", ""))
        highlight = highlight_labels.get(verdict)
        if not highlight:
            continue
        rows.append(
            {
                "highlight_type": highlight,
                "parent_factor_id": row.get("parent_factor_id", ""),
                "factor_id": row.get("factor_id", ""),
                "rewrite_generation_source": row.get("rewrite_generation_source", ""),
                "candidate_review_verdict": verdict,
                "pass_rate_delta": _num(row.get("pass_rate_delta")),
                "mean_sharpe_delta": _num(row.get("mean_sharpe_delta")),
                "candidate_pass_rate": _num(row.get("candidate_pass_rate")),
                "candidate_mean_sharpe": _num(row.get("candidate_mean_sharpe")),
                "candidate_failed_assets": row.get("candidate_failed_assets", ""),
                "formula": row.get("formula", ""),
                "candidate_rank_reason": row.get("candidate_rank_reason", ""),
            }
        )

    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    type_rank = {
        "true_improved": 3,
        "sharpe_improved_no_pass_lift": 2,
        "coverage_only_trap": 1,
    }
    frame["highlight_rank"] = frame["highlight_type"].map(type_rank).fillna(0).astype(int)
    return frame.sort_values(
        ["highlight_rank", "pass_rate_delta", "mean_sharpe_delta", "candidate_mean_sharpe"],
        ascending=[False, False, False, False],
    ).reset_index(drop=True)


def write_selector_candidate_highlight_summary(
    review_dir: str | Path,
    out_dir: str | Path | None = None,
) -> dict[str, Any]:
    review_path = Path(review_dir)
    out = Path(out_dir) if out_dir is not None else review_path
    out.mkdir(parents=True, exist_ok=True)
    highlights = _read_csv(review_path / "selector_pipeline_candidate_highlights.csv")
    if highlights.empty:
        candidate_review = _read_csv(review_path / "selector_pipeline_candidate_review.csv")
        highlights = build_selector_pipeline_candidate_highlights(candidate_review)

    manifest = {
        "artifact_type": "quantumrandy_selector_candidate_highlight_summary",
        "schema_version": 1,
        "safety": {
            "research_only": True,
            "not_runtime_publish_payload": True,
            "does_not_update_runtime": True,
            "does_not_auto_admit_factors": True,
        },
        "source_review_dir": review_path.as_posix(),
        "highlight_rows": len(highlights),
        "highlight_counts": _value_counts(highlights, "highlight_type"),
        "outputs": {
            "summary_markdown": (out / "SELECTOR_CANDIDATE_HIGHLIGHTS.md").as_posix(),
            "summary_manifest": (out / "selector_candidate_highlight_summary_manifest.json").as_posix(),
        },
    }
    safe_write_json(out / "selector_candidate_highlight_summary_manifest.json", manifest, out / "events.jsonl")
    safe_write_text(
        out / "SELECTOR_CANDIDATE_HIGHLIGHTS.md",
        render_candidate_highlight_summary(manifest, highlights),
        out / "events.jsonl",
    )
    return manifest


def render_candidate_highlight_summary(manifest: dict[str, Any], highlights: pd.DataFrame) -> str:
    lines = [
        "# QuantumRandy Selector Candidate Highlights",
        "",
        "This is a research audit artifact only. It is not an admission decision or runtime publish payload.",
        "",
        "## Summary",
        "",
        f"- Highlight rows: `{manifest.get('highlight_rows', 0)}`",
    ]
    counts = manifest.get("highlight_counts") or {}
    if counts:
        lines.append(f"- Highlight mix: `{_format_counts(counts)}`")
    lines.extend(["", "## Highlight Queues", ""])
    if highlights.empty:
        lines.append("No selector candidate highlights available.")
    else:
        for highlight_type, title in [
            ("true_improved", "True Improved Candidates"),
            ("coverage_only_trap", "Coverage-Only Traps"),
            ("sharpe_improved_no_pass_lift", "Sharpe-Improved Without Pass-Rate Lift"),
        ]:
            lines.extend(_render_highlight_summary_table(highlights, highlight_type=highlight_type, title=title))
    lines.extend(
        [
            "",
            "## Files",
            "",
            "- `selector_pipeline_candidate_highlights.csv`: source compact candidate audit queues.",
            "- `selector_candidate_highlight_summary_manifest.json`: machine-readable summary metadata.",
        ]
    )
    return "\n".join(lines) + "\n"


def _render_highlight_summary_table(
    highlights: pd.DataFrame,
    *,
    highlight_type: str,
    title: str,
    limit: int = 10,
) -> list[str]:
    lines = [f"### {title}", ""]
    if "highlight_type" not in highlights.columns:
        lines.extend(["No candidates in this queue.", ""])
        return lines
    rows = highlights[highlights["highlight_type"].fillna("") == highlight_type].copy()
    if rows.empty:
        lines.extend(["No candidates in this queue.", ""])
        return lines
    for column in ("pass_rate_delta", "mean_sharpe_delta", "candidate_mean_sharpe"):
        if column not in rows.columns:
            rows[column] = 0.0
    rows = rows.sort_values(
        ["pass_rate_delta", "mean_sharpe_delta", "candidate_mean_sharpe"],
        ascending=[False, False, False],
    )
    lines.append("| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |")
    lines.append("|---|---|---|---:|---:|---|---|")
    for row in rows.head(limit).to_dict(orient="records"):
        lines.append(
            "| "
            f"`{row.get('parent_factor_id', '')}` | `{row.get('factor_id', '')}` | "
            f"`{row.get('rewrite_generation_source', '')}` | "
            f"{_num(row.get('pass_rate_delta')):.2f} | {_num(row.get('mean_sharpe_delta')):.2f} | "
            f"{_md_cell(row.get('candidate_failed_assets', ''))} | `{_short_formula(row.get('formula', ''))}` |"
        )
    lines.append("")
    return lines


def _load_assets(config_paths: list[str | Path], *, window: str) -> list[AssetDataset]:
    return [load_asset_dataset(path, window=window) for path in config_paths]


def _write_universe_outputs(
    out: Path,
    *,
    details,
    summary,
    assets: list[AssetDataset],
    window: str,
) -> None:
    out.mkdir(parents=True, exist_ok=True)
    manifest = {
        "artifact_type": "quantumrandy_universe_robustness",
        "schema_version": 1,
        "safety": {
            "research_only": True,
            "not_runtime_publish_payload": True,
            "does_not_update_runtime": True,
            "requires_manual_review_before_runtime": True,
        },
        "window": window,
        "asset_count": len(assets),
        "assets": [
            {
                "symbol": asset.name,
                "config": asset.config_path,
                "bars": len(asset.data),
                "ohlcv_csv": str(asset.cfg.ohlcv_csv),
                "funding_csv": str(asset.cfg.funding_csv),
            }
            for asset in assets
        ],
        "summary_rows": len(summary),
        "score": "mean_sharpe + 10*median_rank_ic + pass_rate - sharpe_variance - worst_max_dd",
    }
    safe_write_csv(out / "universe_details.csv", details, out / "events.jsonl")
    safe_write_csv(out / "universe_summary.csv", summary, out / "events.jsonl")
    safe_write_json(out / "universe_manifest.json", manifest, out / "events.jsonl")


def _write_portfolio_outputs(
    out: Path,
    *,
    factors,
    selection,
    portfolios,
    contribution,
    manifest: dict[str, Any],
) -> None:
    out.mkdir(parents=True, exist_ok=True)
    safe_write_csv(out / "portfolio_factors.csv", factors, out / "events.jsonl")
    safe_write_csv(out / "portfolio_selection.csv", selection, out / "events.jsonl")
    safe_write_csv(out / "portfolio_summary.csv", portfolios, out / "events.jsonl")
    safe_write_csv(out / "portfolio_contribution.csv", contribution, out / "events.jsonl")
    safe_write_json(out / "portfolio_manifest.json", manifest, out / "events.jsonl")
    safe_write_text(
        out / "PORTFOLIO_REPORT.md",
        render_portfolio_report(manifest, factors, selection, portfolios, contribution),
        out / "events.jsonl",
    )


def _write_review_outputs(out: Path, *, review: pd.DataFrame, candidate_review: pd.DataFrame | None = None) -> None:
    out.mkdir(parents=True, exist_ok=True)
    candidate_review = candidate_review if candidate_review is not None else pd.DataFrame()
    candidate_highlights = build_selector_pipeline_candidate_highlights(candidate_review)
    manifest = {
        "artifact_type": "quantumrandy_selector_rewrite_pipeline_review",
        "schema_version": 1,
        "safety": {
            "research_only": True,
            "not_runtime_publish_payload": True,
            "does_not_update_runtime": True,
            "does_not_auto_admit_factors": True,
        },
        "review_rows": len(review),
        "candidate_review_rows": len(candidate_review),
        "candidate_highlight_rows": len(candidate_highlights),
        "verdict_counts": _value_counts(review, "review_verdict"),
        "candidate_verdict_counts": _value_counts(candidate_review, "candidate_review_verdict"),
        "candidate_generation_source_counts": _value_counts(candidate_review, "rewrite_generation_source"),
        "candidate_highlight_counts": _value_counts(candidate_highlights, "highlight_type"),
        "candidate_highlight_generation_source_counts": _value_counts(
            candidate_highlights,
            "rewrite_generation_source",
        ),
        "outputs": {
            "candidate_highlight_summary": (out / "SELECTOR_CANDIDATE_HIGHLIGHTS.md").as_posix(),
            "candidate_highlight_summary_manifest": (
                out / "selector_candidate_highlight_summary_manifest.json"
            ).as_posix(),
        },
    }
    highlight_manifest = {
        "artifact_type": "quantumrandy_selector_candidate_highlight_summary",
        "schema_version": 1,
        "safety": manifest["safety"],
        "source_review_dir": out.as_posix(),
        "highlight_rows": len(candidate_highlights),
        "highlight_counts": _value_counts(candidate_highlights, "highlight_type"),
        "outputs": {
            "summary_markdown": (out / "SELECTOR_CANDIDATE_HIGHLIGHTS.md").as_posix(),
            "summary_manifest": (out / "selector_candidate_highlight_summary_manifest.json").as_posix(),
        },
    }
    safe_write_csv(out / "selector_pipeline_review.csv", review, out / "events.jsonl")
    safe_write_csv(out / "selector_pipeline_candidate_review.csv", candidate_review, out / "events.jsonl")
    safe_write_csv(out / "selector_pipeline_candidate_highlights.csv", candidate_highlights, out / "events.jsonl")
    safe_write_json(out / "selector_pipeline_review_manifest.json", manifest, out / "events.jsonl")
    safe_write_json(out / "selector_candidate_highlight_summary_manifest.json", highlight_manifest, out / "events.jsonl")
    safe_write_text(
        out / "SELECTOR_PIPELINE_REVIEW.md",
        render_review_report(manifest, review, candidate_review=candidate_review),
        out / "events.jsonl",
    )
    safe_write_text(
        out / "SELECTOR_CANDIDATE_HIGHLIGHTS.md",
        render_candidate_highlight_summary(highlight_manifest, candidate_highlights),
        out / "events.jsonl",
    )


def render_review_report(
    manifest: dict[str, Any],
    review: pd.DataFrame,
    *,
    candidate_review: pd.DataFrame | None = None,
) -> str:
    lines = [
        "# QuantumRandy Selector Rewrite Pipeline Review",
        "",
        "This is a research comparison artifact only. It is not an admission decision or runtime publish payload.",
        "A rewrite is considered improved only when pass-rate delta is positive and mean-Sharpe delta is non-negative.",
        "",
        "## Summary",
        "",
        f"- Review rows: `{manifest['review_rows']}`",
        f"- Candidate review rows: `{manifest.get('candidate_review_rows', 0)}`",
        "",
        "## Verdict Counts",
        "",
        "| Verdict | Count |",
        "|---|---:|",
    ]
    counts = manifest.get("verdict_counts") or {}
    if counts:
        for verdict, count in counts.items():
            lines.append(f"| `{verdict}` | {count} |")
    else:
        lines.append("| none | 0 |")

    lines.extend(["", "## Candidate Verdict Counts", "", "| Verdict | Count |", "|---|---:|"])
    candidate_counts = manifest.get("candidate_verdict_counts") or {}
    if candidate_counts:
        for verdict, count in candidate_counts.items():
            lines.append(f"| `{verdict}` | {count} |")
    else:
        lines.append("| none | 0 |")

    source_counts = manifest.get("candidate_generation_source_counts") or {}
    if source_counts:
        lines.extend(["", "## Candidate Source Counts", "", "| Source | Count |", "|---|---:|"])
        for source, count in source_counts.items():
            lines.append(f"| `{source}` | {count} |")

    highlight_source_counts = manifest.get("candidate_highlight_generation_source_counts") or {}
    if highlight_source_counts:
        lines.extend(["", "## Candidate Highlight Source Counts", "", "| Source | Count |", "|---|---:|"])
        for source, count in highlight_source_counts.items():
            lines.append(f"| `{source}` | {count} |")

    if candidate_review is not None and not candidate_review.empty:
        lines.extend(["", "## Candidate-Level Highlights", ""])
        lines.extend(
            _render_candidate_highlight_table(
                candidate_review,
                title="True Improved Candidates",
                verdicts={"improved"},
                empty_message="No candidates improved pass rate while preserving or improving mean Sharpe.",
            )
        )
        lines.extend(
            _render_candidate_highlight_table(
                candidate_review,
                title="Coverage-Only Traps",
                verdicts={"coverage_only"},
                empty_message="No candidates only improved coverage while reducing mean Sharpe.",
            )
        )
        lines.extend(
            _render_candidate_highlight_table(
                candidate_review,
                title="Sharpe-Improved Without Pass-Rate Lift",
                verdicts={"mixed"},
                empty_message="No candidates improved mean Sharpe without a pass-rate lift.",
            )
        )

    lines.extend(["", "## Parent vs Rewrite Evidence", ""])
    if review.empty:
        lines.append("No reviewed rewrite candidates.")
    else:
        lines.append(
            "| Parent | Verdict | Pass Rate Delta | Mean Sharpe Delta | Best Candidate | Best Pass Rate | Formula |"
        )
        lines.append("|---|---|---:|---:|---|---:|---|")
        for row in review.head(30).to_dict(orient="records"):
            lines.append(
                "| "
                f"`{row['parent_factor_id']}` | `{row['review_verdict']}` | {row['pass_rate_delta']:.2f} | "
                f"{row['mean_sharpe_delta']:.2f} | `{row['best_candidate_factor_id']}` | "
                f"{row['best_candidate_pass_rate']:.2f} | `{row['best_candidate_formula']}` |"
            )
    lines.extend(
        [
            "",
            "## Files",
            "",
            "- `selector_pipeline_review.csv`: parent-level best-candidate summary.",
            "- `selector_pipeline_candidate_review.csv`: candidate-level parent-vs-rewrite verdicts and deltas.",
            "- `selector_pipeline_candidate_highlights.csv`: compact queues for true improvements, coverage traps, and Sharpe-improved/no-pass-lift candidates.",
            "- `selector_pipeline_review_manifest.json`: machine-readable review counts and safety metadata.",
        ]
    )
    return "\n".join(lines) + "\n"


def _render_candidate_highlight_table(
    candidate_review: pd.DataFrame,
    *,
    title: str,
    verdicts: set[str],
    empty_message: str,
    limit: int = 10,
) -> list[str]:
    lines = [f"### {title}", ""]
    if "candidate_review_verdict" not in candidate_review.columns:
        lines.extend([empty_message, ""])
        return lines

    rows = candidate_review[
        candidate_review["candidate_review_verdict"].fillna("").isin(verdicts)
    ].copy()
    if rows.empty:
        lines.extend([empty_message, ""])
        return lines

    for column in ("candidate_verdict_rank", "pass_rate_delta", "mean_sharpe_delta", "candidate_mean_sharpe"):
        if column not in rows.columns:
            rows[column] = 0.0
    rows = rows.sort_values(
        ["candidate_verdict_rank", "pass_rate_delta", "mean_sharpe_delta", "candidate_mean_sharpe"],
        ascending=[False, False, False, False],
    )
    lines.append("| Parent | Candidate | Source | Verdict | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |")
    lines.append("|---|---|---|---|---:|---:|---|---|")
    for row in rows.head(limit).to_dict(orient="records"):
        lines.append(
            "| "
            f"`{row.get('parent_factor_id', '')}` | `{row.get('factor_id', '')}` | "
            f"`{row.get('rewrite_generation_source', '')}` | "
            f"`{row.get('candidate_review_verdict', '')}` | {_num(row.get('pass_rate_delta')):.2f} | "
            f"{_num(row.get('mean_sharpe_delta')):.2f} | "
            f"{_md_cell(row.get('candidate_failed_assets', ''))} | "
            f"`{_short_formula(row.get('formula', ''))}` |"
        )
    lines.append("")
    return lines


def _short_formula(value: Any, *, limit: int = 96) -> str:
    formula = str(value).replace("\n", " ").strip()
    if len(formula) <= limit:
        return formula
    return formula[: limit - 3].rstrip() + "..."


def _md_cell(value: Any) -> str:
    text = str(value).replace("\n", " ").strip()
    return text.replace("|", "\\|") if text else "none"


def _review_verdict(*, evaluated: int, pass_rate_delta: float, mean_sharpe_delta: float) -> str:
    if evaluated <= 0:
        return "needs_evaluation"
    if pass_rate_delta > 0 and mean_sharpe_delta >= 0:
        return "improved"
    if pass_rate_delta > 0 and mean_sharpe_delta < 0:
        return "coverage_only"
    if mean_sharpe_delta > 0:
        return "mixed"
    return "not_improved"


_VERDICT_RANK = {
    "improved": 4,
    "mixed": 3,
    "coverage_only": 2,
    "not_improved": 1,
    "needs_evaluation": 0,
}


def _candidate_review_rank(row: dict[str, Any], parent_pass_rate: float, parent_mean_sharpe: float) -> tuple[int, float, float, float, float]:
    evaluated = int(row.get("candidate_evaluated_assets", 0))
    pass_rate = _num(row.get("candidate_pass_rate"))
    mean_sharpe = _num(row.get("candidate_mean_sharpe"))
    pass_rate_delta = round(pass_rate - parent_pass_rate, 8)
    mean_sharpe_delta = round(mean_sharpe - parent_mean_sharpe, 8)
    verdict = _review_verdict(
        evaluated=evaluated,
        pass_rate_delta=pass_rate_delta,
        mean_sharpe_delta=mean_sharpe_delta,
    )
    verdict_rank = _VERDICT_RANK.get(verdict, 0)
    return (
        verdict_rank,
        pass_rate_delta,
        mean_sharpe_delta,
        mean_sharpe,
        _num(row.get("candidate_robustness_score")),
    )


def _candidate_verdict_counts(
    rows: list[dict[str, Any]],
    parent_pass_rate: float,
    parent_mean_sharpe: float,
) -> dict[str, int]:
    counts = {verdict: 0 for verdict in _VERDICT_RANK}
    for row in rows:
        pass_rate = _num(row.get("candidate_pass_rate"))
        mean_sharpe = _num(row.get("candidate_mean_sharpe"))
        verdict = _review_verdict(
            evaluated=int(row.get("candidate_evaluated_assets", 0)),
            pass_rate_delta=round(pass_rate - parent_pass_rate, 8),
            mean_sharpe_delta=round(mean_sharpe - parent_mean_sharpe, 8),
        )
        counts[verdict] = counts.get(verdict, 0) + 1
    return {verdict: counts[verdict] for verdict in _VERDICT_RANK if counts.get(verdict)}


def _format_verdict_counts(counts: dict[str, int]) -> str:
    return "|".join(f"{verdict}:{count}" for verdict, count in counts.items() if count)


def _format_counts(counts: dict[str, Any]) -> str:
    return "|".join(f"{key}:{value}" for key, value in counts.items() if value)


def _candidate_rank_reason(row: dict[str, Any], parent_pass_rate: float, parent_mean_sharpe: float) -> str:
    rank = _candidate_review_rank(row, parent_pass_rate, parent_mean_sharpe)
    return (
        f"verdict_rank={rank[0]}; pass_rate_delta={rank[1]:.8f}; "
        f"mean_sharpe_delta={rank[2]:.8f}; mean_sharpe={rank[3]:.8f}; "
        f"robustness_score={rank[4]:.8f}"
    )


def _read_csv(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def _num(value: Any) -> float:
    try:
        if value == "":
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _value_counts(frame: pd.DataFrame, column: str) -> dict[str, int]:
    if frame.empty or column not in frame.columns:
        return {}
    return {str(key): int(value) for key, value in frame[column].value_counts().to_dict().items()}
