# Research v1.2 Failure-Guided Scoped Candidate Re-Spec Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a research-only v1.2 checkpoint that re-specs a narrow independent non-funding candidate cohort from v1.1 failure memory and tests it through the existing RandysLab strict declared-scope stack.

**Architecture:** QuantumRandy owns deterministic v1.2 export, failure memory, report rendering, and tracked documentation. RandysLab source changes are not expected; reuse existing declared review, diagnostic review, correlation, and scope-aware robustness CLIs. The checkpoint may end with a survivor pending manual research review or a clean negative result.

**Tech Stack:** Python 3, pandas, pytest, QuantumRandy JSONL/CSV/Markdown export helpers, RandysLab strict4h config, existing RandysLab factor-candidate sensitivity/review/correlation/robustness CLIs.

---

## Current State

- Research 1.0 has one scoped BTCUSDT 4h funding-return survivor:
  `qr_v09d_funding_return_long_001::thr_0p0_long_short_cap_0p5_none`.
- Research v1.1 tested `10` independent non-funding candidates and found no survivor.
- V1.1 robustness generated `50` candidate/variant rankings, all blocked, with best near misses at `12/15` hard
  stresses.
- V1.2 must remain research-only and must not enter paper observation, RandyPortfolio planning, runtime publishing, or
  live trading.
- V1.2 should use current admitted formula fields only: `open`, `high`, `low`, `close`, `volume`, and `funding_rate`.
- V1.2 candidate formulas must exclude direct `funding_rate` usage to preserve independence from the Research 1.0
  funding-return survivor. RandysLab may still use funding data for funding-cost stress.

## File Structure

### QuantumRandy

- Create `quantumrandy/v12_failure_guided_respec_export.py`
  - Defines the v1.2 deterministic candidate cohort.
  - Excludes `funding_return_long_horizon`, direct `funding_rate` formulas, and bundles containing the v1.0 survivor.
  - Writes JSONL, bundle JSONL, CSV, manifest, Markdown export, and events.
- Create `scripts/export_v1_2_failure_guided_scoped_respec.py`
  - Thin CLI wrapper around the export module.
- Create `quantumrandy/v12_failure_guided_respec_memory.py`
  - Converts RandysLab v1.2 robustness rankings into failure-memory rows.
  - Preserves passed rows in memory but writes only failed rows to `failure_memory.csv`.
  - Adds labels for `failure_guided_respec`, `non_funding_family`, and replication stress failures.
- Create `scripts/build_v1_2_failure_guided_respec_memory.py`
  - CLI wrapper around the v1.2 memory writer.
- Create `scripts/render_v1_2_failure_guided_scoped_respec_report.py`
  - Renders the final v1.2 report from export, RandysLab review/correlation/robustness artifacts, and failure memory.
- Create `tests/test_v1_2_failure_guided_respec.py`
  - Covers export safety/schema, funding-survivor exclusion, memory behavior, and report readiness verdicts.
- Create `docs/RESEARCH_V1_2_FAILURE_GUIDED_SCOPED_RESPEC_REPORT.md`
  - Final tracked report after artifacts are generated.
- Modify `docs/README.md`
  - Add the new v1.2 plan and report entries.
- Modify `docs/PROJECT_LOG.md`
  - Add a top entry after the v1.2 report is rendered.

### RandysLab

- No source changes are expected.
- Reuse existing scripts:
  - `scripts/sweep_factor_candidates.py`
  - `scripts/review_factor_candidate_sensitivity.py`
  - `scripts/review_factor_candidate_correlation.py`
  - `scripts/run_watchlist_robustness_gauntlet.py`
- Generate ignored research artifacts under:
  - `reports/factor_candidate_sensitivity/research_v1_2_btc_primary`
  - `reports/factor_candidate_review/research_v1_2_btc_primary`
  - `reports/factor_candidate_sensitivity/research_v1_2_eth_diagnostic`
  - `reports/factor_candidate_review/research_v1_2_eth_diagnostic`
  - `reports/factor_candidate_sensitivity/research_v1_2_sol_diagnostic`
  - `reports/factor_candidate_review/research_v1_2_sol_diagnostic`
  - `reports/factor_candidate_sensitivity/research_v1_2_bnb_diagnostic`
  - `reports/factor_candidate_review/research_v1_2_bnb_diagnostic`
  - `reports/factor_candidate_sensitivity/research_v1_2_avax_diagnostic`
  - `reports/factor_candidate_review/research_v1_2_avax_diagnostic`
  - `reports/factor_candidate_correlation/research_v1_2_btc`
  - `reports/factor_candidate_robustness/research_v1_2_failure_guided_respec`

## Task 1: Export Failure-Guided v1.2 Candidate Cohort

**Files:**
- Create: `quantumrandy/v12_failure_guided_respec_export.py`
- Create: `scripts/export_v1_2_failure_guided_scoped_respec.py`
- Create: `tests/test_v1_2_failure_guided_respec.py`

- [ ] **Step 1: Write the failing export test**

Create `tests/test_v1_2_failure_guided_respec.py` with this content:

```python
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from quantumrandy.expression import parse_formula
from quantumrandy.v12_failure_guided_respec_export import (
    V12_BUNDLE_CANDIDATES,
    V12_SINGLE_FACTOR_CANDIDATES,
    export_v1_2_failure_guided_scoped_respec,
)


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_export_v1_2_failure_guided_candidates_are_scoped_and_non_funding(tmp_path) -> None:
    out = tmp_path / "v12_export"

    manifest = export_v1_2_failure_guided_scoped_respec(out)

    assert manifest["artifact_type"] == "quantumrandy_factor_candidate_export_manifest"
    assert manifest["research_checkpoint"] == "v1.2"
    assert manifest["candidate_family"] == "failure_guided_scoped_respec"
    assert manifest["scope_contract"]["intended_scope"] == "BTCUSDT_4h"
    assert manifest["scope_contract"]["out_of_scope_policy"] == "diagnostic_only"
    assert manifest["source"]["created_from_spec"] == (
        "docs/superpowers/specs/2026-07-03-research-v1-2-failure-guided-scoped-respec-design.md"
    )
    assert manifest["excluded_research10_survivor"] == {
        "candidate_id": "qr_v09d_funding_return_long_001",
        "variant_id": "thr_0p0_long_short_cap_0p5_none",
        "formula_family": "funding_return_long_horizon",
    }
    assert manifest["candidate_count"] == len(V12_SINGLE_FACTOR_CANDIDATES) + len(V12_BUNDLE_CANDIDATES)
    assert manifest["single_factor_count"] == 9
    assert manifest["bundle_count"] == 3
    assert manifest["safety"]["research_only"] is True
    assert manifest["safety"]["not_runtime_publish_payload"] is True
    assert manifest["safety"]["does_not_auto_admit_factors"] is True

    records = _jsonl(out / "factor_candidates.jsonl")
    bundle_records = _jsonl(out / "bundle_candidates.jsonl")
    assert len(records) == 12
    assert len(bundle_records) == 3

    disallowed_candidate_ids = {"qr_v09d_funding_return_long_001", "qr_v09d_bundle_funding_confirmation_001"}
    disallowed_formula_fragments = {"funding_rate"}
    required_families = {
        "volume_conviction_hardening",
        "trend_quality_simplification",
        "crash_resilient_participation",
        "failure_guided_equal_weight_bundle",
    }
    allowed_fields = {"open", "high", "low", "close", "volume"}
    observed_families = set()

    for record in records:
        assert record["artifact_type"] == "quantumrandy_factor_candidate_export"
        assert record["research_checkpoint"] == "v1.2"
        assert record["research_only"] is True
        assert record["not_runtime_publish_payload"] is True
        assert record["intended_scope"] == "BTCUSDT_4h"
        assert record["out_of_scope_policy"] == "diagnostic_only"
        assert record["candidate_id"] not in disallowed_candidate_ids
        assert record["candidate_tier"] in {"failure_guided_candidate", "failure_guided_bundle"}
        assert set(record["required_features"]).issubset(allowed_fields)
        observed_families.add(record["formula_family"])
        formulas = [record["formula"], *record.get("component_formulas", [])]
        for formula in formulas:
            parse_formula(formula)
            assert not any(fragment in formula for fragment in disallowed_formula_fragments)

    assert required_families.issubset(observed_families)

    csv = pd.read_csv(out / "factor_candidates.csv")
    assert len(csv) == 12
    assert set(csv["intended_scope"]) == {"BTCUSDT_4h"}
    assert set(csv["out_of_scope_policy"]) == {"diagnostic_only"}

    report = (out / "FACTOR_CANDIDATE_EXPORT.md").read_text(encoding="utf-8")
    assert "Research v1.2" in report
    assert "failure-guided scoped candidate re-spec" in report
    assert "not a runtime publish payload" in report
```

- [ ] **Step 2: Run the export test to verify it fails**

Run:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest tests/test_v1_2_failure_guided_respec.py::test_export_v1_2_failure_guided_candidates_are_scoped_and_non_funding -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'quantumrandy.v12_failure_guided_respec_export'`.

- [ ] **Step 3: Implement the export module**

Create `quantumrandy/v12_failure_guided_respec_export.py` with this structure:

```python
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from .io_utils import safe_write_csv, safe_write_json, safe_write_text

V12_SCOPE = "BTCUSDT_4h"
V12_OUT_OF_SCOPE_POLICY = "diagnostic_only"
V12_APPLICABILITY_HYPOTHESIS = (
    "BTCUSDT 4h failure-guided scoped candidate re-spec using v1.1 failure memory and non-funding current-DSL factors."
)
V12_EXPECTED_FAILURE_MODE = (
    "Failure-guided v1.2 candidates may still fail through blind-window weakness, fee or funding stress fragility, "
    "BTC scope weakness, crash-period drawdown, or evidence concentrated in out-of-scope diagnostics."
)
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
        "hypothesis": "Range-normalized price-volume conviction may keep the v1.1 volume edge while reducing crash fragility.",
        "expected_failure_mode": "Can fail when high-volume bars are forced liquidation reversals or when range normalization lags.",
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
        "hypothesis": "Intrabar conviction penalized by high realized volatility may avoid forced-participation crash windows.",
        "expected_failure_mode": "Can fail by over-filtering high-volatility recovery trends or leaving too few completed rows.",
    },
    {
        "candidate_id": "qr_v12_range_expansion_contra_001",
        "formula_family": "crash_resilient_participation",
        "formula": "zscore(div(sub(close,open),mul(sub(high,low),div(volume,sma(volume,96)))),120)",
        "hypothesis": "Price movement divided by range and relative volume may avoid high-participation liquidation noise.",
        "expected_failure_mode": "Can fail when large range and volume are genuine continuation signals.",
    },
    {
        "candidate_id": "qr_v12_close_location_volume_001",
        "formula_family": "crash_resilient_participation",
        "formula": "zscore(mul(div(sub(close,low),sub(high,low)),div(volume,sma(volume,96))),120)",
        "hypothesis": "Close location with relative volume may distinguish participation-backed closes from weak bars.",
        "expected_failure_mode": "Can fail in whipsaw bars where close location does not persist into the next bar.",
    },
]

V12_BUNDLE_CANDIDATES = [
    {
        "candidate_id": "qr_v12_bundle_volume_hardened_001",
        "formula_family": "failure_guided_equal_weight_bundle",
        "component_candidate_ids": [
            "qr_v12_volume_range_conviction_001",
            "qr_v12_volume_location_conviction_001",
            "qr_v12_volume_turnover_damped_001",
        ],
        "hypothesis": "The three volume-hardening variants may preserve v1.1's best near miss while reducing turnover and crash fragility.",
    },
    {
        "candidate_id": "qr_v12_bundle_trend_simplified_001",
        "formula_family": "failure_guided_equal_weight_bundle",
        "component_candidate_ids": [
            "qr_v12_trend_range_efficiency_slow_001",
            "qr_v12_trend_persistence_slow_001",
            "qr_v12_trend_drawdown_aware_001",
        ],
        "hypothesis": "Simplified trend-quality components may reduce redundant bundle risk while preserving BTC trend-quality evidence.",
    },
    {
        "candidate_id": "qr_v12_bundle_crash_participation_001",
        "formula_family": "failure_guided_equal_weight_bundle",
        "component_candidate_ids": [
            "qr_v12_crash_participation_filter_001",
            "qr_v12_range_expansion_contra_001",
            "qr_v12_close_location_volume_001",
        ],
        "hypothesis": "Crash-resilient participation filters may reduce crash-period drawdown without adding execution stops.",
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
            "created_from_spec": "docs/superpowers/specs/2026-07-03-research-v1-2-failure-guided-scoped-respec-design.md",
            "created_from_plan": "docs/superpowers/plans/2026-07-03-research-v1-2-failure-guided-scoped-respec.md",
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
    safe_write_text(report_path, render_v1_2_export_report(manifest, records), events_path)
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
```

- [ ] **Step 4: Add the export CLI**

Create `scripts/export_v1_2_failure_guided_scoped_respec.py`:

```python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantumrandy.v12_failure_guided_respec_export import export_v1_2_failure_guided_scoped_respec


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Research v1.2 failure-guided scoped candidate re-spec.")
    parser.add_argument(
        "--out",
        default="reports/factor_candidate_exports/research_v1_2_failure_guided_scoped_respec",
        help="Output directory for JSONL, bundle JSONL, CSV, manifest, and Markdown report.",
    )
    args = parser.parse_args()
    manifest = export_v1_2_failure_guided_scoped_respec(args.out)
    print(
        "v1.2 failure-guided scoped candidate re-spec export: "
        f"candidates={manifest['candidate_count']} "
        f"single_factors={manifest['single_factor_count']} "
        f"bundles={manifest['bundle_count']} "
        f"jsonl={Path(manifest['outputs']['jsonl']).resolve()}"
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run the export test to verify it passes**

Run:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest tests/test_v1_2_failure_guided_respec.py::test_export_v1_2_failure_guided_candidates_are_scoped_and_non_funding -q
```

Expected: `1 passed`.

- [ ] **Step 6: Commit the export layer**

Run:

```bash
git add quantumrandy/v12_failure_guided_respec_export.py scripts/export_v1_2_failure_guided_scoped_respec.py tests/test_v1_2_failure_guided_respec.py
git commit -m "Add Research v1.2 failure-guided candidate export"
```

## Task 2: Build v1.2 Failure Memory

**Files:**
- Create: `quantumrandy/v12_failure_guided_respec_memory.py`
- Create: `scripts/build_v1_2_failure_guided_respec_memory.py`
- Modify: `tests/test_v1_2_failure_guided_respec.py`

- [ ] **Step 1: Write the failing memory test**

Append this test to `tests/test_v1_2_failure_guided_respec.py`:

```python
def test_v1_2_failure_memory_records_only_failed_rankings(tmp_path) -> None:
    from quantumrandy.v12_failure_guided_respec_memory import (
        build_v1_2_failure_guided_respec_memory_rows,
        write_v1_2_failure_guided_respec_failure_memory,
    )

    ranking_csv = tmp_path / "watchlist_robustness_variant_ranking.csv"
    pd.DataFrame(
        [
            {
                "candidate_id": "qr_v12_volume_range_conviction_001",
                "formula": "zscore(div(corr(sub(close,open),volume,72),div(sub(max(high,48),min(low,48)),close)),96)",
                "variant_id": "thr_0p0_long_flat_cap_0p5_calm_vol_lte_1p5",
                "conservative_verdict": "blocked_pending_new_hypotheses",
                "failure_reasons": "weak_blind_window",
                "diagnostic_failure_reasons": "sol_avax_concentration",
                "robustness_labels": "fee_fragility|btc_weakness",
                "stress_survival_count": 12,
                "stress_count": 15,
                "stress_survival_score": 0.8,
                "diagnostic_scenario_count": 1,
                "mean_sharpe": 0.6,
                "validation_mean_sharpe": 0.2,
                "blind_mean_sharpe": 0.1,
                "mean_max_dd": 0.2,
                "worst_max_dd": 0.45,
            },
            {
                "candidate_id": "qr_v12_trend_persistence_slow_001",
                "formula": "zscore(corr(ret(close,12),ret(close,48),72),120)",
                "variant_id": "thr_0p0_long_short_cap_0p5_calm_vol_lte_1p5",
                "conservative_verdict": "research_watchlist",
                "failure_reasons": "",
                "diagnostic_failure_reasons": "asset_exclusion_fragility",
                "robustness_labels": "sol_avax_concentration",
                "stress_survival_count": 15,
                "stress_count": 15,
                "stress_survival_score": 1.0,
                "diagnostic_scenario_count": 1,
                "mean_sharpe": 0.7,
                "validation_mean_sharpe": 0.4,
                "blind_mean_sharpe": 0.5,
                "mean_max_dd": 0.2,
                "worst_max_dd": 0.3,
            },
        ]
    ).to_csv(ranking_csv, index=False)

    rows = build_v1_2_failure_guided_respec_memory_rows(
        ranking_csv,
        source_robustness_dir="reports/factor_candidate_robustness/research_v1_2_failure_guided_respec",
    )

    assert len(rows) == 2
    by_id = {row["candidate_id"]: row for row in rows}
    failed = by_id["qr_v12_volume_range_conviction_001::thr_0p0_long_flat_cap_0p5_calm_vol_lte_1p5"]
    assert failed["passed"] is False
    assert failed["candidate_family"] == "research_v1_2_failure_guided_respec_variant"
    assert failed["intended_scope"] == "BTCUSDT_4h"
    assert failed["out_of_scope_policy"] == "diagnostic_only"
    assert failed["stress_survival"] == "12/15"
    assert "failure_guided_respec" in failed["failure_labels"]
    assert "non_funding_family" in failed["failure_labels"]
    assert "replication_stress_fragility" in failed["failure_labels"]
    assert "weak_blind_window" in failed["failure_labels"]

    survivor = by_id["qr_v12_trend_persistence_slow_001::thr_0p0_long_short_cap_0p5_calm_vol_lte_1p5"]
    assert survivor["passed"] is True
    assert "replication_stress_fragility" not in survivor["failure_labels"]

    out = tmp_path / "failure_memory"
    manifest = write_v1_2_failure_guided_respec_failure_memory(
        ranking_csv,
        out,
        source_robustness_dir="reports/factor_candidate_robustness/research_v1_2_failure_guided_respec",
    )

    assert manifest["artifact_type"] == "quantumrandy_failure_memory"
    assert manifest["input_rows"] == 2
    assert manifest["failure_count"] == 1
    memory = pd.read_csv(out / "failure_memory.csv")
    assert memory.iloc[0]["candidate_id"] == "qr_v12_volume_range_conviction_001::thr_0p0_long_flat_cap_0p5_calm_vol_lte_1p5"
```

- [ ] **Step 2: Run the memory test to verify it fails**

Run:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest tests/test_v1_2_failure_guided_respec.py::test_v1_2_failure_memory_records_only_failed_rankings -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'quantumrandy.v12_failure_guided_respec_memory'`.

- [ ] **Step 3: Implement the memory module**

Create `quantumrandy/v12_failure_guided_respec_memory.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .failure_memory import write_failure_memory

V12_RESPEC_DESCRIPTION = "Research v1.2 failure-guided scoped candidate re-spec robustness variant."
V12_RESPEC_FAILURE_MODE = (
    "Failure-guided non-funding candidate variants may fail Research v1.2 through BTC scope stress fragility, "
    "weak validation or blind windows, fee/funding sensitivity, crash drawdown, or out-of-scope diagnostic concentration."
)


def build_v1_2_failure_guided_respec_memory_rows(
    ranking_csv: str | Path,
    *,
    source_robustness_dir: str,
) -> list[dict[str, Any]]:
    ranking = pd.read_csv(ranking_csv).fillna("")
    rows: list[dict[str, Any]] = []
    for raw in ranking.to_dict(orient="records"):
        candidate_id = str(raw.get("candidate_id", ""))
        variant_id = str(raw.get("variant_id", "default") or "default")
        labels = _labels(raw)
        verdict = str(raw.get("conservative_verdict", ""))
        passed = verdict == "research_watchlist"
        rows.append(
            {
                "candidate_id": f"{candidate_id}::{variant_id}",
                "formula": raw.get("formula", ""),
                "candidate_family": "research_v1_2_failure_guided_respec_variant",
                "description": V12_RESPEC_DESCRIPTION,
                "hypothesis": f"{candidate_id} failure-guided v1.2 variant {variant_id}.",
                "expected_failure_mode": V12_RESPEC_FAILURE_MODE,
                "intended_scope": raw.get("intended_scope", "BTCUSDT_4h") or "BTCUSDT_4h",
                "out_of_scope_policy": "diagnostic_only",
                "conservative_verdict": verdict,
                "passed": passed,
                "kill_reasons": [] if passed else _kill_reasons(raw, labels),
                "failure_labels": "|".join(labels),
                "source_review_dir": source_robustness_dir,
                "source_robustness_dir": source_robustness_dir,
                "stress_survival": _stress_survival(raw),
                "stress_survival_score": _float(raw.get("stress_survival_score", "")),
                "sharpe": _float(raw.get("mean_sharpe", "")),
                "validation_sharpe": _float(raw.get("validation_mean_sharpe", "")),
                "blind_sharpe": _float(raw.get("blind_mean_sharpe", "")),
                "max_dd": _float(raw.get("mean_max_dd", "")),
                "worst_max_dd": _float(raw.get("worst_max_dd", "")),
            }
        )
    return rows


def write_v1_2_failure_guided_respec_failure_memory(
    ranking_csv: str | Path,
    out_dir: str | Path,
    *,
    source_robustness_dir: str,
) -> dict[str, Any]:
    rows = build_v1_2_failure_guided_respec_memory_rows(
        ranking_csv,
        source_robustness_dir=source_robustness_dir,
    )
    return write_failure_memory(rows, out_dir)


def _labels(row: dict[str, Any]) -> list[str]:
    labels = set(_split_labels(row.get("robustness_labels", "")))
    labels.update(_split_labels(row.get("failure_reasons", "")))
    labels.update(_split_labels(row.get("diagnostic_failure_reasons", "")))
    labels.add("failure_guided_respec")
    labels.add("non_funding_family")
    if _float(row.get("stress_survival_score", "")) < 1.0:
        labels.add("replication_stress_fragility")
    return sorted(label for label in labels if label)


def _kill_reasons(row: dict[str, Any], labels: list[str]) -> list[str]:
    reasons = _split_labels(row.get("failure_reasons", ""))
    if reasons:
        return reasons
    return labels


def _stress_survival(row: dict[str, Any]) -> str:
    survived = _int(row.get("stress_survival_count", ""))
    total = _int(row.get("stress_count", ""))
    return f"{survived}/{total}"


def _split_labels(value: Any) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    return [part.strip() for part in text.replace(",", "|").split("|") if part.strip()]


def _float(value: Any) -> float | str:
    if value in (None, ""):
        return ""
    try:
        return round(float(value), 8)
    except (TypeError, ValueError):
        return ""


def _int(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0
```

- [ ] **Step 4: Add the memory CLI**

Create `scripts/build_v1_2_failure_guided_respec_memory.py`:

```python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantumrandy.v12_failure_guided_respec_memory import write_v1_2_failure_guided_respec_failure_memory


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Research v1.2 failure-guided re-spec failure memory.")
    parser.add_argument("--ranking-csv", required=True)
    parser.add_argument("--source-robustness-dir", required=True)
    parser.add_argument("--out", default="reports/failure_memory/research_v1_2_failure_guided_respec")
    args = parser.parse_args()
    manifest = write_v1_2_failure_guided_respec_failure_memory(
        args.ranking_csv,
        args.out,
        source_robustness_dir=args.source_robustness_dir,
    )
    print(f"Failure rows: {manifest['failure_count']} / input rows: {manifest['input_rows']}")
    print(f"Output: {Path(args.out).resolve()}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run the memory test to verify it passes**

Run:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest tests/test_v1_2_failure_guided_respec.py::test_v1_2_failure_memory_records_only_failed_rankings -q
```

Expected: `1 passed`.

- [ ] **Step 6: Commit the memory layer**

Run:

```bash
git add quantumrandy/v12_failure_guided_respec_memory.py scripts/build_v1_2_failure_guided_respec_memory.py tests/test_v1_2_failure_guided_respec.py
git commit -m "Add Research v1.2 failure memory"
```

## Task 3: Render v1.2 Readiness Report

**Files:**
- Create: `scripts/render_v1_2_failure_guided_scoped_respec_report.py`
- Modify: `tests/test_v1_2_failure_guided_respec.py`
- Later generate: `docs/RESEARCH_V1_2_FAILURE_GUIDED_SCOPED_RESPEC_REPORT.md`

- [ ] **Step 1: Write the failing report test**

Append this test to `tests/test_v1_2_failure_guided_respec.py`:

```python
def test_v1_2_report_renderer_states_readiness_without_admission() -> None:
    import importlib.util

    script = Path(__file__).resolve().parents[1] / "scripts" / "render_v1_2_failure_guided_scoped_respec_report.py"
    spec = importlib.util.spec_from_file_location("render_v1_2_failure_guided_scoped_respec_report", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    ranking = pd.DataFrame(
        [
            {
                "candidate_id": "qr_v12_volume_range_conviction_001",
                "variant_id": "thr_0p0_long_flat_cap_0p5_calm_vol_lte_1p5",
                "conservative_verdict": "research_watchlist",
                "stress_survival_count": 15,
                "stress_count": 15,
                "diagnostic_scenario_count": 1,
                "mean_sharpe": 0.8,
                "worst_sharpe": 0.2,
                "mean_max_dd": 0.2,
                "worst_max_dd": 0.3,
                "validation_mean_sharpe": 0.4,
                "blind_mean_sharpe": 0.5,
                "robustness_labels": "asset_exclusion_fragility",
            }
        ]
    )
    blocked = ranking.assign(conservative_verdict="blocked_pending_new_hypotheses", stress_survival_count=12)

    assert module._readiness_verdict(ranking) == "research_v1_2_failure_guided_candidate_replicated_pending_manual_review"
    assert module._readiness_verdict(blocked) == "research_v1_2_failure_guided_candidate_not_found"

    report = module._render(
        export_manifest={
            "candidate_count": 12,
            "single_factor_count": 9,
            "bundle_count": 3,
            "scope_contract": {"intended_scope": "BTCUSDT_4h", "out_of_scope_policy": "diagnostic_only"},
            "excluded_research10_survivor": {
                "candidate_id": "qr_v09d_funding_return_long_001",
                "variant_id": "thr_0p0_long_short_cap_0p5_none",
                "formula_family": "funding_return_long_horizon",
            },
        },
        candidates=[
            {
                "candidate_id": "qr_v12_volume_range_conviction_001",
                "formula_family": "volume_conviction_hardening",
                "formula": "zscore(div(corr(sub(close,open),volume,72),div(sub(max(high,48),min(low,48)),close)),96)",
            }
        ],
        btc_review_summary={"candidate_count": 144, "verdict_counts": {"research_watchlist": 3}},
        eth_review_summary={"candidate_count": 144, "verdict_counts": {"blocked_by_conservative_rules": 100}},
        correlation_summary={"bundle_count": 3, "bundle_verdict_counts": {"diversified_enough_for_research": 2}},
        robustness_summary={"detail_row_count": 10980, "scenario_summary_count": 960, "variant_count": 60},
        ranking=ranking,
        memory_manifest={"input_rows": 60, "failure_count": 59, "cluster_count": 20},
        readiness="research_v1_2_failure_guided_candidate_replicated_pending_manual_review",
    )

    assert "Research v1.2 Failure-Guided Scoped Candidate Re-Spec Report" in report
    assert "qr_v09d_funding_return_long_001" in report
    assert "qr_v12_volume_range_conviction_001" in report
    assert "research_v1_2_failure_guided_candidate_replicated_pending_manual_review" in report
    assert "not factor admission" in report
    assert "No RandyPortfolio implementation" in report
```

- [ ] **Step 2: Run the report test to verify it fails**

Run:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest tests/test_v1_2_failure_guided_respec.py::test_v1_2_report_renderer_states_readiness_without_admission -q
```

Expected: FAIL because `scripts/render_v1_2_failure_guided_scoped_respec_report.py` does not exist.

- [ ] **Step 3: Implement the report renderer**

Create `scripts/render_v1_2_failure_guided_scoped_respec_report.py`. Use the same path style as the v1.1 renderer:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

EXPORT_DIR = ROOT / "reports/factor_candidate_exports/research_v1_2_failure_guided_scoped_respec"
MEMORY_DIR = ROOT / "reports/failure_memory/research_v1_2_failure_guided_respec"
REPORT_PATH = ROOT / "docs/RESEARCH_V1_2_FAILURE_GUIDED_SCOPED_RESPEC_REPORT.md"
```

Implement `_readiness_verdict` exactly as:

```python
def _readiness_verdict(ranking: pd.DataFrame) -> str:
    if ranking.empty:
        return "research_v1_2_failure_guided_candidate_not_found"
    passed = ranking[ranking["conservative_verdict"] == "research_watchlist"]
    if passed.empty:
        return "research_v1_2_failure_guided_candidate_not_found"
    return "research_v1_2_failure_guided_candidate_replicated_pending_manual_review"
```

The `_render(...)` function must include these sections:

- Title: `# Research v1.2 Failure-Guided Scoped Candidate Re-Spec Report`
- Boundary sentence: research-only, not factor admission, not runtime publishing, not RandyPortfolio, not live execution.
- Objective: re-spec a narrow non-funding cohort from v1.1 failure memory after the v1.1 clean negative result.
- Candidate export counts and excluded Research 1.0 survivor.
- BTC primary declared review summary.
- ETH/SOL/BNB/AVAX diagnostic review summaries if files exist.
- Correlation and redundancy summary.
- Scope-aware robustness summary.
- A table of passed candidates, or a table of best blocked near misses.
- Failure memory manifest counts.
- Readiness verdict.
- Verification checklist.
- Boundary confirmation.

Use helper functions `_json`, `_jsonl`, `_read_csv`, `_fmt_counts`, `_num`, `_stress_survival`, `_rel`, and
`_find_sibling_repo` copied and trimmed from `scripts/render_v1_1_independent_replication_report.py`.

- [ ] **Step 4: Run the report test to verify it passes**

Run:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest tests/test_v1_2_failure_guided_respec.py::test_v1_2_report_renderer_states_readiness_without_admission -q
```

Expected: `1 passed`.

- [ ] **Step 5: Run all v1.2 focused tests**

Run:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest tests/test_v1_2_failure_guided_respec.py -q
```

Expected: all v1.2 tests pass.

- [ ] **Step 6: Commit the report renderer**

Run:

```bash
git add scripts/render_v1_2_failure_guided_scoped_respec_report.py tests/test_v1_2_failure_guided_respec.py
git commit -m "Add Research v1.2 report renderer"
```

## Task 4: Generate v1.2 Research Artifacts

**Files:**
- Generate ignored QuantumRandy reports under `reports/factor_candidate_exports/research_v1_2_failure_guided_scoped_respec`
- Generate ignored RandysLab reports under `reports/factor_candidate_*/research_v1_2_*`
- Generate ignored QuantumRandy failure memory under `reports/failure_memory/research_v1_2_failure_guided_respec`
- Generate tracked report: `docs/RESEARCH_V1_2_FAILURE_GUIDED_SCOPED_RESPEC_REPORT.md`

- [ ] **Step 1: Export v1.2 candidates**

Run in QuantumRandy:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/export_v1_2_failure_guided_scoped_respec.py \
  --out reports/factor_candidate_exports/research_v1_2_failure_guided_scoped_respec
```

Expected output includes:

```text
v1.2 failure-guided scoped candidate re-spec export: candidates=12 single_factors=9 bundles=3
```

- [ ] **Step 2: Run BTC/ETH/SOL/BNB/AVAX sensitivity sweeps**

Run in RandysLab. Keep the volatility-cap argument quoted because zsh treats parentheses as glob syntax:

```bash
for spec in \
  "BTCUSDT:data/BTCUSDT_4h.csv:data/BTCUSDT_funding.csv:btc_primary" \
  "ETHUSDT:data/ETHUSDT_4h.csv:data/ETHUSDT_funding.csv:eth_diagnostic" \
  "SOLUSDT:data/SOLUSDT_4h.csv:data/SOLUSDT_funding.csv:sol_diagnostic" \
  "BNBUSDT:data/BNBUSDT_4h.csv:data/BNBUSDT_funding.csv:bnb_diagnostic" \
  "AVAXUSDT:data/AVAXUSDT_4h.csv:data/AVAXUSDT_funding.csv:avax_diagnostic"; do
  IFS=: read -r symbol ohlcv funding label <<< "$spec"
  /Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/sweep_factor_candidates.py \
    --config configs/strict4h.yaml \
    --candidates ../QuantumRandy/reports/factor_candidate_exports/research_v1_2_failure_guided_scoped_respec/factor_candidates.jsonl \
    --out "reports/factor_candidate_sensitivity/research_v1_2_${label}" \
    --asset "${symbol}:${ohlcv}:${funding}" \
    --window training --window validation --window blind \
    --threshold 0.0 --threshold 0.5 --threshold 1.0 \
    --signal-mode long_flat --signal-mode long_short \
    --exposure-cap 0.5 --exposure-cap 1.0 \
    --volatility-cap 'calm_vol_lte_1p5:zscore(std(close,48),144):1.5'
done
```

Expected: each command exits 0 and prints `artifact_type` as `randyslab_factor_candidate_sensitivity`.

- [ ] **Step 3: Review BTC/ETH/SOL/BNB/AVAX sensitivity**

Run in RandysLab:

```bash
for label in btc_primary eth_diagnostic sol_diagnostic bnb_diagnostic avax_diagnostic; do
  /Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/review_factor_candidate_sensitivity.py \
    --detail-csv "reports/factor_candidate_sensitivity/research_v1_2_${label}/factor_candidate_sensitivity_detail.csv" \
    --out "reports/factor_candidate_review/research_v1_2_${label}" \
    --scope-mode declared
done
```

Expected: each command exits 0 and prints JSON containing `verdict_counts`.

- [ ] **Step 4: Run BTC correlation review**

Run in RandysLab:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/review_factor_candidate_correlation.py \
  --config configs/strict4h.yaml \
  --candidates ../QuantumRandy/reports/factor_candidate_exports/research_v1_2_failure_guided_scoped_respec/factor_candidates.jsonl \
  --out reports/factor_candidate_correlation/research_v1_2_btc \
  --symbol BTCUSDT \
  --ohlcv-csv data/BTCUSDT_4h.csv \
  --funding-csv data/BTCUSDT_funding.csv \
  --high-corr-threshold 0.80
```

Expected: output JSON includes `bundle_count: 3`.

- [ ] **Step 5: Verify the fixed v1.2 robustness variant cohort exists in BTC primary review**

Run in RandysLab:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 - <<'PY'
import pandas as pd
review = pd.read_csv('reports/factor_candidate_review/research_v1_2_btc_primary/factor_candidate_review.csv').fillna('')
required = {
    'thr_0p0_long_flat_cap_0p5_calm_vol_lte_1p5',
    'thr_0p0_long_short_cap_0p5_calm_vol_lte_1p5',
    'thr_0p0_long_flat_cap_1p0_calm_vol_lte_1p5',
    'thr_0p5_long_short_cap_0p5_calm_vol_lte_1p5',
    'thr_1p0_long_short_cap_1p0_calm_vol_lte_1p5',
}
available = set(review['variant_id'].dropna().astype(str))
missing = sorted(required - available)
print('review_rows', len(review))
print('required_variant_count', len(required))
print('missing_variants', missing)
assert not missing
PY
```

Expected: `missing_variants []`.

- [ ] **Step 6: Run scope-aware robustness gauntlet**

Run in RandysLab:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/run_watchlist_robustness_gauntlet.py \
  --config configs/strict4h.yaml \
  --candidates ../QuantumRandy/reports/factor_candidate_exports/research_v1_2_failure_guided_scoped_respec/factor_candidates.jsonl \
  --review-csv reports/factor_candidate_review/research_v1_2_btc_primary/factor_candidate_review.csv \
  --out reports/factor_candidate_robustness/research_v1_2_failure_guided_respec \
  --variant-id thr_0p0_long_flat_cap_0p5_calm_vol_lte_1p5 \
  --variant-id thr_0p0_long_short_cap_0p5_calm_vol_lte_1p5 \
  --variant-id thr_0p0_long_flat_cap_1p0_calm_vol_lte_1p5 \
  --variant-id thr_0p5_long_short_cap_0p5_calm_vol_lte_1p5 \
  --variant-id thr_1p0_long_short_cap_1p0_calm_vol_lte_1p5
```

Expected: output JSON includes `variant_count: 60` because the export has `12` candidates and the fixed cohort has `5`
variants.

- [ ] **Step 7: Build v1.2 failure memory**

Run in QuantumRandy:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/build_v1_2_failure_guided_respec_memory.py \
  --ranking-csv ../RandysLab-STRICT4H/reports/factor_candidate_robustness/research_v1_2_failure_guided_respec/watchlist_robustness_variant_ranking.csv \
  --source-robustness-dir reports/factor_candidate_robustness/research_v1_2_failure_guided_respec \
  --out reports/failure_memory/research_v1_2_failure_guided_respec
```

Expected: the command exits 0 and prints a failure-row count with `input rows: 60`.

- [ ] **Step 8: Render v1.2 report**

Run in QuantumRandy:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/render_v1_2_failure_guided_scoped_respec_report.py
```

Expected output is one of:

```text
Wrote /Users/rosebrain-2/Projects/Quant/QuantumRandy/docs/RESEARCH_V1_2_FAILURE_GUIDED_SCOPED_RESPEC_REPORT.md
readiness=research_v1_2_failure_guided_candidate_replicated_pending_manual_review
```

or:

```text
Wrote /Users/rosebrain-2/Projects/Quant/QuantumRandy/docs/RESEARCH_V1_2_FAILURE_GUIDED_SCOPED_RESPEC_REPORT.md
readiness=research_v1_2_failure_guided_candidate_not_found
```

## Task 5: Documentation, Verification, and GitHub

**Files:**
- Modify: `docs/RESEARCH_V1_2_FAILURE_GUIDED_SCOPED_RESPEC_REPORT.md`
- Modify: `docs/README.md`
- Modify: `docs/PROJECT_LOG.md`

- [ ] **Step 1: Add docs index entry**

Modify `docs/README.md` to include:

```markdown
- `RESEARCH_V1_2_FAILURE_GUIDED_SCOPED_RESPEC_REPORT.md`: failure-guided non-funding scoped candidate re-spec after
  the v1.1 clean negative result.
```

- [ ] **Step 2: Add project log entry**

Add a top entry to `docs/PROJECT_LOG.md`. If the rendered report prints
`research_v1_2_failure_guided_candidate_replicated_pending_manual_review`, use:

```markdown
## 2026-07-03 Research v1.2 Failure-Guided Scoped Candidate Re-Spec

Completed the research-only v1.2 failure-guided scoped candidate re-spec pass.

- Report: `docs/RESEARCH_V1_2_FAILURE_GUIDED_SCOPED_RESPEC_REPORT.md`.
- Current Research 1.0 survivor excluded: `qr_v09d_funding_return_long_001::thr_0p0_long_short_cap_0p5_none`.
- Candidate cohort: `12` non-funding current-DSL candidates, `BTCUSDT_4h`,
  `out_of_scope_policy=diagnostic_only`.
- RandysLab artifacts: BTC primary declared review, ETH/SOL/BNB/AVAX diagnostics, BTC bundle correlation, and
  scope-aware robustness gauntlet.
- Readiness verdict: `research_v1_2_failure_guided_candidate_replicated_pending_manual_review`.

Boundary preserved: no RandyPortfolio implementation, no live trading, no exchange private keys, no runtime factor
publishing, no automatic factor admission, no new formula base fields, no production regime labels, and no selector
evidence61.
```

If the rendered report prints `research_v1_2_failure_guided_candidate_not_found`, use the same entry with this readiness
bullet:

```markdown
- Readiness verdict: `research_v1_2_failure_guided_candidate_not_found`.
```

Only one readiness bullet should remain in the new log entry.

- [ ] **Step 3: Run QuantumRandy focused tests**

Run:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest tests/test_v1_2_failure_guided_respec.py tests/test_v1_1_independent_replication.py tests/test_research10_replication_memory.py -q
```

Expected: all tests pass.

- [ ] **Step 4: Run RandysLab focused tests**

Run:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest tests/test_formula_candidates.py tests/test_factor_candidate_robustness.py tests/test_factor_candidate_correlation.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Run both full test suites**

Run in QuantumRandy:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest -q
```

Expected: all tests pass.

Run in RandysLab:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 6: Run artifact invariant check**

Run in QuantumRandy:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 - <<'PY'
import json
from pathlib import Path
import pandas as pd

export_manifest = json.loads(Path('reports/factor_candidate_exports/research_v1_2_failure_guided_scoped_respec/factor_candidate_export_manifest.json').read_text())
assert export_manifest['research_checkpoint'] == 'v1.2'
assert export_manifest['candidate_count'] == 12
assert export_manifest['single_factor_count'] == 9
assert export_manifest['bundle_count'] == 3
assert export_manifest['excluded_research10_survivor']['candidate_id'] == 'qr_v09d_funding_return_long_001'

ranking_path = Path('../RandysLab-STRICT4H/reports/factor_candidate_robustness/research_v1_2_failure_guided_respec/watchlist_robustness_variant_ranking.csv')
assert ranking_path.exists()
ranking = pd.read_csv(ranking_path).fillna('')
assert len(ranking) == 60
assert 'qr_v09d_funding_return_long_001' not in set(ranking['candidate_id'])
passed = ranking[ranking['conservative_verdict'].eq('research_watchlist')]
for _, row in passed.iterrows():
    assert int(row['stress_survival_count']) == int(row['stress_count'])
    assert int(row.get('diagnostic_scenario_count', 0)) >= 0

memory_manifest = json.loads(Path('reports/failure_memory/research_v1_2_failure_guided_respec/failure_memory_manifest.json').read_text())
assert memory_manifest['input_rows'] >= memory_manifest['failure_count']

report = Path('docs/RESEARCH_V1_2_FAILURE_GUIDED_SCOPED_RESPEC_REPORT.md').read_text()
assert 'Research v1.2 Failure-Guided Scoped Candidate Re-Spec Report' in report
assert 'No RandyPortfolio implementation' in report
assert 'No live trading' in report
assert (
    'research_v1_2_failure_guided_candidate_replicated_pending_manual_review' in report
    or 'research_v1_2_failure_guided_candidate_not_found' in report
)
print('v1.2 invariants OK')
PY
```

Expected: `v1.2 invariants OK`.

- [ ] **Step 7: Boundary scan**

Run in QuantumRandy:

```bash
rg -n "RandyPortfolio|live trading|exchange private keys|runtime factor publishing|automatic factor admission|selector evidence61|production regime|production runtime regime" \
  quantumrandy/v12_failure_guided_respec_export.py \
  quantumrandy/v12_failure_guided_respec_memory.py \
  scripts/export_v1_2_failure_guided_scoped_respec.py \
  scripts/build_v1_2_failure_guided_respec_memory.py \
  scripts/render_v1_2_failure_guided_scoped_respec_report.py \
  tests/test_v1_2_failure_guided_respec.py \
  docs/RESEARCH_V1_2_FAILURE_GUIDED_SCOPED_RESPEC_REPORT.md \
  docs/README.md \
  docs/PROJECT_LOG.md
```

Expected: matches are boundary statements only, not new implementation paths.

Run in RandysLab:

```bash
rg -n "RandyPortfolio|live trading|exchange private keys|runtime factor publishing|automatic factor admission|selector evidence61|production regime|production runtime regime" randyslab scripts tests
```

Expected: matches are existing boundary statements only, not new implementation paths.

- [ ] **Step 8: Commit QuantumRandy tracked outputs**

Run in QuantumRandy:

```bash
git status --short
git add docs/README.md docs/PROJECT_LOG.md docs/RESEARCH_V1_2_FAILURE_GUIDED_SCOPED_RESPEC_REPORT.md
git commit -m "Record Research v1.2 failure-guided respec"
```

Expected: commit succeeds. Ignored `reports/` artifacts remain untracked.

- [ ] **Step 9: Commit RandysLab only if source changed**

Run in RandysLab:

```bash
git status --short
```

If only ignored `reports/` artifacts changed, do not commit RandysLab. If a legitimate source or test fix was required
during execution, first inspect the exact changed paths:

```bash
git status --short
```

Then commit only the actual source/test files printed by `git status --short`. For example, if the only legitimate fix
is in `randyslab/factor_candidate_robustness.py` and `tests/test_factor_candidate_robustness.py`, run:

```bash
git add randyslab/factor_candidate_robustness.py tests/test_factor_candidate_robustness.py
git commit -m "Fix Research v1.2 strict review support"
```

- [ ] **Step 10: Push to GitHub**

Run in any repository with a new commit:

```bash
git push
```

Expected: `main -> main` push succeeds.

## Success Criteria

Research v1.2 is complete when:

- QuantumRandy has a committed v1.2 report.
- The v1.2 export excludes `qr_v09d_funding_return_long_001` and direct `funding_rate` formulas.
- The v1.2 cohort includes failure-guided volume-conviction, trend-quality, and crash-resilient participation families.
- RandysLab has generated BTC primary declared review, ETH/SOL/BNB/AVAX diagnostics, BTC correlation, and scope-aware
  robustness artifacts.
- v1.2 failure memory is generated from robustness ranking.
- Readiness verdict is one of:
  - `research_v1_2_failure_guided_candidate_replicated_pending_manual_review`
  - `research_v1_2_failure_guided_candidate_not_found`
- Full QuantumRandy and RandysLab tests pass.
- Boundary remains intact: no RandyPortfolio, no live trading, no exchange private keys, no runtime publishing, no
  automatic factor admission, no new formula base fields, no production regime labels, no selector evidence61.

## Notes for the Implementer

- Do not treat a v1.2 survivor as a production factor.
- Do not weaken strict judge thresholds to force a pass.
- Do not add new public crypto-native fields in this plan.
- If no v1.2 candidate survives, the correct output is a clean negative result with failure memory.
- If a candidate survives only because out-of-scope rows failed but BTC scope rows passed, that is acceptable only when
  `scope_hard_gate=True` rows all survive and out-of-scope rows remain diagnostic labels.
