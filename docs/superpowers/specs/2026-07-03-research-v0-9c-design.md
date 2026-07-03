# Research v0.9c BTCUSDT Scoped Multi-Factor Bundle Design

Date: 2026-07-03

## Status

Approved direction: current-DSL scoped bundle.

This design defines Research v0.9c only. It is research-only. It is not factor admission, not runtime publishing, not
portfolio construction, not RandyPortfolio implementation, and not live execution.

## Context

Research v0.9a verified the scoped export and RandysLab declared-scope strict-review contract. Research v0.9b used that
contract for one BTCUSDT 4h funding-pressure family and produced a conservative verdict of
`blocked_pending_new_hypotheses`.

Research v0.9c now tests the next shape required by `docs/V0_9_RESEARCH_EXECUTION_PLAN.md`: a BTCUSDT 4h scoped
multi-factor research bundle with explicit applicability boundaries, redundancy review, strict declared-scope judging,
failure memory, and a Research 1.0 readiness verdict.

## Design Decision

Use the current formula DSL and current local data only:

```text
open, high, low, close, volume, funding_rate
```

The pass will not add `open_interest`, basis, liquidation, taker-flow, or order-book fields. Those remain outside the
formula base-field set until a separate point-in-time data-readiness audit accepts them. The v0.9c report will document
this as the regime/public-feature readiness decision for this checkpoint.

## Candidate Families

QuantumRandy will export a deterministic v0.9c candidate set scoped to `BTCUSDT_4h`. The set has single factors from
distinct current-DSL families plus equal-weight component bundles. Exact formulas are fixed so the run is reproducible.

Single-factor candidates:

| Candidate | Family | Formula | Hypothesis |
|---|---|---|---|
| `qr_v09c_liquidity_001` | `liquidity_participation` | `zscore(div(volume,sma(volume,48)),120)` | Relative volume participation may identify BTCUSDT liquidity bursts that precede persistent 4h moves. |
| `qr_v09c_range_001` | `range_compression` | `neg(zscore(div(sub(high,low),close),96))` | Compressed 4h range may mark calmer BTCUSDT states where simple continuation or carry signals are less drawdown-prone. |
| `qr_v09c_trend_001` | `price_trend` | `zscore(ret(close,24),96)` | Medium-horizon BTCUSDT trend may help distinguish persistent direction from funding-only crowding noise. |
| `qr_v09c_reversal_001` | `short_horizon_reversal` | `neg(zscore(ret(close,6),72))` | Short-horizon BTCUSDT overextension may mean-revert after next-bar execution costs. |
| `qr_v09c_funding_001` | `funding_pressure_crowding` | `neg(zscore(div(funding_rate,std(close,48)),96))` | Funding pressure scaled by realized volatility may preserve the least direct v0.9b crowding signal as one component. |
| `qr_v09c_price_volume_001` | `price_volume_confirmation` | `zscore(corr(volume,ret(close,12),48),72)` | Volume-return correlation may mark participation-confirmed BTCUSDT moves without copying selector v0.8.2 formulas. |

Bundle candidates:

| Candidate | Family | Components |
|---|---|---|
| `qr_v09c_bundle_diversified_001` | `scoped_equal_weight_bundle` | liquidity participation, range compression, funding pressure, short-horizon reversal |
| `qr_v09c_bundle_trend_crowding_001` | `scoped_equal_weight_bundle` | price trend, funding pressure, price-volume confirmation |
| `qr_v09c_bundle_calm_reversal_001` | `scoped_equal_weight_bundle` | range compression, short-horizon reversal, funding pressure |

Every candidate record will include:

- `intended_scope=BTCUSDT_4h`;
- an `applicability_hypothesis`;
- `out_of_scope_policy=diagnostic_only`;
- `research_only=true`;
- `not_runtime_publish_payload=true`;
- `portfolio_interface_contract.status=interface_only_not_implemented`;
- `randyslab_eval_profile=strict4h_v1`;
- `research_checkpoint=v0.9c`;
- for bundles, `component_formulas` and `combination_method=equal_weight_mean`.

The exact single-factor formulas are disjoint from `PRIMARY_SELECTOR_V082_FORMULAS`. v0.9c may reuse the v0.9b funding
pressure idea as one component, but not as a promoted standalone conclusion.

## RandysLab Evaluation

RandysLab will consume the QuantumRandy v0.9c JSONL export directly.

Declared-scope sensitivity:

- Asset: `BTCUSDT:data/BTCUSDT_4h.csv:data/BTCUSDT_funding.csv`.
- Windows: `all`, `training`, `validation`, `long`, `blind`.
- Thresholds: `0.0`, `0.5`, `1.0`.
- Signal modes: `long_short`, `long_flat`, `short_flat`.
- Scope mode for review: `declared`.

Bundle diagnostics:

- Evaluate the same JSONL records, including `component_formulas`.
- Treat equal-weight bundles as research signals only, not portfolio weights.
- Add a simple gated diagnostic sweep for bundle rows only if the first declared review identifies a credible row:
  exposure caps `1.0` and `0.5`, and a current-DSL calm-volatility gate based on `zscore(std(close,48),144) <= 1.5`.
- Do not tune drawdown stops in v0.9c. Drawdown-stop or cooldown mitigation would be a separate pass.

## Correlation And Redundancy Review

v0.9c must decide whether the bundle is actually diversified. RandysLab will compute factor values for the exported
single-factor components on BTCUSDT 4h data and write a correlation/redundancy artifact:

- pairwise Pearson correlation on aligned non-NaN factor values;
- overlap count per pair;
- `abs_corr_ge_0p80` flag;
- same-family flag;
- bundle component coverage table;
- redundancy verdict per bundle:
  - `diversified_enough_for_research` when no pair exceeds `0.80`;
  - `redundant_research_memory_only` when high-correlation pairs dominate.

Correlation review is diagnostic evidence only. It does not admit factors or construct a production portfolio.

## Failure Memory

QuantumRandy will convert RandysLab review rows into v0.9c failure memory. Failure labels must preserve:

- strict review gate failures such as `low_mean_sharpe`, `weak_validation_window`, `weak_blind_window`,
  `high_mean_drawdown`, and `extreme_row_drawdown`;
- bundle-specific labels such as `bundle_redundancy`, `component_crowding_overlap`, `trend_reversal_conflict`,
  `funding_pressure_fragility`, and `validation_bundle_fragility`.

If a row earns `research_watchlist`, the QuantumRandy conservative verdict is `scoped_watchlist`. Otherwise it is
`blocked_pending_new_hypotheses` or `research_memory_only`, depending on whether the row is a useful diagnostic pattern
with failed gates.

## Report And Research 1.0 Readiness

QuantumRandy will write a tracked v0.9c report:

```text
docs/RESEARCH_V0_9C_MULTI_FACTOR_BUNDLE_REPORT.md
```

The report must include:

- v0.9a and v0.9b dependency confirmation;
- candidate formulas and bundle component tables;
- export, sensitivity, review, correlation, and failure-memory artifact paths;
- declared-scope review counts and verdict counts;
- top factor and bundle rows with conservative verdicts;
- correlation/redundancy verdict;
- public/regime feature readiness decision for v0.9c;
- Research 1.0 readiness verdict:
  - `not_ready_for_research_1_0` if no scoped bundle survives strict gates and redundancy review;
  - `research_1_0_candidate_pending_replication` only if at least one scoped bundle survives strict gates, is not
    redundant, and has acceptable validation/blind behavior.

## Tests And Verification

Focused QuantumRandy checks:

```bash
python3 -m pytest tests/test_factor_candidate_export.py tests/test_v0_9b_funding_pressure.py tests/test_v0_9c_bundle.py -q
```

Focused RandysLab checks:

```bash
python3 -m pytest tests/test_formula_candidates.py tests/test_factor_candidate_correlation.py -q
```

Repository checks:

- RandysLab full suite must pass.
- QuantumRandy full suite must be run. Existing unrelated full-suite failures may be documented only if focused v0.9c
  tests pass and the failures remain outside the v0.9c path.
- `git diff --check` must pass before commit.

## Boundaries

v0.9c must not:

- implement RandyPortfolio;
- create a portfolio scheduler;
- submit or simulate live orders;
- use exchange private keys;
- publish runtime factors;
- auto-admit factors;
- add new formula base fields;
- run selector evidence61;
- tune drawdown-stop or cooldown mitigation as part of this first bundle pass.

## Completion Criteria

v0.9c is complete when:

- QuantumRandy exports the deterministic scoped v0.9c candidate and bundle JSONL/CSV/manifest/report artifacts;
- RandysLab declared-scope sensitivity and review are generated for factor and bundle rows;
- correlation/redundancy review is generated;
- QuantumRandy failure memory is generated from the v0.9c review;
- `docs/RESEARCH_V0_9C_MULTI_FACTOR_BUNDLE_REPORT.md` states conservative verdicts and Research 1.0 readiness;
- docs index and project log are updated;
- focused tests and RandysLab full tests pass, with any QuantumRandy residual failures explicitly scoped;
- both repositories are clean or have an explicit commit plan;
- no boundary above is violated.
