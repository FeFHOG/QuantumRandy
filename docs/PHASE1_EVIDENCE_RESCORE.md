# Phase 1 Evidence Re-score

Date: 2026-11-05

Produced by `scripts/rescore_phase1.py` (artifacts in ignored `reports/phase1_rescore/`). Everything is evaluated on
the configured BTCUSDT 4h validation window, 2024-01-01 → 2025-11-24, after the Phase 1 fixes:

- shared RandysLab accounting core (settlement-exact funding);
- positions from a causal rolling z-score of each factor;
- factors warmed up on the full history;
- the four gates as configured.

No sealed-holdout data was read.

## Verdict

Nothing in the stack shows evidence of an edge.

- Mined formulas did no better than random formulas at the same budget.
- No candidate's predictive power survives multiple-testing correction.
- Every Deflated Sharpe ratio is far below 0.95.
- The highest Sharpe ratios come from near-duplicate trend z-scores with essentially zero rank IC, i.e. trend exposure
  rather than prediction. The hand-built survivors' Sharpe ratios match buy-and-hold BTC.

## 1. Mined versus random at equal budget

The May 2026 `research_live` run scored 214 distinct formulas (all recovered from its artifacts, including zoo
rejects). The same number of random formulas, drawn uniformly from the same DSL and shape limits
(`quantumrandy/random_search.py`), went through the identical gate code path.

| | Mined (214) | Random (214) | Mined, legacy positions |
|---|---:|---:|---:|
| Pass all four gates | 8 | 5 | 8 |
| Median validation Sharpe | −0.15 | −0.13 | −0.09 |
| 90th percentile validation Sharpe | 0.70 | 0.43 | 0.77 |
| Best validation Sharpe | 1.56 | 1.45 | 1.29 |
| Rank IC with \|HAC t\| > 2, unadjusted | 10, all negative | 5 | — |
| Rank IC significant after Benjamini–Hochberg (q = 0.10) | 0 | 1 | 0 |
| Deflated Sharpe of the best candidate | 0.20 (N = 694) | 0.34 (N = 214) | 0.20 (N = 214) |
| Expected best Sharpe of pure noise at that N (annualized) | 2.22 | 1.82 | 1.96 |
| Probability of backtest overfitting (CSCV, 16 blocks) | 0.44 | 0.80 | 0.52 |

Reading the table:

- **Pass counts are indistinguishable.** 8 of 214 against 5 of 214 is well within chance.
- **The mined set's significant results point the wrong way.** All 10 of its unadjusted HAC-significant rank ICs are
  negative: those factors predicted in the opposite direction on validation from the one they were selected for.
- **The random set's one FDR "discovery" loses money.** `div(high,close)` has t = +4.6 but a validation Sharpe of
  −0.44. Predictive IC that does not survive costs matches the BTC-perp audit in arXiv 2608.25348.
- **The best mined Sharpe is below the noise benchmark.** At 1.56 it sits under the 2.22 expected from the best of
  694 noise strategies with the observed spread of trial Sharpes. N = 694 is the historical lower bound from
  `scripts/backfill_trial_counts.py`.
- **The top validation Sharpes are trend exposure, not prediction.** All 9 formulas with a validation Sharpe of 1.0 or
  more are near-duplicate short-horizon price-trend z-scores such as `zscore(sma(zscore(close,12),24),24)`, and all 9
  fail the gates. Their training rank IC is essentially zero (−0.004 to 0.013), and several are more than 0.7
  correlated with each other or the reference library, although their training Sharpe ratios range from 0.26 to 1.25.
- **PBO is a rough flag.** A single CSCV estimate is noisy; on pure-noise panels it ranges from 0.11 to 0.97 across
  seeds.

## 2. The old leaderboard under the fixed engine

`reports/research_live/leaderboard.json` lists 9 factors as passed. Under the fixed engine and gates, 4 of those 9
still pass. Every one of the 8 mined passers has a validation rank-IC t-stat below 0.9.

## 3. Hand-built survivors

The three survivors were re-judged with the RandysLab judge using their exact variant rules: exposure cap 0.5,
threshold 0, and for v1.3 the `zscore(std(close,48),144) <= 1.5` volatility cap. Costs follow the original judging:
4 bps taker and 2 bps slippage.

| Survivor | Validation Sharpe | Excluding stress regimes | Max drawdown | Rank IC (HAC t) | DSR, N = 250 | DSR, N = 694 |
|---|---:|---:|---:|---:|---:|---:|
| Research 1.0, long-short | 0.89 | 1.00 | 21.6% | 0.002 (0.15) | 0.10 | 0.06 |
| v1.3 primary, long-short | 0.84 | 0.97 | 14.8% | 0.009 (0.62) | 0.10 | 0.06 |
| v1.3 paired, long-flat | 0.71 | 0.88 | 14.9% | 0.009 (0.62) | 0.08 | 0.05 |

N = 250 counts only the variant rankings of the cohorts that produced these survivors; N = 694 is the historical lower
bound. Their Sharpe ratios match BTC buy-and-hold (table below) while their predictive correlation is
indistinguishable from zero.

## 4. Benchmarks on the same window

| Benchmark | Validation Sharpe | Excluding stress regimes | CAGR | Max drawdown |
|---|---:|---:|---:|---:|
| BTC buy-and-hold | 0.78 | 0.89 | 33.8% | 34.7% |
| Volatility-targeted buy-and-hold (40%) | 0.80 | 0.93 | 30.6% | 32.5% |
| Funding carry (short when funding > 0) | −0.35 | −0.46 | −22.7% | 55.3% |
| RandysLab MA cross | −0.31 | −0.25 | −21.0% | 65.7% |
| RandysLab Bollinger breakout | 0.04 | −0.02 | −6.6% | 66.1% |

"Excluding stress regimes" removes the 2025-10-10/11 liquidation cascade (`randyslab/regimes.py`).

## What This Means For Phase 2

- More search on single-asset BTC 4h with OHLCV and funding is not justified. The search component, LLM included, is
  indistinguishable from random sampling here.
- Any new candidate must be pre-registered and judged once on the sealed holdout (`2026-09-06` onward, about 330 bars
  per symbol so far). Use it for confirmation only, and expect it to be underpowered for small edges.
- Next, change the question as proposed: a cross-sectional perpetual universe with basis, open-interest and
  taker-flow data, with this evaluation spine applied from the first trial.

## Reproduce

```bash
python scripts/backfill_trial_counts.py   # historical trial lower bound
python scripts/rescore_phase1.py          # writes reports/phase1_rescore/
```
