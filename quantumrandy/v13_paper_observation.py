from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

OBSERVATION_ID = "research_v1_3_funding_adjacent_paper_observation"
PROTOCOL_VERDICT = "research_v1_3_paper_observation_protocol_ready_not_started"
MANUAL_REVIEW_VERDICT = "research_v1_3_manual_review_pass_for_paper_observation_planning"
READINESS_VERDICT = "pre_third_project_ready_except_paper_observation_execution"

EXPECTED_CANDIDATE_ID = "qr_v13_funding_range_norm_001"
PRIMARY_VARIANT_ID = "thr_0p0_long_short_cap_0p5_calm_vol_lte_1p5"
PAIRED_DIAGNOSTIC_VARIANT_ID = "thr_0p0_long_flat_cap_0p5_calm_vol_lte_1p5"
EXPECTED_FORMULA = "neg(zscore(div(ema(funding_rate,12),div(sub(max(high,96),min(low,96)),close)),120))"
EXPECTED_SCOPE = "BTCUSDT_4h"

FROZEN_RULES = {
    "scope": EXPECTED_SCOPE,
    "out_of_scope_policy": "diagnostic_only",
    "candidate_family": "funding_pressure_normalization",
    "formula": EXPECTED_FORMULA,
    "primary_variant_id": PRIMARY_VARIANT_ID,
    "paired_diagnostic_variant_id": PAIRED_DIAGNOSTIC_VARIANT_ID,
    "exposure_cap": 0.5,
    "volatility_cap": "calm_vol_lte_1p5",
    "minimum_observation_window": "30 calendar days or at least 120 fresh BTCUSDT 4h bars, whichever is longer",
}


def write_v1_3_paper_observation_packet(
    *,
    export_manifest_path: str | Path,
    ranking_csv_path: str | Path,
    out_dir: str | Path,
    protocol_path: str = "docs/RESEARCH_V1_3_PAPER_OBSERVATION_PROTOCOL.md",
    manual_review_path: str = "docs/RESEARCH_V1_3_MANUAL_REVIEW_REPORT.md",
    readiness_path: str = "docs/PRE_THIRD_PROJECT_READINESS_REPORT.md",
) -> dict[str, Any]:
    export_manifest_path = Path(export_manifest_path)
    ranking_csv_path = Path(ranking_csv_path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    export_manifest = _json(export_manifest_path)
    ranking = pd.read_csv(ranking_csv_path).fillna("")
    rows = _validated_observation_rows(export_manifest, ranking)

    candidates_csv = out / "paper_observation_candidates.csv"
    pd.DataFrame(rows).to_csv(candidates_csv, index=False)

    manifest = {
        "artifact_type": "quantumrandy_v1_3_paper_observation_start_packet",
        "schema_version": 1,
        "observation_id": OBSERVATION_ID,
        "status": "ready_not_started",
        "manual_review_verdict": MANUAL_REVIEW_VERDICT,
        "protocol_verdict": PROTOCOL_VERDICT,
        "pre_third_project_verdict": READINESS_VERDICT,
        "funding_adjacent_status": export_manifest["funding_adjacent_status"],
        "independence_claim": export_manifest["independence_claim"],
        "frozen_rules": FROZEN_RULES,
        "source_artifacts": {
            "export_manifest": export_manifest_path.as_posix(),
            "robustness_ranking": ranking_csv_path.as_posix(),
            "protocol": protocol_path,
            "manual_review": manual_review_path,
            "pre_third_project_readiness": readiness_path,
        },
        "outputs": {
            "manifest": (out / "paper_observation_manifest.json").as_posix(),
            "candidates_csv": candidates_csv.as_posix(),
            "start_markdown": (out / "PAPER_OBSERVATION_START.md").as_posix(),
            "daily_note_template": (out / "DAILY_NOTE_TEMPLATE.md").as_posix(),
        },
        "candidates": rows,
        "safety": _safety(),
        "boundary_confirmation": [
            "No RandyPortfolio implementation.",
            "No live trading.",
            "No exchange private keys.",
            "No runtime factor publishing.",
            "No automatic factor admission.",
            "No production runtime regime labels.",
            "No new formula base fields.",
            "No selector evidence61.",
        ],
        "next_required_report": "docs/RESEARCH_V1_3_PAPER_OBSERVATION_REPORT.md",
    }

    (out / "paper_observation_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    (out / "PAPER_OBSERVATION_START.md").write_text(_render_start_packet(manifest), encoding="utf-8")
    (out / "DAILY_NOTE_TEMPLATE.md").write_text(_render_daily_note_template(manifest), encoding="utf-8")
    return manifest


def _validated_observation_rows(export_manifest: dict[str, Any], ranking: pd.DataFrame) -> list[dict[str, Any]]:
    if export_manifest.get("artifact_type") != "quantumrandy_factor_candidate_export_manifest":
        raise ValueError("v1.3 paper observation requires a factor-candidate export manifest")
    if export_manifest.get("research_checkpoint") != "v1.3":
        raise ValueError("v1.3 paper observation requires a v1.3 export manifest")
    if export_manifest.get("candidate_family") != "funding_adjacent_scoped_respec":
        raise ValueError("v1.3 paper observation requires the funding-adjacent scoped re-spec export")
    if export_manifest.get("funding_adjacent_status") != "funding_adjacent_not_independent_non_funding":
        raise ValueError("v1.3 paper observation requires funding-adjacent status")
    if export_manifest.get("independence_claim") != "none_funding_adjacent_locality_probe":
        raise ValueError("v1.3 paper observation must not claim independent non-funding replication")
    scope_contract = export_manifest.get("scope_contract") or {}
    if scope_contract.get("intended_scope") != EXPECTED_SCOPE:
        raise ValueError("v1.3 paper observation requires BTCUSDT_4h intended scope")
    if scope_contract.get("out_of_scope_policy") != "diagnostic_only":
        raise ValueError("v1.3 paper observation requires diagnostic_only out-of-scope policy")
    safety = export_manifest.get("safety") or {}
    if not safety.get("research_only") or not safety.get("not_runtime_publish_payload"):
        raise ValueError("export manifest is not research-only and non-runtime")

    required_columns = {
        "candidate_id",
        "variant_id",
        "formula",
        "conservative_verdict",
        "stress_survival_count",
        "stress_count",
        "mean_sharpe",
        "validation_mean_sharpe",
        "blind_mean_sharpe",
        "worst_max_dd",
        "robustness_labels",
    }
    missing = sorted(required_columns - set(ranking.columns))
    if missing:
        raise ValueError(f"robustness ranking missing columns: {', '.join(missing)}")

    passed = ranking[ranking["conservative_verdict"].eq("research_watchlist")].copy()
    expected_variants = {PRIMARY_VARIANT_ID, PAIRED_DIAGNOSTIC_VARIANT_ID}
    if len(passed) != len(expected_variants):
        raise ValueError("v1.3 paper observation requires exactly two reviewed survivor rows")
    observed_variants = set(passed["variant_id"].astype(str))
    if observed_variants != expected_variants or set(passed["candidate_id"].astype(str)) != {EXPECTED_CANDIDATE_ID}:
        raise ValueError("v1.3 paper observation requires the reviewed survivor family and variants")
    if passed["variant_id"].astype(str).duplicated().any():
        raise ValueError("v1.3 paper observation requires one survivor row per reviewed variant")
    if set(passed["formula"].astype(str)) != {EXPECTED_FORMULA}:
        raise ValueError("v1.3 paper observation formula is not frozen to the reviewed survivor")

    rows: list[dict[str, Any]] = []
    role_by_variant = {
        PRIMARY_VARIANT_ID: "primary",
        PAIRED_DIAGNOSTIC_VARIANT_ID: "paired_diagnostic",
    }
    for variant_id in [PRIMARY_VARIANT_ID, PAIRED_DIAGNOSTIC_VARIANT_ID]:
        row = passed[passed["variant_id"].eq(variant_id)].iloc[0]
        survival_count = int(float(row["stress_survival_count"]))
        stress_count = int(float(row["stress_count"]))
        if survival_count != stress_count:
            raise ValueError(f"survivor did not pass every stress scenario: {variant_id}")
        rows.append(
            {
                "role": role_by_variant[variant_id],
                "candidate_id": str(row["candidate_id"]),
                "variant_id": variant_id,
                "formula": str(row["formula"]),
                "scope": EXPECTED_SCOPE,
                "stress_survival": f"{survival_count}/{stress_count}",
                "mean_sharpe": _rounded(row["mean_sharpe"]),
                "validation_mean_sharpe": _rounded(row["validation_mean_sharpe"]),
                "blind_mean_sharpe": _rounded(row["blind_mean_sharpe"]),
                "worst_max_dd": _rounded(row["worst_max_dd"]),
                "robustness_labels": _labels(row["robustness_labels"]),
                "paper_observation_status": "ready_not_started",
                "runtime_publish_status": "forbidden",
            }
        )
    return rows


def _render_start_packet(manifest: dict[str, Any]) -> str:
    lines = [
        "# Research v1.3 Paper Observation Start Packet",
        "",
        "Status: ready, not started.",
        "",
        "This is a paper-observation starter packet. It is not a runtime publish payload, not factor admission, not",
        "RandyPortfolio, and not live execution approval.",
        "",
        "## Frozen Candidate Set",
        "",
        "| Role | Candidate | Variant | Stress Survival | Validation Sharpe | Blind Sharpe | Worst Max DD | Labels |",
        "|---|---|---|---:|---:|---:|---:|---|",
    ]
    for row in manifest["candidates"]:
        lines.append(
            f"| `{row['role']}` | `{row['candidate_id']}` | `{row['variant_id']}` | "
            f"{row['stress_survival']} | {row['validation_mean_sharpe']:.4f} | "
            f"{row['blind_mean_sharpe']:.4f} | {row['worst_max_dd']:.4f} | "
            f"`{', '.join(row['robustness_labels']) or 'none'}` |"
        )
    lines.extend(
        [
            "",
            "## Required Next Action",
            "",
            "Execute the observation window defined in `docs/RESEARCH_V1_3_PAPER_OBSERVATION_PROTOCOL.md`, then write",
            "`docs/RESEARCH_V1_3_PAPER_OBSERVATION_REPORT.md` with a pass, extend, or fail verdict.",
            "",
            "## Boundary Confirmation",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in manifest["boundary_confirmation"])
    return "\n".join(lines) + "\n"


def _render_daily_note_template(manifest: dict[str, Any]) -> str:
    primary = next(row for row in manifest["candidates"] if row["role"] == "primary")
    diagnostic = next(row for row in manifest["candidates"] if row["role"] == "paired_diagnostic")
    return (
        "# Research v1.3 Paper Observation Daily Note\n\n"
        "Date: YYYY-MM-DD\n\n"
        "## Frozen Candidates\n\n"
        f"- Primary: `{primary['candidate_id']}::{primary['variant_id']}`.\n"
        f"- Paired diagnostic: `{diagnostic['candidate_id']}::{diagnostic['variant_id']}`.\n\n"
        "## Daily Record\n\n"
        "- Fresh BTCUSDT 4h bars since start: TBD.\n"
        "- Primary signal/exposure intent: TBD.\n"
        "- Paired diagnostic signal/exposure intent: TBD.\n"
        "- Paper equity/drawdown/fees/funding impact: TBD.\n"
        "- Data gaps or delayed funding updates: TBD.\n"
        "- Boundary exceptions attempted: none.\n\n"
        "## Boundary Confirmation\n\n"
        "- No runtime factor publishing.\n"
        "- No live trading.\n"
        "- No exchange private keys.\n"
        "- No RandyPortfolio implementation.\n"
    )


def _safety() -> dict[str, bool]:
    return {
        "research_only": True,
        "paper_only": True,
        "not_runtime_publish_payload": True,
        "does_not_update_runtime": True,
        "does_not_auto_admit_factors": True,
        "does_not_create_randyportfolio": True,
        "no_live_trading": True,
        "no_exchange_private_keys": True,
    }


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _labels(value: Any) -> list[str]:
    return [label.strip() for label in str(value or "").split("|") if label.strip()]


def _rounded(value: Any) -> float:
    return round(float(value), 6)
