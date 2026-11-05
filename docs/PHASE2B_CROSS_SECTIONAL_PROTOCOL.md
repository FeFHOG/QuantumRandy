# Phase 2b: Refined Cross-Sectional Family Protocol

Date: 2026-11-05

Status: fixed before any Phase 2b result was computed. The owner chose convention B for criterion 5 on 2026-11-05,
before the evaluation code was written. Any change made before execution is recorded below with its date. Changing a
rule after results are seen voids the corresponding conclusion.

## Question

Do refined versions of the Phase 2a factors, and positioning factors from open-interest data, earn net returns robust
enough to pre-register for the sealed holdout?

Phase 2a (`docs/PHASE2A_CROSS_SECTIONAL_RESULTS.md`) found no holdout candidate. Its diagnostics motivate every variant
below, computed on the same development data, so their development results are partly anticipated. The guards are
the cumulative trial count, the pre-committed rule and the holdout. Development results alone cannot confirm a
variant.

## Unchanged From Phase 2a

Data (`../RandysLab-STRICT4H/data/universe_1d_20261105/`), the point-in-time top-50 crypto universe including the
`NON_CRYPTO` exclusions, execution (scores at the close of day t set positions held during day t+1), costs (4 bps fee
plus 5 bps slippage per unit of turnover, settled funding; everything also at 2x), the robustness universe (contracts
listed before 2025-09-01), the measures, benchmarks and regime reporting. The development window ends 2026-09-05; the
holdout is 2026-09-06 to 2026-10-31 (`docs/PHASE1_EVALUATION_SPINE.md`).

`taker_7d` is not a Phase 2b trial. It is under forward observation
(`docs/PHASE2A_TAKER_FORWARD_PREREGISTRATION.md`) and appears in the tables only as a reference row.

## New Data: Binance Metrics Archive

`data.binance.vision/data/futures/um/daily/metrics/<SYMBOL>/`: 5-minute snapshots of open interest and long/short
ratios, one file per contract and day, checksum-verified. Coverage starts 2020-09 for BTCUSDT but 2021-12 for most
other contracts. The daily value of each column is its last snapshot of the day (23:55 UTC), known at the close.
Downloaded by `../RandysLab-STRICT4H/scripts/fetch_metrics.py` for the 359 contracts that are in the Phase 2a
universe on or after 2021-12-01. Each contract's span runs from 30 days before its first universe day (not before
2021-12-01) to its last universe day in the development window; `scripts/xs_phase2b.py --metrics-spans` writes the
spans. Holdout-window metrics are fetched only if an open-interest trial becomes a holdout candidate.

## Factor Family (7 trials)

Directions and constructions are fixed in advance. A higher score means long.

| Name | Score | Book | Motivation |
|---|---|---|---|
| `taker_3d` | 3-day mean taker-buy share of quote volume, minus 0.5 | quintile long-short | flow persistence at other horizons |
| `taker_14d` | the same over 14 days | quintile long-short | |
| `taker_30d` | the same over 30 days | quintile long-short | |
| `lowvol_30d_vs_universe` | minus 30-day volatility of daily returns | top quintile vs universe basket | the low-volatility rank effect (IC t 17) without shorting lottery coins |
| `basis_1d_buffered` | minus the latest daily premium-index close | buffered quintile long-short | the strongest basis IC (t 4.5) at lower turnover (2a: 1.31 per day) |
| `oi_growth_7d` | minus the 7-day change in log open interest (`sum_open_interest`, contracts) | quintile long-short | fast leverage build-ups mark crowded positioning that unwinds |
| `smart_minus_retail_7d` | 7-day mean of log `sum_toptrader_long_short_ratio` minus log `count_long_short_ratio` | quintile long-short | follow large traders' positions relative to the crowd's accounts |

Book constructions, each dollar-neutral with gross exposure 1.0 and flat when fewer than 10 names have a score:

- **Quintile long-short:** as Phase 2a. Long the top 20%, short the bottom 20%, equal weight within each leg.
- **Top quintile vs universe basket:** long the top 20% equally and short every universe member equally. Weights
  are netted per name, then scaled so gross exposure is 1.0.
- **Buffered quintile long-short:** each leg holds k = floor(20% of the names with a score). A held name stays while
  its rank remains within the leg's outer 40% (top 2k for longs, bottom 2k for shorts). Vacancies are filled with the
  best-ranked names not held. Equal weight 0.5/k per name.

Windows: the taker, low-volatility and basis trials use the Phase 2a development window (2020-11-03 to 2026-09-05). The
open-interest trials start on 2022-01-01, the first full month with metrics for most contracts.

## Measures

As Phase 2a: daily Spearman rank IC with its Newey-West t-stat, net long-short Sharpe (annualized over 365 days, 3%
risk-free rate) at 1x and 2x costs, CAGR, maximum drawdown, turnover, IC by calendar year, Sharpe with labelled
regimes excluded, robustness-universe IC and Sharpe, PBO via CSCV over the 7 books, and the benchmarks.

## Holdout Candidate Rule

The trial count is cumulative: N = 18, the 11 Phase 2a trials plus these 7. A trial becomes a holdout candidate only
if all of these hold in its development window:

1. IC Newey-West t-stat of at least 3.0.
2. A Benjamini-Hochberg discovery at q = 0.05 over the 18 IC p-values of Phase 2a and 2b together.
3. Net Sharpe of at least 0.5 at 1x costs and at least 0 at 2x costs.
4. Positive mean IC in at least 4 of the 5 full years 2021-2025. Open-interest trials need at least 3 of the 4 full
   years 2022-2025.
5. Deflated Sharpe of at least 0.95 with N = 18, under convention B below (null sampling variance), chosen by the
   owner. The runner also reports convention A.

**Criterion 5 convention (owner's choice: B).** Deflated Sharpe compares a trial's Sharpe ratio with the best of N trials that have
no edge. Its spread comes from a variance, and two conventions exist. Figures are daily Sharpe ratios without the 3%
risk-free rate, with the annual equivalents in brackets, over Phase 2a's 2,133 development days.

- **A. Cross-trial variance** of the trials' Sharpe ratios. This is Bailey and López de Prado's convention and Phase
  2a's rule. The 11 Phase 2a books give a standard deviation of 0.047 per day. That is 2.2 times the estimator's
  sampling noise, because the books really differ: cost-driven losers such as `rev_1d` sit far below the rest. With
  N = 18 the no-edge best is 0.087 (1.67), and passing needs about 0.123 (2.35). No Phase 2a book came close; the best
  was 0.078 (1.49).
- **B. Null sampling variance** of the Sharpe estimator, 1/(T - 1). This asks how large the best of N trials would look
  if none had an edge, without counting real differences between distinct books as luck. With N = 18 the no-edge best
  is 0.040 (0.77), and passing needs about 0.076 (1.45). In the open-interest window, which starts 2022-01-01, it needs
  0.085 (1.62).

This choice is being made after seeing Phase 2a's results. Under B, `taker_7d` would score 0.96 and pass at N = 18,
against 0.53 under A at N = 11. That is why `taker_7d` is not a Phase 2b trial: it stays under forward observation.
The taker-horizon trials are correlated with it, so under B they partly inherit its evidence. Under A, Phase 2b is
unlikely to produce any candidate unless a trial is far stronger than anything Phase 2a found.

If two or more trials qualify, their equal-weight composite (average of cross-sectional rank scores, quintile
long-short) is an additional candidate.

## Holdout Decision Rule

Candidates are written to `preregistrations/phase2b_holdout.json` before the holdout is opened, through
`load_panel(..., preregistration=...)`, which records the opening in the trial ledger. The holdout can be opened only
once. A candidate passes if its mean daily net return over the 56 holdout days is above zero at 1x costs. Binance
omits 2026-10-28, so the 56 days are 55 bars, the 2026-10-29 bar spanning both days; the sign of the mean is the same
either way. That is a sign check, not proof.

The holdout universe classifies contracts as the forward observation does
(`preregistrations/phase2a_taker_7d_forward.json`, `new_listing_rule`): a contract outside its reviewed list that was
first listed on or after 2025-09-01 needs a weekend ratio of at least 0.45 over its first 60 bars, which are complete
on the day it becomes eligible. No such contract was ever in the development universe, so development-window days are
unchanged. The rule can also exclude a crypto token that trades quietly at weekends. `holdout.json` lists the
contracts it excludes. A passing candidate moves to forward paper observation under its own pre-registration with the
same betting test and constants from its development window. A failing candidate is retired. If no trial qualifies,
the holdout stays sealed.

## Changes Before Execution

| Date | Change | Reason |
|---|---|---|
| 2026-11-05 | Criterion 5 uses convention B (null sampling variance, N = 18). | Owner's choice, made before the evaluation code was written. |
| 2026-11-05 | The holdout universe applies the forward registration's new-listing rule to unreviewed contracts listed since 2025-09-01. | `NON_CRYPTO` was checked with the weekend test only on contracts that entered the development universe. On development data, 16 contracts listed since 2025-09-01 that never entered it already fail the weekend test, and 20 more, listed from 2026-07-09 to 2026-09-01, first reach the 60-bar minimum inside the holdout. Checked on the sealed panel: the development-window universe is identical. Made before any Phase 2b result was computed. (Counts corrected after the run; the rule is unchanged.) |
