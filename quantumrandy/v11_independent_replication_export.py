from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from .io_utils import safe_write_csv, safe_write_json, safe_write_text

V11_SCOPE = "BTCUSDT_4h"
V11_OUT_OF_SCOPE_POLICY = "diagnostic_only"
V11_APPLICABILITY_HYPOTHESIS = (
    "BTCUSDT 4h independent scoped family replication using non-funding current-DSL factors."
)
V11_EXPECTED_FAILURE_MODE = (
    "v1.1 independent candidates may fail through weak validation or blind windows, cost/funding stress fragility, "
    "crash-period drawdown, BTC scope weakness, or evidence concentrated in out-of-scope assets."
)
V11_EXCLUDED_RESEARCH10_SURVIVOR = {
    "candidate_id": "qr_v09d_funding_return_long_001",
    "variant_id": "thr_0p0_long_short_cap_0p5_none",
    "formula_family": "funding_return_long_horizon",
}

V11_SINGLE_FACTOR_CANDIDATES = [
    {
        "candidate_id": "qr_v11_volume_conviction_001",
        "formula_family": "volume_price_conviction",
        "formula": "zscore(corr(sub(close,open),volume,48),72)",
        "hypothesis": "Correlation between intrabar price change and volume may capture participation-backed BTC direction.",
        "expected_failure_mode": "Volume conviction can fail when high-volume bars are liquidation or news reversals.",
    },
    {
        "candidate_id": "qr_v11_volume_conviction_slow_001",
        "formula_family": "volume_price_conviction",
        "formula": "zscore(corr(sub(close,open),volume,72),120)",
        "hypothesis": "A slower price-volume conviction window may reduce one-off high-volume reversal noise.",
        "expected_failure_mode": "Slower volume conviction can lag fast crash transitions or overfit calm ranges.",
    },
    {
        "candidate_id": "qr_v11_range_position_001",
        "formula_family": "range_position_trend",
        "formula": "zscore(div(sub(close,sma(close,48)),sub(max(high,48),min(low,48))),96)",
        "hypothesis": "Price location inside a rolling range may capture trend state without raw breakout chasing.",
        "expected_failure_mode": "Range position can fail when recent high-low bounds compress before expansion.",
    },
    {
        "candidate_id": "qr_v11_trend_efficiency_001",
        "formula_family": "trend_quality_efficiency",
        "formula": "zscore(div(ret(close,24),div(sub(max(high,48),min(low,48)),close)),96)",
        "hypothesis": "BTC directional moves that earn return per recent high-low range may persist better than raw trend.",
        "expected_failure_mode": "Trend efficiency can fail when range compression precedes violent reversals or gaps.",
    },
    {
        "candidate_id": "qr_v11_trend_persistence_001",
        "formula_family": "trend_persistence_alignment",
        "formula": "zscore(corr(ret(close,6),ret(close,24),48),96)",
        "hypothesis": "Alignment between short and medium returns may distinguish persistent direction from noisy reversals.",
        "expected_failure_mode": "Trend persistence can fail when short returns lag a fast regime transition.",
    },
    {
        "candidate_id": "qr_v11_intrabar_conviction_001",
        "formula_family": "intrabar_conviction",
        "formula": "zscore(div(sub(close,open),sub(high,low)),72)",
        "hypothesis": "Closing location inside the 4h bar may encode participation-backed directional conviction.",
        "expected_failure_mode": "Intrabar conviction can fail in whipsaw bars with narrow ranges or stale opens.",
    },
    {
        "candidate_id": "qr_v11_liquidity_adjusted_momentum_001",
        "formula_family": "liquidity_adjusted_momentum",
        "formula": "zscore(div(ret(close,24),div(volume,sma(volume,96))),120)",
        "hypothesis": "Momentum adjusted for relative volume may avoid participation-only and raw-return traps.",
        "expected_failure_mode": "Liquidity-adjusted momentum can fail when volume expansion confirms trend rather than diluting it.",
    },
    {
        "candidate_id": "qr_v11_vol_adjusted_trend_001",
        "formula_family": "volatility_adjusted_trend",
        "formula": "zscore(div(sub(ema(close,24),ema(close,96)),std(close,48)),120)",
        "hypothesis": "EMA trend scaled by realized volatility may reduce raw trend drawdown.",
        "expected_failure_mode": "Volatility-adjusted trend can fail when realized volatility rises after signal formation.",
    },
]

V11_BUNDLE_CANDIDATES = [
    {
        "candidate_id": "qr_v11_bundle_volume_direction_001",
        "formula_family": "scoped_equal_weight_bundle",
        "component_candidate_ids": [
            "qr_v11_volume_conviction_001",
            "qr_v11_liquidity_adjusted_momentum_001",
            "qr_v11_vol_adjusted_trend_001",
        ],
        "hypothesis": (
            "Volume conviction, liquidity-adjusted momentum, and volatility-adjusted trend may separate BTC direction "
            "from noisy participation."
        ),
    },
    {
        "candidate_id": "qr_v11_bundle_trend_quality_001",
        "formula_family": "scoped_equal_weight_bundle",
        "component_candidate_ids": [
            "qr_v11_trend_efficiency_001",
            "qr_v11_trend_persistence_001",
            "qr_v11_range_position_001",
        ],
        "hypothesis": (
            "Trend efficiency, persistence, and range position may identify higher-quality BTC trend states without "
            "funding features."
        ),
    },
]


def export_v1_1_independent_scoped_candidates(
    out_dir: str | Path,
    *,
    intended_scope: str = V11_SCOPE,
    applicability_hypothesis: str = V11_APPLICABILITY_HYPOTHESIS,
    out_of_scope_policy: str = V11_OUT_OF_SCOPE_POLICY,
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
        "research_checkpoint": "v1.1",
        "candidate_family": "independent_scoped_family_replication",
        "candidate_count": len(records),
        "single_factor_count": len(single_records),
        "bundle_count": len(bundle_records),
        "excluded_research10_survivor": dict(V11_EXCLUDED_RESEARCH10_SURVIVOR),
        "safety": _safety(),
        "scope_contract": {
            "intended_scope": intended_scope,
            "applicability_hypothesis": applicability_hypothesis,
            "out_of_scope_policy": out_of_scope_policy,
        },
        "future_portfolio_interface": _portfolio_contract(),
        "source": {
            "research_checkpoint": "v1.1",
            "created_from_plan": (
                "docs/superpowers/plans/2026-07-03-research-v1-1-independent-scoped-family-replication.md"
            ),
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
    safe_write_text(report_path, render_v1_1_export_report(manifest, records), events_path)
    return manifest


def render_v1_1_export_report(manifest: dict[str, Any], records: list[dict[str, Any]]) -> str:
    excluded = manifest["excluded_research10_survivor"]
    lines = [
        "# QuantumRandy Research v1.1 Independent Scoped Family Replication Export",
        "",
        "This is a research-only factor and bundle export. It is not a runtime publish payload, admission decision,",
        "portfolio construction step, or live execution plan.",
        "Research v1.1 is an independent scoped family replication pass.",
        "",
        "## Summary",
        "",
        f"- Candidate rows: `{manifest['candidate_count']}`",
        f"- Single factors: `{manifest['single_factor_count']}`",
        f"- Bundles: `{manifest['bundle_count']}`",
        f"- Intended scope: `{manifest['scope_contract']['intended_scope']}`",
        f"- Out-of-scope policy: `{manifest['scope_contract']['out_of_scope_policy']}`",
        f"- Excluded Research 1.0 survivor: `{excluded['candidate_id']}::{excluded['variant_id']}`",
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
            "- v1.1 uses only current non-funding DSL fields: open, high, low, close, volume.",
            "- Bundle candidates are equal-weight research signals, not portfolio weights.",
            "- No RandyPortfolio implementation, no runtime publishing, no factor admission, and no live execution.",
        ]
    )
    return "\n".join(lines) + "\n"


def _single_records(**scope: str) -> list[dict[str, Any]]:
    return [
        _record({**item, "component_formulas": [], "component_candidate_ids": []}, **scope)
        for item in V11_SINGLE_FACTOR_CANDIDATES
    ]


def _bundle_records(single_records: list[dict[str, Any]], **scope: str) -> list[dict[str, Any]]:
    by_id = {record["candidate_id"]: record for record in single_records}
    records = []
    for item in V11_BUNDLE_CANDIDATES:
        component_formulas = [by_id[candidate_id]["formula"] for candidate_id in item["component_candidate_ids"]]
        bundle_formula = f"div(add(add({component_formulas[0]},{component_formulas[1]}),{component_formulas[2]}),3)"
        bundle = {
            **item,
            "formula": bundle_formula,
            "component_formulas": component_formulas,
            "expected_failure_mode": V11_EXPECTED_FAILURE_MODE,
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
    formulas = [item["formula"], *list(item.get("component_formulas") or [])]
    if any(re.search(r"\bfunding_rate\b", formula) for formula in formulas):
        raise ValueError(f"v1.1 independent replication excludes funding_rate formulas: {item['candidate_id']}")
    has_components = bool(item.get("component_formulas"))
    return {
        "artifact_type": "quantumrandy_factor_candidate_export",
        "schema_version": 1,
        "research_checkpoint": "v1.1",
        "research_only": True,
        "not_runtime_publish_payload": True,
        "candidate_id": item["candidate_id"],
        "formula": item["formula"],
        "formula_family": item["formula_family"],
        "component_formulas": list(item.get("component_formulas") or []),
        "component_candidate_ids": list(item.get("component_candidate_ids") or []),
        "combination_method": "equal_weight_mean" if has_components else "",
        "intended_scope": intended_scope,
        "applicability_hypothesis": applicability_hypothesis,
        "out_of_scope_policy": out_of_scope_policy,
        "hypothesis": item["hypothesis"],
        "expected_failure_mode": item.get("expected_failure_mode", V11_EXPECTED_FAILURE_MODE),
        "portfolio_interface_contract": _portfolio_contract(),
        "required_features": _required_features(formulas),
        "candidate_tier": "independent_bundle" if has_components else "independent_candidate",
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
    fields = ["open", "high", "low", "close", "volume"]
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
