# Phase 2b Follow-Up: Forward Paper Observation of `taker_30d`

Date: 2026-11-06 (UTC)

Status: registered before the first observed bar. The first paper position is set at the 2026-11-07 00:00 UTC close
of 2026-11-06; the commit that adds this file, pushed to GitHub before that close, is the registration. The
machine-readable copy is `preregistrations/phase2b_taker_30d_forward.json`; the runner records its SHA-256 on every run.

## Why

Phase 2b (`docs/PHASE2B_CROSS_SECTIONAL_RESULTS.md`) produced two holdout candidates, `taker_14d` and `taker_30d`, and
their composite. They qualified under Deflated Sharpe convention B, the owner's choice, made before the evaluation code
was written; under convention A, Phase 2a's rule, neither would have. The holdout was opened once, on 2026-11-05. All
three candidates passed the pre-registered sign check, on weak evidence: a pass is only 1.5 to 2 times as likely if the
backtested edge is real as if there is none, and the mean rank IC over the holdout was negative for all three
(`taker_30d`: −0.038 against +0.019 in development).

The Phase 2b protocol sends each passing candidate to forward paper observation under its own pre-registration. After
the holdout result the owner chose to observe `taker_30d` only, with the same single-test threshold of 20 as `taker_7d`.
`taker_14d` and the composite are parked, not retired: they passed the holdout sign check and have no test. Testing them
later needs its own pre-registration and start date.

`taker_30d` was chosen on development statistics alone, not holdout results: the highest net Sharpe (1.77), the lowest
turnover (0.16 a day), positive rank IC in all five full years and the highest Deflated Sharpe (0.998). The observation
runs alongside the `taker_7d` observation (`docs/PHASE2A_TAKER_FORWARD_PREREGISTRATION.md`), which it does not change.

## What Is Observed

The Phase 2b book, unchanged, on bars that did not exist when it was specified:

- **Factor:** `taker_30d`, the 30-day mean of `taker_buy_quote_volume / quote_volume` minus 0.5. Higher score means long.
- **Universe:** each day, the 50 crypto USDT perpetuals with the highest median quote volume over the 30 days ending
  that day, among contracts with at least 60 daily bars and a price that day. Excluded: stablecoin bases and the
  Phase 2a `NON_CRYPTO` list. New listings are handled as described below. This is the `taker_7d` universe.
- **Book:** long the top 20% and short the bottom 20% of the universe by score, equal weight within each leg, gross
  exposure 1.0, flat when fewer than 10 names have a score. Scores at the close of day t set the positions held during
  day t+1. A contract without a bar on a day is flat that day.
- **Costs:** 4 bps taker fee plus 5 bps slippage per unit of turnover; funding charged per settlement on the position
  held. The first day pays for building the book from flat. Everything is also reported at twice the trading costs.
- **Code:** `quantumrandy/xsection` (`family_2b.TRIALS["taker_30d"]`, `universe.liquid_universe`,
  `evaluate.quantile_weights`, `evaluate.held_weights`) and `randyslab.accounting.build_portfolio_ledger`, as used for
  Phase 2b. The runner is `scripts/xs_forward_taker.py`, shared with the `taker_7d` observation.

The observed series is the book's daily net return at 1x costs, from 2026-11-07.

### Forward-Specific Rules

These rules cover situations the backtest did not face. They are fixed now, before any forward bar exists, and are the
rules of the `taker_7d` observation.

- **Data.** Daily klines through 2026-10-31 come from `RandysLab-STRICT4H/data/universe_1d_20261105/`. From 2026-11-01,
  daily kline files come from `data.binance.vision/data/futures/um/daily/klines/`, checksum-verified. Funding comes
  from the monthly `fundingRate` archive, published a few days after each month ends. Binance's REST API is
  geo-blocked from the research machine and is not used.
- **Final versus provisional days.** A day is final once its month's funding file is published and every contract
  held that day has its bar. Only final days count for the decision rules. Later days are reported as a provisional
  preview with funding set to zero.
- **Archive gaps.** A day missing from the archive for every contract (Binance omitted 2026-10-28 this way) is not a
  trading day. The next bar's return spans the gap, rolling windows count bars, positions carry across, and funding
  settled during the gap is charged to the next bar. A day missing for a single contract follows the backtest rule:
  that contract is flat that day. A bar of a held contract still missing 7 days after its day counts as never
  published: that contract is flat that day, and the day can become final.
- **New listings.** A contract outside the 367 contracts reviewed in Phase 2a (`reviewed_symbols` in the JSON), with
  its first daily bar on or after 2025-09-01, is crypto only if it passes the Phase 2a weekend test on its first 60
  daily bars: the median absolute return on Saturdays and Sundays divided by that on weekdays is at least 0.45. Phase 2a
  measured 0.13-0.43 for underlyings closed at weekends and 0.55-1.4 for crypto. The weekend test cannot detect
  pre-IPO contracts, which trade on sentiment at weekends too. Contracts named on the append-only list
  `preregistrations/forward_exclusions.json`, which both observations share, are excluded. An entry counts only if it
  was committed before the contract's first eligible day, so no exclusion can be chosen after seeing how the contract
  affected the book.

## The Test

Testing by betting (Shafer 2021; Waudby-Smith and Ramdas 2024), as for `taker_7d`. Two bettors start with wealth 1 and
stake on each day's net return `X_t`, choosing the stake before the day:

- `e_edge` multiplies by `1 + s_t X_t`. Null hypothesis: every day's conditional mean net return is at most 0.
- `e_futility` multiplies by `1 - s_t (X_t - m0)`. Null hypothesis: every day's conditional mean net return is at least
  `m0`, the development-window mean.

The stake is half the Kelly bet implied by the development-window Sharpe ratio, rescaled to current volatility:

```text
s_t = min(0.5 * (m0 / sd0) / sigma_{t-1}, 3.0)
sigma_0^2 = sd0^2;  sigma_t^2 = (1 - a) sigma_{t-1}^2 + a X_t^2,  a = 1 - 0.5^(1/60)   (60-day half-life)
m0  = 0.001514832581470181    mean daily net return of taker_30d, 2020-11-03 .. 2026-09-05 (2,133 days)
sd0 = 0.015428022526786423    its standard deviation
```

The constants come from `reports/phase2b/long_short_returns.csv` (SHA-256 of the file as stored in the JSON), which is
development data only. Under its null, each bettor's wealth is a nonnegative supermartingale, so the chance that it
**ever** reaches 20 is at most 5% (Ville's inequality). The wealth can be checked every day and the observation stopped
at any time without raising that rate. The guarantee assumes no day moves the book by more than 1/3 of equity. The
backtest's worst day was −8.1% and its best +14.6%; a day beyond that bound is flagged.

## Decision Rules

Applied to final days only:

1. **Edge confirmed** when `e_edge` reaches 20: `taker_30d` has a positive mean net return out of sample, at 5%.
   Whether to trade it is then an owner decision outside this protocol.
2. **Retire** when `e_futility` reaches 20: forward returns contradict the backtest's edge at 5%. `taker_30d` stops as
   a standalone candidate. This says the edge is smaller than the backtest's, not that it is zero; `m0` is also the best
   of several trials, so it is likely to be optimistic. A smaller-edge variant would need its own pre-registration.
3. **Otherwise continue.** There is no maximum horizon. The owner may end the observation at any time; ending
   without rule 1 means not confirmed, and ending early cannot create a false confirmation.

Two monitoring flags trigger an owner review but no verdict: a paper drawdown deeper than the backtest's 21.4%, and a
day outside the stake bound.

## Relation To The `taker_7d` Observation

The two observations run side by side on the same data, and each test is valid at 5% on its own. They are not
independent: the development returns of the two books correlate 0.63, so a confirmation of both is not twice the
evidence, and a retirement of both is not twice the evidence either.

Running two tests raises the chance that at least one confirms when there is no edge. Simulated with both books
resampled on the same days (stationary bootstrap, 20-day mean blocks, 10,000 paths) and shifted to a true mean of zero,
the chance of confirming within 10 years is 2.0% for `taker_7d`, 2.3% for `taker_30d`, 3.8% for either and 0.4% for
both. The formal bound for either is 10%; the simulated rate is below the 5% that each test is allowed alone.

## What To Expect

Simulated from stationary-bootstrap resamples of the development returns (20-day mean blocks, 2,000 paths), shifted to
each scenario's true mean, with the settings of the `taker_7d` table. Sharpe is annualized without a risk-free rate (the
Phase 2b tables subtract 3%).

| True edge | Sharpe | Confirmed by 2y | 3y | 5y | 10y | Retired by 2y | 3y | 5y | 10y |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| As backtested | 1.88 | 40% | 79% | 97% | 98% | 0% | 1% | 2% | 2% |
| Two thirds | 1.25 | 15% | 37% | 70% | 75% | 2% | 8% | 22% | 25% |
| Half | 0.94 | 7% | 20% | 43% | 49% | 6% | 19% | 45% | 51% |
| None | 0.00 | 0% | 1% | 2% | 2% | 40% | 73% | 95% | 98% |
| Negative half | −0.94 | 0% | 0% | 0% | 0% | 82% | 97% | 100% | 100% |

No scenario produces a verdict within six months. Within one year confirmation has a 3% chance at most (as backtested),
and retirement 3% with no edge and 20% when the true mean is negative half the backtest's. If the edge is real this
confirms sooner than `taker_7d` (79% against 47% by 3 years as backtested), because its development Sharpe is higher.
That row is optimistic: the development Sharpe belongs to the best of several trials, and the 55-day holdout Sharpe was
1.01 (3% risk-free rate subtracted, as in the Phase 2b tables). The planning case is nearer the "Half" row: a 20% chance
of confirming by 3 years and a 19% chance of retiring.

## Holdout

The Phase 2b holdout (2026-09-06 to 2026-10-31) was opened once, on 2026-11-05, for `taker_14d`, `taker_30d` and their
composite (`docs/PHASE2B_CROSS_SECTIONAL_RESULTS.md`, "Holdout Result"). It is spent. This observation evaluates bars
from 2026-11-07 only, so it overlaps neither the holdout nor the bars of 2026-11-01 to 2026-11-06 that existed before
this registration. Its lookback windows read holdout bars as inputs (bar presence, quote and taker volumes) and the
weekend test reads first-60-day prices of new listings. The runner replaces every price before 2026-11-06 with a
presence flag after classification, so no return of the book or of the factor inside the holdout can be computed from
its panel. The trial ledger records the observation under source `forward_observation`.

## Changes

The factor, universe, book, costs, test constants and decision rules above cannot change. Changing any of them ends
this observation; a new one needs a new pre-registration and a new start date. Bug fixes that make the runner match
this document are allowed: each is listed below with its date and reason, and the record is recomputed from
2026-11-07.

| Date | Change | Reason |
|---|---|---|
| | None yet. | |

The runner was generalized before this registration so that one command serves both observations: `forward_record`
takes the registered factor, the drawdown flag is read from the registration, and every
`preregistrations/*_forward.json` is run. Its outputs for `taker_7d` are byte-identical to the previous runner's on
real and synthetic data.

## Run

```bash
python ../RandysLab-STRICT4H/scripts/fetch_daily.py   # daily klines since 2026-11-01, monthly funding when published
python scripts/xs_forward_taker.py                    # every observation; writes reports/forward_<factor>/ for each
```

The record is rebuilt from the archive on every run, so a missed day costs nothing.
