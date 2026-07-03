# Research 1.0 Candidate Replication Report

Date: 2026-07-03

Status: complete for the first scope-aware Research 1.0 candidate replication pass.

This report is research-only. It is not factor admission, runtime publishing, portfolio construction, RandyPortfolio,
or live execution.

## Objective

Research v0.9d produced `research_1_0_candidate_pending_replication` after the RandysLab declared-scope review repair.
This pass tested whether the pending v0.9d variants survive the Research 1.0 robustness gate within their declared
`BTCUSDT_4h` scope while preserving out-of-scope assets as diagnostics.

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
- Scope-hard stress scenarios per ranking: `15`.
- Diagnostic-only scenarios per ranking: `1`.
- Surviving rankings: `1`.
- Blocked rankings: `59`.

Scenarios included base windows, higher fee/slippage, higher funding, combined harsh costs, crash windows, validation
only, blind only, and leave-one-asset-out tests across BTC, ETH, SOL, BNB, and AVAX.

For `BTCUSDT_4h` declared-scope candidates, `exclude_btcusdt` is diagnostic-only because it removes the declared
scope asset. Other scenarios are hard-gated on BTC rows; ETH/SOL/BNB/AVAX rows remain diagnostic labels.

## Scope-Replicated Candidate

| Candidate | Variant | Survival | Mean Sharpe | Worst Sharpe | Mean Max DD | Worst Max DD | Validation Sharpe | Blind Sharpe | Diagnostic Labels |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| `qr_v09d_funding_return_long_001` | `thr_0p0_long_short_cap_0p5_none` | `15/15` | 0.7844 | 0.3589 | 0.2583 | 0.3243 | 0.4345 | 0.6993 | `asset_exclusion_fragility|sol_avax_concentration|validation_weakness|blind_weakness|crash_period_drawdown|funding_fragility|fee_fragility` |

This is a research candidate only. It is not factor admission, runtime publication, portfolio construction, or live
execution approval.

## Best Blocked Near Misses

| Candidate | Variant | Survival | Mean Sharpe | Worst Sharpe | Mean Max DD | Worst Max DD | Labels |
|---|---|---:|---:|---:|---:|---:|---|
| `qr_v09d_volume_conviction_001` | `thr_0p0_long_flat_cap_0p5_none` | `14/15` | 0.8589 | -0.0617 | 0.1765 | 0.2279 | `sol_avax_concentration|funding_fragility|fee_fragility|asset_exclusion_fragility` |
| `qr_v09d_volume_conviction_001` | `thr_0p0_long_short_cap_0p5_none` | `12/15` | 0.6401 | -0.3036 | 0.2695 | 0.4544 | `crash_period_drawdown|sol_avax_concentration|validation_weakness|blind_weakness|asset_exclusion_fragility|funding_fragility|fee_fragility|btc_weakness` |
| `qr_v09d_volume_conviction_001` | `thr_0p0_long_flat_cap_1p0_calm_vol_lte_1p5` | `12/15` | 0.6020 | -0.0936 | 0.3355 | 0.4487 | `asset_exclusion_fragility|sol_avax_concentration|crash_period_drawdown|blind_weakness|funding_fragility|fee_fragility|validation_weakness|btc_weakness` |
| `qr_v09d_volume_conviction_001` | `thr_0p5_long_short_cap_0p5_none` | `12/15` | 0.5890 | -0.1040 | 0.2302 | 0.3495 | `crash_period_drawdown|sol_avax_concentration|blind_weakness|asset_exclusion_fragility|funding_fragility|validation_weakness|fee_fragility|btc_weakness` |
| `qr_v09d_funding_return_long_001` | `thr_0p5_long_short_cap_0p5_none` | `11/15` | 0.5519 | -0.0119 | 0.2814 | 0.4324 | `blind_weakness|sol_avax_concentration|validation_weakness|funding_fragility|fee_fragility|asset_exclusion_fragility|btc_weakness|crash_period_drawdown` |

## Failure Memory

- Input rows: `60`.
- Failure rows: `59`.
- Cluster count: `33`.
- Primary labels: `replication_stress_fragility`, `validation_weakness`, `blind_weakness`, `fee_fragility`,
  `funding_fragility`, `btc_weakness`, `sol_avax_concentration`, `asset_exclusion_fragility`, and
  `crash_period_drawdown`.
- The one passed ranking is intentionally absent from `failure_memory.csv`; its diagnostic labels remain in the
  RandysLab robustness ranking.

## Research 1.0 Readiness

`research_1_0_candidate_replicated_pending_manual_review`

v0.9d now has one BTCUSDT declared-scope candidate/variant that survived all current scope-hard replication stresses.
The remaining work is manual research review and any separately approved Research 1.0 decision process. This report does
not admit a production factor and does not publish a runtime payload.

## Verification

- QuantumRandy focused v0.9d and replication-memory tests on 2026-07-03: `4 passed`.
- QuantumRandy full suite on 2026-07-03: `129 passed`.
- RandysLab focused factor-candidate and correlation tests on 2026-07-03: `21 passed`.
- RandysLab full suite on 2026-07-03: `31 passed`.

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
