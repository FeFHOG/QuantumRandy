# Factor Candidate Exports

QuantumRandy factor-candidate exports are research-only handoff artifacts for strict external judging. They are not
runtime publish payloads, admission decisions, portfolio construction steps, or live execution plans.

## Selector v0.8.2 Milestone Export

The selector v0.8.2 milestone export is built from the frozen evidence60 aggregate summary:

```bash
python scripts/export_factor_candidates.py \
  --evidence-summary reports/selector_pipeline_evidence_v082_summary \
  --out reports/factor_candidate_exports/selector_v082_milestone_4_60 \
  --intended-scope multi_asset_crypto_4h_research \
  --out-of-scope-policy diagnostic_only
```

The default export writes:

- `factor_candidates.jsonl`: one research-only record per exported formula.
- `factor_candidates.csv`: a CSV mirror for review and downstream import.
- `factor_candidate_export_manifest.json`: safety metadata, source paths, and output paths.
- `FACTOR_CANDIDATE_EXPORT.md`: human-readable summary.

The initial export is intentionally narrow. It includes the repeated milestone winners:

- `zscore(ema(volume,48),120)`
- `zscore(ema(volume,24),96)`
- `zscore(ema(volume,24),120)`
- `zscore(ema(volume,36),144)`
- `zscore(std(close,48),120)`
- `zscore(std(close,48),144)`
- `zscore(std(close,36),144)`

Each record carries selector evidence counts, parent context, required raw features, conflict-aware family notes, and
the suggested strict RandysLab profile `strict4h_v1`.

## Scope Contract

Exports now carry an explicit research scope contract:

- `intended_scope`: the asset, asset set, horizon, or regime scope the candidate is meant to test.
- `applicability_hypothesis`: the plain-English reason this scope is economically plausible.
- `out_of_scope_policy`: usually `diagnostic_only`, meaning out-of-scope rows should produce labels and memory rather
  than automatic universal-deployment requirements.

QuantumRandy defines this contract because it owns factor-factory hypotheses. RandysLab consumes the fields during
strict judging and review, but should not invent the factor's intended scope.

## Future Portfolio Interface

Each export also declares a RandyPortfolio interface contract with status `interface_only_not_implemented`.
RandyPortfolio does not exist yet. The contract is present so future portfolio/risk orchestration can consume scoped
research artifacts without either QuantumRandy or RandysLab growing portfolio-allocation behavior by accident.

## Boundary

Exports must stay outside runtime publishing. A candidate remains only a formula candidate until RandysLab judges it
with next-bar/T+1 alignment, fees, funding, slippage, ledger accounting, metrics, and explicit failure reasons.
