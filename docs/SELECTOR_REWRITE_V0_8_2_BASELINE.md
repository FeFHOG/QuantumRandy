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
