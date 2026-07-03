# Research v0.9b Funding Pressure Report

Date: 2026-07-03

Status: complete; conservative verdict is `blocked_pending_new_hypotheses`.

This report closes the BTCUSDT 4h scoped single-family v0.9b pass for the funding-pressure family. It is a
research-only artifact. It is not factor admission, not runtime publishing, not portfolio construction, not
RandyPortfolio, and not live execution.

## Objective

Research v0.9b required a new scoped factor family outside selector v0.8.2, judged fully under RandysLab
declared-scope strict review, with a conservative verdict and reusable failure memory.

The approved family was:

```text
funding_pressure_crowding_mean_reversion
```

Declared scope:

```text
BTCUSDT_4h
```

Hypothesis:

```text
BTCUSDT 4h funding pressure can mark crowded perpetual positioning; extreme or smoothed funding states may
mean-revert after next-bar execution costs.
```

Expected failure mode:

```text
The family may fail in strong directional trends where high funding persists, or when funding pressure is too weak,
sparse, or delayed to offset fees, slippage, and funding costs.
```

## v0.9a Dependency

This pass uses the v0.9a scoped schema and RandysLab declared-scope review contract:

- QuantumRandy export records carry `intended_scope`, `applicability_hypothesis`, and `out_of_scope_policy`.
- RandysLab sensitivity and review artifacts preserve those fields.
- RandysLab review uses `scope_mode=declared`.
- The formulas stay inside the v0.9a profile: `close`, `funding_rate`, `ema`, `std`, `ret`, `div`, `corr`, `zscore`,
  and `neg`.

## Candidate Export

QuantumRandy export path:

```text
reports/factor_candidate_exports/research_v0_9b_funding_pressure/
```

Candidate count: `5`.

| Candidate | Formula | Required Features |
|---|---|---|
| `qr_v09b_funding_001` | `neg(zscore(funding_rate,72))` | `funding_rate` |
| `qr_v09b_funding_002` | `neg(zscore(ema(funding_rate,12),72))` | `funding_rate` |
| `qr_v09b_funding_003` | `neg(zscore(ema(funding_rate,24),96))` | `funding_rate` |
| `qr_v09b_funding_004` | `neg(zscore(div(funding_rate,std(close,48)),96))` | `close`, `funding_rate` |
| `qr_v09b_funding_005` | `neg(zscore(corr(funding_rate,ret(close,12),48),72))` | `close`, `funding_rate` |

These formulas are outside selector v0.8.2's primary volume-participation and realized-volatility formulas.

## RandysLab Strict Review

Sensitivity artifact:

```text
../RandysLab-STRICT4H/reports/factor_candidate_sensitivity/research_v0_9b_funding_pressure_btc_declared/
```

Sensitivity scope:

- Asset: `BTCUSDT`.
- Windows: `all`, `training`, `validation`, `long`, `blind`.
- Thresholds: `0.0`, `0.5`, `1.0`.
- Signal modes: `long_short`, `long_flat`, `short_flat`.
- Run count: `45`.
- Candidate row count: `225`.

Review artifact:

```text
../RandysLab-STRICT4H/reports/factor_candidate_review/research_v0_9b_funding_pressure_btc_declared/
```

Review rules:

- `scope_mode=declared`.
- `scope_asset_count=1`.
- Conservative gates still enforce completed rows, mean/median Sharpe, positive-row share, validation/blind windows,
  and drawdown.

Verdict counts:

```text
blocked_by_conservative_rules: 5
```

## Conservative Verdict Table

| Candidate | Conservative Verdict | Mean Sharpe | Median Sharpe | Worst Sharpe | Positive Rows | Mean Max DD | Worst Max DD | Validation Sharpe | Blind Sharpe | Failure Reasons |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `qr_v09b_funding_001` | `blocked_pending_new_hypotheses` | 0.4850 | 0.6329 | -0.8925 | 34/45 | 0.4555 | 0.7674 | 1.0462 | -0.0538 | `weak_blind_window/high_mean_drawdown` |
| `qr_v09b_funding_004` | `blocked_pending_new_hypotheses` | 0.4625 | 0.6411 | -0.9895 | 34/45 | 0.4516 | 0.7583 | 0.6859 | 0.2209 | `high_mean_drawdown` |
| `qr_v09b_funding_002` | `blocked_pending_new_hypotheses` | 0.4351 | 0.5292 | -1.3102 | 35/45 | 0.4600 | 0.7198 | 0.6540 | 0.0264 | `high_mean_drawdown` |
| `qr_v09b_funding_003` | `blocked_pending_new_hypotheses` | 0.1958 | 0.3135 | -1.5390 | 29/45 | 0.5041 | 0.8111 | 0.5862 | -0.0585 | `low_mean_sharpe/weak_blind_window/high_mean_drawdown/extreme_row_drawdown` |
| `qr_v09b_funding_005` | `blocked_pending_new_hypotheses` | 0.0252 | 0.0065 | -0.8005 | 23/45 | 0.5053 | 0.8648 | 0.2272 | -0.1427 | `low_mean_sharpe/low_median_sharpe/low_positive_row_share/weak_blind_window/high_mean_drawdown/extreme_row_drawdown` |

Interpretation:

- The raw funding and funding/vol-scaled formulas had useful average Sharpe, but still failed drawdown gates.
- Blind-window weakness appears in raw funding, slower smoothed funding, and funding-return-correlation variants.
- The family is worth preserving as research memory, but no candidate earns a scoped watchlist label in this pass.

## Failure Memory

QuantumRandy failure-memory artifact:

```text
reports/failure_memory/research_v0_9b_funding_pressure/
```

Failure rows: `5`.

Failure clusters: `3`.

Preserved labels:

- `drawdown_fragility`
- `high_mean_drawdown`
- `extreme_row_drawdown`
- `weak_blind_window`
- `weak_funding_pressure_edge`
- `trend_persistence_risk`
- `low_positive_row_share`
- `low_mean_sharpe`
- `low_median_sharpe`

The memory implication is conservative: funding pressure is not discarded as an idea, but the direct single-family
forms tested here are blocked pending new hypotheses or mitigation outside v0.9b's first-pass scope.

## Commands

QuantumRandy export:

```bash
python3 scripts/export_v0_9b_funding_pressure_candidates.py
```

RandysLab sensitivity:

```bash
python3 scripts/sweep_factor_candidates.py \
  --config configs/strict4h.yaml \
  --candidates ../QuantumRandy/reports/factor_candidate_exports/research_v0_9b_funding_pressure/factor_candidates.jsonl \
  --out reports/factor_candidate_sensitivity/research_v0_9b_funding_pressure_btc_declared \
  --asset BTCUSDT:data/BTCUSDT_4h.csv:data/BTCUSDT_funding.csv \
  --window all --window training --window validation --window long --window blind \
  --threshold 0.0 --threshold 0.5 --threshold 1.0 \
  --signal-mode long_short --signal-mode long_flat --signal-mode short_flat
```

RandysLab review:

```bash
python3 scripts/review_factor_candidate_sensitivity.py \
  --detail-csv reports/factor_candidate_sensitivity/research_v0_9b_funding_pressure_btc_declared/factor_candidate_sensitivity_detail.csv \
  --out reports/factor_candidate_review/research_v0_9b_funding_pressure_btc_declared \
  --scope-mode declared
```

QuantumRandy failure memory:

```bash
python3 scripts/build_v0_9b_failure_memory.py \
  --review-csv ../RandysLab-STRICT4H/reports/factor_candidate_review/research_v0_9b_funding_pressure_btc_declared/factor_candidate_review.csv \
  --source-review-dir ../RandysLab-STRICT4H/reports/factor_candidate_review/research_v0_9b_funding_pressure_btc_declared \
  --out reports/failure_memory/research_v0_9b_funding_pressure
```

## Verification

Structured artifact audit:

- Export manifest: `candidate_count=5`, `candidate_family=funding_pressure_crowding_mean_reversion`,
  `intended_scope=BTCUSDT_4h`, `out_of_scope_policy=diagnostic_only`.
- Export IDs: `qr_v09b_funding_001` through `qr_v09b_funding_005`.
- RandysLab sensitivity: `run_count=45`, `candidate_row_count=225`.
- RandysLab review: `candidate_count=5`, `scope_mode=declared`,
  `verdict_counts={"blocked_by_conservative_rules": 5}`, review scopes `BTCUSDT_4h`.
- Failure memory: `failure_count=5`, `cluster_count=3`,
  `conservative_verdict=blocked_pending_new_hypotheses`,
  `candidate_family=funding_pressure_crowding_mean_reversion`.

Focused and repository tests:

- QuantumRandy focused tests:
  `python3 -m pytest tests/test_factor_candidate_export.py tests/test_v0_9b_funding_pressure.py -q`
  returned `4 passed`.
- RandysLab formula-candidate tests:
  `python3 -m pytest tests/test_formula_candidates.py -q`
  returned `12 passed`.
- RandysLab full suite:
  `python3 -m pytest -q`
  returned `28 passed`.
- QuantumRandy full suite:
  `python3 -m pytest -q`
  returned `107 passed, 8 failed`. The failures are outside the v0.9b export, strict-review, report, and
  failure-memory path: portfolio selection/universe tests, runtime/smoke tests blocked by missing `scipy`, selector
  pipeline portfolio-spec handling, and universe evaluation summary expectations.
- `git diff --check` returned clean.

## Boundary Confirmation

- No RandyPortfolio implementation.
- No portfolio scheduler.
- No live trading.
- No exchange private keys.
- No runtime factor publishing.
- No automatic factor admission.
- No new formula base fields.
- No drawdown-stop or volatility-cap tuning in this first single-family pass.

## Final Verdict

Research v0.9b is complete for the BTCUSDT 4h funding-pressure single-family pass.

Conservative verdict:

```text
blocked_pending_new_hypotheses
```

Next research should either create a new family outside direct funding pressure or explicitly design a separate
mitigation pass. This v0.9b result should feed failure memory, not runtime or portfolio action.
