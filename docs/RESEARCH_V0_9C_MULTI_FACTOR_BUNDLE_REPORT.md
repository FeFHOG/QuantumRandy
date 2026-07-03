# Research v0.9c Multi-Factor Bundle Report

Date: 2026-07-03

Status: complete for the BTCUSDT 4h scoped multi-factor bundle checkpoint.

This report is research-only. It is not factor admission, runtime publishing, portfolio construction, RandyPortfolio, or live execution.

## Objective

Research v0.9c evaluated a deterministic BTCUSDT 4h current-DSL multi-factor bundle using the v0.9a scoped schema and v0.9b failure-memory discipline.

## Candidate Export

- Export path: `reports/factor_candidate_exports/research_v0_9c_multi_factor_bundle`
- Candidate count: `9`
- Single-factor count: `6`
- Bundle count: `3`
- Intended scope: `BTCUSDT_4h`
- Out-of-scope policy: `diagnostic_only`

| Candidate | Family | Formula |
|---|---|---|
| `qr_v09c_liquidity_001` | `liquidity_participation` | `zscore(div(volume,sma(volume,48)),120)` |
| `qr_v09c_range_001` | `range_compression` | `neg(zscore(div(sub(high,low),close),96))` |
| `qr_v09c_trend_001` | `price_trend` | `zscore(ret(close,24),96)` |
| `qr_v09c_reversal_001` | `short_horizon_reversal` | `neg(zscore(ret(close,6),72))` |
| `qr_v09c_funding_001` | `funding_pressure_crowding` | `neg(zscore(div(funding_rate,std(close,48)),96))` |
| `qr_v09c_price_volume_001` | `price_volume_confirmation` | `zscore(corr(volume,ret(close,12),48),72)` |

| Bundle | Components | Method |
|---|---|---|
| `qr_v09c_bundle_diversified_001` | `qr_v09c_liquidity_001, qr_v09c_range_001, qr_v09c_funding_001, qr_v09c_reversal_001` | `equal_weight_mean` |
| `qr_v09c_bundle_trend_crowding_001` | `qr_v09c_trend_001, qr_v09c_funding_001, qr_v09c_price_volume_001` | `equal_weight_mean` |
| `qr_v09c_bundle_calm_reversal_001` | `qr_v09c_range_001, qr_v09c_reversal_001, qr_v09c_funding_001` | `equal_weight_mean` |

## RandysLab Declared Review

- Sensitivity path: `../RandysLab-STRICT4H/reports/factor_candidate_sensitivity/research_v0_9c_bundle_btc_declared`
- Sensitivity run count: `45`
- Sensitivity candidate row count: `405`
- Review path: `../RandysLab-STRICT4H/reports/factor_candidate_review/research_v0_9c_bundle_btc_declared`
- Scope mode: `declared`
- `scope_mode=declared`
- Review scopes: `BTCUSDT_4h`
- Candidate count: `9`
- Verdict counts: `blocked_by_conservative_rules:9`

| Candidate | Verdict | Mean Sharpe | Validation Sharpe | Blind Sharpe | Failures |
|---|---|---:|---:|---:|---|
| `qr_v09c_funding_001` | `blocked_by_conservative_rules` | 0.4625 | 0.6859 | 0.2209 | `high_mean_drawdown` |
| `qr_v09c_bundle_trend_crowding_001` | `blocked_by_conservative_rules` | 0.2789 | 0.3719 | 0.0130 | `extreme_row_drawdown` |
| `qr_v09c_trend_001` | `blocked_by_conservative_rules` | 0.0377 | -0.1802 | 0.0271 | `low_mean_sharpe|low_median_sharpe|low_positive_row_share|weak_validation_window|high_mean_drawdown|extreme_row_drawdown` |
| `qr_v09c_bundle_calm_reversal_001` | `blocked_by_conservative_rules` | -0.1108 | 0.6309 | -0.2058 | `low_mean_sharpe|low_median_sharpe|low_positive_row_share|weak_blind_window|high_mean_drawdown|extreme_row_drawdown` |
| `qr_v09c_price_volume_001` | `blocked_by_conservative_rules` | -0.2323 | -0.4600 | -0.1595 | `low_mean_sharpe|low_median_sharpe|low_positive_row_share|weak_validation_window|weak_blind_window|high_mean_drawdown|extreme_row_drawdown` |
| `qr_v09c_bundle_diversified_001` | `blocked_by_conservative_rules` | -0.2771 | -0.3104 | 0.1231 | `low_mean_sharpe|low_median_sharpe|low_positive_row_share|weak_validation_window|extreme_row_drawdown` |
| `qr_v09c_reversal_001` | `blocked_by_conservative_rules` | -0.5991 | -0.0092 | -0.4543 | `low_mean_sharpe|low_median_sharpe|low_positive_row_share|weak_validation_window|weak_blind_window|high_mean_drawdown|extreme_row_drawdown` |
| `qr_v09c_range_001` | `blocked_by_conservative_rules` | -1.0968 | -0.9177 | -1.8660 | `low_mean_sharpe|low_median_sharpe|low_positive_row_share|weak_validation_window|weak_blind_window|high_mean_drawdown|extreme_row_drawdown` |
| `qr_v09c_liquidity_001` | `blocked_by_conservative_rules` | -1.3323 | -1.7220 | -1.2742 | `low_mean_sharpe|low_median_sharpe|low_positive_row_share|weak_validation_window|weak_blind_window|high_mean_drawdown|extreme_row_drawdown` |

## Correlation And Redundancy

- Correlation path: `../RandysLab-STRICT4H/reports/factor_candidate_correlation/research_v0_9c_bundle_btc`
- High-correlation threshold: `0.8`
- Pair count: `36`
- Bundle verdict counts: `diversified_enough_for_research:2, redundant_research_memory_only:1`

| Bundle | Redundancy Verdict | Max Abs Corr | High Corr Pairs |
|---|---|---:|---:|
| `qr_v09c_bundle_diversified_001` | `redundant_research_memory_only` | 0.8366 | 1 |
| `qr_v09c_bundle_trend_crowding_001` | `diversified_enough_for_research` | 0.4696 | 0 |
| `qr_v09c_bundle_calm_reversal_001` | `diversified_enough_for_research` | 0.0629 | 0 |

## Gated Bundle Diagnostics

Gated sweep ran because `credible_bundle_rows=1`. Result: `run_count=20`, `candidate_row_count=60`.

## Failure Memory

- Failure-memory path: `reports/failure_memory/research_v0_9c_multi_factor_bundle`
- Failure count: `9`
- Cluster count: `2`
- Conservative verdict counts: `blocked_pending_new_hypotheses:8, research_memory_only:1`
- Failure labels: `blind_bundle_fragility, bundle_redundancy, component_crowding_overlap, drawdown_fragility, extreme_row_drawdown, funding_pressure_fragility, high_mean_drawdown, low_mean_sharpe, low_median_sharpe, low_positive_row_share, multi_factor_bundle, trend_reversal_conflict, validation_bundle_fragility, weak_blind_window, weak_validation_window`

## Regime Feature Readiness

No new base fields were admitted in v0.9c. Current allowed fields remain `open`, `high`, `low`, `close`, `volume`, and `funding_rate`. Open interest, basis, liquidations, taker-flow, and order-book fields require a separate point-in-time data-readiness audit.

## Research 1.0 Readiness

`not_ready_for_research_1_0`

## Verification

- Focused QuantumRandy tests cover the v0.9c exporter, report renderer, and failure-memory adapter.
- Focused RandysLab tests cover formula candidates and correlation review.
- Artifact audit confirmed candidate counts, declared scope, redundancy artifacts, gated diagnostics, and failure memory.
- Final full-suite and diff-check evidence is recorded in the completion notes for this checkpoint.

## Boundary Confirmation

- No RandyPortfolio implementation.
- No portfolio scheduler.
- No live trading.
- No exchange keys.
- No runtime publishing.
- No automatic factor admission.
- No new base fields.
- No selector evidence61.
- No drawdown-stop tuning.
