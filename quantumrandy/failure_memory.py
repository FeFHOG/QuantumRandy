from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

from .expression import subtrees
from .io_utils import safe_write_csv, safe_write_json, safe_write_text

GATE_KEYS = {
    "gate_predictive_power": "predictive_power",
    "gate_homogeneity": "homogeneity",
    "gate_friction_audit": "friction_audit",
    "gate_lifetime": "lifetime",
}


def build_failure_memory(
    rows: list[dict[str, Any]],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    failures = [_failure_row(row) for row in rows if _is_failed(row)]
    clusters = _cluster_rows(failures)
    manifest = {
        "artifact_type": "quantumrandy_failure_memory",
        "schema_version": 1,
        "safety": {
            "research_only": True,
            "not_runtime_publish_payload": True,
            "does_not_change_active_runtime": True,
        },
        "input_rows": len(rows),
        "failure_count": len(failures),
        "cluster_count": len(clusters),
        "usage": [
            "Use failed gates and schema-v2 proposal fields as negative examples for future LLM prompts.",
            "Use shared subtree clusters to avoid repeating structurally similar failed formulas.",
            "Do not auto-promote or auto-block runtime factors from this artifact without manual review.",
        ],
    }
    return pd.DataFrame(failures), pd.DataFrame(clusters), manifest


def write_failure_memory(
    rows: list[dict[str, Any]],
    out_dir: str | Path,
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    failures, clusters, manifest = build_failure_memory(rows)
    safe_write_csv(out / "failure_memory.csv", failures, out / "events.jsonl")
    safe_write_csv(out / "failure_clusters.csv", clusters, out / "events.jsonl")
    safe_write_json(out / "failure_memory_manifest.json", manifest, out / "events.jsonl")
    safe_write_text(out / "FAILURE_MEMORY_REPORT.md", render_failure_memory_report(manifest, failures, clusters), out / "events.jsonl")
    return manifest


def load_failure_prompt_context(
    path: str | Path | None,
    *,
    max_examples: int = 5,
    max_clusters: int = 5,
) -> dict[str, Any]:
    if not path:
        return {"available": False, "examples": [], "clusters": []}
    root = Path(path)
    if root.is_dir():
        memory_path = root / "failure_memory.csv"
        cluster_path = root / "failure_clusters.csv"
    else:
        memory_path = root
        cluster_path = root.with_name("failure_clusters.csv")

    examples = _load_failure_examples(memory_path, max_examples=max_examples)
    clusters = _load_failure_clusters(cluster_path, max_clusters=max_clusters)
    return {
        "available": bool(examples or clusters),
        "source": root.as_posix(),
        "examples": examples,
        "clusters": clusters,
    }


def render_failure_memory_report(
    manifest: dict[str, Any],
    failures: pd.DataFrame,
    clusters: pd.DataFrame,
) -> str:
    lines = [
        "# QuantumRandy Failure Memory Report",
        "",
        "This is a research artifact only. It is not a runtime publish payload.",
        "",
        "## Summary",
        "",
        f"- Input rows: `{manifest['input_rows']}`",
        f"- Failed formulas: `{manifest['failure_count']}`",
        f"- Failure clusters: `{manifest['cluster_count']}`",
        "",
        "## Failed Gates",
        "",
        "| Gate | Count |",
        "|---|---:|",
    ]
    gate_counter: Counter[str] = Counter()
    if not failures.empty:
        for value in failures["failed_gates"].fillna(""):
            gate_counter.update(gate for gate in str(value).split(",") if gate)
    if gate_counter:
        for gate, count in gate_counter.most_common():
            lines.append(f"| `{gate}` | {count} |")
    else:
        lines.append("| none | 0 |")

    lines.extend(["", "## Top Shared Failed Subtrees", ""])
    if clusters.empty:
        lines.append("No failure clusters found.")
    else:
        lines.append("| Rank | Subtree | Count | Gates | Example Formula |")
        lines.append("|---:|---|---:|---|---|")
        for rank, row in enumerate(clusters.head(20).to_dict(orient="records"), start=1):
            lines.append(
                f"| {rank} | `{row['subtree']}` | {row['count']} | `{row['failed_gates']}` | `{row['example_formula']}` |"
            )

    lines.extend(
        [
            "",
            "## Files",
            "",
            "- `failure_memory.csv`: failed formula rows with schema-v2 proposal context and subtree fingerprints.",
            "- `failure_clusters.csv`: repeated failed subtree patterns.",
            "- `failure_memory_manifest.json`: machine-readable artifact metadata.",
            "- `FAILURE_MEMORY_REPORT.md`: this report.",
        ]
    )
    return "\n".join(lines) + "\n"


def _load_failure_examples(path: Path, *, max_examples: int) -> list[dict[str, str]]:
    if max_examples <= 0 or not path.exists():
        return []
    frame = pd.read_csv(path).fillna("")
    rows = []
    for row in frame.head(max_examples).to_dict(orient="records"):
        rows.append(
            {
                "formula": str(row.get("formula", "")),
                "failed_gates": str(row.get("failed_gates", "")),
                "expected_failure_mode": str(row.get("expected_failure_mode", "")),
                "rewrite_plan_if_killed": str(row.get("rewrite_plan_if_killed", "")),
            }
        )
    return rows


def _load_failure_clusters(path: Path, *, max_clusters: int) -> list[dict[str, str]]:
    if max_clusters <= 0 or not path.exists():
        return []
    frame = pd.read_csv(path).fillna("")
    rows = []
    for row in frame.head(max_clusters).to_dict(orient="records"):
        rows.append(
            {
                "subtree": str(row.get("subtree", "")),
                "count": str(row.get("count", "")),
                "failed_gates": str(row.get("failed_gates", "")),
                "example_formula": str(row.get("example_formula", "")),
            }
        )
    return rows


def _is_failed(row: dict[str, Any]) -> bool:
    if row.get("passed") is False:
        return True
    if str(row.get("passed", "")).lower() == "false":
        return True
    return bool(_derive_failed_gates(row))


def _failure_row(row: dict[str, Any]) -> dict[str, Any]:
    formula = str(row.get("formula", ""))
    failed_gates = _derive_failed_gates(row)
    tree_items = _safe_subtrees(formula)
    return {
        "candidate_id": row.get("candidate_id", ""),
        "candidate_family": row.get("candidate_family", ""),
        "formula": formula,
        "description": row.get("description", ""),
        "hypothesis": row.get("hypothesis", ""),
        "expected_edge": row.get("expected_edge", ""),
        "expected_failure_mode": row.get("expected_failure_mode", ""),
        "rewrite_plan_if_killed": row.get("rewrite_plan_if_killed", ""),
        "intended_scope": row.get("intended_scope", ""),
        "out_of_scope_policy": row.get("out_of_scope_policy", ""),
        "conservative_verdict": row.get("conservative_verdict", ""),
        "failure_labels": row.get("failure_labels", ""),
        "source_review_dir": row.get("source_review_dir", ""),
        "failed_gates": ",".join(failed_gates),
        "subtree_fingerprints": "|".join(tree_items),
        "brutal_score": _numeric(row.get("brutal_score")),
        "mcts_score": _numeric(row.get("mcts_score", row.get("score"))),
        "rank_ic": _numeric(row.get("rank_ic", row.get("train_rank_ic"))),
        "sharpe": _numeric(row.get("sharpe", row.get("train_sharpe"))),
        "max_dd": _numeric(row.get("max_dd", row.get("train_max_dd"))),
        "turnover": _numeric(row.get("turnover", row.get("train_turnover"))),
        "validation_sharpe": _numeric(row.get("validation_sharpe", row.get("val_sharpe"))),
        "validation_rank_ic": _numeric(row.get("validation_rank_ic", row.get("val_rank_ic"))),
    }


def _cluster_rows(failures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    gates_by_subtree: dict[str, Counter[str]] = {}
    examples: dict[str, str] = {}
    for row in failures:
        formula = str(row["formula"])
        gates = [gate for gate in str(row.get("failed_gates", "")).split(",") if gate]
        for subtree in str(row.get("subtree_fingerprints", "")).split("|"):
            if not subtree or "(" not in subtree:
                continue
            counter[subtree] += 1
            gates_by_subtree.setdefault(subtree, Counter()).update(gates)
            examples.setdefault(subtree, formula)

    rows = []
    for subtree, count in counter.most_common():
        if count < 2:
            continue
        rows.append(
            {
                "subtree": subtree,
                "count": count,
                "failed_gates": ",".join(gate for gate, _ in gates_by_subtree[subtree].most_common()),
                "example_formula": examples[subtree],
            }
        )
    return rows


def _derive_failed_gates(row: dict[str, Any]) -> list[str]:
    raw = row.get("kill_reasons", [])
    if isinstance(raw, list):
        reasons = [str(item) for item in raw if item]
    elif isinstance(raw, str) and raw.strip():
        text = raw.strip()
        reasons = [item.strip().strip("'\"[]") for item in text.split(",") if item.strip()]
    else:
        reasons = []
    if reasons:
        return reasons
    return [label for key, label in GATE_KEYS.items() if row.get(key) is False or str(row.get(key, "")).lower() == "false"]


def _safe_subtrees(formula: str) -> list[str]:
    try:
        return subtrees(formula)
    except Exception:
        return []


def _numeric(value: Any) -> float | str:
    if value in (None, ""):
        return ""
    try:
        return round(float(value), 8)
    except (TypeError, ValueError):
        return ""
