# Phase 0–1: Evaluation Spine

Date: 2026-11-05

Status: Phase 1 complete on branch `phase1/evaluation-spine` (QuantumRandy and RandysLab), not pushed.

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
- **Holdout window and forward data (amendment 2026-11-05).** The holdout is the 56 daily bars from 2026-09-06 to
  2026-10-31 (`HOLDOUT_START` to `HOLDOUT_END` in RandysLab `randyslab/holdout.py`), the span the Phase 2a protocol
  describes; opening it no longer returns later bars. Bars from 2026-11-01 are forward data: an observation may
  evaluate them only if its pre-registration was committed before its first evaluated bar. A forward observation may
  read holdout bars as lookback inputs (bar presence, volumes) and to classify new listings, but must never compute the
  performance of a strategy or factor on them. The first is `docs/PHASE2A_TAKER_FORWARD_PREREGISTRATION.md`.
- **Regime labels.** `2025-10-10/11` liquidation cascade; `2026-10-29 → 2026-11-05` Binance hot-wallet incident
  (withdrawals halted, then reopened in phases). Report results with and without labelled regimes.

## Work Items

| # | Item | Status |
|---|---|---|
| 0.1 | Sync both repos with GitHub; archive the uncommitted selector diff | Done |
| 0.2 | uv lockfiles on Python 3.13, pinned majors, regenerated `requirements.txt` | Done |
| 0.3 | v1.3 verdict; retire the paper runtime manifest | Done |
| 0.4 | Freeze notice (this document) | Done |
| 1.1 | Fix confirmed bugs, each with a regression test | Done: QuantumRandy `7ce05a4`; RandysLab `13a6955`, `e2ace17` |
| 1.2 | One shared accounting core in RandysLab with event-based funding, checked against an independent reference engine | Done: RandysLab `ef79621`; QuantumRandy `7ce05a4`; DSL parity `7f9a827` |
| 1.3 | Append-only trial ledger covering every evaluated candidate | Done: RandysLab `3536ef2`; QuantumRandy `8cb3345` (history: at least 694 formula trials) |
| 1.4 | Selection statistics (PSR/DSR, PBO via CSCV, HAC IC t-stat), equal-budget random-search baseline, benchmarks | Done: RandysLab `22316c2`; QuantumRandy `scripts/rescore_phase1.py` |
| 1.5 | Sealed holdout guard, regime labels, data refresh into a versioned directory | Done: RandysLab `a3c4e78`, `e2ace17`; QuantumRandy `26a8152` |
| 1.6 | Re-score the existing leaderboard and survivors through the new spine | Done: `docs/PHASE1_EVIDENCE_RESCORE.md` |

Result: no candidate shows evidence of an edge, and mined formulas match random formulas at equal budget. See
`docs/PHASE1_EVIDENCE_RESCORE.md`.

## Using The Sealed Holdout

- Data: `../RandysLab-STRICT4H/data/archive_20261105/` (Binance archive through 2026-10-31, SHA-256 manifests). It
  matches the old files exactly on the overlap and holds about 330 holdout bars per symbol. All five symbols lack
  2026-10-28 because Binance's archive omits that day.
- Configs still point at `data/<SYMBOL>_4h.csv`, which ends 2025-11-23. Point them at the archive directory to
  develop on 2025-11-24 → 2026-09-05; holdout bars stay sealed automatically.
- To confirm a candidate set, write a pre-registration JSON (`hypothesis`, `candidates` with formulas and variant
  rules, and the decision rule you will apply), configure the trial ledger, then load with
  `load_market_frame(..., preregistration=path)` or `load_market(..., preregistration=path)`. Only one
  pre-registration can ever open the holdout.

## Still Open

- The RandysLab judge evaluates factors without warm-up and lacks 9 miner operators (clip, winsorize, decay_linear,
  ts_argmax, ts_argmin, skew, kurtosis, rank, delay); `tests/test_dsl_parity.py` pins the gap.
- Cross-checking against a third-party engine (NautilusTrader or vectorbt) is not done. An independently written
  bar-by-bar reference engine (`RandysLab tests/test_accounting.py`) and the DSL parity test cover the same risk.
- No genetic-programming baseline yet; random search is the only equal-budget baseline.
- The LLM loop was not re-run. The equal-budget comparison uses the candidates the May run recorded.
- The portfolio scaffolds are frozen and still estimate and evaluate weights on the same slice.
- QuantumRandy configs assume 1 bps slippage and RandysLab 2 bps; harmonizing them is a research decision.
- The paper runtime is retired and pinned to legacy positions.
