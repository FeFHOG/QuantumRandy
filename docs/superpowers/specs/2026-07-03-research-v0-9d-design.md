# Research v0.9d Strict Candidate-Family Discovery Design

Date: 2026-07-03

## Status

Approved direction: BTC primary plus ETH diagnostic strict candidate-family discovery.

This design covers Research v0.9d only. It is research-only. It is not factor admission, not runtime publishing, not
portfolio construction, not RandyPortfolio implementation, not live trading, and not production regime classification.

## Context

Research v0.9a, v0.9b, and v0.9c are complete. The Research 1.0 prerequisite verification pass closed the current
engineering and public-feature readiness gaps:

- QuantumRandy full suite: `125 passed`;
- RandysLab full suite: `29 passed`;
- crypto-native feature readiness: all six checked groups are `missing_source`;
- no new formula base fields are admitted.

The remaining Research 1.0 blocker is research evidence:

```text
no strict-surviving robust candidate family
```

v0.9b direct funding-pressure candidates failed mainly through drawdown and blind-window fragility. v0.9c current-DSL
single factors and bundles all failed conservative review, with labels for validation weakness, blind weakness,
drawdown fragility, extreme-row drawdown, bundle redundancy, and trend/reversal conflict.

v0.9d therefore tests new current-DSL hypothesis families. It must not repackage v0.9b/v0.9c failures as success.

## Approach Options Considered

### Option A: BTC Primary Plus ETH Diagnostic

Use BTCUSDT 4h as the declared primary scope and ETHUSDT 4h as the first diagnostic stress scope. If a BTC row earns
`research_watchlist`, ETH evidence is used to label portability and crash sensitivity, not to auto-promote or auto-block
the BTC-scoped result.

This is the selected approach because it can discover a scoped BTC survivor without hiding ETH weakness.

### Option B: BTC/ETH Core Declared Scope

Declare `BTC_ETH_core_4h` and require both assets to pass the strict review at once.

This is more directly aligned with crash robustness, but it is likely too strict for the next discovery pass and may
repeat the current blocked state without isolating which hypothesis families are useful.

### Option C: LLM Mining Or Broad Formula Search

Run broader automated discovery from failure memory.

This may produce more candidates, but it weakens reproducibility and increases the risk of post-hoc filtering. It is
deferred until the deterministic v0.9d pass is complete.

## Design Decision

Use a deterministic, pre-registered current-DSL candidate set:

- primary declared scope: `BTCUSDT_4h`;
- diagnostic scope: `ETHUSDT_4h`;
- current formula fields only: `open`, `high`, `low`, `close`, `volume`, `funding_rate`;
- current RandysLab-supported operators only:
  `zscore`, `ema`, `sma`, `std`, `ret`, `delta`, `corr`, `rsi`, `min`, `max`, `sign`, `add`, `sub`, `mul`, `div`,
  `neg`, `abs`, `log`, and `sqrt`;
- no `rank`, `skew`, `kurtosis`, `clip`, `winsorize`, `delay`, or other functions that are not admitted in RandysLab;
- no new base fields;
- no drawdown-stop or cooldown tuning in the first v0.9d pass.

## Candidate Families

QuantumRandy will export nine single-factor candidates and three equal-weight bundle candidates.

Single-factor candidates:

| Candidate | Family | Formula | Hypothesis |
|---|---|---|---|
| `qr_v09d_trend_efficiency_001` | `trend_quality_efficiency` | `zscore(div(ret(close,24),div(sub(max(high,48),min(low,48)),close)),96)` | BTC directional moves that earn return per recent high-low range may persist better than raw trend. |
| `qr_v09d_trend_persistence_001` | `trend_persistence_alignment` | `zscore(corr(ret(close,6),ret(close,24),48),96)` | Alignment between short and medium returns may distinguish persistent direction from noisy reversals. |
| `qr_v09d_intrabar_conviction_001` | `intrabar_conviction` | `zscore(div(sub(close,open),sub(high,low)),72)` | Closing location inside the 4h bar may encode participation-backed directional conviction. |
| `qr_v09d_range_position_001` | `range_position_trend` | `zscore(div(sub(close,sma(close,48)),sub(max(high,48),min(low,48))),96)` | Price location inside a rolling range may capture trend state without raw breakout chasing. |
| `qr_v09d_rsi_state_change_001` | `rsi_state_change` | `zscore(delta(rsi(close,24),12),72)` | Changes in RSI state may identify improving or deteriorating directional pressure. |
| `qr_v09d_liquidity_adjusted_momentum_001` | `liquidity_adjusted_momentum` | `zscore(div(ret(close,24),div(volume,sma(volume,96))),120)` | Momentum adjusted for relative volume may avoid participation-only and raw-return traps. |
| `qr_v09d_vol_adjusted_trend_001` | `volatility_adjusted_trend` | `zscore(div(sub(ema(close,24),ema(close,96)),std(close,48)),120)` | EMA trend scaled by realized volatility may reduce raw trend drawdown. |
| `qr_v09d_funding_return_long_001` | `funding_return_long_horizon` | `zscore(corr(funding_rate,ret(close,42),120),72)` | Long-horizon funding/return alignment may diagnose positioning pressure without direct funding mean reversion. |
| `qr_v09d_volume_conviction_001` | `volume_price_conviction` | `zscore(corr(sub(close,open),volume,48),72)` | Correlation between intrabar price change and volume may capture participation-backed direction. |

Bundle candidates:

| Candidate | Family | Components |
|---|---|---|
| `qr_v09d_bundle_trend_quality_001` | `scoped_equal_weight_bundle` | trend efficiency, trend persistence, intrabar conviction |
| `qr_v09d_bundle_liquidity_direction_001` | `scoped_equal_weight_bundle` | volume conviction, liquidity-adjusted momentum, volatility-adjusted trend |
| `qr_v09d_bundle_funding_confirmation_001` | `scoped_equal_weight_bundle` | funding-return long horizon, trend efficiency, intrabar conviction |

Every candidate record will include:

- `research_checkpoint=v0.9d`;
- `research_only=true`;
- `not_runtime_publish_payload=true`;
- `intended_scope=BTCUSDT_4h`;
- `applicability_hypothesis`;
- `out_of_scope_policy=diagnostic_only`;
- `portfolio_interface_contract.status=interface_only_not_implemented`;
- `randyslab_eval_profile=strict4h_v1`;
- `expected_failure_mode`;
- for bundles, `component_candidate_ids`, `component_formulas`, and `combination_method=equal_weight_mean`.

## RandysLab Evaluation

Primary declared review:

- Asset: `BTCUSDT:data/BTCUSDT_4h.csv:data/BTCUSDT_funding.csv`.
- Scope mode: `declared`.
- Windows: `all`, `training`, `validation`, `long`, `blind`.
- Thresholds: `0.0`, `0.5`, `1.0`.
- Signal modes: `long_short`, `long_flat`.
- Exposure caps: `1.0`, `0.5`.
- Volatility caps:
  - `none`;
  - `calm_vol_lte_1p5:zscore(std(close,48),144):1.5`.
- Drawdown stops: `none`.

ETH diagnostic review:

- Asset: `ETHUSDT:data/ETHUSDT_4h.csv:data/ETHUSDT_funding.csv`.
- Same fixed grid as BTC primary.
- Scope mode remains `declared`; ETH rows are diagnostic evidence for portability and failure labels.

Optional wider diagnostic, if a BTC row earns `research_watchlist`:

- Assets: SOLUSDT, BNBUSDT, AVAXUSDT.
- Use the same candidate export and a smaller grid: windows `all`, `validation`, `blind`; threshold `0.5`;
  signal modes `long_short`, `long_flat`; exposure caps `1.0`, `0.5`; volatility cap `none`.
- This wider diagnostic does not auto-admit or runtime-publish any candidate.

## Correlation And Redundancy Review

RandysLab will compute v0.9d pairwise and bundle correlation on BTCUSDT 4h:

- high-correlation threshold: `0.80`;
- pairwise Pearson correlation on aligned factor values;
- bundle redundancy verdict:
  - `diversified_enough_for_research`;
  - `redundant_research_memory_only`.

Bundle candidates cannot be treated as Research 1.0 candidates if they are redundant, even if their review row is strong.

## Failure Memory

QuantumRandy will convert v0.9d review and correlation artifacts into failure memory. Labels must preserve:

- `low_mean_sharpe`;
- `low_median_sharpe`;
- `low_positive_row_share`;
- `weak_validation_window`;
- `weak_blind_window`;
- `drawdown_fragility`;
- `extreme_row_drawdown`;
- `eth_diagnostic_weakness`;
- `funding_confirmation_fragility`;
- `trend_quality_fragility`;
- `liquidity_adjusted_momentum_fragility`;
- `intrabar_conviction_fragility`;
- `bundle_redundancy`;
- `component_overlap`.

## Research 1.0 Decision Rules

v0.9d can only change the Research 1.0 verdict if evidence supports it.

Possible outcomes:

- `research_1_0_candidate_pending_replication`: at least one candidate or non-redundant bundle earns
  `research_watchlist` in BTC declared review, has acceptable validation and blind behavior under the registered grid,
  and does not have a contradiction severe enough to invalidate the declared scope.
- `scoped_watchlist_needs_replication`: a BTC candidate earns `research_watchlist`, but ETH diagnostics or redundancy
  evidence require more replication before Research 1.0.
- `not_ready_for_research_1_0`: no candidate earns a strict BTC declared-scope watchlist, or all watchlist rows are
  redundant/fragile after diagnostic review.

No result in v0.9d is factor admission, runtime publishing, live execution approval, or portfolio allocation.

## Report

QuantumRandy will write:

```text
docs/RESEARCH_V0_9D_STRICT_CANDIDATE_DISCOVERY_REPORT.md
```

The report must include:

- dependency confirmation from v0.9a-v0.9c and prerequisite verification;
- candidate and bundle tables;
- export, sensitivity, review, correlation, diagnostic, and failure-memory artifact paths;
- BTC primary review verdict counts;
- ETH diagnostic verdict counts;
- optional wider diagnostic counts when run;
- correlation/redundancy verdicts;
- failure-memory summary;
- explicit Research 1.0 readiness verdict;
- boundary confirmation.

## Tests And Verification

QuantumRandy focused tests:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest tests/test_v0_9d_discovery.py -q
```

RandysLab focused tests:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest tests/test_formula_candidates.py tests/test_factor_candidate_correlation.py -q
```

Repository verification:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest -q
git diff --check
```

Run repository verification in both QuantumRandy and RandysLab before final reporting.

## Boundaries

v0.9d must not:

- implement RandyPortfolio;
- create a portfolio scheduler;
- run live trading;
- use exchange private keys;
- publish runtime factors;
- auto-admit factors;
- add production regime labels;
- add new formula base fields;
- run selector evidence61;
- tune drawdown-stop/cooldown as part of the first discovery pass;
- treat ETH or wider diagnostics as production portfolio filters.

## Completion Criteria

v0.9d is complete when:

- QuantumRandy exports the deterministic v0.9d candidate JSONL, CSV, manifest, and Markdown artifacts;
- RandysLab primary BTC declared-scope sensitivity and review artifacts are generated;
- RandysLab ETH diagnostic sensitivity and review artifacts are generated;
- RandysLab correlation/redundancy review is generated;
- optional wider diagnostics are generated if and only if BTC primary review produces a watchlist row;
- QuantumRandy v0.9d failure memory is generated;
- `docs/RESEARCH_V0_9D_STRICT_CANDIDATE_DISCOVERY_REPORT.md` records the conservative verdict;
- docs index and project log are updated;
- focused and full repository tests pass in both repositories;
- both repositories are clean or have pushed commits;
- no boundary above is violated.

## Spec Self-Review

- Placeholder scan: no placeholders remain.
- Internal consistency: v0.9d tests deterministic candidate families under fixed pre-registered review rules.
- Scope check: this is one implementation plan spanning QuantumRandy export/report/failure memory plus RandysLab
  artifact generation; RandysLab source changes are not expected.
- Ambiguity check: Research 1.0 readiness is conditional on strict evidence; if no survivor appears, the verdict remains
  `not_ready_for_research_1_0`.
