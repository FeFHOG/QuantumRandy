# Research v1.3 Paper Observation Report

Date: 2026-11-05

Status: final verdict for the v1.3 paper observation, signed off by the owner on 2026-11-05. Drafted by the coding
agent at the owner's request during the Phase 0 close-out (see `docs/PHASE1_EVALUATION_SPINE.md`).

This report is research-only. It is not factor admission, runtime publishing, portfolio construction, RandyPortfolio
implementation, or live execution approval.

## Verdict

```text
research_v1_3_paper_observation_fail_return_to_research
reason: edge_not_demonstrated
```

The protocol (`docs/RESEARCH_V1_3_PAPER_OBSERVATION_PROTOCOL.md`) allows three outcomes: pass, extend, or fail and
return to research. The observation has already been extended once, and the evidence cannot distinguish the candidate
from noise, so "return to research" is the only defensible outcome. The third-project launch gate in
`docs/PRE_THIRD_PROJECT_READINESS_REPORT.md` is therefore **not** met.

## What Was Observed

- Candidate: `qr_v13_funding_range_norm_001`, formula
  `neg(zscore(div(ema(funding_rate,12),div(sub(max(high,96),min(low,96)),close)),120))`, scope `BTCUSDT_4h`.
- Primary variant: `thr_0p0_long_short_cap_0p5_calm_vol_lte_1p5`. Paired diagnostic:
  `thr_0p0_long_flat_cap_0p5_calm_vol_lte_1p5`.
- Fresh bars counted after the complete 4h bar `2026-07-05T12:00Z` (`observation_start_marker.json`).
- Every daily record carries the same code versions: QuantumRandy `5d7a89e`, RandysLab `0d3f5ad`.

| Checkpoint (latest complete 4h bar) | Fresh bars | Primary | Paired diagnostic | BTC buy-and-hold |
|---|---:|---:|---:|---:|
| Hard stop fired (`2026-08-19T04:00Z`) | 268 | −0.49% | +0.34% | +2.48% |
| Declared complete (`2026-08-24T12:00Z`) | 300 | +2.77% (max DD −7.15%) | +3.62% (max DD −2.43%) | +26.08% (max DD −6.22%) |

Both variants are capped at 0.5 exposure, so buy-and-hold is not a like-for-like benchmark. The comparison still shows
that the candidate captured about a tenth of the move with a larger drawdown than BTC itself.

Of the final +2.77%, roughly +3.1 points came from one bar (`2026-08-19 12:00–16:00Z`, BTC +6.27%, held at +0.5
exposure). The volatility cap (`calm_vol_lte_1p5`) then held both variants flat while BTC rose a further 15.4%.

## Stopping-Rule History

Quoted from the observer logs under `reports/paper_observation/research_v1_3_funding_adjacent/logs/`:

| Run (UTC) | Logged result |
|---|---|
| 2026-08-19 04:27 | Still collecting, primary=19 / paired=19 of 20. Hard-stop threshold: fresh bars ≥ 268 or latest complete 4h ≥ `2026-08-19T04:00Z`. |
| 2026-08-19 08:26 | **Hard stop triggered** at 268 fresh bars with 19/20 events: `collection_hard_stopped_insufficient_events`, verdict `research_v1_3_paper_observation_extend_insufficient_event_density`. No further observer runs until 08-24. |
| 2026-08-24 16:00 and 16:10 | `paper_observation_blocked_event_count_mismatch`: primary flips=19 vs trades_delta=20; paired flips=20 vs trades_delta=20. |
| 2026-08-24 16:19 | `collection_complete_20_events`, verdict `observation_collection_complete_pending_manual_review`, at 300 fresh bars. |

The recorded commits of both repos are identical across these runs, so the counting change was made outside the repos,
in the server-side observer (`/root/bin/research_v13_paper_observer.sh`). The 20th counted primary event is the
long-to-flat move at `2026-08-19T12:00Z` caused by the volatility cap. It occurred after the hard-stop cutoff, and the
server runbook asks for "20 non-flat signal events". The extension that started on 2026-08-24 (hard stop
2026-09-05T11:00Z) began with both variants flat; no final extension report exists in either repo or in this workspace.

## Why "Edge Not Demonstrated"

1. **The sample is far too small.** About 10 round trips per variant over 50 days, and both variants trade at the same
   20 timestamps, so they are one observation viewed twice.
2. **The positive result depends on bars after the hard stop.** Had the stop been honoured, the primary result would
   have been −0.49% against BTC +2.48%.
3. **The stopping rule changed after the outcome was visible.** The count definition changed between 16:10 and 16:19
   UTC on identical data and code. Whatever the merits of the new definition, changing it mid-run voids the protocol's
   pre-registration.
4. **The selection evidence was already weak.** The candidate was hand-designed and chosen from hand-built cohorts
   screened on the same 2024-01 → 2025-11 window that earlier passes had reused many times (it served as QuantumRandy's
   validation window and as RandysLab's "blind" window). No correction was made for the number of candidates tried.
5. **The protocol could not fail a noise strategy.** Read literally, none of its fail conditions fired and most pass
   conditions (directional consistency, drawdown inside the robustness envelope) were met. Those conditions are
   satisfied by noise too: the protocol had no statistical-power requirement, no benchmark comparison, and a stopping
   rule that could be edited. The literal reading is therefore not informative.

## Consequences

- `qr_v13_funding_range_norm_001` stays research-only. It must not be cited as validated evidence, promoted, or used as
  the "best known" factor in later work.
- No third-project (RandyPortfolio) planning on the basis of v1.3.
- The legacy paper runtime manifest is retired separately (`configs/runtime_factors.json`, generation 2, all entries
  disabled). Its funding factor `neg(zscore(funding_rate,42))` fails the current gates on the configured windows
  (training directional win rate 0.478 < 0.49; validation Sharpe −0.43, CAGR −23%, max drawdown 72%).
- Future observation protocols need a stopping rule that cannot change mid-run, a minimum power requirement, a
  benchmark comparison, and promotion via a sequential test that stays valid under continuous monitoring.
- Next work follows `docs/PHASE1_EVALUATION_SPINE.md`: trial ledger, Deflated Sharpe and PBO, equal-budget random-search
  baselines, and a sealed holdout starting `2026-09-06T00:00Z`.

## Evidence Files

Ignored local copies (from the server snapshot; workspace archive
`docs/server_snapshots/research_v1_3_server_snapshot_20260824.tar.gz`, SHA-256
`9591f7ad0532db54dccfcc0a72c3b3a9bfb73b13237cfc08f6e95eaef08ca80e`):

- `reports/paper_observation/research_v1_3_funding_adjacent/final_forward_performance.json`
- `reports/paper_observation/research_v1_3_funding_adjacent/final_btc_comparison.json`
- `reports/paper_observation/research_v1_3_funding_adjacent/final_event_detail.csv`
- `reports/paper_observation/research_v1_3_funding_adjacent/consolidated_daily_metrics.csv`
- `reports/paper_observation/research_v1_3_funding_adjacent/logs/run_20260819T082656Z.log`
- `reports/paper_observation/research_v1_3_funding_adjacent/logs/run_20260824T161011Z.log`
- `reports/paper_observation/research_v1_3_funding_adjacent/logs/run_20260824T161959Z.log`

BTC figures were recomputed from
`../RandysLab-STRICT4H/data/research_v1_3_20260824/BTCUSDT_20190908_20260824_complete_only_4h.csv`.
