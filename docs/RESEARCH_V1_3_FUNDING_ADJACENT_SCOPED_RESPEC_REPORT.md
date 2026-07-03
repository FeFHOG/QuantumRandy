# Research v1.3 Funding-Adjacent Scoped Re-Spec Report

Date: 2026-07-03

Status: complete for the research-only funding-adjacent scoped re-spec report renderer.

This report is research-only, not factor admission, not runtime publishing, not RandyPortfolio, and not live execution approval.

## Objective

Research v1.3 tests funding, carry, and friction locality after v1.1 and v1.2 produced clean negative non-funding results. It keeps `BTCUSDT_4h` as the declared scope and treats out-of-scope asset rows as diagnostics only.

## Funding-Adjacent Status

- Funding-adjacent status: `funding_adjacent_not_independent_non_funding`
- This is a funding-adjacent locality probe and not independent non-funding replication.

## Candidate Export

- Export path: `reports/factor_candidate_exports/research_v1_3_funding_adjacent_scoped_respec`
- Candidate count: `16`
- Single-factor count: `12`
- Bundle count: `4`
- Intended scope: `BTCUSDT_4h`
- Out-of-scope policy: `diagnostic_only`
- Excluded Research 1.0 survivor: `qr_v09d_funding_return_long_001::thr_0p0_long_short_cap_0p5_none`
- Excluded survivor family: `funding_return_long_horizon`

| Candidate | Family | Formula |
|---|---|---|
| `qr_v13_funding_vol_norm_001` | `funding_pressure_normalization` | `neg(zscore(div(funding_rate,std(close,48)),120))` |
| `qr_v13_funding_range_norm_001` | `funding_pressure_normalization` | `neg(zscore(div(ema(funding_rate,12),div(sub(max(high,96),min(low,96)),close)),120))` |
| `qr_v13_funding_volume_norm_001` | `funding_pressure_normalization` | `neg(zscore(div(funding_rate,div(volume,sma(volume,96))),120))` |
| `qr_v13_funding_return_short_corr_001` | `funding_return_interaction` | `zscore(corr(funding_rate,ret(close,12),72),120)` |
| `qr_v13_funding_return_product_001` | `funding_return_interaction` | `zscore(mul(zscore(funding_rate,96),zscore(ret(close,12),96)),120)` |
| `qr_v13_smooth_funding_return_corr_001` | `funding_return_interaction` | `zscore(corr(ema(funding_rate,12),ret(close,24),96),120)` |
| `qr_v13_funding_volatility_penalty_001` | `cost_aware_carry_filter` | `neg(zscore(mul(funding_rate,std(ret(close,6),48)),120))` |
| `qr_v13_smooth_funding_retvol_norm_001` | `cost_aware_carry_filter` | `neg(zscore(div(ema(funding_rate,24),std(ret(close,6),48)),120))` |
| `qr_v13_funding_calm_filter_001` | `cost_aware_carry_filter` | `zscore(mul(neg(zscore(funding_rate,96)),neg(zscore(std(close,48),144))),120)` |
| `qr_v13_funding_ema_shift_001` | `funding_regime_transition` | `zscore(sub(ema(funding_rate,12),ema(funding_rate,48)),120)` |
| `qr_v13_funding_delta_reversal_001` | `funding_regime_transition` | `neg(zscore(delta(funding_rate,12),96))` |
| `qr_v13_funding_delta_return_corr_001` | `funding_regime_transition` | `zscore(corr(delta(funding_rate,12),ret(close,12),72),120)` |

| Bundle | Components | Method |
|---|---|---|
| `qr_v13_bundle_funding_pressure_norm_001` | `qr_v13_funding_vol_norm_001, qr_v13_funding_range_norm_001, qr_v13_funding_volume_norm_001` | `equal_weight_mean` |
| `qr_v13_bundle_funding_return_interaction_001` | `qr_v13_funding_return_short_corr_001, qr_v13_funding_return_product_001, qr_v13_smooth_funding_return_corr_001` | `equal_weight_mean` |
| `qr_v13_bundle_cost_aware_carry_001` | `qr_v13_funding_volatility_penalty_001, qr_v13_smooth_funding_retvol_norm_001, qr_v13_funding_calm_filter_001` | `equal_weight_mean` |
| `qr_v13_bundle_funding_transition_001` | `qr_v13_funding_ema_shift_001, qr_v13_funding_delta_reversal_001, qr_v13_funding_delta_return_corr_001` | `equal_weight_mean` |

## BTC Primary Declared Review

- Review path: `../RandysLab-STRICT4H/reports/factor_candidate_review/research_v1_3_btc_primary`
- Candidate count: `192`
- Verdict counts: `blocked_by_conservative_rules:148, research_watchlist:44`
- Scope mode: `declared`

## Diagnostic Reviews

ETH/SOL/BNB/AVAX rows remain portability diagnostics. They do not alter the declared BTCUSDT scope and do not authorize portfolio deployment.

- ETH candidate count: `192`, verdict counts: `blocked_by_conservative_rules:179, research_watchlist:13`
- SOL candidate count: `192`, verdict counts: `blocked_by_conservative_rules:189, research_watchlist:3`
- BNB candidate count: `192`, verdict counts: `blocked_by_conservative_rules:164, research_watchlist:28`
- AVAX candidate count: `192`, verdict counts: `blocked_by_conservative_rules:191, research_watchlist:1`

## Correlation And Redundancy

- Correlation path: `../RandysLab-STRICT4H/reports/factor_candidate_correlation/research_v1_3_btc`
- Bundle count: `4`
- High-correlation threshold: `0.8`
- Bundle verdict counts: `diversified_enough_for_research:4`

## Scope-Aware Robustness

- Robustness path: `../RandysLab-STRICT4H/reports/factor_candidate_robustness/research_v1_3_funding_adjacent_respec`
- Detail rows: `14640`
- Scenario summary rows: `1280`
- Variant rankings: `80`

### Passed Candidates

| Candidate | Variant | Verdict | Stress Survival | Mean Sharpe | Validation Sharpe | Blind Sharpe | Worst Max DD | Labels |
|---|---|---|---:|---:|---:|---:|---:|---|
| `qr_v13_funding_range_norm_001` | `thr_0p0_long_short_cap_0p5_calm_vol_lte_1p5` | `research_watchlist` | 15/15 | 1.1468 | 0.7933 | 0.8921 | 0.3841 | `sol_avax_concentration, validation_weakness, blind_weakness` |
| `qr_v13_funding_range_norm_001` | `thr_0p0_long_flat_cap_0p5_calm_vol_lte_1p5` | `research_watchlist` | 15/15 | 1.2317 | 0.3383 | 0.6310 | 0.2939 | `blind_weakness, sol_avax_concentration` |

## Failure Memory

- Failure-memory path: `reports/failure_memory/research_v1_3_funding_adjacent_respec`
- Input rows: `80`
- Failure count: `78`
- Cluster count: `57`

## Readiness Verdict

`research_v1_3_funding_adjacent_candidate_replicated_pending_manual_review`

This verdict is research-only. A surviving candidate, if present, remains pending manual research review and does not become a production factor. This is not factor admission.

## Verification Checklist

- v1.3 export excludes `qr_v09d_funding_return_long_001` while preserving the exclusion in report memory.
- Funding-adjacent status is explicit and does not claim independent non-funding replication.
- BTC primary declared review summary is included.
- ETH/SOL/BNB/AVAX diagnostic review summaries are included when generated.
- BTC bundle correlation and redundancy summary is included.
- Scope-aware robustness ranking is included.
- Failure memory is generated from robustness ranking.
- Boundary remains research-only.

## Boundary Confirmation

- No RandyPortfolio implementation.
- No live trading.
- No exchange private keys.
- No runtime factor publishing.
- No automatic factor admission.
- No new formula base fields.
- No production runtime regime labels.
- No selector evidence61.
