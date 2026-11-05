# Phase 0–1: Evaluation Spine

Date: 2026-11-05

Status: in progress on branch `phase1/evaluation-spine` (QuantumRandy and RandysLab).

## Why

A November 2026 review found that the stack cannot yet produce trustworthy evidence:

- no clean holdout remains: the 2024-01 → 2025-11 window is the gate, LLM prompt context, selector evidence, and
  RandysLab's "blind" window at the same time;
- the 4-gate filter sits at noise level (rank IC ≥ 0.01 is about 0.6 standard errors on the training window) and
  nothing corrects for the number of formulas tried, which is not even recorded;
- confirmed accounting bugs in both repos (scale-dependent positions, fixed 8h funding, a Stage II window regression,
  stale pass flags);
- the only paper-observed candidate did not demonstrate an edge (`docs/RESEARCH_V1_3_PAPER_OBSERVATION_REPORT.md`).

Recent literature points the same way: on BTC perpetuals an audited agent matched random search at equal budget and
had negative net Sharpe on its holdout (arXiv 2608.25348); trial-count deflation rejected every LLM-found strategy in
2608.27734; FactorBench (2610.06947) found no mining paradigm consistently dominates. The bottleneck is evaluation, not
search.

## Frozen Until Phase 1 Completes

Bug fixes, tests, and changes required by Phase 1 are allowed. No new features in:

- the selector / rewrite / highlight pipeline (`candidate_selector`, `candidate_rewrite`, `selector_pipeline`,
  `selector_evidence`, and their scripts);
- the Research v0.9–v1.3 export, report, and memory modules (kept as the historical record);
- the mining dashboard and runtime dashboard;
- the paper runtime (manifest retired at generation 2, all entries disabled);
- LLM prompt engineering, until an equal-budget comparison against random search exists.

The Sep–Oct 2026 selector logging work is preserved on the local branch `archive/selector-logging-2026-10`.

## Data Policy

- **Burned data.** Everything with bar open time before `2026-09-06T00:00Z` has been used for selection, tuning, or
  observation by some earlier pass. Use it for development and for in-sample diagnostics only, never as confirmation.
- **Sealed holdout.** Bars with open time at or after `2026-09-06T00:00Z`. Access only through the holdout guard with
  a pre-registration file listing every candidate in advance. Each access is recorded in the trial ledger, and a
  pre-registration may be used once.
- **Regime labels.** `2025-10-10/11` liquidation cascade; `2026-10-29 → 2026-11-05` Binance hot-wallet incident
  (withdrawals halted, then reopened in phases). Report results with and without labelled regimes.

## Work Items

| # | Item | Status |
|---|---|---|
| 0.1 | Sync both repos with GitHub; archive the uncommitted selector diff | Done |
| 0.2 | uv lockfiles on Python 3.13, pinned majors, regenerated `requirements.txt` | Done |
| 0.3 | v1.3 verdict; retire the paper runtime manifest | Done |
| 0.4 | Freeze notice (this document) | Done |
| 1.1 | Fix confirmed bugs, each with a regression test | Pending |
| 1.2 | One shared accounting core in RandysLab with event-based funding, checked against an independent reference engine | Pending |
| 1.3 | Append-only trial ledger covering every evaluated candidate | Pending |
| 1.4 | Selection statistics (PSR/DSR, PBO via CSCV, HAC IC t-stat), equal-budget random-search baseline, benchmarks | Pending |
| 1.5 | Sealed holdout guard, regime labels, data refresh into a versioned directory | Pending |
| 1.6 | Re-score the existing leaderboard and survivors through the new spine | Pending |
