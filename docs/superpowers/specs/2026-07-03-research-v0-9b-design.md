# Research v0.9b BTCUSDT Scoped Single-Family Design

Date: 2026-07-03

## Goal

Research v0.9b produces one new BTCUSDT 4h scoped single-family research pass outside selector v0.8.2, then judges it
with RandysLab declared-scope strict review and records a conservative verdict plus reusable failure memory.

This is research-only. It is not a runtime publish payload, factor admission, RandyPortfolio implementation,
portfolio scheduling plan, live trading run, or exchange-key workflow.

## Approved Family

Family name:

```text
funding_pressure_crowding_mean_reversion
```

Economic hypothesis:

```text
Extreme or smoothed BTCUSDT perpetual funding pressure can mark crowded positioning. On a 4h horizon, crowded funding
states may mean-revert or underperform after next-bar execution costs.
```

Expected failure mode:

```text
The family may fail in strong directional trends where high funding persists, or when funding pressure is too weak,
too sparse, or too delayed to offset fees, slippage, and funding costs.
```

Declared scope:

```text
BTCUSDT_4h
```

Out-of-scope policy:

```text
diagnostic_only
```

## Alternatives Considered

Recommended path: funding pressure and crowding mean-reversion. This is clearly outside selector v0.8.2 because it is a
funding-rate family rather than volume participation or realized-volatility state. It uses fields and operators already
accepted by v0.9a.

Alternative: crash-pressure family based on returns, high-low range, and realized volatility. This is useful, but it is
too close to the selector v0.8.2 crash-remediation memory and could blur the goal of producing a clean new family.

Alternative: liquidity participation imbalance based on volume and price-volume correlation. This is also plausible,
but it is adjacent to the selector v0.8.2 participation family and is therefore a weaker "outside selector v0.8.2"
candidate for v0.9b.

## Candidate Export Design

QuantumRandy will add a deterministic exporter for the approved family. It will not call LLMs, MCTS, runtime code, or
live data fetchers.

Initial candidates:

```text
neg(zscore(funding_rate,72))
neg(zscore(ema(funding_rate,12),72))
neg(zscore(ema(funding_rate,24),96))
neg(zscore(div(funding_rate,std(close,48)),96))
neg(zscore(corr(funding_rate,ret(close,12),48),72))
```

Each record will use the v0.9a factor-candidate contract:

- `artifact_type`: `quantumrandy_factor_candidate_export`
- `schema_version`: `1`
- `research_only`: `true`
- `not_runtime_publish_payload`: `true`
- `candidate_id`: stable deterministic id
- `formula`: candidate formula
- `formula_family`: `funding_pressure_crowding`
- `intended_scope`: `BTCUSDT_4h`
- `applicability_hypothesis`: approved family hypothesis
- `out_of_scope_policy`: `diagnostic_only`
- `hypothesis`: per-candidate rationale
- `expected_failure_mode`: family expected failure mode
- `required_features`: fields used by the formula
- `randyslab_eval_profile`: `strict4h_v1`
- `portfolio_interface_contract.status`: `interface_only_not_implemented`

The exporter will write:

```text
reports/factor_candidate_exports/research_v0_9b_funding_pressure/
  factor_candidates.jsonl
  factor_candidates.csv
  factor_candidate_export_manifest.json
  FACTOR_CANDIDATE_EXPORT.md
```

Reports are ignored research artifacts. Source code, tests, and docs are tracked.

## RandysLab Judgment Design

RandysLab will consume the QuantumRandy JSONL export through existing strict candidate tooling.

Sensitivity sweep:

- Asset: BTCUSDT only.
- Windows: `all`, `training`, `validation`, `long`, `blind`.
- Thresholds: `0.0`, `0.5`, `1.0`.
- Signal modes: `long_short`, `long_flat`, `short_flat`.
- Exposure caps: default `1.0` for the first single-family pass.
- Volatility caps and drawdown stops: none for the first pass, to avoid turning v0.9b into mitigation tuning.

Expected output path:

```text
RandysLab-STRICT4H/reports/factor_candidate_sensitivity/research_v0_9b_funding_pressure_btc_declared/
```

Conservative declared-scope review:

- Use `scope_mode=declared`.
- Preserve `intended_scope`, `applicability_hypothesis`, and `out_of_scope_policy`.
- Enforce conservative row count, Sharpe, validation, blind, positive-row, and drawdown gates.
- Do not require universal multi-asset positive-asset counts for the single-asset declared scope.

Expected output path:

```text
RandysLab-STRICT4H/reports/factor_candidate_review/research_v0_9b_funding_pressure_btc_declared/
```

## Conservative Verdict

The final v0.9b report will state a conservative label for every candidate:

- `scoped_watchlist` only if the declared-scope review returns `research_watchlist`;
- `blocked_pending_new_hypotheses` if conservative gates fail;
- `research_memory_only` for useful patterns that fail strict admission-style gates but should inform later research.

A `scoped_watchlist` label is still not factor admission and not runtime publishing.

## Failure Memory Design

QuantumRandy will produce a v0.9b failure-memory artifact from RandysLab review rows. The memory will map conservative
failures into reusable labels and context.

Expected output path:

```text
reports/failure_memory/research_v0_9b_funding_pressure/
  failure_memory.csv
  failure_clusters.csv
  failure_memory_manifest.json
  FAILURE_MEMORY_REPORT.md
```

Memory rows will include:

- candidate id and formula;
- family name;
- hypothesis and expected failure mode;
- intended scope;
- conservative verdict;
- RandysLab failure reasons;
- derived failure labels such as `weak_validation_window`, `weak_blind_window`, `low_positive_row_share`,
  `high_mean_drawdown`, `extreme_row_drawdown`, `weak_funding_pressure_edge`, and `trend_persistence_risk`;
- source artifact paths.

## Report Design

QuantumRandy will add a tracked v0.9b report:

```text
docs/RESEARCH_V0_9B_FUNDING_PRESSURE_REPORT.md
```

The report will include:

- v0.9a dependency confirmation;
- candidate export path and manifest summary;
- RandysLab sensitivity path and run counts;
- declared-scope review path and verdict counts;
- conservative verdict table;
- failure-memory path and labels;
- commands and tests run;
- boundary confirmation.

## Testing

QuantumRandy tests:

- exporter writes a research-only BTCUSDT scoped JSONL/CSV/manifest/report;
- candidates are outside selector v0.8.2 primary formulas;
- records preserve hypothesis, expected failure mode, scope contract, required features, and interface-only
  RandyPortfolio metadata;
- failure-memory builder converts RandysLab review rows into memory artifacts and labels.

RandysLab tests:

- existing factor-candidate tests continue to pass;
- declared-scope review preserves scope metadata and conservative failures.

Verification commands:

```bash
python3 -m pytest tests/test_factor_candidate_export.py tests/test_v0_9b_funding_pressure.py -q
python3 -m pytest tests/test_formula_candidates.py -q
```

RandysLab full suite will be run when practical. QuantumRandy full suite may still show pre-existing non-v0.9b failures
noted in the v0.9a report; any such failures must be documented instead of hidden.

## Boundaries

Do not:

- implement RandyPortfolio;
- build a portfolio scheduler;
- run live trading;
- use exchange private keys;
- publish runtime factors;
- auto-admit factors from a watchlist label;
- add new base formula fields beyond the v0.9a formula profile;
- optimize drawdown stops or volatility caps as part of this first v0.9b single-family pass.
