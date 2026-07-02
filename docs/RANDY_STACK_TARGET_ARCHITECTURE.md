# Randy Quant Stack Target Architecture

This document records the target project boundaries for the Randy quant stack. It is an interface-first architecture note,
not a migration plan. Do not split repositories, move modules, or rewrite large code paths solely because this document
exists.

The current algorithm evidence program continues inside QuantumRandy. Selector evidence, factor evidence, failure memory,
and research-only rewrite loops should keep accumulating unless a concrete experiment says otherwise.

## Target Projects

### QuantumRandy: Factor Factory

QuantumRandy owns research for individual alpha factors:

- mine formulaic alpha candidates;
- evaluate individual factor behavior across assets and windows;
- rewrite weak candidates with LLM and failure-memory context;
- produce research-only factor artifacts for downstream review;
- maintain selector evidence and factor evidence audit trails.

QuantumRandy does not own the final portfolio layer:

- no final multi-factor capital allocation;
- no production regime classifier;
- no dynamic portfolio risk engine;
- no position manager;
- no live execution code;
- no exchange private-key integration.

Current `portfolio`, `portfolio_universe`, `walk_forward`, and `portfolio_walk_forward` modules in QuantumRandy are
temporary research scaffolds. They are allowed to remain while they help judge factor quality and evidence stability, but
they should not become the permanent portfolio brain. In a future migration, some of this logic may move to
RandyPortfolio after explicit review.

### RandysLab: Strict Backtest Judge

RandysLab owns strict backtest judgment:

- T+1 or next-bar matching semantics;
- fees, funding, slippage, ledger construction, and metrics;
- failure reasons and audit reports;
- baseline exports used as control artifacts.

RandysLab baseline exports are control artifacts. They are not QuantumRandy runtime publish payloads, factor admission
decisions, or live strategy definitions.

RandysLab should stay skeptical and deterministic. It should judge submitted factors, signal bundles, or portfolio
bundles without becoming the LLM mining engine or the future portfolio commander.

### RandyPortfolio: Future All-Weather Commander

RandyPortfolio does not exist yet and should not be created as part of this boundary note.

Its future responsibility is the portfolio layer:

- consume QuantumRandy factor artifacts;
- combine multiple factors into signal bundles;
- detect regimes;
- manage dynamic risk;
- produce position-intent or portfolio signal bundles for RandysLab judgment;
- compare portfolio behavior against control baselines through RandysLab.

RandyPortfolio should eventually own the all-weather orchestration logic that QuantumRandy should not grow into by
accident.

## Boundary Rules

- Keep runtime, research, and publishing boundaries explicit.
- Keep new algorithm artifacts research-only unless a separate manual promotion process says otherwise.
- Do not add live execution code in QuantumRandy or RandysLab.
- Do not connect exchange private keys.
- Do not turn RandysLab baseline exports into runtime publish payloads.
- Do not block selector evidence accumulation because of future architecture planning.
- Prefer interface contracts and documentation before moving modules.
- Treat current QuantumRandy portfolio scaffolds as research aids, not as final ownership claims.

## Future Artifact Contracts

These contracts are draft interface shapes. They are intended to guide future producers and consumers, not to force an
immediate implementation.

### `quantumrandy_factor_candidate`

Producer: QuantumRandy.

Consumer: RandyPortfolio first; RandysLab may also consume it directly for strict single-factor judgment.

Purpose: describe one research-only alpha factor candidate with enough provenance for downstream testing.

Draft fields:

```json
{
  "artifact_type": "quantumrandy_factor_candidate",
  "schema_version": 1,
  "factor_id": "qr_example",
  "formula": "zscore(ema(volume,48),120)",
  "source": "selector_rewrite",
  "generation_source": "llm_rewrite",
  "research_only": true,
  "parent_factor_id": "qr_parent",
  "hypothesis": "Plain-English economic rationale.",
  "expected_failure_mode": "Plain-English failure mode.",
  "evidence": {
    "selector_run_id": "selector_rewrite_pipeline_llm_v082_evidence52_conflict_aware_memory_repeat",
    "validation_window": "validation",
    "assets": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "AVAXUSDT"],
    "pass_rate": 0.8,
    "mean_sharpe": 0.73775772,
    "failed_assets": ["BTCUSDT"]
  },
  "safety": {
    "not_runtime_publish_payload": true,
    "does_not_auto_admit_factor": true,
    "requires_manual_review_before_portfolio_use": true
  }
}
```

### `randyportfolio_signal_bundle`

Producer: future RandyPortfolio.

Consumer: RandysLab.

Purpose: describe a portfolio-level signal bundle or position-intent proposal for strict judgment.

Draft fields:

```json
{
  "artifact_type": "randyportfolio_signal_bundle",
  "schema_version": 1,
  "bundle_id": "rp_example",
  "research_only": true,
  "input_factors": [
    {
      "factor_id": "qr_example",
      "artifact_type": "quantumrandy_factor_candidate",
      "weight_policy": "regime_adjusted"
    }
  ],
  "regime_model": {
    "model_id": "regime_research_v1",
    "features": ["volatility_state", "liquidity_state"],
    "training_window": "research"
  },
  "risk_policy": {
    "max_gross_exposure": 1.0,
    "max_single_factor_weight": 0.35,
    "rebalance_rule": "next_bar"
  },
  "outputs": {
    "signal_frequency": "4h",
    "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "AVAXUSDT"]
  },
  "safety": {
    "not_live_execution_payload": true,
    "requires_randyslab_verdict": true,
    "requires_manual_review_before_runtime": true
  }
}
```

### `randyslab_verdict`

Producer: RandysLab.

Consumer: QuantumRandy for research feedback; RandyPortfolio for portfolio iteration.

Purpose: provide strict, reproducible judgment of a factor candidate or signal bundle.

Draft fields:

```json
{
  "artifact_type": "randyslab_verdict",
  "schema_version": 1,
  "verdict_id": "rl_verdict_example",
  "input_artifact_type": "quantumrandy_factor_candidate",
  "input_artifact_id": "qr_example",
  "backtest_protocol": {
    "bar_interval": "4h",
    "execution_timing": "next_bar",
    "fees_included": true,
    "funding_included": true,
    "slippage_included": true
  },
  "metrics": {
    "net_return": 0.0,
    "sharpe": 0.0,
    "max_drawdown": 0.0,
    "turnover": 0.0
  },
  "failure_reasons": [],
  "ledger_path": "reports/example/ledger.csv",
  "decision": "research_review_required",
  "safety": {
    "not_runtime_publish_payload": true,
    "not_live_execution_approval": true
  }
}
```

## Near-Term Working Agreement

For now, keep working in QuantumRandy on selector evidence and factor evidence. Use this document to prevent boundary
drift, not to interrupt the current evidence campaign. The next architecture step should be contract refinement or
documentation updates only, unless the user explicitly asks for a scoped implementation.
