# Selector Rewrite v0.8.2 Milestone Review

Date: 2026-07-02

Scope: selector rewrite evidence attempts 4-60, summarized in
`reports/selector_pipeline_evidence_v082_summary`.

This is a research-only milestone review. It is not an admission decision, runtime publish payload, portfolio
construction step, or live execution plan.

## Stop Condition

The hard-gated selector repeat loop is stopped at evidence60. Do not run evidence61 unless explicitly requested.

Aggregate state through evidence60:

- Runs: `57`
- LLM policy evidence runs: `53`
- LLM true-improvement evidence runs: `35`
- Coverage-only trap runs: `4`
- Highlighted candidate rows: `115`
- Distinct highlighted candidates: `52`
- Negative candidate rows: `109`
- Negative candidate family rows: `19`

## Top Repeated True-Improved Candidates

| Parent | Formula | LLM true-improved rows | Best pass-rate delta | Best mean-Sharpe delta | Read |
|---|---|---:|---:|---:|---|
| `qr_7a765d304b` | `zscore(ema(volume,48),120)` | 19 | 0.80 | 0.44211152 | Dominant repeated selector winner. |
| `qr_ccda5f2f68` | `zscore(ema(volume,24),96)` | 5 | 0.80 | 1.10799695 | Strong funding-interaction replacement. |
| `qr_4a7fa246c2` | `zscore(std(close,48),120)` | 5 | 0.60 | 0.84810419 | Robust positive volatility-regime replacement. |
| `qr_4a7fa246c2` | `zscore(ema(volume,48),120)` | 5 | 0.60 | 0.77176916 | Confirms the dominant volume shape outside the price parent. |
| `qr_4a7fa246c2` | `zscore(ema(volume,24),120)` | 5 | 0.60 | 0.65493676 | Shorter smoothed participation also repeats. |
| `qr_ccda5f2f68` | `zscore(ema(volume,36),144)` | 4 | 1.00 | 1.20305771 | High-confidence participation variant. |
| `qr_ccda5f2f68` | `zscore(std(close,48),120)` | 4 | 0.80 | 1.28492586 | Funding-interaction parent also likes realized volatility. |
| `qr_ccda5f2f68` | `zscore(std(close,36),144)` | 4 | 0.60 | 1.30535681 | Useful shape-specific volatility-regime variant. |

The strongest repeated economic theme is positive smoothed volume participation. The second theme is positive realized
volatility-regime state. These are not portfolio decisions; they are factor-factory candidates for stricter judging.

## Parent-Context Winners

### `qr_7a765d304b`

Parent formula: `zscore(sub(sma(close,12),sma(close,48)),48)`.

Best replacement:

- `zscore(ema(volume,48),120)` with `19` LLM true-improved rows.

Interpretation: the weak price-spread parent is most consistently rescued by a smoothed participation state, not by
more signed price-volume correlation.

### `qr_4a7fa246c2`

Parent formula: `neg(zscore(div(funding_rate,std(close,48)),120))`.

Best replacement cluster:

- `zscore(std(close,48),120)` with `5` LLM true-improved rows.
- `zscore(ema(volume,48),120)` with `5` LLM true-improved rows.
- `zscore(ema(volume,24),120)` with `5` LLM true-improved rows.
- `zscore(std(close,48),144)` with `4` LLM true-improved rows.

Interpretation: the failed negative funding/volatility construction should be replaced by positive participation or
positive realized-volatility state, not by negative volatility or negative range-volume signs.

### `qr_ccda5f2f68`

Parent formula: `zscore(corr(funding_rate,volume,48),96)`.

Best replacement cluster:

- `zscore(ema(volume,24),96)` with `5` LLM true-improved rows.
- `zscore(ema(volume,36),144)` with `4` LLM true-improved rows.
- `zscore(std(close,48),120)` with `4` LLM true-improved rows.
- `zscore(std(close,36),144)` with `4` LLM true-improved rows.
- `zscore(ema(volume,48),120)` with `3` LLM true-improved rows.

Interpretation: funding-interaction parents repeatedly improve when rewritten into standalone participation or
standalone volatility-regime states. The signal should not be interpreted as evidence for raw funding interaction.

## Top Negative Candidate Families

| Parent family | Candidate family | Negative rows | True-improved rows | Worst mean-Sharpe delta | Example weak shape |
|---|---:|---:|---:|---:|---|
| `price` | `volume_liquidity` | 19 | 23 | -2.06273192 | `neg(zscore(volume,96))` |
| `funding_interaction` | `range_volatility` | 19 | 36 | -1.68629608 | `neg(zscore(sub(high,low),120))` |
| `funding_interaction` | `volume_liquidity` | 15 | 40 | -0.55994105 | `zscore(delta(volume,48),120)` |
| `pure_funding` | `volume_liquidity` | 5 | 0 | -1.47893646 | `neg(zscore(delta(volume,24),120))` |
| `pure_funding` | `pure_funding` | 5 | 0 | -0.96723150 | `neg(zscore(sma(funding_rate,96),192))` |
| `volume_liquidity` | `pure_funding` | 5 | 0 | -0.64920061 | `neg(zscore(sma(funding_rate,72),168))` |
| `price` | `range_volatility` | 4 | 0 | -2.42479556 | `neg(zscore(sub(high,low),96))` |
| `pure_funding` | `price` | 4 | 0 | -1.99001275 | `zscore(sub(close,open),96)` |

Negative evidence is strongest for raw or negative-sign variants: negative volume, negative volatility/range, raw signed
price-volume correlation, and pure funding carry rewrites.

## Conflict-Aware Families

Do not globally block these families:

- `funding_interaction -> volume_liquidity`
- `funding_interaction -> range_volatility`
- `price -> volume_liquidity`

Each has both many negative rows and many true-improved rows. The conflict is shape-specific:

- Positive smoothed participation is strong.
- Raw volume, volume acceleration, and negative volume signs are weak.
- Positive realized-volatility state is often useful.
- Negative range-volatility and negative volatility-regime signs are weak.
- Raw signed price-volume correlation is unstable, but early narrower normalized versions had limited positive evidence.

The next selector memory should remain sign-aware and formula-shape-aware rather than family-ban-driven.

## Saturation Decision

Marginal repeat evidence is saturated enough to stop the loop.

Evidence:

- Attempts 50-60 produced `33` true-improved rows across `11` runs.
- Only `2` true-improved formulas first appeared in attempts 50-60.
- Attempts 55-60 produced `14` true-improved rows but only `1` first-seen formula.
- Most recent positive rows reinforced already-known participation and volatility-regime shapes.

Decision: stop selector repeats at evidence60 and move to candidate export plus stricter external judging.

## Factor-Candidate Export Schema

Next phase should export individual factor candidates from QuantumRandy as research-only artifacts for RandysLab-style
strict judging. Recommended artifact: JSONL plus CSV mirror under a reports path such as
`reports/factor_candidate_exports/selector_v082_milestone_4_60/`.

Recommended fields:

| Field | Type | Purpose |
|---|---|---|
| `artifact_type` | string | `quantumrandy_factor_candidate_export` |
| `schema_version` | integer | Start with `1`. |
| `research_only` | boolean | Must be `true`. |
| `not_runtime_publish_payload` | boolean | Must be `true`. |
| `candidate_id` | string | Stable factor id, for example `qr_a2cd9fd69f`. |
| `formula` | string | Alpha formula only, no portfolio instruction. |
| `formula_family` | string | `volume_liquidity`, `range_volatility`, `price`, etc. |
| `generation_source` | string | Usually `llm_rewrite`. |
| `selector_evidence_window` | string | Example: `attempts_4_60`. |
| `parent_factor_id` | string | Selector parent context. |
| `parent_formula` | string | Failed or weak parent formula. |
| `parent_formula_family` | string | Parent family for conflict-aware memory. |
| `llm_true_improved_count` | integer | Count from aggregate evidence. |
| `highlight_count` | integer | All highlight rows. |
| `coverage_only_trap_count` | integer | Trap count for caution. |
| `sharpe_improved_no_pass_lift_count` | integer | Mixed signal count. |
| `best_pass_rate_delta` | number | Best selector-review delta. |
| `best_mean_sharpe_delta` | number | Best selector-review delta. |
| `mean_pass_rate_delta` | number | Aggregate selector-review mean. |
| `mean_sharpe_delta` | number | Aggregate selector-review mean. |
| `failed_assets_examples` | string/list | Repeated weak assets from selector review. |
| `negative_family_conflict` | boolean | True when family has both positive and negative evidence. |
| `conflict_notes` | string | Sign/window/family cautions. |
| `required_features` | array | `close`, `volume`, `funding_rate`, etc. |
| `candidate_tier` | string | Suggested tiers: `primary`, `secondary`, `exploratory`, `do_not_export`. |
| `randyslab_eval_profile` | string | Suggested strict judge profile, for example `strict4h_v1`. |
| `created_from_report` | string | Path to the aggregate evidence summary. |

Initial primary export candidates should include the strongest repeated standalone formulas, not every highlighted row:

- `zscore(ema(volume,48),120)`
- `zscore(ema(volume,24),96)`
- `zscore(ema(volume,24),120)`
- `zscore(ema(volume,36),144)`
- `zscore(std(close,48),120)`
- `zscore(std(close,48),144)`
- `zscore(std(close,36),144)`

## Crypto-Native Feature Recommendation

Add crypto-native public-data features in the next research phase, but keep them out of runtime execution and private
exchange connectivity.

Recommended feature candidates:

- Open interest: useful for leverage crowding, participation confirmation, and distinguishing spot-led from perp-led moves.
- Basis or perp-spot premium: useful for carry/crowding context beyond raw funding rate.
- Liquidation prints: useful for separating forced deleveraging volatility from organic participation.
- Taker buy/sell imbalance: useful for directional aggressor flow, especially as an alternative to candle-body volume correlation.

Constraints:

- Public or purchased research data only; no exchange private keys.
- All features must be available in RandysLab with T+1/next-bar alignment before being trusted.
- Missing data, exchange coverage changes, and survivorship must be explicit failure reasons.
- Feature candidates should be exported as research formulas, not runtime strategies.

## Next Phase Recommendation

Move from selector repetition to factor-candidate export and strict judging:

1. Freeze selector repeat evidence at attempts 4-60.
2. Build a research-only export artifact from the primary and secondary candidate list.
3. Evaluate exported candidates in RandysLab with strict 4h matching, fees, funding, slippage, ledger, metrics, and failure reasons.
4. Add public crypto-native features only after data readiness and alignment checks.
5. Keep RandyPortfolio postponed until candidate-level judging produces enough stable, independent factors.
