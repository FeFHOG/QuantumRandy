# QuantumRandy v0.8 Beta Handoff

Last updated: 2026-07-03

This handoff records the v0.8 beta state of the Randy quant stack after the first server-paper application layer and
Phase 4 portfolio research path. GitHub-facing notes are intentionally in English.

For the archived v0.8 maturity-level view of what was beta-ready versus still research-only, see
`docs/archive/legacy_runtime_beta/STACK_MATURITY_STATUS.md`.

## Repository State

### QuantumRandy

- Branch: `codex/multi-asset-robustness`
- Remote: `https://github.com/FeFHOG/QuantumRandy`
- Recent pushed commits:
  - `80d117a` Add server paper runtime feeder and monitor
  - `ee77fd5` Add manual runtime factor publisher
  - `6cb2733` Add server agent deployment notes
  - `97926fc` Add offline portfolio research builder
  - `486aad0` Add portfolio contribution analysis
  - `1652dcf` Add portfolio runtime proposal flow
  - `e71d558` Add local paper trial smoke runner
  - `82ca85e` Use RandysLab naming and friction audit gate

### RandysLab

- Local companion repo: `../RandysLab-STRICT4H`
- Remote: `https://github.com/FeFHOG/RandysLab-STRICT4H.git`
- Canonical package: `randyslab`
- Recent pushed commits:
  - `10485be` Add QuantumRandy baseline export
  - `2387b01` Remove legacy compatibility layer

## Safety Boundary

- Target three-project architecture and interface-first boundary note:
  `docs/RANDY_STACK_TARGET_ARCHITECTURE.md`.
- No live exchange orders.
- No exchange trading keys.
- Runtime admin endpoints must stay on `127.0.0.1` or a private interface.
- Research/mining and runtime/paper observation remain separate processes.
- Newly mined factors cannot auto-promote into runtime.
- Runtime updates require a manual publisher or another explicit review flow.
- RandysLab baseline exports are control artifacts, not QuantumRandy runtime publish payloads.
- Current QuantumRandy portfolio, portfolio-universe, and walk-forward modules are research scaffolds, not the final
  RandyPortfolio layer.
- Future live execution is only a reserved roadmap interface after stable multi-factor paper validation. It is not part
  of this beta deployment.

## QuantumRandy Capabilities In This Beta

- Paper runtime server: `scripts/runtime_server.py`
- Read-only server deployment preflight: `scripts/preflight_server.py`
- Binance public-data feeder: `scripts/binance_feeder.py`
- Read-only runtime monitor and daily report: `scripts/runtime_monitor.py`
- Read-only runtime web dashboard: `scripts/runtime_dashboard.py`
- Optional RandysLab baseline comparison in runtime reports via `configs/runtime_monitor.yaml`
- Manual factor publisher: `scripts/publish_factors.py`
- Offline portfolio research builder: `scripts/build_portfolio.py` (temporary research scaffold)
- Portfolio fixed-blend walk-forward validator: `scripts/portfolio_walk_forward.py` (temporary research scaffold)
- Optional RandysLab baseline comparison in `PORTFOLIO_REPORT.md` via `--baseline-summary`
- Portfolio contribution and ablation analysis
- Reviewable runtime proposal flow for fixed portfolio blends
- Local end-to-end paper trial smoke runner: `scripts/run_paper_trial.py`

## Verified Commands

RandysLab:

```bash
python -m pytest
```

QuantumRandy:

```bash
python -m pytest
python scripts/build_portfolio.py --leaderboard reports/research_live/leaderboard.json --out reports/portfolio_smoke
python scripts/portfolio_walk_forward.py \
  --portfolio-manifest reports/portfolio_smoke/portfolio_manifest.json \
  --portfolio-factors reports/portfolio_smoke/portfolio_factors.csv \
  --portfolio-id equal_weight_accepted \
  --out reports/portfolio_walk_forward_smoke
python scripts/run_paper_trial.py \
  --portfolio-manifest reports/portfolio_smoke/portfolio_manifest.json \
  --portfolio-factors reports/portfolio_smoke/portfolio_factors.csv \
  --portfolio-id equal_weight_accepted \
  --out reports/paper_trial_smoke
```

The local paper trial path is:

```text
portfolio manifest -> runtime proposal -> localhost runtime -> submit proposal -> push local bars -> monitor report
```

`stale=True` is expected when the trial uses old local historical sample data.

## Server 48h Paper Trial Checklist

Use `docs/archive/legacy_runtime_beta/SERVER_48H_TRIAL_RUNBOOK.md` as the operator-facing Ubuntu/tmux checklist for the
first full trial.

1. Start `scripts/runtime_server.py` with `QUANTUMRANDY_ADMIN_TOKEN` and `QUANTUMRANDY_INGEST_TOKEN` set to long random
   local-only values.
2. Keep the runtime bound to `127.0.0.1` or a private interface.
3. Start `scripts/binance_feeder.py` with only the ingest token.
4. Start `scripts/runtime_monitor.py` with the RandysLab baseline summary path configured if the export is present.
5. Preserve process logs plus `reports/runtime_live/snapshots.jsonl`, `latest_snapshot.json`, and daily Markdown reports.
6. Do not change active runtime strategies during the first smoke period unless fixing a runtime bug.
7. After 48 hours, check for missing 4h bars, stale-bar alerts, process restarts, abnormal drawdown, and readability of
   the daily report.

## Manual Paper Blend Promotion Checklist

1. Build or refresh portfolio artifacts with `scripts/build_portfolio.py`.
2. Review `PORTFOLIO_REPORT.md`, `portfolio_summary.csv`, `portfolio_contribution.csv`, and component factor metrics.
3. Compare the proposed blend with the RandysLab baseline export for the same symbol/window when available.
4. Generate a dry-run runtime proposal with `scripts/publish_factors.py` and no `--submit`.
5. Inspect the generated JSON payload and audit Markdown file.
6. Submit only after manual approval with `--submit`.
7. Record runtime generation, selected portfolio ID, component weights, and promotion rationale.

## Selector Rewrite Research State

- Latest hard-gated LLM-only successful repeat: `reports/selector_rewrite_pipeline_llm_v082_evidence60_conflict_aware_memory_repeat`
- Latest LLM-policy repeat without true-improvement evidence:
  `reports/selector_rewrite_pipeline_llm_v082_evidence55_conflict_aware_memory_repeat`
- Latest failed repeat artifact: `reports/selector_rewrite_pipeline_llm_v082_evidence47_conflict_aware_memory_repeat`
  failed the LLM policy-evidence gate due to repeated SSL EOF transport errors and produced no candidates.
- Current aggregate summary: `reports/selector_pipeline_evidence_v082_summary`
- Aggregate runs: `57`
- LLM policy evidence runs: `53`
- LLM true-improvement evidence runs: `35`
- Coverage-only trap runs: `4`
- Highlighted candidate rows: `115`
- Negative candidate rows: `109`
- Negative candidate family rows: `19`
- Strongest repeated theme: positive smoothed volume participation, led by `zscore(ema(volume,48),120)`.
- Latest evidence60 note: `zscore(ema(volume,48),120)`, `zscore(std(close,24),144)`, and
  `zscore(std(close,12),120)` were true-improved; raw signed price-volume correlation remained weak.
- Latest evidence55 note: attribution-clean LLM policy evidence, but no true-improved highlights; all four accepted
  candidates were not improved, reinforcing negative memory for raw signed price-volume correlation, negative
  range-volume correlation, and negative volatility-regime signs.
- Current memory posture: keep exact failed-formula blocking and sign-aware negative memory, but do not mechanically
  block entire volume-liquidity or range-volatility families.
- Milestone review: `docs/SELECTOR_REWRITE_V0_8_2_MILESTONE_REVIEW.md`.
- Selector repeat stop: do not run evidence61 unless explicitly requested. Marginal evidence is saturated enough to
  move to research-only candidate export and strict RandysLab judging.
- Research-only factor-candidate export:
  `reports/factor_candidate_exports/selector_v082_milestone_4_60/`.
- Export docs: `docs/FACTOR_CANDIDATE_EXPORTS.md`.
- Export contents: `7` primary formula candidates as JSONL plus CSV mirror, manifest, and Markdown summary.
- First RandysLab strict judge pass completed across local BTC, ETH, SOL, BNB, and AVAX datasets. All `7` formulas
  completed without formula failures under next-bar/T+1 matching, fees, funding, slippage, ledgers, metrics, and
  failure-reason preservation.
- First strict read: mixed, not admission evidence. BTC was weak under the blunt direct-sign rule; SOL/AVAX supplied
  the strongest positives. The best mean-Sharpe formulas across the five local assets were
  `zscore(std(close,48),144)` and `zscore(std(close,48),120)`, but drawdowns remained large.
- Window/threshold sensitivity sweep completed across BTC, ETH, SOL, BNB, AVAX; training, validation, blind; and
  thresholds `0.0`, `0.5`, `1.0`. All `315` standalone rows completed.
- Simple equal-weight component combo sweep completed with `180` rows. The strongest diagnostic blend was
  `mean(zscore(ema(volume,48),120), zscore(std(close,48),144))`, which improved mean Sharpe and worst-row Sharpe
  versus the standalone formulas, but still had large drawdowns.
- Conservative RandysLab review gate completed. All `7` standalone formulas and all `4` simple combos were
  `blocked_by_conservative_rules`; the strongest combo was blocked for `high_mean_drawdown` and
  `extreme_row_drawdown`.
- Long/flat drawdown probe improved simple-combo aggregate metrics versus long/short. Best long/flat combo remained
  `mean(zscore(ema(volume,48),120), zscore(std(close,48),144))`, with mean Sharpe `0.6969`, median Sharpe `0.7924`,
  worst Sharpe `-0.8382`, and mean max drawdown `0.4626`; it still failed conservative review due to drawdown.
- Scoped RandysLab drawdown-reduction pass completed for the participation-plus-realized-volatility combo only. The
  pass was long-flat only and swept thresholds `0.5`, `1.0`, `1.5`, `2.0`; exposure caps `1.0`, `0.75`, `0.5`, `0.25`;
  and simple realized-volatility caps using `zscore(std(close,48),144) <= 1.5` or `<= 1.0` across BTC, ETH, SOL, BNB,
  AVAX and training/validation/blind windows.
- Drawdown-reduction result: `11/48` variants became RandysLab `research_watchlist`; `37/48` remained
  `blocked_by_conservative_rules`. The best drawdown-balanced variant was
  `thr_0p5_long_flat_cap_0p5_none`, with mean Sharpe `0.6378`, median Sharpe `0.5469`, mean max drawdown `0.2785`,
  worst max drawdown `0.6975`, and positive rows `14/15`.
- The full-exposure no-filter control at threshold `0.5` still failed for
  `high_mean_drawdown|extreme_row_drawdown`. Lower exposure caps and the `rvz_lte_1p5` volatility cap were the clearest
  drawdown reducers. BTC weakness and validation-window fragility remain material caveats.
- Deep RandysLab drawdown mitigation completed for the same participation-plus-realized-volatility combo. The expanded
  campaign swept `4320` strict rows across long-short and long-flat modes, exposure caps, realized-volatility filters,
  stricter thresholds, and research drawdown-stop cooldown rules. Conservative review produced `44/288`
  `research_watchlist` variants and `244/288` blocked variants.
- Best deep-mitigation variant: `thr_0p5_long_flat_cap_0p5_none_dd_stop_35_cd_42`, with mean Sharpe `0.6419`, median
  Sharpe `0.6415`, worst Sharpe `-1.0450`, mean max drawdown `0.2683`, worst max drawdown `0.5888`, and positive rows
  `14/15`. This is still a research-watchlist label only, not factor admission or runtime publishing.
- Drawdown root-cause audit captured `3329` episodes across a `1440` row core grid. Worst episode: SOLUSDT validation,
  full-exposure long-flat control, peak `2021-09-09 00:00 UTC`, trough `2022-11-09 16:00 UTC`, max drawdown `0.9239`.
  Preserved labels: `sol_avax_concentration|validation_weakness|crash_period_drawdown|extreme_row_drawdown`.
- Factor-factory memory update: keep participation plus realized volatility as a useful theme; prefer long-flat,
  half-exposure, and moderate realized-volatility filters as strict-judge mitigation hints; do not promote
  full-exposure variants; do not treat drawdown stops as a cure without exposure control; preserve BTC weakness,
  SOL/AVAX concentration, validation weakness, and crash-period drawdown labels.
- Strict judging verdict: `docs/SELECTOR_V082_STRICT_JUDGING_VERDICT.md`.
- Drawdown-reduction summary: `../RandysLab-STRICT4H/docs/SELECTOR_V082_DRAWDOWN_REDUCTION_PASS.md`.
- Deep drawdown mitigation summary:
  `../RandysLab-STRICT4H/docs/SELECTOR_V082_DRAWDOWN_DEEP_MITIGATION_REPORT.md`.
- Follow-up RandysLab robustness gauntlet completed for the leading watchlist and near-miss variants under stricter
  fee/slippage, funding, combined harsh-cost, crash-window, leave-one-asset-out, validation-only, and blind-only
  stresses. Artifacts:
  `../RandysLab-STRICT4H/reports/factor_candidate_robustness/selector_v082_combo_watchlist_robustness_gauntlet/`.
- Robustness verdict: no tested variant remains `research_watchlist` after the stricter gauntlet. The best prior
  watchlist variant, `thr_0p5_long_flat_cap_0p5_none_dd_stop_35_cd_42`, survived `15/16` scenarios but failed the
  2020 COVID crash-focused window on BTC/ETH weakness. The tested family is downgraded to
  `blocked pending new hypotheses`.
- Robustness report:
  `../RandysLab-STRICT4H/docs/SELECTOR_V082_WATCHLIST_ROBUSTNESS_GAUNTLET_REPORT.md`.
- Follow-up RandysLab crash-remediation hypothesis gauntlet completed without restoring watchlist status. The pass
  tested `7` research-only combo candidates across the prior `7` mitigation variants and `21` strict stress scenarios,
  including paired SOL/AVAX exclusion, BTC/ETH-only validation, and BTC/ETH-only 2020 COVID stress. Artifacts:
  `../RandysLab-STRICT4H/reports/factor_candidate_robustness/selector_v082_crash_remediation_hypothesis_gauntlet/`.
- Crash-remediation verdict: all `49` candidate-variant rankings remain `blocked_pending_new_hypotheses`. The best new
  diagnostic row, `combo_volume48_ret24_calmvol_funding_calm_mean` with
  `thr_0p5_long_flat_cap_1p0_none_dd_stop_35_cd_42`, survived `16/21` scenarios and improved the broad 2020 COVID
  slice, but still failed BTC/ETH-only COVID on low positive-row share and failed validation-focused stresses on low
  mean/median Sharpe.
- Crash-remediation report:
  `../RandysLab-STRICT4H/docs/SELECTOR_V082_CRASH_REMEDIATION_HYPOTHESIS_REPORT.md`.
- Factor-factory memory update: trend plus calm-volatility plus funding-calm components can reduce the prior COVID
  crash symptom, but they are diagnostic memory only. Selector v0.8.2 remains blocked pending genuinely new hypotheses,
  with ETH crash behavior, validation robustness, and SOL/AVAX paired-exclusion fragility preserved as first-class
  labels.
- Boundary: these are research-only selector evidence artifacts, not runtime publish payloads or admission decisions.

## Next Best Steps

- Treat the drawdown-reduced participation-plus-realized-volatility family as blocked pending new hypotheses after the
  robustness gauntlet. Do not publish it into runtime and do not promote it as admitted factor evidence.
- Next strict research checkpoint should be Research v0.9a: scoped schema and strict-judge alignment. Confirm
  `intended_scope`, `applicability_hypothesis`, and `out_of_scope_policy` flow from QuantumRandy exports into RandysLab
  sensitivity/review artifacts before starting a BTCUSDT scoped single-family pass.
- After v0.9a, move beyond the tested selector v0.8.2 crash-remediation formula family. ETH crash behavior,
  validation-window robustness, and SOL/AVAX paired-exclusion fragility should remain hard gates.
- Add public crypto-native feature candidates only after data readiness checks for open interest, basis, liquidation
  prints, and taker imbalance.
- Keep RandyPortfolio as an interface-only future consumer. Do not implement portfolio scheduling, dynamic allocation,
  or production regime routing in QuantumRandy or RandysLab.
- Run one real Binance feeder one-shot against a local runtime and inspect the monitor report with baseline comparison.
- If that is clean, run the server 48h paper trial without strategy churn.
- Keep aligning portfolio reports and runtime monitor reports around comparable metrics.
- Keep the runtime dashboard read-only and bound to `127.0.0.1` or a private interface.
- Do not implement live execution code until the Phase 6 interface spec is deliberately reviewed.
