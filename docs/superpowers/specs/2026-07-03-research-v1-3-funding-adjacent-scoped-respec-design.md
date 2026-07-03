# Research v1.3 Funding-Adjacent Scoped Re-Spec Design

Date: 2026-07-03

## Summary

Research v1.3 should continue the research-only path after two non-funding replication attempts failed cleanly.
Research 1.0 found one scoped BTCUSDT 4h funding-return survivor. Research v1.1 then tested an independent
non-funding cohort and found no survivor. Research v1.2 used v1.1 failure memory to re-spec a narrower non-funding
cohort; it also found no survivor, with `60/60` robustness rankings blocked and a best near miss at `14/15` scope-hard
stresses.

The next checkpoint should stop treating the current admitted non-funding DSL space as the most promising search area.
Instead, v1.3 should test whether the observed edge is local to funding/carry/friction structure while preserving the
same strict scoped research boundaries.

The working title is:

```text
Research v1.3: Funding-Adjacent Scoped Re-Spec
```

## Decision

Use the funding-adjacent scoped re-spec path.

This is not a continuation of the v1.1/v1.2 independent non-funding replication attempt. It is a locality probe around
the Research 1.0 funding-return survivor. The checkpoint may show that a broader funding-adjacent family exists, or it
may confirm that the current evidence is concentrated in one survivor and should not be generalized.

Rejected alternatives:

- **Paper observation:** still too early because v1.1 and v1.2 did not produce a second scoped family, and Research 1.0
  remains a research-only checkpoint.
- **RandyPortfolio planning:** too early because allocation design would risk treating one funding-return survivor as a
  production input.
- **Another non-funding v1.2-style pass:** lower expected value after v1.1 and v1.2 both failed with informative
  failure memory.
- **Data-readiness-only v1.3:** useful if v1.3 fails, but it would skip the direct question raised by the current
  evidence: whether funding/carry/friction locality is the actual edge.
- **Direct survivor clone:** invalid because it would only rediscover the current Research 1.0 survivor rather than test
  whether a neighboring family is robust.

## Current Evidence

Research 1.0 declared one research-only survivor:

```text
qr_v09d_funding_return_long_001::thr_0p0_long_short_cap_0p5_none
```

The declared scope is:

```text
BTCUSDT_4h
```

Research v1.1 tested `10` independent non-funding current-DSL candidates and found no survivor:

- `50` robustness rankings;
- `50` blocked;
- best blocked near misses survived `12/15` scope-hard stresses;
- failure memory recorded `50` failed rows across `34` clusters.

Research v1.2 tested `12` failure-guided non-funding candidates and found no survivor:

- `60` robustness rankings;
- `60` blocked;
- best blocked near miss survived `14/15` scope-hard stresses;
- failure memory recorded `60` failed rows across `47` clusters.

The v1.2 strongest near miss was:

| Candidate | Variant | Stress Survival | Validation Sharpe | Blind Sharpe | Worst Max DD |
|---|---|---:|---:|---:|---:|
| `qr_v12_volume_turnover_damped_001` | `thr_0p5_long_short_cap_0p5_calm_vol_lte_1p5` | `14/15` | 0.8147 | 0.1895 | 0.3578 |

The repeated failure labels across v1.1 and v1.2 point to:

- blind-window weakness;
- fee and funding stress fragility;
- BTC scope weakness;
- crash-period drawdown;
- SOL/AVAX diagnostic concentration;
- asset-exclusion fragility.

These labels suggest that a purely non-funding signal search is not resolving the key failure modes. A funding-adjacent
probe is the next narrow, falsifiable question.

## Scope

V1.3 remains research-only and uses only the current admitted formula profile:

```text
open, high, low, close, volume, funding_rate
```

Unlike v1.1 and v1.2, v1.3 may use `funding_rate` directly. That must be explicit in the export and report. V1.3 must
not claim to be an independent non-funding replication. It is a funding-adjacent scoped re-spec.

The declared scope remains:

```text
BTCUSDT_4h
```

The out-of-scope policy remains:

```text
diagnostic_only
```

ETH/SOL/BNB/AVAX evidence should remain diagnostic. It can inform failure memory, concentration labels, and manual
research interpretation, but it must not turn the declared scope into a multi-asset deployment claim.

## Independence And Non-Duplication Policy

V1.3 allows funding-adjacent formulas, so it cannot use the v1.1/v1.2 non-funding independence claim. It must instead
enforce a stricter non-duplication policy around the Research 1.0 survivor:

- exclude `qr_v09d_funding_return_long_001::thr_0p0_long_short_cap_0p5_none` from any export, bundle, report, or
  candidate cohort;
- exclude exact candidate IDs, variant IDs, formulas, and bundle membership that reproduce the Research 1.0 survivor;
- label the checkpoint as `funding_adjacent_scoped_respec`, not `independent_non_funding_replication`;
- report any survivor as funding-adjacent evidence pending manual research review, not as a second independent family;
- preserve failure memory for all blocked variants, including funding-adjacent failures.

## Non-Goals

V1.3 must not:

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
- treat ETH/SOL/BNB/AVAX diagnostics as universal deployment requirements;
- claim that funding-adjacent evidence is independent from the Research 1.0 funding-return survivor.

## Candidate Families

V1.3 should export a small deterministic cohort. The cohort should be large enough to test funding-adjacent locality and
small enough that a negative result is informative.

### Family A: Funding Pressure Normalization

This family should test whether funding pressure survives when normalized by current market context.

Design intent:

- use `funding_rate` directly, but avoid copying the Research 1.0 survivor;
- normalize funding pressure by range, volatility, or volume context;
- reduce raw funding-signal fragility during high-volatility periods;
- keep formulas parseable by the current DSL.

Expected failure mode:

- may still be funding-stress fragile;
- may collapse in blind windows if the edge was concentrated in one historical period;
- may lose signal when normalization suppresses the useful carry component.

### Family B: Funding-Return Interaction

This family should test whether funding pressure only matters when price action confirms or rejects it.

Design intent:

- combine `funding_rate` with return, trend, or intrabar direction features;
- distinguish funding pressure that coincides with trend continuation from funding pressure that marks crowding;
- avoid direct reuse of the v1.0 funding-return long-horizon formula;
- prefer simple two-component interactions before larger bundles.

Expected failure mode:

- may become redundant with the Research 1.0 survivor;
- may fail when price confirmation lags the useful funding event;
- may increase turnover or fee sensitivity.

### Family C: Cost-Aware Carry Filters

This family should test whether funding-adjacent signals can reduce fee and funding fragility without introducing
execution-layer controls.

Design intent:

- use signal design only, not drawdown stops or portfolio controls;
- prefer long-flat and lower-turnover variants in RandysLab sensitivity;
- test whether carry-like features can survive fee/funding stress when exposure is capped;
- keep the output as research artifacts, not runtime allocation logic.

Expected failure mode:

- may over-filter and fail completed-row or positive-row floors;
- may still fail strict fee/funding stress;
- may perform only in the v1.0 survivor's original niche.

### Family D: Funding Regime Transition

This family should test whether changes in funding state, rather than static funding level, carry the robust signal.

Design intent:

- use current DSL operators over `funding_rate` to represent pressure shifts, smoothing, or relative funding state;
- test transition and mean-reversion hypotheses separately;
- avoid claiming regime classification for production runtime;
- keep BTC declared scope hard-gated and other assets diagnostic.

Expected failure mode:

- may introduce noisy transition timing;
- may be too sparse for strict completed-row requirements;
- may fail blind windows if the transition behavior is sample-specific.

## Architecture

QuantumRandy owns:

- v1.3 deterministic candidate export;
- v1.3 failure-memory adapter;
- v1.3 final research report;
- docs index and project log updates.

RandysLab owns:

- existing declared-scope strict review;
- existing BTC/ETH/SOL/BNB/AVAX sensitivity and review runs;
- existing BTC correlation and redundancy review;
- existing scope-aware robustness gauntlet.

No RandysLab source change is expected. If execution reveals a real strict-judge bug, it must be fixed with focused
tests and committed separately.

## Data Flow

1. QuantumRandy exports v1.3 research-only funding-adjacent candidates to
   `reports/factor_candidate_exports/research_v1_3_funding_adjacent_scoped_respec`.
2. RandysLab runs BTC primary declared sensitivity and review.
3. RandysLab runs ETH/SOL/BNB/AVAX diagnostics.
4. RandysLab runs BTC correlation and redundancy review for v1.3 bundles.
5. RandysLab runs the scope-aware robustness gauntlet on a fixed variant cohort.
6. QuantumRandy converts robustness rankings into v1.3 failure memory.
7. QuantumRandy renders `docs/RESEARCH_V1_3_FUNDING_ADJACENT_SCOPED_RESPEC_REPORT.md`.

## Success Criteria

V1.3 is complete when:

- a tracked v1.3 report exists;
- the v1.3 export excludes the Research 1.0 survivor;
- the v1.3 export explicitly declares funding-adjacent status and does not claim non-funding independence;
- candidates include funding pressure normalization, funding-return interaction, cost-aware carry, and funding regime
  transition families;
- RandysLab artifacts exist for BTC primary review, ETH/SOL/BNB/AVAX diagnostics, BTC correlation, and robustness;
- v1.3 failure memory is generated from robustness ranking;
- the readiness verdict is one of:
  - `research_v1_3_funding_adjacent_candidate_replicated_pending_manual_review`;
  - `research_v1_3_funding_adjacent_candidate_not_found`;
- full QuantumRandy and RandysLab tests pass;
- all boundary constraints remain intact.

If no v1.3 candidate survives, the correct result is a clean negative report with failure memory. The next recommended
step should then be data-readiness and new admitted-field planning, not another current-DSL funding-adjacent search.

If a v1.3 candidate survives, it remains funding-adjacent evidence pending manual research review. It still does not
authorize paper observation, RandyPortfolio planning, runtime factor publishing, or automatic factor admission.

## Verification Strategy

Focused QuantumRandy tests should cover:

- export schema and safety flags;
- exclusion of the Research 1.0 survivor;
- explicit funding-adjacent metadata;
- absence of any non-funding independence claim;
- candidate family counts and required features;
- parsability of all exported formulas;
- failure-memory behavior, including writing only failed rows to `failure_memory.csv`;
- report renderer readiness verdicts for both survivor and clean-negative cases.

RandysLab focused tests should cover the already-used factor candidate, robustness, and correlation paths. V1.3 should
reuse existing RandysLab CLIs unless a real bug is found.

Final verification should include:

- focused QuantumRandy v1.3 tests;
- focused RandysLab factor-candidate, robustness, and correlation tests;
- both full test suites;
- artifact invariant checks for counts, survivor exclusion, funding-adjacent declaration, verdicts, and boundary
  statements;
- git status checks for both repositories.

## Boundary Statement

Research v1.3 remains a research-only funding-adjacent scoped re-spec. It is not factor admission, runtime publishing,
live execution, portfolio construction, RandyPortfolio implementation, production regime classification, or proof of an
independent non-funding family.
