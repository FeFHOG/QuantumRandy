# Research v1.2 Failure-Guided Scoped Candidate Re-Spec Report

Date: 2026-07-03

Status: complete for the research-only failure-guided scoped candidate re-spec report renderer.

This report is research-only, not factor admission, not runtime publishing, not RandyPortfolio, and not live execution approval.

## Objective

Research v1.2 re-specs a narrow non-funding cohort from v1.1 failure memory after the v1.1 clean negative result. It keeps `BTCUSDT_4h` as the declared scope and treats out-of-scope asset rows as diagnostics only.

## Candidate Export

- Export path: `reports/factor_candidate_exports/research_v1_2_failure_guided_scoped_respec`
- Candidate count: `12`
- Single-factor count: `9`
- Bundle count: `3`
- Intended scope: `BTCUSDT_4h`
- Out-of-scope policy: `diagnostic_only`
- Excluded Research 1.0 survivor: `qr_v09d_funding_return_long_001::thr_0p0_long_short_cap_0p5_none`
- Excluded survivor family: `funding_return_long_horizon`

| Candidate | Family | Formula |
|---|---|---|
| `qr_v12_volume_range_conviction_001` | `volume_conviction_hardening` | `zscore(div(corr(sub(close,open),volume,72),div(sub(max(high,48),min(low,48)),close)),96)` |
| `qr_v12_volume_location_conviction_001` | `volume_conviction_hardening` | `zscore(mul(div(sub(close,open),sub(high,low)),div(volume,sma(volume,96))),120)` |
| `qr_v12_volume_turnover_damped_001` | `volume_conviction_hardening` | `zscore(div(corr(sub(close,open),volume,96),std(ret(close,6),48)),120)` |
| `qr_v12_trend_range_efficiency_slow_001` | `trend_quality_simplification` | `zscore(div(ret(close,48),div(sub(max(high,96),min(low,96)),close)),120)` |
| `qr_v12_trend_persistence_slow_001` | `trend_quality_simplification` | `zscore(corr(ret(close,12),ret(close,48),72),120)` |
| `qr_v12_trend_drawdown_aware_001` | `trend_quality_simplification` | `zscore(div(sub(ema(close,48),ema(close,144)),sub(max(high,96),min(low,96))),120)` |
| `qr_v12_crash_participation_filter_001` | `crash_resilient_participation` | `zscore(mul(div(sub(close,open),sub(high,low)),neg(zscore(std(close,48),144))),120)` |
| `qr_v12_range_expansion_contra_001` | `crash_resilient_participation` | `zscore(div(sub(close,open),mul(sub(high,low),div(volume,sma(volume,96)))),120)` |
| `qr_v12_close_location_volume_001` | `crash_resilient_participation` | `zscore(mul(div(sub(close,low),sub(high,low)),div(volume,sma(volume,96))),120)` |

| Bundle | Components | Method |
|---|---|---|
| `qr_v12_bundle_volume_conviction_hardening_001` | `qr_v12_volume_range_conviction_001, qr_v12_volume_location_conviction_001, qr_v12_volume_turnover_damped_001` | `equal_weight_mean` |
| `qr_v12_bundle_trend_quality_simplification_001` | `qr_v12_trend_range_efficiency_slow_001, qr_v12_trend_persistence_slow_001, qr_v12_trend_drawdown_aware_001` | `equal_weight_mean` |
| `qr_v12_bundle_crash_resilient_participation_001` | `qr_v12_crash_participation_filter_001, qr_v12_range_expansion_contra_001, qr_v12_close_location_volume_001` | `equal_weight_mean` |

## BTC Primary Declared Review

- Review path: `../RandysLab-STRICT4H/reports/factor_candidate_review/research_v1_2_btc_primary`
- Candidate count: `144`
- Verdict counts: `blocked_by_conservative_rules:139, research_watchlist:5`
- Scope mode: `declared`

## Diagnostic Reviews

ETH/SOL/BNB/AVAX rows remain portability diagnostics. They do not alter the declared BTCUSDT scope and do not authorize portfolio deployment.

- ETH candidate count: `144`, verdict counts: `blocked_by_conservative_rules:134, research_watchlist:10`
- SOL candidate count: `144`, verdict counts: `blocked_by_conservative_rules:136, research_watchlist:8`
- BNB candidate count: `144`, verdict counts: `blocked_by_conservative_rules:124, research_watchlist:20`
- AVAX candidate count: `144`, verdict counts: `blocked_by_conservative_rules:143, research_watchlist:1`

## Correlation And Redundancy

- Correlation path: `../RandysLab-STRICT4H/reports/factor_candidate_correlation/research_v1_2_btc`
- Bundle count: `3`
- High-correlation threshold: `0.8`
- Bundle verdict counts: `diversified_enough_for_research:3`

## Scope-Aware Robustness

- Robustness path: `../RandysLab-STRICT4H/reports/factor_candidate_robustness/research_v1_2_failure_guided_respec`
- Detail rows: `10980`
- Scenario summary rows: `960`
- Variant rankings: `60`

### Best Blocked Near Misses

| Candidate | Variant | Verdict | Stress Survival | Mean Sharpe | Validation Sharpe | Blind Sharpe | Worst Max DD | Labels |
|---|---|---|---:|---:|---:|---:|---:|---|
| `qr_v12_volume_turnover_damped_001` | `thr_0p5_long_short_cap_0p5_calm_vol_lte_1p5` | `blocked_pending_new_hypotheses` | 14/15 | 0.7428 | 0.8147 | 0.1895 | 0.3578 | `asset_exclusion_fragility|blind_weakness|sol_avax_concentration|validation_weakness|funding_fragility|fee_fragility|crash_period_drawdown` |
| `qr_v12_volume_turnover_damped_001` | `thr_0p0_long_short_cap_0p5_calm_vol_lte_1p5` | `blocked_pending_new_hypotheses` | 10/15 | 0.4433 | 0.3911 | -0.0619 | 0.3958 | `asset_exclusion_fragility|blind_weakness|sol_avax_concentration|validation_weakness|funding_fragility|crash_period_drawdown|btc_weakness|fee_fragility` |
| `qr_v12_volume_range_conviction_001` | `thr_1p0_long_short_cap_1p0_calm_vol_lte_1p5` | `blocked_pending_new_hypotheses` | 3/15 | -0.1072 | 1.1883 | -0.8635 | 0.6430 | `crash_period_drawdown|sol_avax_concentration|validation_weakness|asset_exclusion_fragility|blind_weakness|btc_weakness|funding_fragility|fee_fragility` |
| `qr_v12_volume_range_conviction_001` | `thr_0p5_long_short_cap_0p5_calm_vol_lte_1p5` | `blocked_pending_new_hypotheses` | 3/15 | -0.0222 | 1.1817 | -0.7660 | 0.4717 | `crash_period_drawdown|sol_avax_concentration|validation_weakness|asset_exclusion_fragility|blind_weakness|btc_weakness|funding_fragility|fee_fragility` |
| `qr_v12_volume_range_conviction_001` | `thr_0p0_long_short_cap_0p5_calm_vol_lte_1p5` | `blocked_pending_new_hypotheses` | 3/15 | -0.0247 | 0.8546 | -0.5223 | 0.5200 | `crash_period_drawdown|sol_avax_concentration|validation_weakness|asset_exclusion_fragility|blind_weakness|btc_weakness|funding_fragility|fee_fragility` |
| `qr_v12_volume_turnover_damped_001` | `thr_1p0_long_short_cap_1p0_calm_vol_lte_1p5` | `blocked_pending_new_hypotheses` | 3/15 | 0.3976 | 0.7603 | -0.4985 | 0.5563 | `crash_period_drawdown|sol_avax_concentration|validation_weakness|asset_exclusion_fragility|blind_weakness|btc_weakness|funding_fragility|fee_fragility` |
| `qr_v12_bundle_volume_conviction_hardening_001` | `thr_0p5_long_short_cap_0p5_calm_vol_lte_1p5` | `blocked_pending_new_hypotheses` | 3/15 | -0.3077 | 0.7043 | -1.7146 | 0.5902 | `crash_period_drawdown|sol_avax_concentration|validation_weakness|asset_exclusion_fragility|blind_weakness|btc_weakness|funding_fragility|fee_fragility` |
| `qr_v12_bundle_volume_conviction_hardening_001` | `thr_1p0_long_short_cap_1p0_calm_vol_lte_1p5` | `blocked_pending_new_hypotheses` | 3/15 | -0.6224 | 0.6820 | -2.5680 | 0.8021 | `crash_period_drawdown|sol_avax_concentration|validation_weakness|asset_exclusion_fragility|blind_weakness|btc_weakness|funding_fragility|fee_fragility` |
| `qr_v12_volume_range_conviction_001` | `thr_0p0_long_flat_cap_1p0_calm_vol_lte_1p5` | `blocked_pending_new_hypotheses` | 3/15 | 0.5426 | 0.5076 | -0.2699 | 0.5269 | `crash_period_drawdown|sol_avax_concentration|asset_exclusion_fragility|blind_weakness|funding_fragility|fee_fragility|btc_weakness|validation_weakness` |
| `qr_v12_volume_range_conviction_001` | `thr_0p0_long_flat_cap_0p5_calm_vol_lte_1p5` | `blocked_pending_new_hypotheses` | 3/15 | 0.4588 | 0.4409 | -0.3790 | 0.2839 | `sol_avax_concentration|asset_exclusion_fragility|blind_weakness|funding_fragility|fee_fragility|btc_weakness|validation_weakness` |

## Failure Memory

- Failure-memory path: `reports/failure_memory/research_v1_2_failure_guided_respec`
- Input rows: `60`
- Failure count: `60`
- Cluster count: `47`

## Readiness Verdict

`research_v1_2_failure_guided_candidate_not_found`

This verdict is research-only. A surviving candidate, if present, remains pending manual research review and does not become a production factor. This is not factor admission.

## Verification Checklist

- v1.2 export excludes `qr_v09d_funding_return_long_001` and direct `funding_rate` formulas.
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
