# Research 1.0 Prerequisite Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the auditable Research 1.0 prerequisites that remain after v0.9c and verify existing logic errors without claiming factor readiness.

**Architecture:** QuantumRandy owns the Spearman robustness fix, public crypto-native feature-readiness audit, generated readiness artifacts, and the tracked prerequisite verification report. RandysLab remains the strict judge and formula-profile authority; this pass verifies RandysLab but does not change its formula profile or implement portfolio/runtime behavior.

**Tech Stack:** Python 3.12 via Codex bundled runtime, pandas, numpy, pytest, existing QuantumRandy safe I/O helpers, existing RandysLab strict4h tests.

---

## Execution Setup

Use the Codex bundled Python runtime for all verification:

```bash
PY=/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3
```

The user selected linear execution in the current session and prior v0.9 commits were made directly on `main`. Before implementation, verify both repositories are clean and aligned:

```bash
git -C /Users/rosebrain-2/Projects/Quant/QuantumRandy status --short --branch
git -C /Users/rosebrain-2/Projects/Quant/RandysLab-STRICT4H status --short --branch
```

Expected: both print `## main...origin/main` with no file rows.

Baseline commands:

```bash
$PY -m pytest -q
```

Run from `/Users/rosebrain-2/Projects/Quant/QuantumRandy`.

Expected baseline before Task 1 implementation: `110 passed, 8 failed`, with direct failures in the SciPy-backed
Spearman path and downstream portfolio/universe failures caused by swallowed metric exceptions.

```bash
$PY -m pytest -q
```

Run from `/Users/rosebrain-2/Projects/Quant/RandysLab-STRICT4H`.

Expected baseline: `29 passed`.

## File Structure

QuantumRandy files:

- Create `quantumrandy/stats.py`: SciPy-free conservative correlation helpers.
- Modify `quantumrandy/backtest.py`: use `spearman_corr` for `rank_ic`.
- Modify `quantumrandy/lab.py`: use `spearman_corr` for horizon-decay half-life scoring.
- Create `tests/test_stats.py`: focused rank-correlation tests.
- Modify `tests/test_smoke.py`: regression test proving `summarize_ledger` rank IC works under the bundled runtime.
- Create `quantumrandy/feature_readiness.py`: read-only public crypto-native feature audit.
- Create `scripts/crypto_feature_readiness.py`: CLI wrapper that writes CSV, JSON, Markdown, and events.
- Create `tests/test_feature_readiness.py`: readiness audit tests.
- Create `docs/RESEARCH_1_0_PREREQUISITE_VERIFICATION_REPORT.md`: tracked final report.
- Modify `docs/README.md`: add the new report to current research docs.
- Modify `docs/PROJECT_LOG.md`: add the prerequisite-closure entry.

RandysLab files:

- No source modifications expected.
- Use current tests and docs as verification evidence only.

Generated ignored artifacts:

- `reports/research_1_0_feature_readiness/crypto_feature_readiness.csv`
- `reports/research_1_0_feature_readiness/crypto_feature_readiness_manifest.json`
- `reports/research_1_0_feature_readiness/CRYPTO_FEATURE_READINESS_REPORT.md`
- `reports/research_1_0_feature_readiness/events.jsonl`

### Task 1: Establish Baseline And TDD Red Tests

**Files:**
- Create: `tests/test_stats.py`
- Modify: `tests/test_smoke.py`

- [ ] **Step 1: Verify clean repository state**

Run:

```bash
git status --short --branch
git -C /Users/rosebrain-2/Projects/Quant/RandysLab-STRICT4H status --short --branch
```

Expected:

```text
## main...origin/main
## main...origin/main
```

- [ ] **Step 2: Re-run QuantumRandy baseline**

Run:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest -q
```

Expected: current QuantumRandy baseline remains `110 passed, 8 failed`. Preserve the exact failure count in notes for
the final report.

- [ ] **Step 3: Re-run RandysLab baseline**

Run from `/Users/rosebrain-2/Projects/Quant/RandysLab-STRICT4H`:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest -q
```

Expected: `29 passed`.

- [ ] **Step 4: Write the failing stats tests**

Create `tests/test_stats.py`:

```python
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quantumrandy.stats import finite_float, spearman_corr


def test_spearman_corr_uses_rank_correlation_without_scipy() -> None:
    left = pd.Series([1.0, 2.0, 3.0, 4.0])
    right = pd.Series([10.0, 5.0, 2.0, -1.0])

    assert spearman_corr(left, right) == pytest.approx(-1.0)


def test_spearman_corr_returns_zero_for_constant_or_too_short_inputs() -> None:
    assert spearman_corr(pd.Series([1.0]), pd.Series([2.0])) == 0.0
    assert spearman_corr(pd.Series([1.0, 1.0, 1.0]), pd.Series([1.0, 2.0, 3.0])) == 0.0


def test_finite_float_converts_nan_and_infinity_to_zero() -> None:
    assert finite_float(np.nan) == 0.0
    assert finite_float(np.inf) == 0.0
    assert finite_float(-np.inf) == 0.0
    assert finite_float(0.25) == 0.25
```

- [ ] **Step 5: Add the summarize_ledger regression test**

Append this test to `tests/test_smoke.py`:

```python
def test_summarize_ledger_rank_ic_is_scipy_free() -> None:
    idx = pd.date_range("2024-01-01", periods=5, freq="4h", tz="UTC")
    ledger = pd.DataFrame(
        {
            "factor": [1.0, 2.0, 3.0, 4.0, 5.0],
            "r_mkt": [0.0, 0.04, 0.03, 0.02, 0.01],
            "r_net": 0.0,
            "delta_exposure": 0.0,
        },
        index=idx,
    )

    metrics = summarize_ledger(ledger, bar_hours=4)

    assert metrics["predictive_observations"] == 4.0
    assert metrics["rank_ic"] == pytest.approx(-1.0)
```

- [ ] **Step 6: Run the red tests**

Run:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest tests/test_stats.py tests/test_smoke.py::test_summarize_ledger_rank_ic_is_scipy_free -q
```

Expected: failure because `quantumrandy.stats` does not exist yet, or because the current Spearman path imports SciPy.

### Task 2: Implement SciPy-Free Spearman Metrics

**Files:**
- Create: `quantumrandy/stats.py`
- Modify: `quantumrandy/backtest.py`
- Modify: `quantumrandy/lab.py`
- Test: `tests/test_stats.py`
- Test: `tests/test_smoke.py`

- [ ] **Step 1: Create the stats helper**

Create `quantumrandy/stats.py`:

```python
from __future__ import annotations

import numpy as np
import pandas as pd


def finite_float(value: object, default: float = 0.0) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if np.isfinite(out) else default


def pearson_corr(left: pd.Series, right: pd.Series) -> float:
    frame = pd.concat([left, right], axis=1).replace([np.inf, -np.inf], np.nan).dropna()
    if len(frame) < 2:
        return 0.0
    first = frame.iloc[:, 0].astype(float)
    second = frame.iloc[:, 1].astype(float)
    if float(first.std(ddof=0)) <= 0.0 or float(second.std(ddof=0)) <= 0.0:
        return 0.0
    return finite_float(first.corr(second))


def spearman_corr(left: pd.Series, right: pd.Series) -> float:
    frame = pd.concat([left, right], axis=1).replace([np.inf, -np.inf], np.nan).dropna()
    if len(frame) < 2:
        return 0.0
    left_rank = frame.iloc[:, 0].astype(float).rank(method="average")
    right_rank = frame.iloc[:, 1].astype(float).rank(method="average")
    return pearson_corr(left_rank, right_rank)
```

- [ ] **Step 2: Wire `summarize_ledger` to the helper**

Modify imports and metric lines in `quantumrandy/backtest.py`:

```python
from .stats import finite_float, pearson_corr, spearman_corr
```

Replace:

```python
    ic = float(predictive_factor.corr(predictive_return)) if has_variation else 0.0
    rank_ic = float(predictive_factor.corr(predictive_return, method="spearman")) if has_variation else 0.0
```

with:

```python
    return_has_variation = len(predictive_return) > 1 and predictive_return.std(ddof=0) > 0
    ic = pearson_corr(predictive_factor, predictive_return) if has_variation and return_has_variation else 0.0
    rank_ic = spearman_corr(predictive_factor, predictive_return) if has_variation and return_has_variation else 0.0
```

Replace the returned metric normalizers:

```python
        "ic": 0.0 if np.isnan(ic) else ic,
        "rank_ic": 0.0 if np.isnan(rank_ic) else rank_ic,
        "directional_win_rate": 0.0 if np.isnan(directional_win_rate) else directional_win_rate,
```

with:

```python
        "ic": finite_float(ic),
        "rank_ic": finite_float(rank_ic),
        "directional_win_rate": finite_float(directional_win_rate),
```

- [ ] **Step 3: Wire `estimate_halflife_bars` to the helper**

Modify imports in `quantumrandy/lab.py`:

```python
from .stats import spearman_corr
```

Replace `estimate_halflife_bars` with:

```python
def estimate_halflife_bars(factor: pd.Series, returns: pd.Series, max_horizon: int = 42) -> int:
    base = abs(spearman_corr(factor, returns.shift(-1)))
    if base <= 1e-9:
        return 0
    for horizon in range(2, max_horizon + 1):
        corr = abs(spearman_corr(factor, returns.shift(-horizon)))
        if corr <= base * 0.5:
            return horizon
    return max_horizon
```

- [ ] **Step 4: Run focused green tests**

Run:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest tests/test_stats.py tests/test_smoke.py tests/test_runtime.py -q
```

Expected: pass.

- [ ] **Step 5: Run former failure cluster**

Run:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest tests/test_portfolio.py tests/test_portfolio_universe.py tests/test_selector_pipeline.py tests/test_universe.py -q
```

Expected: pass.

- [ ] **Step 6: Commit Spearman robustness**

Run:

```bash
git add quantumrandy/stats.py quantumrandy/backtest.py quantumrandy/lab.py tests/test_stats.py tests/test_smoke.py
git commit -m "Make research rank metrics scipy-free"
```

### Task 3: Add Crypto-Native Feature Readiness Audit

**Files:**
- Create: `quantumrandy/feature_readiness.py`
- Create: `scripts/crypto_feature_readiness.py`
- Create: `tests/test_feature_readiness.py`

- [ ] **Step 1: Write feature-readiness tests**

Create `tests/test_feature_readiness.py`:

```python
from __future__ import annotations

from pathlib import Path

import pandas as pd

from quantumrandy.feature_readiness import (
    CRYPTO_FEATURE_SPECS,
    feature_readiness_manifest,
    feature_readiness_report,
    run_crypto_feature_readiness,
)


def test_crypto_feature_readiness_marks_missing_sources(tmp_path: Path) -> None:
    frame = run_crypto_feature_readiness([tmp_path])

    assert set(frame["feature"]) == {spec.feature for spec in CRYPTO_FEATURE_SPECS}
    assert set(frame["status"]) == {"missing_source"}
    assert set(frame["point_in_time_ready"]) == {False}
    assert set(frame["formula_profile_action"]) == {"do_not_admit"}
    assert "no local source file matched" in set(frame["reason"]).pop()


def test_crypto_feature_readiness_reports_incomplete_and_complete_schema(tmp_path: Path) -> None:
    pd.DataFrame({"timestamp": ["2024-01-01T00:00:00Z"], "value": [1.0]}).to_csv(
        tmp_path / "BTCUSDT_open_interest.csv",
        index=False,
    )
    pd.DataFrame(
        {
            "timestamp": ["2024-01-01T00:00:00Z"],
            "taker_buy_volume": [10.0],
            "taker_sell_volume": [8.0],
        }
    ).to_csv(tmp_path / "BTCUSDT_taker_imbalance.csv", index=False)

    frame = run_crypto_feature_readiness([tmp_path])
    rows = {row["feature"]: row for row in frame.to_dict(orient="records")}

    assert rows["open_interest"]["status"] == "present_schema_incomplete"
    assert rows["open_interest"]["point_in_time_ready"] is False
    assert "open_interest" in rows["open_interest"]["missing_columns"]
    assert rows["taker_buy_sell_imbalance"]["status"] == "eligible_for_candidate_design"
    assert rows["taker_buy_sell_imbalance"]["point_in_time_ready"] is True
    assert rows["taker_buy_sell_imbalance"]["formula_profile_action"] == "requires_separate_profile_admission"


def test_feature_readiness_manifest_and_report_are_research_only(tmp_path: Path) -> None:
    frame = run_crypto_feature_readiness([tmp_path])

    manifest = feature_readiness_manifest(frame, [tmp_path])
    report = feature_readiness_report(frame, manifest)

    assert manifest["artifact"] == "crypto_feature_readiness"
    assert manifest["research_only"] is True
    assert manifest["ready_for_formula_profile_admission"] is False
    assert "does not download data" in report
    assert "No new base fields are admitted" in report
```

- [ ] **Step 2: Run the red tests**

Run:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest tests/test_feature_readiness.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'quantumrandy.feature_readiness'`.

- [ ] **Step 3: Implement the feature-readiness module**

Create `quantumrandy/feature_readiness.py` with:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class CryptoFeatureSpec:
    feature: str
    description: str
    required_columns: tuple[str, ...]
    filename_patterns: tuple[str, ...]


CRYPTO_FEATURE_SPECS = [
    CryptoFeatureSpec(
        "open_interest",
        "Point-in-time futures open interest.",
        ("timestamp", "open_interest"),
        ("*open_interest*.csv", "*oi*.csv"),
    ),
    CryptoFeatureSpec(
        "basis_perp_spot_spread",
        "Point-in-time perpetual versus spot basis or spread.",
        ("timestamp", "basis"),
        ("*basis*.csv", "*perp_spot*.csv", "*spread*.csv"),
    ),
    CryptoFeatureSpec(
        "funding_term_structure",
        "Multiple contract funding-rate curve or term-structure observations.",
        ("timestamp", "contract", "funding_rate"),
        ("*funding_term_structure*.csv", "*funding_curve*.csv"),
    ),
    CryptoFeatureSpec(
        "liquidation_imbalance",
        "Point-in-time liquidation notional or buy/sell liquidation imbalance.",
        ("timestamp", "long_liquidation_notional", "short_liquidation_notional"),
        ("*liquidation*.csv", "*liquidations*.csv"),
    ),
    CryptoFeatureSpec(
        "taker_buy_sell_imbalance",
        "Point-in-time taker buy and taker sell participation imbalance.",
        ("timestamp", "taker_buy_volume", "taker_sell_volume"),
        ("*taker_imbalance*.csv", "*taker_flow*.csv", "*aggtrade*.csv"),
    ),
    CryptoFeatureSpec(
        "order_book_depth",
        "Point-in-time order-book depth or bid/ask imbalance proxy.",
        ("timestamp", "bid_depth", "ask_depth"),
        ("*order_book*.csv", "*orderbook*.csv", "*depth*.csv"),
    ),
]


def run_crypto_feature_readiness(data_roots: list[str | Path]) -> pd.DataFrame:
    roots = [Path(root) for root in data_roots]
    rows = [_inspect_feature(spec, roots) for spec in CRYPTO_FEATURE_SPECS]
    return pd.DataFrame(rows)


def feature_readiness_manifest(frame: pd.DataFrame, data_roots: list[str | Path]) -> dict[str, object]:
    eligible = int((frame["status"] == "eligible_for_candidate_design").sum()) if not frame.empty else 0
    return {
        "artifact": "crypto_feature_readiness",
        "research_only": True,
        "not_runtime_publish_payload": True,
        "does_not_download_data": True,
        "data_roots": [str(Path(root)) for root in data_roots],
        "feature_count": int(len(frame)),
        "eligible_for_candidate_design_count": eligible,
        "ready_for_formula_profile_admission": False,
        "formula_profile_action": "No new base fields are admitted by this audit.",
        "rows": frame.to_dict(orient="records"),
    }


def feature_readiness_report(frame: pd.DataFrame, manifest: dict[str, object]) -> str:
    status_counts = frame["status"].value_counts().to_dict() if "status" in frame else {}
    lines = [
        "# Crypto-Native Feature Readiness Report",
        "",
        "This is a read-only research artifact. It does not download data, call exchange APIs, store credentials,",
        "publish factors, admit formula fields, or mutate runtime state.",
        "",
        "## Summary",
        "",
        f"- Features checked: `{manifest['feature_count']}`",
        f"- Eligible for candidate design: `{manifest['eligible_for_candidate_design_count']}`",
        f"- Ready for formula profile admission: `{manifest['ready_for_formula_profile_admission']}`",
        "- No new base fields are admitted by this audit.",
        f"- Status counts: `{status_counts}`",
        "",
        "## Features",
        "",
        "| Feature | Status | Point-In-Time Ready | Formula Profile Action | Required Columns | Observed Files | Reason |",
        "|---|---|---:|---|---|---|---|",
    ]
    for row in frame.to_dict(orient="records"):
        lines.append(
            "| "
            f"`{row['feature']}` | `{row['status']}` | `{row['point_in_time_ready']}` | "
            f"`{row['formula_profile_action']}` | `{row['required_columns']}` | "
            f"`{row['observed_files']}` | `{row['reason']}` |"
        )
    lines.extend(
        [
            "",
            "## Formula Profile Decision",
            "",
            "Current admitted formula fields remain `open`, `high`, `low`, `close`, `volume`, and `funding_rate`.",
            "Open interest, basis, funding term structure, liquidations, taker imbalance, and order-book depth remain",
            "outside formula execution until a separate profile-admission pass approves them.",
        ]
    )
    return "\n".join(lines) + "\n"


def _inspect_feature(spec: CryptoFeatureSpec, roots: list[Path]) -> dict[str, object]:
    files = _matching_files(spec, roots)
    required = set(spec.required_columns)
    row = {
        "feature": spec.feature,
        "description": spec.description,
        "status": "missing_source",
        "reason": "no local source file matched expected patterns",
        "observed_files": "",
        "required_columns": ",".join(spec.required_columns),
        "observed_columns": "",
        "missing_columns": ",".join(spec.required_columns),
        "row_count": 0,
        "point_in_time_ready": False,
        "formula_profile_action": "do_not_admit",
    }
    if not files:
        return row

    observed_columns: set[str] = set()
    total_rows = 0
    read_errors: list[str] = []
    for path in files:
        try:
            frame = pd.read_csv(path, nrows=25)
        except Exception as exc:
            read_errors.append(f"{path.name}:{exc}")
            continue
        observed_columns.update(str(column) for column in frame.columns)
        total_rows += len(frame)

    missing = sorted(required - observed_columns)
    row.update(
        {
            "observed_files": ";".join(str(path) for path in files),
            "observed_columns": ",".join(sorted(observed_columns)),
            "missing_columns": ",".join(missing),
            "row_count": int(total_rows),
        }
    )
    if read_errors:
        row["status"] = "present_schema_incomplete"
        row["reason"] = "read errors: " + ";".join(read_errors)
        return row
    if missing:
        row["status"] = "present_schema_incomplete"
        row["reason"] = "missing required columns"
        return row
    row["status"] = "eligible_for_candidate_design"
    row["reason"] = "local source schema contains required point-in-time columns"
    row["point_in_time_ready"] = True
    row["formula_profile_action"] = "requires_separate_profile_admission"
    return row


def _matching_files(spec: CryptoFeatureSpec, roots: list[Path]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for pattern in spec.filename_patterns:
            files.extend(path for path in root.glob(pattern) if path.is_file())
    return sorted(set(files))
```

- [ ] **Step 4: Implement the CLI**

Create `scripts/crypto_feature_readiness.py`:

```python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantumrandy.feature_readiness import (
    feature_readiness_manifest,
    feature_readiness_report,
    run_crypto_feature_readiness,
)
from quantumrandy.io_utils import safe_write_csv, safe_write_json, safe_write_text


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only crypto-native feature readiness audit")
    parser.add_argument("--data-root", action="append", default=[], help="Local data directory to inspect.")
    parser.add_argument("--out", default="reports/research_1_0_feature_readiness", help="Output directory.")
    args = parser.parse_args()

    data_roots = args.data_root or ["../RandysLab-STRICT4H/data"]
    frame = run_crypto_feature_readiness(data_roots)
    manifest = feature_readiness_manifest(frame, data_roots)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    safe_write_csv(out / "crypto_feature_readiness.csv", frame, out / "events.jsonl")
    safe_write_json(out / "crypto_feature_readiness_manifest.json", manifest, out / "events.jsonl")
    safe_write_text(out / "CRYPTO_FEATURE_READINESS_REPORT.md", feature_readiness_report(frame, manifest), out / "events.jsonl")

    print(f"Checked {len(frame)} crypto-native feature groups")
    print(f"Eligible for candidate design: {manifest['eligible_for_candidate_design_count']}")
    print("Formula profile admission: false")
    print(f"Output: {out.resolve()}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run focused green tests**

Run:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest tests/test_feature_readiness.py -q
```

Expected: pass.

- [ ] **Step 6: Generate current feature-readiness artifacts**

Run:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/crypto_feature_readiness.py --data-root ../RandysLab-STRICT4H/data --out reports/research_1_0_feature_readiness
```

Expected:

```text
Checked 6 crypto-native feature groups
Eligible for candidate design: 0
Formula profile admission: false
```

- [ ] **Step 7: Commit feature readiness**

Run:

```bash
git add quantumrandy/feature_readiness.py scripts/crypto_feature_readiness.py tests/test_feature_readiness.py
git commit -m "Add crypto-native feature readiness audit"
```

### Task 4: Produce Research 1.0 Prerequisite Verification Report

**Files:**
- Create: `docs/RESEARCH_1_0_PREREQUISITE_VERIFICATION_REPORT.md`
- Modify: `docs/README.md`
- Modify: `docs/PROJECT_LOG.md`

- [ ] **Step 1: Gather verification evidence**

Run from QuantumRandy:

```bash
git rev-parse --short HEAD
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest -q
```

Run from RandysLab:

```bash
git rev-parse --short HEAD
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest -q
```

Inspect generated readiness summary:

```bash
head -n 20 reports/research_1_0_feature_readiness/CRYPTO_FEATURE_READINESS_REPORT.md
```

Expected:

- QuantumRandy full suite passes after Task 2.
- RandysLab full suite remains `29 passed`.
- Feature-readiness report says no new base fields are admitted.

- [ ] **Step 2: Create the tracked verification report**

Create `docs/RESEARCH_1_0_PREREQUISITE_VERIFICATION_REPORT.md` with these sections and the exact command output from
Step 1. Do not save summary-only evidence where exact counts are available.

```markdown
# Research 1.0 Prerequisite Verification Report

Date: 2026-07-03

Status: prerequisite closure complete, Research 1.0 factor readiness still blocked.

This report is research-only. It is not factor admission, runtime publishing, RandyPortfolio, live trading, or
production regime classification.

## Verdict

`not_ready_for_research_1_0`

## v0.9 Completion

- v0.9a: complete.
- v0.9b: complete.
- v0.9c: complete.

## Engineering Hygiene

- QuantumRandy rank metrics now compute Spearman rank correlation without requiring SciPy at runtime.
- QuantumRandy full suite evidence: record the exact fresh pytest output from Step 1.
- RandysLab full suite evidence: record the exact fresh pytest output from Step 1.

## Existing Logic Error Audit

- The current Codex bundled Python runtime has pytest and pandas but no SciPy.
- Previous QuantumRandy failures came from pandas importing SciPy for `Series.corr(method="spearman")`.
- The direct metric path and downstream portfolio/universe paths are covered by focused and full-suite tests.
- Config data paths are resolved relative to config files by `load_config`, so `../../RandysLab-STRICT4H/data` in
  config YAMLs resolves to the local RandysLab data directory.

## Crypto-Native Feature Readiness

- Artifact path: `reports/research_1_0_feature_readiness`.
- Open interest: record the status from `crypto_feature_readiness.csv`.
- Basis/perp-spot spread: record the status from `crypto_feature_readiness.csv`.
- Funding term structure: record the status from `crypto_feature_readiness.csv`.
- Liquidation imbalance: record the status from `crypto_feature_readiness.csv`.
- Taker buy/sell imbalance: record the status from `crypto_feature_readiness.csv`.
- Order-book depth: record the status from `crypto_feature_readiness.csv`.
- Formula profile decision: no new base fields are admitted.

## Declared Scope And Formula Profile Alignment

- v0.9a/v0.9b/v0.9c exports preserve `intended_scope`, `applicability_hypothesis`, and `out_of_scope_policy`.
- RandysLab declared-scope review consumed those fields with `scope_mode=declared`.
- RandysLab supported formula fields remain `open`, `high`, `low`, `close`, `volume`, and `funding_rate`.

## Strict Factor-Family Status

- v0.9c tested 9 scoped BTCUSDT 4h current-DSL candidates.
- RandysLab blocked all 9 under conservative rules.
- No strict-surviving robust candidate family exists yet.

## Boundary Confirmation

- No RandyPortfolio implementation.
- No live trading.
- No exchange private keys.
- No runtime factor publishing.
- No automatic factor admission.
- No new formula base fields.
- No selector evidence61.
```

Before saving, every evidence line above must contain concrete values such as `125 passed`, `29 passed`, or
`missing_source`.

- [ ] **Step 3: Update docs index**

Add one bullet to `docs/README.md` under Current Research:

```markdown
- `RESEARCH_1_0_PREREQUISITE_VERIFICATION_REPORT.md`: post-v0.9 prerequisite closure, logic-error audit,
  crypto-native feature-readiness verdict, and Research 1.0 blocker status.
```

- [ ] **Step 4: Update project log**

Add a new top entry to `docs/PROJECT_LOG.md`:

```markdown
## 2026-07-03 Research 1.0 Prerequisite Closure

Closed the post-v0.9 engineering and readiness prerequisites that can be completed without inventing strict factor
evidence.

- Report: `docs/RESEARCH_1_0_PREREQUISITE_VERIFICATION_REPORT.md`.
- Fixed QuantumRandy rank-correlation metrics so Research tests do not require SciPy at runtime.
- Added a read-only crypto-native feature-readiness audit for open interest, basis, funding term structure,
  liquidations, taker imbalance, and order-book depth.
- No new formula base fields were admitted.
- Research 1.0 readiness remains blocked because no strict-surviving robust factor family exists yet.

Boundary preserved: no RandyPortfolio implementation, no live trading, no exchange private keys, no runtime factor
publishing, no automatic factor admission, no new base formula fields, and no selector evidence61.
```

- [ ] **Step 5: Check report markers**

Run:

```bash
rg -n "record the status|record the exact|<|>" docs/RESEARCH_1_0_PREREQUISITE_VERIFICATION_REPORT.md
```

Expected: no output.

- [ ] **Step 6: Commit report and docs**

Run:

```bash
git add docs/RESEARCH_1_0_PREREQUISITE_VERIFICATION_REPORT.md docs/README.md docs/PROJECT_LOG.md
git commit -m "Report Research 1.0 prerequisite verification"
```

### Task 5: Final Verification And GitHub Push

**Files:**
- Verify all touched files and repository state.

- [ ] **Step 1: Run QuantumRandy full verification**

Run:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest -q
git diff --check
git status --short --branch
```

Expected:

- pytest exits 0.
- `git diff --check` exits 0.
- status is clean except ahead-of-origin commits before push.

- [ ] **Step 2: Run RandysLab full verification**

Run from `/Users/rosebrain-2/Projects/Quant/RandysLab-STRICT4H`:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest -q
git diff --check
git status --short --branch
```

Expected:

- `29 passed`.
- diff check exits 0.
- repository remains clean.

- [ ] **Step 3: Push QuantumRandy commits**

Run from QuantumRandy:

```bash
git push
```

Expected: local commits push to `origin/main`.

- [ ] **Step 4: Confirm pushed state**

Run:

```bash
git status --short --branch
git log --oneline -5
```

Expected: `## main...origin/main` and the three new commits visible near the top:

- `Make research rank metrics scipy-free`
- `Add crypto-native feature readiness audit`
- `Report Research 1.0 prerequisite verification`

## Plan Self-Review

- Spec coverage: Tasks cover Spearman robustness, feature readiness, declared-scope/profile evidence, final report,
  tests, docs, commits, and push.
- Placeholder scan: the plan contains no final-artifact placeholders; Task 4 requires concrete command output before
  saving the tracked report.
- Type consistency: feature-readiness function and manifest names match across tests, module, and CLI.
- Scope check: no RandysLab source changes, no RandyPortfolio, no live trading, no runtime publish, no new base-field
  admission, and no selector evidence61.
