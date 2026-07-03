# Research v0.9d Strict Candidate-Family Discovery Report

Date: 2026-07-03

Status: complete for the BTCUSDT 4h strict candidate-family discovery checkpoint.

This report is research-only. It is not factor admission, runtime publishing, portfolio construction, RandyPortfolio, or live execution.

## Objective

Research v0.9d tested deterministic current-DSL candidate families under the v0.9a scoped schema, v0.9b/v0.9c failure-memory discipline, and RandysLab strict declared-scope review.

## Dependency Confirmation

- Research v0.9a scoped schema and strict-judge alignment are complete.
- Research v0.9b funding-pressure single-family review and failure memory are complete.
- Research v0.9c multi-factor bundle review, redundancy review, and failure memory are complete.
- Research 1.0 prerequisite closure verified the test suites and admitted no new formula base fields.

## Candidate Export

- Export path: `reports/factor_candidate_exports/research_v0_9d_strict_candidate_discovery`
- Candidate count: `12`
- Single-factor count: `9`
- Bundle count: `3`
- Intended scope: `BTCUSDT_4h`
- Out-of-scope policy: `diagnostic_only`

| Candidate | Family | Formula |
|---|---|---|
| `qr_v09d_trend_efficiency_001` | `trend_quality_efficiency` | `zscore(div(ret(close,24),div(sub(max(high,48),min(low,48)),close)),96)` |
| `qr_v09d_trend_persistence_001` | `trend_persistence_alignment` | `zscore(corr(ret(close,6),ret(close,24),48),96)` |
| `qr_v09d_intrabar_conviction_001` | `intrabar_conviction` | `zscore(div(sub(close,open),sub(high,low)),72)` |
| `qr_v09d_range_position_001` | `range_position_trend` | `zscore(div(sub(close,sma(close,48)),sub(max(high,48),min(low,48))),96)` |
| `qr_v09d_rsi_state_change_001` | `rsi_state_change` | `zscore(delta(rsi(close,24),12),72)` |
| `qr_v09d_liquidity_adjusted_momentum_001` | `liquidity_adjusted_momentum` | `zscore(div(ret(close,24),div(volume,sma(volume,96))),120)` |
| `qr_v09d_vol_adjusted_trend_001` | `volatility_adjusted_trend` | `zscore(div(sub(ema(close,24),ema(close,96)),std(close,48)),120)` |
| `qr_v09d_funding_return_long_001` | `funding_return_long_horizon` | `zscore(corr(funding_rate,ret(close,42),120),72)` |
| `qr_v09d_volume_conviction_001` | `volume_price_conviction` | `zscore(corr(sub(close,open),volume,48),72)` |

| Bundle | Components | Method |
|---|---|---|
| `qr_v09d_bundle_trend_quality_001` | `qr_v09d_trend_efficiency_001, qr_v09d_trend_persistence_001, qr_v09d_intrabar_conviction_001` | `equal_weight_mean` |
| `qr_v09d_bundle_liquidity_direction_001` | `qr_v09d_volume_conviction_001, qr_v09d_liquidity_adjusted_momentum_001, qr_v09d_vol_adjusted_trend_001` | `equal_weight_mean` |
| `qr_v09d_bundle_funding_confirmation_001` | `qr_v09d_funding_return_long_001, qr_v09d_trend_efficiency_001, qr_v09d_intrabar_conviction_001` | `equal_weight_mean` |

## BTC Primary Declared Review

- Sensitivity path: `../RandysLab-STRICT4H/reports/factor_candidate_sensitivity/research_v0_9d_btc_primary`
- Sensitivity run count: `120`
- Sensitivity candidate row count: `1440`
- Review path: `../RandysLab-STRICT4H/reports/factor_candidate_review/research_v0_9d_btc_primary`
- Scope mode: `declared`
- `scope_mode=declared`
- Review scopes: `BTCUSDT_4h`
- Candidate count: `288`
- Verdict counts: `blocked_by_conservative_rules:273, research_watchlist:15`

| Candidate | Verdict | Mean Sharpe | Validation Sharpe | Blind Sharpe | Failures |
|---|---|---:|---:|---:|---|
| `qr_v09d_volume_conviction_001` | `research_watchlist` | 0.9613 | 0.3946 | 0.9735 | `none` |
| `qr_v09d_volume_conviction_001` | `research_watchlist` | 0.8877 | 0.0486 | 0.7109 | `none` |
| `qr_v09d_volume_conviction_001` | `research_watchlist` | 0.8873 | 0.3351 | 0.8800 | `none` |
| `qr_v09d_funding_return_long_001` | `research_watchlist` | 0.6877 | 0.2148 | 0.3440 | `none` |
| `qr_v09d_funding_return_long_001` | `research_watchlist` | 0.5979 | 0.1437 | 0.2313 | `none` |
| `qr_v09d_trend_persistence_001` | `research_watchlist` | 0.5924 | 0.1878 | 0.7945 | `none` |
| `qr_v09d_funding_return_long_001` | `research_watchlist` | 0.5412 | 0.4561 | 0.7364 | `none` |
| `qr_v09d_volume_conviction_001` | `research_watchlist` | 0.5403 | 0.3285 | 0.3644 | `none` |
| `qr_v09d_vol_adjusted_trend_001` | `research_watchlist` | 0.5383 | 0.2739 | 0.0248 | `none` |
| `qr_v09d_volume_conviction_001` | `research_watchlist` | 0.4868 | 0.0608 | 0.0564 | `none` |
| `qr_v09d_trend_persistence_001` | `research_watchlist` | 0.4857 | 0.0993 | 0.6645 | `none` |
| `qr_v09d_volume_conviction_001` | `research_watchlist` | 0.4811 | 0.9182 | 0.4366 | `none` |

## ETH Diagnostic Review

ETH diagnostics are portability and fragility evidence only; they do not change the declared BTC scope and do not create production portfolio filters.

- Sensitivity path: `../RandysLab-STRICT4H/reports/factor_candidate_sensitivity/research_v0_9d_eth_diagnostic`
- Sensitivity run count: `120`
- Sensitivity candidate row count: `1440`
- Review path: `../RandysLab-STRICT4H/reports/factor_candidate_review/research_v0_9d_eth_diagnostic`
- Scope mode: `declared`
- Candidate count: `288`
- Verdict counts: `blocked_by_conservative_rules:218, research_watchlist:70`

| Candidate | Verdict | Mean Sharpe | Validation Sharpe | Blind Sharpe | Failures |
|---|---|---:|---:|---:|---|
| `qr_v09d_range_position_001` | `research_watchlist` | 1.2913 | 0.7402 | 1.1727 | `none` |
| `qr_v09d_range_position_001` | `research_watchlist` | 1.2217 | 0.6792 | 1.0895 | `none` |
| `qr_v09d_rsi_state_change_001` | `research_watchlist` | 1.1225 | 0.2420 | 0.5321 | `none` |
| `qr_v09d_funding_return_long_001` | `research_watchlist` | 1.0719 | 0.4122 | 0.3645 | `none` |
| `qr_v09d_trend_persistence_001` | `research_watchlist` | 1.0651 | 0.8080 | 0.6890 | `none` |
| `qr_v09d_range_position_001` | `research_watchlist` | 1.0633 | 0.6993 | 0.6321 | `none` |
| `qr_v09d_funding_return_long_001` | `research_watchlist` | 0.9938 | 0.5861 | 0.3864 | `none` |
| `qr_v09d_funding_return_long_001` | `research_watchlist` | 0.9935 | 0.3496 | 0.2708 | `none` |
| `qr_v09d_trend_persistence_001` | `research_watchlist` | 0.9879 | 0.7377 | 0.5955 | `none` |
| `qr_v09d_volume_conviction_001` | `research_watchlist` | 0.9835 | 0.7099 | 0.4664 | `none` |
| `qr_v09d_range_position_001` | `research_watchlist` | 0.9831 | 0.6302 | 0.5390 | `none` |
| `qr_v09d_range_position_001` | `research_watchlist` | 0.9816 | 0.4097 | 0.3552 | `none` |

## Declared Review Mechanics Audit

- BTC review rows with `too_few_completed_rows`: `0` of `288`.
- ETH review rows with `too_few_completed_rows`: `0` of `288`.
- BTC effective completed-row floor values: `5`.
- ETH effective completed-row floor values: `5`.
- RandysLab now records an effective completed-row floor for declared variant-level reviews, capped at the registered group size so a single-asset declared profile is not mechanically blocked by the multi-asset `min_completed_rows=15` default.
- Sharpe, validation, blind-window, positive-row, and drawdown gates remain unchanged.

## Correlation And Redundancy

- Correlation path: `../RandysLab-STRICT4H/reports/factor_candidate_correlation/research_v0_9d_btc`
- High-correlation threshold: `0.8`
- Pair count: `66`
- Bundle verdict counts: `diversified_enough_for_research:3`

| Bundle | Redundancy Verdict | Max Abs Corr | High Corr Pairs |
|---|---|---:|---:|
| `qr_v09d_bundle_trend_quality_001` | `diversified_enough_for_research` | 0.1627 | 0 |
| `qr_v09d_bundle_liquidity_direction_001` | `diversified_enough_for_research` | 0.4661 | 0 |
| `qr_v09d_bundle_funding_confirmation_001` | `diversified_enough_for_research` | 0.1627 | 0 |

## Wider Diagnostics

- `wider_avax`: candidate_count=`48`, verdict_counts=`blocked_by_conservative_rules:44, research_watchlist:4`
- `wider_bnb`: candidate_count=`48`, verdict_counts=`blocked_by_conservative_rules:31, research_watchlist:17`
- `wider_sol`: candidate_count=`48`, verdict_counts=`blocked_by_conservative_rules:43, research_watchlist:5`

## Failure Memory

- Failure-memory path: `reports/failure_memory/research_v0_9d_strict_candidate_discovery`
- Failure count: `282`
- Cluster count: `33`
- Conservative verdict counts: `blocked_pending_new_hypotheses:273, scoped_watchlist_needs_replication:9`
- Failure labels: `drawdown_fragility, eth_diagnostic_weakness, extreme_row_drawdown, funding_confirmation_fragility, high_mean_drawdown, intrabar_conviction_fragility, liquidity_adjusted_momentum_fragility, low_mean_sharpe, low_median_sharpe, low_positive_row_share, too_few_positive_assets, trend_quality_fragility, weak_blind_window, weak_validation_window`

## Research 1.0 Readiness

`research_1_0_candidate_pending_replication`

## Verification

- Focused QuantumRandy v0.9d tests on 2026-07-03: `3 passed`.
- QuantumRandy full suite on 2026-07-03: `128 passed`.
- Focused RandysLab formula-candidate and correlation tests on 2026-07-03: `14 passed`.
- RandysLab full suite on 2026-07-03: `30 passed`.
- Artifact audit confirms candidate counts, declared scope, BTC/ETH review artifacts, redundancy artifacts, and failure memory.

## Boundary Confirmation

- No RandyPortfolio implementation.
- No portfolio scheduler.
- No live trading.
- No exchange keys.
- No runtime publishing.
- No automatic factor admission.
- No new base fields.
- No production regime labels.
- No selector evidence61.
- No drawdown-stop tuning.
