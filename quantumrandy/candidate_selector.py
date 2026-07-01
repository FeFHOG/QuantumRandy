from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .expression import subtrees
from .io_utils import safe_write_csv, safe_write_json, safe_write_text
from .walk_forward import stable_factor_id


@dataclass(frozen=True)
class CandidateSelectorPolicy:
    min_rewrite_universe_pass_rate: float = 0.40
    min_keep_universe_pass_rate: float = 0.60
    min_keep_mean_sharpe: float = 0.0
    max_cluster_pass_rate: float = 0.20
    min_cluster_size: int = 2


def select_research_candidates(
    leaderboard_rows: list[dict[str, Any]],
    *,
    universe_summary: pd.DataFrame | None = None,
    portfolio_universe_summary: pd.DataFrame | None = None,
    failure_memory: pd.DataFrame | None = None,
    failure_clusters: pd.DataFrame | None = None,
    policy: CandidateSelectorPolicy | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    policy = policy or CandidateSelectorPolicy()
    universe_by_factor = _index_records(universe_summary, "factor_id")
    universe_by_formula = _index_records(universe_summary, "formula")
    portfolio_evidence = _portfolio_evidence_by_factor(portfolio_universe_summary)
    failed_subtrees = _failed_subtree_counts(failure_memory, failure_clusters)

    rows = []
    for index, row in enumerate(leaderboard_rows, start=1):
        formula = str(row.get("formula", ""))
        if not formula:
            continue
        factor_id = _factor_id(row, formula, index)
        universe = universe_by_factor.get(factor_id, {}) or universe_by_formula.get(formula, {})
        portfolio = portfolio_evidence.get(factor_id, {})
        tree_hits = _matched_failed_subtrees(formula, failed_subtrees)
        decision = _candidate_row(row, factor_id, universe, portfolio, tree_hits, policy)
        rows.append(decision)

    candidates = pd.DataFrame(rows)
    if not candidates.empty:
        candidates = candidates.sort_values(
            ["selector_score", "universe_pass_rate", "leaderboard_score"],
            ascending=[False, False, False],
        ).reset_index(drop=True)

    cluster_frame = _build_universe_failure_clusters(candidates, policy)
    rewrite_frame = _build_rewrite_targets(candidates)
    manifest = {
        "artifact_type": "quantumrandy_research_candidate_selector",
        "schema_version": 1,
        "safety": {
            "research_only": True,
            "not_runtime_publish_payload": True,
            "does_not_update_runtime": True,
            "does_not_auto_admit_factors": True,
        },
        "policy": asdict(policy),
        "input_count": len(leaderboard_rows),
        "candidate_count": len(candidates),
        "rewrite_target_count": len(rewrite_frame),
        "cluster_count": len(cluster_frame),
        "verdict_counts": _value_counts(candidates, "selector_verdict"),
        "usage": [
            "Use rewrite targets as research prompt context or manual mining priority.",
            "Use cluster rows as negative evidence for repeated BTC-only or fragile structures.",
            "Do not publish selected candidates to runtime without separate admission and manual review.",
        ],
    }
    return candidates, cluster_frame, rewrite_frame, manifest


def write_candidate_selector_report(
    leaderboard_rows: list[dict[str, Any]],
    out_dir: str | Path,
    *,
    universe_summary: pd.DataFrame | None = None,
    portfolio_universe_summary: pd.DataFrame | None = None,
    failure_memory: pd.DataFrame | None = None,
    failure_clusters: pd.DataFrame | None = None,
    policy: CandidateSelectorPolicy | None = None,
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    candidates, clusters, rewrite_targets, manifest = select_research_candidates(
        leaderboard_rows,
        universe_summary=universe_summary,
        portfolio_universe_summary=portfolio_universe_summary,
        failure_memory=failure_memory,
        failure_clusters=failure_clusters,
        policy=policy,
    )
    safe_write_csv(out / "candidate_selector.csv", candidates, out / "events.jsonl")
    safe_write_csv(out / "multi_asset_failure_clusters.csv", clusters, out / "events.jsonl")
    safe_write_csv(out / "rewrite_targets.csv", rewrite_targets, out / "events.jsonl")
    safe_write_json(out / "candidate_selector_manifest.json", manifest, out / "events.jsonl")
    safe_write_text(
        out / "CANDIDATE_SELECTOR_REPORT.md",
        render_candidate_selector_report(manifest, candidates, clusters, rewrite_targets),
        out / "events.jsonl",
    )
    return manifest


def load_json_rows(path: str | Path) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Expected JSON list: {path}")
    return [item for item in payload if isinstance(item, dict) and item.get("formula")]


def load_optional_csv(path: str | Path | None) -> pd.DataFrame | None:
    if not path:
        return None
    return pd.read_csv(path)


def load_candidate_selector_prompt_context(
    path: str | Path | None,
    *,
    max_rewrite_targets: int = 5,
    max_evidence_gaps: int = 5,
    max_clusters: int = 5,
) -> dict[str, Any]:
    if not path:
        return {"available": False, "rewrite_targets": [], "evidence_gaps": [], "clusters": []}
    root = Path(path)
    if root.is_dir():
        candidate_path = root / "candidate_selector.csv"
        rewrite_path = root / "rewrite_targets.csv"
        cluster_path = root / "multi_asset_failure_clusters.csv"
    else:
        candidate_path = root
        rewrite_path = root.with_name("rewrite_targets.csv")
        cluster_path = root.with_name("multi_asset_failure_clusters.csv")

    rewrite_targets = _load_selector_rows(rewrite_path, max_rows=max_rewrite_targets)
    if not rewrite_targets:
        rewrite_targets = _load_selector_rows(
            candidate_path,
            max_rows=max_rewrite_targets,
            verdicts={"rewrite", "deprioritize"},
        )
    evidence_gaps = _load_selector_rows(candidate_path, max_rows=max_evidence_gaps, verdicts={"needs_evidence"})
    clusters = _load_selector_clusters(cluster_path, max_rows=max_clusters)
    return {
        "available": bool(rewrite_targets or evidence_gaps or clusters),
        "source": root.as_posix(),
        "rewrite_targets": rewrite_targets,
        "evidence_gaps": evidence_gaps,
        "clusters": clusters,
    }


def render_candidate_selector_report(
    manifest: dict[str, Any],
    candidates: pd.DataFrame,
    clusters: pd.DataFrame,
    rewrite_targets: pd.DataFrame,
) -> str:
    lines = [
        "# QuantumRandy Research Candidate Selector",
        "",
        "This is a research evidence artifact only. It is not a runtime publish payload and does not admit factors.",
        "",
        "## Summary",
        "",
        f"- Input factors: `{manifest['input_count']}`",
        f"- Evaluated candidates: `{manifest['candidate_count']}`",
        f"- Rewrite targets: `{manifest['rewrite_target_count']}`",
        f"- Multi-asset failure clusters: `{manifest['cluster_count']}`",
        "",
        "## Verdict Counts",
        "",
        "| Verdict | Count |",
        "|---|---:|",
    ]
    counts = manifest.get("verdict_counts", {})
    if counts:
        for verdict, count in counts.items():
            lines.append(f"| `{verdict}` | {count} |")
    else:
        lines.append("| none | 0 |")

    lines.extend(["", "## Top Rewrite Targets", ""])
    if rewrite_targets.empty:
        lines.append("No rewrite targets were selected.")
    else:
        lines.append(
            "| Rank | Factor | Score | Universe Pass Rate | Mean Sharpe | Failed Assets | Rewrite Focus | Formula |"
        )
        lines.append("|---:|---|---:|---:|---:|---|---|---|")
        for rank, row in enumerate(rewrite_targets.head(20).to_dict(orient="records"), start=1):
            lines.append(
                "| "
                f"{rank} | `{row['factor_id']}` | {row['selector_score']:.2f} | "
                f"{_num(row.get('universe_pass_rate')):.2f} | {_num(row.get('universe_mean_sharpe')):.2f} | "
                f"`{row['failed_assets']}` | `{row['rewrite_focus']}` | `{row['formula']}` |"
            )

    evidence_gaps = (
        candidates[candidates["selector_verdict"] == "needs_evidence"] if not candidates.empty else pd.DataFrame()
    )
    lines.extend(["", "## Evidence Gaps", ""])
    if evidence_gaps.empty:
        lines.append("No candidates are missing multi-asset evidence.")
    else:
        lines.append("| Factor | Leaderboard Passed | Leaderboard Score | Focus | Formula |")
        lines.append("|---|---:|---:|---|---|")
        for row in evidence_gaps.head(20).to_dict(orient="records"):
            lines.append(
                "| "
                f"`{row['factor_id']}` | `{row['leaderboard_passed']}` | {row['leaderboard_score']:.2f} | "
                f"`{row['rewrite_focus']}` | `{row['formula']}` |"
            )

    lines.extend(["", "## Multi-Asset Failure Clusters", ""])
    if clusters.empty:
        lines.append("No repeated multi-asset failure clusters were found.")
    else:
        lines.append("| Rank | Subtree | Count | Avg Pass Rate | Avg Mean Sharpe | Example Factors |")
        lines.append("|---:|---|---:|---:|---:|---|")
        for rank, row in enumerate(clusters.head(20).to_dict(orient="records"), start=1):
            lines.append(
                "| "
                f"{rank} | `{row['subtree']}` | {row['count']} | {row['avg_universe_pass_rate']:.2f} | "
                f"{row['avg_universe_mean_sharpe']:.2f} | `{row['example_factor_ids']}` |"
            )

    lines.extend(
        [
            "",
            "## Files",
            "",
            "- `candidate_selector.csv`: per-factor leaderboard, universe, portfolio-universe, and failure-memory "
            "evidence.",
            "- `multi_asset_failure_clusters.csv`: repeated subtrees associated with weak cross-asset evidence.",
            "- `rewrite_targets.csv`: ranked research-only candidates for targeted rewrite prompts.",
            "- `candidate_selector_manifest.json`: machine-readable policy, safety flags, and counts.",
            "- `CANDIDATE_SELECTOR_REPORT.md`: this report.",
        ]
    )
    return "\n".join(lines) + "\n"


def _candidate_row(
    row: dict[str, Any],
    factor_id: str,
    universe: dict[str, Any],
    portfolio: dict[str, Any],
    matched_failed_subtrees: list[tuple[str, int]],
    policy: CandidateSelectorPolicy,
) -> dict[str, Any]:
    universe_pass_rate = _num(universe.get("pass_rate"))
    universe_mean_sharpe = _num(universe.get("mean_sharpe"))
    universe_rank_ic = _num(universe.get("median_rank_ic"))
    portfolio_best_pass_rate = _num(portfolio.get("best_portfolio_universe_pass_rate"))
    leaderboard_score = _num(row.get("brutal_score", row.get("score", row.get("mcts_score"))))
    matched_text = "|".join(subtree for subtree, _ in matched_failed_subtrees)
    matched_count = sum(count for _, count in matched_failed_subtrees)
    failed_assets = str(universe.get("failed_assets", ""))
    has_universe_evidence = bool(universe)

    score = (
        35.0 * universe_pass_rate
        + 10.0 * max(universe_mean_sharpe, -2.0)
        + 250.0 * universe_rank_ic
        + 15.0 * portfolio_best_pass_rate
        + min(20.0, leaderboard_score / 5.0)
        - min(20.0, matched_count * 2.0)
    )
    verdict, focus = _verdict_and_focus(
        has_universe_evidence=has_universe_evidence,
        universe_pass_rate=universe_pass_rate,
        universe_mean_sharpe=universe_mean_sharpe,
        matched_failed_subtrees=matched_failed_subtrees,
        policy=policy,
    )
    return {
        "factor_id": factor_id,
        "formula": row.get("formula", ""),
        "description": row.get("description", ""),
        "selector_verdict": verdict,
        "rewrite_focus": focus,
        "selector_score": round(score, 4),
        "leaderboard_passed": _bool(row.get("passed")),
        "leaderboard_score": leaderboard_score,
        "validation_sharpe": _num(row.get("validation_sharpe", row.get("val_sharpe"))),
        "validation_rank_ic": _num(row.get("validation_rank_ic", row.get("val_rank_ic"))),
        "has_universe_evidence": has_universe_evidence,
        "universe_pass_rate": universe_pass_rate if universe else "",
        "universe_mean_sharpe": universe_mean_sharpe if universe else "",
        "universe_median_rank_ic": universe_rank_ic if universe else "",
        "universe_evaluated_assets": _num(universe.get("evaluated_assets")) if universe else "",
        "failed_assets": failed_assets,
        "portfolio_universe_best_portfolio": portfolio.get("best_portfolio_id", ""),
        "portfolio_universe_best_pass_rate": portfolio_best_pass_rate if portfolio else "",
        "portfolio_universe_best_mean_sharpe": (
            _num(portfolio.get("best_portfolio_universe_mean_sharpe")) if portfolio else ""
        ),
        "matched_failed_subtrees": matched_text,
        "matched_failed_subtree_count": matched_count,
        "hypothesis": row.get("hypothesis", ""),
        "expected_edge": row.get("expected_edge", ""),
        "expected_failure_mode": row.get("expected_failure_mode", ""),
        "rewrite_plan_if_killed": row.get("rewrite_plan_if_killed", ""),
    }


def _verdict_and_focus(
    *,
    has_universe_evidence: bool,
    universe_pass_rate: float,
    universe_mean_sharpe: float,
    matched_failed_subtrees: list[tuple[str, int]],
    policy: CandidateSelectorPolicy,
) -> tuple[str, str]:
    if not has_universe_evidence:
        return "needs_evidence", "run_universe_evaluation_first"
    if (
        universe_pass_rate < policy.min_rewrite_universe_pass_rate
        and universe_mean_sharpe < policy.min_keep_mean_sharpe
    ):
        return "deprioritize", "abandon_or_change_economic_family"
    if matched_failed_subtrees and universe_pass_rate <= policy.max_cluster_pass_rate:
        return "deprioritize", "avoid_repeated_failed_subtrees"
    if universe_pass_rate < policy.min_keep_universe_pass_rate:
        return "rewrite", "improve_cross_asset_robustness"
    if universe_mean_sharpe < policy.min_keep_mean_sharpe:
        return "rewrite", "improve_cross_asset_profitability"
    return "keep_for_review", "manual_review"


def _build_rewrite_targets(candidates: pd.DataFrame) -> pd.DataFrame:
    if candidates.empty:
        return pd.DataFrame()
    frame = candidates[candidates["selector_verdict"].isin(["rewrite", "deprioritize"])].copy()
    if frame.empty:
        return frame
    rewrite_priority = {"rewrite": 1, "deprioritize": 2}
    frame["rewrite_priority"] = frame["selector_verdict"].map(rewrite_priority).fillna(99)
    return frame.sort_values(
        ["rewrite_priority", "selector_score", "universe_pass_rate"],
        ascending=[True, False, False],
    ).reset_index(drop=True)


def _build_universe_failure_clusters(candidates: pd.DataFrame, policy: CandidateSelectorPolicy) -> pd.DataFrame:
    if candidates.empty:
        return pd.DataFrame()
    cluster_rows: dict[str, list[dict[str, Any]]] = {}
    weak = candidates[
        (
            candidates["has_universe_evidence"].astype(bool)
            & (
                (
                    pd.to_numeric(candidates["universe_pass_rate"], errors="coerce").fillna(0.0)
                    <= policy.max_cluster_pass_rate
                )
                | (
                    pd.to_numeric(candidates["universe_mean_sharpe"], errors="coerce").fillna(0.0)
                    < policy.min_keep_mean_sharpe
                )
            )
        )
    ]
    for row in weak.to_dict(orient="records"):
        for subtree in set(_safe_subtrees(str(row.get("formula", "")))):
            if "(" not in subtree:
                continue
            cluster_rows.setdefault(subtree, []).append(row)

    rows = []
    for subtree, items in cluster_rows.items():
        if len(items) < policy.min_cluster_size:
            continue
        rows.append(
            {
                "subtree": subtree,
                "count": len(items),
                "avg_universe_pass_rate": round(_mean([_num(item.get("universe_pass_rate")) for item in items]), 8),
                "avg_universe_mean_sharpe": round(_mean([_num(item.get("universe_mean_sharpe")) for item in items]), 8),
                "example_factor_ids": ",".join(str(item.get("factor_id", "")) for item in items[:5]),
                "example_formula": str(items[0].get("formula", "")),
                "failed_assets": "|".join(
                    str(item.get("failed_assets", "")) for item in items[:5] if item.get("failed_assets")
                ),
            }
        )
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    return frame.sort_values(
        ["count", "avg_universe_pass_rate", "avg_universe_mean_sharpe"],
        ascending=[False, True, True],
    ).reset_index(drop=True)


def _portfolio_evidence_by_factor(frame: pd.DataFrame | None) -> dict[str, dict[str, Any]]:
    if frame is None or frame.empty or "weights" not in frame.columns:
        return {}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in frame.to_dict(orient="records"):
        for factor_id in _parse_weight_factor_ids(row.get("weights")):
            grouped.setdefault(factor_id, []).append(row)
    out = {}
    for factor_id, rows in grouped.items():
        best = max(
            rows,
            key=lambda row: (
                _num(row.get("pass_rate")),
                _num(row.get("mean_sharpe")),
                _num(row.get("robustness_score")),
            ),
        )
        out[factor_id] = {
            "best_portfolio_id": best.get("portfolio_id", ""),
            "best_portfolio_universe_pass_rate": _num(best.get("pass_rate")),
            "best_portfolio_universe_mean_sharpe": _num(best.get("mean_sharpe")),
            "best_portfolio_universe_score": _num(best.get("robustness_score")),
        }
    return out


def _failed_subtree_counts(
    failure_memory: pd.DataFrame | None,
    failure_clusters: pd.DataFrame | None,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    if failure_clusters is not None and not failure_clusters.empty:
        for row in failure_clusters.to_dict(orient="records"):
            subtree = str(row.get("subtree", ""))
            if subtree:
                counts[subtree] = max(counts.get(subtree, 0), int(_num(row.get("count")) or 1))
    if failure_memory is not None and not failure_memory.empty and "subtree_fingerprints" in failure_memory.columns:
        for raw in failure_memory["subtree_fingerprints"].fillna(""):
            for subtree in str(raw).split("|"):
                if subtree:
                    counts[subtree] = counts.get(subtree, 0) + 1
    return counts


def _matched_failed_subtrees(formula: str, failed_subtrees: dict[str, int]) -> list[tuple[str, int]]:
    if not failed_subtrees:
        return []
    tree = set(_safe_subtrees(formula))
    hits = [(subtree, count) for subtree, count in failed_subtrees.items() if subtree in tree]
    return sorted(hits, key=lambda item: item[1], reverse=True)[:10]


def _safe_subtrees(formula: str) -> list[str]:
    try:
        return subtrees(formula)
    except Exception:
        return []


def _index_records(frame: pd.DataFrame | None, key: str) -> dict[str, dict[str, Any]]:
    if frame is None or frame.empty or key not in frame.columns:
        return {}
    return {str(row.get(key, "")): row for row in frame.to_dict(orient="records") if row.get(key) not in (None, "")}


def _load_selector_rows(
    path: Path,
    *,
    max_rows: int,
    verdicts: set[str] | None = None,
) -> list[dict[str, str]]:
    if max_rows <= 0 or not path.exists():
        return []
    try:
        frame = pd.read_csv(path).fillna("")
    except pd.errors.EmptyDataError:
        return []
    if verdicts and "selector_verdict" in frame.columns:
        frame = frame[frame["selector_verdict"].astype(str).isin(verdicts)]
    if "rewrite_priority" in frame.columns:
        frame = frame.sort_values(["rewrite_priority", "selector_score"], ascending=[True, False])
    elif "selector_score" in frame.columns:
        frame = frame.sort_values("selector_score", ascending=False)
    rows = []
    for row in frame.head(max_rows).to_dict(orient="records"):
        rows.append(
            {
                "factor_id": str(row.get("factor_id", "")),
                "formula": str(row.get("formula", "")),
                "selector_verdict": str(row.get("selector_verdict", "")),
                "rewrite_focus": str(row.get("rewrite_focus", "")),
                "universe_pass_rate": str(row.get("universe_pass_rate", "")),
                "universe_mean_sharpe": str(row.get("universe_mean_sharpe", "")),
                "failed_assets": str(row.get("failed_assets", "")),
                "matched_failed_subtrees": str(row.get("matched_failed_subtrees", "")),
            }
        )
    return rows


def _load_selector_clusters(path: Path, *, max_rows: int) -> list[dict[str, str]]:
    if max_rows <= 0 or not path.exists():
        return []
    try:
        frame = pd.read_csv(path).fillna("")
    except pd.errors.EmptyDataError:
        return []
    rows = []
    for row in frame.head(max_rows).to_dict(orient="records"):
        rows.append(
            {
                "subtree": str(row.get("subtree", "")),
                "count": str(row.get("count", "")),
                "avg_universe_pass_rate": str(row.get("avg_universe_pass_rate", "")),
                "avg_universe_mean_sharpe": str(row.get("avg_universe_mean_sharpe", "")),
                "example_factor_ids": str(row.get("example_factor_ids", "")),
                "example_formula": str(row.get("example_formula", "")),
            }
        )
    return rows


def _factor_id(row: dict[str, Any], formula: str, index: int) -> str:
    if row.get("factor_id"):
        return str(row["factor_id"])
    if formula:
        return stable_factor_id(formula)
    return f"factor_{index:03d}"


def _parse_weight_factor_ids(value: Any) -> list[str]:
    ids: list[str] = []
    for part in str(value or "").split(","):
        factor_id = part.split(":", 1)[0].strip()
        if factor_id:
            ids.append(factor_id)
    return ids


def _value_counts(frame: pd.DataFrame, column: str) -> dict[str, int]:
    if frame.empty or column not in frame.columns:
        return {}
    return {str(key): int(value) for key, value in frame[column].value_counts().to_dict().items()}


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(pd.Series(values, dtype=float).mean())


def _num(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if pd.notna(number) else 0.0


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes", "y"}
