# Research v1.3 Funding-Adjacent Scoped Re-Spec Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a research-only v1.3 checkpoint that tests a funding-adjacent scoped candidate cohort around, but not duplicating, the Research 1.0 funding-return survivor.

**Architecture:** QuantumRandy owns deterministic v1.3 export, failure memory, report rendering, and tracked documentation. RandysLab source changes are not expected; reuse existing declared review, diagnostic review, correlation, and scope-aware robustness CLIs. The checkpoint may end with a funding-adjacent survivor pending manual research review or a clean negative result.

**Tech Stack:** Python 3, pandas, pytest, QuantumRandy JSONL/CSV/Markdown export helpers, RandysLab strict4h config, existing RandysLab factor-candidate sensitivity/review/correlation/robustness CLIs.

---

## Current State

- Research 1.0 has one scoped BTCUSDT 4h funding-return survivor:
  `qr_v09d_funding_return_long_001::thr_0p0_long_short_cap_0p5_none`.
- Research v1.1 tested `10` independent non-funding candidates and found no survivor.
- Research v1.2 tested `12` failure-guided non-funding candidates and found no survivor; robustness generated `60`
  rankings, all blocked, with the best near miss at `14/15` scope-hard stresses.
- V1.3 must remain research-only and must not enter paper observation, RandyPortfolio planning, runtime publishing, or
  live trading.
- V1.3 may use current admitted formula fields: `open`, `high`, `low`, `close`, `volume`, and `funding_rate`.
- V1.3 must explicitly declare funding-adjacent status. It must not claim non-funding independence from the Research
  1.0 survivor.

## File Structure

### QuantumRandy

- Create `quantumrandy/v13_funding_adjacent_respec_export.py`
  - Defines the v1.3 deterministic funding-adjacent candidate cohort.
  - Excludes the Research 1.0 survivor by ID, formula, and bundle membership.
  - Writes JSONL, bundle JSONL, CSV, manifest, Markdown export, and events.
- Create `scripts/export_v1_3_funding_adjacent_scoped_respec.py`
  - Thin CLI wrapper around the export module.
- Create `quantumrandy/v13_funding_adjacent_respec_memory.py`
  - Converts RandysLab v1.3 robustness rankings into failure-memory rows.
  - Preserves passed rows in builder output but writes only failed rows to `failure_memory.csv`.
  - Adds labels for `funding_adjacent_respec`, `funding_adjacent_family`, and replication stress failures.
- Create `scripts/build_v1_3_funding_adjacent_respec_memory.py`
  - CLI wrapper around the v1.3 memory writer.
- Create `scripts/render_v1_3_funding_adjacent_scoped_respec_report.py`
  - Renders the final v1.3 report from export, RandysLab review/correlation/robustness artifacts, and failure memory.
- Create `tests/test_v1_3_funding_adjacent_respec.py`
  - Covers export safety/schema, survivor non-duplication, funding-adjacent metadata, memory behavior, and report verdicts.
- Create `docs/RESEARCH_V1_3_FUNDING_ADJACENT_SCOPED_RESPEC_REPORT.md`
  - Final tracked report after artifacts are generated.
- Modify `docs/README.md`
  - Add the new v1.3 plan and report entries.
- Modify `docs/PROJECT_LOG.md`
  - Add a top entry after the v1.3 report is rendered.

### RandysLab

- No source changes are expected.
- Reuse existing scripts:
  - `scripts/sweep_factor_candidates.py`
  - `scripts/review_factor_candidate_sensitivity.py`
  - `scripts/review_factor_candidate_correlation.py`
  - `scripts/run_watchlist_robustness_gauntlet.py`
- Generate ignored research artifacts under:
  - `reports/factor_candidate_sensitivity/research_v1_3_btc_primary`
  - `reports/factor_candidate_review/research_v1_3_btc_primary`
  - `reports/factor_candidate_sensitivity/research_v1_3_eth_diagnostic`
  - `reports/factor_candidate_review/research_v1_3_eth_diagnostic`
  - `reports/factor_candidate_sensitivity/research_v1_3_sol_diagnostic`
  - `reports/factor_candidate_review/research_v1_3_sol_diagnostic`
  - `reports/factor_candidate_sensitivity/research_v1_3_bnb_diagnostic`
  - `reports/factor_candidate_review/research_v1_3_bnb_diagnostic`
  - `reports/factor_candidate_sensitivity/research_v1_3_avax_diagnostic`
  - `reports/factor_candidate_review/research_v1_3_avax_diagnostic`
  - `reports/factor_candidate_correlation/research_v1_3_btc`
  - `reports/factor_candidate_robustness/research_v1_3_funding_adjacent_respec`

## Task 1: Export Funding-Adjacent v1.3 Candidate Cohort

**Files:**
- Create: `quantumrandy/v13_funding_adjacent_respec_export.py`
- Create: `scripts/export_v1_3_funding_adjacent_scoped_respec.py`
- Create: `tests/test_v1_3_funding_adjacent_respec.py`

- [ ] **Step 1: Write the failing export test**

Create `tests/test_v1_3_funding_adjacent_respec.py` with this initial test:

```python
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from quantumrandy.expression import parse_formula
from quantumrandy.v13_funding_adjacent_respec_export import (
    V13_BUNDLE_CANDIDATES,
    V13_EXCLUDED_RESEARCH10_SURVIVOR,
    V13_SINGLE_FACTOR_CANDIDATES,
    export_v1_3_funding_adjacent_scoped_respec,
)


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_export_v1_3_funding_adjacent_candidates_are_scoped_and_nonduplicative(tmp_path) -> None:
    out = tmp_path / "v13_export"

    manifest = export_v1_3_funding_adjacent_scoped_respec(out)

    assert manifest["artifact_type"] == "quantumrandy_factor_candidate_export_manifest"
    assert manifest["research_checkpoint"] == "v1.3"
    assert manifest["candidate_family"] == "funding_adjacent_scoped_respec"
    assert manifest["funding_adjacent_status"] == "funding_adjacent_not_independent_non_funding"
    assert manifest["scope_contract"]["intended_scope"] == "BTCUSDT_4h"
    assert manifest["scope_contract"]["out_of_scope_policy"] == "diagnostic_only"
    assert manifest["source"]["created_from_spec"] == (
        "docs/superpowers/specs/2026-07-03-research-v1-3-funding-adjacent-scoped-respec-design.md"
    )
    assert manifest["excluded_research10_survivor"] == V13_EXCLUDED_RESEARCH10_SURVIVOR
    assert manifest["candidate_count"] == len(V13_SINGLE_FACTOR_CANDIDATES) + len(V13_BUNDLE_CANDIDATES)
    assert manifest["single_factor_count"] == 12
    assert manifest["bundle_count"] == 4
    assert manifest["safety"]["research_only"] is True
    assert manifest["safety"]["not_runtime_publish_payload"] is True
    assert manifest["safety"]["does_not_auto_admit_factors"] is True

    records = _jsonl(out / "factor_candidates.jsonl")
    bundle_records = _jsonl(out / "bundle_candidates.jsonl")
    assert len(records) == 16
    assert len(bundle_records) == 4

    excluded_id = V13_EXCLUDED_RESEARCH10_SURVIVOR["candidate_id"]
    excluded_formula = V13_EXCLUDED_RESEARCH10_SURVIVOR["formula"]
    required_families = {
        "funding_pressure_normalization",
        "funding_return_interaction",
        "cost_aware_carry_filter",
        "funding_regime_transition",
        "funding_adjacent_equal_weight_bundle",
    }
    allowed_fields = {"open", "high", "low", "close", "volume", "funding_rate"}
    observed_families = set()

    for record in records:
        assert record["artifact_type"] == "quantumrandy_factor_candidate_export"
        assert record["research_checkpoint"] == "v1.3"
        assert record["research_only"] is True
        assert record["not_runtime_publish_payload"] is True
        assert record["candidate_id"] != excluded_id
        assert record["formula"] != excluded_formula
        assert record["candidate_tier"] in {"funding_adjacent_candidate", "funding_adjacent_bundle"}
        assert record["funding_adjacent_status"] == "funding_adjacent_not_independent_non_funding"
        assert record["independence_claim"] == "none_funding_adjacent_locality_probe"
        assert record["intended_scope"] == "BTCUSDT_4h"
        assert record["out_of_scope_policy"] == "diagnostic_only"
        assert set(record["required_features"]).issubset(allowed_fields)
        assert "funding_rate" in record["required_features"]
        observed_families.add(record["formula_family"])
        formulas = [record["formula"], *record.get("component_formulas", [])]
        assert excluded_formula not in formulas
        for formula in formulas:
            parse_formula(formula)
            assert "funding_rate" in formula
            assert formula != excluded_formula

    for bundle in bundle_records:
        assert excluded_id not in bundle["component_candidate_ids"]
        assert excluded_formula not in bundle["component_formulas"]

    assert required_families.issubset(observed_families)

    csv = pd.read_csv(out / "factor_candidates.csv")
    assert len(csv) == 16
    assert set(csv["intended_scope"]) == {"BTCUSDT_4h"}
    assert set(csv["out_of_scope_policy"]) == {"diagnostic_only"}
    assert set(csv["funding_adjacent_status"]) == {"funding_adjacent_not_independent_non_funding"}

    report = (out / "FACTOR_CANDIDATE_EXPORT.md").read_text(encoding="utf-8")
    assert "Research v1.3" in report
    assert "funding-adjacent scoped re-spec" in report
    assert "not a runtime publish payload" in report
    assert "not independent non-funding replication" in report
```

- [ ] **Step 2: Run the export test to verify it fails**

Run:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest tests/test_v1_3_funding_adjacent_respec.py::test_export_v1_3_funding_adjacent_candidates_are_scoped_and_nonduplicative -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'quantumrandy.v13_funding_adjacent_respec_export'`.

- [ ] **Step 3: Implement the export module**

Create `quantumrandy/v13_funding_adjacent_respec_export.py` with constants and candidate definitions:

```python
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

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
        "hypothesis": "Funding pressure scaled by realized price level volatility may capture crowding without raw mean reversion.",
        "expected_failure_mode": "Can fail if normalized funding remains a direct crowding proxy that is fee or blind-window fragile.",
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
        "hypothesis": "Shorter funding/return alignment may test locality without duplicating the long-horizon Research 1.0 survivor.",
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
        "hypothesis": "Recent funding increases may identify crowding reversal risk without copying long-horizon return alignment.",
        "expected_failure_mode": "Can fail if funding changes persist through trend continuation.",
    },
    {
        "candidate_id": "qr_v13_funding_delta_return_corr_001",
        "formula_family": "funding_regime_transition",
        "formula": "zscore(corr(delta(funding_rate,12),ret(close,12),72),120)",
        "hypothesis": "Funding transition alignment with short returns may capture state changes distinct from static funding pressure.",
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
        "hypothesis": "Funding-pressure normalization variants may test whether the v1.3 edge is broader than raw funding pressure.",
    },
    {
        "candidate_id": "qr_v13_bundle_funding_return_interaction_001",
        "formula_family": "funding_adjacent_equal_weight_bundle",
        "component_candidate_ids": [
            "qr_v13_funding_return_short_corr_001",
            "qr_v13_funding_return_product_001",
            "qr_v13_smooth_funding_return_corr_001",
        ],
        "hypothesis": "Funding/return interactions at non-survivor horizons may test local robustness around the Research 1.0 edge.",
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
```

Create the full export implementation by copying `quantumrandy/v12_failure_guided_respec_export.py` to
`quantumrandy/v13_funding_adjacent_respec_export.py`, then make these deterministic edits in the new file:

- rename `export_v1_2_failure_guided_scoped_respec(...)` to `export_v1_3_funding_adjacent_scoped_respec(...)`;
- rename `render_v1_2_export_report(...)` to `render_v1_3_export_report(...)`;
- rename v1.2 constants to v1.3 constants shown above and replace the v1.2 candidate lists with
  `V13_SINGLE_FACTOR_CANDIDATES` and `V13_BUNDLE_CANDIDATES`;
- set `research_checkpoint` to `v1.3`;
- set `candidate_family` to `funding_adjacent_scoped_respec`;
- include `funding_adjacent_status` and `independence_claim` in the manifest and every candidate row;
- include `excluded_research10_survivor`;
- include `source.created_from_spec` and `source.created_from_plan`;
- set `source.created_from_plan` to
  `docs/superpowers/plans/2026-07-03-research-v1-3-funding-adjacent-scoped-respec.md`;
- reject any candidate ID equal to `qr_v09d_funding_return_long_001`;
- reject any formula equal to `zscore(corr(funding_rate,ret(close,42),120),72)`;
- reject any bundle containing the excluded survivor ID or formula;
- do not reject direct `funding_rate`;
- set `"candidate_tier"` to `"funding_adjacent_candidate"` or `"funding_adjacent_bundle"`;
- build bundle formulas as `div(add(add(f1,f2),f3),3)` so `parse_formula` accepts them.
- keep the existing output names: `factor_candidates.jsonl`, `bundle_candidates.jsonl`,
  `factor_candidates.csv`, `factor_candidate_export_manifest.json`, `FACTOR_CANDIDATE_EXPORT.md`, and
  `events.jsonl`;
- keep atomic writes through `safe_write_csv`, `safe_write_json`, `safe_write_text`, and `append_jsonl`.

- [ ] **Step 4: Add the export CLI**

Create `scripts/export_v1_3_funding_adjacent_scoped_respec.py`:

```python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantumrandy.v13_funding_adjacent_respec_export import export_v1_3_funding_adjacent_scoped_respec


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Research v1.3 funding-adjacent scoped re-spec candidates.")
    parser.add_argument(
        "--out",
        default="reports/factor_candidate_exports/research_v1_3_funding_adjacent_scoped_respec",
        help="Output directory for JSONL, bundle JSONL, CSV, manifest, events, and Markdown report.",
    )
    args = parser.parse_args()
    manifest = export_v1_3_funding_adjacent_scoped_respec(args.out)
    print(
        "v1.3 funding-adjacent scoped re-spec export: "
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
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest tests/test_v1_3_funding_adjacent_respec.py::test_export_v1_3_funding_adjacent_candidates_are_scoped_and_nonduplicative -q
```

Expected: `1 passed`.

- [ ] **Step 6: Commit the export layer**

Run:

```bash
git add quantumrandy/v13_funding_adjacent_respec_export.py scripts/export_v1_3_funding_adjacent_scoped_respec.py tests/test_v1_3_funding_adjacent_respec.py
git commit -m "Add Research v1.3 funding-adjacent candidate export"
```

## Task 2: Build v1.3 Failure Memory

**Files:**
- Create: `quantumrandy/v13_funding_adjacent_respec_memory.py`
- Create: `scripts/build_v1_3_funding_adjacent_respec_memory.py`
- Modify: `tests/test_v1_3_funding_adjacent_respec.py`

- [ ] **Step 1: Write the failing memory test**

Append this test to `tests/test_v1_3_funding_adjacent_respec.py`:

```python
def test_v1_3_failure_memory_records_only_failed_rankings(tmp_path) -> None:
    from quantumrandy.v13_funding_adjacent_respec_memory import (
        build_v1_3_funding_adjacent_respec_memory_rows,
        write_v1_3_funding_adjacent_respec_failure_memory,
    )

    source_robustness_dir = "reports/factor_candidate_robustness/research_v1_3_funding_adjacent_respec"
    ranking_csv = tmp_path / "watchlist_robustness_variant_ranking.csv"
    pd.DataFrame(
        [
            {
                "candidate_id": "qr_v13_funding_return_short_corr_001",
                "variant_id": "thr_0p0_long_flat_cap_0p5_calm_vol_lte_1p5",
                "formula": "zscore(corr(funding_rate,ret(close,12),72),120)",
                "conservative_verdict": "blocked_pending_new_hypotheses",
                "intended_scope": "BTCUSDT_4h",
                "failure_reasons": "weak_blind_window",
                "diagnostic_failure_reasons": "sol_avax_concentration",
                "robustness_labels": "fee_fragility|btc_weakness",
                "stress_survival_score": 0.8,
                "stress_survival_count": 12,
                "stress_count": 15,
                "mean_sharpe": 0.6,
                "validation_mean_sharpe": 0.2,
                "blind_mean_sharpe": 0.1,
                "mean_max_dd": 0.2,
                "worst_max_dd": 0.45,
            },
            {
                "candidate_id": "qr_v13_funding_ema_shift_001",
                "variant_id": "thr_0p0_long_short_cap_0p5_calm_vol_lte_1p5",
                "formula": "zscore(sub(ema(funding_rate,12),ema(funding_rate,48)),120)",
                "conservative_verdict": "research_watchlist",
                "intended_scope": "",
                "failure_reasons": "",
                "diagnostic_failure_reasons": "",
                "robustness_labels": "funding_adjacent_locality",
                "stress_survival_count": 15,
                "stress_count": 15,
                "mean_sharpe": 0.7,
                "validation_mean_sharpe": 0.4,
                "blind_mean_sharpe": 0.5,
                "mean_max_dd": 0.2,
                "worst_max_dd": 0.3,
            },
        ]
    ).to_csv(ranking_csv, index=False)

    rows = build_v1_3_funding_adjacent_respec_memory_rows(
        ranking_csv,
        source_robustness_dir=source_robustness_dir,
    )
    manifest = write_v1_3_funding_adjacent_respec_failure_memory(
        ranking_csv,
        tmp_path / "failure_memory",
        source_robustness_dir=source_robustness_dir,
    )

    assert len(rows) == 2
    assert manifest["input_rows"] == 2
    assert manifest["failure_count"] == 1
    failed_row, survivor_row = rows
    assert failed_row["candidate_family"] == "research_v1_3_funding_adjacent_respec_variant"
    assert failed_row["funding_adjacent_status"] == "funding_adjacent_not_independent_non_funding"
    assert failed_row["independence_claim"] == "none_funding_adjacent_locality_probe"
    assert failed_row["intended_scope"] == "BTCUSDT_4h"
    assert failed_row["out_of_scope_policy"] == "diagnostic_only"
    assert failed_row["source_review_dir"] == source_robustness_dir
    assert failed_row["source_robustness_dir"] == source_robustness_dir
    assert failed_row["stress_survival"] == "12/15"
    assert failed_row["passed"] is False
    assert "funding_adjacent_respec" in failed_row["failure_labels"]
    assert "funding_adjacent_family" in failed_row["failure_labels"]
    assert "replication_stress_fragility" in failed_row["failure_labels"]
    assert survivor_row["passed"] is True
    assert survivor_row["intended_scope"] == "BTCUSDT_4h"
    assert "replication_stress_fragility" not in set(str(survivor_row["failure_labels"]).split("|"))

    failure_memory = pd.read_csv(tmp_path / "failure_memory" / "failure_memory.csv")
    assert len(failure_memory) == 1
    failed = failure_memory.iloc[0]
    assert failed["candidate_id"] == "qr_v13_funding_return_short_corr_001::thr_0p0_long_flat_cap_0p5_calm_vol_lte_1p5"
    assert failed["candidate_family"] == "research_v1_3_funding_adjacent_respec_variant"
    assert failed["failed_gates"] == "weak_blind_window"
```

- [ ] **Step 2: Run the memory test to verify it fails**

Run:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest tests/test_v1_3_funding_adjacent_respec.py::test_v1_3_failure_memory_records_only_failed_rankings -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'quantumrandy.v13_funding_adjacent_respec_memory'`.

- [ ] **Step 3: Implement the memory module**

Create the full memory implementation by copying `quantumrandy/v12_failure_guided_respec_memory.py` to
`quantumrandy/v13_funding_adjacent_respec_memory.py`, then make these deterministic edits in the new file:

- exported functions:
  - `build_v1_3_funding_adjacent_respec_memory_rows(...)`;
  - `write_v1_3_funding_adjacent_respec_failure_memory(...)`;
- rename `V12_RESPEC_DESCRIPTION` to `V13_FUNDING_ADJACENT_RESPEC_DESCRIPTION`;
- rename `V12_RESPEC_FAILURE_MODE` to `V13_FUNDING_ADJACENT_RESPEC_FAILURE_MODE`;
- `candidate_family`: `research_v1_3_funding_adjacent_respec_variant`;
- `funding_adjacent_status`: `funding_adjacent_not_independent_non_funding`;
- `independence_claim`: `none_funding_adjacent_locality_probe`;
- `description`: `Research v1.3 funding-adjacent scoped re-spec robustness variant.`;
- `expected_failure_mode`: `Funding-adjacent v1.3 robustness variants may fail through redundancy with the Research 1.0 survivor, blind-window weakness, fee or funding stress fragility, BTC scope weakness, crash-period drawdown, or diagnostic out-of-scope concentration.`;
- each row dictionary must include `funding_adjacent_status` and `independence_claim`;
- `_labels(...)` must combine `robustness_labels`, `failure_reasons`, and `diagnostic_failure_reasons`, then add
  `funding_adjacent_respec` and `funding_adjacent_family`;
- add `replication_stress_fragility` only when numeric `stress_survival_score < 1.0`;
- preserve the v1.2 fix that invalid or blank `stress_survival_score` does not raise `TypeError`.

- [ ] **Step 4: Add the memory CLI**

Create `scripts/build_v1_3_funding_adjacent_respec_memory.py`:

```python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantumrandy.v13_funding_adjacent_respec_memory import write_v1_3_funding_adjacent_respec_failure_memory


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Research v1.3 funding-adjacent respec failure memory.")
    parser.add_argument("--ranking-csv", required=True)
    parser.add_argument("--source-robustness-dir", required=True)
    parser.add_argument("--out", default="reports/failure_memory/research_v1_3_funding_adjacent_respec")
    args = parser.parse_args()
    manifest = write_v1_3_funding_adjacent_respec_failure_memory(
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
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest tests/test_v1_3_funding_adjacent_respec.py::test_v1_3_failure_memory_records_only_failed_rankings -q
```

Expected: `1 passed`.

- [ ] **Step 6: Commit the memory layer**

Run:

```bash
git add quantumrandy/v13_funding_adjacent_respec_memory.py scripts/build_v1_3_funding_adjacent_respec_memory.py tests/test_v1_3_funding_adjacent_respec.py
git commit -m "Add Research v1.3 failure memory"
```

## Task 3: Render v1.3 Readiness Report

**Files:**
- Create: `scripts/render_v1_3_funding_adjacent_scoped_respec_report.py`
- Modify: `tests/test_v1_3_funding_adjacent_respec.py`
- Later generate: `docs/RESEARCH_V1_3_FUNDING_ADJACENT_SCOPED_RESPEC_REPORT.md`

- [ ] **Step 1: Write the failing report test**

Append this test to `tests/test_v1_3_funding_adjacent_respec.py`:

```python
def test_v1_3_report_renderer_states_readiness_without_admission(monkeypatch) -> None:
    import importlib.util

    script = Path(__file__).resolve().parents[1] / "scripts" / "render_v1_3_funding_adjacent_scoped_respec_report.py"
    spec = importlib.util.spec_from_file_location("render_v1_3_funding_adjacent_scoped_respec_report", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    ranking = pd.DataFrame(
        [
            {
                "candidate_id": "qr_v13_funding_return_short_corr_001",
                "variant_id": "thr_0p0_long_flat_cap_0p5_calm_vol_lte_1p5",
                "conservative_verdict": "research_watchlist",
                "stress_survival_count": 15,
                "stress_count": 15,
                "mean_sharpe": 0.8,
                "worst_max_dd": 0.3,
                "validation_mean_sharpe": 0.4,
                "blind_mean_sharpe": 0.5,
                "robustness_labels": "funding_adjacent_locality",
            }
        ]
    )
    blocked = ranking.assign(conservative_verdict="blocked_pending_new_hypotheses", stress_survival_count=12)

    assert (
        module._readiness_verdict(ranking)
        == "research_v1_3_funding_adjacent_candidate_replicated_pending_manual_review"
    )
    assert module._readiness_verdict(blocked) == "research_v1_3_funding_adjacent_candidate_not_found"
    assert module._readiness_verdict(pd.DataFrame()) == "research_v1_3_funding_adjacent_candidate_not_found"

    fake_randyslab = Path("/tmp/nonstandard_quant_workspace/RandysLab-STRICT4H")
    monkeypatch.setattr(module, "_find_sibling_repo", lambda root, repo_name: fake_randyslab)
    artifact_paths = module._artifact_paths(fake_randyslab)

    report = module._render(
        export_manifest={
            "candidate_count": 16,
            "single_factor_count": 12,
            "bundle_count": 4,
            "funding_adjacent_status": "funding_adjacent_not_independent_non_funding",
            "scope_contract": {"intended_scope": "BTCUSDT_4h", "out_of_scope_policy": "diagnostic_only"},
            "excluded_research10_survivor": {
                "candidate_id": "qr_v09d_funding_return_long_001",
                "variant_id": "thr_0p0_long_short_cap_0p5_none",
                "formula_family": "funding_return_long_horizon",
                "formula": "zscore(corr(funding_rate,ret(close,42),120),72)",
            },
        },
        candidates=[
            {
                "candidate_id": "qr_v13_funding_return_short_corr_001",
                "formula_family": "funding_return_interaction",
                "formula": "zscore(corr(funding_rate,ret(close,12),72),120)",
            }
        ],
        btc_review_summary={"candidate_count": 192, "verdict_counts": {"research_watchlist": 3}},
        eth_review_summary={"candidate_count": 192, "verdict_counts": {"blocked_by_conservative_rules": 100}},
        correlation_summary={"bundle_count": 4, "bundle_verdict_counts": {"diversified_enough_for_research": 3}},
        robustness_summary={"detail_row_count": 14640, "scenario_summary_count": 1280, "variant_count": 80},
        ranking=ranking,
        memory_manifest={"input_rows": 80, "failure_count": 79, "cluster_count": 25},
        readiness="research_v1_3_funding_adjacent_candidate_replicated_pending_manual_review",
    )

    assert "Research v1.3 Funding-Adjacent Scoped Re-Spec Report" in report
    assert "qr_v09d_funding_return_long_001" in report
    assert "qr_v13_funding_return_short_corr_001" in report
    assert "research_v1_3_funding_adjacent_candidate_replicated_pending_manual_review" in report
    assert "not factor admission" in report
    assert "not independent non-funding replication" in report
    assert "No RandyPortfolio implementation" in report
    assert f"- Review path: `{module._rel(artifact_paths['btc_review'])}`" in report
    assert f"- Correlation path: `{module._rel(artifact_paths['correlation'])}`" in report
    assert f"- Robustness path: `{module._rel(artifact_paths['robustness'])}`" in report
```

- [ ] **Step 2: Run the report test to verify it fails**

Run:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest tests/test_v1_3_funding_adjacent_respec.py::test_v1_3_report_renderer_states_readiness_without_admission -q
```

Expected: FAIL because `scripts/render_v1_3_funding_adjacent_scoped_respec_report.py` does not exist.

- [ ] **Step 3: Implement the report renderer**

Create the full report renderer by copying `scripts/render_v1_2_failure_guided_scoped_respec_report.py` to
`scripts/render_v1_3_funding_adjacent_scoped_respec_report.py`, then make these deterministic edits in the new file.
Use these exact path constants:

```python
ROOT = Path(__file__).resolve().parents[1]
EXPORT_DIR = ROOT / "reports/factor_candidate_exports/research_v1_3_funding_adjacent_scoped_respec"
MEMORY_DIR = ROOT / "reports/failure_memory/research_v1_3_funding_adjacent_respec"
REPORT_PATH = ROOT / "docs/RESEARCH_V1_3_FUNDING_ADJACENT_SCOPED_RESPEC_REPORT.md"
```

Implement `_readiness_verdict` exactly as:

```python
def _readiness_verdict(ranking: pd.DataFrame) -> str:
    if ranking.empty or "conservative_verdict" not in ranking.columns:
        return "research_v1_3_funding_adjacent_candidate_not_found"
    passed = ranking[ranking["conservative_verdict"] == "research_watchlist"]
    if passed.empty:
        return "research_v1_3_funding_adjacent_candidate_not_found"
    return "research_v1_3_funding_adjacent_candidate_replicated_pending_manual_review"
```

The `_render(...)` function must include:

- title: `# Research v1.3 Funding-Adjacent Scoped Re-Spec Report`;
- boundary sentence: research-only, not factor admission, not runtime publishing, not RandyPortfolio, not live execution;
- objective: test funding/carry/friction locality after v1.1 and v1.2 clean negative non-funding results;
- explicit funding-adjacent status and statement that this is not independent non-funding replication;
- candidate export counts and excluded Research 1.0 survivor;
- BTC primary declared review summary;
- ETH/SOL/BNB/AVAX diagnostic review summaries if files exist;
- correlation and redundancy summary;
- scope-aware robustness summary;
- passed candidates table or best blocked near misses table;
- failure memory manifest counts;
- readiness verdict;
- verification checklist;
- boundary confirmation with `No RandyPortfolio implementation`, `No live trading`, `No runtime factor publishing`,
  `No automatic factor admission`, `No new formula base fields`, and `No selector evidence61`.

Use `_artifact_paths` for v1.3 RandysLab artifact paths:

```python
def _artifact_paths(randyslab: Path) -> dict[str, Path]:
    return {
        "btc_review": randyslab / "reports/factor_candidate_review/research_v1_3_btc_primary",
        "eth_review": randyslab / "reports/factor_candidate_review/research_v1_3_eth_diagnostic",
        "sol_review": randyslab / "reports/factor_candidate_review/research_v1_3_sol_diagnostic",
        "bnb_review": randyslab / "reports/factor_candidate_review/research_v1_3_bnb_diagnostic",
        "avax_review": randyslab / "reports/factor_candidate_review/research_v1_3_avax_diagnostic",
        "correlation": randyslab / "reports/factor_candidate_correlation/research_v1_3_btc",
        "robustness": randyslab / "reports/factor_candidate_robustness/research_v1_3_funding_adjacent_respec",
    }
```

- [ ] **Step 4: Run the report test to verify it passes**

Run:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest tests/test_v1_3_funding_adjacent_respec.py::test_v1_3_report_renderer_states_readiness_without_admission -q
```

Expected: `1 passed`.

- [ ] **Step 5: Run all v1.3 focused tests**

Run:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest tests/test_v1_3_funding_adjacent_respec.py -q
```

Expected: all v1.3 tests pass.

- [ ] **Step 6: Commit the report renderer**

Run:

```bash
git add scripts/render_v1_3_funding_adjacent_scoped_respec_report.py tests/test_v1_3_funding_adjacent_respec.py
git commit -m "Add Research v1.3 report renderer"
```

## Task 4: Generate v1.3 Research Artifacts

**Files:**
- Generate ignored QuantumRandy reports under `reports/factor_candidate_exports/research_v1_3_funding_adjacent_scoped_respec`
- Generate ignored RandysLab reports under `reports/factor_candidate_*/research_v1_3_*`
- Generate ignored QuantumRandy failure memory under `reports/failure_memory/research_v1_3_funding_adjacent_respec`
- Generate tracked report: `docs/RESEARCH_V1_3_FUNDING_ADJACENT_SCOPED_RESPEC_REPORT.md`

- [ ] **Step 1: Export v1.3 candidates**

Run in QuantumRandy:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/export_v1_3_funding_adjacent_scoped_respec.py \
  --out reports/factor_candidate_exports/research_v1_3_funding_adjacent_scoped_respec
```

Expected output includes:

```text
v1.3 funding-adjacent scoped re-spec export: candidates=16 single_factors=12 bundles=4
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
    --candidates ../QuantumRandy/reports/factor_candidate_exports/research_v1_3_funding_adjacent_scoped_respec/factor_candidates.jsonl \
    --out "reports/factor_candidate_sensitivity/research_v1_3_${label}" \
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
    --detail-csv "reports/factor_candidate_sensitivity/research_v1_3_${label}/factor_candidate_sensitivity_detail.csv" \
    --out "reports/factor_candidate_review/research_v1_3_${label}" \
    --scope-mode declared
done
```

Expected: each command exits 0 and prints JSON containing `verdict_counts`.

- [ ] **Step 4: Run BTC correlation review**

Run in RandysLab:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/review_factor_candidate_correlation.py \
  --config configs/strict4h.yaml \
  --candidates ../QuantumRandy/reports/factor_candidate_exports/research_v1_3_funding_adjacent_scoped_respec/factor_candidates.jsonl \
  --out reports/factor_candidate_correlation/research_v1_3_btc \
  --symbol BTCUSDT \
  --ohlcv-csv data/BTCUSDT_4h.csv \
  --funding-csv data/BTCUSDT_funding.csv \
  --high-corr-threshold 0.80
```

Expected: output JSON includes `bundle_count: 4`.

- [ ] **Step 5: Verify the fixed v1.3 robustness variant cohort exists in BTC primary review**

Run in RandysLab:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 - <<'PY'
import pandas as pd
review = pd.read_csv('reports/factor_candidate_review/research_v1_3_btc_primary/factor_candidate_review.csv').fillna('')
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
  --candidates ../QuantumRandy/reports/factor_candidate_exports/research_v1_3_funding_adjacent_scoped_respec/factor_candidates.jsonl \
  --review-csv reports/factor_candidate_review/research_v1_3_btc_primary/factor_candidate_review.csv \
  --out reports/factor_candidate_robustness/research_v1_3_funding_adjacent_respec \
  --variant-id thr_0p0_long_flat_cap_0p5_calm_vol_lte_1p5 \
  --variant-id thr_0p0_long_short_cap_0p5_calm_vol_lte_1p5 \
  --variant-id thr_0p0_long_flat_cap_1p0_calm_vol_lte_1p5 \
  --variant-id thr_0p5_long_short_cap_0p5_calm_vol_lte_1p5 \
  --variant-id thr_1p0_long_short_cap_1p0_calm_vol_lte_1p5
```

Expected: output JSON includes `variant_count: 80` because the export has `16` candidates and the fixed cohort has `5`
variants.

- [ ] **Step 7: Build v1.3 failure memory**

Run in QuantumRandy:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/build_v1_3_funding_adjacent_respec_memory.py \
  --ranking-csv ../RandysLab-STRICT4H/reports/factor_candidate_robustness/research_v1_3_funding_adjacent_respec/watchlist_robustness_variant_ranking.csv \
  --source-robustness-dir reports/factor_candidate_robustness/research_v1_3_funding_adjacent_respec \
  --out reports/failure_memory/research_v1_3_funding_adjacent_respec
```

Expected: the command exits 0 and prints a failure-row count with `input rows: 80`.

- [ ] **Step 8: Render v1.3 report**

Run in QuantumRandy:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/render_v1_3_funding_adjacent_scoped_respec_report.py
```

Expected output is one of:

```text
Wrote /Users/rosebrain-2/Projects/Quant/QuantumRandy/docs/RESEARCH_V1_3_FUNDING_ADJACENT_SCOPED_RESPEC_REPORT.md
readiness=research_v1_3_funding_adjacent_candidate_replicated_pending_manual_review
```

or:

```text
Wrote /Users/rosebrain-2/Projects/Quant/QuantumRandy/docs/RESEARCH_V1_3_FUNDING_ADJACENT_SCOPED_RESPEC_REPORT.md
readiness=research_v1_3_funding_adjacent_candidate_not_found
```

## Task 5: Documentation, Verification, and GitHub

**Files:**
- Modify: `docs/RESEARCH_V1_3_FUNDING_ADJACENT_SCOPED_RESPEC_REPORT.md`
- Modify: `docs/README.md`
- Modify: `docs/PROJECT_LOG.md`

- [ ] **Step 1: Add docs index entry**

Modify `docs/README.md` to include:

```markdown
- `RESEARCH_V1_3_FUNDING_ADJACENT_SCOPED_RESPEC_REPORT.md`: funding-adjacent scoped re-spec after v1.1 and v1.2
  clean negative non-funding results.
```

- [ ] **Step 2: Add project log entry**

Add a top entry to `docs/PROJECT_LOG.md`. If the rendered report prints
`research_v1_3_funding_adjacent_candidate_replicated_pending_manual_review`, use:

```markdown
## 2026-07-03 Research v1.3 Funding-Adjacent Scoped Re-Spec

Completed the research-only v1.3 funding-adjacent scoped re-spec pass.

- Report: `docs/RESEARCH_V1_3_FUNDING_ADJACENT_SCOPED_RESPEC_REPORT.md`.
- Current Research 1.0 survivor excluded: `qr_v09d_funding_return_long_001::thr_0p0_long_short_cap_0p5_none`.
- Candidate cohort: `16` funding-adjacent current-DSL candidates, `BTCUSDT_4h`,
  `out_of_scope_policy=diagnostic_only`.
- RandysLab artifacts: BTC primary declared review, ETH/SOL/BNB/AVAX diagnostics, BTC bundle correlation, and
  scope-aware robustness gauntlet.
- Readiness verdict: `research_v1_3_funding_adjacent_candidate_replicated_pending_manual_review`.

Boundary preserved: no RandyPortfolio implementation, no live trading, no exchange private keys, no runtime factor
publishing, no automatic factor admission, no new formula base fields, no production regime labels, and no selector
evidence61.
```

If the rendered report prints `research_v1_3_funding_adjacent_candidate_not_found`, use the same entry with this
readiness bullet:

```markdown
- Readiness verdict: `research_v1_3_funding_adjacent_candidate_not_found`.
```

Only one readiness bullet should remain in the new log entry.

- [ ] **Step 3: Run QuantumRandy focused tests**

Run:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest tests/test_v1_3_funding_adjacent_respec.py tests/test_v1_2_failure_guided_respec.py tests/test_v1_1_independent_replication.py tests/test_research10_replication_memory.py -q
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

export_manifest = json.loads(Path('reports/factor_candidate_exports/research_v1_3_funding_adjacent_scoped_respec/factor_candidate_export_manifest.json').read_text())
assert export_manifest['research_checkpoint'] == 'v1.3'
assert export_manifest['candidate_count'] == 16
assert export_manifest['single_factor_count'] == 12
assert export_manifest['bundle_count'] == 4
assert export_manifest['candidate_family'] == 'funding_adjacent_scoped_respec'
assert export_manifest['funding_adjacent_status'] == 'funding_adjacent_not_independent_non_funding'
assert export_manifest['excluded_research10_survivor']['candidate_id'] == 'qr_v09d_funding_return_long_001'

records = [json.loads(line) for line in Path('reports/factor_candidate_exports/research_v1_3_funding_adjacent_scoped_respec/factor_candidates.jsonl').read_text().splitlines() if line.strip()]
excluded_formula = export_manifest['excluded_research10_survivor']['formula']
for record in records:
    assert record['candidate_id'] != 'qr_v09d_funding_return_long_001'
    assert record['formula'] != excluded_formula
    assert record['funding_adjacent_status'] == 'funding_adjacent_not_independent_non_funding'
    assert record['independence_claim'] == 'none_funding_adjacent_locality_probe'
    assert 'funding_rate' in record['required_features']
    assert 'independent_non_funding_replication' not in json.dumps(record)

ranking_path = Path('../RandysLab-STRICT4H/reports/factor_candidate_robustness/research_v1_3_funding_adjacent_respec/watchlist_robustness_variant_ranking.csv')
assert ranking_path.exists()
ranking = pd.read_csv(ranking_path).fillna('')
assert len(ranking) == 80
assert 'qr_v09d_funding_return_long_001' not in set(ranking['candidate_id'])
passed = ranking[ranking['conservative_verdict'].eq('research_watchlist')]
for _, row in passed.iterrows():
    assert int(row['stress_survival_count']) == int(row['stress_count'])
    assert int(row.get('diagnostic_scenario_count', 0)) >= 0

memory_manifest = json.loads(Path('reports/failure_memory/research_v1_3_funding_adjacent_respec/failure_memory_manifest.json').read_text())
assert memory_manifest['input_rows'] >= memory_manifest['failure_count']

report = Path('docs/RESEARCH_V1_3_FUNDING_ADJACENT_SCOPED_RESPEC_REPORT.md').read_text()
assert 'Research v1.3 Funding-Adjacent Scoped Re-Spec Report' in report
assert 'not independent non-funding replication' in report
assert 'No RandyPortfolio implementation' in report
assert 'No live trading' in report
assert (
    'research_v1_3_funding_adjacent_candidate_replicated_pending_manual_review' in report
    or 'research_v1_3_funding_adjacent_candidate_not_found' in report
)
print('v1.3 invariants OK')
PY
```

Expected: `v1.3 invariants OK`.

- [ ] **Step 7: Boundary scan**

Run in QuantumRandy:

```bash
rg -n "RandyPortfolio|live trading|exchange private keys|runtime factor publishing|automatic factor admission|selector evidence61|production regime|production runtime regime|independent_non_funding_replication" \
  quantumrandy/v13_funding_adjacent_respec_export.py \
  quantumrandy/v13_funding_adjacent_respec_memory.py \
  scripts/export_v1_3_funding_adjacent_scoped_respec.py \
  scripts/build_v1_3_funding_adjacent_respec_memory.py \
  scripts/render_v1_3_funding_adjacent_scoped_respec_report.py \
  tests/test_v1_3_funding_adjacent_respec.py \
  docs/RESEARCH_V1_3_FUNDING_ADJACENT_SCOPED_RESPEC_REPORT.md \
  docs/README.md \
  docs/PROJECT_LOG.md
```

Expected: matches are boundary statements, explicit non-independence assertions, or interface-only metadata; there must
be no RandyPortfolio implementation, live execution, runtime publishing, automatic admission, or non-funding
independence claim.

Run in RandysLab:

```bash
rg -n "RandyPortfolio|live trading|exchange private keys|runtime factor publishing|automatic factor admission|selector evidence61|production regime|production runtime regime" randyslab scripts tests
```

Expected: matches are existing boundary statements only, not new implementation paths.

- [ ] **Step 8: Commit QuantumRandy tracked outputs**

Run in QuantumRandy:

```bash
git status --short
git add docs/README.md docs/PROJECT_LOG.md docs/RESEARCH_V1_3_FUNDING_ADJACENT_SCOPED_RESPEC_REPORT.md
git commit -m "Record Research v1.3 funding-adjacent respec"
```

Expected: commit succeeds. Ignored `reports/` artifacts remain untracked.

- [ ] **Step 9: Commit RandysLab only if source changed**

Run in RandysLab:

```bash
git status --short
```

If only ignored `reports/` artifacts changed, do not commit RandysLab. If a legitimate source or test fix was required
during execution, inspect the exact changed paths and commit only those source/test files.

- [ ] **Step 10: Push to GitHub**

Run in any repository with a new commit:

```bash
git push
```

Expected: `main -> main` push succeeds.

## Success Criteria

Research v1.3 is complete when:

- QuantumRandy has a committed v1.3 report.
- The v1.3 export excludes `qr_v09d_funding_return_long_001` and its exact Research 1.0 survivor formula.
- The v1.3 export explicitly declares funding-adjacent status and does not claim non-funding independence.
- The v1.3 cohort includes funding pressure normalization, funding-return interaction, cost-aware carry, and funding
  regime transition families.
- RandysLab has generated BTC primary declared review, ETH/SOL/BNB/AVAX diagnostics, BTC correlation, and scope-aware
  robustness artifacts.
- v1.3 failure memory is generated from robustness ranking.
- Readiness verdict is one of:
  - `research_v1_3_funding_adjacent_candidate_replicated_pending_manual_review`
  - `research_v1_3_funding_adjacent_candidate_not_found`
- Full QuantumRandy and RandysLab tests pass.
- Boundary remains intact: no RandyPortfolio, no live trading, no exchange private keys, no runtime publishing, no
  automatic factor admission, no new formula base fields, no production regime labels, no selector evidence61, and no
  claim of independent non-funding replication.

## Notes for the Implementer

- Do not treat a v1.3 survivor as a production factor.
- Do not claim a v1.3 survivor is independent from the Research 1.0 funding-return survivor.
- Do not weaken strict judge thresholds to force a pass.
- Do not add new public crypto-native fields in this plan.
- If no v1.3 candidate survives, the correct output is a clean negative result with failure memory.
- If a candidate survives, the next step is manual research review of funding-adjacent locality, not RandyPortfolio.
