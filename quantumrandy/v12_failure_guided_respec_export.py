from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from .io_utils import append_jsonl, safe_write_csv, safe_write_json, safe_write_text

V12_SCOPE = "BTCUSDT_4h"
V12_OUT_OF_SCOPE_POLICY = "diagnostic_only"
V12_APPLICABILITY_HYPOTHESIS = (
    "BTCUSDT 4h failure-guided scoped candidate re-spec using v1.1 failure memory and non-funding current-DSL factors."
)
V12_EXPECTED_FAILURE_MODE = (
    "Failure-guided v1.2 candidates may still fail through blind-window weakness, fee or funding stress fragility, "
    "BTC scope weakness, crash-period drawdown, or evidence concentrated in out-of-scope diagnostics."
)
V12_CREATED_FROM_SPEC = "docs/superpowers/specs/2026-07-03-research-v1-2-failure-guided-scoped-respec-design.md"
V12_EXCLUDED_RESEARCH10_SURVIVOR = {
    "candidate_id": "qr_v09d_funding_return_long_001",
    "variant_id": "thr_0p0_long_short_cap_0p5_none",
    "formula_family": "funding_return_long_horizon",
}

V12_SINGLE_FACTOR_CANDIDATES = [
    {
        "candidate_id": "qr_v12_volume_range_conviction_001",
        "formula_family": "volume_conviction_hardening",
        "formula": "zscore(div(corr(sub(close,open),volume,72),div(sub(max(high,48),min(low,48)),close)),96)",
        "hypothesis": (
            "Range-normalized price-volume conviction may keep the v1.1 volume edge while reducing crash fragility."
        ),
        "expected_failure_mode": (
            "Can fail when high-volume bars are forced liquidation reversals or when range normalization lags."
        ),
    },
    {
        "candidate_id": "qr_v12_volume_location_conviction_001",
        "formula_family": "volume_conviction_hardening",
        "formula": "zscore(mul(div(sub(close,open),sub(high,low)),div(volume,sma(volume,96))),120)",
        "hypothesis": "Intrabar close/open conviction scaled by relative volume may filter low-participation noise.",
        "expected_failure_mode": "Can fail in narrow-range bars or when relative-volume expansion marks exhaustion.",
    },
    {
        "candidate_id": "qr_v12_volume_turnover_damped_001",
        "formula_family": "volume_conviction_hardening",
        "formula": "zscore(div(corr(sub(close,open),volume,96),std(ret(close,6),48)),120)",
        "hypothesis": "A slower volume-conviction window damped by short-horizon volatility may reduce fee fragility.",
        "expected_failure_mode": "Can fail if volatility damping removes the best BTC directional windows.",
    },
    {
        "candidate_id": "qr_v12_trend_range_efficiency_slow_001",
        "formula_family": "trend_quality_simplification",
        "formula": "zscore(div(ret(close,48),div(sub(max(high,96),min(low,96)),close)),120)",
        "hypothesis": "Slower trend return per recent range may preserve trend-quality signal while lowering turnover.",
        "expected_failure_mode": "Can fail when slow trend efficiency lags crash or recovery transitions.",
    },
    {
        "candidate_id": "qr_v12_trend_persistence_slow_001",
        "formula_family": "trend_quality_simplification",
        "formula": "zscore(corr(ret(close,12),ret(close,48),72),120)",
        "hypothesis": "Slower short/medium return alignment may keep persistent BTC direction and reduce whipsaw.",
        "expected_failure_mode": "Can fail in sideways BTC regimes or when persistence is a late signal.",
    },
    {
        "candidate_id": "qr_v12_trend_drawdown_aware_001",
        "formula_family": "trend_quality_simplification",
        "formula": "zscore(div(sub(ema(close,48),ema(close,144)),sub(max(high,96),min(low,96))),120)",
        "hypothesis": "EMA trend scaled by a wider range may reduce raw trend drawdown and redundant bundle risk.",
        "expected_failure_mode": "Can fail when broad range scaling suppresses valid trend acceleration.",
    },
    {
        "candidate_id": "qr_v12_crash_participation_filter_001",
        "formula_family": "crash_resilient_participation",
        "formula": "zscore(mul(div(sub(close,open),sub(high,low)),neg(zscore(std(close,48),144))),120)",
        "hypothesis": "Intrabar conviction gated against high realized volatility may reduce crash-period drawdown.",
        "expected_failure_mode": "Can fail by filtering valid high-volatility rebounds or leaving too few positive rows.",
    },
    {
        "candidate_id": "qr_v12_range_expansion_contra_001",
        "formula_family": "crash_resilient_participation",
        "formula": "zscore(div(sub(close,open),mul(sub(high,low),div(volume,sma(volume,96)))),120)",
        "hypothesis": "Range and relative-volume damped intrabar movement may avoid forced-liquidation participation traps.",
        "expected_failure_mode": "Can fail when volume expansion confirms trend rather than exhaustion.",
    },
    {
        "candidate_id": "qr_v12_close_location_volume_001",
        "formula_family": "crash_resilient_participation",
        "formula": "zscore(mul(div(sub(close,low),sub(high,low)),div(volume,sma(volume,96))),120)",
        "hypothesis": "Close location with relative volume may distinguish resilient participation from noisy direction.",
        "expected_failure_mode": "Can fail when close-location strength is a reversal or liquidation artifact.",
    },
]

V12_BUNDLE_CANDIDATES = [
    {
        "candidate_id": "qr_v12_bundle_volume_conviction_hardening_001",
        "formula_family": "failure_guided_equal_weight_bundle",
        "component_candidate_ids": [
            "qr_v12_volume_range_conviction_001",
            "qr_v12_volume_location_conviction_001",
            "qr_v12_volume_turnover_damped_001",
        ],
        "hypothesis": (
            "Equal-weight volume-conviction hardening components may preserve the v1.1 near miss while reducing "
            "turnover and crash fragility."
        ),
    },
    {
        "candidate_id": "qr_v12_bundle_trend_quality_simplification_001",
        "formula_family": "failure_guided_equal_weight_bundle",
        "component_candidate_ids": [
            "qr_v12_trend_range_efficiency_slow_001",
            "qr_v12_trend_persistence_slow_001",
            "qr_v12_trend_drawdown_aware_001",
        ],
        "hypothesis": (
            "Equal-weight simplified trend-quality components may reduce redundant v1.1 bundle behavior while "
            "staying BTC scoped."
        ),
    },
    {
        "candidate_id": "qr_v12_bundle_crash_resilient_participation_001",
        "formula_family": "failure_guided_equal_weight_bundle",
        "component_candidate_ids": [
            "qr_v12_crash_participation_filter_001",
            "qr_v12_range_expansion_contra_001",
            "qr_v12_close_location_volume_001",
        ],
        "hypothesis": (
            "Equal-weight crash-resilient participation components may reduce crash-period drawdown without adding "
            "runtime risk controls."
        ),
    },
]


def export_v1_2_failure_guided_scoped_respec(
    out_dir: str | Path,
    *,
    intended_scope: str = V12_SCOPE,
    applicability_hypothesis: str = V12_APPLICABILITY_HYPOTHESIS,
    out_of_scope_policy: str = V12_OUT_OF_SCOPE_POLICY,
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
        "research_checkpoint": "v1.2",
        "candidate_family": "failure_guided_scoped_respec",
        "candidate_count": len(records),
        "single_factor_count": len(single_records),
        "bundle_count": len(bundle_records),
        "excluded_research10_survivor": dict(V12_EXCLUDED_RESEARCH10_SURVIVOR),
        "safety": _safety(),
        "scope_contract": {
            "intended_scope": intended_scope,
            "applicability_hypothesis": applicability_hypothesis,
            "out_of_scope_policy": out_of_scope_policy,
        },
        "future_portfolio_interface": _portfolio_contract(),
        "source": {
            "research_checkpoint": "v1.2",
            "created_from_spec": V12_CREATED_FROM_SPEC,
        },
        "outputs": {
            "jsonl": jsonl_path.as_posix(),
            "bundle_jsonl": bundle_jsonl_path.as_posix(),
            "csv": csv_path.as_posix(),
            "markdown": report_path.as_posix(),
            "manifest": manifest_path.as_posix(),
            "events": events_path.as_posix(),
        },
    }
    safe_write_json(manifest_path, manifest, events_path)
    safe_write_text(report_path, render_v1_2_export_report(manifest, records), events_path)
    append_jsonl(
        events_path,
        {
            "event": "v1_2_failure_guided_scoped_respec_exported",
            "candidate_count": len(records),
            "single_factor_count": len(single_records),
            "bundle_count": len(bundle_records),
        },
    )
    return manifest


def render_v1_2_export_report(manifest: dict[str, Any], records: list[dict[str, Any]]) -> str:
    excluded = manifest["excluded_research10_survivor"]
    lines = [
        "# QuantumRandy Research v1.2 Failure-Guided Scoped Candidate Re-Spec Export",
        "",
        "This is a research-only factor and bundle export. It is not a runtime publish payload, admission decision,",
        "portfolio construction step, or live execution plan.",
        "Research v1.2 is a failure-guided scoped candidate re-spec.",
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
            "- v1.2 uses only current non-funding DSL fields: open, high, low, close, volume.",
            "- Bundle candidates are equal-weight research signals, not portfolio weights.",
            "- No RandyPortfolio implementation, no runtime publishing, no factor admission, and no live execution.",
        ]
    )
    return "\n".join(lines) + "\n"


def _single_records(**scope: str) -> list[dict[str, Any]]:
    return [
        _record({**item, "component_formulas": [], "component_candidate_ids": []}, **scope)
        for item in V12_SINGLE_FACTOR_CANDIDATES
    ]


def _bundle_records(single_records: list[dict[str, Any]], **scope: str) -> list[dict[str, Any]]:
    by_id = {record["candidate_id"]: record for record in single_records}
    records = []
    for item in V12_BUNDLE_CANDIDATES:
        component_formulas = [by_id[candidate_id]["formula"] for candidate_id in item["component_candidate_ids"]]
        bundle_formula = f"div(add(add({component_formulas[0]},{component_formulas[1]}),{component_formulas[2]}),3)"
        bundle = {
            **item,
            "formula": bundle_formula,
            "component_formulas": component_formulas,
            "expected_failure_mode": V12_EXPECTED_FAILURE_MODE,
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
        raise ValueError(f"v1.2 failure-guided respec excludes funding_rate formulas: {item['candidate_id']}")
    has_components = bool(item.get("component_formulas"))
    return {
        "artifact_type": "quantumrandy_factor_candidate_export",
        "schema_version": 1,
        "research_checkpoint": "v1.2",
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
        "expected_failure_mode": item.get("expected_failure_mode", V12_EXPECTED_FAILURE_MODE),
        "portfolio_interface_contract": _portfolio_contract(),
        "required_features": _required_features(formulas),
        "candidate_tier": "failure_guided_bundle" if has_components else "failure_guided_candidate",
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
