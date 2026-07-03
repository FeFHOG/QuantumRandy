from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from .expression import parse_formula
from .io_utils import append_jsonl, safe_write_csv, safe_write_json, safe_write_text

V13_SCOPE = "BTCUSDT_4h"
V13_OUT_OF_SCOPE_POLICY = "diagnostic_only"
V13_FUNDING_ADJACENT_STATUS = "funding_adjacent_not_independent_non_funding"
V13_INDEPENDENCE_CLAIM = "none_funding_adjacent_locality_probe"
V13_APPLICABILITY_HYPOTHESIS = (
    "BTCUSDT 4h funding-adjacent scoped re-spec testing whether Research 1.0 evidence is local to "
    "funding, carry, and friction structure without duplicating the Research 1.0 survivor."
)
V13_EXPECTED_FAILURE_MODE = (
    "Funding-adjacent v1.3 candidates may fail through redundancy with the Research 1.0 survivor, blind-window "
    "weakness, fee or funding stress fragility, BTC scope weakness, crash-period drawdown, or diagnostic "
    "out-of-scope concentration."
)
V13_CREATED_FROM_SPEC = (
    "docs/superpowers/specs/2026-07-03-research-v1-3-funding-adjacent-scoped-respec-design.md"
)
V13_CREATED_FROM_PLAN = (
    "docs/superpowers/plans/2026-07-03-research-v1-3-funding-adjacent-scoped-respec.md"
)
V13_EXCLUDED_RESEARCH10_SURVIVOR = {
    "candidate_id": "qr_v09d_funding_return_long_001",
    "variant_id": "thr_0p0_long_short_cap_0p5_none",
    "formula_family": "funding_return_long_horizon",
    "formula": "zscore(corr(funding_rate,ret(close,42),120),72)",
}

V13_SINGLE_FACTOR_CANDIDATES = [
    {
        "candidate_id": "qr_v13_funding_vol_norm_001",
        "formula_family": "funding_pressure_normalization",
        "formula": "neg(zscore(div(funding_rate,std(close,48)),120))",
        "hypothesis": (
            "Funding pressure scaled by realized price level volatility may capture crowding without raw mean "
            "reversion."
        ),
        "expected_failure_mode": (
            "Can fail if normalized funding remains a direct crowding proxy that is fee or blind-window fragile."
        ),
    },
    {
        "candidate_id": "qr_v13_funding_range_norm_001",
        "formula_family": "funding_pressure_normalization",
        "formula": "neg(zscore(div(ema(funding_rate,12),div(sub(max(high,96),min(low,96)),close)),120))",
        "hypothesis": "Smoothed funding pressure per recent range may reduce crash-window funding noise.",
        "expected_failure_mode": "Can fail when range expansion is the actual funding edge rather than a dampener.",
    },
    {
        "candidate_id": "qr_v13_funding_volume_norm_001",
        "formula_family": "funding_pressure_normalization",
        "formula": "neg(zscore(div(funding_rate,div(volume,sma(volume,96))),120))",
        "hypothesis": "Funding pressure adjusted by relative volume may reduce low-participation funding traps.",
        "expected_failure_mode": "Can fail when high participation confirms rather than dilutes funding pressure.",
    },
    {
        "candidate_id": "qr_v13_funding_return_short_corr_001",
        "formula_family": "funding_return_interaction",
        "formula": "zscore(corr(funding_rate,ret(close,12),72),120)",
        "hypothesis": (
            "Shorter funding/return alignment may test locality without duplicating the long-horizon Research 1.0 "
            "survivor."
        ),
        "expected_failure_mode": "Can fail if useful evidence only exists at the excluded long-horizon alignment.",
    },
    {
        "candidate_id": "qr_v13_funding_return_product_001",
        "formula_family": "funding_return_interaction",
        "formula": "zscore(mul(zscore(funding_rate,96),zscore(ret(close,12),96)),120)",
        "hypothesis": "Funding pressure interacting with recent return may distinguish trend confirmation from crowding.",
        "expected_failure_mode": "Can fail through higher turnover or redundancy with funding-return correlation.",
    },
    {
        "candidate_id": "qr_v13_smooth_funding_return_corr_001",
        "formula_family": "funding_return_interaction",
        "formula": "zscore(corr(ema(funding_rate,12),ret(close,24),96),120)",
        "hypothesis": "Smoothed funding/return alignment may test carry locality at a horizon distinct from Research 1.0.",
        "expected_failure_mode": "Can fail if smoothing lags funding transitions or weakens blind-window behavior.",
    },
    {
        "candidate_id": "qr_v13_funding_volatility_penalty_001",
        "formula_family": "cost_aware_carry_filter",
        "formula": "neg(zscore(mul(funding_rate,std(ret(close,6),48)),120))",
        "hypothesis": "Funding pressure penalized by short-horizon volatility may reduce fee and funding stress fragility.",
        "expected_failure_mode": "Can fail by suppressing valid high-volatility funding opportunities.",
    },
    {
        "candidate_id": "qr_v13_smooth_funding_retvol_norm_001",
        "formula_family": "cost_aware_carry_filter",
        "formula": "neg(zscore(div(ema(funding_rate,24),std(ret(close,6),48)),120))",
        "hypothesis": "Smoothed funding per short-horizon return volatility may reduce noisy carry exposure.",
        "expected_failure_mode": "Can fail when return volatility normalization removes the useful carry signal.",
    },
    {
        "candidate_id": "qr_v13_funding_calm_filter_001",
        "formula_family": "cost_aware_carry_filter",
        "formula": "zscore(mul(neg(zscore(funding_rate,96)),neg(zscore(std(close,48),144))),120)",
        "hypothesis": "Funding crowding only in calmer realized-volatility states may improve cost robustness.",
        "expected_failure_mode": "Can fail by over-filtering and leaving too few positive or completed rows.",
    },
    {
        "candidate_id": "qr_v13_funding_ema_shift_001",
        "formula_family": "funding_regime_transition",
        "formula": "zscore(sub(ema(funding_rate,12),ema(funding_rate,48)),120)",
        "hypothesis": "Funding pressure shifts may be more informative than static funding level.",
        "expected_failure_mode": "Can fail when funding transitions are noisy or too sparse.",
    },
    {
        "candidate_id": "qr_v13_funding_delta_reversal_001",
        "formula_family": "funding_regime_transition",
        "formula": "neg(zscore(delta(funding_rate,12),96))",
        "hypothesis": (
            "Recent funding increases may identify crowding reversal risk without copying long-horizon return "
            "alignment."
        ),
        "expected_failure_mode": "Can fail if funding changes persist through trend continuation.",
    },
    {
        "candidate_id": "qr_v13_funding_delta_return_corr_001",
        "formula_family": "funding_regime_transition",
        "formula": "zscore(corr(delta(funding_rate,12),ret(close,12),72),120)",
        "hypothesis": (
            "Funding transition alignment with short returns may capture state changes distinct from static funding "
            "pressure."
        ),
        "expected_failure_mode": "Can fail if transition timing is sample-specific or blind-window weak.",
    },
]

V13_BUNDLE_CANDIDATES = [
    {
        "candidate_id": "qr_v13_bundle_funding_pressure_norm_001",
        "formula_family": "funding_adjacent_equal_weight_bundle",
        "component_candidate_ids": [
            "qr_v13_funding_vol_norm_001",
            "qr_v13_funding_range_norm_001",
            "qr_v13_funding_volume_norm_001",
        ],
        "hypothesis": (
            "Funding-pressure normalization variants may test whether the v1.3 edge is broader than raw funding "
            "pressure."
        ),
    },
    {
        "candidate_id": "qr_v13_bundle_funding_return_interaction_001",
        "formula_family": "funding_adjacent_equal_weight_bundle",
        "component_candidate_ids": [
            "qr_v13_funding_return_short_corr_001",
            "qr_v13_funding_return_product_001",
            "qr_v13_smooth_funding_return_corr_001",
        ],
        "hypothesis": (
            "Funding/return interactions at non-survivor horizons may test local robustness around the Research 1.0 "
            "edge."
        ),
    },
    {
        "candidate_id": "qr_v13_bundle_cost_aware_carry_001",
        "formula_family": "funding_adjacent_equal_weight_bundle",
        "component_candidate_ids": [
            "qr_v13_funding_volatility_penalty_001",
            "qr_v13_smooth_funding_retvol_norm_001",
            "qr_v13_funding_calm_filter_001",
        ],
        "hypothesis": "Cost-aware carry filters may reduce fee and funding fragility without adding execution controls.",
    },
    {
        "candidate_id": "qr_v13_bundle_funding_transition_001",
        "formula_family": "funding_adjacent_equal_weight_bundle",
        "component_candidate_ids": [
            "qr_v13_funding_ema_shift_001",
            "qr_v13_funding_delta_reversal_001",
            "qr_v13_funding_delta_return_corr_001",
        ],
        "hypothesis": "Funding transition components may test whether shifts in funding state are more robust than static level.",
    },
]


def export_v1_3_funding_adjacent_scoped_respec(
    out_dir: str | Path,
    *,
    intended_scope: str = V13_SCOPE,
    applicability_hypothesis: str = V13_APPLICABILITY_HYPOTHESIS,
    out_of_scope_policy: str = V13_OUT_OF_SCOPE_POLICY,
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
        "research_checkpoint": "v1.3",
        "candidate_family": "funding_adjacent_scoped_respec",
        "funding_adjacent_status": V13_FUNDING_ADJACENT_STATUS,
        "independence_claim": V13_INDEPENDENCE_CLAIM,
        "candidate_count": len(records),
        "single_factor_count": len(single_records),
        "bundle_count": len(bundle_records),
        "excluded_research10_survivor": dict(V13_EXCLUDED_RESEARCH10_SURVIVOR),
        "safety": _safety(),
        "scope_contract": {
            "intended_scope": intended_scope,
            "applicability_hypothesis": applicability_hypothesis,
            "out_of_scope_policy": out_of_scope_policy,
        },
        "future_portfolio_interface": _portfolio_contract(),
        "source": _source(),
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
    safe_write_text(report_path, render_v1_3_export_report(manifest, records), events_path)
    append_jsonl(
        events_path,
        {
            "event": "v1_3_funding_adjacent_scoped_respec_exported",
            "candidate_count": len(records),
            "single_factor_count": len(single_records),
            "bundle_count": len(bundle_records),
        },
    )
    return manifest


def render_v1_3_export_report(manifest: dict[str, Any], records: list[dict[str, Any]]) -> str:
    excluded = manifest["excluded_research10_survivor"]
    lines = [
        "# QuantumRandy Research v1.3 Funding-Adjacent Scoped Re-Spec Export",
        "",
        "This is a research-only factor and bundle export. It is not a runtime publish payload, admission decision,",
        "portfolio construction step, or live execution plan.",
        "Research v1.3 is a funding-adjacent scoped re-spec and not independent non-funding replication.",
        "",
        "## Summary",
        "",
        f"- Candidate rows: `{manifest['candidate_count']}`",
        f"- Single factors: `{manifest['single_factor_count']}`",
        f"- Bundles: `{manifest['bundle_count']}`",
        f"- Funding-adjacent status: `{manifest['funding_adjacent_status']}`",
        f"- Independence claim: `{manifest['independence_claim']}`",
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
            "- v1.3 uses funding-adjacent DSL fields and requires funding_rate in every exported row.",
            "- Bundle candidates are equal-weight research signals, not portfolio weights.",
            "- No RandyPortfolio implementation, no runtime publishing, no factor admission, and no live execution.",
        ]
    )
    return "\n".join(lines) + "\n"


def _single_records(**scope: str) -> list[dict[str, Any]]:
    return [
        _record({**item, "component_formulas": [], "component_candidate_ids": []}, **scope)
        for item in V13_SINGLE_FACTOR_CANDIDATES
    ]


def _bundle_records(single_records: list[dict[str, Any]], **scope: str) -> list[dict[str, Any]]:
    by_id = {record["candidate_id"]: record for record in single_records}
    records = []
    for item in V13_BUNDLE_CANDIDATES:
        _validate_bundle_components(item, by_id)
        component_formulas = [by_id[candidate_id]["formula"] for candidate_id in item["component_candidate_ids"]]
        bundle_formula = f"div(add(add({component_formulas[0]},{component_formulas[1]}),{component_formulas[2]}),3)"
        bundle = {
            **item,
            "formula": bundle_formula,
            "component_formulas": component_formulas,
            "expected_failure_mode": V13_EXPECTED_FAILURE_MODE,
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
    _reject_excluded_survivor(item["candidate_id"], formulas)
    required_features = _required_features(formulas)
    if "funding_rate" not in required_features:
        raise ValueError(f"v1.3 funding-adjacent respec requires funding_rate: {item['candidate_id']}")
    has_components = bool(item.get("component_formulas"))
    return {
        "artifact_type": "quantumrandy_factor_candidate_export",
        "schema_version": 1,
        "research_checkpoint": "v1.3",
        "research_only": True,
        "not_runtime_publish_payload": True,
        "candidate_id": item["candidate_id"],
        "formula": item["formula"],
        "formula_family": item["formula_family"],
        "component_formulas": list(item.get("component_formulas") or []),
        "component_candidate_ids": list(item.get("component_candidate_ids") or []),
        "combination_method": "equal_weight_mean" if has_components else "",
        "funding_adjacent_status": V13_FUNDING_ADJACENT_STATUS,
        "independence_claim": V13_INDEPENDENCE_CLAIM,
        "excluded_research10_survivor": dict(V13_EXCLUDED_RESEARCH10_SURVIVOR),
        "source": _source(),
        "safety": _safety(),
        "intended_scope": intended_scope,
        "applicability_hypothesis": applicability_hypothesis,
        "out_of_scope_policy": out_of_scope_policy,
        "hypothesis": item["hypothesis"],
        "expected_failure_mode": item.get("expected_failure_mode", V13_EXPECTED_FAILURE_MODE),
        "portfolio_interface_contract": _portfolio_contract(),
        "required_features": required_features,
        "candidate_tier": "funding_adjacent_bundle" if has_components else "funding_adjacent_candidate",
        "randyslab_eval_profile": randyslab_eval_profile,
    }


def _reject_excluded_survivor(candidate_id: str, formulas: list[str]) -> None:
    excluded_id = V13_EXCLUDED_RESEARCH10_SURVIVOR["candidate_id"]
    excluded_formula = V13_EXCLUDED_RESEARCH10_SURVIVOR["formula"]
    excluded_canonical = _canonical_formula(excluded_formula)
    if candidate_id == excluded_id:
        raise ValueError(f"v1.3 funding-adjacent respec excludes Research 1.0 survivor ID: {candidate_id}")
    if any(_canonical_formula(formula) == excluded_canonical for formula in formulas):
        raise ValueError(f"v1.3 funding-adjacent respec excludes Research 1.0 survivor formula: {candidate_id}")


def _validate_bundle_components(item: dict[str, Any], by_id: dict[str, dict[str, Any]]) -> None:
    candidate_id = item["candidate_id"]
    component_candidate_ids = list(item.get("component_candidate_ids") or [])
    if len(component_candidate_ids) != 3:
        raise ValueError(f"v1.3 funding-adjacent bundle requires exactly 3 components: {candidate_id}")
    if len(set(component_candidate_ids)) != 3:
        raise ValueError(f"v1.3 funding-adjacent bundle requires unique components: {candidate_id}")
    excluded_id = V13_EXCLUDED_RESEARCH10_SURVIVOR["candidate_id"]
    if excluded_id in component_candidate_ids:
        raise ValueError(f"v1.3 funding-adjacent respec excludes Research 1.0 survivor bundle member: {candidate_id}")
    for component_id in component_candidate_ids:
        if component_id not in by_id:
            raise ValueError(
                f"v1.3 funding-adjacent bundle references unknown component {component_id}: {candidate_id}"
            )


def _canonical_formula(formula: str) -> str:
    return parse_formula(formula).canonical()


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
        row["excluded_research10_survivor"] = json.dumps(
            record.get("excluded_research10_survivor", {}), ensure_ascii=True
        )
        row["source"] = json.dumps(record.get("source", {}), ensure_ascii=True)
        row["safety"] = json.dumps(record.get("safety", {}), ensure_ascii=True)
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


def _source() -> dict[str, str]:
    return {
        "research_checkpoint": "v1.3",
        "created_from_spec": V13_CREATED_FROM_SPEC,
        "created_from_plan": V13_CREATED_FROM_PLAN,
    }


def _portfolio_contract() -> dict[str, str]:
    return {
        "consumer_project": "RandyPortfolio",
        "status": "interface_only_not_implemented",
        "allowed_use": "research_artifact_input",
        "forbidden_use": "runtime_allocation_or_live_execution",
    }
