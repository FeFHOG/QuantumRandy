# Pre-Third-Project Readiness Report

Date: 2026-07-04

Status: pre-third-project preparation is almost complete; third project is not started.

This report closes the documentation and evidence package needed before opening a third project such as
RandyPortfolio. It does not create RandyPortfolio, does not publish runtime factors, and does not approve live trading.

## Current Verdict

```text
pre_third_project_ready_except_paper_observation_execution
```

The remaining blocker before a third project is not another current-DSL search. It is a time-based paper observation
gate for the manually reviewed v1.3 survivor family, followed by one final launch decision.

## Completed Before Third Project

| Area | Status | Evidence |
|---|---|---|
| Research 1.0 checkpoint | Complete | `docs/RESEARCH_1_0_CHECKPOINT_REPORT.md` |
| Independent non-funding replication attempt | Complete clean negative | `docs/RESEARCH_V1_1_INDEPENDENT_SCOPED_FAMILY_REPLICATION_REPORT.md` |
| Failure-guided non-funding re-spec | Complete clean negative | `docs/RESEARCH_V1_2_FAILURE_GUIDED_SCOPED_RESPEC_REPORT.md` |
| Funding-adjacent locality probe | Complete with survivor | `docs/RESEARCH_V1_3_FUNDING_ADJACENT_SCOPED_RESPEC_REPORT.md` |
| v1.3 manual review | Complete | `docs/RESEARCH_V1_3_MANUAL_REVIEW_REPORT.md` |
| Paper observation protocol | Ready, not started | `docs/RESEARCH_V1_3_PAPER_OBSERVATION_PROTOCOL.md` |
| Paper observation starter packet | Scripted, not started | `scripts/prepare_v1_3_paper_observation.py` |
| Stack boundary | Current | `docs/RANDY_STACK_TARGET_ARCHITECTURE.md` |

## Evidence Position

The stack now has:

- one Research 1.0 scoped funding-return survivor;
- two failed independent non-funding replication passes;
- one v1.3 funding-adjacent survivor family with two robust variants;
- explicit failure memory for failed v1.3 variants;
- declared-scope RandysLab review with BTC primary evidence and ETH/SOL/BNB/AVAX diagnostics;
- a clear architecture boundary that keeps QuantumRandy as factor factory and RandysLab as strict judge.

The stack still does not have:

- an independent non-funding second family;
- paper observation of the v1.3 survivor on fresh bars;
- evidence that portfolio-layer allocation is stable;
- a production regime classifier;
- any approval to publish runtime factors or open live execution.

## Third Project Launch Gate

A third project may be planned only after a paper-observation report chooses:

```text
research_v1_3_paper_observation_pass_ready_for_third_project_planning
```

Even then, the first third-project artifact should be an interface and requirements document, not an implementation of
allocation, scheduling, live execution, or exchange integration.

## Recommended Third-Project Scope When Eligible

If the paper gate passes, the initial third-project scope should be:

- repository name reserved conceptually as `RandyPortfolio`;
- interface-first design only;
- consume research-only QuantumRandy factor artifacts;
- submit portfolio or signal-bundle proposals back to RandysLab for strict judgment;
- preserve all paper-only and no-live-execution boundaries;
- avoid owning formula mining, strict backtest internals, or exchange adapters.

The initial third-project scope should not include:

- live order placement;
- exchange private keys;
- automatic factor admission;
- production regime labels;
- dynamic capital allocation beyond documented paper proposals;
- mutation of QuantumRandy runtime manifests;
- migration of QuantumRandy or RandysLab internals.

## Remaining Work Before Opening The Third Project

Only these gates remain:

1. Run `python scripts/prepare_v1_3_paper_observation.py` to create the ignored starter packet.
2. Execute the v1.3 paper-observation protocol for the required minimum window.
3. Write `docs/RESEARCH_V1_3_PAPER_OBSERVATION_REPORT.md`.
4. Run a final boundary and repository audit.
5. Decide whether to open RandyPortfolio planning, extend observation, or return to research.

## Boundary Confirmation

- No RandyPortfolio implementation.
- No new repository was created.
- No live trading.
- No exchange private keys.
- No runtime factor publishing.
- No automatic factor admission.
- No production runtime regime labels.
- No new formula base fields.
- No selector evidence61.
