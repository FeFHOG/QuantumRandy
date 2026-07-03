# Research v1.3 Paper Observation Protocol

Date: 2026-07-04

Status: ready protocol, not started.

This protocol describes how to observe the manually reviewed v1.3 funding-adjacent survivor on paper. It is not a
runtime publish payload, not live trading, not RandyPortfolio, and not factor admission.

## Protocol Verdict

```text
research_v1_3_paper_observation_protocol_ready_not_started
```

The protocol is ready to execute after an explicit paper-observation start decision. The remaining work before a third
project is time-based observation and a final launch gate, not more current-DSL mining.

## Candidate Under Observation

Primary candidate:

```text
candidate_id: qr_v13_funding_range_norm_001
variant_id: thr_0p0_long_short_cap_0p5_calm_vol_lte_1p5
scope: BTCUSDT_4h
formula: neg(zscore(div(ema(funding_rate,12),div(sub(max(high,96),min(low,96)),close)),120))
```

Paired diagnostic candidate:

```text
candidate_id: qr_v13_funding_range_norm_001
variant_id: thr_0p0_long_flat_cap_0p5_calm_vol_lte_1p5
scope: BTCUSDT_4h
formula: neg(zscore(div(ema(funding_rate,12),div(sub(max(high,96),min(low,96)),close)),120))
```

The primary candidate has stronger validation and blind Sharpe. The paired diagnostic has lower worst drawdown. They
should be observed together as two views of the same family, not as independent evidence.

## Observation Objective

Observe whether v1.3's range-normalized funding pressure edge behaves consistently on fresh BTCUSDT 4h bars without
changing the formula, variant definition, exposure cap, scope, or review rules.

The observation should answer:

- Does the candidate continue to behave like a funding-pressure locality signal?
- Do blind weakness and validation weakness labels worsen on fresh bars?
- Does drawdown remain inside the robustness envelope?
- Do diagnostics remain diagnostic rather than becoming a portability claim?
- Is the evidence stable enough to justify a third-project planning document?

## Frozen Rules

- Scope: `BTCUSDT_4h`.
- Out-of-scope assets: diagnostics only.
- Candidate family: `funding_pressure_normalization`.
- Formula: frozen exactly as exported by v1.3.
- Variants: the two listed above only.
- Exposure cap: `0.5`.
- Volatility cap: `calm_vol_lte_1p5`.
- No formula rewrite during observation.
- No new formula base fields during observation.
- No automatic fallback to the Research 1.0 survivor.

## Minimum Observation Window

Recommended minimum:

```text
30 calendar days or at least 120 fresh BTCUSDT 4h bars, whichever is longer.
```

The observation can be extended if the market is inactive, the data feed is unstable, or fewer than 20 non-flat signal
events occur.

## Required Daily Record

Each daily paper note should record:

- latest BTCUSDT 4h bar count since observation start;
- primary and paired diagnostic candidate signal values;
- simulated paper exposure intent under the frozen variant rule;
- paper equity, drawdown, realized fees, and funding impact if a local paper runner is used;
- whether any data gap, formula parse issue, or delayed funding update occurred;
- whether any boundary exception was attempted.

## Pass Conditions

Paper observation can pass only if all are true:

- no runtime boundary violation occurs;
- no formula or variant mutation occurs;
- no data integrity failure remains unresolved;
- maximum observed drawdown remains within the v1.3 robustness envelope;
- paper behavior remains explainable as funding-pressure locality;
- the primary candidate remains at least directionally consistent with its v1.3 evidence;
- paired diagnostic behavior does not contradict the primary candidate's rationale;
- final manual review still classifies the evidence as research-only.

## Fail Conditions

Paper observation fails if any are true:

- data gaps make the observation unrecoverable;
- drawdown exceeds the robustness envelope without a documented external data issue;
- the candidate needs formula edits or parameter tuning to remain viable;
- the candidate only works by switching scope or importing new base fields;
- diagnostics are mistakenly treated as all-asset approval;
- any runtime factor publication, live order path, private-key path, or automatic admission path is introduced.

## Outputs To Produce After Observation

- `docs/RESEARCH_V1_3_PAPER_OBSERVATION_REPORT.md`.
- A daily paper-observation note directory under ignored `reports/`, if a paper runner is used.
- A final go/no-go decision for third-project planning.

The paper-observation report should decide one of:

```text
research_v1_3_paper_observation_pass_ready_for_third_project_planning
research_v1_3_paper_observation_extend
research_v1_3_paper_observation_fail_return_to_research
```

## Boundary Confirmation

- No RandyPortfolio implementation.
- No live trading.
- No exchange private keys.
- No runtime factor publishing.
- No automatic factor admission.
- No production runtime regime labels.
- No new formula base fields.
- No selector evidence61.
