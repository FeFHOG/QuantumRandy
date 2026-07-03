# Research 1.0 Checkpoint Report

Date: 2026-07-03

Status: Research 1.0 is declared as a research-only checkpoint.

This checkpoint is not factor admission, runtime publishing, portfolio construction, RandyPortfolio implementation, or
live execution approval.

## Verdict

```text
research_1_0_checkpoint_declared_research_only
```

Research 1.0 is reached because the stack can export scoped research candidates, judge them reproducibly with
RandysLab, preserve failures as memory, and now has one BTCUSDT 4h candidate/variant that survived every current
scope-hard Research 1.0 robustness stress without ad hoc exceptions.

## Declared Candidate

| Candidate | Variant | Scope | Hard-Stress Survival | Mean Sharpe | Validation Sharpe | Blind Sharpe | Worst Max DD |
|---|---|---|---:|---:|---:|---:|---:|
| `qr_v09d_funding_return_long_001` | `thr_0p0_long_short_cap_0p5_none` | `BTCUSDT_4h` | `15/15` | 0.7844 | 0.4345 | 0.6993 | 0.3243 |

Candidate formula:

```text
zscore(corr(funding_rate,ret(close,42),120),72)
```

Manual research review accepts this as the first Research 1.0 scoped candidate because:

- the candidate came from the v0.9d research-only export with provenance, hypothesis, expected failure mode, and scope
  contract;
- BTCUSDT hard-gate scenarios all passed after RandysLab scope-aware robustness alignment;
- the `exclude_btcusdt` stress is correctly diagnostic-only for a `BTCUSDT_4h` candidate because it removes the
  declared target asset;
- ETH/SOL/BNB/AVAX rows remain diagnostic labels instead of being treated as universal-deployment requirements;
- failure memory records the other `59` failed candidate/variant rankings across `33` clusters.

This is still research evidence only. It does not authorize production use.

## Definition Audit

| Requirement from `V1_0_RESEARCH_READINESS_PLAN.md` | Status | Evidence |
|---|---|---|
| QuantumRandy exports research-only candidates with provenance, safety flags, formulas, hypotheses, and expected failure modes. | Passed | `reports/factor_candidate_exports/research_v0_9d_strict_candidate_discovery`; `docs/RESEARCH_V0_9D_STRICT_CANDIDATE_DISCOVERY_REPORT.md`. |
| RandysLab judges candidates across assets, windows, costs, funding, declared-scope rules, and robustness scenarios. | Passed | BTC/ETH/SOL/BNB/AVAX sensitivity and review artifacts plus `reports/factor_candidate_robustness/research_v0_9d_candidate_replication`. |
| At least one candidate family survives strict Research 1.0 gates within a declared scope. | Passed | `qr_v09d_funding_return_long_001::thr_0p0_long_short_cap_0p5_none` survived `15/15` BTCUSDT hard stresses. |
| Failed candidates produce reusable memory labels. | Passed | `reports/failure_memory/research_1_0_candidate_replication`, `59` failures, `33` clusters. |
| The loop moves beyond the blocked selector v0.8.2 family. | Passed | v0.9b/v0.9c/v0.9d generated new scoped hypotheses outside selector v0.8.2. |
| Reports distinguish all-asset robustness, single-asset usefulness, and portfolio-layer suitability. | Passed | Scope-aware replication report records BTC hard gates separately from out-of-scope diagnostics and explicitly excludes portfolio approval. |
| Documentation is compact enough for continuation. | Passed | This checkpoint report, prerequisite report, replication report, v0.9d report, and v1.1 plan are indexed in `docs/README.md`. |
| Research artifacts are not treated as runtime publishing, portfolio construction, live execution approval, or factor admission. | Passed | Boundary confirmations in this report and linked reports. |

## Gate Audit

| Gate | Status | Evidence |
|---|---|---|
| Candidate Export Gate | Passed | JSONL/CSV/manifest/Markdown export for v0.9d candidates; all records are `research_only` and `not_runtime_publish_payload`. |
| Strict Judge Gate | Passed | RandysLab declared-scope review used next-bar execution semantics, fees, slippage, funding, training/validation/blind windows, and explicit `intended_scope=BTCUSDT_4h`. |
| Robustness Gate | Passed | Candidate survived base, higher-cost, funding, combined harsh-cost, crash, validation-only, blind-only, and asset-exclusion hard stresses for the declared BTC scope. |
| Conservative Review Gate | Passed | Candidate was not promoted by mean Sharpe alone; validation, blind, drawdown, cost, funding, and positive-row gates were checked through RandysLab review and robustness ranking. |
| Regime Feature Gate | Passed as audit, not new feature admission | Crypto-native feature readiness found open interest, basis, liquidation, taker imbalance, and order-book depth unavailable locally; no new base fields were admitted. |

## Exit Checklist

| Checklist Item | Status | Evidence |
|---|---|---|
| Both repositories have a clean committed Research 1.0 checkpoint. | Passed | QuantumRandy contains this checkpoint report; RandysLab checkpoint source is `0d3f5ad Add scope-aware robustness ranking`. |
| RandysLab tests pass. | Passed | Full suite: `31 passed in 1.92s`. |
| QuantumRandy tests pass. | Passed | Full suite: `129 passed in 1.82s`. |
| At least one scoped factor family or bundle survives strict gates. | Passed | `qr_v09d_funding_return_long_001::thr_0p0_long_short_cap_0p5_none`, `15/15` hard stresses. |
| Failure-memory reports are updated. | Passed | `reports/failure_memory/research_1_0_candidate_replication`, `59/60` failed rows. |
| Handoff and project log are updated. | Passed | `docs/README.md`, `docs/PROJECT_LOG.md`, and `docs/V1_0_RESEARCH_READINESS_PLAN.md` point to this checkpoint. |
| Runtime and paper boundaries remain intact. | Passed | No runtime factor publishing, no active runtime strategy change, and no portfolio construction. |
| No live execution code or private-key path is introduced. | Passed | No live trading, no exchange keys, and no live execution adapters were added. |
| Next-step docs explain whether to pursue Research 1.1, RandyPortfolio planning, or paper observation. | Passed | `docs/superpowers/plans/2026-07-03-research-v1-1-independent-scoped-family-replication.md` is the next research plan. |

## Verification

Final verification commands for this checkpoint:

```text
QuantumRandy focused v0.9d/replication tests: 4 passed in 0.25s
QuantumRandy full suite: 129 passed in 1.82s
RandysLab focused factor-candidate/correlation tests: 21 passed in 0.41s
RandysLab full suite: 31 passed in 1.92s
```

## Next Step

The recommended next step is:

```text
Research v1.1: Independent Scoped Family Replication
```

The v1.1 plan is already written at
`docs/superpowers/plans/2026-07-03-research-v1-1-independent-scoped-family-replication.md`.

Research v1.1 should try to replicate a second independent non-funding scoped family. It should not implement
RandyPortfolio, run live trading, publish runtime factors, auto-admit factors, or add new formula base fields.

## Boundary Confirmation

- No RandyPortfolio implementation.
- No portfolio scheduler.
- No live trading.
- No exchange private keys.
- No runtime factor publishing.
- No automatic factor admission.
- No production runtime regime labels.
- No new formula base fields.
- No selector evidence61.
