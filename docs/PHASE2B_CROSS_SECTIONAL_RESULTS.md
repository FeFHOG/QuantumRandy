# Phase 2b: Refined Cross-Sectional Family Results

Date: 2026-11-05

Executed exactly as fixed in `docs/PHASE2B_CROSS_SECTIONAL_PROTOCOL.md`. The protocol, the owner's choice of Deflated
Sharpe convention B, the runner and the holdout step were committed and pushed before the run (QuantumRandy `c0feeef`,
RandysLab `4977fe4`). Produced by `scripts/xs_phase2b.py`; artifacts in ignored `reports/phase2b/`. The development
results below were computed with the holdout (2026-09-06 to 2026-10-31) sealed. It was opened afterwards, once; see
"Holdout Result".

## Verdict

**Two trials meet the pre-committed holdout-candidate rule: `taker_14d` and `taker_30d`.** With their composite they
are the three candidates in `preregistrations/phase2b_holdout.json`, which the runner wrote mechanically from the rule's
output and which was committed and pushed (`f2ad500`, `76535f9`) before the holdout was opened.

**The holdout was then opened once, on 2026-11-05, and all three candidates pass the sign check** (mean daily net
return above zero at 1x costs over 55 bars). The evidence is weak, and the mean rank IC over the holdout is negative for
all three. The protocol sends each passing candidate to forward paper observation; the owner chose `taker_30d` only
(`docs/PHASE2B_TAKER_30D_FORWARD_PREREGISTRATION.md`). `taker_14d` and the composite are parked without a test, not
retired.

Both candidates qualify only because criterion 5 uses convention B. Under convention A, Phase 2a's rule, neither would
qualify (Deflated Sharpe 0.45 and 0.62).

## Setup

- Data as Phase 2a: 922 Binance USD-M USDT perpetuals, the point-in-time top-50 crypto universe (367 contracts),
  development window 2020-11-03 to 2026-09-05 (2,133 days). Costs are 4 bps fee plus 5 bps slippage per unit of
  turnover, with settled funding; everything is also run at 2x.
- Metrics (open interest and long/short ratios) for the 359 contracts in the universe from 2021-12: 172,980
  contract-days, 99.5% of the calendar days in their spans, with 0 failed downloads. A rerun finds nothing left to
  fetch, so the remaining days are missing from the archive itself. The largest gaps are ICPUSDT (82% of its span),
  TLMUSDT (84%) and LITUSDT (89%). 1,562 days (0.9%) have fewer than the 288 five-minute snapshots, and their value is
  that day's last available snapshot. Both issues affect only the two open-interest trials, which start on 2022-01-01.

## Results

| Trial | Book | From | Rank IC | IC t (HAC) | BH, N = 18 | Net Sharpe | 2x costs | Turnover/day | Positive IC years | DSR B | DSR A | Robust IC t / Sharpe | Candidate |
|---|---|---|---:|---:|:-:|---:|---:|---:|---:|---:|---:|---:|:-:|
| `taker_30d` | quintile | 2020-11 | +0.019 | +4.66 | yes | **1.77** | **1.60** | 0.16 | 5 of 5 | **0.998** | 0.62 | +4.72 / 1.50 | **yes** |
| `taker_14d` | quintile | 2020-11 | +0.019 | +4.78 | yes | **1.60** | **1.34** | 0.24 | 4 of 5 | **0.990** | 0.45 | +4.88 / 1.62 | **yes** |
| `taker_3d` | quintile | 2020-11 | +0.006 | +1.47 | no | 0.67 | −0.06 | 0.65 | 4 of 5 | 0.50 | 0.01 | +1.38 / 0.41 | no |
| `smart_minus_retail_7d` | quintile | 2022-01 | −0.017 | −3.89 | yes | 0.39 | 0.19 | 0.14 | 0 of 4 | 0.23 | 0.00 | −4.25 / 0.04 | no |
| `basis_1d_buffered` | buffered | 2020-11 | +0.017 | +4.53 | yes | 0.11 | −0.86 | 0.90 | 4 of 5 | 0.09 | 0.00 | +4.13 / −0.10 | no |
| `lowvol_30d_vs_universe` | top vs basket | 2020-11 | +0.092 | +16.98 | yes | 0.00 | −0.14 | 0.09 | 5 of 5 | 0.06 | 0.00 | +16.75 / −0.04 | no |
| `oi_growth_7d` | quintile | 2022-01 | +0.008 | +1.83 | no | −1.21 | −1.94 | 0.69 | 4 of 4 | 0.00 | 0.00 | +1.89 / −1.14 | no |

- **DSR columns:** both use N = 18, Phase 2a's 11 trials plus these 7. B uses the null sampling variance; it is the
  criterion and the owner's choice. A uses the cross-trial variance and is reported only. An independent
  recomputation from the return series matches both to four decimals.
- **Positive IC years:** out of the full years 2021-2025, or 2022-2025 for the open-interest trials.
- **Family PBO** (CSCV, 16 blocks, 7 books, over their common window from 2022-01-01) is 0.005.

**Composite of the two candidates.** The protocol makes it an additional candidate; it is not a trial. Rank IC +0.019
(t +4.75), net Sharpe 1.72 (1.50 at 2x costs), turnover 0.20 a day, positive IC in 5 of 5 years, CAGR 64%, maximum
drawdown 23%.

**Reference, not a trial.** `taker_7d` from Phase 2a, now under forward observation: rank IC +0.014 (t +3.65), net
Sharpe 1.39 (0.97 at 2x costs), turnover 0.37 a day. Its Deflated Sharpe is 0.53 under A at N = 11, and 0.96 under B
at N = 18.

## What The Results Say

**Taker flow is stronger at slower horizons.**

- **14 and 30 days:**
  - net Sharpe 1.60 and 1.77, still 1.34 and 1.60 at 2x costs;
  - maximum drawdowns 24% and 21%;
  - positive net Sharpe in every calendar year, and about the same in the robustness universe.
- **Why slower is better:** turnover falls with the horizon, from 0.37 a day at 7 days to 0.24 and 0.16, so costs
  take less.
- **Funding:** both books also collect 12-14% a year in net funding.
- **3 days is too fast:** turnover is 0.65 a day, the IC t-stat is 1.5, and the book loses money at 2x costs.

**The candidates are close relatives of `taker_7d`.** Their daily net returns correlate 0.80 (14 days) and 0.63 (30
days) with `taker_7d`'s. The protocol anticipated this: under convention B they partly inherit `taker_7d`'s evidence,
and Phase 2a's results partly predicted theirs. They are not independent confirmation of the taker-flow effect. Only
the holdout and forward observation can supply that.

**Not shorting lottery coins removes the losses but earns nothing.** Low volatility against the universe basket keeps
its IC t-stat of 17 and stops losing money. Its net Sharpe is 0.00, against −0.32 for Phase 2a's quintile book.

**Buffering cuts basis turnover, but not enough.** Turnover falls to 0.90 a day from 1.31. Net Sharpe rises to 0.11
from −0.80, but is −0.86 at 2x costs.

**The open-interest factors fail.**

- **`oi_growth_7d`** shorts fast leverage build-ups. Its IC is +0.008 (t 1.8), and its book loses money (net Sharpe
  −1.21) at 0.69 turnover a day.
- **`smart_minus_retail_7d`** has a significantly negative IC (t −3.9): contracts where top traders lean more long than
  the crowd's accounts underperform. That is the opposite of the pre-committed direction, so the trial fails.
  Reversing it now would be a forking path, and the reversed book would lose money. The book as committed earns a
  Sharpe of 0.39 despite its negative IC, the right-skew pattern Phase 2a described.

## Holdout Procedure

`preregistrations/phase2b_holdout.json` lists the three candidates, the hypothesis and the decision rule, and records
the development summary's sha256.

`scripts/xs_phase2b.py --open-holdout preregistrations/phase2b_holdout.json` then:

- refuses to run unless that file is committed unchanged;
- opens the holdout once through the guard and records the opening in the trial ledger;
- writes `reports/phase2b/holdout.json`.

**Decision rule.** A candidate passes if its mean daily net return over the 55 holdout bars is above zero at 1x
costs. Binance omits 2026-10-28, so the 2026-10-29 bar spans two days. Passing candidates move to forward observation
under their own pre-registration; failing candidates are retired.

**Holdout universe.** Listings that were never reviewed are classified with the forward registration's new-listing
rule (protocol, "Changes Before Execution"). On development data, 16 contracts listed since 2025-09-01 that never
entered the development universe already fail its weekend test. Another 20, listed from 2026-07-09 to 2026-09-01,
first reach the 60-bar minimum inside the holdout. The 16 include stock-like tickers (CAT, TER, BX) and also what look
like crypto tokens (HOLO, FLUID, FF, EUL), so the rule is conservative.

**The check is weak.** In 55-bar windows of the development returns, the pass rate depends on the true edge:

- edge as backtested: about 75-79%;
- half that edge: about 60%;
- no edge: about 40-50%.

A pass moves a candidate on to forward observation; it does not confirm it.

## Holdout Result

Opened once, on the owner's go-ahead to apply the new-listing rule, at 2026-11-05 23:45 UTC with
`preregistrations/phase2b_holdout.json` (sha256 `cf95722d590a1fff986885da1eb1705c47695bf200e8287e9280f79df96611f2`).
The trial ledger holds one `holdout_open` row with `repeat_access` false. Outside that run, only bar and funding
timestamps in the window were read, to count bars and to check funding coverage; no price, volume or return. Artifacts
are in ignored `reports/phase2b/holdout.json` and `holdout_run.log`.

| Candidate | Bars | Mean net, bps/day | Cumulative net | Net Sharpe | Turnover/day | Rank IC | Development Sharpe / IC | Sign check |
|---|---:|---:|---:|---:|---:|---:|---:|:-:|
| `taker_14d` | 55 | +16.9 | +7.30% | 1.06 | 0.27 | −0.016 | 1.60 / +0.019 | pass |
| `taker_30d` | 55 | +18.1 | +7.35% | 1.01 | 0.13 | −0.038 | 1.77 / +0.019 | pass |
| `composite` | 55 | +11.8 | +3.94% | 0.67 | 0.21 | −0.030 | 1.72 / +0.019 | pass |

**All three candidates pass the sign check:** the mean daily net return over the 55 bars is above zero at 1x costs.
That is the pre-registered decision, and nothing below changes it. The composite is its own book, so its mean does not
have to lie between its members' means.

**A pass is weak evidence.** In 55-bar windows of the development returns, a candidate with the backtested edge passes
about 75-79% of the time and one with no edge 40-50% of the time, so a pass is only 1.5 to 2 times as likely if the
backtested edge is real as if there is none. The holdout Sharpe ratios (0.7 to 1.1) are below their development values (1.6 to 1.8) but within sampling error of both
those and zero: the standard error of an annualized Sharpe over 55 days is about 2.6.

**The rank IC disagrees with the book.** The mean daily rank IC over the holdout is negative for all three (−0.016,
−0.038, −0.030), against +0.019 in development. IC is not part of the decision rule. Scaling the development
Newey-West standard errors to 55 days gives roughly 0.025, so the holdout values are about 0.7 to 1.5 standard errors
below zero and 1.4 to 2.3 below the development mean. That is compatible with noise, but it is not a confirmation. A
positive book mean next to a negative mean IC is the pattern right-skewed returns produce, and Phase 2a showed it for
several factors. This was not investigated further: every additional look at the holdout is a forking path.

**Funding on the last day.** The universe download's funding ends at 2026-10-31 16:00 (8-hourly contracts) or 20:00
(4-hourly), so the 2026-11-01 00:00 settlement that the last bar would pay is missing. That is at most a third of one
day's funding on one of 55 days, far too small to move a mean of +12 to +18 bps/day across zero.

**Universe.** The new-listing rule excluded 45 contracts that were never reviewed: 11 by the forward registration's
name list, 30 by the weekend test, and 4 with fewer than 60 bars on 2026-10-31, which the test cannot classify. The
names are in `holdout.json`. Whether the rule changed any result was not tested; that would need a second, differently
defined look at the holdout.

**Status.** The holdout is spent: the guard refuses any other pre-registration, and reading it again for these
candidates would be a repeat access. Per the protocol, a passing candidate moves to forward paper observation under its
own pre-registration, with the same betting test and constants from its development window. The owner chose to observe
`taker_30d` only, at the single-test threshold of 20, on development statistics rather than holdout results: its
registration is `docs/PHASE2B_TAKER_30D_FORWARD_PREREGISTRATION.md`, with the first P&L day 2026-11-07. `taker_14d` and
the composite are parked, not retired: they passed the sign check and have no test, and observing them later needs their
own pre-registration and start date. Bars from 2026-11-01 are forward data and count only for observations registered
before them.

## Reproduce

```bash
python ../RandysLab-STRICT4H/scripts/fetch_universe.py        # once; resumable (Phase 2a)
python scripts/xs_phase2b.py --metrics-spans ../RandysLab-STRICT4H/data/metrics_1d_20261105/spans.json
python ../RandysLab-STRICT4H/scripts/fetch_metrics.py --spans ../RandysLab-STRICT4H/data/metrics_1d_20261105/spans.json
python scripts/xs_phase2b.py                                  # evaluation; writes the pre-registration if any trial qualifies
python scripts/xs_phase2b.py --open-holdout preregistrations/phase2b_holdout.json   # run once, on 2026-11-05
```
