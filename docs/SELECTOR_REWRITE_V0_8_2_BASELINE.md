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

## Required LLM True-Improvement Gate

Date: 2026-07-02

The selector rewrite pipeline now exposes a stricter research-only CLI gate:

```bash
--require-llm-true-improvement
```

This is intentionally stronger than `--require-llm-evidence`. `--require-llm-evidence` only verifies that at least one
LLM rewrite candidate was accepted. `--require-llm-true-improvement` exits non-zero unless the completed review stage
contains at least one `true_improved` highlight whose `rewrite_generation_source` is `llm_rewrite`.

The pipeline and review manifests now include:

- `llm_true_improved_count`
- `is_llm_true_improvement_evidence`

Attempt 6 used the new hard gate:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence6_llm_only_required \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke
```

Attempt 6 completed successfully:

- `allow_local_fallback`: `false`
- `llm_rewrite_accepted`: `4`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- `llm_true_improved_count`: `1`
- `is_llm_true_improvement_evidence`: `true`
- Candidate generation source counts: `llm_rewrite:4`
- Candidate verdicts: `not_improved:3|improved:1`
- Candidate highlights: `true_improved:1`
- Candidate highlight source counts: `llm_rewrite:1`
- Coverage-only traps: `0`

The true improved LLM candidate was:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_7a765d304b` | `qr_d907a41282` | `llm_rewrite` | 0.20 | 0.02518252 | BTCUSDT,SOLUSDT,BNBUSDT,AVAXUSDT | `neg(zscore(sma(funding_rate,48),120))` |

Interpretation: attempt 6 confirms the automated gate works end-to-end: a run can now require not just LLM participation
but an LLM-sourced true-improved highlight after multi-asset review. The resulting candidate still fails four assets and
does not qualify for admission or runtime publishing. It is process evidence for cleaner LLM rewrite audits, not a
strategy promotion claim.

## Multi-Run Evidence Summary

Date: 2026-07-02

Selector rewrite evidence can now be summarized across multiple pipeline output directories with:

```bash
.venv/bin/python scripts/summarize_selector_evidence.py \
  reports/selector_rewrite_pipeline_llm_v082_evidence4 \
  reports/selector_rewrite_pipeline_llm_v082_evidence5_llm_only \
  reports/selector_rewrite_pipeline_llm_v082_evidence6_llm_only_required \
  --out reports/selector_pipeline_evidence_v082_summary
```

This writes:

- `selector_pipeline_evidence_summary.csv`
- `selector_pipeline_candidate_evidence_summary.csv`
- `selector_pipeline_evidence_manifest.json`
- `SELECTOR_PIPELINE_EVIDENCE_SUMMARY.md`

The summary is research-only and does not admit, publish, or update runtime state. Its main purpose is attribution
discipline across repeated selector rewrite experiments.

For the v0.8.2 attempt 4/5/6 comparison, the summary reported:

- Runs: `3`
- LLM policy evidence runs: `3`
- LLM true-improvement evidence runs: `2`
- Runs with coverage-only traps: `0`
- Attempt 4: `is_llm_true_improvement_evidence=false` because its only true-improved highlight was `local_rewrite`
- Attempt 5: `is_llm_true_improvement_evidence=true` with candidate `qr_cd595899ee`
- Attempt 6: `is_llm_true_improvement_evidence=true` with candidate `qr_d907a41282`

The candidate aggregate table reported three distinct highlighted candidates:

- `qr_cd595899ee`: `llm_rewrite`, `llm_true_improved_count=1`
- `qr_d907a41282`: `llm_rewrite`, `llm_true_improved_count=1`
- `qr_e033dc4b6b`: `local_rewrite`, `llm_true_improved_count=0`

Interpretation: the aggregate artifact preserves the same source attribution rule as the single-run review. Mixed-source
runs can prove the LLM path works, but only highlights sourced from `llm_rewrite` count toward LLM true-improvement
evidence.

The read-only research review dashboard payload now also loads the latest `selector_pipeline_evidence*` summary and
surfaces run counts, LLM true-improvement evidence counts, coverage-only trap runs, source mixes, and top LLM-sourced
true-improved candidates. It also surfaces the highlighted-candidate aggregate so repeated or one-off LLM improvements
can be compared without opening raw CSV files. This is display-only review context and does not change admission,
publishing, or runtime state.

## LLM-Only Hard-Gate Repeats 7 And 8

Date: 2026-07-02

Two more LLM-only selector rewrite repeats were run with the same hard gate used in attempt 6:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence7_llm_only_required \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke
```

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence8_llm_only_required \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke
```

Both attempts completed the full research pipeline and produced valid LLM policy evidence, but both exited with code
`3` because the hard gate correctly rejected runs with no LLM-sourced true-improved highlight.

Attempt 7:

- `allow_local_fallback`: `false`
- `llm_rewrite_accepted`: `3`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- Candidate generation source counts: `llm_rewrite:3`
- Candidate verdicts: `not_improved:3`
- Candidate highlights: `0`
- `llm_true_improved_count`: `0`
- `is_llm_true_improvement_evidence`: `false`
- Coverage-only traps: `0`

Attempt 8:

- `allow_local_fallback`: `false`
- `llm_rewrite_accepted`: `3`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- Candidate generation source counts: `llm_rewrite:3`
- Candidate verdicts: `not_improved:3`
- Candidate highlights: `0`
- `llm_true_improved_count`: `0`
- `is_llm_true_improvement_evidence`: `false`
- Coverage-only traps: `0`

The useful result is negative evidence discipline: the LLM path accepted candidates and the universe/review stages
completed, but the stricter gate prevented those runs from being counted as LLM true-improvement evidence. Attempts 7
and 8 also show policy drift toward slow contrarian funding rewrites that were materially worse than their parents on
five-asset review. These runs remain research-only negative controls, not admission evidence and not runtime publish
material.

## Five-Run Evidence Summary Update

Date: 2026-07-02

The multi-run summary was refreshed with attempts 4 through 8:

```bash
.venv/bin/python scripts/summarize_selector_evidence.py \
  reports/selector_rewrite_pipeline_llm_v082_evidence4 \
  reports/selector_rewrite_pipeline_llm_v082_evidence5_llm_only \
  reports/selector_rewrite_pipeline_llm_v082_evidence6_llm_only_required \
  reports/selector_rewrite_pipeline_llm_v082_evidence7_llm_only_required \
  reports/selector_rewrite_pipeline_llm_v082_evidence8_llm_only_required \
  --out reports/selector_pipeline_evidence_v082_summary
```

The refreshed summary reported:

- Runs: `5`
- LLM policy evidence runs: `5`
- LLM true-improvement evidence runs: `2`
- Runs with coverage-only traps: `0`
- Highlighted candidate rows: `3`
- Distinct highlighted candidates: `3`

Run-level result:

| Run | LLM Evidence | LLM True Improvement | Candidate Sources | Highlight Sources | Best LLM True Improved |
|---|---:|---:|---|---|---|
| `selector_rewrite_pipeline_llm_v082_evidence5_llm_only` | `true` | `true` | `llm_rewrite:5` | `llm_rewrite:1` | `qr_cd595899ee` |
| `selector_rewrite_pipeline_llm_v082_evidence6_llm_only_required` | `true` | `true` | `llm_rewrite:4` | `llm_rewrite:1` | `qr_d907a41282` |
| `selector_rewrite_pipeline_llm_v082_evidence4` | `true` | `false` | `llm_rewrite:4|local_rewrite:2` | `local_rewrite:1` | `none` |
| `selector_rewrite_pipeline_llm_v082_evidence7_llm_only_required` | `true` | `false` | `llm_rewrite:3` | `none` | `none` |
| `selector_rewrite_pipeline_llm_v082_evidence8_llm_only_required` | `true` | `false` | `llm_rewrite:3` | `none` | `none` |

The highlighted candidate aggregate still contains only one occurrence each of the two LLM-sourced true improvements:

- `qr_cd595899ee`: `zscore(corr(sub(close,open),volume,36),96)`, pass-rate delta `+0.20`, mean-Sharpe delta
  `+0.04900644`.
- `qr_d907a41282`: `neg(zscore(sma(funding_rate,48),120))`, pass-rate delta `+0.20`, mean-Sharpe delta `+0.02518252`.

Interpretation: the LLM-only audit path is now repeatable, but the evidence is not stable enough to claim a reliable
selector rewrite improvement policy. The two positive LLM true-improved candidates did not repeat, attempts 7 and 8
were cleanly rejected by the hard gate, and every highlighted candidate still failed four of five assets. The next useful
algorithm step is not runtime promotion; it is to revise selector rewrite prompting or target selection so LLM repeats
are less likely to collapse into weak slow-funding variants and more likely to produce repeatable, profitability-aware
cross-asset improvements.

## Policy-Guarded LLM-Only Repeat 9

Date: 2026-07-02

After attempts 7 and 8 drifted toward weak slow-funding variants, the selector rewrite generation policy was tightened
without touching admission, publishing, or runtime behavior:

- selector rewrite artifacts now classify each parent formula family;
- non-funding parents default to `max_pure_funding_candidates=0`;
- pure funding parents still allow at most one pure funding-rate-only rewrite;
- the same family limit is included in the LLM rewrite prompt and enforced by the LLM candidate parser;
- prompt examples were corrected so non-funding family examples obey the current DSL depth limit.

The first policy-guarded attempt exposed an invalid prompt-example issue: the LLM copied range-normalization formulas
such as `zscore(div(sub(high,low),close),96)`, which exceed the current `max_depth=4` shape rule. That run produced no
accepted LLM candidates and was treated as a prompt-shape negative control rather than selector evidence. The prompt was
then corrected to use valid examples such as `zscore(sub(high,low),96)` and `zscore(std(close,24),96)`.

The corrected run used:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence9_policy_guarded_shape_fixed \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke
```

Attempt 9 completed the full research pipeline and produced valid LLM policy evidence, but exited with code `3`
because the hard gate correctly rejected a run with no LLM-sourced true-improved highlight:

- `allow_local_fallback`: `false`
- `llm_rewrite_accepted`: `3`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- Candidate generation source counts: `llm_rewrite:3`
- Candidate verdicts: `not_improved:3`
- Candidate highlights: `0`
- `llm_true_improved_count`: `0`
- `is_llm_true_improvement_evidence`: `false`
- Coverage-only traps: `0`

The policy guard changed the failure mode in a useful way: the LLM no longer collapsed into pure funding-only rewrites
for non-funding parents. Instead, the accepted candidates shifted toward realized-volatility stress proxies such as
`neg(zscore(std(close,24),96))`, `neg(zscore(std(close,12),120))`, and `neg(zscore(std(close,24),120))`. These were
cleanly evaluated but materially underperformed their parents on five-asset review, so the hard gate still rejected the
run.

The multi-run summary was refreshed with attempts 4 through 9:

- Runs: `6`
- LLM policy evidence runs: `6`
- LLM true-improvement evidence runs: `2`
- Runs with coverage-only traps: `0`
- Highlighted candidate rows: `3`
- Distinct highlighted candidates: `3`

Interpretation: the policy guard improved attribution and candidate-family discipline, but it did not improve selector
rewrite quality yet. The next useful algorithm step is to make the rewrite objective more asset-specific or to add
negative evidence memory for failed realized-volatility rewrites, not to relax the hard gate or publish any candidate.

## Negative Selector Evidence Memory And Repeats 10-11

Date: 2026-07-02

The multi-run evidence summary now also writes a negative candidate-family aggregate:

```text
reports/selector_pipeline_evidence_v082_summary/selector_pipeline_negative_candidate_summary.csv
```

This table is built from candidate-level review rows, not only highlights. It summarizes LLM-sourced `not_improved` and
`coverage_only` rewrite families by parent family and candidate family, including negative counts, average deltas, worst
mean-Sharpe delta, example formulas, failed assets, and source run ids. It is research-only prompt memory; it does not
admit, publish, or update runtime state.

The selector rewrite CLI and pipeline now accept:

```bash
--selector-evidence-path reports/selector_pipeline_evidence_v082_summary
```

When provided, the LLM rewrite prompt receives negative selector rewrite memories. The parser also treats exact
negative example formulas as disallowed formulas, so a previously failed candidate can no longer be accepted again just
because the prompt politely asked the LLM not to repeat it. Rewrite event rows record:

- `selector_negative_examples`
- `selector_negative_families`
- `selector_negative_disallowed_formulas`

Attempt 10 used negative selector evidence as prompt context, but exact negative formulas were not yet parser-disallowed.
It completed review and produced valid LLM policy evidence, but the hard gate rejected it:

- `llm_rewrite_accepted`: `3`
- `fallback_rewrite_accepted`: `0`
- Candidate verdicts: `not_improved:3`
- `llm_true_improved_count`: `0`
- One accepted candidate repeated a known negative realized-volatility formula:
  `neg(zscore(std(close,24),96))`

The parser was then tightened so exact negative example formulas are added to `disallowed_formulas`.

Attempt 11 used the same negative selector evidence path after exact negative disallow was added:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence11_negative_memory_disallow \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke \
  --selector-evidence-path reports/selector_pipeline_evidence_v082_summary
```

Attempt 11 completed successfully and passed the hard gate:

- `allow_local_fallback`: `false`
- `llm_rewrite_accepted`: `2`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- Candidate generation source counts: `llm_rewrite:2`
- Candidate verdicts: `improved:1|not_improved:1`
- Candidate highlights: `true_improved:1`
- Candidate highlight source counts: `llm_rewrite:1`
- `llm_true_improved_count`: `1`
- `is_llm_true_improvement_evidence`: `true`
- Coverage-only traps: `0`

The true-improved LLM candidate was a repeat of the strongest prior LLM-sourced candidate:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_7a765d304b` | `qr_cd595899ee` | `llm_rewrite` | 0.20 | 0.04900644 | BTCUSDT,ETHUSDT,BNBUSDT,AVAXUSDT | `zscore(corr(sub(close,open),volume,36),96)` |

The refreshed attempts 4-11 summary reported:

- Runs: `8`
- LLM policy evidence runs: `8`
- LLM true-improvement evidence runs: `3`
- Runs with coverage-only traps: `0`
- Highlighted candidate rows: `4`
- Distinct highlighted candidates: `3`
- Negative candidate rows: `24`
- Negative candidate family rows: `10`

The highlighted-candidate aggregate now shows:

- `qr_cd595899ee`: `llm_rewrite`, `llm_true_improved_count=2`, runs
  `selector_rewrite_pipeline_llm_v082_evidence5_llm_only` and
  `selector_rewrite_pipeline_llm_v082_evidence11_negative_memory_disallow`.
- `qr_d907a41282`: `llm_rewrite`, `llm_true_improved_count=1`.
- `qr_e033dc4b6b`: `local_rewrite`, `llm_true_improved_count=0`.

Interpretation: negative selector evidence memory improved the audit loop in two ways. First, failed LLM families are
now summarized and reusable as prompt context instead of being trapped only in individual ignored `reports/` directories.
Second, exact negative repeats are blocked mechanically. Attempt 11 is the first sign of repeated LLM-sourced
true-improvement evidence for the same candidate, but it is still not admission evidence: the candidate still failed
four of five assets and remains a research-only selector rewrite artifact.

## Negative-Memory Repeats 12-13

Date: 2026-07-02

Attempt 12 repeated the negative-memory hard-gated command after attempt 11:

- `llm_rewrite_accepted`: `2`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- Candidate verdicts: `not_improved:1|improved:1`
- Candidate highlights: `true_improved:1`
- Candidate highlight source counts: `llm_rewrite:1`
- `llm_true_improved_count`: `1`
- Coverage-only traps: `0`

The true-improved LLM candidate was again `qr_cd595899ee`:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_7a765d304b` | `qr_cd595899ee` | `llm_rewrite` | 0.20 | 0.04900644 | BTCUSDT,ETHUSDT,BNBUSDT,AVAXUSDT | `zscore(corr(sub(close,open),volume,36),96)` |

Attempt 12 also showed that the initial exact-negative disallow list was too short: it mechanically disallowed only the
top negative examples, so a lower-ranked negative formula such as `neg(zscore(std(close,24),96))` could still be
accepted again. The negative selector evidence loader was therefore split into two concepts:

- a small prompt-facing example/family set, to keep prompts compact;
- a wider exact disallow formula set, defaulting to up to `20` negative formulas.

Attempt 13 used this wider exact-negative disallow list:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence13_negative_memory_wide_disallow \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke \
  --selector-evidence-path reports/selector_pipeline_evidence_v082_summary
```

Attempt 13 also passed the hard gate:

- `llm_rewrite_accepted`: `4`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- Candidate verdicts: `not_improved:3|improved:1`
- Candidate highlights: `true_improved:1`
- Candidate highlight source counts: `llm_rewrite:1`
- `llm_true_improved_count`: `1`
- Coverage-only traps: `0`
- Rewrite events recorded `selector_negative_disallowed_formulas=10` in this run.

The true-improved candidate was a nearby price-volume variant with stronger review deltas than the previous repeats:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_7a765d304b` | `qr_655fb2a53d` | `llm_rewrite` | 0.40 | 0.16858771 | BTCUSDT,ETHUSDT,BNBUSDT | `zscore(corr(sub(close,open),volume,36),84)` |

The refreshed attempts 4-13 summary reported:

- Runs: `10`
- LLM policy evidence runs: `10`
- LLM true-improvement evidence runs: `5`
- Runs with coverage-only traps: `0`
- Highlighted candidate rows: `6`
- Distinct highlighted candidates: `4`
- Negative candidate rows: `28`
- Negative candidate family rows: `12`

The highlighted-candidate aggregate now shows:

- `qr_cd595899ee`: `llm_rewrite`, `llm_true_improved_count=3`.
- `qr_655fb2a53d`: `llm_rewrite`, `llm_true_improved_count=1`, best pass-rate delta `+0.40`, mean-Sharpe delta
  `+0.16858771`.
- `qr_d907a41282`: `llm_rewrite`, `llm_true_improved_count=1`.
- `qr_e033dc4b6b`: `local_rewrite`, `llm_true_improved_count=0`.

Interpretation: the negative-memory loop is starting to produce repeatable LLM-sourced improvements in the same
price-volume family, and attempt 13 improved both pass-rate and mean-Sharpe deltas more than earlier repeats. This is
still research-only selector evidence, not admission or runtime publish evidence. The next useful step is to evaluate
whether the stable price-volume variants remain useful under broader selector targets, additional hard-gated repeats, or
a stricter parent selection set; no automatic promotion should be made from these artifacts.

## Negative-Memory Repeat 14

Date: 2026-07-02

Attempt 14 repeated the hard-gated negative-memory command after the wider exact-negative disallow change:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence14_negative_memory_repeat \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke \
  --selector-evidence-path reports/selector_pipeline_evidence_v082_summary
```

The command exited with code `3`, as intended, because the run did not produce LLM true-improvement evidence:

- `llm_rewrite_accepted`: `2`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- Candidate verdicts: `mixed:1|coverage_only:1`
- Candidate highlights: `sharpe_improved_no_pass_lift:1|coverage_only_trap:1`
- Candidate highlight source counts: `llm_rewrite:2`
- `llm_true_improved_count`: `0`
- Coverage-only traps: `1`
- Rewrite events recorded `selector_negative_disallowed_formulas=12` in this run.

The highlight queues were:

| Highlight Type | Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---|---:|---:|---|---|
| `sharpe_improved_no_pass_lift` | `qr_1c002c4c13` | `qr_cd595899ee` | `llm_rewrite` | 0.00 | 0.12454568 | BTCUSDT,ETHUSDT,BNBUSDT,AVAXUSDT | `zscore(corr(sub(close,open),volume,36),96)` |
| `coverage_only_trap` | `qr_7a765d304b` | `qr_9a30f357c2` | `llm_rewrite` | 0.20 | -0.30235366 | BTCUSDT,ETHUSDT,SOLUSDT,AVAXUSDT | `zscore(corr(sub(high,low),volume,48),96)` |

The refreshed attempts 4-14 summary reported:

- Runs: `11`
- LLM policy evidence runs: `11`
- LLM true-improvement evidence runs: `5`
- Runs with coverage-only traps: `1`
- Highlighted candidate rows: `8`
- Distinct highlighted candidates: `6`
- Negative candidate rows: `29`
- Negative candidate family rows: `12`

Interpretation: attempt 14 is useful negative evidence, not a new positive result. It confirms that the hard gate
distinguishes repeat Sharpe-only improvements and coverage-only traps from true improvements. The exact negative
disallow also remained active; the accepted candidates were not repeats of the mechanically disallowed negative
formulas, while two rejected LLM formulas failed the formula-depth guard. The next selector-layer step should mine this
new negative evidence into prompt memory and keep pressure on price-volume variants that improve both pass-rate and
mean Sharpe, without relaxing the true-improvement gate.

## Negative-Memory Repeat 15

Date: 2026-07-02

Attempt 15 reused the refreshed selector evidence summary after attempt 14:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence15_negative_memory_after_trap \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke \
  --selector-evidence-path reports/selector_pipeline_evidence_v082_summary
```

The command exited with code `3`, again as intended, because there were no LLM true-improved candidates:

- `llm_rewrite_accepted`: `1`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- `llm_error_count`: `2`
- Candidate verdicts: `not_improved:1`
- Candidate highlights: `0`
- `llm_true_improved_count`: `0`
- Coverage-only traps: `0`
- Rewrite events again recorded `selector_negative_disallowed_formulas=12`.

The only reviewed candidate was:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_7a765d304b` | `qr_a3c34a6150` | `llm_rewrite` | 0.00 | -0.65077117 | BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,AVAXUSDT | `neg(corr(funding_rate,sub(close,open),72))` |

Two target attempts produced only rejected LLM formulas before review. The rejected formulas failed the formula-depth
guard or DSL validation (`ret(close,1)` is below the allowed return window).

The refreshed attempts 4-15 summary reported:

- Runs: `12`
- LLM policy evidence runs: `12`
- LLM true-improvement evidence runs: `5`
- Runs with coverage-only traps: `1`
- Highlighted candidate rows: `8`
- Distinct highlighted candidates: `6`
- Negative candidate rows: `30`
- Negative candidate family rows: `12`

Interpretation: attempt 15 adds a clean negative-control run after the coverage-only trap. It produced no highlight
rows and added another `price` parent to `funding_interaction` negative family example, reinforcing that the selector
loop should not drift from price parents into funding interactions unless both cross-asset pass rate and mean Sharpe
improve. The hard gate and DSL validator both behaved as intended.

## Negative-Memory Repeat 16

Date: 2026-07-02

Attempt 16 repeated the same hard-gated negative-memory command:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence16_negative_memory_repeat \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke \
  --selector-evidence-path reports/selector_pipeline_evidence_v082_summary
```

The command exited with code `3`, as intended, because the completed review produced no LLM true-improved candidates:

- `llm_rewrite_accepted`: `4`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- `llm_error_count`: `1`
- Candidate verdicts: `not_improved:4`
- Candidate highlights: `0`
- `llm_true_improved_count`: `0`
- Coverage-only traps: `0`
- Rewrite events again recorded `selector_negative_disallowed_formulas=12`.

The rejected LLM formulas for the price parent are also useful audit evidence: one copied an exact disallowed failed
formula (`zscore(corr(sub(close,open),volume,48),72)`), and one failed the formula-depth guard.

Reviewed candidates:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_1c002c4c13` | `qr_f601c23c4e` | `llm_rewrite` | -0.20 | -0.37907329 | BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,AVAXUSDT | `neg(corr(funding_rate,sub(close,open),96))` |
| `qr_1c002c4c13` | `qr_eb18ffbb62` | `llm_rewrite` | -0.20 | -1.47893646 | BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,AVAXUSDT | `neg(zscore(delta(volume,24),120))` |
| `qr_cb62796f3b` | `qr_c4479c5050` | `llm_rewrite` | -0.20 | -0.69316767 | BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,AVAXUSDT | `neg(corr(funding_rate,volume,96))` |
| `qr_cb62796f3b` | `qr_039d2acc19` | `llm_rewrite` | -0.20 | -1.86926194 | BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,AVAXUSDT | `neg(zscore(delta(volume,12),96))` |

The refreshed attempts 4-16 summary reported:

- Runs: `13`
- LLM policy evidence runs: `13`
- LLM true-improvement evidence runs: `5`
- Runs with coverage-only traps: `1`
- Highlighted candidate rows: `8`
- Distinct highlighted candidates: `6`
- Negative candidate rows: `34`
- Negative candidate family rows: `13`

Interpretation: attempt 16 is a stronger negative-memory repeat than attempt 15 because it accepted four LLM candidates
and all four failed both pass-rate and mean-Sharpe deltas. It reinforces three prompt-memory lessons: pure-funding
parents should not drift into funding-price or volume-shock reversals, volume-liquidity parents should not drift into
funding-volume interactions, and exact disallowed failed formulas must remain mechanically blocked. This is still
research-only selector evidence and should not affect runtime or admission policy.

## Negative Family-Pair Blocking And Attempt 17

Date: 2026-07-02

Attempts 14-16 showed that prompt-only negative family memory was not enough: the LLM still drifted from specific
parent families into candidate families that had repeatedly lowered mean Sharpe. The selector negative evidence loader
therefore now exposes a mechanical family-pair block list in addition to prompt examples and exact formula disallows.

New prompt config defaults:

- `selector_negative_block_families`: `20`
- `selector_negative_block_min_count`: `3`

Only parent/candidate family pairs with at least `selector_negative_block_min_count` negative rows and negative average
mean-Sharpe delta are blocked. This keeps the rule conservative: isolated failed families remain prompt guidance, while
repeatedly bad family transitions are rejected by the LLM rewrite parser. The rewrite event CSV now records
`selector_negative_blocked_family_pairs`.

Attempt 17 then ran the same hard-gated command with the new parser rule:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence17_family_block \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke \
  --selector-evidence-path reports/selector_pipeline_evidence_v082_summary
```

The command exited with code `3`, as intended, because there were no LLM true-improved candidates:

- `llm_rewrite_accepted`: `4`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- Candidate verdicts: `not_improved:3|mixed:1`
- Candidate highlights: `sharpe_improved_no_pass_lift:1`
- `llm_true_improved_count`: `0`
- Coverage-only traps: `0`
- Rewrite events recorded `selector_negative_blocked_family_pairs=6` and
  `selector_negative_disallowed_formulas=13`.

The only highlight was again a Sharpe-only/no-pass-lift repeat:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_1c002c4c13` | `qr_cd595899ee` | `llm_rewrite` | 0.00 | 0.12454568 | BTCUSDT,ETHUSDT,BNBUSDT,AVAXUSDT | `zscore(corr(sub(close,open),volume,36),96)` |

The refreshed attempts 4-17 summary reported:

- Runs: `14`
- LLM policy evidence runs: `14`
- LLM true-improvement evidence runs: `5`
- Runs with coverage-only traps: `1`
- Highlighted candidate rows: `9`
- Distinct highlighted candidates: `6`
- Negative candidate rows: `37`
- Negative candidate family rows: `13`

Interpretation: family-pair blocking is now active and audit-visible, but attempt 17 is not positive evidence. It
removed neither the need for the true-improvement hard gate nor the need for broader validation of price-volume
variants. The useful outcome is process-level: repeated bad family transitions can now be converted from prompt hints
into deterministic research-only parser rejections while exact formula blocking remains separate.

## Rejection-Audit Fields And Attempt 18

Date: 2026-07-02

After attempt 17, selector rewrite event rows were still too compact to audit validator behavior. They showed that
negative family-pair blocking was loaded, but not which candidate formulas were rejected or why. The rewrite event CSV
therefore now records:

- `rejected_count`
- `rejected_reason_mix`
- `rejected_formula_examples`

These are audit-only fields. They do not affect generation, evaluation, admission, publishing, or runtime behavior.

Attempt 18 then ran the same hard-gated command:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence18_rejection_audit \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke \
  --selector-evidence-path reports/selector_pipeline_evidence_v082_summary
```

The command exited with code `3`, as intended, because there were no LLM true-improved candidates:

- `llm_rewrite_accepted`: `3`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- Candidate verdicts: `not_improved:3`
- Candidate highlights: `0`
- `llm_true_improved_count`: `0`
- Coverage-only traps: `0`
- Rewrite events recorded `selector_negative_blocked_family_pairs=7` and
  `selector_negative_disallowed_formulas=13`.

The new rejection-audit columns captured three validator rejections before review:

| Parent | Rejected Reason Mix | Example |
|---|---|---|
| `qr_cb62796f3b` | `Operator ret requires an integer window >= 2:1` | `neg(corr(abs(ret(close,1)),volume,72))` |
| `qr_1c002c4c13` | `Formula depth 5 exceeds max_depth=4: neg(zscore(corr(sub(close,open),volume,48),72)):1` | `neg(zscore(corr(sub(close,open),volume,48),72))` |
| `qr_7a765d304b` | `copies disallowed failed formula:1` | `zscore(corr(sub(close,open),volume,48),72)` |

The refreshed attempts 4-18 summary reported:

- Runs: `15`
- LLM policy evidence runs: `15`
- LLM true-improvement evidence runs: `5`
- Runs with coverage-only traps: `1`
- Highlighted candidate rows: `9`
- Distinct highlighted candidates: `6`
- Negative candidate rows: `40`
- Negative candidate family rows: `14`

Interpretation: attempt 18 is another negative-control run, but the important improvement is observability. The selector
rewrite audit trail can now distinguish DSL signature errors, formula-depth errors, exact negative-memory repeats, and
future family-pair blocks directly from `selector_rewrite_events.csv`.

## Rejection-Audit Repeat 19

Date: 2026-07-02

Attempt 19 repeated the hard-gated command after refreshing selector memory with attempt 18:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence19_rejection_audit_repeat \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke \
  --selector-evidence-path reports/selector_pipeline_evidence_v082_summary
```

The command exited with code `3`, as intended, because there were no LLM true-improved candidates:

- `llm_rewrite_accepted`: `4`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- Candidate verdicts: `not_improved:3|coverage_only:1`
- Candidate highlights: `coverage_only_trap:1`
- `llm_true_improved_count`: `0`
- Coverage-only traps: `1`
- Rewrite events recorded `selector_negative_blocked_family_pairs=9` and
  `selector_negative_disallowed_formulas=14`.

The coverage-only trap was:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_7a765d304b` | `qr_5d66b52699` | `llm_rewrite` | 0.20 | -0.30446903 | BTCUSDT,ETHUSDT,BNBUSDT,AVAXUSDT | `neg(zscore(ts_argmax(close,72),120))` |

The rejection-audit columns captured two validator rejections before review:

| Parent | Rejected Reason Mix | Example |
|---|---|---|
| `qr_cb62796f3b` | `Formula depth 5 exceeds max_depth=4: zscore(corr(sign(sub(close,open)),volume,72),120):1` | `zscore(corr(sign(sub(close,open)),volume,72),120)` |
| `qr_7a765d304b` | `copies disallowed failed formula:1` | `zscore(corr(sub(close,open),volume,48),72)` |

The refreshed attempts 4-19 summary reported:

- Runs: `16`
- LLM policy evidence runs: `16`
- LLM true-improvement evidence runs: `5`
- Runs with coverage-only traps: `2`
- Highlighted candidate rows: `10`
- Distinct highlighted candidates: `7`
- Negative candidate rows: `44`
- Negative candidate family rows: `14`

Interpretation: attempt 19 confirms the rejection-audit fields are useful across repeats and adds a new coverage-only
trap to negative memory. The new trap belongs to a price-family time-since-extreme/reversal shape, and should not be
treated as improvement because pass-rate rose while mean Sharpe fell. The true-improvement hard gate remains essential.

## Rejection-Audit Repeat 20

Date: 2026-07-02

Attempt 20 repeated the same hard-gated command after refreshing selector memory with attempt 19:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence20_rejection_audit_repeat \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke \
  --selector-evidence-path reports/selector_pipeline_evidence_v082_summary
```

The command exited with code `3`, as intended, because there were no LLM true-improved candidates:

- `llm_rewrite_accepted`: `4`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- Candidate verdicts: `not_improved:3|mixed:1`
- Candidate highlights: `sharpe_improved_no_pass_lift:1`
- `llm_true_improved_count`: `0`
- Coverage-only traps: `0`
- Rewrite events recorded `selector_negative_blocked_family_pairs=11` and
  `selector_negative_disallowed_formulas=14`.

The highlight was Sharpe-improved only and lost pass-rate coverage:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_1c002c4c13` | `qr_8096823a14` | `llm_rewrite` | -0.20 | 0.03912457 | BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,AVAXUSDT | `zscore(ret(close,48),120)` |

The rejection-audit columns captured two validator rejections before review:

| Parent | Rejected Reason Mix | Example |
|---|---|---|
| `qr_cb62796f3b` | `Formula depth 5 exceeds max_depth=4: neg(zscore(skew(ret(close,6),48),120)):1` | `neg(zscore(skew(ret(close,6),48),120))` |
| `qr_7a765d304b` | `copies disallowed failed formula:1` | `zscore(corr(sub(close,open),volume,48),72)` |

The refreshed attempts 4-20 summary reported:

- Runs: `17`
- LLM policy evidence runs: `17`
- LLM true-improvement evidence runs: `5`
- Runs with coverage-only traps: `2`
- Highlighted candidate rows: `11`
- Distinct highlighted candidates: `8`
- Negative candidate rows: `47`
- Negative candidate family rows: `15`

Interpretation: attempt 20 adds another negative selector-memory row, this time for a pure-funding parent drifting into
a price-only medium-horizon momentum candidate. The hard gate correctly rejects a candidate that slightly improves mean
Sharpe but reduces pass-rate coverage and still fails every evaluated asset.

## Mixed Negative Memory And Attempt 21

Date: 2026-07-02

Attempts 14, 17, and 20 showed that `sharpe_improved_no_pass_lift` candidates can repeat even though the
true-improvement hard gate correctly rejects them. The selector evidence summary therefore now treats LLM-sourced
`mixed` review verdicts as negative selector memory alongside `not_improved` and `coverage_only` rows. The negative
family summary also records `sharpe_only_count`, so prompt memory can distinguish true losses, coverage-only traps, and
Sharpe-only/no-pass-lift failures.

After refreshing the attempts 4-20 summary with this change:

- Negative candidate rows rose from `47` to `50`.
- The negative family table added a `Sharpe Only` column.
- Sharpe-only rows now feed exact negative disallow and family-pair blocking.

Attempt 21 then ran the same hard-gated command:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence21_mixed_negative_memory \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke \
  --selector-evidence-path reports/selector_pipeline_evidence_v082_summary
```

The command exited with code `3`, as intended, because there were no LLM true-improved candidates:

- `llm_rewrite_accepted`: `2`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- `llm_error_count`: `1`
- Candidate verdicts: `not_improved:2`
- Candidate highlights: `0`
- `llm_true_improved_count`: `0`
- Coverage-only traps: `0`
- Rewrite events recorded `selector_negative_blocked_family_pairs=13` and
  `selector_negative_disallowed_formulas=15`.

The rejection-audit columns captured family-pair blocking and exact disallow before review:

| Parent | Rejected Reason Mix | Example |
|---|---|---|
| `qr_cb62796f3b` | `candidate family is blocked by negative selector memory (volume_liquidity->range_volatility):1` | `zscore(div(sub(close,low),sub(high,low)),96)` |
| `qr_1c002c4c13` | `candidate family is blocked by negative selector memory (pure_funding->range_volatility):1|copies disallowed failed formula:1` | `neg(corr(ret(close,12),sub(high,low),72))` |
| `qr_7a765d304b` | `copies disallowed failed formula:1` | `zscore(corr(sub(close,open),volume,48),72)` |

The refreshed attempts 4-21 summary reported:

- Runs: `18`
- LLM policy evidence runs: `18`
- LLM true-improvement evidence runs: `5`
- Runs with coverage-only traps: `2`
- Highlighted candidate rows: `11`
- Distinct highlighted candidates: `8`
- Negative candidate rows: `52`
- Negative candidate family rows: `15`

Interpretation: attempt 21 is process-positive even though it is not alpha-positive. The mixed-negative memory change
converted repeated Sharpe-only failures into negative prompt/validator memory, and the next repeat produced no highlight
rows while visibly blocking bad family transitions before review.

## Mixed Negative Memory Repeat Attempt 22

Date: 2026-07-02

Attempt 22 reused the same hard-gated, LLM-only research command with the refreshed attempts 4-21 selector evidence
summary:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence22_mixed_negative_memory_repeat \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke \
  --selector-evidence-path reports/selector_pipeline_evidence_v082_summary
```

The command exited with code `3`, as intended, because there were no LLM true-improved candidates:

- `llm_rewrite_accepted`: `1`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- `llm_error_count`: `2`
- Candidate verdicts: `not_improved:1`
- Candidate highlights: `0`
- `llm_true_improved_count`: `0`
- Coverage-only traps: `0`
- Rewrite events recorded `selector_negative_blocked_family_pairs=14` and
  `selector_negative_disallowed_formulas=15`.

The accepted LLM candidate was reviewed and rejected:

| Parent | Candidate | Verdict | Pass Rate Delta | Mean Sharpe Delta | Formula |
|---|---|---|---:|---:|---|
| `qr_cb62796f3b` | `qr_a885e72b5e` | `not_improved` | -0.20 | -0.99873822 | `neg(zscore(rsi(close,48),144))` |

The rejection-audit columns again showed negative-memory filtering before review:

| Rejected Reason Mix | Example |
|---|---|
| `candidate family is blocked by negative selector memory (volume_liquidity->range_volatility):1` | `zscore(div(sub(close,low),sub(high,low)),120)` |
| `candidate family is blocked by negative selector memory (pure_funding->range_volatility):1|copies disallowed failed formula:1` | `zscore(corr(sub(close,open),sub(high,low),48),72)` |
| `candidate family is blocked by negative selector memory (price->volume_liquidity):1|copies disallowed failed formula:1` | `zscore(corr(sub(close,open),volume,72),120)` |

The refreshed attempts 4-22 summary reported:

- Runs: `19`
- LLM policy evidence runs: `19`
- LLM true-improvement evidence runs: `5`
- Runs with coverage-only traps: `2`
- Highlighted candidate rows: `11`
- Distinct highlighted candidates: `8`
- Negative candidate rows: `53`
- Negative candidate family rows: `15`

Interpretation: attempt 22 adds another negative-memory confirmation rather than a new alpha improvement. It accepted
only one LLM candidate, rejected it on multi-asset review, and blocked additional exact/family repeats before review.
The `volume_liquidity->price` family now has three negative observations, while the aggregate true-improvement count
remains unchanged.

## Exhausted Target Handling And Attempts 23-26

Date: 2026-07-02

Attempts 23 and 24 reused the same hard-gated LLM-only command with the refreshed attempts 4-22 selector evidence
summary. Both commands exited with code `2` because they produced no accepted LLM rewrite candidates:

- Attempt 23 output: `reports/selector_rewrite_pipeline_llm_v082_evidence23_mixed_negative_memory_repeat`
- Attempt 24 output: `reports/selector_rewrite_pipeline_llm_v082_evidence24_mixed_negative_memory_repeat`
- `llm_rewrite_accepted`: `0`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `false`
- Universe, portfolio, portfolio-universe, and review stages were skipped because there were no candidate formulas.

The rejection audit showed that LLM calls returned formulas, but every formula was mechanically rejected before review.
The repeated reasons were exact negative formula copies, blocked negative-memory family pairs, and formula-depth
violations such as nested `zscore(corr(sub(...),sub(...),window),window)` or `neg(zscore(skew(...),window),window)`.

The rewrite prompt then gained a research-only `mechanical_rejection_guard` section. It exposes the current parent
formula family, blocked candidate families for that parent, allowed candidate families, family-classification rules, and
depth-safe templates. This does not loosen any validator, admission, publishing, or runtime rule.

Attempt 25 used the prompt guard:

- Output: `reports/selector_rewrite_pipeline_llm_v082_evidence25_mechanical_guard`
- `llm_rewrite_accepted`: `0`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `false`

Attempt 25 made the deeper failure mode explicit: for the top selector rewrite targets, negative-memory blocking had
already exhausted all primary candidate families, so the model returned no candidate formulas rather than a reviewable
candidate. The selector rewrite loop was then tightened so LLM-only mode skips targets whose parent family has no
allowed candidate families left under selector negative memory. These skips are written to `selector_rewrite_events.csv`
as `selector_target_skip` rows with `exhausted_candidate_families`.

Attempt 26 used the exhausted-target skip:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence26_exhausted_target_skip \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke \
  --selector-evidence-path reports/selector_pipeline_evidence_v082_summary
```

The command exited with code `3`, as intended, because there were no LLM true-improved candidates:

- `llm_rewrite_accepted`: `2`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- `llm_error_count`: `1`
- Candidate verdicts: `mixed:1|not_improved:1`
- Candidate highlights: `sharpe_improved_no_pass_lift:1`
- `llm_true_improved_count`: `0`
- Coverage-only traps: `0`
- Rewrite events recorded `selector_target_skip:7`, `llm_rewrite:1`, and `rewrite_fallback:1`.

The highlighted-but-not-true-improved candidate was:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_4a7fa246c2` | `qr_d4f351fd82` | `llm_rewrite` | 0.00 | 0.25326526 | BTCUSDT,SOLUSDT,BNBUSDT,AVAXUSDT | `corr(volume,ret(close,12),72)` |

The refreshed attempts 4-26 summary reported:

- Runs: `23`
- LLM policy evidence runs: `20`
- LLM true-improvement evidence runs: `5`
- Runs with coverage-only traps: `2`
- Highlighted candidate rows: `12`
- Distinct highlighted candidates: `9`
- Negative candidate rows: `55`
- Negative candidate family rows: `17`

Interpretation: attempts 23-26 are process evidence for selector-memory saturation. The top rewrite targets are now
recognized as exhausted under current negative memory, so the research loop can move to later selector targets instead
of spending repeated LLM calls on mechanically impossible family transitions. Attempt 26 restored LLM policy evidence
but still produced only a Sharpe-only/no-pass-lift candidate, which remains negative memory rather than admission or
runtime publish evidence.

## Exhausted Target Skip Repeats 27 And 28

Date: 2026-07-02

Attempt 27 reused the hard-gated LLM-only command after refreshing the attempts 4-26 selector evidence summary:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence27_exhausted_target_skip_repeat \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke \
  --selector-evidence-path reports/selector_pipeline_evidence_v082_summary
```

The command exited with code `3`, as intended, because there were no LLM true-improved candidates:

- `llm_rewrite_accepted`: `3`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- `llm_error_count`: `0`
- Candidate verdicts: `not_improved:2|mixed:1`
- Candidate highlights: `sharpe_improved_no_pass_lift:1`
- `llm_true_improved_count`: `0`
- Coverage-only traps: `0`
- Rewrite events recorded `selector_target_skip:7`, `llm_rewrite:2`, and `rewrite_validator:1`.

The highlighted-but-not-true-improved candidate was:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_ccda5f2f68` | `qr_a853a7393b` | `llm_rewrite` | 0.00 | 0.19930544 | BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,AVAXUSDT | `corr(sub(close,open),volume,96)` |

After refreshing the attempts 4-27 summary, negative candidate rows rose from `55` to `58`. Attempt 28 then reused the
same hard-gated command:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence28_exhausted_target_skip_repeat \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke \
  --selector-evidence-path reports/selector_pipeline_evidence_v082_summary
```

Attempt 28 completed successfully and passed the LLM true-improvement hard gate:

- `llm_rewrite_accepted`: `4`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- `llm_error_count`: `0`
- Candidate verdicts: `improved:2|not_improved:1|mixed:1`
- Candidate highlights: `true_improved:2|sharpe_improved_no_pass_lift:1`
- `llm_true_improved_count`: `2`
- Coverage-only traps: `0`
- Rewrite events recorded `selector_target_skip:7` and `llm_rewrite:2`.

The true-improved LLM candidates were:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_ccda5f2f68` | `qr_e23cfc8ae6` | `llm_rewrite` | 0.80 | 1.49835622 | AVAXUSDT | `zscore(std(close,48),144)` |
| `qr_4a7fa246c2` | `qr_a2cd9fd69f` | `llm_rewrite` | 0.60 | 0.77176916 | BTCUSDT | `zscore(ema(volume,48),120)` |

Attempt 28 also produced one Sharpe-only/no-pass-lift highlight:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_ccda5f2f68` | `qr_1a08a872ec` | `llm_rewrite` | 0.00 | 0.08509279 | BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,AVAXUSDT | `zscore(volume,120)` |

The refreshed attempts 4-28 summary reported:

- Runs: `25`
- LLM policy evidence runs: `22`
- LLM true-improvement evidence runs: `6`
- Runs with coverage-only traps: `2`
- Highlighted candidate rows: `16`
- Distinct highlighted candidates: `13`
- Negative candidate rows: `60`
- Negative candidate family rows: `18`

Interpretation: exhausted-target skipping is now doing useful work. It bypasses saturated top targets while preserving
auditability, and attempt 28 found two LLM-sourced true-improved candidates on later selector targets. These are still
research-only selector rewrite evidence: neither candidate is admitted, published, or runtime-ready without separate
admission, walk-forward, portfolio, and manual review.

## Conflict-Aware Negative Memory And Attempts 29-30

Date: 2026-07-02

Attempt 29 reused the same hard-gated LLM-only command with the refreshed attempts 4-28 selector evidence summary:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence29_exhausted_target_skip_repeat \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke \
  --selector-evidence-path reports/selector_pipeline_evidence_v082_summary
```

The command exited with code `3`, as intended, because there were no LLM true-improved candidates:

- `llm_rewrite_accepted`: `3`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- `llm_error_count`: `0`
- Candidate verdicts: `not_improved:3`
- Candidate highlights: `0`
- `llm_true_improved_count`: `0`
- Rewrite events recorded `selector_target_skip:7`, `llm_rewrite:2`, and `rewrite_validator:1`.

Attempt 29 added negative rows for funding-interaction parents drifting into price and volume/liquidity candidates. The
refreshed attempts 4-29 summary reported:

- Runs: `26`
- LLM policy evidence runs: `23`
- LLM true-improvement evidence runs: `6`
- Negative candidate rows: `63`
- Negative candidate family rows: `19`

This exposed a selector-memory nuance: some family pairs now have both negative evidence and LLM true-improved evidence.
For example, `funding_interaction->volume_liquidity` contains repeated Sharpe-only/no-pass-lift failures, but also the
true-improved `zscore(ema(volume,48),120)` result from attempt 28. The evidence summary now records family-level
`true_improved_count`, true-improved run IDs, and best true-improved deltas in
`selector_pipeline_negative_candidate_summary.csv`. Family-pair blocking no longer blocks a whole family pair when that
pair has LLM true-improved evidence; exact failed formulas still remain disallowed.

Attempt 30 then ran with this conflict-aware selector memory:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence30_conflict_aware_memory \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke \
  --selector-evidence-path reports/selector_pipeline_evidence_v082_summary
```

Attempt 30 completed successfully and passed the LLM true-improvement hard gate:

- `llm_rewrite_accepted`: `4`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- `llm_error_count`: `0`
- Candidate verdicts: `improved:4`
- Candidate highlights: `true_improved:4`
- `llm_true_improved_count`: `4`
- Rewrite events recorded `selector_target_skip:4`, `llm_rewrite:3`, and `rewrite_validator:2`.

The true-improved LLM candidates were:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_7a765d304b` | `qr_a2cd9fd69f` | `llm_rewrite` | 0.80 | 0.44211152 | BTCUSDT | `zscore(ema(volume,48),120)` |
| `qr_4a7fa246c2` | `qr_e23cfc8ae6` | `llm_rewrite` | 0.60 | 1.06153455 | AVAXUSDT | `zscore(std(close,48),144)` |
| `qr_4a7fa246c2` | `qr_f61439dfd5` | `llm_rewrite` | 0.40 | 0.73177118 | BTCUSDT,ETHUSDT | `zscore(ema(volume,24),144)` |
| `qr_ccda5f2f68` | `qr_1aa34f4735` | `llm_rewrite` | 0.40 | 0.68271748 | BTCUSDT,BNBUSDT,AVAXUSDT | `corr(sub(close,open),volume,48)` |

The refreshed attempts 4-30 summary reported:

- Runs: `27`
- LLM policy evidence runs: `24`
- LLM true-improvement evidence runs: `7`
- Runs with coverage-only traps: `2`
- Highlighted candidate rows: `20`
- Distinct highlighted candidates: `17`
- Negative candidate rows: `63`
- Negative candidate family rows: `19`

Interpretation: conflict-aware negative memory prevents over-blocking family pairs that have produced true-improved
evidence while preserving exact failed-formula disallow and pure-negative family-pair blocking. Attempt 30 is positive
process evidence for this selector-memory refinement, but the highlighted formulas remain research-only until separate
walk-forward, admission, portfolio, and manual runtime-publishing review.

Attempt 31 repeated the same conflict-aware selector memory setup:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence31_conflict_aware_memory_repeat \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke \
  --selector-evidence-path reports/selector_pipeline_evidence_v082_summary
```

Attempt 31 completed successfully and passed the LLM true-improvement hard gate:

- `llm_rewrite_accepted`: `4`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- `llm_error_count`: `0`
- Candidate verdicts: `not_improved:3|improved:1`
- Candidate highlights: `true_improved:1`
- `llm_true_improved_count`: `1`
- Rewrite events recorded `selector_target_skip:4`, `llm_rewrite:3`, and `rewrite_validator:2`.

The true-improved LLM candidate was:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_4a7fa246c2` | `qr_a2cd9fd69f` | `llm_rewrite` | 0.60 | 0.77176916 | BTCUSDT | `zscore(ema(volume,48),120)` |

The refreshed attempts 4-31 summary reported:

- Runs: `28`
- LLM policy evidence runs: `25`
- LLM true-improvement evidence runs: `8`
- Runs with coverage-only traps: `2`
- Highlighted candidate rows: `21`
- Distinct highlighted candidates: `17`
- Negative candidate rows: `66`
- Negative candidate family rows: `19`

Interpretation: attempt 31 is a narrower repeat of the conflict-aware memory result. It reinforces that the family-level
conflict guard can keep useful volume-liquidity candidates reachable even when the same family pairs also contain
negative evidence. The repeat also added three new LLM-sourced negative candidates to memory, including weak price,
raw volume fade, and negative realized-volatility shapes. The positive formula remains a research-only selector
candidate and is not admission, publishing, or runtime evidence.

Attempt 32 repeated the same hard-gated conflict-aware memory setup:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence32_conflict_aware_memory_repeat \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke \
  --selector-evidence-path reports/selector_pipeline_evidence_v082_summary
```

Attempt 32 completed successfully and passed the LLM true-improvement hard gate:

- `llm_rewrite_accepted`: `4`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- Candidate verdicts: `improved:3|mixed:1`
- Candidate highlights: `true_improved:3|sharpe_improved_no_pass_lift:1`
- `llm_true_improved_count`: `3`
- Rewrite events recorded `selector_target_skip:4`, `llm_rewrite:3`, and `rewrite_validator:2`.

The true-improved LLM candidates were:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_7a765d304b` | `qr_a2cd9fd69f` | `llm_rewrite` | 0.80 | 0.44211152 | BTCUSDT | `zscore(ema(volume,48),120)` |
| `qr_ccda5f2f68` | `qr_edd31d7e32` | `llm_rewrite` | 0.60 | 0.97526250 | BTCUSDT,SOLUSDT | `zscore(std(ret(close,4),24),120)` |
| `qr_ccda5f2f68` | `qr_33f1508627` | `llm_rewrite` | 0.60 | 0.80809019 | BTCUSDT,SOLUSDT | `zscore(sma(volume,24),96)` |

The non-true-improved highlight was:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_4a7fa246c2` | `qr_cd595899ee` | `llm_rewrite` | 0.00 | 0.37866408 | BTCUSDT,ETHUSDT,BNBUSDT,AVAXUSDT | `zscore(corr(sub(close,open),volume,36),96)` |

The rewrite validator also rejected `neg(zscore(std(ret(close,1),36),144))` because `ret` requires an integer window
of at least `2`, confirming the existing parser guard still catches invalid LLM shapes before review.

The refreshed attempts 4-32 summary reported:

- Runs: `29`
- LLM policy evidence runs: `26`
- LLM true-improvement evidence runs: `9`
- Runs with coverage-only traps: `2`
- Highlighted candidate rows: `25`
- Distinct highlighted candidates: `20`
- Negative candidate rows: `67`
- Negative candidate family rows: `19`

Interpretation: attempt 32 is another positive process result for conflict-aware selector memory. It repeated the
strong `zscore(ema(volume,48),120)` candidate and added two new LLM-sourced true-improved candidates in range-volatility
and volume-liquidity families. The Sharpe-only/no-pass-lift row for `qr_cd595899ee` shows why candidate-level
parent-specific review remains necessary: a formula that was true-improved for earlier parents can still fail the
pass-rate lift requirement for a different parent. These artifacts remain research-only selector evidence and do not
admit, publish, or update runtime strategies.

Attempt 33 repeated the same hard-gated conflict-aware memory setup:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence33_conflict_aware_memory_repeat \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke \
  --selector-evidence-path reports/selector_pipeline_evidence_v082_summary
```

Attempt 33 completed successfully and passed the LLM true-improvement hard gate:

- `llm_rewrite_accepted`: `6`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- Candidate verdicts: `not_improved:4|improved:2`
- Candidate highlights: `true_improved:2`
- `llm_true_improved_count`: `2`
- Rewrite events recorded `selector_target_skip:4` and `llm_rewrite:3`; no LLM candidate required validator rejection.

The true-improved LLM candidates were:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_ccda5f2f68` | `qr_f5f52b2594` | `llm_rewrite` | 1.00 | 1.24213645 | none | `zscore(sma(volume,36),144)` |
| `qr_4a7fa246c2` | `qr_295d2e9ee2` | `llm_rewrite` | 0.60 | 0.65493676 | BTCUSDT | `zscore(ema(volume,24),120)` |

The four not-improved candidates added negative evidence for:

- negative realized-volatility stress: `neg(zscore(std(close,36),120))`
- volume acceleration: `zscore(delta(volume,48),144)`
- negative slow volume crowding: `neg(zscore(ema(volume,48),120))`
- negative range stress: `neg(zscore(sub(high,low),120))`

The refreshed attempts 4-33 summary reported:

- Runs: `30`
- LLM policy evidence runs: `27`
- LLM true-improvement evidence runs: `10`
- Runs with coverage-only traps: `2`
- Highlighted candidate rows: `27`
- Distinct highlighted candidates: `22`
- Negative candidate rows: `71`
- Negative candidate family rows: `19`

Interpretation: attempt 33 strengthens the volume-liquidity rewrite theme. The best candidate,
`zscore(sma(volume,36),144)`, passed all five reviewed assets and is the strongest single selector rewrite highlight in
this repeat sequence by pass-rate delta. At the same time, the negative volume variants show the edge is sign and
smoothing sensitive: positive smoothed participation helped, while acceleration and negative crowding variants failed.
This remains research-only evidence; the new candidate still needs repeat, walk-forward, admission, portfolio, and
manual runtime-publishing review before any runtime consideration.

Attempt 34 repeated the same hard-gated conflict-aware memory setup:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence34_conflict_aware_memory_repeat \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke \
  --selector-evidence-path reports/selector_pipeline_evidence_v082_summary
```

Attempt 34 completed successfully and passed the LLM true-improvement hard gate:

- `llm_rewrite_accepted`: `6`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- Candidate verdicts: `improved:4|not_improved:2`
- Candidate highlights: `true_improved:4`
- `llm_true_improved_count`: `4`
- Rewrite events recorded `selector_target_skip:4` and `llm_rewrite:3`; no LLM candidate required validator rejection.

The true-improved LLM candidates were:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_7a765d304b` | `qr_a2cd9fd69f` | `llm_rewrite` | 0.80 | 0.44211152 | BTCUSDT | `zscore(ema(volume,48),120)` |
| `qr_4a7fa246c2` | `qr_c3ccb8e228` | `llm_rewrite` | 0.60 | 0.84810419 | AVAXUSDT | `zscore(std(close,48),120)` |
| `qr_4a7fa246c2` | `qr_aded180101` | `llm_rewrite` | 0.60 | 0.67117528 | BTCUSDT | `zscore(ema(volume,24),96)` |
| `qr_ccda5f2f68` | `qr_6cab970b52` | `llm_rewrite` | 0.20 | 0.29108682 | BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT | `zscore(std(close,12),120)` |

The two not-improved candidates were both volume-acceleration variants:

- `zscore(delta(volume,48),144)`
- `zscore(delta(volume,6),96)`

The refreshed attempts 4-34 summary reported:

- Runs: `31`
- LLM policy evidence runs: `28`
- LLM true-improvement evidence runs: `11`
- Runs with coverage-only traps: `2`
- Highlighted candidate rows: `31`
- Distinct highlighted candidates: `25`
- Negative candidate rows: `73`
- Negative candidate family rows: `19`

Interpretation: attempt 34 is another strong conflict-aware repeat. `zscore(ema(volume,48),120)` now has three
true-improved highlights against the price parent in the aggregate summary, making it the most repeated positive after
the early `qr_cd595899ee` cluster. The result also adds fresh positive range-volatility evidence for funding-interaction
parents, while volume acceleration remains negative. These artifacts remain research-only selector evidence and do not
admit, publish, or update runtime strategies.

Attempt 35 repeated the same hard-gated conflict-aware memory setup:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence35_conflict_aware_memory_repeat \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke \
  --selector-evidence-path reports/selector_pipeline_evidence_v082_summary
```

Attempt 35 completed successfully and passed the LLM true-improvement hard gate:

- `llm_rewrite_accepted`: `5`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- Candidate verdicts: `improved:3|not_improved:2`
- Candidate highlights: `true_improved:3`
- `llm_true_improved_count`: `3`
- Rewrite events recorded `selector_target_skip:4`, `rewrite_validator:1`, and `llm_rewrite:3`.

The true-improved LLM candidates were:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_ccda5f2f68` | `qr_3cdea28d1b` | `llm_rewrite` | 1.00 | 1.20305771 | none | `zscore(ema(volume,36),144)` |
| `qr_7a765d304b` | `qr_a2cd9fd69f` | `llm_rewrite` | 0.80 | 0.44211152 | BTCUSDT | `zscore(ema(volume,48),120)` |
| `qr_4a7fa246c2` | `qr_295d2e9ee2` | `llm_rewrite` | 0.60 | 0.65493676 | BTCUSDT | `zscore(ema(volume,24),120)` |

The two not-improved candidates were range-volatility variants:

- `zscore(std(close,12),120)`
- `neg(zscore(std(close,24),120))`

The refreshed attempts 4-35 summary reported:

- Runs: `32`
- LLM policy evidence runs: `29`
- LLM true-improvement evidence runs: `12`
- Runs with coverage-only traps: `2`
- Highlighted candidate rows: `34`
- Distinct highlighted candidates: `26`
- Negative candidate rows: `75`
- Negative candidate family rows: `19`

Interpretation: attempt 35 further concentrates positive evidence around smoothed volume participation. The price-parent
`zscore(ema(volume,48),120)` row now has four LLM true-improved highlights in the aggregate summary, and
`zscore(ema(volume,24),120)` has repeated twice for a funding-interaction parent. The new
`zscore(ema(volume,36),144)` result mirrors attempt 33's all-asset `zscore(sma(volume,36),144)` highlight, suggesting
the 36/144 smoothed participation shape is worth repeat testing. Range-volatility remains mixed rather than uniformly
positive, so exact negative memory should continue without whole-family blocking. These artifacts remain research-only
selector evidence and do not admit, publish, or update runtime strategies.

Attempt 36 repeated the same hard-gated conflict-aware memory setup:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence36_conflict_aware_memory_repeat \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke \
  --selector-evidence-path reports/selector_pipeline_evidence_v082_summary
```

Attempt 36 completed successfully and passed the LLM true-improvement hard gate:

- `llm_rewrite_accepted`: `4`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- Candidate verdicts: `improved:4`
- Candidate highlights: `true_improved:4`
- `llm_true_improved_count`: `4`
- Rewrite events recorded `selector_target_skip:4`, `rewrite_validator:2`, and `llm_rewrite:3`.

The true-improved LLM candidates were:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_ccda5f2f68` | `qr_7a81ad156d` | `llm_rewrite` | 0.80 | 1.15668668 | SOLUSDT | `zscore(sma(volume,36),120)` |
| `qr_7a765d304b` | `qr_a2cd9fd69f` | `llm_rewrite` | 0.80 | 0.44211152 | BTCUSDT | `zscore(ema(volume,48),120)` |
| `qr_4a7fa246c2` | `qr_aded180101` | `llm_rewrite` | 0.60 | 0.67117528 | BTCUSDT | `zscore(ema(volume,24),96)` |
| `qr_ccda5f2f68` | `qr_b49066f917` | `llm_rewrite` | 0.40 | 0.79389268 | ETHUSDT,SOLUSDT,AVAXUSDT | `zscore(std(close,24),120)` |

The rewrite validator rejected `neg(zscore(std(ret(close,4),60),144))` because formula depth `5` exceeded
`max_depth=4`, confirming that the depth guard still catches invalid LLM shapes before review.

The refreshed attempts 4-36 summary reported:

- Runs: `33`
- LLM policy evidence runs: `30`
- LLM true-improvement evidence runs: `13`
- Runs with coverage-only traps: `2`
- Highlighted candidate rows: `38`
- Distinct highlighted candidates: `28`
- Negative candidate rows: `75`
- Negative candidate family rows: `19`

Interpretation: attempt 36 is a clean positive repeat: all reviewed candidates were LLM-sourced true-improved
highlights, and no coverage-only or Sharpe-only queue was populated. The price-parent `zscore(ema(volume,48),120)` row
now has five LLM true-improved highlights in the aggregate summary. The broader 36-bar smoothed participation family is
also strengthening through `sma(volume,36)` and `ema(volume,36)` variants across both 120- and 144-bar normalization.
These artifacts remain research-only selector evidence and do not admit, publish, or update runtime strategies.

Attempt 37 repeated the same hard-gated conflict-aware memory setup:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence37_conflict_aware_memory_repeat \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke \
  --selector-evidence-path reports/selector_pipeline_evidence_v082_summary
```

Attempt 37 completed successfully and passed the LLM true-improvement hard gate:

- `llm_rewrite_accepted`: `3`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- Candidate verdicts: `not_improved:2|improved:1`
- Candidate highlights: `true_improved:1`
- `llm_true_improved_count`: `1`
- Rewrite events recorded `selector_target_skip:4`, `rewrite_validator:3`, and `llm_rewrite:3`.

The true-improved LLM candidate was:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_7a765d304b` | `qr_a2cd9fd69f` | `llm_rewrite` | 0.80 | 0.44211152 | BTCUSDT | `zscore(ema(volume,48),120)` |

The two not-improved candidates were volume/range coupling variants:

- `zscore(corr(volume,sub(high,low),72),96)`
- `neg(corr(volume,sub(high,low),96))`

The refreshed attempts 4-37 summary reported:

- Runs: `34`
- LLM policy evidence runs: `31`
- LLM true-improvement evidence runs: `14`
- Runs with coverage-only traps: `2`
- Highlighted candidate rows: `39`
- Distinct highlighted candidates: `28`
- Negative candidate rows: `77`
- Negative candidate family rows: `19`

Interpretation: attempt 37 is a narrower positive repeat that further strengthens smoothed positive volume
participation. The price-parent `zscore(ema(volume,48),120)` row now has six LLM true-improved highlights in the
aggregate summary, and the same formula has eight true-improved highlights across the two reviewed parent contexts.
The new negative volume/range coupling rows add caution around range-volatility rewrites, especially when volume and
range co-move as stress rather than constructive participation. Keep conflict-aware family memory: exact failed
formulas and pure-negative family pairs should remain blocked, while volume-liquidity and range-volatility families
should not be mechanically banned. These artifacts remain research-only selector evidence and do not admit, publish,
or update runtime strategies.

Attempt 38 repeated the same hard-gated conflict-aware memory setup:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence38_conflict_aware_memory_repeat \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke \
  --selector-evidence-path reports/selector_pipeline_evidence_v082_summary
```

Attempt 38 completed successfully and passed the LLM true-improvement hard gate:

- `llm_rewrite_accepted`: `6`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- Candidate verdicts: `improved:5|not_improved:1`
- Candidate highlights: `true_improved:5`
- `llm_true_improved_count`: `5`
- Rewrite events recorded `selector_target_skip:4` and `llm_rewrite:3`.

The true-improved LLM candidates were:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_ccda5f2f68` | `qr_3cdea28d1b` | `llm_rewrite` | 1.00 | 1.20305771 | none | `zscore(ema(volume,36),144)` |
| `qr_7a765d304b` | `qr_a2cd9fd69f` | `llm_rewrite` | 0.80 | 0.44211152 | BTCUSDT | `zscore(ema(volume,48),120)` |
| `qr_4a7fa246c2` | `qr_c3ccb8e228` | `llm_rewrite` | 0.60 | 0.84810419 | AVAXUSDT | `zscore(std(close,48),120)` |
| `qr_4a7fa246c2` | `qr_295d2e9ee2` | `llm_rewrite` | 0.60 | 0.65493676 | BTCUSDT | `zscore(ema(volume,24),120)` |
| `qr_ccda5f2f68` | `qr_337094fb55` | `llm_rewrite` | 0.40 | 0.85028641 | ETHUSDT,SOLUSDT,AVAXUSDT | `zscore(std(close,24),144)` |

The not-improved candidate was another volume-acceleration variant:

- `zscore(delta(volume,24),168)`

The refreshed attempts 4-38 summary reported:

- Runs: `35`
- LLM policy evidence runs: `32`
- LLM true-improvement evidence runs: `15`
- Runs with coverage-only traps: `2`
- Highlighted candidate rows: `44`
- Distinct highlighted candidates: `29`
- Negative candidate rows: `78`
- Negative candidate family rows: `19`

Interpretation: attempt 38 is a strong positive repeat for conflict-aware selector memory. The price-parent
`zscore(ema(volume,48),120)` row now has seven LLM true-improved highlights in the aggregate summary, and the same
formula has nine true-improved highlights across the two reviewed parent contexts. `zscore(ema(volume,36),144)` now has
two true-improved repeats for the funding-interaction parent, while `zscore(ema(volume,24),120)` has three. Some
range-volatility candidates continue to produce true-improved evidence, but the family still contains enough negative
rows to stay conflict-aware rather than mechanically preferred. The fresh `zscore(delta(volume,24),168)` failure
reinforces the existing negative pattern for volume acceleration. These artifacts remain research-only selector
evidence and do not admit, publish, or update runtime strategies.

Attempt 39 repeated the same hard-gated conflict-aware memory setup:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence39_conflict_aware_memory_repeat \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke \
  --selector-evidence-path reports/selector_pipeline_evidence_v082_summary
```

Attempt 39 completed successfully and passed the LLM true-improvement hard gate:

- `llm_rewrite_accepted`: `5`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- Candidate verdicts: `improved:5`
- Candidate highlights: `true_improved:5`
- `llm_true_improved_count`: `5`
- Rewrite events recorded `selector_target_skip:4`, `rewrite_validator:1`, and `llm_rewrite:3`.

The true-improved LLM candidates were:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_ccda5f2f68` | `qr_aded180101` | `llm_rewrite` | 0.80 | 1.10799695 | BTCUSDT | `zscore(ema(volume,24),96)` |
| `qr_7a765d304b` | `qr_a2cd9fd69f` | `llm_rewrite` | 0.80 | 0.44211152 | BTCUSDT | `zscore(ema(volume,48),120)` |
| `qr_4a7fa246c2` | `qr_c3ccb8e228` | `llm_rewrite` | 0.60 | 0.84810419 | AVAXUSDT | `zscore(std(close,48),120)` |
| `qr_4a7fa246c2` | `qr_1aa34f4735` | `llm_rewrite` | 0.20 | 0.24589581 | BTCUSDT,BNBUSDT,AVAXUSDT | `corr(sub(close,open),volume,48)` |
| `qr_ccda5f2f68` | `qr_e2186d7430` | `llm_rewrite` | 0.20 | 0.17836891 | BTCUSDT,ETHUSDT,BNBUSDT,AVAXUSDT | `zscore(sub(high,low),96)` |

Attempt 39 added no coverage-only, Sharpe-only, or not-improved candidate queue rows. The rewrite validator blocked
one exact failed-formula repeat, `zscore(corr(sub(close,open),volume,48),72)`.

The refreshed attempts 4-39 summary reported:

- Runs: `36`
- LLM policy evidence runs: `33`
- LLM true-improvement evidence runs: `16`
- Runs with coverage-only traps: `2`
- Highlighted candidate rows: `49`
- Distinct highlighted candidates: `32`
- Negative candidate rows: `78`
- Negative candidate family rows: `19`

Interpretation: attempt 39 is another clean positive repeat. The price-parent `zscore(ema(volume,48),120)` row now has
eight LLM true-improved highlights in the aggregate summary, and the same formula has ten true-improved highlights
across the two reviewed parent contexts. The repeat also strengthens the secondary clusters around
`zscore(std(close,48),120)` and shorter smoothed-volume variants. Range-volatility still remains mixed overall, but
conflict-aware memory is doing the right thing: it permits specific positive volatility/range candidates while exact
failed formulas and pure-negative family pairs remain blocked. These artifacts remain research-only selector evidence
and do not admit, publish, or update runtime strategies.

Attempt 40 repeated the same hard-gated conflict-aware memory setup:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence40_conflict_aware_memory_repeat \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke \
  --selector-evidence-path reports/selector_pipeline_evidence_v082_summary
```

Attempt 40 completed successfully and passed the LLM true-improvement hard gate:

- `llm_rewrite_accepted`: `5`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- Candidate verdicts: `improved:4|coverage_only:1`
- Candidate highlights: `true_improved:4|coverage_only_trap:1`
- `llm_true_improved_count`: `4`
- Rewrite events recorded `selector_target_skip:4` and `llm_rewrite:3`.

The true-improved LLM candidates were:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_ccda5f2f68` | `qr_36c5a0e5ea` | `llm_rewrite` | 0.60 | 1.48584351 | SOLUSDT,AVAXUSDT | `zscore(std(close,36),168)` |
| `qr_4a7fa246c2` | `qr_a2cd9fd69f` | `llm_rewrite` | 0.60 | 0.77176916 | BTCUSDT | `zscore(ema(volume,48),120)` |
| `qr_4a7fa246c2` | `qr_9f0abad4e7` | `llm_rewrite` | 0.40 | 1.17130170 | BTCUSDT,AVAXUSDT | `zscore(std(close,48),168)` |
| `qr_ccda5f2f68` | `qr_ca1279db8a` | `llm_rewrite` | 0.40 | 0.67025639 | BTCUSDT,SOLUSDT,BNBUSDT | `zscore(sma(volume,24),120)` |

The coverage-only trap was:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_7a765d304b` | `qr_1aa34f4735` | `llm_rewrite` | 0.40 | -0.08376183 | BTCUSDT,BNBUSDT,AVAXUSDT | `corr(sub(close,open),volume,48)` |

The refreshed attempts 4-40 summary reported:

- Runs: `37`
- LLM policy evidence runs: `34`
- LLM true-improvement evidence runs: `17`
- Runs with coverage-only traps: `3`
- Highlighted candidate rows: `54`
- Distinct highlighted candidates: `36`
- Negative candidate rows: `79`
- Negative candidate family rows: `19`

Interpretation: attempt 40 still passed the hard gate, but it is a useful reminder that parent-specific review matters.
`corr(sub(close,open),volume,48)` has true-improved evidence for a funding-interaction parent, but became a
coverage-only trap against the price parent in this run. The strongest repeated artifact remains
`zscore(ema(volume,48),120)`, which now has eleven true-improved highlights across the two reviewed parent contexts.
Range/volatility candidates continue to add positive evidence in specific shapes such as `zscore(std(close,36),168)`
and `zscore(std(close,48),168)`, while the family-level memory should remain conflict-aware rather than whole-family
acceptance. These artifacts remain research-only selector evidence and do not admit, publish, or update runtime
strategies.

Attempt 41 repeated the same hard-gated conflict-aware memory setup:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence41_conflict_aware_memory_repeat \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke \
  --selector-evidence-path reports/selector_pipeline_evidence_v082_summary
```

Attempt 41 completed successfully and passed the LLM true-improvement hard gate:

- `llm_rewrite_accepted`: `4`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- Candidate verdicts: `improved:3|not_improved:1`
- Candidate highlights: `true_improved:3`
- `llm_true_improved_count`: `3`
- Rewrite events recorded `selector_target_skip:4`, `rewrite_validator:2`, and `llm_rewrite:3`.

The true-improved LLM candidates were:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_ccda5f2f68` | `qr_e23cfc8ae6` | `llm_rewrite` | 0.80 | 1.49835622 | AVAXUSDT | `zscore(std(close,48),144)` |
| `qr_ccda5f2f68` | `qr_d96fec850d` | `llm_rewrite` | 0.80 | 1.10976543 | BTCUSDT | `zscore(ema(volume,36),120)` |
| `qr_4a7fa246c2` | `qr_fcc0b75150` | `llm_rewrite` | 0.40 | 0.66090047 | SOLUSDT,AVAXUSDT | `zscore(std(close,36),120)` |

The not-improved candidate was:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_7a765d304b` | `qr_62da79b468` | `llm_rewrite` | 0.00 | -1.33201839 | BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,AVAXUSDT | `neg(zscore(ema(volume,48),120))` |

The rewrite validator blocked one exact failed-formula repeat,
`zscore(corr(sub(close,open),volume,48),72)`, and one depth-5 negative volume/range correlation:
`neg(zscore(corr(volume,sub(high,low),48),96))`.

The refreshed attempts 4-41 summary reported:

- Runs: `38`
- LLM policy evidence runs: `35`
- LLM true-improvement evidence runs: `18`
- Runs with coverage-only traps: `3`
- Highlighted candidate rows: `57`
- Distinct highlighted candidates: `38`
- Negative candidate rows: `80`
- Negative candidate family rows: `19`

Interpretation: attempt 41 reinforces two selector rewrite themes at once. First, the sign of the smoothed-volume edge
is important: `neg(zscore(ema(volume,48),120))` was broadly not improved, while positive smoothed participation
variants keep accumulating true-improved evidence. Second, realized-volatility regime candidates continue to work in
specific medium-horizon shapes, with `zscore(std(close,48),144)` now repeating for the funding-interaction parent.
Conflict-aware memory remains appropriate: preserve exact failed-formula blocking and negative-sign volume memory while
leaving positive smoothed-volume and selected volatility-regime candidates reachable. These artifacts remain
research-only selector evidence and do not admit, publish, or update runtime strategies.

Attempt 42 repeated the same hard-gated conflict-aware memory setup:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence42_conflict_aware_memory_repeat \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke \
  --selector-evidence-path reports/selector_pipeline_evidence_v082_summary
```

Attempt 42 completed successfully and passed the LLM true-improvement hard gate:

- `llm_rewrite_accepted`: `5`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- Candidate verdicts: `improved:3|not_improved:2`
- Candidate highlights: `true_improved:3`
- `llm_true_improved_count`: `3`
- Rewrite events recorded `selector_target_skip:4`, `rewrite_validator:1`, and `llm_rewrite:3`.

The true-improved LLM candidates were:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_ccda5f2f68` | `qr_d96fec850d` | `llm_rewrite` | 0.80 | 1.10976543 | BTCUSDT | `zscore(ema(volume,36),120)` |
| `qr_7a765d304b` | `qr_a2cd9fd69f` | `llm_rewrite` | 0.80 | 0.44211152 | BTCUSDT | `zscore(ema(volume,48),120)` |
| `qr_ccda5f2f68` | `qr_fcc0b75150` | `llm_rewrite` | 0.60 | 1.09772214 | SOLUSDT,AVAXUSDT | `zscore(std(close,36),120)` |

The not-improved LLM candidates were:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_4a7fa246c2` | `qr_a853a7393b` | `llm_rewrite` | -0.20 | -0.23751623 | BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,AVAXUSDT | `corr(sub(close,open),volume,96)` |
| `qr_4a7fa246c2` | `qr_903b1672ff` | `llm_rewrite` | -0.20 | -1.24060683 | BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,AVAXUSDT | `neg(zscore(std(close,48),144))` |

The rewrite validator also blocked one exact failed-formula repeat:
`zscore(corr(sub(close,open),volume,48),72)`.

The refreshed attempts 4-42 summary reported:

- Runs: `39`
- LLM policy evidence runs: `36`
- LLM true-improvement evidence runs: `19`
- Runs with coverage-only traps: `3`
- Highlighted candidate rows: `60`
- Distinct highlighted candidates: `39`
- Negative candidate rows: `82`
- Negative candidate family rows: `19`

Interpretation: attempt 42 is another mixed positive repeat. Positive smoothed volume participation remains the
strongest repeated theme: the price-parent `zscore(ema(volume,48),120)` row now has nine LLM true-improved highlights,
and the same formula has twelve true-improved highlights across the two reviewed parent contexts. The 36-bar
participation smoother is also repeating through `zscore(ema(volume,36),120)`. The negative candidates reinforce that
longer signed price-volume correlation and negative volatility-regime signs are fragile; exact and sign-aware negative
memory should keep filtering those shapes while conflict-aware memory leaves the positive variants reachable. These
artifacts remain research-only selector evidence and do not admit, publish, or update runtime strategies.

Attempt 43 repeated the same hard-gated conflict-aware memory setup:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence43_conflict_aware_memory_repeat \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke \
  --selector-evidence-path reports/selector_pipeline_evidence_v082_summary
```

Attempt 43 completed successfully and passed the LLM true-improvement hard gate:

- `llm_rewrite_accepted`: `4`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- Candidate verdicts: `improved:3|not_improved:1`
- Candidate highlights: `true_improved:3`
- `llm_true_improved_count`: `3`
- Rewrite events recorded `selector_target_skip:4`, `rewrite_validator:2`, and `llm_rewrite:3`.

The true-improved LLM candidates were:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_ccda5f2f68` | `qr_3cdea28d1b` | `llm_rewrite` | 1.00 | 1.20305771 | none | `zscore(ema(volume,36),144)` |
| `qr_7a765d304b` | `qr_a2cd9fd69f` | `llm_rewrite` | 0.80 | 0.44211152 | BTCUSDT | `zscore(ema(volume,48),120)` |
| `qr_4a7fa246c2` | `qr_aded180101` | `llm_rewrite` | 0.60 | 0.67117528 | BTCUSDT | `zscore(ema(volume,24),96)` |

The not-improved LLM candidate was:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_4a7fa246c2` | `qr_bb4e0fef71` | `llm_rewrite` | 0.00 | -0.28385329 | BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT | `zscore(std(close,12),96)` |

The rewrite validator blocked one exact failed-formula repeat,
`zscore(corr(sub(close,open),volume,48),72)`, and one invalid return-window shape:
`zscore(std(ret(close,1),36),120)`.

The refreshed attempts 4-43 summary reported:

- Runs: `40`
- LLM policy evidence runs: `37`
- LLM true-improvement evidence runs: `20`
- Runs with coverage-only traps: `3`
- Highlighted candidate rows: `63`
- Distinct highlighted candidates: `39`
- Negative candidate rows: `83`
- Negative candidate family rows: `19`

Interpretation: attempt 43 is another clean positive repeat for conflict-aware selector memory. The price-parent
`zscore(ema(volume,48),120)` row now has ten LLM true-improved highlights in the aggregate summary, and the same
formula has thirteen true-improved highlights across the two reviewed parent contexts. The funding-interaction parent
also strengthened two smoothed-volume branches: `zscore(ema(volume,36),144)` now has three true-improved repeats, and
`zscore(ema(volume,24),96)` now has three true-improved repeats for the reviewed funding-interaction parent. The short
`zscore(std(close,12),96)` miss keeps range/volatility memory shape-specific rather than family-wide. These artifacts
remain research-only selector evidence and do not admit, publish, or update runtime strategies.

Attempt 44 repeated the same hard-gated conflict-aware memory setup:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence44_conflict_aware_memory_repeat \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke \
  --selector-evidence-path reports/selector_pipeline_evidence_v082_summary
```

Attempt 44 completed successfully and passed the LLM true-improvement hard gate:

- `llm_rewrite_accepted`: `5`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- Candidate verdicts: `improved:3|not_improved:2`
- Candidate highlights: `true_improved:3`
- `llm_true_improved_count`: `3`
- Rewrite events recorded `selector_target_skip:4`, `rewrite_validator:1`, and `llm_rewrite:3`.

The true-improved LLM candidates were:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_ccda5f2f68` | `qr_c3ccb8e228` | `llm_rewrite` | 0.80 | 1.28492586 | AVAXUSDT | `zscore(std(close,48),120)` |
| `qr_ccda5f2f68` | `qr_295d2e9ee2` | `llm_rewrite` | 0.80 | 1.09175843 | BTCUSDT | `zscore(ema(volume,24),120)` |
| `qr_7a765d304b` | `qr_a2cd9fd69f` | `llm_rewrite` | 0.80 | 0.44211152 | BTCUSDT | `zscore(ema(volume,48),120)` |

The not-improved LLM candidates were:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_4a7fa246c2` | `qr_60e5b16ff4` | `llm_rewrite` | -0.20 | -0.55994105 | BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,AVAXUSDT | `zscore(delta(volume,48),120)` |
| `qr_4a7fa246c2` | `qr_c5c1799453` | `llm_rewrite` | -0.20 | -0.56037291 | BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,AVAXUSDT | `neg(corr(volume,sub(high,low),96))` |

The rewrite validator blocked one exact failed-formula repeat:
`zscore(corr(sub(close,open),volume,48),72)`.

The refreshed attempts 4-44 summary reported:

- Runs: `41`
- LLM policy evidence runs: `38`
- LLM true-improvement evidence runs: `21`
- Runs with coverage-only traps: `3`
- Highlighted candidate rows: `66`
- Distinct highlighted candidates: `41`
- Negative candidate rows: `85`
- Negative candidate family rows: `19`

Interpretation: attempt 44 is a mixed positive repeat. The strongest price-parent row,
`zscore(ema(volume,48),120)`, now has eleven LLM true-improved highlights in the aggregate summary and fourteen
true-improved highlights across the two reviewed parent contexts. The funding-interaction parent added fresh
true-improved evidence for both `zscore(std(close,48),120)` and `zscore(ema(volume,24),120)`, so medium-horizon
realized volatility and shorter smoothed-volume variants remain worth leaving reachable. The two misses,
`zscore(delta(volume,48),120)` and `neg(corr(volume,sub(high,low),96))`, reinforce that volume acceleration and
negative volume/range correlation shapes should remain guarded by exact and sign-aware memory. These artifacts remain
research-only selector evidence and do not admit, publish, or update runtime strategies.

Attempt 45 repeated the same hard-gated conflict-aware memory setup:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence45_conflict_aware_memory_repeat \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke \
  --selector-evidence-path reports/selector_pipeline_evidence_v082_summary
```

Attempt 45 completed successfully and passed the LLM true-improvement hard gate:

- `llm_rewrite_accepted`: `5`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- Candidate verdicts: `improved:3|mixed:1|not_improved:1`
- Candidate highlights: `true_improved:3|sharpe_improved_no_pass_lift:1`
- `llm_true_improved_count`: `3`
- Rewrite events recorded `selector_target_skip:4`, `rewrite_validator:1`, and `llm_rewrite:3`.

The true-improved LLM candidates were:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_ccda5f2f68` | `qr_295d2e9ee2` | `llm_rewrite` | 0.80 | 1.09175843 | BTCUSDT | `zscore(ema(volume,24),120)` |
| `qr_7a765d304b` | `qr_a2cd9fd69f` | `llm_rewrite` | 0.80 | 0.44211152 | BTCUSDT | `zscore(ema(volume,48),120)` |
| `qr_ccda5f2f68` | `qr_b49066f917` | `llm_rewrite` | 0.40 | 0.79389268 | ETHUSDT,SOLUSDT,AVAXUSDT | `zscore(std(close,24),120)` |

The Sharpe-improved candidate without pass-rate lift was:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_4a7fa246c2` | `qr_64c1e0fe44` | `llm_rewrite` | -0.20 | 0.22535215 | BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,AVAXUSDT | `corr(volume,ret(close,12),96)` |

The not-improved LLM candidate was:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_4a7fa246c2` | `qr_a10a67ad28` | `llm_rewrite` | -0.20 | -1.02954010 | BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,AVAXUSDT | `neg(zscore(std(close,48),120))` |

The rewrite validator blocked one exact failed-formula repeat:
`zscore(corr(sub(close,open),volume,48),72)`.

The refreshed attempts 4-45 summary reported:

- Runs: `42`
- LLM policy evidence runs: `39`
- LLM true-improvement evidence runs: `22`
- Runs with coverage-only traps: `3`
- Highlighted candidate rows: `70`
- Distinct highlighted candidates: `42`
- Negative candidate rows: `87`
- Negative candidate family rows: `19`

Interpretation: attempt 45 preserves the same conflict-aware shape. The price-parent
`zscore(ema(volume,48),120)` row now has twelve LLM true-improved highlights in the aggregate summary and fifteen
true-improved highlights across the two reviewed parent contexts. `zscore(ema(volume,24),120)` now repeats for the
funding-interaction parent, while `zscore(std(close,24),120)` adds another lower-horizon volatility-regime repeat.
The Sharpe-only `corr(volume,ret(close,12),96)` row and the failed `neg(zscore(std(close,48),120))` row reinforce that
price-volume correlation and negative volatility-regime signs should remain guarded unless they clear pass-rate lift.
These artifacts remain research-only selector evidence and do not admit, publish, or update runtime strategies.

Attempt 46 repeated the same hard-gated conflict-aware memory setup:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence46_conflict_aware_memory_repeat \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke \
  --selector-evidence-path reports/selector_pipeline_evidence_v082_summary
```

Attempt 46 completed successfully and passed the LLM true-improvement hard gate:

- `llm_rewrite_accepted`: `3`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- `llm_error_count`: `1`
- Candidate verdicts: `improved:2|not_improved:1`
- Candidate highlights: `true_improved:2`
- `llm_true_improved_count`: `2`
- Rewrite events recorded `selector_target_skip:4`, `rewrite_validator:2`, `llm_rewrite:2`, and
  `rewrite_fallback:1`.

The true-improved LLM candidates were:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_ccda5f2f68` | `qr_c3ccb8e228` | `llm_rewrite` | 0.80 | 1.28492586 | AVAXUSDT | `zscore(std(close,48),120)` |
| `qr_ccda5f2f68` | `qr_a2cd9fd69f` | `llm_rewrite` | 0.80 | 1.20859083 | BTCUSDT | `zscore(ema(volume,48),120)` |

The not-improved LLM candidate was:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_7a765d304b` | `qr_ebc90a536a` | `llm_rewrite` | 0.00 | -0.62920208 | BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,AVAXUSDT | `zscore(corr(sub(close,open),volume,72),96)` |

The rewrite validator blocked one exact failed-formula repeat,
`zscore(corr(sub(close,open),volume,48),72)`, plus two depth-5 negative correlation formulas:
`neg(zscore(corr(ret(close,6),std(close,24),72),96))` and
`neg(zscore(corr(ret(close,12),volume,72),120))`.

The refreshed attempts 4-46 summary reported:

- Runs: `43`
- LLM policy evidence runs: `40`
- LLM true-improvement evidence runs: `23`
- Runs with coverage-only traps: `3`
- Highlighted candidate rows: `72`
- Distinct highlighted candidates: `43`
- Negative candidate rows: `88`
- Negative candidate family rows: `19`

Interpretation: attempt 46 is smaller because one target produced only invalid depth-5 formulas, but the accepted LLM
evidence still passed both hard gates. The funding-interaction parent added another true-improved repeat for
`zscore(std(close,48),120)` and a new true-improved parent context for `zscore(ema(volume,48),120)`. The price-parent
`zscore(corr(sub(close,open),volume,72),96)` miss extends the weak longer signed price-volume correlation pattern, and
the rejected depth-5 negative correlation formulas reinforce keeping validator depth limits and sign-aware correlation
memory strict. These artifacts remain research-only selector evidence and do not admit, publish, or update runtime
strategies.

Attempt 47 repeated the same hard-gated conflict-aware memory setup, but failed the LLM policy-evidence gate because
all three LLM requests hit the same transport error:

- Output: `reports/selector_rewrite_pipeline_llm_v082_evidence47_conflict_aware_memory_repeat`
- `llm_rewrite_accepted`: `0`
- `fallback_rewrite_accepted`: `0`
- `allow_local_fallback`: `false`
- `is_llm_policy_evidence`: `false`
- `llm_error_count`: `3`
- Universe, portfolio, portfolio-universe, and review stages were skipped because no candidate formulas were produced.
- Error class: `ConnectionError` from `HTTPSConnectionPool(host='www.kuaiaiapi.com', port=443)` with SSL EOF during
  `/v1/chat/completions`.

Interpretation: attempt 47 is a transport-failure artifact, not selector policy evidence. It is included in the
multi-run audit as a failed LLM-evidence run, but it contributes no candidate review, highlight, or negative-formula
signal. These artifacts remain research-only selector evidence and do not admit, publish, or update runtime strategies.

Attempt 48 repeated the same hard-gated conflict-aware memory setup after the attempt 47 transport failure:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence48_conflict_aware_memory_repeat \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke \
  --selector-evidence-path reports/selector_pipeline_evidence_v082_summary
```

Attempt 48 completed successfully and passed the LLM true-improvement hard gate:

- `llm_rewrite_accepted`: `5`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- Candidate verdicts: `improved:3|not_improved:2`
- Candidate highlights: `true_improved:3`
- `llm_true_improved_count`: `3`
- Rewrite events recorded `selector_target_skip:4`, `llm_rewrite:3`, and `rewrite_validator:1`.

The true-improved LLM candidates were:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_7a765d304b` | `qr_a2cd9fd69f` | `llm_rewrite` | 0.80 | 0.44211152 | BTCUSDT | `zscore(ema(volume,48),120)` |
| `qr_4a7fa246c2` | `qr_e23cfc8ae6` | `llm_rewrite` | 0.60 | 1.06153455 | AVAXUSDT | `zscore(std(close,48),144)` |
| `qr_4a7fa246c2` | `qr_ca1279db8a` | `llm_rewrite` | 0.20 | 0.23343472 | BTCUSDT,SOLUSDT,BNBUSDT | `zscore(sma(volume,24),120)` |

The not-improved LLM candidates were:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_7a765d304b` | `qr_d3a7976c67` | `llm_rewrite` | 0.00 | -0.68440468 | BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,AVAXUSDT | `zscore(delta(volume,36),120)` |
| `qr_ccda5f2f68` | `qr_88f46eeebc` | `llm_rewrite` | 0.00 | -0.64941947 | BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,AVAXUSDT | `neg(zscore(std(close,36),144))` |

The rewrite validator blocked one exact failed-formula repeat:
`zscore(corr(sub(close,open),volume,48),72)`.

The refreshed attempts 4-48 summary reported:

- Runs: `45`
- LLM policy evidence runs: `41`
- LLM true-improvement evidence runs: `24`
- Runs with coverage-only traps: `3`
- Highlighted candidate rows: `75`
- Distinct highlighted candidates: `44`
- Negative candidate rows: `90`
- Negative candidate family rows: `19`

Interpretation: attempt 48 recovered from the attempt 47 transport failure and again strengthened the dominant
positive smoothed-volume signal. The price-parent `zscore(ema(volume,48),120)` row now has thirteen LLM true-improved
highlights in the aggregate summary and sixteen true-improved highlights across the two reviewed parent contexts.
Medium-horizon realized volatility repeated through `zscore(std(close,48),144)` for the funding-interaction parent,
while `zscore(sma(volume,24),120)` added a smaller positive smoothed-volume row. The misses reinforce existing
memory: volume acceleration and negative volatility-regime signs remain weak enough for exact and sign-aware guards,
without blocking the broader positive volume-liquidity or range-volatility families. These artifacts remain
research-only selector evidence and do not admit, publish, or update runtime strategies.

Attempt 49 repeated the same hard-gated conflict-aware memory setup:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence49_conflict_aware_memory_repeat \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke \
  --selector-evidence-path reports/selector_pipeline_evidence_v082_summary
```

Attempt 49 completed successfully and passed the LLM true-improvement hard gate:

- `llm_rewrite_accepted`: `5`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- Candidate verdicts: `improved:4|not_improved:1`
- Candidate highlights: `true_improved:4`
- `llm_true_improved_count`: `4`
- Rewrite events recorded `selector_target_skip:4`, `llm_rewrite:3`, and `rewrite_validator:1`.

The true-improved LLM candidates were:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_ccda5f2f68` | `qr_aded180101` | `llm_rewrite` | 0.80 | 1.10799695 | BTCUSDT | `zscore(ema(volume,24),96)` |
| `qr_7a765d304b` | `qr_a2cd9fd69f` | `llm_rewrite` | 0.80 | 0.44211152 | BTCUSDT | `zscore(ema(volume,48),120)` |
| `qr_ccda5f2f68` | `qr_41f6f43247` | `llm_rewrite` | 0.60 | 1.30535681 | SOLUSDT,AVAXUSDT | `zscore(std(close,36),144)` |
| `qr_4a7fa246c2` | `qr_c3ccb8e228` | `llm_rewrite` | 0.60 | 0.84810419 | AVAXUSDT | `zscore(std(close,48),120)` |

The not-improved LLM candidate was:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_4a7fa246c2` | `qr_1a08a872ec` | `llm_rewrite` | -0.20 | -0.35172888 | BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,AVAXUSDT | `zscore(volume,120)` |

The rewrite validator blocked one exact failed-formula repeat:
`zscore(corr(sub(close,open),volume,48),72)`.

The refreshed attempts 4-49 summary reported:

- Runs: `46`
- LLM policy evidence runs: `42`
- LLM true-improvement evidence runs: `25`
- Runs with coverage-only traps: `3`
- Highlighted candidate rows: `79`
- Distinct highlighted candidates: `45`
- Negative candidate rows: `91`
- Negative candidate family rows: `19`

Interpretation: attempt 49 is a strong positive repeat. The price-parent `zscore(ema(volume,48),120)` row now has
fourteen LLM true-improved highlights in the aggregate summary and seventeen true-improved highlights across the two
reviewed parent contexts. The funding-interaction parent strengthened both shorter smoothed-volume
`zscore(ema(volume,24),96)` and medium-horizon realized-volatility shapes such as `zscore(std(close,36),144)`, while
`zscore(std(close,48),120)` now has four true-improved highlights against the reviewed funding-interaction parent.
The raw `zscore(volume,120)` miss reinforces that the repeated edge is in smoothed/normalized participation variants,
not plain volume level. These artifacts remain research-only selector evidence and do not admit, publish, or update
runtime strategies.

Attempt 50 repeated the same hard-gated conflict-aware memory setup:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence50_conflict_aware_memory_repeat \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke \
  --selector-evidence-path reports/selector_pipeline_evidence_v082_summary
```

Attempt 50 completed successfully and passed the LLM true-improvement hard gate:

- `llm_rewrite_accepted`: `5`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- Candidate verdicts: `improved:5`
- Candidate highlights: `true_improved:5`
- `llm_true_improved_count`: `5`
- Rewrite events recorded `selector_target_skip:4`, `llm_rewrite:3`, and `rewrite_validator:1`.

The true-improved LLM candidates were:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_ccda5f2f68` | `qr_3cdea28d1b` | `llm_rewrite` | 1.00 | 1.20305771 | none | `zscore(ema(volume,36),144)` |
| `qr_7a765d304b` | `qr_a2cd9fd69f` | `llm_rewrite` | 0.80 | 0.44211152 | BTCUSDT | `zscore(ema(volume,48),120)` |
| `qr_ccda5f2f68` | `qr_41f6f43247` | `llm_rewrite` | 0.60 | 1.30535681 | SOLUSDT,AVAXUSDT | `zscore(std(close,36),144)` |
| `qr_4a7fa246c2` | `qr_c3ccb8e228` | `llm_rewrite` | 0.60 | 0.84810419 | AVAXUSDT | `zscore(std(close,48),120)` |
| `qr_4a7fa246c2` | `qr_295d2e9ee2` | `llm_rewrite` | 0.60 | 0.65493676 | BTCUSDT | `zscore(ema(volume,24),120)` |

The rewrite validator blocked one exact failed-formula repeat:
`zscore(corr(sub(close,open),volume,48),72)`.

The refreshed attempts 4-50 summary reported:

- Runs: `47`
- LLM policy evidence runs: `43`
- LLM true-improvement evidence runs: `26`
- Runs with coverage-only traps: `3`
- Highlighted candidate rows: `84`
- Distinct highlighted candidates: `45`
- Negative candidate rows: `91`
- Negative candidate family rows: `19`

Interpretation: attempt 50 is a clean all-improved repeat and the strongest recent confirmation of the conflict-aware
memory posture. The price-parent `zscore(ema(volume,48),120)` row now has fifteen LLM true-improved highlights in the
aggregate summary and eighteen true-improved highlights across the two reviewed parent contexts. The funding-interaction
parent also reinforced `zscore(ema(volume,36),144)`, `zscore(ema(volume,24),120)`, and medium-horizon realized-volatility
shapes including `zscore(std(close,36),144)` and `zscore(std(close,48),120)`. No new negative candidates were added in
this run; exact failed-formula blocking still caught the recurring price-volume correlation repeat. These artifacts
remain research-only selector evidence and do not admit, publish, or update runtime strategies.

Attempt 51 repeated the same hard-gated conflict-aware memory setup:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence51_conflict_aware_memory_repeat \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke \
  --selector-evidence-path reports/selector_pipeline_evidence_v082_summary
```

Attempt 51 completed successfully and passed the LLM true-improvement hard gate:

- `llm_rewrite_accepted`: `4`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- Candidate verdicts: `improved:3|not_improved:1`
- Candidate highlights: `true_improved:3`
- `llm_true_improved_count`: `3`
- Rewrite events recorded `selector_target_skip:4`, `llm_rewrite:3`, and `rewrite_validator:2`.

The true-improved LLM candidates were:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_ccda5f2f68` | `qr_585c6f8fcd` | `llm_rewrite` | 1.00 | 1.48620762 | none | `zscore(ema(volume,96),192)` |
| `qr_7a765d304b` | `qr_a2cd9fd69f` | `llm_rewrite` | 0.80 | 0.44211152 | BTCUSDT | `zscore(ema(volume,48),120)` |
| `qr_4a7fa246c2` | `qr_aded180101` | `llm_rewrite` | 0.60 | 0.67117528 | BTCUSDT | `zscore(ema(volume,24),96)` |

The not-improved LLM candidate was:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_4a7fa246c2` | `qr_e2186d7430` | `llm_rewrite` | 0.00 | -0.25845276 | BTCUSDT,ETHUSDT,BNBUSDT,AVAXUSDT | `zscore(sub(high,low),96)` |

The rewrite validator blocked one exact failed-formula repeat:
`zscore(corr(sub(close,open),volume,48),72)`.

It also rejected one over-depth negative realized-volatility formula:
`neg(zscore(std(ret(close,6),36),120))`.

The refreshed attempts 4-51 summary reported:

- Runs: `48`
- LLM policy evidence runs: `44`
- LLM true-improvement evidence runs: `27`
- Runs with coverage-only traps: `3`
- Highlighted candidate rows: `87`
- Distinct highlighted candidates: `46`
- Negative candidate rows: `92`
- Negative candidate family rows: `19`

Interpretation: attempt 51 keeps the selector evidence moving in the same direction. The price-parent
`zscore(ema(volume,48),120)` row now has sixteen LLM true-improved highlights in the aggregate summary and nineteen
true-improved highlights across the two most repeated reviewed parent contexts. Including the isolated
funding-interaction repeat from attempt 46, the same formula now has twenty true-improved highlights across all reviewed
parent contexts. Attempt 51 also added the first slow smoothed-volume highlight,
`zscore(ema(volume,96),192)`, with a full pass-rate lift against the funding-volume parent, and strengthened
`zscore(ema(volume,24),96)` against the funding-interaction parent. The raw range candidate
`zscore(sub(high,low),96)` missed, so range evidence remains conflict-aware and shape-specific rather than a broad
plain-range endorsement. These artifacts remain research-only selector evidence and do not admit, publish, or update
runtime strategies.

Attempt 52 repeated the same hard-gated conflict-aware memory setup:

```bash
.venv/bin/python scripts/run_selector_rewrite_pipeline.py \
  --selector reports/candidate_selector_archive_eval \
  --out reports/selector_rewrite_pipeline_llm_v082_evidence52_conflict_aware_memory_repeat \
  --config configs/btcusdt.yaml \
  --config configs/ethusdt.yaml \
  --config configs/solusdt.yaml \
  --config configs/bnbusdt.yaml \
  --config configs/avaxusdt.yaml \
  --use-llm \
  --llm-only \
  --require-llm-evidence \
  --require-llm-true-improvement \
  --max-targets 3 \
  --candidates-per-target 2 \
  --failure-memory-path reports/failure_memory_smoke \
  --selector-evidence-path reports/selector_pipeline_evidence_v082_summary
```

Attempt 52 completed successfully and passed the LLM true-improvement hard gate:

- `llm_rewrite_accepted`: `5`
- `fallback_rewrite_accepted`: `0`
- `is_llm_policy_evidence`: `true`
- Candidate verdicts: `improved:3|not_improved:2`
- Candidate highlights: `true_improved:3`
- `llm_true_improved_count`: `3`
- Rewrite events recorded `selector_target_skip:4`, `llm_rewrite:3`, and `rewrite_validator:1`.

The true-improved LLM candidates were:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_ccda5f2f68` | `qr_295d2e9ee2` | `llm_rewrite` | 0.80 | 1.09175843 | BTCUSDT | `zscore(ema(volume,24),120)` |
| `qr_7a765d304b` | `qr_a2cd9fd69f` | `llm_rewrite` | 0.80 | 0.44211152 | BTCUSDT | `zscore(ema(volume,48),120)` |
| `qr_ccda5f2f68` | `qr_fcc0b75150` | `llm_rewrite` | 0.60 | 1.09772214 | SOLUSDT,AVAXUSDT | `zscore(std(close,36),120)` |

The not-improved LLM candidates were:

| Parent | Candidate | Source | Pass Rate Delta | Mean Sharpe Delta | Failed Assets | Formula |
|---|---|---|---:|---:|---|---|
| `qr_4a7fa246c2` | `qr_ebc90a536a` | `llm_rewrite` | -0.20 | -0.29954444 | BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,AVAXUSDT | `zscore(corr(sub(close,open),volume,72),96)` |
| `qr_4a7fa246c2` | `qr_903b1672ff` | `llm_rewrite` | -0.20 | -1.24060683 | BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,AVAXUSDT | `neg(zscore(std(close,48),144))` |

The rewrite validator blocked one exact failed-formula repeat:
`zscore(corr(sub(close,open),volume,48),72)`.

The refreshed attempts 4-52 summary reported:

- Runs: `49`
- LLM policy evidence runs: `45`
- LLM true-improvement evidence runs: `28`
- Runs with coverage-only traps: `3`
- Highlighted candidate rows: `90`
- Distinct highlighted candidates: `46`
- Negative candidate rows: `94`
- Negative candidate family rows: `19`

Interpretation: attempt 52 is another positive smoothed-volume repeat with a useful negative-memory check. The
price-parent `zscore(ema(volume,48),120)` row now has seventeen LLM true-improved highlights in the aggregate summary,
twenty true-improved highlights across the two most repeated reviewed parent contexts, and twenty-one across all
reviewed parent contexts. Funding-interaction parent evidence also strengthened `zscore(ema(volume,24),120)` and made
`zscore(std(close,36),120)` a repeated true-improved volatility-regime shape. The misses on
`zscore(corr(sub(close,open),volume,72),96)` and `neg(zscore(std(close,48),144))` reinforce that longer signed
price-volume correlation and negative volatility-regime signs remain weak. These artifacts remain research-only
selector evidence and do not admit, publish, or update runtime strategies.
