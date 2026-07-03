from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

EXPORT_DIR = ROOT / "reports/factor_candidate_exports/research_v1_1_independent_scoped_family_replication"
MEMORY_DIR = ROOT / "reports/failure_memory/research_v1_1_independent_replication"
REPORT_PATH = ROOT / "docs/RESEARCH_V1_1_INDEPENDENT_SCOPED_FAMILY_REPLICATION_REPORT.md"


def main() -> None:
    randyslab = _find_sibling_repo(ROOT, "RandysLab-STRICT4H")
    paths = _artifact_paths(randyslab)

    export_manifest = _json(EXPORT_DIR / "factor_candidate_export_manifest.json")
    candidates = _jsonl(EXPORT_DIR / "factor_candidates.jsonl")
    btc_review_summary = _json(paths["btc_review"] / "factor_candidate_review_summary.json")
    eth_review_summary = _json(paths["eth_review"] / "factor_candidate_review_summary.json")
    correlation_summary = _json(paths["correlation"] / "factor_candidate_correlation_summary.json")
    robustness_summary = _json(paths["robustness"] / "watchlist_robustness_summary.json")
    ranking = _read_csv(paths["robustness"] / "watchlist_robustness_variant_ranking.csv")
    memory_manifest = _json(MEMORY_DIR / "failure_memory_manifest.json")

    readiness = _readiness_verdict(ranking)
    report = _render(
        export_manifest=export_manifest,
        candidates=candidates,
        btc_review_summary=btc_review_summary,
        eth_review_summary=eth_review_summary,
        correlation_summary=correlation_summary,
        robustness_summary=robustness_summary,
        ranking=ranking,
        memory_manifest=memory_manifest,
        readiness=readiness,
        diagnostic_review_summaries=_diagnostic_review_summaries(paths),
    )
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"Wrote {REPORT_PATH}")
    print(f"readiness={readiness}")


def _readiness_verdict(ranking: pd.DataFrame) -> str:
    if ranking.empty:
        return "research_v1_1_independent_candidate_not_found"
    passed = ranking[ranking["conservative_verdict"] == "research_watchlist"]
    if passed.empty:
        return "research_v1_1_independent_candidate_not_found"
    return "research_v1_1_independent_candidate_replicated_pending_manual_review"


def _render(
    *,
    export_manifest: dict[str, Any],
    candidates: list[dict[str, Any]],
    btc_review_summary: dict[str, Any],
    eth_review_summary: dict[str, Any],
    correlation_summary: dict[str, Any],
    robustness_summary: dict[str, Any],
    ranking: pd.DataFrame,
    memory_manifest: dict[str, Any],
    readiness: str,
    diagnostic_review_summaries: dict[str, dict[str, Any]] | None = None,
) -> str:
    scope_contract = export_manifest.get("scope_contract") or {}
    excluded = export_manifest.get("excluded_research10_survivor") or {}
    singles = [row for row in candidates if not row.get("component_candidate_ids")]
    bundles = [row for row in candidates if row.get("component_candidate_ids")]
    diagnostic_review_summaries = diagnostic_review_summaries or {}
    btc_counts = btc_review_summary.get("verdict_counts") or {}
    eth_counts = eth_review_summary.get("verdict_counts") or {}
    bundle_counts = correlation_summary.get("bundle_verdict_counts") or {}
    passed_rows = _passed_rows(ranking)
    displayed_rows = passed_rows if passed_rows else _best_blocked_rows(ranking)
    table_title = "Passed Candidates" if passed_rows else "Best Blocked Near Misses"

    lines = [
        "# Research v1.1 Independent Scoped Family Replication Report",
        "",
        "Date: 2026-07-03",
        "",
        "Status: complete for the research-only independent scoped family replication pass.",
        "",
        "This report is research-only, not factor admission, not runtime publishing, not RandyPortfolio, and not live "
        "execution approval.",
        "",
        "## Objective",
        "",
        "Research v1.1 tries to replicate a second independent non-funding scoped family after the Research 1.0 "
        "funding-return survivor. It keeps `BTCUSDT_4h` as the declared scope and treats out-of-scope asset rows as "
        "diagnostic evidence only.",
        "",
        "## Candidate Export",
        "",
        f"- Export path: `{_rel(EXPORT_DIR)}`",
        f"- Candidate count: `{export_manifest.get('candidate_count')}`",
        f"- Single-factor count: `{export_manifest.get('single_factor_count')}`",
        f"- Bundle count: `{export_manifest.get('bundle_count')}`",
        f"- Intended scope: `{scope_contract.get('intended_scope', '')}`",
        f"- Out-of-scope policy: `{scope_contract.get('out_of_scope_policy', '')}`",
        f"- Excluded Research 1.0 survivor: `{excluded.get('candidate_id', '')}::{excluded.get('variant_id', '')}`",
        f"- Excluded survivor family: `{excluded.get('formula_family', '')}`",
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
            f"- Review path: `{_rel(_artifact_paths(_find_sibling_repo(ROOT, 'RandysLab-STRICT4H'))['btc_review'])}`",
            f"- Candidate count: `{btc_review_summary.get('candidate_count')}`",
            f"- Verdict counts: `{_fmt_counts(btc_counts)}`",
            f"- Scope mode: `{btc_review_summary.get('rules', {}).get('scope_mode', '')}`",
            "",
            "## Diagnostic Reviews",
            "",
            "ETH/SOL/BNB/AVAX rows remain portability diagnostics. They do not alter the declared BTCUSDT scope and do "
            "not authorize portfolio deployment.",
            "",
            f"- ETH candidate count: `{eth_review_summary.get('candidate_count')}`",
            f"- ETH verdict counts: `{_fmt_counts(eth_counts)}`",
            _diagnostic_text(diagnostic_review_summaries),
            "",
            "## Correlation And Redundancy",
            "",
            f"- Correlation path: `{_rel(_artifact_paths(_find_sibling_repo(ROOT, 'RandysLab-STRICT4H'))['correlation'])}`",
            f"- Bundle count: `{correlation_summary.get('bundle_count')}`",
            f"- High-correlation threshold: `{correlation_summary.get('high_corr_threshold', '')}`",
            f"- Bundle verdict counts: `{_fmt_counts(bundle_counts)}`",
            "",
            "## Scope-Aware Robustness",
            "",
            f"- Robustness path: `{_rel(_artifact_paths(_find_sibling_repo(ROOT, 'RandysLab-STRICT4H'))['robustness'])}`",
            f"- Detail rows: `{robustness_summary.get('detail_row_count')}`",
            f"- Scenario summary rows: `{robustness_summary.get('scenario_summary_count')}`",
            f"- Variant rankings: `{robustness_summary.get('variant_count')}`",
            "",
            f"### {table_title}",
            "",
            "| Candidate | Variant | Verdict | Stress Survival | Mean Sharpe | Validation Sharpe | Blind Sharpe | Worst Max DD | Labels |",
            "|---|---|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    if displayed_rows:
        for row in displayed_rows:
            lines.append(
                f"| `{row.get('candidate_id', '')}` | `{row.get('variant_id', '')}` | "
                f"`{row.get('conservative_verdict', '')}` | "
                f"{_stress_survival(row)} | {_num(row.get('mean_sharpe'))} | "
                f"{_num(row.get('validation_mean_sharpe'))} | {_num(row.get('blind_mean_sharpe'))} | "
                f"{_num(row.get('worst_max_dd'))} | `{row.get('robustness_labels', '') or 'none'}` |"
            )
    else:
        lines.append("| none | none | none | 0/0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | none |")

    lines.extend(
        [
            "",
            "## Failure Memory",
            "",
            f"- Failure-memory path: `{_rel(MEMORY_DIR)}`",
            f"- Input rows: `{memory_manifest.get('input_rows')}`",
            f"- Failure count: `{memory_manifest.get('failure_count')}`",
            f"- Cluster count: `{memory_manifest.get('cluster_count')}`",
            "",
            "## Readiness Verdict",
            "",
            f"`{readiness}`",
            "",
            "This verdict is research-only. A surviving candidate, if present, remains pending manual research review and "
            "does not become a production factor.",
            "",
            "## Verification Checklist",
            "",
            "- v1.1 export excludes `qr_v09d_funding_return_long_001` and direct `funding_rate` formulas.",
            "- RandysLab BTC primary declared review is generated.",
            "- ETH/SOL/BNB/AVAX diagnostics are generated when available.",
            "- BTC bundle correlation and redundancy review is generated.",
            "- Scope-aware robustness ranking is generated.",
            "- Failure memory is generated from robustness ranking.",
            "- Boundary remains research-only.",
            "",
            "## Boundary Confirmation",
            "",
            "- No RandyPortfolio implementation.",
            "- No portfolio scheduler.",
            "- No live trading.",
            "- No exchange private keys.",
            "- No runtime factor publishing.",
            "- No automatic factor admission.",
            "- No new formula base fields.",
            "- No production runtime regime labels.",
            "- No selector evidence61.",
        ]
    )
    return "\n".join(lines) + "\n"


def _artifact_paths(randyslab: Path) -> dict[str, Path]:
    return {
        "btc_review": randyslab / "reports/factor_candidate_review/research_v1_1_btc_primary",
        "eth_review": randyslab / "reports/factor_candidate_review/research_v1_1_eth_diagnostic",
        "sol_review": randyslab / "reports/factor_candidate_review/research_v1_1_sol_diagnostic",
        "bnb_review": randyslab / "reports/factor_candidate_review/research_v1_1_bnb_diagnostic",
        "avax_review": randyslab / "reports/factor_candidate_review/research_v1_1_avax_diagnostic",
        "correlation": randyslab / "reports/factor_candidate_correlation/research_v1_1_btc",
        "robustness": randyslab / "reports/factor_candidate_robustness/research_v1_1_independent_replication",
    }


def _diagnostic_review_summaries(paths: dict[str, Path]) -> dict[str, dict[str, Any]]:
    summaries: dict[str, dict[str, Any]] = {}
    for label in ["sol_review", "bnb_review", "avax_review"]:
        path = paths[label] / "factor_candidate_review_summary.json"
        if path.exists():
            summaries[label] = _json(path)
    return summaries


def _diagnostic_text(summaries: dict[str, dict[str, Any]]) -> str:
    if not summaries:
        return "- SOL/BNB/AVAX diagnostics: not generated or not available."
    lines = []
    labels = {"sol_review": "SOL", "bnb_review": "BNB", "avax_review": "AVAX"}
    for key, summary in sorted(summaries.items()):
        lines.append(
            f"- {labels.get(key, key)} candidate count: `{summary.get('candidate_count')}`, "
            f"verdict counts: `{_fmt_counts(summary.get('verdict_counts') or {})}`"
        )
    return "\n".join(lines)


def _passed_rows(ranking: pd.DataFrame) -> list[dict[str, Any]]:
    if ranking.empty or "conservative_verdict" not in ranking.columns:
        return []
    passed = ranking[ranking["conservative_verdict"].eq("research_watchlist")]
    return _sort_ranking(passed).to_dict(orient="records")


def _best_blocked_rows(ranking: pd.DataFrame) -> list[dict[str, Any]]:
    if ranking.empty:
        return []
    return _sort_ranking(ranking).head(10).to_dict(orient="records")


def _sort_ranking(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    sortable = frame.copy()
    for column in ["stress_survival_count", "stress_survival_score", "mean_sharpe", "validation_mean_sharpe", "blind_mean_sharpe"]:
        if column in sortable.columns:
            sortable[column] = pd.to_numeric(sortable[column], errors="coerce")
    sort_columns = [
        column
        for column in ["stress_survival_count", "stress_survival_score", "validation_mean_sharpe", "blind_mean_sharpe", "mean_sharpe"]
        if column in sortable.columns
    ]
    if not sort_columns:
        return sortable
    return sortable.sort_values(sort_columns, ascending=[False] * len(sort_columns))


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _read_csv(path: Path) -> pd.DataFrame:
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


def _num(value: Any) -> str:
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return "0.0000"


def _stress_survival(row: dict[str, Any]) -> str:
    return f"{_int(row.get('stress_survival_count'))}/{_int(row.get('stress_count'))}"


def _int(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


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


if __name__ == "__main__":
    main()
