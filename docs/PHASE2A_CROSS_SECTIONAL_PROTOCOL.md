# Phase 2a: Cross-Sectional Baseline Protocol

Date: 2026-11-05

Status: fixed before any cross-sectional result was computed. Changing a rule below after seeing results voids the
corresponding conclusion; record any change as a dated amendment with its reason.

## Question

Do known cross-sectional premia in Binance USD-M USDT perpetuals earn returns net of costs in a survivorship-free
universe, and are any robust enough to pre-register for the sealed holdout?

Phase 1 showed that single-asset BTC 4h timing has no detectable edge (`docs/PHASE1_EVIDENCE_RESCORE.md`). Ranking
many assets against each other gives far more independent observations per day, and the literature studies it.

## Data

- `../RandysLab-STRICT4H/data/universe_1d_20261105/`: daily klines (incl. taker buy volume), funding settlements and
  premium-index klines for every USDT perpetual in the Binance archive, including delisted contracts, through
  2026-10-31. Checksum-verified; see its `manifest.json`.
- Bars at or after 2026-09-06 are the sealed holdout and are dropped unless a pre-registration opens them.
- Open interest is not used in Phase 2a; its archive is about 200k daily files and is left for Phase 2b.

## Universe

- Rebalanced daily. On day t, take USDT perpetuals with at least 60 daily bars, excluding stablecoin bases, and keep
  the 50 with the highest median quote volume over the 30 days ending on t.
- Only data up to the close of day t is used.
- Development window: from the first day with at least 50 eligible contracts until 2026-09-05.

## Execution and Costs

- Scores computed at the close of day t set positions held during day t+1.
- Each factor's portfolio is long the top 20% and short the bottom 20% of the universe, equal-weighted within each leg,
  with gross exposure 1.0 (0.5 long, 0.5 short).
- Costs are 4 bps taker fee plus 5 bps slippage per unit of turnover. Every result is also reported at twice that.
- Funding is charged per settlement through `randyslab.accounting.build_portfolio_ledger`.

## Factor Family (11 trials)

Directions follow the literature and are fixed in advance. A higher score means long.

| Name | Score | Rationale |
|---|---|---|
| `carry_3d` | minus the 3-day mean funding rate (8h-equivalent) | short crowded longs that pay carry |
| `carry_7d` | minus the 7-day mean funding rate | slower carry |
| `basis_1d` | minus the latest daily premium-index close | short contracts trading rich to spot |
| `basis_7d` | minus the 7-day mean premium-index close | slower basis |
| `mom_7d` | 7-day return | short-horizon momentum |
| `mom_30d` | 30-day return, skipping the last day | medium-horizon momentum |
| `mom_90d` | 90-day return, skipping the last 7 days | slow momentum |
| `rev_1d` | minus the 1-day return | short-term reversal |
| `taker_7d` | 7-day mean taker-buy share of quote volume | buy-pressure continuation |
| `lowvol_30d` | minus 30-day volatility of daily returns | low-volatility premium |
| `size_small` | minus log 30-day median quote volume | small-minus-big within the liquid universe |

Every evaluation is recorded in the trial ledger. No factor, window or parameter is added or changed after results are
seen, except through a dated amendment counted as new trials.

## Measures

- Daily cross-sectional Spearman rank IC between the score on day t and returns over day t+1; its mean with a
  Newey-West t-stat.
- Long-short net Sharpe (annualized with 365 days), CAGR, maximum drawdown and turnover, at 1x and 2x costs.
- IC mean by calendar year, and Sharpe with the 2025-10-10/11 cascade excluded.
- Across the family: Benjamini-Hochberg at q = 0.05 on the IC p-values, Deflated Sharpe with N = 11, and PBO via CSCV
  over the 11 long-short return series.
- Benchmarks: equal-weight long-only basket of the universe, and BTC buy-and-hold.

## Holdout Candidate Rule

A factor becomes a holdout candidate only if all of these hold in the development window:

1. IC Newey-West t-stat of at least 3.0;
2. a Benjamini-Hochberg discovery at q = 0.05;
3. net long-short Sharpe of at least 0.5 at 1x costs and at least 0 at 2x costs;
4. positive mean IC in at least 4 of the 5 full development years 2021-2025;
5. Deflated Sharpe of at least 0.95 with N = 11.

If two or more factors qualify, their equal-weight composite (average of cross-sectional rank scores) is pre-registered
as an additional candidate. Candidates and the decision rule for the holdout are written to a pre-registration file
before the holdout is opened. The holdout holds about 56 days, so it serves as a sign check, not as proof; a candidate
that passes moves to forward paper observation under a sequential test.
