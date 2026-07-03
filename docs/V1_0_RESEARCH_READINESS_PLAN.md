# Research 1.0 Readiness Plan

Date: 2026-07-03

This document defines **Research 1.0** for the Randy quant stack. It is not a live-trading plan, not a runtime
promotion plan, and not a RandyPortfolio implementation plan.

Research 1.0 means the research system can repeatedly produce, judge, reject, preserve, and advance factor hypotheses
under strict evidence rules. It does not mean live execution is approved, and it does not require one universal factor
to work all-weather across every asset.

## Completion Update

Research 1.0 is now declared as a research-only checkpoint.

- Final checkpoint report: `docs/RESEARCH_1_0_CHECKPOINT_REPORT.md`.
- Checkpoint verdict: `research_1_0_checkpoint_declared_research_only`.
- Declared scoped candidate:
  `qr_v09d_funding_return_long_001::thr_0p0_long_short_cap_0p5_none`.
- Declared scope: `BTCUSDT_4h`.
- Scope-hard robustness survival: `15/15`.
- Boundary remains unchanged: no RandyPortfolio, no live trading, no exchange private keys, no runtime factor
  publishing, no automatic factor admission, no new formula base fields, no production regime labels, and no selector
  evidence61.

The original plan below is preserved as the definition and historical path that led to the checkpoint.

## Current Position

At the time this plan was written, the stack was past a simple prototype. QuantumRandy could mine and export factor
candidates, while RandysLab could strictly judge them with next-bar execution, fees, slippage, funding, ledgers,
robustness scenarios, and failure labels.

The then-current maturity was best described as:

```text
v0.8 beta: strict research infrastructure exists, but robust factor evidence is not yet sufficient for Research 1.0.
```

Useful current assets:

- QuantumRandy selector evidence and failure-memory pipeline.
- Research-only factor-candidate export format.
- RandysLab strict factor judge.
- RandysLab sensitivity, conservative review, drawdown diagnostics, and robustness gauntlets.
- Paper runtime infrastructure for observation, separated from research.
- Clear stack boundary: QuantumRandy is the factor factory; RandysLab is the strict judge; RandyPortfolio is future work.

Main gap at the time:

- The latest selector v0.8.2 participation-plus-realized-volatility family is blocked pending new hypotheses.
- The current next step is multi-factor, asset-scoped research with explicit applicability boundaries, not another
  attempt to find a single all-weather, all-asset formula.

## Research 1.0 Definition

Research 1.0 is reached when all of these are true:

1. QuantumRandy can export research-only candidates with stable provenance, safety flags, formulas, hypotheses, and
   expected failure modes.
2. RandysLab can judge those candidates reproducibly across assets, windows, costs, funding, drawdown diagnostics,
   declared-scope review rules, and robustness scenarios.
3. At least one candidate family, and preferably two or more independent families, survives strict Research 1.0 review
   gates within a clearly declared asset and regime scope without needing ad hoc exceptions.
4. Failed candidates produce explicit reusable memory labels such as `btc_weakness`, `validation_weakness`,
   `sol_avax_concentration`, `crash_period_drawdown`, `fee_fragility`, and `funding_fragility`.
5. The research loop can move beyond a blocked family instead of repeatedly optimizing the same exhausted hypothesis.
6. Candidate reports distinguish between all-asset robustness, single-asset usefulness, and portfolio-layer suitability.
7. Documentation and artifacts are compact enough that a new agent can continue from the current state without
   restarting discovery.
8. No research artifact is treated as runtime publishing, portfolio construction, live execution approval, or factor
   admission without a separate manual promotion path.

Research 1.0 explicitly excludes:

- live exchange orders;
- exchange private keys;
- automatic runtime factor publishing;
- RandyPortfolio implementation;
- final portfolio allocation;
- production regime classification;
- live execution adapters.

## Research 1.0 Target Shape

Research 1.0 should not optimize for a mythical single factor that works in all regimes across all coins. The target is:

```text
multiple factors + explicit asset/regime applicability + future portfolio/risk-layer scheduling
```

For example, a factor can be useful if it is robust for BTCUSDT 4h in a defined regime, even if it should not be traded
on SOL or AVAX. RandysLab should still stress it across other assets where data exists, but that stress is used to
label scope and failure modes rather than to require universal deployment.

The right research question is therefore:

```text
Where does this factor work, where does it fail, and can those boundaries be used by a future multi-factor portfolio
or risk layer?
```

The wrong research question is:

```text
Can this one factor trade every asset in every regime?
```

## Research 1.0 Gates

The following gates should be treated as hard requirements.

### Candidate Export Gate

Each candidate family must have:

- JSONL or equivalent structured export;
- `research_only: true`;
- `not_runtime_publish_payload: true`;
- formula or component formulas;
- candidate family label;
- source/provenance;
- plain-English hypothesis;
- expected failure mode.

### Strict Judge Gate

Each candidate family must pass RandysLab strict judgment with:

- T+1 or next-bar execution semantics;
- taker fees;
- slippage;
- funding;
- ledger output or reproducible summary artifacts;
- completed rows for the declared target asset or asset set;
- out-of-scope diagnostic rows across other assets where data exists;
- training, validation, and blind windows;
- an explicit `intended_scope` such as `BTCUSDT_4h`, `BTC_ETH_core_4h`, or `altcoin_liquidity_stress_research`.

### Robustness Gate

A Research 1.0 candidate family should survive stress scenarios covering its declared target scope:

- base all-window review;
- higher fee/slippage;
- higher funding;
- combined harsh costs;
- validation-only review;
- blind-only review;
- crash-period review;
- leave-one-asset-out review;
- paired concentration tests where relevant, such as SOL/AVAX exclusion;
- BTC/ETH-only review for crash-sensitive crypto factors.

For out-of-scope assets, failing a stress does not automatically invalidate the factor. It should produce a failure
label and a scope boundary. A BTC-only factor can fail SOL/AVAX and still remain useful if the BTC evidence is strong,
stable, and honestly scoped.

### Conservative Review Gate

The review should block candidates for:

- low mean Sharpe;
- low median Sharpe;
- low positive-row share;
- weak validation window;
- weak blind window;
- high mean drawdown;
- extreme row drawdown;
- positive evidence concentrated in too few assets;
- cost or funding fragility;
- asset-exclusion fragility.

No candidate should be promoted by mean Sharpe alone.

### Regime Feature Gate

Research 1.0 should support regime-aware research, but only with reproducible, point-in-time features. Regime features
should be treated as research inputs and formula components before they become portfolio gates.

Current QuantumRandy formula fields are limited to:

```text
open, high, low, close, volume, funding_rate
```

Current formulas can express weak regime proxies through operators such as `std`, `zscore`, `ret`, `corr`, `rank`,
`skew`, `kurtosis`, `min`, `max`, and `rsi`. Local proposal templates already generate shapes such as realized
volatility, high-low range, price-volume return correlation, funding-volume correlation, and funding-rate pressure.

That is useful, but not a complete regime feature layer. Research v0.9 should add data-readiness checks before
introducing new base fields such as:

- `open_interest`;
- `basis` or perpetual/spot spread;
- liquidation notional or liquidation imbalance;
- taker buy/sell imbalance;
- depth or order-book imbalance proxies if reproducible.

These should not be hard-coded as magic regime labels. They should first enter the research system as point-in-time
base fields and candidate formula components, then be judged by RandysLab like any other hypothesis.

## Current Blocker: Selector v0.8.2

Selector v0.8.2 produced a useful research theme:

```text
participation plus realized volatility
```

The key formula family was:

```text
mean(zscore(ema(volume,48),120), zscore(std(close,48),144))
```

This family produced promising intermediate results:

- long-flat variants were better than long-short variants;
- half exposure reduced drawdown;
- drawdown-stop cooldown helped some validation and 2021-2022 crash rows;
- moderate realized-volatility filters helped some full-exposure variants.

But the stricter gauntlets blocked the family:

- The prior best variant survived `15/16` scenarios but failed the 2020 COVID crash-focused BTC/ETH stress.
- The crash-remediation follow-up tested `7` new combo hypotheses across `7` mitigation variants and `21` stress
  scenarios.
- All `49` final candidate-variant rankings remained `blocked_pending_new_hypotheses`.

The latest best diagnostic row was:

```text
combo_volume48_ret24_calmvol_funding_calm_mean
thr_0p5_long_flat_cap_1p0_none_dd_stop_35_cd_42
```

It improved the broad 2020 COVID slice, but still failed:

- BTC/ETH-only COVID stress on low positive-row share, mainly because ETH remained weak;
- validation-only stress on low mean and median Sharpe;
- validation without SOL/AVAX on low mean and median Sharpe;
- 2021-2022 crash stress;
- very harsh combined cost/funding stress.

Verdict:

```text
selector v0.8.2 is useful diagnostic memory, not a Research 1.0 candidate.
```

## What Is Blocking Forward Progress

The blockers are research blockers, not engineering blockers.

1. **No robust scoped factor bundle yet.**
   The infrastructure can judge candidates, but the latest main family failed strict robustness. The next target should
   be a scoped multi-factor research bundle, not a universal single-factor admission.

2. **The current hypothesis family is saturated.**
   Lower exposure, drawdown stops, trend guards, calm volatility, and funding calmness improved symptoms but did not
   clear validation and crash gates.

3. **ETH crash behavior remains unsolved.**
   BTC/ETH-only COVID and validation stresses showed that fixing all-asset averages is not enough.

4. **Validation-window weakness remains first-class.**
   Several variants looked acceptable in broad or blind slices but failed validation-focused gates.

5. **SOL/AVAX evidence remains double-edged.**
   These assets often contribute positive rows, but paired exclusion and crash diagnostics show concentration and
   drawdown risk.

6. **Regime and public crypto-native feature readiness is not done.**
   Open interest, basis, liquidation prints, taker imbalance, and other market-structure inputs need data-readiness
   checks before becoming the next major hypothesis source.

7. **The repositories are not in release hygiene.**
   Both repos contain substantial uncommitted work. This is acceptable for active research, but not for a versioned
   Research 1.0 checkpoint.

## Version Target Recommendation

Agents should not aim directly at Research 1.0 as the next local milestone. The next target should be:

```text
Research v0.9: Scoped Multi-Factor Hypothesis Engine and Strict Evidence Hygiene
```

Research v0.9 should produce:

- a clean committed baseline for both repos;
- public crypto-native data readiness report;
- at least one new candidate family outside selector v0.8.2 participation-plus-realized-volatility;
- verified scope-aware schema and strict-judge alignment;
- at least one scoped multi-factor research bundle, preferably starting with BTCUSDT 4h;
- strict RandysLab gauntlet artifacts for that new family;
- compact failure-memory feedback into QuantumRandy;
- clear yes/no decision on whether any candidate family can enter Research 1.0 watchlist consideration within a
  declared asset/regime scope.

Research 1.0 should be targeted only after Research v0.9 finds at least one family that survives strict robustness
inside its declared scope without ad hoc exceptions, with out-of-scope failures preserved as labels and memory.

## Recommended Agent Work Streams

### Stream A: Repository Hygiene

Goal: make the current research state commit-ready without losing prior work.

Outputs:

- separate commits or change groups for QuantumRandy docs/archive changes;
- separate commits or change groups for QuantumRandy factor-candidate export code;
- separate commits or change groups for RandysLab strict judge extensions;
- separate commits or change groups for selector v0.8.2 reports and artifacts;
- verified tests for each repo.

### Stream B: Regime and Public Crypto-Native Data Readiness

Goal: decide which new feature sources are usable before creating formulas or regime-aware bundles.

Candidate data sources:

- open interest;
- basis or perpetual/spot spread;
- funding term structure if available;
- liquidation prints;
- taker buy/sell imbalance;
- order-book or depth proxies only if stable and reproducible.

Outputs:

- data availability table by asset and date range;
- schema and timestamp alignment notes;
- missing-data policy;
- RandysLab ingestion feasibility note;
- first allowed feature list for new hypotheses;
- explicit decision on which features become base formula fields and which remain derived diagnostics.

### Stream C: New Hypothesis Families

Goal: move beyond selector v0.8.2 and produce scoped factor candidates.

Priority hypotheses:

- crash-pressure and deleveraging proxies;
- liquidity stress and participation imbalance;
- funding/open-interest crowding;
- basis dislocation;
- regime-aware volatility compression and expansion;
- cross-asset confirmation that does not depend on SOL/AVAX concentration.

Outputs:

- research-only candidate exports;
- strict sensitivity sweeps;
- conservative review;
- robustness gauntlet;
- failure-memory labels;
- intended asset/regime scope for each surviving candidate.

### Stream D: Scoped Multi-Factor Research Bundle

Goal: test the actual end-state shape of the research system: multiple factors with explicit boundaries.

Recommended first scope:

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

### Stream E: Paper Runtime Observation

Goal: keep paper runtime healthy, but do not confuse it with Research 1.0.

Outputs:

- one real Binance feeder one-shot against local runtime;
- monitor report with RandysLab baseline comparison;
- 48-hour paper trial only after the one-shot is clean.

## Research 1.0 Exit Checklist

Research 1.0 can be declared only when:

- both repositories have a clean committed Research 1.0 checkpoint;
- RandysLab tests pass;
- QuantumRandy tests pass;
- at least one scoped factor family or multi-factor research bundle survives strict gates for its declared scope;
- failure-memory reports are updated;
- handoff and project log are updated;
- runtime/paper boundaries remain intact;
- no live execution code or private-key path is introduced;
- next-step docs explain whether to pursue Research 1.1, RandyPortfolio planning, or paper observation.

Exit-checklist result: complete in `docs/RESEARCH_1_0_CHECKPOINT_REPORT.md`.

## Current Recommendation

Set the next agent objective to:

```text
Prepare Research v0.9 by cleaning the current research state, then evaluate scoped multi-factor and public
crypto-native hypothesis families outside selector v0.8.2 under RandysLab strict gates.
```

Do not ask agents to optimize selector v0.8.2 again unless the task is explicitly diagnostic. The family has already
produced useful memory, and the current bottleneck is new scoped hypothesis quality. The preferred next target is a
BTCUSDT 4h multi-factor research bundle with regime-aware features treated as research inputs, not as production
regime labels.
