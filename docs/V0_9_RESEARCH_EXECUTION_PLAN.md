# Research v0.9 Execution Plan

Date: 2026-07-03

This document defines the next research milestone before Research 1.0. It is a research-only execution plan, not a
live-trading plan, not a runtime publishing plan, and not a RandyPortfolio implementation plan.

## Objective

Research v0.9 should prepare the stack for Research 1.0 by producing a clean, reproducible, scoped multi-factor
research checkpoint.

The target is:

```text
multiple factors + explicit asset/regime applicability + future portfolio/risk-layer scheduling
```

The target is not:

```text
one universal factor that must work all-weather across every asset
```

All-asset and cross-regime diagnostics still matter, but their first job is to expose scope, fragility, and failure
modes. They should not silently turn a BTC-scoped factor into a universal deployment requirement.

## Current Starting State

The current stack has useful research infrastructure:

- QuantumRandy can mine and export research-only factor candidates.
- RandysLab can judge candidates with strict next-bar execution, costs, funding, drawdown diagnostics, sensitivity
  sweeps, and robustness scenarios.
- Selector v0.8.2 produced valuable memory around participation and realized-volatility shapes.

The current blocker is evidence quality, not basic tooling:

- selector v0.8.2 is blocked pending new hypotheses;
- validation-window weakness remains unresolved;
- BTC/ETH crash behavior, especially ETH, remains unresolved;
- SOL/AVAX can improve broad averages while creating concentration and exclusion fragility;
- public crypto-native regime features are not yet data-ready as base formula inputs.

## Decision Frame

Research v0.9 should ask these questions for each hypothesis:

1. What asset, asset set, horizon, and regime is this hypothesis intended for?
2. Does the evidence survive strict judgment inside that declared scope?
3. Do failures outside that scope create a fatal contradiction, or do they define an honest applicability boundary?
4. Is the factor distinct enough from other factors to be useful in a future multi-factor bundle?
5. What should be stored as reusable failure memory?

A factor can be useful if it is robust for `BTCUSDT_4h` and honestly labeled as such. It does not need to trade SOL,
AVAX, ETH, and BTC equally well before it can become research memory or scoped watchlist material.

## Required Sequencing

Research v0.9 should be split into checkpoints so implementation does not jump ahead of infrastructure:

```text
v0.9a: scoped schema and strict-judge alignment
v0.9b: BTCUSDT 4h scoped single-family research
v0.9c: BTCUSDT 4h scoped multi-factor research bundle
```

The next local target is v0.9a. It requires:

- QuantumRandy exports with `intended_scope`, `applicability_hypothesis`, and `out_of_scope_policy`;
- RandysLab scope-aware conservative review, so a declared single-asset scope is not judged by universal asset-count
  gates;
- a documented formula profile shared by QuantumRandy exports and RandysLab strict judging;
- RandyPortfolio interface metadata only, with no portfolio scheduler implementation.

Only after v0.9a is verified should agents build the BTCUSDT scoped single-family pass or a multi-factor bundle.

## Regime Feature Staging

Regime-aware research is desirable, but only if features are point-in-time, reproducible, and judged like any other
hypothesis.

Current base formula fields are:

```text
open, high, low, close, volume, funding_rate
```

Current formulas can already express weak regime proxies such as realized volatility, high-low range, volume
participation, price-volume correlation, funding-volume correlation, and funding pressure.

Research v0.9 should stage new regime features in this order:

1. **Data-readiness audit.** Check availability, timestamps, missing values, asset coverage, and survivorship risks.
2. **Base-field decision.** Decide which fields can safely enter the formula DSL, and which should remain diagnostics.
3. **Candidate input.** Allow LLM-mined hypotheses to combine approved fields with existing operators.
4. **Strict judgment.** Require RandysLab to judge regime-aware candidates under declared scope and stress scenarios.
5. **Portfolio-layer deferral.** Do not hard-code production regime labels or allocation rules in QuantumRandy.

Candidate regime fields for audit:

- `open_interest`;
- `basis` or perpetual/spot spread;
- liquidation notional or liquidation imbalance;
- taker buy/sell imbalance;
- depth or order-book imbalance proxies, only if stable and reproducible.

## Work Streams

### Stream A: Repository Hygiene

Goal: make the current research state commit-ready without losing prior work.

Outputs:

- separate commit groups for QuantumRandy docs/archive updates;
- separate commit groups for QuantumRandy factor-candidate export code;
- separate commit groups for RandysLab strict judge extensions;
- separate commit groups for selector v0.8.2 reports and artifacts;
- passing relevant tests or explicit notes for anything not run.

### Stream B: Regime and Public Crypto-Native Data Readiness

Goal: decide which new feature sources are usable before formulas depend on them.

Outputs:

- data availability table by asset and date range;
- schema and timestamp alignment notes;
- missing-data policy;
- leakage and point-in-time risk notes;
- first allowed feature list for new hypotheses;
- explicit decision on base formula fields versus derived diagnostics.

### Stream C: Scoped Candidate Families

Goal: generate hypotheses outside selector v0.8.2 and label their intended scope before strict judgment.

Priority families:

- crash-pressure and deleveraging proxies;
- liquidity stress and participation imbalance;
- funding/open-interest crowding;
- basis dislocation;
- volatility compression and expansion;
- cross-asset confirmation that does not depend on SOL/AVAX concentration.

Outputs:

- research-only candidate exports;
- plain-English hypothesis and expected failure mode for each family;
- intended asset/regime scope for each family;
- failure-memory labels for rejected candidates.

### Stream D: Scoped Multi-Factor Bundle

Goal: test the end-state research shape after v0.9a and v0.9b are complete: multiple factors with explicit boundaries.

Recommended first target:

```text
BTCUSDT 4h multi-factor research bundle
```

Outputs:

- 3-8 candidate factors from distinct families;
- factor-level RandysLab verdicts;
- correlation and redundancy review;
- fixed-weight and simple gated bundle diagnostics as research artifacts only;
- explicit factor applicability labels;
- no runtime publishing and no RandyPortfolio implementation.

### Stream E: Strict RandysLab Judgment

Goal: apply conservative evidence gates fully, not just first-pass screens.

Required diagnostics:

- training, validation, and blind windows for declared scope;
- next-bar execution with fees, slippage, and funding;
- validation-only and blind-only stress;
- crash-window stress;
- cost/funding harshness stress;
- leave-one-asset-out or paired exclusion tests where relevant;
- BTC/ETH-only stress for crash-sensitive hypotheses;
- SOL/AVAX exclusion diagnostics for broad crypto factors.

### Stream F: Documentation and Handoff

Goal: leave compact English artifacts that a future agent can continue from without rediscovery.

Outputs:

- RandysLab strict report with artifact paths and conservative verdict;
- QuantumRandy handoff update;
- QuantumRandy project log update;
- updated factor-factory memory labels;
- exact commands/tests run.

## Labels

Use conservative labels:

- `blocked_pending_new_hypotheses`: exhausted or failed under strict gates.
- `research_memory_only`: useful pattern or failure mode, not a candidate.
- `scoped_watchlist`: promising only inside a declared asset/regime scope.
- `research_1_0_candidate_pending_replication`: strong scoped result that still needs replication before Research 1.0.

Do not use runtime or production labels in Research v0.9.

## Exit Criteria

Research v0.9 is complete when:

- both repositories have a clean committed research checkpoint or explicit commit plan;
- at least one new scoped candidate family outside selector v0.8.2 is judged fully;
- at least one scoped multi-factor bundle is evaluated as a research artifact;
- regime/public crypto-native feature readiness is documented;
- all failures become reusable memory instead of loose notes;
- relevant tests and lint checks pass, or missing checks are explicitly justified;
- the final verdict states whether the stack is ready to pursue Research 1.0.

## Recommended Next Agent Objective

The next agent should target:

```text
Research v0.9a: finish scoped schema and RandysLab strict-judge alignment, then prepare the BTCUSDT 4h scoped
single-family research pass.
```

Selector v0.8.2 should be treated as diagnostic memory unless a task explicitly asks for retrospective analysis.
