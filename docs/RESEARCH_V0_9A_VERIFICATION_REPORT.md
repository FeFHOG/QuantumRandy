# Research v0.9a Verification Report

Date: 2026-07-03

Status: verified for scoped schema and strict-judge alignment.

This report closes the Research v0.9a checkpoint only. It does not start BTCUSDT scoped single-family research, does not
build a multi-factor bundle, does not implement RandyPortfolio, does not run live trading, and does not publish runtime
factors.

## Scope

Research v0.9a required three alignment checks:

1. QuantumRandy factor-candidate exports must carry `intended_scope`, `applicability_hypothesis`, and
   `out_of_scope_policy`.
2. RandysLab sensitivity and review artifacts must preserve those fields.
3. RandysLab declared-scope review and strict formula profile must match the current scoped research contract.

## Repository State Audited

QuantumRandy was audited on `main` with existing uncommitted v0.8-v0.9 work in docs, archive moves, the new
factor-candidate exporter, export docs, and exporter tests.

RandysLab-STRICT4H was audited on `main` with existing uncommitted strict-judge work in docs, factor-candidate judging,
sensitivity, review, robustness, diagnostics, scripts, and tests.

The parent `Quant` directory is not a git repository; the two child projects are independent repositories.

## Code Alignment

QuantumRandy:

- `quantumrandy/factor_candidate_export.py` writes the three scoped fields into every JSONL candidate record.
- The export manifest writes the same values under `scope_contract`.
- The CSV mirror preserves the same columns.
- The exporter marks artifacts as research-only, not runtime publish payloads, not auto-admission payloads, and not
  live-execution payloads.
- RandyPortfolio is represented only as an interface contract with `interface_only_not_implemented`.

RandysLab:

- `randyslab/formula_candidates.py` loads the QuantumRandy JSONL and carries the scoped fields in each strict judge
  result.
- `randyslab/factor_candidate_sensitivity.py` writes `intended_scope`, `applicability_hypothesis`, and
  `out_of_scope_policy` into `factor_candidate_sensitivity_detail.csv`.
- `randyslab/factor_candidate_review.py` now groups and writes all three fields into review rows, and the Markdown
  review report includes a Scope Contract table.
- Declared-scope review still enforces row count, Sharpe, positive-row share, validation/blind, and drawdown gates, but
  it does not require a single-asset scoped candidate to satisfy universal multi-asset positive-asset counts.

Formula profile:

- Supported functions: `abs`, `add`, `corr`, `delta`, `div`, `ema`, `log`, `max`, `min`, `mul`, `neg`, `ret`, `rsi`,
  `sign`, `sma`, `sqrt`, `std`, `sub`, `zscore`.
- Supported base fields: `close`, `funding_rate`, `high`, `low`, `open`, `volume`.
- New fields such as open interest, basis, liquidation imbalance, taker imbalance, or depth proxies remain out of scope
  until a separate data-readiness audit accepts them.

## Verification Artifacts

Generated research-only QuantumRandy export:

```text
QuantumRandy/reports/factor_candidate_exports/research_v0_9a_scope_alignment/
```

Export command:

```bash
python3 scripts/export_factor_candidates.py \
  --out reports/factor_candidate_exports/research_v0_9a_scope_alignment \
  --intended-scope BTCUSDT_4h \
  --applicability-hypothesis "BTCUSDT 4h scoped participation/regime research; non-BTC rows are diagnostic boundary evidence." \
  --out-of-scope-policy diagnostic_only
```

Observed export evidence:

- Candidate count: `7`.
- Manifest `scope_contract.intended_scope`: `BTCUSDT_4h`.
- Manifest `scope_contract.applicability_hypothesis`: `BTCUSDT 4h scoped participation/regime research; non-BTC rows
  are diagnostic boundary evidence.`
- Manifest `scope_contract.out_of_scope_policy`: `diagnostic_only`.
- All JSONL records preserve the same three values.
- Portfolio interface status: `interface_only_not_implemented`.

Generated RandysLab sensitivity artifact:

```text
RandysLab-STRICT4H/reports/factor_candidate_sensitivity/research_v0_9a_scope_alignment_btc_declared/
```

Sensitivity command:

```bash
python3 scripts/sweep_factor_candidates.py \
  --config configs/strict4h.yaml \
  --candidates ../QuantumRandy/reports/factor_candidate_exports/research_v0_9a_scope_alignment/factor_candidates.jsonl \
  --out reports/factor_candidate_sensitivity/research_v0_9a_scope_alignment_btc_declared \
  --asset BTCUSDT:data/BTCUSDT_4h.csv:data/BTCUSDT_funding.csv \
  --window all --window training --window validation --window long --window blind \
  --threshold 0.0 --threshold 0.5 --threshold 1.0
```

Observed sensitivity evidence:

- Run count: `15`.
- Candidate row count: `105`.
- Detail columns include `intended_scope`, `applicability_hypothesis`, and `out_of_scope_policy`.
- Unique detail values are `BTCUSDT_4h`, the declared hypothesis above, and `diagnostic_only`.
- Asset set is `BTCUSDT`; windows are `all`, `training`, `validation`, `long`, and `blind`.

Generated RandysLab declared-scope review artifact:

```text
RandysLab-STRICT4H/reports/factor_candidate_review/research_v0_9a_scope_alignment_btc_declared/
```

Review command:

```bash
python3 scripts/review_factor_candidate_sensitivity.py \
  --detail-csv reports/factor_candidate_sensitivity/research_v0_9a_scope_alignment_btc_declared/factor_candidate_sensitivity_detail.csv \
  --out reports/factor_candidate_review/research_v0_9a_scope_alignment_btc_declared \
  --scope-mode declared
```

Observed review evidence:

- Candidate count: `7`.
- Review rules `scope_mode`: `declared`.
- Review columns include `intended_scope`, `applicability_hypothesis`, `out_of_scope_policy`, `scope_mode`, and
  `scope_asset_count`.
- Unique review values are `BTCUSDT_4h`, the declared hypothesis above, `diagnostic_only`, `declared`, and
  `scope_asset_count=1`.
- The Markdown review report includes a Scope Contract table with those same values.
- All seven candidates are still `blocked_by_conservative_rules`; this is expected and remains research memory, not
  factor admission.

## Test Evidence

Commands run with the bundled Codex Python:

```bash
python3 -m pytest tests/test_factor_candidate_export.py -q
```

Result: `2 passed`.

```bash
python3 -m pytest tests/test_formula_candidates.py -q
```

Result: `12 passed`.

The focused RandysLab TDD check first failed because review rows did not expose `applicability_hypothesis`; it then
passed after the review code preserved the field and rendered it in the Markdown Scope Contract table.

Additional full-suite check:

```bash
python3 -m pytest -q
```

RandysLab result: `28 passed`.

QuantumRandy result: `105 passed, 8 failed`. The failures were outside this v0.9a scoped-schema path: runtime/backtest
tests requiring `scipy` for pandas Spearman correlation in the bundled Python environment, plus existing
portfolio/universe/selector-pipeline behavior expectations. The v0.9a export suite passed, and no v0.9a code path was
changed in those failing modules.

## Boundary Confirmation

- No RandyPortfolio implementation was added.
- No portfolio scheduler or regime allocator was created.
- No exchange private keys were used.
- No live order path was run.
- No QuantumRandy runtime factor was published.
- Generated reports are ignored research artifacts under `reports/`; tracked changes are code, tests, and docs only.

## Verdict

Research v0.9a scoped schema and strict-judge alignment is verified. The next research step may start BTCUSDT 4h scoped
single-family research, but only as a separate research checkpoint.
