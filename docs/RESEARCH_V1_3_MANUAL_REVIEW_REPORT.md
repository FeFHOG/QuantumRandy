# Research v1.3 Manual Review Report

Date: 2026-07-04

Status: manual review complete for paper-observation planning.

This review is research-only. It is not factor admission, runtime publishing, portfolio construction,
RandyPortfolio implementation, or live execution approval.

## Verdict

```text
research_v1_3_manual_review_pass_for_paper_observation_planning
```

Research v1.3 produced two surviving funding-adjacent robustness variants. Manual review accepts them as enough
evidence to plan a paper-observation protocol, but not enough to open RandyPortfolio or publish any runtime factor.

## Evidence Reviewed

- v1.3 report: `docs/RESEARCH_V1_3_FUNDING_ADJACENT_SCOPED_RESPEC_REPORT.md`.
- Candidate export:
  `reports/factor_candidate_exports/research_v1_3_funding_adjacent_scoped_respec/factor_candidates.jsonl`.
- RandysLab BTC declared review:
  `../RandysLab-STRICT4H/reports/factor_candidate_review/research_v1_3_btc_primary/factor_candidate_review.csv`.
- RandysLab diagnostics:
  `../RandysLab-STRICT4H/reports/factor_candidate_review/research_v1_3_eth_diagnostic`,
  `../RandysLab-STRICT4H/reports/factor_candidate_review/research_v1_3_sol_diagnostic`,
  `../RandysLab-STRICT4H/reports/factor_candidate_review/research_v1_3_bnb_diagnostic`, and
  `../RandysLab-STRICT4H/reports/factor_candidate_review/research_v1_3_avax_diagnostic`.
- RandysLab robustness ranking:
  `../RandysLab-STRICT4H/reports/factor_candidate_robustness/research_v1_3_funding_adjacent_respec/watchlist_robustness_variant_ranking.csv`.
- v1.3 failure memory:
  `reports/failure_memory/research_v1_3_funding_adjacent_respec/failure_memory.csv`.

## Survivor Set

Both surviving rows are variants of one candidate, not two independent factor families.

| Candidate | Variant | Stress Survival | Mean Sharpe | Validation Sharpe | Blind Sharpe | Worst Max DD | Labels |
|---|---|---:|---:|---:|---:|---:|---|
| `qr_v13_funding_range_norm_001` | `thr_0p0_long_flat_cap_0p5_calm_vol_lte_1p5` | 15/15 | 1.2317 | 0.3383 | 0.6310 | 0.2939 | `blind_weakness`, `sol_avax_concentration` |
| `qr_v13_funding_range_norm_001` | `thr_0p0_long_short_cap_0p5_calm_vol_lte_1p5` | 15/15 | 1.1468 | 0.7933 | 0.8921 | 0.3841 | `sol_avax_concentration`, `validation_weakness`, `blind_weakness` |

Formula:

```text
neg(zscore(div(ema(funding_rate,12),div(sub(max(high,96),min(low,96)),close)),120))
```

Manual interpretation: the survivor is a range-normalized funding pressure signal. It is plausibly distinct from the
Research 1.0 survivor, which used long-horizon funding-return correlation, but it is still funding-adjacent and should
not be described as independent non-funding replication.

## Acceptance Reasons

- The survivor family was not the excluded Research 1.0 survivor
  `qr_v09d_funding_return_long_001::thr_0p0_long_short_cap_0p5_none`.
- Both surviving variants passed every current v1.3 scope-aware robustness stress for the declared `BTCUSDT_4h` scope.
- The surviving formula has an interpretable locality hypothesis: high smoothed funding pressure relative to the recent
  high-low range is treated as an overpayment or crowded-carry warning.
- The signal survives both long-flat and long-short mode at the same conservative `0.5` exposure cap.
- The v1.3 export and report correctly label the evidence as
  `funding_adjacent_not_independent_non_funding`.

## Reservations

- The two survivor rows are parameter variants of the same formula, so they do not provide a second independent family.
- Both survivors retain `blind_weakness`; one also keeps `validation_weakness`.
- Both survivors retain `sol_avax_concentration`, so out-of-scope portability remains weak.
- The formula uses `funding_rate` directly. That is allowed for v1.3, but it means the evidence is local to funding,
  carry, and friction structure.
- This review does not prove portfolio-layer suitability, allocation stability, regime classification, or execution
  readiness.

## Manual Decision

The correct next action is paper-observation planning for the single survivor family:

```text
qr_v13_funding_range_norm_001
```

The long-short variant is the primary observation candidate because its validation and blind Sharpe are stronger, but the
long-flat variant should be retained as a paired diagnostic because its drawdown is lower.

This decision does not authorize:

- factor admission;
- runtime manifest publication;
- RandyPortfolio implementation;
- live trading;
- exchange private-key integration;
- automatic factor promotion;
- production regime labels.

## Boundary Confirmation

- No RandyPortfolio implementation.
- No paper runtime publish payload.
- No live trading.
- No exchange private keys.
- No runtime factor publishing.
- No automatic factor admission.
- No new formula base fields.
- No production runtime regime labels.
- No selector evidence61.
