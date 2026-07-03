# Research 1.0 Prerequisite Verification Report

Date: 2026-07-03

Status: prerequisite closure complete; Research 1.0 factor readiness remains blocked.

This report is research-only. It is not factor admission, runtime publishing, RandyPortfolio, live trading, or
production regime classification.

## Verdict

```text
not_ready_for_research_1_0
```

Research 1.0 is still blocked because no strict-surviving robust candidate family exists yet. This pass closes the
remaining engineering and data-readiness prerequisites that can be completed without inventing factor evidence.

## v0.9 Completion

- Research v0.9a is complete: scoped schema and RandysLab strict-judge alignment are verified in
  `docs/RESEARCH_V0_9A_VERIFICATION_REPORT.md`.
- Research v0.9b is complete: BTCUSDT 4h funding-pressure single-family review and failure memory are recorded in
  `docs/RESEARCH_V0_9B_FUNDING_PRESSURE_REPORT.md`.
- Research v0.9c is complete: BTCUSDT 4h current-DSL multi-factor bundle review, redundancy review, and failure memory
  are recorded in `docs/RESEARCH_V0_9C_MULTI_FACTOR_BUNDLE_REPORT.md`.

## Repository State

- QuantumRandy code evidence commit before this report: `6f4495e`.
- RandysLab strict judge evidence commit: `ab9c67a`.
- Both repositories were clean and aligned with `origin/main` before implementation.
- QuantumRandy had two local prerequisite-closure commits before this report commit:
  - `a625ce1 Make research rank metrics scipy-free`;
  - `6f4495e Add crypto-native feature readiness audit`.
- RandysLab source was not modified in this pass.

## Engineering Hygiene

Baseline before the fix:

```text
QuantumRandy: 110 passed, 8 failed in 1.80s
RandysLab: 29 passed in 1.58s
```

Root cause:

- The Codex bundled Python runtime has pytest and pandas but no SciPy.
- QuantumRandy declared `scipy>=1.12`, but core research metric code called
  `pandas.Series.corr(method="spearman")`, which imports SciPy inside pandas.
- Direct failures occurred in `summarize_ledger`.
- Portfolio, portfolio-universe, selector-pipeline, and universe failures were downstream effects of the same metric
  exception being raised or swallowed during aggregation.

Fix:

- Added `quantumrandy/stats.py` with conservative `finite_float`, `pearson_corr`, and `spearman_corr` helpers.
- `summarize_ledger` now computes `rank_ic` through rank correlation without requiring SciPy at runtime.
- `estimate_halflife_bars` now uses the same SciPy-free Spearman helper.
- Added regression tests in `tests/test_stats.py` and `tests/test_smoke.py`.

Fresh verification after the fix and feature-readiness implementation:

```text
QuantumRandy: 125 passed in 1.74s
RandysLab: 29 passed in 1.58s
```

Focused evidence:

```text
tests/test_stats.py tests/test_smoke.py tests/test_runtime.py: 24 passed in 0.71s
tests/test_portfolio.py tests/test_portfolio_universe.py tests/test_selector_pipeline.py tests/test_universe.py: 9 passed in 0.30s
tests/test_feature_readiness.py tests/test_data_readiness.py: 13 passed in 0.16s
```

## Existing Logic Error Audit

Resolved issue:

- The SciPy-backed Spearman path was a real reproducibility weakness for the current runtime and caused all eight
  observed QuantumRandy failures.

Checked non-issue:

- `configs/btcusdt.yaml` uses `../../RandysLab-STRICT4H/data/...`, which looks wrong from the repository root.
- `quantumrandy/config.py::load_config` resolves relative paths from the config file directory, so the path resolves to
  `/Users/rosebrain-2/Projects/Quant/RandysLab-STRICT4H/data/...` and exists locally.

Remaining logic status:

- No additional current test failures remain after the Spearman fix.
- No RandyPortfolio, runtime publish, live trading, or formula-profile mutation path was added.

## Crypto-Native Feature Readiness

Artifact path:

```text
reports/research_1_0_feature_readiness
```

Generated files:

- `crypto_feature_readiness.csv`;
- `crypto_feature_readiness_manifest.json`;
- `CRYPTO_FEATURE_READINESS_REPORT.md`;
- `events.jsonl`.

Current local data verdict:

| Feature | Status | Point-In-Time Ready | Formula Profile Action |
|---|---|---:|---|
| `open_interest` | `missing_source` | `False` | `do_not_admit` |
| `basis_perp_spot_spread` | `missing_source` | `False` | `do_not_admit` |
| `funding_term_structure` | `missing_source` | `False` | `do_not_admit` |
| `liquidation_imbalance` | `missing_source` | `False` | `do_not_admit` |
| `taker_buy_sell_imbalance` | `missing_source` | `False` | `do_not_admit` |
| `order_book_depth` | `missing_source` | `False` | `do_not_admit` |

Feature-readiness summary:

```text
Checked 6 crypto-native feature groups
Eligible for candidate design: 0
Formula profile admission: false
```

No new base fields are admitted by this audit.

## Declared Scope And Formula Profile Alignment

Scoped schema evidence:

- v0.9a verifies that QuantumRandy exports carry `intended_scope`, `applicability_hypothesis`, and
  `out_of_scope_policy`.
- v0.9a verifies that RandysLab sensitivity writes those fields into `factor_candidate_sensitivity_detail.csv`.
- v0.9a verifies that RandysLab review rows include those fields plus `scope_mode`.
- v0.9b and v0.9c preserve `scope_mode=declared` in the tracked reports.

Formula profile evidence:

- RandysLab `randyslab/formula_candidates.py` still declares:

```python
SUPPORTED_FIELDS = {"open", "high", "low", "close", "volume", "funding_rate"}
```

- Current RandysLab local 4h data files expose only `timestamp, open, high, low, close, volume`; funding is loaded from
  separate funding CSV files.
- Open interest, basis, funding term structure, liquidations, taker imbalance, and order-book depth remain outside
  formula execution until a separate profile-admission pass approves them.

## Strict Factor-Family Status

v0.9c strict review remains the current factor-family status:

- Candidate count: `9`.
- Single-factor count: `6`.
- Bundle count: `3`.
- Intended scope: `BTCUSDT_4h`.
- Declared-scope review verdict counts: `blocked_by_conservative_rules:9`.
- Failure-memory conservative verdict counts: `blocked_pending_new_hypotheses:8, research_memory_only:1`.

There is still no robust scoped candidate family that survives strict Research 1.0 review gates.

## Research 1.0 Gate Status

| Gate | Status | Evidence |
|---|---|---|
| Candidate export schema | Closed | v0.9a/v0.9b/v0.9c tracked reports. |
| Strict declared-scope judge alignment | Closed | v0.9a/v0.9b/v0.9c tracked reports. |
| Failure-memory loop | Closed | v0.9b and v0.9c failure-memory reports. |
| Repository test hygiene | Closed | QuantumRandy `125 passed`; RandysLab `29 passed`. |
| Public crypto-native feature readiness | Closed as audit, not admitted | Feature audit shows all six groups `missing_source`. |
| Strict-surviving robust factor family | Blocked | v0.9c blocked all 9 candidates. |
| Research 1.0 readiness | Blocked | No strict-surviving robust candidate family exists yet. |

## Boundary Confirmation

- No RandyPortfolio implementation.
- No portfolio scheduler.
- No live trading.
- No exchange private keys.
- No runtime factor publishing.
- No automatic factor admission.
- No production runtime regime labels.
- No new formula base fields.
- No selector evidence61.
