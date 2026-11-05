# Phase 2a: Cross-Sectional Baseline Results

Date: 2026-11-05

Executed exactly as fixed in `docs/PHASE2A_CROSS_SECTIONAL_PROTOCOL.md` (protocol, amendment and exclusion list were
committed before any factor was evaluated). Produced by `scripts/xs_phase2a.py`; artifacts in ignored
`reports/phase2a/`. The sealed holdout (2026-09-06 onwards) was not read.

## Verdict

**No factor meets the pre-committed holdout-candidate rule, so the holdout stays sealed.**

Taker-buy flow (`taker_7d`) meets four of the five criteria and fails only Deflated Sharpe: 0.53 against the 0.95
required. Under a different DSR convention, chosen after seeing the results, it would reach 0.98 (see "Taker flow").
Whether to act on that is an owner decision, because it would bend a pre-committed rule and spend the one-shot holdout.

## Setup

- 922 Binance USD-M USDT perpetuals including delisted ones. 367 crypto contracts enter the daily top-50 universe at
  some point. (An earlier version said 370: that was the universe review's count before six non-crypto contracts were
  added to the exclusion list. The results below were computed with the final list.)
- Development window: 2020-11-03 (first day with 50 eligible contracts) to 2026-09-05, 2,133 trading days.
- Dollar-neutral quintile books (top and bottom 20%, gross 1.0), rebalanced daily, 4 bps fee plus 5 bps slippage per
  unit of turnover, settlement-exact funding.

## Results

| Factor | Rank IC | IC t (HAC) | Net Sharpe | Net Sharpe, 2x costs | Price-only Sharpe | Turnover/day | Positive IC years (of 5) | DSR (N=11) | Robust-universe IC t / Sharpe |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `taker_7d` | +0.014 | +3.65 | **1.39** | **0.97** | 1.47 | 0.37 | 4 | 0.53 | +3.77 / 1.35 |
| `carry_3d` | +0.009 | +2.22 | 0.79 | 0.32 | 0.19 | 0.46 | 3 | 0.08 | +1.92 / 0.61 |
| `carry_7d` | +0.007 | +1.64 | 0.74 | 0.44 | — | 0.28 | 3 | 0.06 | +1.38 / 0.74 |
| `mom_30d` | −0.019 | −4.11 | 0.53 | 0.24 | 0.51 | 0.32 | 0 | 0.02 | −4.54 / 0.23 |
| `mom_7d` | −0.028 | −5.59 | 0.32 | −0.23 | 0.83 | 0.62 | 0 | 0.01 | −6.01 / 0.23 |
| `basis_7d` | +0.011 | +3.03 | 0.16 | −0.29 | — | 0.43 | 4 | 0.00 | +2.96 / 0.27 |
| `size_small` | −0.021 | −5.94 | −0.24 | −0.41 | — | 0.14 | 0 | 0.00 | −6.02 / −0.36 |
| `mom_90d` | −0.022 | −4.45 | −0.29 | −0.49 | — | 0.21 | 0 | 0.00 | −4.35 / −0.54 |
| `lowvol_30d` | +0.092 | +16.98 | −0.32 | −0.43 | 0.20 | 0.14 | 5 | 0.00 | +16.75 / −0.22 |
| `basis_1d` | +0.017 | +4.53 | −0.80 | −2.24 | −0.23 | 1.31 | 4 | 0.00 | +4.13 / −1.09 |
| `rev_1d` | +0.026 | +5.23 | −1.92 | −3.33 | −0.56 | 1.52 | 5 | 0.00 | +5.33 / −1.83 |

"Price-only" excludes fees, slippage and funding (computed for diagnosis, not part of the protocol; "—" not computed).
Family PBO (CSCV, 16 blocks) is 0.07: the in-sample ranking of the 11 books largely persists out of sample.

| Benchmark | Sharpe | CAGR | Max drawdown |
|---|---:|---:|---:|
| Equal-weight long-only universe | 0.31 | −8.2% | 94.4% |
| BTC buy-and-hold | 0.57 | 21.1% | 78.9% |

## What The Results Say

**Strong rank effects mostly do not become money.** Low volatility has an IC t-stat of 17 and short-term reversal 5.2,
yet both long-short books lose money. Their rank ICs reflect the median day, while the books earn the mean. Crypto
returns are extremely right-skewed, so the two diverge:

| bps/day, development window | Top quintile mean / median | Bottom quintile mean / median |
|---|---|---|
| `mom_7d` (long winners) | +15.6 / −44.1 | −2.7 / −18.9 |
| `lowvol_30d` (long calm coins) | +13.6 / +3.9 | +7.6 / −62.3 |
| `rev_1d` (long yesterday's losers) | −1.6 / −26.2 | +7.6 / −49.8 |

High-volatility coins and recent winners bleed on a typical day but sometimes explode upwards, so shorting them is
ruinous on the mean. Recent winners give back more than losers on the median day (negative momentum IC), yet their
occasional runs make the long-winners book mildly profitable. Reversal and 1-day basis also turn over 130–150% a day,
which costs alone cannot survive.

**Carry is real income, mostly cancelled by price.** The carry books receive about 34% a year in net funding, but
the coins they short rally and the coins they hold lag, leaving a price-only Sharpe of 0.19. Net Sharpe is 0.79
(0.32 at 2x costs), with an IC t-stat of 2.2, not significant for a family of 11.

**Taker flow is the one robust lead.** Long the contracts with the highest 7-day taker-buy share, short the lowest:

- net Sharpe 1.39 (0.97 at 2x costs), CAGR 48%, maximum drawdown 34%;
- positive net Sharpe in every calendar year (0.65–2.1 in full years) and positive IC in 6 of 7 years;
- the same in the robustness universe (IC t 3.77, Sharpe 1.35);
- the direction was fixed a priori (buy-pressure continuation).

Its Deflated Sharpe fails because of how the protocol estimates the luck benchmark:

- **Pre-committed convention (fails):** the variance of Sharpe ratios across the 11 trials. These factors genuinely
  differ, from −1.9 to +1.4, so the cross-trial standard deviation (0.047 per day) is 2.2 times the estimator's
  sampling noise (0.021). The expected best-of-11 Sharpe under "no edge" becomes 1.46, and `taker_7d`'s 1.49 barely
  clears it: DSR 0.53.
- **Post-hoc sensitivity (would pass):** using the sampling variance of the Sharpe estimator as the null puts the
  benchmark at 0.66 and the DSR at 0.98.

The first is the convention in Bailey & López de Prado and was fixed in advance, so the verdict stands. The second is
a defensible reading, but choosing it after seeing the results is a forking path.

## Options For The Owner

1. **Keep the rule.** The holdout stays sealed. Phase 2b adds open-interest data and pre-commits refined variants
   (taker-flow horizons, skew-aware construction that avoids shorting lottery coins, lower-turnover basis), then tests
   them as one family.
2. **Amend after results.** Pre-register `taker_7d` for the holdout now and open it once. That is about 56 days, so it
   is a weak sign check and uses up the holdout.
3. **Pre-register `taker_7d` for forward paper observation** from today under a sequential test, keeping the holdout
   sealed for the Phase 2b family.

Recommended: 3 together with 1. Forward observation starts the clock on the lead without spending the clean historical
holdout, and Phase 2b tests the refined family with its decision rule fixed in advance.

## Reproduce

```bash
python ../RandysLab-STRICT4H/scripts/fetch_universe.py   # once; resumable
python scripts/xs_phase2a.py --review-universe           # universe review
python scripts/xs_phase2a.py                             # factor evaluation
```
