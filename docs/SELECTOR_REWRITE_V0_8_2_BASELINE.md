# Selector Rewrite v0.8.2 Local Baseline

Date: 2026-07-01

This note records the first v0.8.2 selector rewrite evidence run after the candidate-level review and highlight
artifacts were added. It is a research-only baseline. It is not an admission decision, runtime publish payload, or
strategy promotion recommendation.

## Command

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_local_v081_baseline \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke
```

The run used the local fallback rewrite path. No LLM API/proxy environment variables were present in this session, so
this should not be treated as LLM policy evidence.

Future pipeline manifests expose `llm_rewrite_accepted`, `fallback_rewrite_accepted`, and `is_llm_policy_evidence` so
this distinction is visible in machine-readable artifacts.

For future LLM-only evidence runs, prefer adding `--require-llm-evidence` to the pipeline command. The command will exit
non-zero if the run falls back to local rewrites without accepting any LLM rewrite candidates.

## Outputs

Local output directory:

```text
reports/selector_rewrite_pipeline_local_v081_baseline
```

Key artifacts:

- `SELECTOR_REWRITE_PIPELINE_REPORT.md`
- `review/SELECTOR_CANDIDATE_HIGHLIGHTS.md`
- `review/selector_pipeline_candidate_review.csv`
- `review/selector_pipeline_candidate_highlights.csv`
- `review/selector_pipeline_review_manifest.json`
- `portfolio_universe/PORTFOLIO_UNIVERSE_REPORT.md`

The `reports/` tree is ignored by git, so this note preserves the high-level result for handoff.

## Result Summary

- Rewrite targets: `3`
- Rewrite candidates: `6`
- Parent review verdicts: `not_improved:2|improved:1`
- Candidate verdicts: `not_improved:4|improved:1|coverage_only:1`
- Candidate highlights: `true_improved:1|coverage_only_trap:1`

True improved candidate:

| Parent | Candidate | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---:|---:|---|---|
| `qr_7a765d304b` | `qr_e033dc4b6b` | 0.20 | 0.09427579 | BTCUSDT,SOLUSDT,BNBUSDT,AVAXUSDT | `zscore(corr(funding_rate,ret(close,42),120),72)` |

Coverage-only trap:

| Parent | Candidate | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---:|---:|---|---|
| `qr_7a765d304b` | `qr_a0a0bc6baa` | 0.40 | -0.52984922 | BTCUSDT,ETHUSDT,BNBUSDT | `zscore(corr(funding_rate,ret(close,12),24),72)` |

## Interpretation

The new candidate-level audit loop is working as intended: it preserves the true improved candidate while preventing a
higher-coverage but materially lower-Sharpe rewrite from being misread as an improvement.

This baseline still does not establish a deployable edge. The improved candidate passed only one additional asset bucket
and still failed four assets. The useful conclusion is process-level: the selector rewrite evidence chain can now
separate profitability-aware improvement from coverage-only traps.

## Next Step

The next v0.8.2 experiment should be a small LLM rewrite run with working LLM network credentials, using the same
selector, asset configs, and failure-memory path. Compare its `SELECTOR_CANDIDATE_HIGHLIGHTS.md` against this local
baseline. A useful LLM run should increase true improved candidates without increasing coverage-only traps.

## LLM Evidence Attempt 1

Date: 2026-07-01

Command:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence1 \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --require-llm-evidence \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke
```

Result: the command exited with code `2`, as intended, because no LLM rewrite candidates were accepted.

Machine-readable rewrite summary:

- `use_llm_requested`: `true`
- `llm_rewrite_accepted`: `0`
- `fallback_rewrite_accepted`: `6`
- `is_llm_policy_evidence`: `false`
- `llm_error_count`: `3`

The LLM calls failed before candidate parsing because the session could not connect to the configured local proxy
`127.0.0.1:7897`. The recorded error begins with:

```text
LLM request failed after 3 attempts: ConnectionError: HTTPSConnectionPool(host='www.kuaiaiapi.com', port=443) ...
ProxyError('Unable to connect to proxy' ... [Errno 1] Operation not permitted)
```

An attempted non-sandbox rerun could not be approved because the approval service returned HTTP 503, so no successful
LLM policy evidence run was produced in this session.

The generated local fallback candidates and review mix matched the local baseline:

- Candidate verdicts: `not_improved:4|improved:1|coverage_only:1`
- Candidate highlights: `true_improved:1|coverage_only_trap:1`

This output directory must not be treated as LLM evidence. It is useful only as a failed LLM-attempt audit and another
local fallback comparison. Future reports and manifests now surface `llm_error_count` and `llm_error_summary` near the
top-level rewrite metadata so proxy/API failures are visible without opening `selector_rewrite_events.csv`.

## LLM Evidence Attempts 2 And 3

Date: 2026-07-01

After network/proxy access was available, the same research-only pipeline was rerun with
`--use-llm --require-llm-evidence`.

Attempt 2 output:

```text
reports/selector_rewrite_pipeline_llm_v082_evidence2
```

Attempt 2 produced real LLM policy evidence:

- `llm_rewrite_accepted`: `3`
- `fallback_rewrite_accepted`: `3`
- `is_llm_policy_evidence`: `true`
- `llm_error_count`: `0`
- Candidate verdicts: `not_improved:4|improved:2`
- Candidate highlights: `true_improved:2`
- Coverage-only traps: `0`

However, one highlighted improvement was a cross-target reuse: the candidate `qr_cb62796f3b` for parent
`qr_7a765d304b` was already another selector rewrite target formula. This is valid evidence that the LLM call worked,
but it should not be interpreted as a newly discovered rewrite improvement.

The rewrite generator was then tightened so known selector target formulas are passed as exact disallowed formulas for
every rewrite target. This prevents LLM candidates and local fill-ins from reusing another selector parent as a new
candidate. The manifest and event rows now record:

- `known_selector_formula_count`
- `known_selector_formulas`
- `disallowed_formula_count`

Attempt 3 output:

```text
reports/selector_rewrite_pipeline_llm_v082_evidence3
```

Attempt 3 is the cleaner LLM evidence run after the cross-target reuse guard:

- `known_selector_formula_count`: `3`
- `llm_rewrite_accepted`: `4`
- `fallback_rewrite_accepted`: `2`
- `is_llm_policy_evidence`: `true`
- `llm_error_count`: `0`
- Candidate verdicts: `not_improved:5|improved:1`
- Candidate highlights: `true_improved:1`
- Coverage-only traps: `0`

The only true improved candidate in attempt 3 is the same stable candidate found by the local baseline:

| Parent | Candidate | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---:|---:|---|---|
| `qr_7a765d304b` | `qr_e033dc4b6b` | 0.20 | 0.09427579 | BTCUSDT,SOLUSDT,BNBUSDT,AVAXUSDT | `zscore(corr(funding_rate,ret(close,42),120),72)` |

Interpretation: the LLM path is now verified end-to-end and no longer falls back silently. The stricter audit removes
the coverage-only trap seen in the local baseline and blocks cross-target formula reuse, but this single small run does
not yet establish a deployable alpha. It should be treated as selector rewrite evidence for the research loop only.

## Candidate Source Provenance Follow-Up

Date: 2026-07-01

The attempt 3 evidence is a mixed-source batch: accepted LLM rewrites can be followed by local fill-in candidates when
the requested candidate count is not fully satisfied by LLM output. To avoid over-attributing a candidate-level
improvement to the LLM just because the batch contains LLM candidates, rewrite artifacts now carry candidate-level
source provenance:

- `selector_rewrite_candidates.csv`: `rewrite_generation_source`
- `selector_pipeline_candidate_review.csv`: `rewrite_generation_source`
- `selector_pipeline_candidate_highlights.csv`: `rewrite_generation_source`
- `selector_rewrite_manifest.json`: `candidate_generation_source_counts`
- `selector_pipeline_review_manifest.json`: `candidate_generation_source_counts` and
  `candidate_highlight_generation_source_counts`
- Markdown review/highlight summaries: `Source` columns and source-count sections
- Research dashboard review payload: source fields for parent best-candidate, candidate rows, and highlight rows

This does not change evaluation metrics, admission policy, publishing, or runtime behavior. It only makes the audit
chain explicit enough to answer: "Did the highlighted improvement come from an LLM rewrite or from local fallback?"

## LLM Evidence Repeat 4

Date: 2026-07-02

Command:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence4 \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --require-llm-evidence \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke
```

Attempt 4 completed as a research-only mixed-source repeat:

- `known_selector_formula_count`: `3`
- `llm_rewrite_accepted`: `4`
- `fallback_rewrite_accepted`: `2`
- `is_llm_policy_evidence`: `true`
- `llm_error_count`: `0`
- Candidate generation source counts: `llm_rewrite:4|local_rewrite:2`
- Candidate verdicts: `not_improved:5|improved:1`
- Candidate highlights: `true_improved:1`
- Candidate highlight source counts: `local_rewrite:1`
- Coverage-only traps: `0`

The only true improved candidate was again:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_7a765d304b` | `qr_e033dc4b6b` | `local_rewrite` | 0.20 | 0.09427579 | BTCUSDT,SOLUSDT,BNBUSDT,AVAXUSDT | `zscore(corr(funding_rate,ret(close,42),120),72)` |

Interpretation: attempt 4 reconfirms that the LLM rewrite path is reachable and accepted four candidates without
errors, but the single highlighted improvement came from the local fallback fill candidate. This run should therefore
be treated as LLM-path evidence plus a local-improvement repeat, not as evidence that the LLM policy itself generated a
new true-improved selector rewrite. The candidate-level source provenance is doing its job: it prevents a mixed batch
from over-attributing local improvements to LLM rewrites.

## LLM-Only Evidence Repeat 5

Date: 2026-07-02

After attempt 4 showed that mixed-source batches still require careful attribution, the selector rewrite pipeline gained
an explicit research-only LLM-only mode. Passing `--llm-only` disables local fallback fills when LLM output produces
fewer candidates than requested. Default behavior is unchanged: local fallback remains enabled unless this flag is
provided.

Command:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence5_llm_only \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke
```

Attempt 5 completed as a research-only LLM-only evidence run:

- `allow_local_fallback`: `false`
- `known_selector_formula_count`: `3`
- `llm_rewrite_accepted`: `5`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- `llm_error_count`: `0`
- Candidate generation source counts: `llm_rewrite:5`
- Candidate verdicts: `not_improved:4|improved:1`
- Candidate highlights: `true_improved:1`
- Candidate highlight source counts: `llm_rewrite:1`
- Coverage-only traps: `0`

The true improved LLM candidate was:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_7a765d304b` | `qr_cd595899ee` | `llm_rewrite` | 0.20 | 0.04900644 | BTCUSDT,ETHUSDT,BNBUSDT,AVAXUSDT | `zscore(corr(sub(close,open),volume,36),96)` |

Interpretation: attempt 5 is the first clean run in this sequence where a true-improved selector rewrite highlight comes
from an LLM-generated candidate rather than local fallback. The improvement is still modest and fails four of five
assets, so it is not admission evidence and must not be published to runtime. The useful result is process-level:
LLM-only evidence can now be generated and audited without mixed-source attribution ambiguity.
