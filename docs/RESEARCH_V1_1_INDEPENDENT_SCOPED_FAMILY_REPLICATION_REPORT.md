# Research v1.1 Independent Scoped Family Replication Report

Date: 2026-07-03

Status: complete for the research-only independent scoped family replication pass.

This report is research-only, not factor admission, not runtime publishing, not RandyPortfolio, and not live execution approval.

## Objective

Research v1.1 tries to replicate a second independent non-funding scoped family after the Research 1.0 funding-return survivor. It keeps `BTCUSDT_4h` as the declared scope and treats out-of-scope asset rows as diagnostic evidence only.

## Candidate Export

- Export path: `reports/factor_candidate_exports/research_v1_1_independent_scoped_family_replication`
- Candidate count: `10`
- Single-factor count: `8`
- Bundle count: `2`
- Intended scope: `BTCUSDT_4h`
- Out-of-scope policy: `diagnostic_only`
- Excluded Research 1.0 survivor: `qr_v09d_funding_return_long_001::thr_0p0_long_short_cap_0p5_none`
- Excluded survivor family: `funding_return_long_horizon`

| Candidate | Family | Formula |
|---|---|---|
| `qr_v11_volume_conviction_001` | `volume_price_conviction` | `zscore(corr(sub(close,open),volume,48),72)` |
| `qr_v11_volume_conviction_slow_001` | `volume_price_conviction` | `zscore(corr(sub(close,open),volume,72),120)` |
| `qr_v11_range_position_001` | `range_position_trend` | `zscore(div(sub(close,sma(close,48)),sub(max(high,48),min(low,48))),96)` |
| `qr_v11_trend_efficiency_001` | `trend_quality_efficiency` | `zscore(div(ret(close,24),div(sub(max(high,48),min(low,48)),close)),96)` |
| `qr_v11_trend_persistence_001` | `trend_persistence_alignment` | `zscore(corr(ret(close,6),ret(close,24),48),96)` |
| `qr_v11_intrabar_conviction_001` | `intrabar_conviction` | `zscore(div(sub(close,open),sub(high,low)),72)` |
| `qr_v11_liquidity_adjusted_momentum_001` | `liquidity_adjusted_momentum` | `zscore(div(ret(close,24),div(volume,sma(volume,96))),120)` |
| `qr_v11_vol_adjusted_trend_001` | `volatility_adjusted_trend` | `zscore(div(sub(ema(close,24),ema(close,96)),std(close,48)),120)` |

| Bundle | Components | Method |
|---|---|---|
| `qr_v11_bundle_volume_direction_001` | `qr_v11_volume_conviction_001, qr_v11_liquidity_adjusted_momentum_001, qr_v11_vol_adjusted_trend_001` | `equal_weight_mean` |
| `qr_v11_bundle_trend_quality_001` | `qr_v11_trend_efficiency_001, qr_v11_trend_persistence_001, qr_v11_range_position_001` | `equal_weight_mean` |

## BTC Primary Declared Review

- Review path: `../RandysLab-STRICT4H/reports/factor_candidate_review/research_v1_1_btc_primary`
- Candidate count: `120`
- Verdict counts: `blocked_by_conservative_rules:113, research_watchlist:7`
- Scope mode: `declared`

## Diagnostic Reviews

ETH/SOL/BNB/AVAX rows remain portability diagnostics. They do not alter the declared BTCUSDT scope and do not authorize portfolio deployment.

- ETH candidate count: `120`
- ETH verdict counts: `blocked_by_conservative_rules:91, research_watchlist:29`
- AVAX candidate count: `120`, verdict counts: `blocked_by_conservative_rules:120`
- BNB candidate count: `120`, verdict counts: `blocked_by_conservative_rules:80, research_watchlist:40`
- SOL candidate count: `120`, verdict counts: `blocked_by_conservative_rules:110, research_watchlist:10`

## Correlation And Redundancy

- Correlation path: `../RandysLab-STRICT4H/reports/factor_candidate_correlation/research_v1_1_btc`
- Bundle count: `2`
- High-correlation threshold: `0.8`
- Bundle verdict counts: `diversified_enough_for_research:1, redundant_research_memory_only:1`

## Scope-Aware Robustness

- Robustness path: `../RandysLab-STRICT4H/reports/factor_candidate_robustness/research_v1_1_independent_replication`
- Detail rows: `9150`
- Scenario summary rows: `800`
- Variant rankings: `50`

### Best Blocked Near Misses

| Candidate | Variant | Verdict | Stress Survival | Mean Sharpe | Validation Sharpe | Blind Sharpe | Worst Max DD | Labels |
|---|---|---|---:|---:|---:|---:|---:|---|
| `qr_v11_volume_conviction_001` | `thr_0p0_long_flat_cap_1p0_calm_vol_lte_1p5` | `blocked_pending_new_hypotheses` | 12/15 | 0.6020 | 0.2389 | 0.2626 | 0.4487 | `asset_exclusion_fragility|sol_avax_concentration|crash_period_drawdown|blind_weakness|funding_fragility|fee_fragility|validation_weakness|btc_weakness` |
| `qr_v11_bundle_trend_quality_001` | `thr_0p0_long_flat_cap_1p0_calm_vol_lte_1p5` | `blocked_pending_new_hypotheses` | 12/15 | 0.5294 | 0.1338 | 0.4179 | 0.5698 | `sol_avax_concentration|crash_period_drawdown|blind_weakness|btc_weakness|fee_fragility|funding_fragility` |
| `qr_v11_bundle_trend_quality_001` | `thr_0p0_long_flat_cap_0p5_calm_vol_lte_1p5` | `blocked_pending_new_hypotheses` | 10/15 | 0.4381 | 0.0589 | 0.2994 | 0.3306 | `sol_avax_concentration|blind_weakness|btc_weakness|fee_fragility|funding_fragility|validation_weakness` |
| `qr_v11_volume_conviction_001` | `thr_0p0_long_flat_cap_0p5_calm_vol_lte_1p5` | `blocked_pending_new_hypotheses` | 9/15 | 0.5166 | 0.1683 | 0.1544 | 0.2531 | `sol_avax_concentration|asset_exclusion_fragility|blind_weakness|validation_weakness|funding_fragility|fee_fragility|btc_weakness` |
| `qr_v11_volume_conviction_001` | `thr_0p0_long_short_cap_0p5_calm_vol_lte_1p5` | `blocked_pending_new_hypotheses` | 4/15 | 0.0237 | 0.4304 | 0.1898 | 0.4769 | `blind_weakness|sol_avax_concentration|crash_period_drawdown|validation_weakness|asset_exclusion_fragility|btc_weakness|funding_fragility|fee_fragility` |
| `qr_v11_trend_persistence_001` | `thr_1p0_long_short_cap_1p0_calm_vol_lte_1p5` | `blocked_pending_new_hypotheses` | 3/15 | -0.1602 | 0.7907 | 0.5787 | 0.4608 | `blind_weakness|sol_avax_concentration|crash_period_drawdown|validation_weakness|asset_exclusion_fragility|btc_weakness|funding_fragility|fee_fragility` |
| `qr_v11_volume_conviction_slow_001` | `thr_0p0_long_short_cap_0p5_calm_vol_lte_1p5` | `blocked_pending_new_hypotheses` | 3/15 | -0.1824 | 0.5975 | -0.6437 | 0.4965 | `crash_period_drawdown|sol_avax_concentration|validation_weakness|asset_exclusion_fragility|blind_weakness|btc_weakness|funding_fragility|fee_fragility` |
| `qr_v11_volume_conviction_slow_001` | `thr_0p5_long_short_cap_0p5_calm_vol_lte_1p5` | `blocked_pending_new_hypotheses` | 3/15 | 0.0651 | 0.5326 | -0.4837 | 0.3701 | `crash_period_drawdown|sol_avax_concentration|validation_weakness|asset_exclusion_fragility|blind_weakness|btc_weakness|funding_fragility|fee_fragility` |
| `qr_v11_volume_conviction_slow_001` | `thr_0p0_long_flat_cap_1p0_calm_vol_lte_1p5` | `blocked_pending_new_hypotheses` | 3/15 | 0.4349 | 0.3552 | -0.3519 | 0.5434 | `crash_period_drawdown|sol_avax_concentration|asset_exclusion_fragility|blind_weakness|validation_weakness|funding_fragility|fee_fragility|btc_weakness` |
| `qr_v11_trend_persistence_001` | `thr_0p5_long_short_cap_0p5_calm_vol_lte_1p5` | `blocked_pending_new_hypotheses` | 3/15 | -0.2284 | 0.3264 | 0.9133 | 0.3657 | `blind_weakness|sol_avax_concentration|crash_period_drawdown|validation_weakness|asset_exclusion_fragility|btc_weakness|funding_fragility|fee_fragility` |

## Failure Memory

- Failure-memory path: `reports/failure_memory/research_v1_1_independent_replication`
- Input rows: `50`
- Failure count: `50`
- Cluster count: `34`

## Readiness Verdict

`research_v1_1_independent_candidate_not_found`

This verdict is research-only. A surviving candidate, if present, remains pending manual research review and does not become a production factor.

## Verification Checklist

- v1.1 export excludes `qr_v09d_funding_return_long_001` and direct `funding_rate` formulas.
- RandysLab BTC primary declared review is generated.
- ETH/SOL/BNB/AVAX diagnostics are generated when available.
- BTC bundle correlation and redundancy review is generated.
- Scope-aware robustness ranking is generated.
- Failure memory is generated from robustness ranking.
- Boundary remains research-only.

## Boundary Confirmation

- No RandyPortfolio implementation.
- No portfolio scheduler.
- No live trading.
- No exchange private keys.
- No runtime factor publishing.
- No automatic factor admission.
- No new formula base fields.
- No production runtime regime labels.
- No selector evidence61.
