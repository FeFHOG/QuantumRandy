# Research v1.2 Failure-Guided Scoped Candidate Re-Spec Design

Date: 2026-07-03

## Summary

Research v1.2 should continue the research-only path after Research v1.1 returned a clean negative result. V1.0 found
one scoped BTCUSDT 4h funding-return survivor; v1.1 then tried a second independent non-funding family and found no
survivor across `50` robustness rankings. V1.2 should not move into paper observation or RandyPortfolio planning yet.
It should use the v1.1 failure memory to design a narrower, failure-guided independent non-funding cohort.

The working title is:

```text
Research v1.2: Failure-Guided Scoped Candidate Re-Spec
```

## Decision

Use the failure-guided scoped re-spec path.

Rejected alternatives:

- **Paper observation:** too early because only the Research 1.0 funding-return survivor has passed scope-hard
  robustness; v1.1 did not produce a second independent family.
- **RandyPortfolio planning:** too early because portfolio-layer suitability still lacks independent replicated
  families and would risk treating research artifacts as allocation inputs.
- **Data-readiness-only v1.2:** useful later, but the latest local audit still shows open interest, basis,
  liquidations, taker imbalance, and order-book depth as unavailable or not admitted. V1.2 should stay inside the
  admitted formula profile.
- **Funding-adjacent v1.2:** more likely to find another survivor, but it weakens independence from the current
  Research 1.0 funding-return survivor. It can become v1.3 if v1.2 also fails cleanly.

## Current Evidence

Research v1.1 exported `10` independent non-funding current-DSL candidates:

- `8` single-factor rows;
- `2` equal-weight bundle rows;
- declared scope `BTCUSDT_4h`;
- `out_of_scope_policy=diagnostic_only`;
- excluded `qr_v09d_funding_return_long_001::thr_0p0_long_short_cap_0p5_none`.

RandysLab v1.1 artifacts produced:

- BTC primary declared review: `120` rows, `7` `research_watchlist` rows before robustness;
- ETH/SOL/BNB/AVAX diagnostics;
- BTC bundle correlation review: `1` bundle diversified enough, `1` redundant research-memory-only;
- scope-aware robustness: `50` candidate/variant rankings, all blocked;
- failure memory: `50` failed rows across `34` clusters.

The strongest v1.1 near misses were:

| Candidate | Variant | Stress Survival | Validation Sharpe | Blind Sharpe | Worst Max DD |
|---|---|---:|---:|---:|---:|
| `qr_v11_volume_conviction_001` | `thr_0p0_long_flat_cap_1p0_calm_vol_lte_1p5` | `12/15` | 0.2389 | 0.2626 | 0.4487 |
| `qr_v11_bundle_trend_quality_001` | `thr_0p0_long_flat_cap_1p0_calm_vol_lte_1p5` | `12/15` | 0.1338 | 0.4179 | 0.5698 |
| `qr_v11_bundle_trend_quality_001` | `thr_0p0_long_flat_cap_0p5_calm_vol_lte_1p5` | `10/15` | 0.0589 | 0.2994 | 0.3306 |
| `qr_v11_volume_conviction_001` | `thr_0p0_long_flat_cap_0p5_calm_vol_lte_1p5` | `9/15` | 0.1683 | 0.1544 | 0.2531 |

The dominant failure labels were:

- `sol_avax_concentration`: `50/50`;
- `blind_weakness`: `50/50`;
- `funding_fragility`: `50/50`;
- `fee_fragility`: `50/50`;
- `btc_weakness`: `50/50`;
- `validation_weakness`: `49/50`;
- `asset_exclusion_fragility`: `48/50`;
- `crash_period_drawdown`: `39/50`.

These labels imply that v1.2 should avoid broad all-purpose formulas and instead test candidates that explicitly try
to reduce turnover, drawdown, and blind-window fragility while staying within the declared BTC scope.

## Scope

V1.2 is in scope only if it remains research-only and uses the existing admitted formula profile:

```text
open, high, low, close, volume, funding_rate
```

For this checkpoint, the exported candidates should remain independent from the v1.0 funding-return survivor by
excluding direct `funding_rate` formulas and bundles containing the v1.0 survivor. `funding_rate` may still be used by
RandysLab as a cost/funding stress input, but not as a v1.2 candidate feature.

The declared scope remains:

```text
BTCUSDT_4h
```

The out-of-scope policy remains:

```text
diagnostic_only
```

## Non-Goals

V1.2 must not:

- implement RandyPortfolio;
- plan allocations or portfolio schedules;
- run live trading;
- use exchange private keys;
- publish runtime factors;
- auto-admit factors;
- add production runtime regime labels;
- add new formula base fields;
- run selector evidence61;
- weaken RandysLab strict judge thresholds to force a pass;
- treat ETH/SOL/BNB/AVAX diagnostics as universal deployment requirements.

## Candidate Families

V1.2 should export a small deterministic cohort rather than a broad search. The cohort should be narrow enough that a
negative result is informative.

### Family A: BTC Volume Conviction Hardening

This family starts from the best v1.1 near miss, `qr_v11_volume_conviction_001`, but should reduce turnover and
crash-window fragility. Candidate formulas should combine intrabar direction, volume participation, and range or
volatility normalization using only current DSL operators.

Design intent:

- preserve the volume/price conviction idea that reached `12/15`;
- prefer long-flat and low-turnover variants;
- reduce crash-period drawdown by normalizing conviction by recent range or volatility;
- avoid direct funding fields.

Expected failure mode:

- may still fail when high-volume bars are liquidation reversals;
- may remain fee fragile if signal changes too often;
- may remain blind weak if the effect was concentrated in the v1.1 validation period.

### Family B: BTC Trend-Quality Simplification

This family starts from the v1.1 trend-quality bundle near miss, but should simplify redundant components and avoid
wide all-market portability claims. Candidate formulas should focus on BTC trend quality per unit of recent range,
trend persistence, and drawdown-aware normalization.

Design intent:

- keep the trend-quality idea that reached `12/15`;
- reduce the redundant bundle risk seen in v1.1 correlation review;
- test simpler single-factor and two-component bundle variants before larger bundles;
- keep diagnostics separate from BTC scope-hard gates.

Expected failure mode:

- may fail in sideways BTC regimes;
- may fail crash windows when trend persistence lags regime transition;
- may be too slow for validation or blind windows.

### Family C: Crash-Resilient Participation Filter

This family should explicitly test whether participation signals can be made less fragile during crash windows without
adding new fields. It should combine range expansion, close location, and volume normalization to avoid long exposure
when participation looks like forced liquidation rather than conviction.

Design intent:

- target `crash_period_drawdown` and `asset_exclusion_fragility` labels;
- keep formulas deterministic and parsable by the current DSL;
- do not introduce drawdown-stop execution logic or runtime risk controls;
- treat the family as signal design only.

Expected failure mode:

- may filter out too many bars and fail completed-row or positive-row floors;
- may overfit crash windows and lose normal-regime Sharpe;
- may still fail funding/cost stress if turnover stays high.

## Architecture

QuantumRandy owns:

- v1.2 deterministic candidate export;
- v1.2 failure-memory adapter;
- v1.2 final research report;
- docs index and project log updates.

RandysLab owns:

- existing declared-scope strict review;
- existing BTC/ETH/SOL/BNB/AVAX sensitivity and review runs;
- existing BTC correlation review;
- existing scope-aware robustness gauntlet.

No RandysLab source change is expected. If execution reveals a real strict-judge bug, it must be fixed with focused
tests and committed separately.

## Data Flow

1. QuantumRandy exports v1.2 research-only candidates to
   `reports/factor_candidate_exports/research_v1_2_failure_guided_scoped_respec`.
2. RandysLab runs BTC primary declared sensitivity and review.
3. RandysLab runs ETH/SOL/BNB/AVAX diagnostics.
4. RandysLab runs BTC correlation/redundancy review for v1.2 bundles.
5. RandysLab runs the scope-aware robustness gauntlet on a fixed variant cohort.
6. QuantumRandy converts robustness rankings into v1.2 failure memory.
7. QuantumRandy renders `docs/RESEARCH_V1_2_FAILURE_GUIDED_SCOPED_RESPEC_REPORT.md`.

## Success Criteria

V1.2 is complete when:

- a tracked v1.2 report exists;
- the v1.2 export excludes `qr_v09d_funding_return_long_001` and direct `funding_rate` formulas;
- candidates include failure-guided volume-conviction, trend-quality, and crash-resilient participation families;
- RandysLab artifacts exist for BTC primary review, ETH/SOL/BNB/AVAX diagnostics, BTC correlation, and robustness;
- v1.2 failure memory is generated from robustness ranking;
- the readiness verdict is one of:
  - `research_v1_2_failure_guided_candidate_replicated_pending_manual_review`;
  - `research_v1_2_failure_guided_candidate_not_found`;
- full QuantumRandy and RandysLab tests pass;
- all boundary constraints remain intact.

If no v1.2 candidate survives, the correct result is a clean negative report with failure memory. The checkpoint must
not retry, tune thresholds, or weaken strict judging to force a survivor.

## Verification Strategy

Focused QuantumRandy tests should cover:

- export schema and safety flags;
- exclusion of the v1.0 funding-return survivor and direct `funding_rate` formulas;
- candidate family counts and required features;
- parsability of all exported formulas;
- failure-memory behavior, including writing only failed rows to `failure_memory.csv`;
- report renderer readiness verdicts for both survivor and clean-negative cases.

RandysLab focused tests should cover the already-used factor candidate, robustness, and correlation paths. V1.2 should
reuse existing RandysLab CLIs unless a real bug is found.

Final verification should include:

- focused QuantumRandy v1.2 tests;
- focused RandysLab factor-candidate/robustness/correlation tests;
- both full test suites;
- artifact invariant checks for counts, exclusions, verdicts, and boundary statements;
- git status checks for both repositories.

## Boundary Statement

Research v1.2 remains a research-only checkpoint. It is not factor admission, runtime publishing, live execution,
portfolio construction, RandyPortfolio implementation, or production regime classification.
