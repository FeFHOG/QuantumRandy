from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .io_utils import safe_write_csv, safe_write_json, safe_write_text


@dataclass(frozen=True)
class AdmissionPolicy:
    min_brutal_score: float = 0.0
    require_brutal_pass: bool = True
    max_turnover: float = 0.60
    max_drawdown: float = 0.50
    min_validation_sharpe: float = 0.0
    min_validation_rank_ic: float = 0.0
    min_walk_forward_survival_rate: float = 0.50
    min_walk_forward_windows: int = 1
    min_universe_pass_rate: float = 0.50
    min_universe_assets: int = 1
    max_portfolio_corr: float = 0.70
    require_portfolio_selected: bool = False
    min_portfolio_walk_forward_survival_rate: float = 0.50
    min_portfolio_walk_forward_windows: int = 1


def evaluate_admission(
    leaderboard_rows: list[dict[str, Any]],
    *,
    walk_forward_summary: pd.DataFrame | None = None,
    universe_summary: pd.DataFrame | None = None,
    portfolio_selection: pd.DataFrame | None = None,
    portfolio_walk_forward_summary: pd.DataFrame | None = None,
    policy: AdmissionPolicy | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    policy = policy or AdmissionPolicy()
    wf_by_formula = _index_records(walk_forward_summary, "formula")
    universe_by_formula = _index_records(universe_summary, "formula")
    portfolio_by_factor = _index_records(portfolio_selection, "factor_id")
    portfolio_wf_by_factor = _index_portfolio_walk_forward(portfolio_walk_forward_summary)
    rows = []
    for idx, row in enumerate(leaderboard_rows, start=1):
        formula = str(row.get("formula", ""))
        factor_id = str(row.get("factor_id") or f"factor_{idx:03d}")
        wf = wf_by_formula.get(formula, {})
        uni = universe_by_formula.get(formula, {})
        port = portfolio_by_factor.get(factor_id, {})
        port_wf = portfolio_wf_by_factor.get(factor_id, {})
        decision = _decision_row(row, factor_id, wf, uni, port, port_wf, policy)
        rows.append(decision)
    frame = pd.DataFrame(rows)
    manifest = {
        "artifact_type": "quantumrandy_factor_admission",
        "schema_version": 1,
        "safety": {
            "research_only": True,
            "not_runtime_publish_payload": True,
            "requires_manual_review_before_runtime": True,
        },
        "policy": asdict(policy),
        "input_count": len(leaderboard_rows),
        "approved_count": int(frame["admission_pass"].sum()) if not frame.empty else 0,
        "review_count": int((frame["admission_status"] == "review").sum()) if not frame.empty else 0,
        "rejected_count": int((frame["admission_status"] == "reject").sum()) if not frame.empty else 0,
    }
    return frame, manifest


def write_admission_report(
    leaderboard_rows: list[dict[str, Any]],
    out_dir: str | Path,
    *,
    walk_forward_summary: pd.DataFrame | None = None,
    universe_summary: pd.DataFrame | None = None,
    portfolio_selection: pd.DataFrame | None = None,
    portfolio_walk_forward_summary: pd.DataFrame | None = None,
    policy: AdmissionPolicy | None = None,
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    decisions, manifest = evaluate_admission(
        leaderboard_rows,
        walk_forward_summary=walk_forward_summary,
        universe_summary=universe_summary,
        portfolio_selection=portfolio_selection,
        portfolio_walk_forward_summary=portfolio_walk_forward_summary,
        policy=policy,
    )
    safe_write_csv(out / "admission_decisions.csv", decisions, out / "events.jsonl")
    safe_write_json(out / "admission_manifest.json", manifest, out / "events.jsonl")
    safe_write_text(out / "ADMISSION_REPORT.md", render_admission_report(manifest, decisions), out / "events.jsonl")
    return manifest


def render_admission_report(manifest: dict[str, Any], decisions: pd.DataFrame) -> str:
    lines = [
        "# QuantumRandy Factor Admission Report",
        "",
        "This is a research governance artifact only. It is not a runtime publish payload.",
        "",
        "## Summary",
        "",
        f"- Input factors: `{manifest['input_count']}`",
        f"- Approved: `{manifest['approved_count']}`",
        f"- Review: `{manifest['review_count']}`",
        f"- Rejected: `{manifest['rejected_count']}`",
        "",
        "## Policy",
        "",
        "| Rule | Value |",
        "|---|---:|",
    ]
    for key, value in manifest["policy"].items():
        lines.append(f"| `{key}` | `{value}` |")

    lines.extend(["", "## Top Decisions", ""])
    if decisions.empty:
        lines.append("No factors evaluated.")
    else:
        lines.append("| Status | Score | Factor | Failed Rules | Formula |")
        lines.append("|---|---:|---|---|---|")
        for row in decisions.head(30).to_dict(orient="records"):
            lines.append(
                "| "
                f"`{row['admission_status']}` | {row['admission_score']:.2f} | `{row['factor_id']}` | "
                f"`{row['failed_rules']}` | `{row['formula']}` |"
            )

    lines.extend(
        [
            "",
            "## Files",
            "",
            "- `admission_decisions.csv`: per-factor gates, evidence, score, and decision.",
            "- `admission_manifest.json`: machine-readable policy and run summary.",
            "- `ADMISSION_REPORT.md`: this report.",
        ]
    )
    return "\n".join(lines) + "\n"


def load_json_rows(path: str | Path) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Expected JSON list: {path}")
    return [item for item in payload if isinstance(item, dict) and item.get("formula")]


def load_optional_csv(path: str | Path | None) -> pd.DataFrame | None:
    if not path:
        return None
    return pd.read_csv(path)


def _decision_row(
    row: dict[str, Any],
    factor_id: str,
    wf: dict[str, Any],
    uni: dict[str, Any],
    port: dict[str, Any],
    port_wf: dict[str, Any],
    policy: AdmissionPolicy,
) -> dict[str, Any]:
    checks = {
        "brutal_pass": (not policy.require_brutal_pass) or _bool(row.get("passed")),
        "brutal_score": _num(row.get("brutal_score", row.get("score"))) >= policy.min_brutal_score,
        "turnover": _num(row.get("turnover", row.get("train_turnover"))) <= policy.max_turnover,
        "drawdown": _num(row.get("max_dd", row.get("train_max_dd"))) <= policy.max_drawdown,
        "validation_sharpe": _num(row.get("validation_sharpe", row.get("val_sharpe"))) >= policy.min_validation_sharpe,
        "validation_rank_ic": _num(row.get("validation_rank_ic", row.get("val_rank_ic"))) >= policy.min_validation_rank_ic,
    }
    if wf:
        checks["walk_forward_survival"] = (
            _num(wf.get("survival_rate")) >= policy.min_walk_forward_survival_rate
            and _num(wf.get("windows")) >= policy.min_walk_forward_windows
        )
    if uni:
        checks["universe_robustness"] = (
            _num(uni.get("pass_rate")) >= policy.min_universe_pass_rate
            and _num(uni.get("evaluated_assets")) >= policy.min_universe_assets
        )
    if port:
        checks["portfolio_corr"] = _num(port.get("max_abs_corr_to_selected")) <= policy.max_portfolio_corr
        if policy.require_portfolio_selected:
            checks["portfolio_selected"] = _bool(port.get("selected"))
    if port_wf:
        checks["portfolio_walk_forward_survival"] = (
            _num(port_wf.get("best_survival_rate")) >= policy.min_portfolio_walk_forward_survival_rate
            and _num(port_wf.get("best_windows")) >= policy.min_portfolio_walk_forward_windows
        )

    failed = [name for name, passed in checks.items() if not passed]
    evidence_count = 6 + int(bool(wf)) + int(bool(uni)) + int(bool(port)) + int(bool(port_wf))
    pass_count = sum(1 for passed in checks.values() if passed)
    score = round(100.0 * pass_count / max(len(checks), 1), 4)
    status = "approve" if not failed else "review" if score >= 70.0 and evidence_count >= 6 else "reject"
    return {
        "factor_id": factor_id,
        "formula": row.get("formula", ""),
        "description": row.get("description", ""),
        "admission_status": status,
        "admission_pass": status == "approve",
        "admission_score": score,
        "failed_rules": ",".join(failed),
        "evidence_count": evidence_count,
        "brutal_passed": _bool(row.get("passed")),
        "brutal_score": _num(row.get("brutal_score", row.get("score"))),
        "turnover": _num(row.get("turnover", row.get("train_turnover"))),
        "max_dd": _num(row.get("max_dd", row.get("train_max_dd"))),
        "validation_sharpe": _num(row.get("validation_sharpe", row.get("val_sharpe"))),
        "validation_rank_ic": _num(row.get("validation_rank_ic", row.get("val_rank_ic"))),
        "walk_forward_survival_rate": _num(wf.get("survival_rate")) if wf else "",
        "walk_forward_windows": _num(wf.get("windows")) if wf else "",
        "universe_pass_rate": _num(uni.get("pass_rate")) if uni else "",
        "universe_assets": _num(uni.get("evaluated_assets")) if uni else "",
        "portfolio_selected": _bool(port.get("selected")) if port else "",
        "portfolio_max_corr": _num(port.get("max_abs_corr_to_selected")) if port else "",
        "portfolio_walk_forward_portfolios": port_wf.get("portfolio_ids", "") if port_wf else "",
        "portfolio_walk_forward_best_survival_rate": _num(port_wf.get("best_survival_rate")) if port_wf else "",
        "portfolio_walk_forward_best_windows": _num(port_wf.get("best_windows")) if port_wf else "",
        "portfolio_walk_forward_best_test_sharpe_median": (
            _num(port_wf.get("best_test_sharpe_median")) if port_wf else ""
        ),
        **{f"rule_{name}": passed for name, passed in checks.items()},
    }


def _index_records(frame: pd.DataFrame | None, key: str) -> dict[str, dict[str, Any]]:
    if frame is None or frame.empty or key not in frame.columns:
        return {}
    return {str(row.get(key, "")): row for row in frame.to_dict(orient="records")}


def _index_portfolio_walk_forward(frame: pd.DataFrame | None) -> dict[str, dict[str, Any]]:
    if frame is None or frame.empty or "weights" not in frame.columns:
        return {}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in frame.to_dict(orient="records"):
        for factor_id in _parse_weight_factor_ids(row.get("weights")):
            grouped.setdefault(factor_id, []).append(row)
    return {factor_id: _summarize_portfolio_walk_forward(rows) for factor_id, rows in grouped.items()}


def _parse_weight_factor_ids(value: Any) -> list[str]:
    ids: list[str] = []
    for part in str(value or "").split(","):
        factor_id = part.split(":", 1)[0].strip()
        if factor_id:
            ids.append(factor_id)
    return ids


def _summarize_portfolio_walk_forward(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def sort_key(row: dict[str, Any]) -> tuple[float, float, float]:
        return (
            _num(row.get("survival_rate")),
            _num(row.get("test_sharpe_median")),
            _num(row.get("test_rank_ic_median")),
        )

    best = max(rows, key=sort_key)
    return {
        "portfolio_ids": ",".join(str(row.get("portfolio_id", "")) for row in rows if row.get("portfolio_id")),
        "best_portfolio_id": best.get("portfolio_id", ""),
        "best_survival_rate": _num(best.get("survival_rate")),
        "best_windows": _num(best.get("windows")),
        "best_test_sharpe_median": _num(best.get("test_sharpe_median")),
        "best_test_rank_ic_median": _num(best.get("test_rank_ic_median")),
    }


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
