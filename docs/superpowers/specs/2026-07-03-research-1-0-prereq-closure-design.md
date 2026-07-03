# Research 1.0 Prerequisite Closure Design

Date: 2026-07-03

## Status

Approved direction: linear prerequisite closure.

This design covers the remaining Research 1.0 prerequisites after Research v0.9c. It is research-only. It is not
RandyPortfolio implementation, not live trading, not runtime factor publishing, not factor admission, and not a
production regime-classification plan.

## Context

Research v0.9a, v0.9b, and v0.9c are complete and pushed. v0.9c ended with this conservative verdict:

```text
not_ready_for_research_1_0
```

That verdict is correct. v0.9c proved the scoped schema, strict declared-scope review path, bundle correlation review,
and failure-memory loop, but it did not produce a strict-surviving robust factor family. The next work should therefore
close Research 1.0 prerequisites and audit existing logic before attempting to claim Research 1.0 readiness.

Current repository evidence:

- `QuantumRandy` is aligned with `origin/main` at `ccc8e86 Record v0.9c verification results`.
- `RandysLab-STRICT4H` is aligned with `origin/main` at `ab9c67a Add factor candidate correlation review`.
- `RandysLab-STRICT4H` full suite passes under the Codex bundled Python runtime: `29 passed`.
- `QuantumRandy` full suite currently reports `110 passed, 8 failed` under the same runtime.
- The direct QuantumRandy failure root is `pandas.Series.corr(method="spearman")` importing SciPy when SciPy is not
  available in the runtime. Portfolio, universe, runtime, selector-pipeline, and smoke failures are downstream of that
  rank-correlation path or its swallowed exceptions.
- `QuantumRandy` declares `scipy>=1.12` in `pyproject.toml` and `requirements.txt`, so the failure is an environment
  reproducibility and robustness issue, not an absent declared dependency.
- Current RandysLab 4h data files expose `timestamp, open, high, low, close, volume`; funding is loaded separately.
  There are no local point-in-time open-interest, basis, liquidation, taker-imbalance, or order-book/depth feature
  files admitted to the formula profile.

## Goals

The work has four goals:

1. Make the existing Research 1.0 readiness verdict auditable: v0.9 is complete, Research 1.0 is not yet reached.
2. Remove or quarantine existing logic/environment failures that prevent a clean QuantumRandy research test baseline.
3. Add a public crypto-native feature-readiness audit for new base-field candidates before any formula-profile
   admission.
4. Produce a tracked Research 1.0 prerequisite verification report that states which gates are closed, which remain
   blocked, and what evidence proves each decision.

## Non-Goals

This work must not:

- implement RandyPortfolio;
- create a portfolio scheduler;
- run live trading;
- use or request exchange private keys;
- publish runtime factors;
- auto-admit factors;
- add production runtime regime labels;
- add formula base fields without a point-in-time readiness verdict;
- run selector evidence61;
- present a failed strict-review family as Research 1.0-ready.

## Approach Options Considered

### Option A: Engineering And Readiness Closure First

Fix the reproducible QuantumRandy test failure, add feature-readiness auditing, and write the prerequisite verification
report before new factor discovery.

This is the selected approach because it turns known unknowns into explicit gates and avoids confusing infrastructure
repair with alpha discovery.

### Option B: Aggressive Candidate Search Now

Start a new candidate-family gauntlet immediately, while also repairing the test and readiness gaps.

This may find useful diagnostic memory, but it risks burying basic reproducibility and data-admission questions under
another failed factor search. It is deferred until the prerequisite report is credible.

### Option C: Audit-Only Documentation

Document the blockers without changing code.

This would be fast but insufficient because the current QuantumRandy test failure is actionable and weakens every later
Research 1.0 claim.

## Design

### 1. Spearman Robustness And Test Hygiene

QuantumRandy should compute rank information coefficients without requiring pandas to import SciPy at runtime. The
project can continue declaring SciPy as a dependency, but the core research metric should be robust when the execution
environment contains pandas and numpy but not SciPy.

Design decision:

- Add a small internal Spearman helper that aligns the two series, drops missing values, ranks both sides with pandas
  average ranks, then computes ordinary Pearson correlation on the ranks.
- Use that helper in `quantumrandy/backtest.py` for `rank_ic`.
- Use the same helper in `quantumrandy/lab.py` for horizon decay Spearman metrics.
- Add focused tests that fail on the current implementation in the Codex bundled runtime and pass after the helper is
  wired in.

The helper should return `0.0` for too-few rows, constant ranked inputs, NaN correlation, or non-finite results. That
matches the existing conservative metric style and avoids leaking exceptions into universe and portfolio aggregation.

### 2. Public Crypto-Native Feature Readiness

Research 1.0 can introduce new base-field hypotheses only after a point-in-time data-readiness audit. The audit should
be read-only and diagnostic.

Feature candidates to audit:

- `open_interest`;
- `basis` or perpetual/spot spread;
- funding term-structure fields, if available;
- liquidation notional or liquidation imbalance;
- taker buy/sell imbalance;
- order-book depth or imbalance proxies.

Design decision:

- Add a QuantumRandy feature-readiness module that inspects configured data directories and known file patterns without
  downloading data.
- Emit structured rows with `feature`, `status`, `reason`, `observed_files`, `required_columns`, `observed_columns`,
  `point_in_time_ready`, and `formula_profile_action`.
- Use statuses:
  - `missing_source`: no local reproducible source file exists;
  - `present_schema_incomplete`: files exist but required columns are missing;
  - `diagnostic_only`: source appears usable for audit but is not admitted to formulas;
  - `eligible_for_candidate_design`: source passes the audit but still requires a separate formula-profile change.
- The current expected verdict is that no new base fields are admitted. If taker columns exist only in raw archive
  fetcher logic, they remain `missing_source` or `diagnostic_only` until local files and schema admission exist.

This audit must not mutate RandysLab formulas or `SUPPORTED_FIELDS`.

### 3. Declared Scope And Formula Profile Alignment

The prerequisite report should prove that QuantumRandy and RandysLab still agree on the scoped review contract:

- v0.9a scoped records carry `intended_scope`, `applicability_hypothesis`, and `out_of_scope_policy`;
- RandysLab sensitivity/review reads those fields into declared-scope review;
- RandysLab formula profile still admits only `open`, `high`, `low`, `close`, `volume`, and `funding_rate`;
- any new crypto-native feature remains outside formula execution until a separate readiness and profile-admission
  pass approves it.

This is a documentation and artifact-audit task unless the audit finds a contradiction.

### 4. Research 1.0 Prerequisite Verification Report

QuantumRandy will own the tracked report:

```text
docs/RESEARCH_1_0_PREREQUISITE_VERIFICATION_REPORT.md
```

The report must include:

- v0.9 completion status;
- current repository commits and cleanliness;
- QuantumRandy and RandysLab test evidence;
- Spearman robustness fix evidence;
- feature-readiness audit artifact paths and verdicts;
- declared-scope/schema alignment evidence;
- formula-profile status;
- strict-surviving factor-family status;
- Research 1.0 readiness verdict.

The expected verdict after this prerequisite closure is still:

```text
not_ready_for_research_1_0
```

The report may only change that verdict if a candidate family independently survives strict Research 1.0 review gates.
This design does not include a new candidate-family gauntlet, so it should not claim Research 1.0 readiness.

## Data Flow

1. Existing v0.9 reports and generated artifacts provide checkpoint history.
2. QuantumRandy tests exercise research metrics and aggregation paths.
3. The feature-readiness module scans local data roots and writes ignored diagnostic artifacts under `reports/`.
4. The tracked prerequisite report summarizes evidence and points to generated artifact paths.
5. RandysLab remains the strict judge and formula-profile authority for candidate execution.

## Error Handling

- Rank-correlation helpers return `0.0` for insufficient, constant, missing, NaN, or non-finite inputs.
- Feature-readiness audit rows explain missing paths and missing columns instead of raising for absent optional sources.
- Required baseline data files for existing OHLCV/funding checks should continue to fail loudly through existing
  data-readiness tests.
- The verification report must preserve failed or blocked verdicts instead of converting them into success wording.

## Testing

Focused tests:

- A QuantumRandy metric test proves `rank_ic` is computed in the bundled runtime without SciPy.
- A QuantumRandy lab metric test proves horizon-decay Spearman scoring does not import SciPy.
- A feature-readiness test proves missing optional crypto-native sources produce explicit diagnostic rows and no formula
  profile admission.
- Existing v0.9a/v0.9b/v0.9c tests continue to pass.

Verification commands:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest tests/test_smoke.py tests/test_runtime.py tests/test_portfolio.py tests/test_portfolio_universe.py tests/test_selector_pipeline.py tests/test_universe.py -q
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest -q
```

RandysLab verification:

```bash
/Users/rosebrain-2/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest -q
```

Repository verification:

```bash
git diff --check
```

## Completion Criteria

This prerequisite-closure pass is complete when:

- a written implementation plan exists under `docs/superpowers/plans/`;
- the QuantumRandy rank-correlation failure is fixed or explicitly quarantined with stronger evidence;
- QuantumRandy full tests pass under the Codex bundled Python runtime, or any remaining failures are proven unrelated to
  Research 1.0 prerequisites and documented as such;
- RandysLab full tests pass under the same runtime;
- public crypto-native feature readiness is audited without admitting new base fields;
- `docs/RESEARCH_1_0_PREREQUISITE_VERIFICATION_REPORT.md` is tracked and evidence-backed;
- docs index and project log are updated;
- both repositories are clean or have explicit commits pushed to GitHub;
- no non-goal boundary is violated.

## Spec Self-Review

- Placeholder scan: no placeholder work remains in this spec.
- Internal consistency: the selected approach closes engineering and readiness gates before candidate discovery.
- Scope check: this is one implementation plan spanning QuantumRandy code/docs and RandysLab verification only.
- Ambiguity check: Research 1.0 readiness cannot be claimed by this pass unless strict factor-family evidence appears
  independently; otherwise the verdict remains `not_ready_for_research_1_0`.
