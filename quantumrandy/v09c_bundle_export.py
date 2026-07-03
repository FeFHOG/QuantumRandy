from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from .io_utils import safe_write_csv, safe_write_json, safe_write_text

V09C_SCOPE = "BTCUSDT_4h"
V09C_OUT_OF_SCOPE_POLICY = "diagnostic_only"
V09C_APPLICABILITY_HYPOTHESIS = (
    "BTCUSDT 4h scoped multi-factor research bundle using only current point-in-time OHLCV and funding fields."
)
V09C_EXPECTED_FAILURE_MODE = (
    "The bundle may fail if components are redundant, trend and reversal components conflict, validation or blind "
    "windows are weak, or drawdown remains high after next-bar execution costs."
)

V09C_SINGLE_FACTOR_CANDIDATES = [
    {
        "candidate_id": "qr_v09c_liquidity_001",
        "formula_family": "liquidity_participation",
        "formula": "zscore(div(volume,sma(volume,48)),120)",
        "hypothesis": "Relative volume participation may identify BTCUSDT liquidity bursts that precede persistent 4h moves.",
        "expected_failure_mode": "Liquidity bursts can become exhaustion or noise when participation is not directional.",
    },
    {
        "candidate_id": "qr_v09c_range_001",
        "formula_family": "range_compression",
        "formula": "neg(zscore(div(sub(high,low),close),96))",
        "hypothesis": "Compressed 4h range may mark calmer BTCUSDT states where continuation or carry signals are less drawdown-prone.",
        "expected_failure_mode": "Range compression can fail during volatility expansion and breakout transitions.",
    },
    {
        "candidate_id": "qr_v09c_trend_001",
        "formula_family": "price_trend",
        "formula": "zscore(ret(close,24),96)",
        "hypothesis": "Medium-horizon BTCUSDT trend may distinguish persistent direction from funding-only crowding noise.",
        "expected_failure_mode": "Trend can reverse sharply during crash rebounds or crowded momentum unwinds.",
    },
    {
        "candidate_id": "qr_v09c_reversal_001",
        "formula_family": "short_horizon_reversal",
        "formula": "neg(zscore(ret(close,6),72))",
        "hypothesis": "Short-horizon BTCUSDT overextension may mean-revert after next-bar execution costs.",
        "expected_failure_mode": "Reversal can fail in persistent directional trends and high-volatility liquidation cascades.",
    },
    {
        "candidate_id": "qr_v09c_funding_001",
        "formula_family": "funding_pressure_crowding",
        "formula": "neg(zscore(div(funding_rate,std(close,48)),96))",
        "hypothesis": "Funding pressure scaled by realized volatility may preserve the least direct v0.9b crowding signal as one component.",
        "expected_failure_mode": "Funding pressure can persist during strong trends and fail to offset costs or drawdown.",
    },
    {
        "candidate_id": "qr_v09c_price_volume_001",
        "formula_family": "price_volume_confirmation",
        "formula": "zscore(corr(volume,ret(close,12),48),72)",
        "hypothesis": "Volume-return correlation may mark participation-confirmed BTCUSDT moves without copying selector v0.8.2 formulas.",
        "expected_failure_mode": "Price-volume confirmation can overfit noisy participation and degrade in blind windows.",
    },
]

V09C_BUNDLE_CANDIDATES = [
    {
        "candidate_id": "qr_v09c_bundle_diversified_001",
        "formula_family": "scoped_equal_weight_bundle",
        "component_candidate_ids": [
            "qr_v09c_liquidity_001",
            "qr_v09c_range_001",
            "qr_v09c_funding_001",
            "qr_v09c_reversal_001",
        ],
        "hypothesis": "A diversified current-DSL bundle may reduce single-family fragility across liquidity, calm-range, funding, and reversal states.",
    },
    {
        "candidate_id": "qr_v09c_bundle_trend_crowding_001",
        "formula_family": "scoped_equal_weight_bundle",
        "component_candidate_ids": [
            "qr_v09c_trend_001",
            "qr_v09c_funding_001",
            "qr_v09c_price_volume_001",
        ],
        "hypothesis": "Trend, funding pressure, and price-volume confirmation may separate persistent BTCUSDT direction from crowded positioning.",
    },
    {
        "candidate_id": "qr_v09c_bundle_calm_reversal_001",
        "formula_family": "scoped_equal_weight_bundle",
        "component_candidate_ids": [
            "qr_v09c_range_001",
            "qr_v09c_reversal_001",
            "qr_v09c_funding_001",
        ],
        "hypothesis": "Calm-range, reversal, and funding pressure may define a cautious BTCUSDT mean-reversion research state.",
    },
]


def export_v0_9c_multi_factor_bundle_candidates(
    out_dir: str | Path,
    *,
    intended_scope: str = V09C_SCOPE,
    applicability_hypothesis: str = V09C_APPLICABILITY_HYPOTHESIS,
    out_of_scope_policy: str = V09C_OUT_OF_SCOPE_POLICY,
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
        "research_checkpoint": "v0.9c",
        "candidate_family": "scoped_multi_factor_bundle",
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
            "research_checkpoint": "v0.9c",
            "created_from_report": "docs/superpowers/specs/2026-07-03-research-v0-9c-design.md",
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
    safe_write_text(report_path, render_v0_9c_export_report(manifest, records), events_path)
    return manifest


def render_v0_9c_export_report(manifest: dict[str, Any], records: list[dict[str, Any]]) -> str:
    lines = [
        "# QuantumRandy Research v0.9c Multi-Factor Bundle Export",
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
            "- v0.9c uses only current DSL fields: open, high, low, close, volume, funding_rate.",
            "- Bundle candidates are equal-weight research signals, not portfolio weights.",
            "- No RandyPortfolio implementation, no runtime publishing, and no live execution.",
        ]
    )
    return "\n".join(lines) + "\n"


def _single_records(**scope: str) -> list[dict[str, Any]]:
    return [
        _record({**item, "component_formulas": [], "component_candidate_ids": []}, **scope)
        for item in V09C_SINGLE_FACTOR_CANDIDATES
    ]


def _bundle_records(single_records: list[dict[str, Any]], **scope: str) -> list[dict[str, Any]]:
    by_id = {record["candidate_id"]: record for record in single_records}
    records = []
    for item in V09C_BUNDLE_CANDIDATES:
        component_formulas = [by_id[candidate_id]["formula"] for candidate_id in item["component_candidate_ids"]]
        bundle = {
            **item,
            "formula": f"equal_weight_mean({','.join(component_formulas)})",
            "component_formulas": component_formulas,
            "expected_failure_mode": V09C_EXPECTED_FAILURE_MODE,
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
        "research_checkpoint": "v0.9c",
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
        "expected_failure_mode": item.get("expected_failure_mode", V09C_EXPECTED_FAILURE_MODE),
        "portfolio_interface_contract": _portfolio_contract(),
        "required_features": _required_features([item["formula"], *list(item.get("component_formulas") or [])]),
        "candidate_tier": "exploratory_bundle" if item.get("component_formulas") else "exploratory",
        "randyslab_eval_profile": randyslab_eval_profile,
        "created_from_report": "docs/superpowers/specs/2026-07-03-research-v0-9c-design.md",
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
    return [field for field in fields if any(field in formula for formula in formulas)]


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
