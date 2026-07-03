# Research 1.0 Candidate Replication Report

Date: 2026-07-03

Status: complete for the first Research 1.0 candidate replication attempt.

This report is research-only. It is not factor admission, runtime publishing, portfolio construction, RandyPortfolio,
or live execution.

## Objective

Research v0.9d produced `research_1_0_candidate_pending_replication` after the RandysLab declared-scope review repair.
This pass tested whether the pending v0.9d variants survive the Research 1.0 robustness gate.

## Inputs

- Candidate export: `reports/factor_candidate_exports/research_v0_9d_strict_candidate_discovery`.
- BTC primary review: `../RandysLab-STRICT4H/reports/factor_candidate_review/research_v0_9d_btc_primary`.
- ETH diagnostic review: `../RandysLab-STRICT4H/reports/factor_candidate_review/research_v0_9d_eth_diagnostic`.
- Robustness gauntlet: `../RandysLab-STRICT4H/reports/factor_candidate_robustness/research_v0_9d_candidate_replication`.
- Replication failure memory: `reports/failure_memory/research_1_0_candidate_replication`.

v0.9d had `15` BTC watchlist rows and `6` same-variant ETH-confirmed rows. The replication gauntlet stressed the
corresponding `5` unique variant ids against the full v0.9d candidate export.

## Robustness Gauntlet

- Detail rows: `10980`.
- Scenario summary rows: `960`.
- Candidate/variant rankings: `60`.
- Stress scenarios: `16`.
- Surviving rankings: `0`.
- Blocked rankings: `60`.

Scenarios included base windows, higher fee/slippage, higher funding, combined harsh costs, crash windows, validation
only, blind only, and leave-one-asset-out tests across BTC, ETH, SOL, BNB, and AVAX.

## Best Near Misses

| Candidate | Variant | Survival | Mean Sharpe | Worst Sharpe | Mean Max DD | Worst Max DD | Labels |
|---|---|---:|---:|---:|---:|---:|---|
| `qr_v09d_range_position_001` | `thr_0p0_long_flat_cap_0p5_none` | `14/16` | 0.5705 | -1.6860 | 0.2628 | 0.4737 | `sol_avax_concentration|btc_weakness|blind_weakness|fee_fragility|funding_fragility|validation_weakness` |
| `qr_v09d_trend_persistence_001` | `thr_0p0_long_flat_cap_0p5_none` | `14/16` | 0.3109 | -2.5593 | 0.3290 | 0.6976 | `btc_weakness|sol_avax_concentration|crash_period_drawdown|validation_weakness|blind_weakness|fee_fragility|funding_fragility` |
| `qr_v09d_rsi_state_change_001` | `thr_0p0_long_flat_cap_1p0_calm_vol_lte_1p5` | `13/16` | 0.8534 | -1.4329 | 0.4142 | 0.7483 | `sol_avax_concentration|validation_weakness|blind_weakness|btc_weakness|crash_period_drawdown|fee_fragility|funding_fragility` |
| `qr_v09d_trend_efficiency_001` | `thr_0p0_long_flat_cap_0p5_none` | `13/16` | 0.5935 | -4.1928 | 0.2504 | 0.5670 | `validation_weakness|btc_weakness|sol_avax_concentration|blind_weakness|fee_fragility|funding_fragility` |
| `qr_v09d_liquidity_adjusted_momentum_001` | `thr_0p0_long_flat_cap_0p5_none` | `13/16` | 0.4441 | -2.1279 | 0.2607 | 0.5768 | `btc_weakness|validation_weakness|sol_avax_concentration|blind_weakness|fee_fragility|funding_fragility` |

## Failure Memory

- Input rows: `60`.
- Failure rows: `60`.
- Cluster count: `33`.
- Primary labels: `replication_stress_fragility`, `validation_weakness`, `blind_weakness`, `fee_fragility`,
  `funding_fragility`, `btc_weakness`, `sol_avax_concentration`, `asset_exclusion_fragility`, and
  `crash_period_drawdown`.

## Research 1.0 Readiness

`not_ready_for_research_1_0`

v0.9d found promising scoped candidates, but the first Research 1.0 replication gauntlet did not produce a variant that
survived all required stress scenarios. The remaining blocker is still strict-surviving robust candidate evidence.

## Verification

- QuantumRandy focused v0.9d and replication-memory tests on 2026-07-03: `4 passed`.
- QuantumRandy full suite on 2026-07-03: `129 passed`.
- RandysLab focused factor-candidate and correlation tests on 2026-07-03: `14 passed`.
- RandysLab full suite on 2026-07-03: `30 passed`.

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
