from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import request

import pandas as pd

from .expression import parse_formula


@dataclass(frozen=True)
class PublishSelection:
    factors: list[dict[str, Any]]
    strategies: list[dict[str, Any]]
    selected_rows: list[dict[str, Any]]


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def select_runtime_factors(
    leaderboard: list[dict[str, Any]],
    *,
    max_factors: int = 5,
    include_unpassed: bool = False,
    min_brutal_score: float | None = None,
    exposure_threshold: float = 0.15,
    strategy_id: str = "published_equal_weight_blend",
    initial_capital_usd: float = 1000.0,
) -> PublishSelection:
    rows = []
    seen: set[str] = set()
    for row in sorted(leaderboard, key=_sort_key, reverse=True):
        formula = parse_formula(str(row.get("formula", ""))).canonical()
        if formula in seen:
            continue
        if not include_unpassed and row.get("passed") is not True:
            continue
        if min_brutal_score is not None and float(row.get("brutal_score", 0.0)) < min_brutal_score:
            continue
        seen.add(formula)
        item = dict(row)
        item["formula"] = formula
        rows.append(item)
        if len(rows) >= max_factors:
            break

    factors = [
        {
            "factor_id": factor_id_for_formula(row["formula"]),
            "formula": row["formula"],
            "description": str(row.get("description", "")).strip(),
            "enabled": True,
            "exposure_threshold": exposure_threshold,
        }
        for row in rows
    ]
    strategies = []
    if factors:
        strategies.append(
            {
                "strategy_id": strategy_id,
                "description": "Manual equal-weight blend published from validated QuantumRandy factors.",
                "initial_capital_usd": initial_capital_usd,
                "enabled": True,
                "components": [{"factor_id": item["factor_id"], "weight": 1.0} for item in factors],
                "execution_model": {
                    "latency_bars": 2,
                    "max_exposure_abs": 0.75,
                    "exposure_threshold": 0.20,
                    "base_slippage_bps": 1.5,
                    "slippage_jitter_bps": 3.0,
                    "adverse_slippage_bps": 5.0,
                    "signal_noise_std": 0.08,
                    "fill_probability": 0.95,
                    "seed": 101,
                },
            }
        )
    return PublishSelection(factors=factors, strategies=strategies, selected_rows=rows)


def build_update_payload(
    *,
    expected_generation: int,
    factors: list[dict[str, Any]],
    strategies: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "expected_generation": int(expected_generation),
        "factors": factors,
        "strategies": strategies,
    }


def current_generation_from_manifest(path: str | Path) -> int:
    manifest = load_json(path)
    return int(manifest.get("generation", 0))


def fetch_runtime_manifest(runtime_url: str, *, timeout: float = 10.0) -> dict[str, Any]:
    with request.urlopen(f"{runtime_url.rstrip('/')}/v1/factors", timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("Runtime manifest response was not a JSON object")
    return payload


def submit_runtime_config(
    runtime_url: str,
    admin_token: str,
    payload: dict[str, Any],
    *,
    timeout: float = 10.0,
) -> dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=True, allow_nan=False).encode("utf-8")
    req = request.Request(
        f"{runtime_url.rstrip('/')}/v1/admin/config",
        data=data,
        headers={
            "Content-Type": "application/json",
            "X-Admin-Token": admin_token,
        },
        method="PUT",
    )
    with request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def write_publish_artifacts(
    out_path: str | Path,
    payload: dict[str, Any],
    selected_rows: list[dict[str, Any]],
) -> Path:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=True, allow_nan=False) + "\n", encoding="utf-8")
    audit_path = out.with_name(out.stem + "_audit.md")
    audit_path.write_text(render_publish_audit(payload, selected_rows), encoding="utf-8")
    return audit_path


def render_publish_audit(payload: dict[str, Any], selected_rows: list[dict[str, Any]]) -> str:
    lines = [
        "# QuantumRandy Runtime Publish Audit",
        "",
        f"- Expected runtime generation: `{payload.get('expected_generation')}`",
        f"- Factors selected: `{len(payload.get('factors') or [])}`",
        f"- Strategies selected: `{len(payload.get('strategies') or [])}`",
        "",
        "## Selected Factors",
        "",
    ]
    if selected_rows:
        lines.extend(
            [
                "| Factor ID | Passed | Brutal Score | Sharpe | Rank IC | Formula |",
                "|---|---:|---:|---:|---:|---|",
            ]
        )
        id_by_formula = {item["formula"]: item["factor_id"] for item in payload.get("factors", [])}
        for row in selected_rows:
            formula = row.get("formula", "")
            lines.append(
                "| "
                f"{id_by_formula.get(formula, '-')} | "
                f"{row.get('passed')} | "
                f"{_fmt(row.get('brutal_score'))} | "
                f"{_fmt(row.get('sharpe'))} | "
                f"{_fmt(row.get('rank_ic'))} | "
                f"`{formula}` |"
            )
    else:
        lines.append("No factors selected.")
    lines.extend(["", "## Strategies", ""])
    for strategy in payload.get("strategies") or []:
        components = ", ".join(f"{item['factor_id']}:{item.get('weight', 1.0)}" for item in strategy.get("components", []))
        lines.append(f"- `{strategy.get('strategy_id')}`: {components}")
    return "\n".join(lines) + "\n"


def publish_from_files(
    *,
    leaderboard_path: str | Path,
    runtime_manifest_path: str | Path,
    out_path: str | Path,
    max_factors: int = 5,
    include_unpassed: bool = False,
    min_brutal_score: float | None = None,
    exposure_threshold: float = 0.15,
    strategy_id: str = "published_equal_weight_blend",
    initial_capital_usd: float = 1000.0,
) -> dict[str, Any]:
    leaderboard = load_json(leaderboard_path)
    if not isinstance(leaderboard, list):
        raise ValueError("leaderboard must be a JSON list")
    selection = select_runtime_factors(
        leaderboard,
        max_factors=max_factors,
        include_unpassed=include_unpassed,
        min_brutal_score=min_brutal_score,
        exposure_threshold=exposure_threshold,
        strategy_id=strategy_id,
        initial_capital_usd=initial_capital_usd,
    )
    payload = build_update_payload(
        expected_generation=current_generation_from_manifest(runtime_manifest_path),
        factors=selection.factors,
        strategies=selection.strategies,
    )
    audit_path = write_publish_artifacts(out_path, payload, selection.selected_rows)
    return {"payload": payload, "audit_path": str(audit_path), "selected_count": len(selection.selected_rows)}


def factor_id_for_formula(formula: str) -> str:
    digest = hashlib.sha1(formula.encode("utf-8")).hexdigest()[:10]
    return f"qr_{digest}"


def admin_token_from_env(env_name: str) -> str:
    token = os.environ.get(env_name, "")
    if not token:
        raise RuntimeError(f"Set non-empty {env_name} before submitting a runtime update")
    return token


def _sort_key(row: dict[str, Any]) -> tuple[float, float, float]:
    return (
        float(row.get("brutal_score", 0.0)),
        float(row.get("validation_sharpe", row.get("val_sharpe", 0.0))),
        float(row.get("rank_ic", row.get("train_rank_ic", 0.0))),
    )


def _fmt(value: Any) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return str(value)
