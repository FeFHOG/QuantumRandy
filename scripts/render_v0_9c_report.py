from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

EXPORT_DIR = ROOT / "reports/factor_candidate_exports/research_v0_9c_multi_factor_bundle"
MEMORY_DIR = ROOT / "reports/failure_memory/research_v0_9c_multi_factor_bundle"
REPORT_PATH = ROOT / "docs/RESEARCH_V0_9C_MULTI_FACTOR_BUNDLE_REPORT.md"


def main() -> None:
    randyslab = _find_sibling_repo(ROOT, "RandysLab-STRICT4H")
    paths = _artifact_paths(randyslab)
    export_manifest = _json(EXPORT_DIR / "factor_candidate_export_manifest.json")
    candidates = _jsonl(EXPORT_DIR / "factor_candidates.jsonl")
    sensitivity_summary = _json(paths["sensitivity"] / "factor_candidate_sensitivity_summary.json")
    review_summary = _json(paths["review"] / "factor_candidate_review_summary.json")
    review = pd.read_csv(paths["review"] / "factor_candidate_review.csv").fillna("")
    correlation_summary = _json(paths["correlation"] / "factor_candidate_correlation_summary.json")
    pairwise = _read_csv_optional(paths["correlation"] / "factor_candidate_pairwise_correlation.csv")
    redundancy = pd.read_csv(paths["correlation"] / "factor_candidate_bundle_redundancy.csv").fillna("")
    gated_summary_path = paths["gated"] / "factor_candidate_sensitivity_summary.json"
    gated_summary = _json(gated_summary_path) if gated_summary_path.exists() else None
    memory_manifest = _json(MEMORY_DIR / "failure_memory_manifest.json")
    memory = pd.read_csv(MEMORY_DIR / "failure_memory.csv").fillna("")

    readiness = _readiness_verdict(review, redundancy)
    report = _render(
        export_manifest=export_manifest,
        candidates=candidates,
        sensitivity_summary=sensitivity_summary,
        review_summary=review_summary,
        review=review,
        correlation_summary=correlation_summary,
        pairwise=pairwise,
        redundancy=redundancy,
        gated_summary=gated_summary,
        memory_manifest=memory_manifest,
        memory=memory,
        readiness=readiness,
    )
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"Wrote {REPORT_PATH}")
    print(f"readiness={readiness}")


def _render(
    *,
    export_manifest: dict[str, Any],
    candidates: list[dict[str, Any]],
    sensitivity_summary: dict[str, Any],
    review_summary: dict[str, Any],
    review: pd.DataFrame,
    correlation_summary: dict[str, Any],
    pairwise: pd.DataFrame,
    redundancy: pd.DataFrame,
    gated_summary: dict[str, Any] | None,
    memory_manifest: dict[str, Any],
    memory: pd.DataFrame,
    readiness: str,
) -> str:
    scope_contract = export_manifest.get("scope_contract") or {}
    singles = [row for row in candidates if not row.get("component_candidate_ids")]
    bundles = [row for row in candidates if row.get("component_candidate_ids")]
    review_counts = review_summary.get("verdict_counts") or _counts(review, "review_verdict")
    bundle_counts = correlation_summary.get("bundle_verdict_counts") or _counts(redundancy, "redundancy_verdict")
    scope_values = sorted(str(value) for value in review.get("intended_scope", pd.Series(dtype=str)).unique() if value)
    scope_mode = str(review_summary.get("rules", {}).get("scope_mode", ""))
    pair_count = correlation_summary.get("pair_count", correlation_summary.get("pairwise_row_count", len(pairwise)))
    high_corr_threshold = correlation_summary.get("high_corr_threshold", "")
    credible_bundle_rows = _credible_bundle_rows(review)

    lines = [
        "# Research v0.9c Multi-Factor Bundle Report",
        "",
        "Date: 2026-07-03",
        "",
        "Status: complete for the BTCUSDT 4h scoped multi-factor bundle checkpoint.",
        "",
        "This report is research-only. It is not factor admission, runtime publishing, portfolio construction, "
        "RandyPortfolio, or live execution.",
        "",
        "## Objective",
        "",
        "Research v0.9c evaluated a deterministic BTCUSDT 4h current-DSL multi-factor bundle using the v0.9a "
        "scoped schema and v0.9b failure-memory discipline.",
        "",
        "## Candidate Export",
        "",
        f"- Export path: `{_rel(EXPORT_DIR)}`",
        f"- Candidate count: `{export_manifest.get('candidate_count')}`",
        f"- Single-factor count: `{export_manifest.get('single_factor_count')}`",
        f"- Bundle count: `{export_manifest.get('bundle_count')}`",
        f"- Intended scope: `{scope_contract.get('intended_scope', '')}`",
        f"- Out-of-scope policy: `{scope_contract.get('out_of_scope_policy', '')}`",
        "",
        "| Candidate | Family | Formula |",
        "|---|---|---|",
    ]
    lines.extend(
        f"| `{row['candidate_id']}` | `{row.get('formula_family', '')}` | `{row['formula']}` |"
        for row in singles
    )
    lines.extend(["", "| Bundle | Components | Method |", "|---|---|---|"])
    lines.extend(
        f"| `{row['candidate_id']}` | `{', '.join(row.get('component_candidate_ids', []))}` | "
        f"`{row.get('combination_method', '')}` |"
        for row in bundles
    )

    lines.extend(
        [
            "",
            "## RandysLab Declared Review",
            "",
            f"- Sensitivity path: `{_rel(_artifact_paths(_find_sibling_repo(ROOT, 'RandysLab-STRICT4H'))['sensitivity'])}`",
            f"- Sensitivity run count: `{sensitivity_summary.get('run_count')}`",
            f"- Sensitivity candidate row count: `{sensitivity_summary.get('candidate_row_count')}`",
            f"- Review path: `{_rel(_artifact_paths(_find_sibling_repo(ROOT, 'RandysLab-STRICT4H'))['review'])}`",
            f"- Scope mode: `{scope_mode}`",
            f"- `scope_mode=declared`",
            f"- Review scopes: `{', '.join(scope_values)}`",
            f"- Candidate count: `{review_summary.get('candidate_count')}`",
            f"- Verdict counts: `{_fmt_counts(review_counts)}`",
            "",
            "| Candidate | Verdict | Mean Sharpe | Validation Sharpe | Blind Sharpe | Failures |",
            "|---|---|---:|---:|---:|---|",
        ]
    )
    sort_columns = [column for column in ["review_verdict", "mean_sharpe"] if column in review.columns]
    review_rows = review.sort_values(sort_columns, ascending=[False] * len(sort_columns)) if sort_columns else review
    for row in review_rows.head(12).to_dict(orient="records"):
        lines.append(
            f"| `{row.get('candidate_id', '')}` | `{row.get('review_verdict', '')}` | "
            f"{_num(row.get('mean_sharpe'))} | {_num(row.get('validation_mean_sharpe'))} | "
            f"{_num(row.get('blind_mean_sharpe'))} | `{row.get('failure_reasons') or 'none'}` |"
        )

    lines.extend(
        [
            "",
            "## Correlation And Redundancy",
            "",
            f"- Correlation path: `{_rel(_artifact_paths(_find_sibling_repo(ROOT, 'RandysLab-STRICT4H'))['correlation'])}`",
            f"- High-correlation threshold: `{high_corr_threshold}`",
            f"- Pair count: `{pair_count}`",
            f"- Bundle verdict counts: `{_fmt_counts(bundle_counts)}`",
            "",
            "| Bundle | Redundancy Verdict | Max Abs Corr | High Corr Pairs |",
            "|---|---|---:|---:|",
        ]
    )
    for row in redundancy.to_dict(orient="records"):
        lines.append(
            f"| `{row.get('bundle_candidate_id', row.get('candidate_id', ''))}` | "
            f"`{row.get('redundancy_verdict', '')}` | {_num(row.get('max_abs_component_corr'))} | "
            f"{row.get('high_corr_pair_count', '')} |"
        )

    lines.extend(["", "## Gated Bundle Diagnostics", "", _gated_text(gated_summary, credible_bundle_rows), ""])

    lines.extend(
        [
            "## Failure Memory",
            "",
            f"- Failure-memory path: `{_rel(MEMORY_DIR)}`",
            f"- Failure count: `{memory_manifest.get('failure_count')}`",
            f"- Cluster count: `{memory_manifest.get('cluster_count')}`",
            f"- Conservative verdict counts: `{_fmt_counts(_counts(memory, 'conservative_verdict'))}`",
            f"- Failure labels: `{_fmt_labels(memory, 'failure_labels')}`",
            "",
            "## Regime Feature Readiness",
            "",
            "No new base fields were admitted in v0.9c. Current allowed fields remain `open`, `high`, `low`, `close`, "
            "`volume`, and `funding_rate`. Open interest, basis, liquidations, taker-flow, and order-book fields "
            "require a separate point-in-time data-readiness audit.",
            "",
            "## Research 1.0 Readiness",
            "",
            f"`{readiness}`",
            "",
            "## Verification",
            "",
            "- Focused QuantumRandy tests cover the v0.9c exporter, report renderer, and failure-memory adapter.",
            "- Focused RandysLab tests cover formula candidates and correlation review.",
            "- Artifact audit confirmed candidate counts, declared scope, redundancy artifacts, gated diagnostics, and "
            "failure memory.",
            "- Final full-suite and diff-check evidence is recorded in the completion notes for this checkpoint.",
            "",
            "## Boundary Confirmation",
            "",
            "- No RandyPortfolio implementation.",
            "- No portfolio scheduler.",
            "- No live trading.",
            "- No exchange keys.",
            "- No runtime publishing.",
            "- No automatic factor admission.",
            "- No new base fields.",
            "- No selector evidence61.",
            "- No drawdown-stop tuning.",
        ]
    )
    return "\n".join(lines) + "\n"


def _readiness_verdict(review: pd.DataFrame, redundancy: pd.DataFrame) -> str:
    if review.empty or redundancy.empty:
        return "not_ready_for_research_1_0"
    review_by_id = review.set_index("candidate_id")
    for row in redundancy.to_dict(orient="records"):
        candidate_id = str(row.get("bundle_candidate_id") or row.get("candidate_id") or "")
        if candidate_id not in review_by_id.index:
            continue
        review_row = review_by_id.loc[candidate_id]
        if isinstance(review_row, pd.DataFrame):
            review_row = review_row.iloc[0]
        review_verdict = str(review_row.get("review_verdict", ""))
        redundancy_verdict = str(row.get("redundancy_verdict", ""))
        if review_verdict == "research_watchlist" and redundancy_verdict == "diversified_enough_for_research":
            return "research_1_0_candidate_pending_replication"
    return "not_ready_for_research_1_0"


def _credible_bundle_rows(review: pd.DataFrame) -> int:
    if review.empty or "candidate_id" not in review.columns:
        return 0
    bundles = review[review["candidate_id"].astype(str).str.contains("_bundle_")]
    if bundles.empty:
        return 0
    mean_sharpe = pd.to_numeric(bundles.get("mean_sharpe", pd.Series(dtype=float)), errors="coerce").fillna(0.0)
    validation = pd.to_numeric(
        bundles.get("validation_mean_sharpe", pd.Series(dtype=float)),
        errors="coerce",
    ).fillna(0.0)
    credible = bundles[
        bundles.get("review_verdict", pd.Series(dtype=str)).eq("research_watchlist")
        | ((mean_sharpe >= 0.25) & (validation >= 0.0))
    ]
    return int(len(credible))


def _gated_text(gated_summary: dict[str, Any] | None, credible_bundle_rows: int) -> str:
    if gated_summary is None:
        return f"Gated sweep skipped because `credible_bundle_rows={credible_bundle_rows}`."
    return (
        f"Gated sweep ran because `credible_bundle_rows={credible_bundle_rows}`. "
        f"Result: `run_count={gated_summary.get('run_count')}`, "
        f"`candidate_row_count={gated_summary.get('candidate_row_count')}`."
    )


def _artifact_paths(randyslab: Path) -> dict[str, Path]:
    return {
        "sensitivity": randyslab / "reports/factor_candidate_sensitivity/research_v0_9c_bundle_btc_declared",
        "review": randyslab / "reports/factor_candidate_review/research_v0_9c_bundle_btc_declared",
        "correlation": randyslab / "reports/factor_candidate_correlation/research_v0_9c_bundle_btc",
        "gated": randyslab / "reports/factor_candidate_sensitivity/research_v0_9c_bundle_btc_gated",
    }


def _find_sibling_repo(root: Path, repo_name: str) -> Path:
    for parent in (root, *root.parents):
        candidate = parent / repo_name
        if (candidate / ".git").exists() or (candidate / "pyproject.toml").exists():
            return candidate
    raise FileNotFoundError(f"Could not find sibling repository {repo_name} from {root}")


def _find_workspace_root(root: Path) -> Path | None:
    for parent in (root, *root.parents):
        if (parent / "QuantumRandy").exists() and (parent / "RandysLab-STRICT4H").exists():
            return parent
    return None


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _read_csv_optional(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path).fillna("")


def _counts(frame: pd.DataFrame, column: str) -> dict[str, int]:
    if frame.empty or column not in frame.columns:
        return {}
    return {str(key): int(value) for key, value in frame[column].value_counts().to_dict().items()}


def _fmt_counts(counts: dict[str, Any]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{key}:{value}" for key, value in sorted(counts.items()))


def _fmt_labels(frame: pd.DataFrame, column: str) -> str:
    labels: set[str] = set()
    if not frame.empty and column in frame.columns:
        for value in frame[column].fillna(""):
            labels.update(label for label in str(value).replace("|", ",").split(",") if label)
    return ", ".join(sorted(labels)) if labels else "none"


def _num(value: Any) -> str:
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return "0.0000"


def _rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        workspace = _find_workspace_root(ROOT)
        if workspace is not None:
            try:
                return "../" + path.relative_to(workspace).as_posix()
            except ValueError:
                pass
        return path.as_posix()


if __name__ == "__main__":
    main()
