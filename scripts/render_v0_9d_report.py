from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

EXPORT_DIR = ROOT / "reports/factor_candidate_exports/research_v0_9d_strict_candidate_discovery"
MEMORY_DIR = ROOT / "reports/failure_memory/research_v0_9d_strict_candidate_discovery"
REPORT_PATH = ROOT / "docs/RESEARCH_V0_9D_STRICT_CANDIDATE_DISCOVERY_REPORT.md"


def main() -> None:
    randyslab = _find_sibling_repo(ROOT, "RandysLab-STRICT4H")
    paths = _artifact_paths(randyslab)
    export_manifest = _json(EXPORT_DIR / "factor_candidate_export_manifest.json")
    candidates = _jsonl(EXPORT_DIR / "factor_candidates.jsonl")
    btc_sensitivity_summary = _json(paths["btc_sensitivity"] / "factor_candidate_sensitivity_summary.json")
    btc_review_summary = _json(paths["btc_review"] / "factor_candidate_review_summary.json")
    btc_review = pd.read_csv(paths["btc_review"] / "factor_candidate_review.csv").fillna("")
    eth_sensitivity_summary = _json(paths["eth_sensitivity"] / "factor_candidate_sensitivity_summary.json")
    eth_review_summary = _json(paths["eth_review"] / "factor_candidate_review_summary.json")
    eth_review = pd.read_csv(paths["eth_review"] / "factor_candidate_review.csv").fillna("")
    correlation_summary = _json(paths["correlation"] / "factor_candidate_correlation_summary.json")
    redundancy = pd.read_csv(paths["correlation"] / "factor_candidate_bundle_redundancy.csv").fillna("")
    wider_summaries = _wider_summaries(paths)
    memory_manifest = _json(MEMORY_DIR / "failure_memory_manifest.json")
    memory = pd.read_csv(MEMORY_DIR / "failure_memory.csv").fillna("")

    readiness = _readiness_verdict(btc_review, eth_review, redundancy)
    report = _render(
        export_manifest=export_manifest,
        candidates=candidates,
        btc_sensitivity_summary=btc_sensitivity_summary,
        btc_review_summary=btc_review_summary,
        btc_review=btc_review,
        eth_sensitivity_summary=eth_sensitivity_summary,
        eth_review_summary=eth_review_summary,
        eth_review=eth_review,
        correlation_summary=correlation_summary,
        redundancy=redundancy,
        wider_summaries=wider_summaries,
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
    btc_sensitivity_summary: dict[str, Any],
    btc_review_summary: dict[str, Any],
    btc_review: pd.DataFrame,
    eth_sensitivity_summary: dict[str, Any],
    eth_review_summary: dict[str, Any],
    eth_review: pd.DataFrame,
    correlation_summary: dict[str, Any],
    redundancy: pd.DataFrame,
    wider_summaries: dict[str, dict[str, Any]],
    memory_manifest: dict[str, Any],
    memory: pd.DataFrame,
    readiness: str,
) -> str:
    scope_contract = export_manifest.get("scope_contract") or {}
    singles = [row for row in candidates if not row.get("component_candidate_ids")]
    bundles = [row for row in candidates if row.get("component_candidate_ids")]
    btc_counts = btc_review_summary.get("verdict_counts") or _counts(btc_review, "review_verdict")
    eth_counts = eth_review_summary.get("verdict_counts") or _counts(eth_review, "review_verdict")
    bundle_counts = correlation_summary.get("bundle_verdict_counts") or _counts(redundancy, "redundancy_verdict")
    btc_scope_values = sorted(str(value) for value in btc_review.get("intended_scope", pd.Series(dtype=str)).unique() if value)
    btc_scope_mode = str(btc_review_summary.get("rules", {}).get("scope_mode", ""))
    eth_scope_mode = str(eth_review_summary.get("rules", {}).get("scope_mode", ""))
    pair_count = correlation_summary.get("pair_count", correlation_summary.get("pairwise_row_count", ""))
    high_corr_threshold = correlation_summary.get("high_corr_threshold", "")

    lines = [
        "# Research v0.9d Strict Candidate-Family Discovery Report",
        "",
        "Date: 2026-07-03",
        "",
        "Status: complete for the BTCUSDT 4h strict candidate-family discovery checkpoint.",
        "",
        "This report is research-only. It is not factor admission, runtime publishing, portfolio construction, "
        "RandyPortfolio, or live execution.",
        "",
        "## Objective",
        "",
        "Research v0.9d tested deterministic current-DSL candidate families under the v0.9a scoped schema, "
        "v0.9b/v0.9c failure-memory discipline, and RandysLab strict declared-scope review.",
        "",
        "## Dependency Confirmation",
        "",
        "- Research v0.9a scoped schema and strict-judge alignment are complete.",
        "- Research v0.9b funding-pressure single-family review and failure memory are complete.",
        "- Research v0.9c multi-factor bundle review, redundancy review, and failure memory are complete.",
        "- Research 1.0 prerequisite closure verified the test suites and admitted no new formula base fields.",
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
            "## BTC Primary Declared Review",
            "",
            f"- Sensitivity path: `{_rel(_artifact_paths(_find_sibling_repo(ROOT, 'RandysLab-STRICT4H'))['btc_sensitivity'])}`",
            f"- Sensitivity run count: `{btc_sensitivity_summary.get('run_count')}`",
            f"- Sensitivity candidate row count: `{btc_sensitivity_summary.get('candidate_row_count')}`",
            f"- Review path: `{_rel(_artifact_paths(_find_sibling_repo(ROOT, 'RandysLab-STRICT4H'))['btc_review'])}`",
            f"- Scope mode: `{btc_scope_mode}`",
            f"- `scope_mode=declared`",
            f"- Review scopes: `{', '.join(btc_scope_values)}`",
            f"- Candidate count: `{btc_review_summary.get('candidate_count')}`",
            f"- Verdict counts: `{_fmt_counts(btc_counts)}`",
            "",
            "| Candidate | Verdict | Mean Sharpe | Validation Sharpe | Blind Sharpe | Failures |",
            "|---|---|---:|---:|---:|---|",
        ]
    )
    for row in _sorted_review_rows(btc_review):
        lines.append(
            f"| `{row.get('candidate_id', '')}` | `{row.get('review_verdict', '')}` | "
            f"{_num(row.get('mean_sharpe'))} | {_num(row.get('validation_mean_sharpe'))} | "
            f"{_num(row.get('blind_mean_sharpe'))} | `{row.get('failure_reasons') or 'none'}` |"
        )

    lines.extend(
        [
            "",
            "## ETH Diagnostic Review",
            "",
            "ETH diagnostics are portability and fragility evidence only; they do not change the declared BTC scope and "
            "do not create production portfolio filters.",
            "",
            f"- Sensitivity path: `{_rel(_artifact_paths(_find_sibling_repo(ROOT, 'RandysLab-STRICT4H'))['eth_sensitivity'])}`",
            f"- Sensitivity run count: `{eth_sensitivity_summary.get('run_count')}`",
            f"- Sensitivity candidate row count: `{eth_sensitivity_summary.get('candidate_row_count')}`",
            f"- Review path: `{_rel(_artifact_paths(_find_sibling_repo(ROOT, 'RandysLab-STRICT4H'))['eth_review'])}`",
            f"- Scope mode: `{eth_scope_mode}`",
            f"- Candidate count: `{eth_review_summary.get('candidate_count')}`",
            f"- Verdict counts: `{_fmt_counts(eth_counts)}`",
            "",
            "| Candidate | Verdict | Mean Sharpe | Validation Sharpe | Blind Sharpe | Failures |",
            "|---|---|---:|---:|---:|---|",
        ]
    )
    for row in _sorted_review_rows(eth_review):
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

    lines.extend(["", "## Wider Diagnostics", "", _wider_text(wider_summaries), ""])

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
            "## Research 1.0 Readiness",
            "",
            f"`{readiness}`",
            "",
            "## Verification",
            "",
            "- Focused QuantumRandy tests cover the v0.9d exporter, failure-memory adapter, and report renderer.",
            "- Focused RandysLab tests cover formula-candidate execution and correlation review.",
            "- Full QuantumRandy and RandysLab suites are required before the final v0.9d commit.",
            "- Artifact audit confirms candidate counts, declared scope, BTC/ETH review artifacts, redundancy artifacts, "
            "and failure memory.",
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
            "- No production regime labels.",
            "- No selector evidence61.",
            "- No drawdown-stop tuning.",
        ]
    )
    return "\n".join(lines) + "\n"


def _readiness_verdict(btc_review: pd.DataFrame, eth_review: pd.DataFrame, redundancy: pd.DataFrame) -> str:
    if btc_review.empty:
        return "not_ready_for_research_1_0"
    redundant = _redundant_candidate_ids(redundancy)
    diagnostic_weak = _diagnostic_weak_candidate_ids(eth_review)
    for row in btc_review.to_dict(orient="records"):
        candidate_id = str(row.get("candidate_id", ""))
        if str(row.get("review_verdict", "")) != "research_watchlist":
            continue
        if candidate_id in redundant:
            continue
        if candidate_id in diagnostic_weak:
            return "scoped_watchlist_needs_replication"
        return "research_1_0_candidate_pending_replication"
    return "not_ready_for_research_1_0"


def _redundant_candidate_ids(redundancy: pd.DataFrame) -> set[str]:
    if redundancy.empty:
        return set()
    rows = redundancy[redundancy.get("redundancy_verdict", pd.Series(dtype=str)).eq("redundant_research_memory_only")]
    return {str(row.get("bundle_candidate_id") or row.get("candidate_id") or "") for row in rows.to_dict(orient="records")}


def _diagnostic_weak_candidate_ids(review: pd.DataFrame) -> set[str]:
    if review.empty:
        return set()
    weak: set[str] = set()
    for row in review.to_dict(orient="records"):
        candidate_id = str(row.get("candidate_id", ""))
        if not candidate_id:
            continue
        if str(row.get("review_verdict", "")) and str(row.get("review_verdict", "")) != "research_watchlist":
            weak.add(candidate_id)
            continue
        if str(row.get("failure_reasons", "")).strip():
            weak.add(candidate_id)
            continue
        if _float(row.get("validation_mean_sharpe", "")) < 0.0 or _float(row.get("blind_mean_sharpe", "")) < 0.0:
            weak.add(candidate_id)
    return weak


def _artifact_paths(randyslab: Path) -> dict[str, Path]:
    return {
        "btc_sensitivity": randyslab / "reports/factor_candidate_sensitivity/research_v0_9d_btc_primary",
        "btc_review": randyslab / "reports/factor_candidate_review/research_v0_9d_btc_primary",
        "eth_sensitivity": randyslab / "reports/factor_candidate_sensitivity/research_v0_9d_eth_diagnostic",
        "eth_review": randyslab / "reports/factor_candidate_review/research_v0_9d_eth_diagnostic",
        "correlation": randyslab / "reports/factor_candidate_correlation/research_v0_9d_btc",
        "wider_sol": randyslab / "reports/factor_candidate_review/research_v0_9d_sol_diagnostic",
        "wider_bnb": randyslab / "reports/factor_candidate_review/research_v0_9d_bnb_diagnostic",
        "wider_avax": randyslab / "reports/factor_candidate_review/research_v0_9d_avax_diagnostic",
    }


def _wider_summaries(paths: dict[str, Path]) -> dict[str, dict[str, Any]]:
    summaries: dict[str, dict[str, Any]] = {}
    for label in ["wider_sol", "wider_bnb", "wider_avax"]:
        path = paths[label] / "factor_candidate_review_summary.json"
        if path.exists():
            summaries[label] = _json(path)
    return summaries


def _wider_text(wider_summaries: dict[str, dict[str, Any]]) -> str:
    if not wider_summaries:
        return "Wider SOL/BNB/AVAX diagnostics were skipped because no BTC primary condition required them, or they were not generated."
    parts = []
    for label, summary in sorted(wider_summaries.items()):
        parts.append(
            f"- `{label}`: candidate_count=`{summary.get('candidate_count')}`, "
            f"verdict_counts=`{_fmt_counts(summary.get('verdict_counts') or {})}`"
        )
    return "\n".join(parts)


def _sorted_review_rows(review: pd.DataFrame) -> list[dict[str, Any]]:
    if review.empty:
        return []
    sort_columns = [column for column in ["review_verdict", "mean_sharpe"] if column in review.columns]
    if not sort_columns:
        return review.to_dict(orient="records")
    return review.sort_values(sort_columns, ascending=[False] * len(sort_columns)).to_dict(orient="records")


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


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


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
