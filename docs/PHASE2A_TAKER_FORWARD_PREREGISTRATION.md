# Phase 2a Follow-Up: Forward Paper Observation of `taker_7d`

Date: 2026-11-05

Status: registered before the first observed bar. The first paper position is set at the 2026-11-06 00:00 UTC close
of 2026-11-05; the commit that adds this file, pushed to GitHub before that close, is the registration. The
machine-readable copy is `preregistrations/phase2a_taker_7d_forward.json`; the runner records its SHA-256 on every run.

## Why

Phase 2a (`docs/PHASE2A_CROSS_SECTIONAL_RESULTS.md`) found no holdout candidate. `taker_7d` met four of the five
pre-committed criteria and failed only Deflated Sharpe (0.53 against 0.95). On 2026-11-05 the owner chose to keep the
rule (Phase 2b tests refined variants as a new family) and to observe `taker_7d` on paper from today under a test that
stays valid when checked daily, keeping the sealed holdout for Phase 2b.

## What Is Observed

The Phase 2a book, unchanged, on bars that did not exist when it was specified:

- **Factor:** `taker_7d`, the 7-day mean of `taker_buy_quote_volume / quote_volume` minus 0.5. Higher score means long.
- **Universe:** each day, the 50 crypto USDT perpetuals with the highest median quote volume over the 30 days ending
  that day, among contracts with at least 60 daily bars and a price that day. Excluded: stablecoin bases and the
  Phase 2a `NON_CRYPTO` list. New listings are handled as described below.
- **Book:** long the top 20% and short the bottom 20% of the universe by score, equal weight within each leg, gross
  exposure 1.0, flat when fewer than 10 names have a score. Scores at the close of day t set the positions held during
  day t+1. A contract without a bar on a day is flat that day.
- **Costs:** 4 bps taker fee plus 5 bps slippage per unit of turnover; funding charged per settlement on the position
  held. The first day pays for building the book from flat. Everything is also reported at twice the trading costs.
- **Code:** `quantumrandy/xsection` (`factors.FACTORS["taker_7d"]`, `universe.liquid_universe`,
  `evaluate.quantile_weights`, `evaluate.held_weights`) and `randyslab.accounting.build_portfolio_ledger`, as used for
  Phase 2a.

The observed series is the book's daily net return at 1x costs, from 2026-11-06.

### Forward-Specific Rules

These rules cover situations the backtest did not face. They are fixed now, before any forward bar exists.

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
  that contract is flat that day.
- **New listings.** A contract outside the 367 contracts reviewed in Phase 2a (`reviewed_symbols` in the JSON), with
  its first daily bar on or after 2025-09-01, is crypto only if it passes the Phase 2a weekend test on its first 60
  daily bars: the median absolute return on Saturdays and Sundays divided by that on weekdays is at least 0.45. Phase 2a
  measured 0.13-0.43 for underlyings closed at weekends and 0.55-1.4 for crypto. The weekend test cannot detect
  pre-IPO contracts, which trade on sentiment at weekends too. Contracts named on the append-only list
  `preregistrations/forward_exclusions.json` are excluded. An entry counts only if it was committed before the
  contract's first eligible day, so no exclusion can be chosen after seeing how the contract affected the book.

## The Test

Testing by betting (Shafer 2021; Waudby-Smith and Ramdas 2024). Two bettors start with wealth 1 and stake on each day's
net return `X_t`, choosing the stake before the day:

- `e_edge` multiplies by `1 + s_t X_t`. Null hypothesis: every day's conditional mean net return is at most 0.
- `e_futility` multiplies by `1 - s_t (X_t - m0)`. Null hypothesis: every day's conditional mean net return is at least
  `m0`, the development-window mean.

The stake is half the Kelly bet implied by the development-window Sharpe ratio, rescaled to current volatility:

```text
s_t = min(0.5 * (m0 / sd0) / sigma_{t-1}, 3.0)
sigma_0^2 = sd0^2;  sigma_t^2 = (1 - a) sigma_{t-1}^2 + a X_t^2,  a = 1 - 0.5^(1/60)   (60-day half-life)
m0  = 0.0011870355384682384   mean daily net return of taker_7d, 2020-11-03 .. 2026-09-05 (2,133 days)
sd0 = 0.015221591195965587    its standard deviation
```

The constants come from `reports/phase2a/long_short_returns.csv` (SHA-256 in the JSON), which is development data only.
Under its null, each bettor's wealth is a nonnegative supermartingale, so the chance that it **ever** reaches 20 is at
most 5% (Ville's inequality). The wealth can be checked every day and the observation stopped at any time without
raising that rate. The guarantee assumes no day moves the book by more than 1/3 of equity. The backtest's worst day was
−9.8% and its best +15.9%; a day beyond that bound is flagged.

## Decision Rules

Applied to final days only:

1. **Edge confirmed** when `e_edge` reaches 20: `taker_7d` has a positive mean net return out of sample, at 5%. Whether
   to trade it is then an owner decision outside this protocol.
2. **Retire** when `e_futility` reaches 20: forward returns contradict the backtest's edge at 5%. `taker_7d` stops as
   a standalone candidate. A smaller-edge variant would need its own pre-registration.
3. **Otherwise continue.** There is no maximum horizon. The owner may end the observation at any time; ending
   without rule 1 means not confirmed, and ending early cannot create a false confirmation.

Two monitoring flags trigger an owner review but no verdict: a paper drawdown deeper than the backtest's 34.4%, and a
day outside the stake bound.

## What To Expect

Simulated from stationary-bootstrap resamples of the development returns (20-day mean blocks, 2,000 paths), shifted to
each scenario's true mean. Sharpe is annualized without a risk-free rate (the Phase 2a tables subtract 3%).

| True edge | Sharpe | Confirmed by 2y | 3y | 5y | 10y | Retired by 2y | 3y | 5y | 10y |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| As backtested | 1.49 | 14% | 47% | 87% | 99% | 0% | 0% | 1% | 1% |
| Two thirds | 0.99 | 3% | 16% | 46% | 78% | 0% | 2% | 9% | 22% |
| Half | 0.75 | 1% | 7% | 25% | 51% | 2% | 7% | 24% | 49% |
| None | 0.00 | 0% | 0% | 1% | 2% | 13% | 43% | 83% | 98% |
| Negative half | −0.75 | 0% | 0% | 0% | 0% | 47% | 85% | 99% | 100% |

Within one year neither verdict is likely in any scenario (at most 2%). A daily Sharpe of 0.078 needs years of data
to separate from zero; no valid test changes that. The observation is cheap to run (public archive data, no server),
it checks the data and execution path, and it accumulates evidence that cannot be gamed by when one looks.

## Holdout

The sealed holdout is the 56 daily bars 2026-09-06 to 2026-10-31 (amendment in `docs/PHASE1_EVALUATION_SPINE.md`). It
stays sealed for Phase 2b: this observation evaluates bars from 2026-11-06 only. Its lookback windows read holdout bars
as inputs (bar presence, quote and taker volumes) and the weekend test reads first-60-day prices of new listings, but
the runner replaces every price before 2026-11-05 with a presence flag after classification, so no return of the book or
of the factor inside the holdout can be computed. This is not a holdout opening; the trial ledger records it under
source `forward_observation`.

## Changes

The factor, universe, book, costs, test constants and decision rules above cannot change. Changing any of them ends
this observation; a new one needs a new pre-registration and a new start date. Bug fixes that make the runner match
this document are allowed: each is listed below with its date and reason, and the record is recomputed from
2026-11-06.

| Date | Change | Reason |
|---|---|---|
| 2026-11-05, before the first position | A bar of a held contract still missing 7 days after its day counts as never published: that contract is flat that day, as in the backtest, and the day can become final. | Binance omits some days for good (2026-10-28); without a cutoff such a day could never become final. |
| 2026-11-05, before the first position | First 11 entries on the exclusion list: stocks AGPU, CYPH, PATH, RUM, MP, SECZ, USDEX, STM; ETF ZCSH; pre-IPO MOONSHOT, OURA. | Binance launch announcements name their underlyings. All were listed after the development window, and none can be eligible before mid-November. |

## Run

```bash
python ../RandysLab-STRICT4H/scripts/fetch_daily.py   # daily klines since 2026-11-01, monthly funding when published
python scripts/xs_forward_taker.py                    # rebuilds the record from 2026-11-06; writes reports/forward_taker_7d/
```

The record is rebuilt from the archive on every run, so a missed day costs nothing.
