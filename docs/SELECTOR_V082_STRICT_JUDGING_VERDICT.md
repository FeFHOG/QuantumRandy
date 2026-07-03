# Selector v0.8.2 Strict Judging Verdict

Date: 2026-07-03

Scope: selector v0.8.2 milestone factor export, RandysLab strict 4h judging, multi-asset/window/threshold sensitivity,
simple component-combo diagnostics, and conservative review gates.

This is a research-only verdict. It is not a factor admission decision, runtime publish payload, portfolio construction
step, or live execution plan.

## Short Verdict

The selector v0.8.2 evidence60 winners contain useful factor-factory research signal, especially around positive
smoothed participation and positive realized-volatility state. However, none of the exported standalone formulas or
simple combos currently pass conservative RandysLab review.

The strongest diagnostic path is:

```text
mean(zscore(ema(volume,48),120), zscore(std(close,48),144))
```

The best current interpretation is:

- Keep the participation-plus-realized-volatility blend as a research hint.
- Do not admit, publish, or promote it.
- Focus the next research goal on drawdown reduction and window stability.

## Evidence Chain

### QuantumRandy Export

QuantumRandy exported `7` primary selector v0.8.2 milestone formulas from the frozen evidence60 summary:

- `zscore(ema(volume,48),120)`
- `zscore(ema(volume,24),96)`
- `zscore(ema(volume,24),120)`
- `zscore(ema(volume,36),144)`
- `zscore(std(close,48),120)`
- `zscore(std(close,48),144)`
- `zscore(std(close,36),144)`

Export artifact:

```text
reports/factor_candidate_exports/selector_v082_milestone_4_60/
```

The export is JSONL plus CSV mirror and is stamped research-only.

### RandysLab Strict First Pass

RandysLab judged all `7` formulas across local BTC, ETH, SOL, BNB, and AVAX datasets with:

- 4h bars;
- next-bar/T+1 matching;
- fees;
- slippage;
- funding;
- ledger accounting;
- metrics and failure-reason preservation.

All formulas completed without formula failures.

First-pass read:

- BTC was weak under the blunt direct-sign rule.
- SOL and AVAX carried the strongest positives.
- Positive realized-volatility shapes were more stable than expected from the original selector-only read.
- Drawdowns were too large for any admission claim.

### Sensitivity Sweep

Standalone sweep:

- Assets: BTC, ETH, SOL, BNB, AVAX.
- Windows: training, validation, blind.
- Thresholds: `0.0`, `0.5`, `1.0`.
- Rows: `315`.
- Formula failures: `0`.

Best standalone by mean Sharpe:

| Candidate | Formula | Mean Sharpe | Median Sharpe | Worst Sharpe | Mean Max DD |
|---|---|---:|---:|---:|---:|
| `qr_a2cd9fd69f` | `zscore(ema(volume,48),120)` | 0.4083 | 0.4156 | -1.5848 | 0.5814 |
| `qr_e23cfc8ae6` | `zscore(std(close,48),144)` | 0.3558 | 0.4822 | -1.2775 | 0.5848 |
| `qr_295d2e9ee2` | `zscore(ema(volume,24),120)` | 0.3510 | 0.3317 | -1.7473 | 0.5817 |

The sweep confirmed that threshold and window choice matter, but it did not remove drawdown risk.

### Simple Combo Diagnostics

RandysLab also tested four research-only equal-weight component combos. This is not RandyPortfolio and not runtime
publishing.

Best simple combo:

```text
mean(zscore(ema(volume,48),120), zscore(std(close,48),144))
```

Combo sweep summary:

| Combo | Mean Sharpe | Median Sharpe | Worst Sharpe | Positive Rows | Mean Max DD |
|---|---:|---:|---:|---:|---:|
| participation + realized volatility | 0.5412 | 0.7308 | -1.0577 | 35/45 | 0.5336 |

This improved the standalone evidence, but still failed the drawdown standard.

### Conservative Review

The conservative review gate blocks candidates for:

- low mean or median Sharpe;
- weak validation or blind-window Sharpe;
- concentrated positive evidence;
- high mean drawdown;
- extreme row drawdown.

Result:

- `7/7` standalone formulas: `blocked_by_conservative_rules`.
- `4/4` simple combos: `blocked_by_conservative_rules`.

The strongest combo was blocked by:

- `high_mean_drawdown`;
- `extreme_row_drawdown`.

### Long/Flat Drawdown Probe

The first drawdown-reduction probe compared direct long/short exposure with long/flat exposure for simple combos.

Aggregate result:

| Signal Mode | Mean Sharpe | Median Sharpe | Worst Sharpe | Mean Max DD | Worst Max DD | Positive Rows |
|---|---:|---:|---:|---:|---:|---:|
| `long_flat` | 0.6101 | 0.7385 | -1.2124 | 0.4808 | 0.9249 | 151/180 |
| `long_short` | 0.3836 | 0.5220 | -1.8016 | 0.5663 | 0.9572 | 126/180 |

Best long/flat combo:

| Combo | Mean Sharpe | Median Sharpe | Worst Sharpe | Mean Max DD | Worst Max DD | Positive Rows |
|---|---:|---:|---:|---:|---:|---:|
| participation + realized volatility | 0.6969 | 0.7924 | -0.8382 | 0.4626 | 0.9239 | 37/45 |

Long/flat improved the evidence materially, but the conservative gate still blocked it because worst drawdown remained
too high.

## What To Remember

### Positive Research Evidence

- Positive smoothed participation remains meaningful.
- Positive realized-volatility state is stronger under strict judging than selector evidence alone implied.
- Combining participation and realized volatility is better than either theme alone in the first simple diagnostic.
- Long/flat exposure is materially better than long/short for the simple combo set.

### Blockers

- Drawdown is the dominant blocker.
- Extreme row drawdown persists even after long/flat filtering.
- Validation-window weakness appears in several participation-heavy candidates.
- BTC weakness is persistent and should not be ignored.
- SOL/AVAX positives are useful but can overstate robustness if read alone.

### Rejected Interpretations

- Do not treat selector true-improvement evidence as factor admission.
- Do not treat the best combo as a portfolio policy.
- Do not create RandyPortfolio from this evidence.
- Do not publish these formulas into runtime.
- Do not run evidence61 unless explicitly requested.
- Do not globally ban volume-liquidity or range-volatility families; shape, sign, and window still matter.

## Next Research Goals

Recommended one-day Goal mode targets:

1. Drawdown-reduction variants for the participation-plus-realized-volatility combo.
   Test exposure sizing, volatility caps, regime filters, and stricter thresholds under RandysLab conservative review.

2. Strict ledger audit for the blocked-but-interesting combo.
   Inspect the worst rows, worst assets, and worst windows to understand whether drawdown comes from crash periods,
   churn, funding, or asset-specific behavior.

3. RandyPortfolio interface spec only.
   Define what future RandyPortfolio may consume from QuantumRandy and RandysLab without creating the repo or migrating
   current portfolio scaffolds.

## Boundary

- Research-only.
- No live exchange orders.
- No exchange private keys.
- No runtime strategy updates.
- No automatic factor admission.
- No RandyPortfolio repo creation yet.
- Current QuantumRandy portfolio modules remain temporary research scaffolds.
