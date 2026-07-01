# Randy Quant Stack Maturity Status

Last updated: 2026-06-30

This note summarizes where QuantumRandy and RandysLab stand after the v0.8 beta application-layer work. It is a product
and research maturity view, not a trading-performance claim.

## Short Verdict

The Randy quant stack is now a paper-only v0.8 beta system with a usable research pipeline and a deployable observation
runtime. It is past the prototype-script stage, but it is not a proven production trading system.

- Application layer: beta-ready for a 48-hour paper observation trial.
- Algorithm layer: research alpha / early beta, with promising scaffolding but not enough evidence for strategy claims.
- Live trading: not implemented and not authorized.

## Application Layer

Current maturity: v0.8 beta readiness.

Implemented:

- deterministic paper runtime server;
- public Binance 4h feeder;
- monitor and daily runtime report;
- read-only runtime dashboard;
- server preflight;
- generation-guarded manual factor publisher;
- local end-to-end paper trial runner;
- RandysLab baseline export integration for runtime and portfolio reports;
- explicit safety boundary separating research, runtime, publishing, and future execution planning.

What this means:

- The stack can ingest real public BTCUSDT 4h data and observe approved paper strategies.
- Runtime reports can compare paper results against RandysLab baseline/control artifacts.
- Active runtime strategy changes require a manual publisher or explicit review flow.
- The first server task is operational validation, not algorithm improvement.

Remaining application risks:

- 48-hour server paper trial has not completed yet.
- Process restart behavior, stale-bar behavior, and log/report persistence still need real server evidence.
- Runtime blend monitoring is present, but factor-decay and promotion evidence dashboards are still thin.
- There is no production process manager configuration yet beyond the first-trial tmux runbook.

## Algorithm Layer

Current maturity: research alpha / early beta.

Implemented:

- formula DSL and strict 4h perpetual futures backtest;
- LLM plus MCTS factor proposal loop;
- local proposal fallback;
- formula shape limits and complexity penalty;
- four-gate brutal filter;
- blind validation support;
- walk-forward validation;
- multi-asset robustness evaluator;
- first fixed-weight portfolio research builder;
- portfolio contribution/ablation report;
- portfolio-level fixed-blend walk-forward validation;
- RandysLab baseline comparison in portfolio research;
- LLM proposal schema v2 fields for hypothesis, expected edge, expected failure mode, and rewrite plan;
- research-only candidate selector that combines leaderboard, universe robustness, portfolio-universe robustness, and
  failure-memory evidence into rewrite, deprioritize, and needs-evidence queues.

What this means:

- The research system can generate, evaluate, filter, validate, and package factor candidates.
- The portfolio layer can build equal-weight, rank-IC-weighted, and Sharpe-weighted research-only blends.
- LLM proposals now preserve enough research intent to support future failure memory and targeted rewrites.

Remaining algorithm risks:

- Multi-asset evaluation exists, but broader BTC/ETH/SOL/BNB/AVAX data coverage and repeated runs are still needed.
- Portfolio construction is fixed-weight and offline; fixed-blend walk-forward exists, but no walk-forward retraining of
  weights yet.
- Factor admission policy has a first research-only implementation and can ingest factor-level and portfolio-level
  walk-forward evidence; the mining dashboard can summarize admission, failure-cluster, and portfolio walk-forward
  artifacts in a read-only review panel.
- Failure memory has a first artifact builder and prompt-context integration, but richer retrieval and dashboard views
  are still pending.
- Candidate selection can now flag weak cross-asset formulas before more rewrite effort is spent, but it remains an
  offline research triage artifact rather than an automated mining or promotion gate.
- Pareto MCTS archive exists as a research review artifact; MCTS acquisition still uses the scalar reward.
- DSL still uses a compact OHLCV/funding field set; open interest, basis, taker flow, liquidation, and cross-asset fields
  remain future work.
- Current results are research artifacts, not evidence of deployable edge.

## Current Phase Map

- Phase 0 boundary freeze: complete.
- Phase 1 minimum paper loop: implemented and locally verified.
- Phase 2 server trial: ready for the server agent, not completed.
- Phase 3 manual publishing flow: first implementation complete.
- Phase 4 multi-factor portfolio layer: first offline implementation complete; runtime promotion remains manual.
- Phase 5 algorithm upgrades: schema-v2 proposals, failure memory, admission, candidate selector, portfolio
  walk-forward, dashboard review, and first Pareto archive are implemented; richer Pareto-guided acquisition is still
  pending.
- Phase 6 live execution: planning only; no live execution code should be added in v0.8.

## Practical Next Steps

While the server agent handles the 48-hour paper trial:

1. Keep active runtime strategies frozen unless fixing runtime bugs.
2. Continue algorithm work in research-only artifacts.
3. Formalize a factor admission policy that combines brutal filter, blind validation, walk-forward survival, multi-asset
   robustness, correlation, turnover, and drawdown.
4. Feed candidate selector rewrite targets and evidence gaps into the next research-only LLM rewrite or universe
   evaluation batch.
5. Build failure memory from rejected candidates and schema-v2 proposal fields.
6. Expand review panels with deeper drill-downs and artifact freshness checks.
7. Prepare v0.8 beta release notes only after the server trial result is known.

The useful mental model: the lab bench and observation chamber now exist. The scientist still needs stronger evidence
discipline before any strategy can be called mature.
