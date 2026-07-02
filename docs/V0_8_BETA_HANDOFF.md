# QuantumRandy v0.8 Beta Handoff

Last updated: 2026-07-02

This handoff records the v0.8 beta state of the Randy quant stack after the first server-paper application layer and
Phase 4 portfolio research path. GitHub-facing notes are intentionally in English.

For a maturity-level view of what is beta-ready versus still research-only, see
`docs/STACK_MATURITY_STATUS.md`.

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

Use `docs/SERVER_48H_TRIAL_RUNBOOK.md` as the operator-facing Ubuntu/tmux checklist for the first full trial.

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

- Latest hard-gated LLM-only successful repeat: `reports/selector_rewrite_pipeline_llm_v082_evidence53_conflict_aware_memory_repeat`
- Latest failed repeat artifact: `reports/selector_rewrite_pipeline_llm_v082_evidence47_conflict_aware_memory_repeat`
  failed the LLM policy-evidence gate due to repeated SSL EOF transport errors and produced no candidates.
- Current aggregate summary: `reports/selector_pipeline_evidence_v082_summary`
- Aggregate runs: `50`
- LLM policy evidence runs: `46`
- LLM true-improvement evidence runs: `29`
- Coverage-only trap runs: `3`
- Highlighted candidate rows: `94`
- Negative candidate rows: `95`
- Negative candidate family rows: `19`
- Strongest repeated theme: positive smoothed volume participation, led by `zscore(ema(volume,48),120)`.
- Latest evidence53 note: `zscore(ema(volume,24),96)`, `zscore(ema(volume,48),120)`,
  `zscore(std(close,36),144)`, and `zscore(std(close,24),120)` were true-improved, while unnormalized
  `corr(sub(close,open),volume,72)` was not improved.
- Current memory posture: keep exact failed-formula blocking and sign-aware negative memory, but do not mechanically
  block entire volume-liquidity or range-volatility families.
- Boundary: these are research-only selector evidence artifacts, not runtime publish payloads or admission decisions.

## Next Best Steps

- If continuing the selector evidence campaign, run another hard-gated LLM-only conflict-aware repeat with the current
  selector evidence summary, then refresh the aggregate report and document only evidence/docs changes.
- Run one real Binance feeder one-shot against a local runtime and inspect the monitor report with baseline comparison.
- If that is clean, run the server 48h paper trial without strategy churn.
- Keep aligning portfolio reports and runtime monitor reports around comparable metrics.
- Keep the runtime dashboard read-only and bound to `127.0.0.1` or a private interface.
- Do not implement live execution code until the Phase 6 interface spec is deliberately reviewed.
