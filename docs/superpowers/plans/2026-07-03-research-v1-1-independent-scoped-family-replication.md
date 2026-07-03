# Research v1.1 Independent Scoped Family Replication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a research-only v1.1 checkpoint that tries to replicate a second independent scoped candidate family, excluding the current funding-return Research 1.0 survivor.

**Architecture:** QuantumRandy owns the v1.1 independent candidate export, replication memory, and final report. RandysLab reuses the existing declared-scope strict judge, correlation review, and scope-aware robustness gauntlet to evaluate those exported candidates. The checkpoint succeeds only if at least one non-funding candidate/variant survives every BTCUSDT hard stress while all out-of-scope assets remain diagnostic-only.

**Tech Stack:** Python 3, pandas, pytest, QuantumRandy JSONL/CSV/Markdown export helpers, RandysLab strict4h config, existing RandysLab factor-candidate sensitivity/review/correlation/robustness CLIs.

---

## Current State

- Research v1.0 has one replicated scoped research candidate:
  `qr_v09d_funding_return_long_001::thr_0p0_long_short_cap_0p5_none`.
- That candidate is research-only and pending manual review. It is not factor admission, runtime publishing, live trading, or RandyPortfolio.
- Research v1.1 should not tune that same funding-return family. Its purpose is to find or reject an independent family.
- The v1.1 cohort must use current admitted formula fields only: `open`, `high`, `low`, `close`, `volume`, and `funding_rate`.
- No new formula base fields, runtime factors, production regime labels, exchange private keys, live trading, selector evidence61, or RandyPortfolio implementation are in scope.

## File Structure

### QuantumRandy

- Create `quantumrandy/v11_independent_replication_export.py`
  - Defines the v1.1 independent candidate cohort.
  - Excludes `funding_return_long_horizon`, direct `funding_rate` formulas, and bundles containing the v1.0 survivor.
  - Writes JSONL, CSV, manifest, Markdown export, and events.
- Create `scripts/export_v1_1_independent_scoped_candidates.py`
  - Thin CLI wrapper around the export module.
- Create `quantumrandy/v11_independent_replication_memory.py`
  - Converts RandysLab v1.1 robustness rankings into failure memory rows.
  - Preserves passed rows in the in-memory return value but writes only failures to `failure_memory.csv`, following existing failure-memory behavior.
  - Adds labels for `independent_family_replication`, `non_funding_family`, and replication stress failures.
- Create `scripts/build_v1_1_independent_replication_memory.py`
  - CLI wrapper around the v1.1 memory writer.
- Create `scripts/render_v1_1_independent_replication_report.py`
  - Renders the final v1.1 report from export, RandysLab review/correlation/robustness artifacts, and v1.1 failure memory.
- Create `tests/test_v1_1_independent_replication.py`
  - Covers export safety/schema, exclusion of the funding survivor, memory behavior, and report readiness verdicts.
- Create `docs/RESEARCH_V1_1_INDEPENDENT_SCOPED_FAMILY_REPLICATION_REPORT.md`
  - Final tracked report after artifacts are generated.
- Modify `docs/README.md`
  - Add the new v1.1 report to the research reports list.
- Modify `docs/PROJECT_LOG.md`
  - Add a top entry after the v1.1 report is rendered.

### RandysLab

- No source changes are expected.
- Reuse existing scripts:
  - `scripts/sweep_factor_candidates.py`
  - `scripts/review_factor_candidate_sensitivity.py`
  - `scripts/review_factor_candidate_correlation.py`
  - `scripts/run_watchlist_robustness_gauntlet.py`
- Generate ignored research artifacts under:
  - `reports/factor_candidate_sensitivity/research_v1_1_btc_primary`
  - `reports/factor_candidate_review/research_v1_1_btc_primary`
  - `reports/factor_candidate_sensitivity/research_v1_1_eth_diagnostic`
  - `reports/factor_candidate_review/research_v1_1_eth_diagnostic`
  - `reports/factor_candidate_sensitivity/research_v1_1_sol_diagnostic`
  - `reports/factor_candidate_review/research_v1_1_sol_diagnostic`
  - `reports/factor_candidate_sensitivity/research_v1_1_bnb_diagnostic`
  - `reports/factor_candidate_review/research_v1_1_bnb_diagnostic`
  - `reports/factor_candidate_sensitivity/research_v1_1_avax_diagnostic`
  - `reports/factor_candidate_review/research_v1_1_avax_diagnostic`
  - `reports/factor_candidate_correlation/research_v1_1_btc`
  - `reports/factor_candidate_robustness/research_v1_1_independent_replication`

## Task 1: Export Independent v1.1 Candidate Cohort

**Files:**
- Create: `quantumrandy/v11_independent_replication_export.py`
- Create: `scripts/export_v1_1_independent_scoped_candidates.py`
- Test: `tests/test_v1_1_independent_replication.py`

- [ ] **Step 1: Write the failing export test**

Add this to `tests/test_v1_1_independent_replication.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from quantumrandy.expression import parse_formula
from quantumrandy.v11_independent_replication_export import (
    V11_BUNDLE_CANDIDATES,
    V11_SINGLE_FACTOR_CANDIDATES,
    export_v1_1_independent_scoped_candidates,
)


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_export_v1_1_independent_candidates_excludes_current_funding_survivor(tmp_path) -> None:
    out = tmp_path / "v11_export"

    manifest = export_v1_1_independent_scoped_candidates(out)

    assert manifest["artifact_type"] == "quantumrandy_factor_candidate_export_manifest"
    assert manifest["research_checkpoint"] == "v1.1"
    assert manifest["candidate_family"] == "independent_scoped_family_replication"
    assert manifest["scope_contract"]["intended_scope"] == "BTCUSDT_4h"
    assert manifest["scope_contract"]["out_of_scope_policy"] == "diagnostic_only"
    assert manifest["excluded_research10_survivor"] == {
        "candidate_id": "qr_v09d_funding_return_long_001",
        "variant_id": "thr_0p0_long_short_cap_0p5_none",
        "formula_family": "funding_return_long_horizon",
    }
    assert manifest["candidate_count"] == len(V11_SINGLE_FACTOR_CANDIDATES) + len(V11_BUNDLE_CANDIDATES)
    assert manifest["single_factor_count"] == 8
    assert manifest["bundle_count"] == 2
    assert manifest["safety"]["research_only"] is True
    assert manifest["safety"]["not_runtime_publish_payload"] is True
    assert manifest["safety"]["does_not_auto_admit_factors"] is True

    records = _jsonl(out / "factor_candidates.jsonl")
    bundle_records = _jsonl(out / "bundle_candidates.jsonl")
    assert len(records) == 10
    assert len(bundle_records) == 2

    disallowed_candidate_ids = {"qr_v09d_funding_return_long_001", "qr_v09d_bundle_funding_confirmation_001"}
    disallowed_formula_fragments = {"funding_rate"}
    allowed_fields = {"open", "high", "low", "close", "volume"}

    for record in records:
        assert record["artifact_type"] == "quantumrandy_factor_candidate_export"
        assert record["research_checkpoint"] == "v1.1"
        assert record["research_only"] is True
        assert record["not_runtime_publish_payload"] is True
        assert record["intended_scope"] == "BTCUSDT_4h"
        assert record["out_of_scope_policy"] == "diagnostic_only"
        assert record["candidate_id"] not in disallowed_candidate_ids
        assert record["candidate_tier"] in {"independent_candidate", "independent_bundle"}
        assert set(record["required_features"]).issubset(allowed_fields)
        formulas = [record["formula"], *record.get("component_formulas", [])]
        for formula in formulas:
            parse_formula(formula)
            assert not any(fragment in formula for fragment in disallowed_formula_fragments)

    csv = pd.read_csv(out / "factor_candidates.csv")
    assert len(csv) == 10
    assert set(csv["intended_scope"]) == {"BTCUSDT_4h"}
    assert set(csv["out_of_scope_policy"]) == {"diagnostic_only"}

    report = (out / "FACTOR_CANDIDATE_EXPORT.md").read_text(encoding="utf-8")
    assert "Research v1.1" in report
    assert "independent scoped family replication" in report
    assert "not a runtime publish payload" in report
```

- [ ] **Step 2: Run the export test to verify it fails**

Run:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest tests/test_v1_1_independent_replication.py::test_export_v1_1_independent_candidates_excludes_current_funding_survivor -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'quantumrandy.v11_independent_replication_export'`.

- [ ] **Step 3: Implement the export module**

Create `quantumrandy/v11_independent_replication_export.py` with this structure:

```python
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
        "hypothesis": "Volume conviction, liquidity-adjusted momentum, and volatility-adjusted trend may separate BTC direction from noisy participation.",
    },
    {
        "candidate_id": "qr_v11_bundle_trend_quality_001",
        "formula_family": "scoped_equal_weight_bundle",
        "component_candidate_ids": [
            "qr_v11_trend_efficiency_001",
            "qr_v11_trend_persistence_001",
            "qr_v11_range_position_001",
        ],
        "hypothesis": "Trend efficiency, persistence, and range position may identify higher-quality BTC trend states without funding features.",
    },
]
```

Add export functions by mirroring `quantumrandy/v09d_discovery_export.py` with these exact differences:

```python
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
            "created_from_plan": "docs/superpowers/plans/2026-07-03-research-v1-1-independent-scoped-family-replication.md",
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
```

Implement helper functions `_single_records`, `_bundle_records`, `_record`, `_jsonl`, `_csv_frame`, `_required_features`, `_safety`, and `_portfolio_contract` using the same shapes as `v09d_discovery_export.py`. Set `"candidate_tier"` to `"independent_bundle"` for bundle records and `"independent_candidate"` for single records. In `_record`, raise `ValueError` if `"funding_rate"` appears in the formula or any component formula.

- [ ] **Step 4: Add the export CLI**

Create `scripts/export_v1_1_independent_scoped_candidates.py`:

```python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantumrandy.v11_independent_replication_export import export_v1_1_independent_scoped_candidates


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Research v1.1 independent scoped family replication candidates.")
    parser.add_argument(
        "--out",
        default="reports/factor_candidate_exports/research_v1_1_independent_scoped_family_replication",
        help="Output directory for JSONL, bundle JSONL, CSV, manifest, and Markdown report.",
    )
    args = parser.parse_args()
    manifest = export_v1_1_independent_scoped_candidates(args.out)
    print(
        "v1.1 independent scoped family replication export: "
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
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest tests/test_v1_1_independent_replication.py::test_export_v1_1_independent_candidates_excludes_current_funding_survivor -q
```

Expected: `1 passed`.

- [ ] **Step 6: Commit the export layer**

Run:

```bash
git add quantumrandy/v11_independent_replication_export.py scripts/export_v1_1_independent_scoped_candidates.py tests/test_v1_1_independent_replication.py
git commit -m "Add Research v1.1 independent candidate export"
```

## Task 2: Build v1.1 Replication Failure Memory

**Files:**
- Create: `quantumrandy/v11_independent_replication_memory.py`
- Create: `scripts/build_v1_1_independent_replication_memory.py`
- Modify: `tests/test_v1_1_independent_replication.py`

- [ ] **Step 1: Write the failing memory test**

Append this test to `tests/test_v1_1_independent_replication.py`:

```python
def test_v1_1_failure_memory_records_only_failed_independent_rankings(tmp_path) -> None:
    from quantumrandy.v11_independent_replication_memory import (
        build_v1_1_independent_replication_memory_rows,
        write_v1_1_independent_replication_failure_memory,
    )

    ranking_csv = tmp_path / "watchlist_robustness_variant_ranking.csv"
    pd.DataFrame(
        [
            {
                "candidate_id": "qr_v11_volume_conviction_001",
                "formula": "zscore(corr(sub(close,open),volume,48),72)",
                "variant_id": "thr_0p0_long_flat_cap_0p5_none",
                "conservative_verdict": "blocked_pending_new_hypotheses",
                "failure_reasons": "weak_validation_window",
                "diagnostic_failure_reasons": "low_mean_sharpe",
                "robustness_labels": "fee_fragility|asset_exclusion_fragility",
                "stress_survival_count": 14,
                "stress_count": 15,
                "stress_survival_score": 0.93333333,
                "diagnostic_scenario_count": 1,
                "mean_sharpe": 0.8,
                "validation_mean_sharpe": -0.1,
                "blind_mean_sharpe": 0.5,
                "mean_max_dd": 0.2,
                "worst_max_dd": 0.4,
            },
            {
                "candidate_id": "qr_v11_range_position_001",
                "formula": "zscore(div(sub(close,sma(close,48)),sub(max(high,48),min(low,48))),96)",
                "variant_id": "thr_0p0_long_short_cap_0p5_none",
                "conservative_verdict": "research_watchlist",
                "failure_reasons": "",
                "diagnostic_failure_reasons": "low_mean_sharpe",
                "robustness_labels": "sol_avax_concentration",
                "stress_survival_count": 15,
                "stress_count": 15,
                "stress_survival_score": 1.0,
                "diagnostic_scenario_count": 1,
                "mean_sharpe": 0.7,
                "validation_mean_sharpe": 0.3,
                "blind_mean_sharpe": 0.4,
                "mean_max_dd": 0.2,
                "worst_max_dd": 0.3,
            },
        ]
    ).to_csv(ranking_csv, index=False)

    rows = build_v1_1_independent_replication_memory_rows(
        ranking_csv,
        source_robustness_dir="reports/factor_candidate_robustness/research_v1_1_independent_replication",
    )

    assert len(rows) == 2
    by_id = {row["candidate_id"]: row for row in rows}
    failed = by_id["qr_v11_volume_conviction_001::thr_0p0_long_flat_cap_0p5_none"]
    assert failed["passed"] is False
    assert failed["candidate_family"] == "research_v1_1_independent_replication_variant"
    assert failed["intended_scope"] == "BTCUSDT_4h"
    assert failed["out_of_scope_policy"] == "diagnostic_only"
    assert failed["stress_survival"] == "14/15"
    assert "independent_family_replication" in failed["failure_labels"]
    assert "replication_stress_fragility" in failed["failure_labels"]
    assert "weak_validation_window" in failed["failure_labels"]

    survivor = by_id["qr_v11_range_position_001::thr_0p0_long_short_cap_0p5_none"]
    assert survivor["passed"] is True
    assert "replication_stress_fragility" not in survivor["failure_labels"]

    out = tmp_path / "failure_memory"
    manifest = write_v1_1_independent_replication_failure_memory(
        ranking_csv,
        out,
        source_robustness_dir="reports/factor_candidate_robustness/research_v1_1_independent_replication",
    )

    assert manifest["artifact_type"] == "quantumrandy_failure_memory"
    assert manifest["input_rows"] == 2
    assert manifest["failure_count"] == 1
    memory = pd.read_csv(out / "failure_memory.csv")
    assert memory.iloc[0]["candidate_id"] == "qr_v11_volume_conviction_001::thr_0p0_long_flat_cap_0p5_none"
```

- [ ] **Step 2: Run the memory test to verify it fails**

Run:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest tests/test_v1_1_independent_replication.py::test_v1_1_failure_memory_records_only_failed_independent_rankings -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'quantumrandy.v11_independent_replication_memory'`.

- [ ] **Step 3: Implement the v1.1 memory module**

Create `quantumrandy/v11_independent_replication_memory.py` by adapting `quantumrandy/research10_replication_memory.py`. Use these constants and differences:

```python
V11_REPLICATION_DESCRIPTION = "Research v1.1 independent scoped family replication robustness variant."
V11_REPLICATION_FAILURE_MODE = (
    "Independent non-funding candidate variants may fail Research v1.1 replication through BTC scope stress fragility, "
    "weak validation or blind windows, fee/funding sensitivity, crash drawdown, or out-of-scope asset concentration."
)
```

For each ranking row, write:

```python
{
    "candidate_id": f"{candidate_id}::{variant_id}",
    "formula": raw.get("formula", ""),
    "candidate_family": "research_v1_1_independent_replication_variant",
    "description": V11_REPLICATION_DESCRIPTION,
    "hypothesis": f"{candidate_id} independent v1.1 replication variant {variant_id}.",
    "expected_failure_mode": V11_REPLICATION_FAILURE_MODE,
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
```

The `_labels` function must include labels from `robustness_labels`, `failure_reasons`, and `diagnostic_failure_reasons`, then always add `independent_family_replication` and `non_funding_family`. Add `replication_stress_fragility` only when `stress_survival_score < 1.0`.

- [ ] **Step 4: Add the memory CLI**

Create `scripts/build_v1_1_independent_replication_memory.py`:

```python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantumrandy.v11_independent_replication_memory import write_v1_1_independent_replication_failure_memory


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Research v1.1 independent replication failure memory.")
    parser.add_argument("--ranking-csv", required=True)
    parser.add_argument("--source-robustness-dir", required=True)
    parser.add_argument("--out", default="reports/failure_memory/research_v1_1_independent_replication")
    args = parser.parse_args()
    manifest = write_v1_1_independent_replication_failure_memory(
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
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest tests/test_v1_1_independent_replication.py::test_v1_1_failure_memory_records_only_failed_independent_rankings -q
```

Expected: `1 passed`.

- [ ] **Step 6: Commit the memory layer**

Run:

```bash
git add quantumrandy/v11_independent_replication_memory.py scripts/build_v1_1_independent_replication_memory.py tests/test_v1_1_independent_replication.py
git commit -m "Add Research v1.1 replication memory"
```

## Task 3: Render v1.1 Readiness Report

**Files:**
- Create: `scripts/render_v1_1_independent_replication_report.py`
- Modify: `tests/test_v1_1_independent_replication.py`
- Later generated/modified: `docs/RESEARCH_V1_1_INDEPENDENT_SCOPED_FAMILY_REPLICATION_REPORT.md`

- [ ] **Step 1: Write the failing report test**

Append this test to `tests/test_v1_1_independent_replication.py`:

```python
def test_v1_1_report_renderer_states_readiness_without_admission() -> None:
    import importlib.util

    script = Path(__file__).resolve().parents[1] / "scripts" / "render_v1_1_independent_replication_report.py"
    spec = importlib.util.spec_from_file_location("render_v1_1_independent_replication_report", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    ranking = pd.DataFrame(
        [
            {
                "candidate_id": "qr_v11_volume_conviction_001",
                "variant_id": "thr_0p0_long_flat_cap_0p5_none",
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
    blocked = ranking.assign(conservative_verdict="blocked_pending_new_hypotheses", stress_survival_count=14)

    assert module._readiness_verdict(ranking) == "research_v1_1_independent_candidate_replicated_pending_manual_review"
    assert module._readiness_verdict(blocked) == "research_v1_1_independent_candidate_not_found"

    report = module._render(
        export_manifest={
            "candidate_count": 10,
            "single_factor_count": 8,
            "bundle_count": 2,
            "scope_contract": {"intended_scope": "BTCUSDT_4h", "out_of_scope_policy": "diagnostic_only"},
            "excluded_research10_survivor": {
                "candidate_id": "qr_v09d_funding_return_long_001",
                "variant_id": "thr_0p0_long_short_cap_0p5_none",
                "formula_family": "funding_return_long_horizon",
            },
        },
        candidates=[
            {
                "candidate_id": "qr_v11_volume_conviction_001",
                "formula_family": "volume_price_conviction",
                "formula": "zscore(corr(sub(close,open),volume,48),72)",
            }
        ],
        btc_review_summary={"candidate_count": 10, "verdict_counts": {"research_watchlist": 2}},
        eth_review_summary={"candidate_count": 10, "verdict_counts": {"blocked_by_conservative_rules": 8}},
        correlation_summary={"bundle_count": 2, "bundle_verdict_counts": {"diversified_enough_for_research": 2}},
        robustness_summary={"detail_row_count": 9000, "scenario_summary_count": 800, "variant_count": 50},
        ranking=ranking,
        memory_manifest={"input_rows": 50, "failure_count": 49, "cluster_count": 12},
        readiness="research_v1_1_independent_candidate_replicated_pending_manual_review",
    )

    assert "Research v1.1 Independent Scoped Family Replication Report" in report
    assert "qr_v09d_funding_return_long_001" in report
    assert "qr_v11_volume_conviction_001" in report
    assert "research_v1_1_independent_candidate_replicated_pending_manual_review" in report
    assert "not factor admission" in report
    assert "No RandyPortfolio implementation" in report
```

- [ ] **Step 2: Run the report test to verify it fails**

Run:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest tests/test_v1_1_independent_replication.py::test_v1_1_report_renderer_states_readiness_without_admission -q
```

Expected: FAIL because `scripts/render_v1_1_independent_replication_report.py` does not exist.

- [ ] **Step 3: Implement the report renderer**

Create `scripts/render_v1_1_independent_replication_report.py`. Use the same path style as `scripts/render_v0_9d_report.py`:

```python
ROOT = Path(__file__).resolve().parents[1]
EXPORT_DIR = ROOT / "reports/factor_candidate_exports/research_v1_1_independent_scoped_family_replication"
MEMORY_DIR = ROOT / "reports/failure_memory/research_v1_1_independent_replication"
REPORT_PATH = ROOT / "docs/RESEARCH_V1_1_INDEPENDENT_SCOPED_FAMILY_REPLICATION_REPORT.md"
```

Implement:

```python
def _readiness_verdict(ranking: pd.DataFrame) -> str:
    if ranking.empty:
        return "research_v1_1_independent_candidate_not_found"
    passed = ranking[ranking["conservative_verdict"] == "research_watchlist"]
    if passed.empty:
        return "research_v1_1_independent_candidate_not_found"
    return "research_v1_1_independent_candidate_replicated_pending_manual_review"
```

The `_render(...)` function must include these sections:

- Title: `# Research v1.1 Independent Scoped Family Replication Report`
- Boundary sentence: research-only, not factor admission, not runtime publishing, not RandyPortfolio, not live execution.
- Objective: find a second independent non-funding scoped family after the v1.0 funding-return survivor.
- Candidate export counts and excluded survivor.
- BTC primary declared review summary.
- ETH/SOL/BNB/AVAX diagnostic review summaries if files exist.
- Correlation and redundancy summary.
- Scope-aware robustness summary.
- A table of passed candidates, or a table of best blocked near misses.
- Failure memory manifest counts.
- Readiness verdict.
- Verification checklist.
- Boundary confirmation.

Use helper functions `_json`, `_jsonl`, `_read_csv`, `_counts`, `_fmt_counts`, `_num`, `_rel`, and `_find_sibling_repo` copied and trimmed from `render_v0_9d_report.py`.

- [ ] **Step 4: Run the report test to verify it passes**

Run:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest tests/test_v1_1_independent_replication.py::test_v1_1_report_renderer_states_readiness_without_admission -q
```

Expected: `1 passed`.

- [ ] **Step 5: Run all v1.1 focused tests**

Run:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest tests/test_v1_1_independent_replication.py -q
```

Expected: all v1.1 tests pass.

- [ ] **Step 6: Commit the report renderer**

Run:

```bash
git add scripts/render_v1_1_independent_replication_report.py tests/test_v1_1_independent_replication.py
git commit -m "Add Research v1.1 report renderer"
```

## Task 4: Generate v1.1 Research Artifacts

**Files:**
- Generate ignored QuantumRandy reports under `reports/factor_candidate_exports/research_v1_1_independent_scoped_family_replication`
- Generate ignored RandysLab reports under `reports/factor_candidate_*/research_v1_1_*`
- Generate ignored QuantumRandy failure memory under `reports/failure_memory/research_v1_1_independent_replication`
- Generate tracked report: `docs/RESEARCH_V1_1_INDEPENDENT_SCOPED_FAMILY_REPLICATION_REPORT.md`

- [ ] **Step 1: Export v1.1 candidates**

Run in QuantumRandy:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/export_v1_1_independent_scoped_candidates.py \
  --out reports/factor_candidate_exports/research_v1_1_independent_scoped_family_replication
```

Expected output includes:

```text
v1.1 independent scoped family replication export: candidates=10 single_factors=8 bundles=2
```

- [ ] **Step 2: Run BTC primary sensitivity**

Run in RandysLab:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/sweep_factor_candidates.py \
  --config configs/strict4h.yaml \
  --candidates ../QuantumRandy/reports/factor_candidate_exports/research_v1_1_independent_scoped_family_replication/factor_candidates.jsonl \
  --out reports/factor_candidate_sensitivity/research_v1_1_btc_primary \
  --asset BTCUSDT:data/BTCUSDT_4h.csv:data/BTCUSDT_funding.csv \
  --window training --window validation --window blind \
  --threshold 0.0 --threshold 0.5 --threshold 1.0 \
  --signal-mode long_flat --signal-mode long_short \
  --exposure-cap 0.5 --exposure-cap 1.0 \
  --volatility-cap calm_vol_lte_1p5:zscore(std(close,48),144):1.5
```

Expected: `artifact_type` is `randyslab_factor_candidate_sensitivity`.

- [ ] **Step 3: Review BTC primary sensitivity**

Run in RandysLab:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/review_factor_candidate_sensitivity.py \
  --detail-csv reports/factor_candidate_sensitivity/research_v1_1_btc_primary/factor_candidate_sensitivity_detail.csv \
  --out reports/factor_candidate_review/research_v1_1_btc_primary \
  --scope-mode declared
```

Expected: output JSON includes `verdict_counts`.

- [ ] **Step 4: Run ETH diagnostic sensitivity and review**

Run in RandysLab:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/sweep_factor_candidates.py \
  --config configs/strict4h.yaml \
  --candidates ../QuantumRandy/reports/factor_candidate_exports/research_v1_1_independent_scoped_family_replication/factor_candidates.jsonl \
  --out reports/factor_candidate_sensitivity/research_v1_1_eth_diagnostic \
  --asset ETHUSDT:data/ETHUSDT_4h.csv:data/ETHUSDT_funding.csv \
  --window training --window validation --window blind \
  --threshold 0.0 --threshold 0.5 --threshold 1.0 \
  --signal-mode long_flat --signal-mode long_short \
  --exposure-cap 0.5 --exposure-cap 1.0 \
  --volatility-cap calm_vol_lte_1p5:zscore(std(close,48),144):1.5

/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/review_factor_candidate_sensitivity.py \
  --detail-csv reports/factor_candidate_sensitivity/research_v1_1_eth_diagnostic/factor_candidate_sensitivity_detail.csv \
  --out reports/factor_candidate_review/research_v1_1_eth_diagnostic \
  --scope-mode declared
```

Expected: both commands exit 0.

- [ ] **Step 5: Run SOL/BNB/AVAX diagnostics**

Run in RandysLab:

```bash
for asset in SOLUSDT BNBUSDT AVAXUSDT; do
  lower=$(printf "%s" "$asset" | tr '[:upper:]' '[:lower:]' | sed 's/usdt$//')
  /Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/sweep_factor_candidates.py \
    --config configs/strict4h.yaml \
    --candidates ../QuantumRandy/reports/factor_candidate_exports/research_v1_1_independent_scoped_family_replication/factor_candidates.jsonl \
    --out "reports/factor_candidate_sensitivity/research_v1_1_${lower}_diagnostic" \
    --asset "${asset}:data/${asset}_4h.csv:data/${asset}_funding.csv" \
    --window training --window validation --window blind \
    --threshold 0.0 --threshold 0.5 --threshold 1.0 \
    --signal-mode long_flat --signal-mode long_short \
    --exposure-cap 0.5 --exposure-cap 1.0 \
    --volatility-cap calm_vol_lte_1p5:zscore(std(close,48),144):1.5
  /Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/review_factor_candidate_sensitivity.py \
    --detail-csv "reports/factor_candidate_sensitivity/research_v1_1_${lower}_diagnostic/factor_candidate_sensitivity_detail.csv" \
    --out "reports/factor_candidate_review/research_v1_1_${lower}_diagnostic" \
    --scope-mode declared
done
```

Expected: all six commands exit 0.

- [ ] **Step 6: Run BTC correlation review**

Run in RandysLab:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/review_factor_candidate_correlation.py \
  --config configs/strict4h.yaml \
  --candidates ../QuantumRandy/reports/factor_candidate_exports/research_v1_1_independent_scoped_family_replication/factor_candidates.jsonl \
  --out reports/factor_candidate_correlation/research_v1_1_btc \
  --symbol BTCUSDT \
  --ohlcv-csv data/BTCUSDT_4h.csv \
  --funding-csv data/BTCUSDT_funding.csv \
  --high-corr-threshold 0.80
```

Expected: output JSON includes `bundle_count: 2`.

- [ ] **Step 7: Verify the fixed v1.1 replication variant cohort exists in BTC primary review**

Run in RandysLab:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 - <<'PY'
import pandas as pd
review = pd.read_csv('reports/factor_candidate_review/research_v1_1_btc_primary/factor_candidate_review.csv').fillna('')
required = {
    'thr_0p0_long_flat_cap_0p5_none',
    'thr_0p0_long_short_cap_0p5_none',
    'thr_0p0_long_flat_cap_1p0_calm_vol_lte_1p5',
    'thr_0p5_long_short_cap_0p5_none',
    'thr_1p0_long_short_cap_1p0_none',
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

- [ ] **Step 8: Run scope-aware robustness gauntlet**

Run in RandysLab:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/run_watchlist_robustness_gauntlet.py \
  --config configs/strict4h.yaml \
  --candidates ../QuantumRandy/reports/factor_candidate_exports/research_v1_1_independent_scoped_family_replication/factor_candidates.jsonl \
  --review-csv reports/factor_candidate_review/research_v1_1_btc_primary/factor_candidate_review.csv \
  --out reports/factor_candidate_robustness/research_v1_1_independent_replication \
  --variant-id thr_0p0_long_flat_cap_0p5_none \
  --variant-id thr_0p0_long_short_cap_0p5_none \
  --variant-id thr_0p0_long_flat_cap_1p0_calm_vol_lte_1p5 \
  --variant-id thr_0p5_long_short_cap_0p5_none \
  --variant-id thr_1p0_long_short_cap_1p0_none
```

Expected: output JSON includes `variant_count: 50` because the export has `10` candidates and the fixed cohort has `5` variants.

- [ ] **Step 9: Build v1.1 failure memory**

Run in QuantumRandy:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/build_v1_1_independent_replication_memory.py \
  --ranking-csv ../RandysLab-STRICT4H/reports/factor_candidate_robustness/research_v1_1_independent_replication/watchlist_robustness_variant_ranking.csv \
  --source-robustness-dir reports/factor_candidate_robustness/research_v1_1_independent_replication \
  --out reports/failure_memory/research_v1_1_independent_replication
```

Expected: the command exits 0 and prints a failure-row count with `input rows: 50`.

- [ ] **Step 10: Render v1.1 report**

Run in QuantumRandy:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/render_v1_1_independent_replication_report.py
```

Expected output:

```text
Wrote /Users/rosebrain-2/Projects/Quant/QuantumRandy/docs/RESEARCH_V1_1_INDEPENDENT_SCOPED_FAMILY_REPLICATION_REPORT.md
readiness=research_v1_1_independent_candidate_replicated_pending_manual_review
```

If no independent candidate survives, the second line is exactly:

```text
readiness=research_v1_1_independent_candidate_not_found
```

## Task 5: Documentation, Verification, and GitHub

**Files:**
- Modify: `docs/RESEARCH_V1_1_INDEPENDENT_SCOPED_FAMILY_REPLICATION_REPORT.md`
- Modify: `docs/README.md`
- Modify: `docs/PROJECT_LOG.md`

- [ ] **Step 1: Add docs index entry**

Modify `docs/README.md` to include:

```markdown
- `RESEARCH_V1_1_INDEPENDENT_SCOPED_FAMILY_REPLICATION_REPORT.md`: independent non-funding scoped family replication
  pass after the first Research 1.0 candidate.
```

- [ ] **Step 2: Add project log entry**

Add a top entry to `docs/PROJECT_LOG.md`:

```markdown
## 2026-07-03 Research v1.1 Independent Scoped Family Replication

Completed the research-only v1.1 independent scoped family replication pass.

- Report: `docs/RESEARCH_V1_1_INDEPENDENT_SCOPED_FAMILY_REPLICATION_REPORT.md`.
- Current Research 1.0 survivor excluded: `qr_v09d_funding_return_long_001::thr_0p0_long_short_cap_0p5_none`.
- Candidate cohort: non-funding, current-DSL, `BTCUSDT_4h`, `out_of_scope_policy=diagnostic_only`.
- RandysLab artifacts: BTC primary declared review, ETH/SOL/BNB/AVAX diagnostics, BTC bundle correlation, and
  scope-aware robustness gauntlet.
- Readiness verdict: `research_v1_1_independent_candidate_replicated_pending_manual_review`.

Boundary preserved: no RandyPortfolio implementation, no live trading, no exchange private keys, no runtime factor
publishing, no automatic factor admission, no new formula base fields, no production regime labels, and no selector
evidence61.
```

If the rendered report prints `research_v1_1_independent_candidate_not_found`, use this exact readiness bullet instead:

```markdown
- Readiness verdict: `research_v1_1_independent_candidate_not_found`.
```

Only one readiness bullet should remain in `docs/PROJECT_LOG.md`.

- [ ] **Step 3: Run QuantumRandy focused tests**

Run:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest tests/test_v1_1_independent_replication.py tests/test_research10_replication_memory.py tests/test_v0_9d_discovery.py -q
```

Expected: all tests pass.

- [ ] **Step 4: Run RandysLab focused tests**

Run:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest tests/test_formula_candidates.py tests/test_factor_candidate_robustness.py tests/test_factor_candidate_correlation.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Run both full test suites**

Run in RandysLab:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest -q
```

Expected: all tests pass.

Run in QuantumRandy:

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

export_manifest = json.loads(Path('reports/factor_candidate_exports/research_v1_1_independent_scoped_family_replication/factor_candidate_export_manifest.json').read_text())
assert export_manifest['research_checkpoint'] == 'v1.1'
assert export_manifest['excluded_research10_survivor']['candidate_id'] == 'qr_v09d_funding_return_long_001'

ranking_path = Path('../RandysLab-STRICT4H/reports/factor_candidate_robustness/research_v1_1_independent_replication/watchlist_robustness_variant_ranking.csv')
if ranking_path.exists():
    ranking = pd.read_csv(ranking_path).fillna('')
    assert 'qr_v09d_funding_return_long_001' not in set(ranking['candidate_id'])
    passed = ranking[ranking['conservative_verdict'].eq('research_watchlist')]
    for _, row in passed.iterrows():
        assert int(row['stress_survival_count']) == int(row['stress_count'])
        assert int(row.get('diagnostic_scenario_count', 0)) >= 0

memory_manifest = json.loads(Path('reports/failure_memory/research_v1_1_independent_replication/failure_memory_manifest.json').read_text())
assert memory_manifest['input_rows'] >= memory_manifest['failure_count']
print('v1.1 invariants OK')
PY
```

Expected: `v1.1 invariants OK`.

- [ ] **Step 7: Boundary scan**

Run in both repositories:

```bash
rg -n "RandyPortfolio|live trading|exchange keys|runtime publishing|automatic factor admission|selector evidence61|production regime" docs scripts quantumrandy tests
```

For RandysLab, use:

```bash
rg -n "RandyPortfolio|live trading|exchange keys|runtime publishing|automatic factor admission|selector evidence61|production regime" randyslab scripts tests
```

Expected: matches are boundary statements only, not new implementation paths.

- [ ] **Step 8: Commit QuantumRandy tracked outputs**

Run in QuantumRandy:

```bash
git status --short
git add docs/README.md docs/PROJECT_LOG.md docs/RESEARCH_V1_1_INDEPENDENT_SCOPED_FAMILY_REPLICATION_REPORT.md
git commit -m "Record Research v1.1 independent replication"
```

Expected: commit succeeds. Ignored `reports/` artifacts remain untracked.

- [ ] **Step 9: Commit RandysLab only if source changed**

Run in RandysLab:

```bash
git status --short
```

If only ignored `reports/` artifacts changed, do not commit RandysLab. If a legitimate source or test fix was required during execution, commit only those source/test files:

```bash
git add path/to/source.py path/to/test.py
git commit -m "Fix Research v1.1 strict review support"
```

- [ ] **Step 10: Push to GitHub**

Run in any repository with a new commit:

```bash
git push
```

Expected: `main -> main` push succeeds.

## Success Criteria

Research v1.1 is complete when:

- QuantumRandy has a committed v1.1 report.
- The v1.1 export excludes `qr_v09d_funding_return_long_001` and any `funding_rate` formula.
- RandysLab has generated BTC primary declared review, ETH/SOL/BNB/AVAX diagnostics, BTC correlation, and scope-aware robustness artifacts.
- v1.1 failure memory is generated from robustness ranking.
- Readiness verdict is one of:
  - `research_v1_1_independent_candidate_replicated_pending_manual_review`
  - `research_v1_1_independent_candidate_not_found`
- Full QuantumRandy and RandysLab tests pass.
- Boundary remains intact: no RandyPortfolio, no live trading, no exchange private keys, no runtime publishing, no automatic factor admission, no new formula base fields, no production regime labels, no selector evidence61.

## Notes for the Implementer

- Do not treat a v1.1 survivor as a production factor.
- Do not weaken strict judge thresholds to force a pass.
- Do not add new public crypto-native fields in this plan.
- If no non-funding candidate survives, the correct output is a clean negative result with failure memory, not a retry loop.
- If a candidate survives only because scope-out rows failed but BTC scope rows passed, that is acceptable only when `scope_hard_gate=True` rows all survive and out-of-scope rows are diagnostic labels.
