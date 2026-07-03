from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from .io_utils import safe_write_csv, safe_write_json, safe_write_text

V09D_SCOPE = "BTCUSDT_4h"
V09D_OUT_OF_SCOPE_POLICY = "diagnostic_only"
V09D_APPLICABILITY_HYPOTHESIS = (
    "BTCUSDT 4h scoped strict candidate-family discovery using only current point-in-time OHLCV and funding fields."
)
V09D_EXPECTED_FAILURE_MODE = (
    "v0.9d candidates may fail through low strict-grid Sharpe, validation or blind weakness, drawdown fragility, "
    "ETH diagnostic weakness, or bundle component redundancy."
)

V09D_SINGLE_FACTOR_CANDIDATES = [
    {
        "candidate_id": "qr_v09d_trend_efficiency_001",
        "formula_family": "trend_quality_efficiency",
        "formula": "zscore(div(ret(close,24),div(sub(max(high,48),min(low,48)),close)),96)",
        "hypothesis": "BTC directional moves that earn return per recent high-low range may persist better than raw trend.",
        "expected_failure_mode": "Trend-efficiency can fail when range compression precedes violent reversals or gaps.",
    },
    {
        "candidate_id": "qr_v09d_trend_persistence_001",
        "formula_family": "trend_persistence_alignment",
        "formula": "zscore(corr(ret(close,6),ret(close,24),48),96)",
        "hypothesis": "Alignment between short and medium returns may distinguish persistent direction from noisy reversals.",
        "expected_failure_mode": "Trend persistence can fail when short returns lag a fast regime transition.",
    },
    {
        "candidate_id": "qr_v09d_intrabar_conviction_001",
        "formula_family": "intrabar_conviction",
        "formula": "zscore(div(sub(close,open),sub(high,low)),72)",
        "hypothesis": "Closing location inside the 4h bar may encode participation-backed directional conviction.",
        "expected_failure_mode": "Intrabar conviction can fail in whipsaw bars with narrow ranges or stale opens.",
    },
    {
        "candidate_id": "qr_v09d_range_position_001",
        "formula_family": "range_position_trend",
        "formula": "zscore(div(sub(close,sma(close,48)),sub(max(high,48),min(low,48))),96)",
        "hypothesis": "Price location inside a rolling range may capture trend state without raw breakout chasing.",
        "expected_failure_mode": "Range position can fail when recent high-low bounds compress before expansion.",
    },
    {
        "candidate_id": "qr_v09d_rsi_state_change_001",
        "formula_family": "rsi_state_change",
        "formula": "zscore(delta(rsi(close,24),12),72)",
        "hypothesis": "Changes in RSI state may identify improving or deteriorating directional pressure.",
        "expected_failure_mode": "RSI state changes can lag crashes or overreact to temporary rebounds.",
    },
    {
        "candidate_id": "qr_v09d_liquidity_adjusted_momentum_001",
        "formula_family": "liquidity_adjusted_momentum",
        "formula": "zscore(div(ret(close,24),div(volume,sma(volume,96))),120)",
        "hypothesis": "Momentum adjusted for relative volume may avoid participation-only and raw-return traps.",
        "expected_failure_mode": "Liquidity-adjusted momentum can fail when volume expansion confirms trend rather than diluting it.",
    },
    {
        "candidate_id": "qr_v09d_vol_adjusted_trend_001",
        "formula_family": "volatility_adjusted_trend",
        "formula": "zscore(div(sub(ema(close,24),ema(close,96)),std(close,48)),120)",
        "hypothesis": "EMA trend scaled by realized volatility may reduce raw trend drawdown.",
        "expected_failure_mode": "Volatility-adjusted trend can fail when realized volatility rises after signal formation.",
    },
    {
        "candidate_id": "qr_v09d_funding_return_long_001",
        "formula_family": "funding_return_long_horizon",
        "formula": "zscore(corr(funding_rate,ret(close,42),120),72)",
        "hypothesis": "Long-horizon funding/return alignment may diagnose positioning pressure without direct funding mean reversion.",
        "expected_failure_mode": "Funding-return alignment can fail when positioning pressure persists through directional trends.",
    },
    {
        "candidate_id": "qr_v09d_volume_conviction_001",
        "formula_family": "volume_price_conviction",
        "formula": "zscore(corr(sub(close,open),volume,48),72)",
        "hypothesis": "Correlation between intrabar price change and volume may capture participation-backed direction.",
        "expected_failure_mode": "Volume conviction can fail when high-volume bars are liquidation or news reversals.",
    },
]

V09D_BUNDLE_CANDIDATES = [
    {
        "candidate_id": "qr_v09d_bundle_trend_quality_001",
        "formula_family": "scoped_equal_weight_bundle",
        "component_candidate_ids": [
            "qr_v09d_trend_efficiency_001",
            "qr_v09d_trend_persistence_001",
            "qr_v09d_intrabar_conviction_001",
        ],
        "hypothesis": "Trend efficiency, persistence, and intrabar conviction may identify higher-quality BTC trend states.",
    },
    {
        "candidate_id": "qr_v09d_bundle_liquidity_direction_001",
        "formula_family": "scoped_equal_weight_bundle",
        "component_candidate_ids": [
            "qr_v09d_volume_conviction_001",
            "qr_v09d_liquidity_adjusted_momentum_001",
            "qr_v09d_vol_adjusted_trend_001",
        ],
        "hypothesis": "Volume conviction, liquidity-adjusted momentum, and volatility-adjusted trend may separate direction from noisy participation.",
    },
    {
        "candidate_id": "qr_v09d_bundle_funding_confirmation_001",
        "formula_family": "scoped_equal_weight_bundle",
        "component_candidate_ids": [
            "qr_v09d_funding_return_long_001",
            "qr_v09d_trend_efficiency_001",
            "qr_v09d_intrabar_conviction_001",
        ],
        "hypothesis": "Funding-return alignment may confirm trend-quality and intrabar-conviction states without direct funding mean reversion.",
    },
]


def export_v0_9d_strict_candidate_discovery(
    out_dir: str | Path,
    *,
    intended_scope: str = V09D_SCOPE,
    applicability_hypothesis: str = V09D_APPLICABILITY_HYPOTHESIS,
    out_of_scope_policy: str = V09D_OUT_OF_SCOPE_POLICY,
    randyslab_eval_profile: str = "strict4h_v1",
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    single_records = _single_records(
        intended_scope=intended_scope,
        applicability_hypothesis=applicability_hypothesis,
        out_of_scope_policy=out_of_scope_policy,
        randyslab_eval_profile=randyslab_eval_profile,
    )
    bundle_records = _bundle_records(
        single_records,
        intended_scope=intended_scope,
        applicability_hypothesis=applicability_hypothesis,
        out_of_scope_policy=out_of_scope_policy,
        randyslab_eval_profile=randyslab_eval_profile,
    )
    records = single_records + bundle_records

    jsonl_path = out / "factor_candidates.jsonl"
    bundle_jsonl_path = out / "bundle_candidates.jsonl"
    csv_path = out / "factor_candidates.csv"
    manifest_path = out / "factor_candidate_export_manifest.json"
    report_path = out / "FACTOR_CANDIDATE_EXPORT.md"
    events_path = out / "events.jsonl"

    safe_write_text(jsonl_path, _jsonl(records), events_path)
    safe_write_text(bundle_jsonl_path, _jsonl(bundle_records), events_path)
    safe_write_csv(csv_path, _csv_frame(records), events_path)
    manifest = {
        "artifact_type": "quantumrandy_factor_candidate_export_manifest",
        "schema_version": 1,
        "research_checkpoint": "v0.9d",
        "candidate_family": "strict_candidate_family_discovery",
        "candidate_count": len(records),
        "single_factor_count": len(single_records),
        "bundle_count": len(bundle_records),
        "safety": _safety(),
        "scope_contract": {
            "intended_scope": intended_scope,
            "applicability_hypothesis": applicability_hypothesis,
            "out_of_scope_policy": out_of_scope_policy,
        },
        "future_portfolio_interface": _portfolio_contract(),
        "source": {
            "research_checkpoint": "v0.9d",
            "created_from_report": "docs/superpowers/specs/2026-07-03-research-v0-9d-design.md",
        },
        "outputs": {
            "jsonl": jsonl_path.as_posix(),
            "bundle_jsonl": bundle_jsonl_path.as_posix(),
            "csv": csv_path.as_posix(),
            "markdown": report_path.as_posix(),
            "manifest": manifest_path.as_posix(),
        },
    }
    safe_write_json(manifest_path, manifest, events_path)
    safe_write_text(report_path, render_v0_9d_export_report(manifest, records), events_path)
    return manifest


def render_v0_9d_export_report(manifest: dict[str, Any], records: list[dict[str, Any]]) -> str:
    lines = [
        "# QuantumRandy Research v0.9d Strict Candidate-Family Discovery Export",
        "",
        "This is a research-only factor and bundle export. It is not a runtime publish payload, admission decision,",
        "portfolio construction step, or live execution plan.",
        "",
        "## Summary",
        "",
        f"- Candidate rows: `{manifest['candidate_count']}`",
        f"- Single factors: `{manifest['single_factor_count']}`",
        f"- Bundles: `{manifest['bundle_count']}`",
        f"- Intended scope: `{manifest['scope_contract']['intended_scope']}`",
        f"- Out-of-scope policy: `{manifest['scope_contract']['out_of_scope_policy']}`",
        "",
        "## Candidates",
        "",
        "| Candidate | Family | Components | Formula |",
        "|---|---|---:|---|",
    ]
    for record in records:
        lines.append(
            "| `{candidate_id}` | `{formula_family}` | {component_count} | `{formula}` |".format(
                candidate_id=record["candidate_id"],
                formula_family=record["formula_family"],
                component_count=len(record.get("component_formulas") or []),
                formula=record["formula"],
            )
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- v0.9d uses only current DSL fields: open, high, low, close, volume, funding_rate.",
            "- Bundle candidates are equal-weight research signals, not portfolio weights.",
            "- No RandyPortfolio implementation, no runtime publishing, and no live execution.",
        ]
    )
    return "\n".join(lines) + "\n"


def _single_records(**scope: str) -> list[dict[str, Any]]:
    return [
        _record({**item, "component_formulas": [], "component_candidate_ids": []}, **scope)
        for item in V09D_SINGLE_FACTOR_CANDIDATES
    ]


def _bundle_records(single_records: list[dict[str, Any]], **scope: str) -> list[dict[str, Any]]:
    by_id = {record["candidate_id"]: record for record in single_records}
    records = []
    for item in V09D_BUNDLE_CANDIDATES:
        component_formulas = [by_id[candidate_id]["formula"] for candidate_id in item["component_candidate_ids"]]
        bundle = {
            **item,
            "formula": f"equal_weight_mean({','.join(component_formulas)})",
            "component_formulas": component_formulas,
            "expected_failure_mode": V09D_EXPECTED_FAILURE_MODE,
        }
        records.append(_record(bundle, **scope))
    return records


def _record(
    item: dict[str, Any],
    *,
    intended_scope: str,
    applicability_hypothesis: str,
    out_of_scope_policy: str,
    randyslab_eval_profile: str,
) -> dict[str, Any]:
    return {
        "artifact_type": "quantumrandy_factor_candidate_export",
        "schema_version": 1,
        "research_checkpoint": "v0.9d",
        "research_only": True,
        "not_runtime_publish_payload": True,
        "candidate_id": item["candidate_id"],
        "formula": item["formula"],
        "formula_family": item["formula_family"],
        "component_formulas": list(item.get("component_formulas") or []),
        "component_candidate_ids": list(item.get("component_candidate_ids") or []),
        "combination_method": "equal_weight_mean" if item.get("component_formulas") else "",
        "intended_scope": intended_scope,
        "applicability_hypothesis": applicability_hypothesis,
        "out_of_scope_policy": out_of_scope_policy,
        "hypothesis": item["hypothesis"],
        "expected_failure_mode": item.get("expected_failure_mode", V09D_EXPECTED_FAILURE_MODE),
        "portfolio_interface_contract": _portfolio_contract(),
        "required_features": _required_features([item["formula"], *list(item.get("component_formulas") or [])]),
        "candidate_tier": "exploratory_bundle" if item.get("component_formulas") else "exploratory",
        "randyslab_eval_profile": randyslab_eval_profile,
    }


def _jsonl(records: list[dict[str, Any]]) -> str:
    return "".join(json.dumps(record, ensure_ascii=True) + "\n" for record in records)


def _csv_frame(records: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for record in records:
        row = dict(record)
        row["component_formulas"] = json.dumps(record.get("component_formulas", []), ensure_ascii=True)
        row["component_candidate_ids"] = json.dumps(record.get("component_candidate_ids", []), ensure_ascii=True)
        row["portfolio_interface_contract"] = json.dumps(record.get("portfolio_interface_contract", {}), ensure_ascii=True)
        row["required_features"] = json.dumps(record.get("required_features", []), ensure_ascii=True)
        rows.append(row)
    return pd.DataFrame(rows)


def _required_features(formulas: list[str]) -> list[str]:
    fields = ["open", "high", "low", "close", "volume", "funding_rate"]
    return [field for field in fields if any(re.search(rf"\b{re.escape(field)}\b", formula) for formula in formulas)]


def _safety() -> dict[str, bool]:
    return {
        "research_only": True,
        "not_runtime_publish_payload": True,
        "does_not_update_runtime": True,
        "does_not_auto_admit_factors": True,
        "no_live_execution": True,
        "does_not_create_portfolio_scheduler": True,
    }


def _portfolio_contract() -> dict[str, str]:
    return {
        "consumer_project": "RandyPortfolio",
        "status": "interface_only_not_implemented",
        "allowed_use": "research_artifact_input",
        "forbidden_use": "runtime_allocation_or_live_execution",
    }
