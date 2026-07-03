# QuantumRandy + RandysLab Server Paper Roadmap

Last updated: 2026-06-30

This document records the application-layer plan for running QuantumRandy and RandysLab on a server without live
exchange trading. The goal is to build a safe, long-running paper observation system fed by real market data, while
keeping factor mining and algorithm research isolated enough that they can continue to evolve.

## Safety Boundary

- No live orders.
- No exchange API keys with trading permissions.
- Runtime receives public market data only.
- Runtime simulates strategy equity and exposure with capped paper capital.
- Research/mining may create candidate factors, but candidates must not automatically become active paper strategies.
- Factor promotion into the runtime should be manual at first, generation-guarded, and fully logged.
- Future live execution may be planned only as a separate, explicitly reviewed execution adapter after the multi-factor
  paper strategy layer is stable. This roadmap reserves that interface conceptually; it does not authorize live trading
  code in the current runtime.

## Project Roles

### RandysLab

RandysLab should be used as the baseline and data utility layer:

- fetch and maintain Binance historical OHLCV/funding data;
- provide traditional baseline strategies such as EMA, Bollinger, and funding-deviation logic;
- run parameter-search and robustness checks for non-LLM strategies;
- act as the benchmark floor for QuantumRandy factors;
- provide a sanity reference for execution costs and strict 4h backtest assumptions.

RandysLab should not become the LLM factor-mining engine. It is the baseline/control group.

### QuantumRandy

QuantumRandy should remain the formulaic alpha research and paper runtime system:

- mine symbolic factors with LLM + MCTS;
- evaluate factors through strict cost-aware backtests;
- run brutal filter, blind validation, walk-forward validation, and multi-asset robustness checks;
- publish approved factors into a deterministic runtime manifest;
- receive real 4h bars in the runtime server and track paper performance.

### Runtime / Paper Layer

The runtime layer should be conservative:

- execute only approved factors and fixed-weight or prebuilt multi-factor strategies;
- accept normalized real market bars from a separate feeder;
- expose `/health`, `/v1/factors`, and `/v1/snapshot`;
- support token-protected hot updates;
- avoid LLM, MCTS, exchange order routing, or strategy discovery code.

## Recommended Architecture

Keep one repository for now. Do not split into separate repos yet.

Use separate processes and clear interfaces:

```text
Process A: runtime_server
  - stable paper execution
  - receives pushed real K-line bars
  - serves snapshots and strategy paper metrics

Process B: market_feeder
  - pulls Binance 4h OHLCV and funding data
  - normalizes data
  - posts bars to runtime_server
  - no strategy logic

Process C: research_miner
  - runs QuantumRandy LLM/MCTS mining
  - writes research reports and leaderboards
  - does not directly mutate runtime factors

Process D: factor_publisher
  - reads approved research artifacts
  - builds runtime_factors.json updates
  - calls runtime hot-update API with generation guard
  - manual confirmation at first

Process E: monitor/reporter
  - polls runtime snapshots
  - writes daily paper reports
  - alerts on stale bars, process failures, and abnormal drawdown

Future Process F: execution_adapter (not in current beta)
  - consumes only approved multi-factor target exposures after paper validation
  - owns broker/exchange connectivity behind a separate permission boundary
  - requires explicit kill switch, dry-run mode, order caps, audit logs, and operator approval
  - must not import LLM, MCTS, mining, or automatic factor promotion code
```

Physical repo split can wait until runtime is stable for several weeks. A future split may look like:

```text
quantumrandy-core      # DSL, factor evaluation, metrics, manifest schema
QuantumRandyResearch   # LLM/MCTS mining, validation, portfolio research
QuantumRandyRuntime    # feeder, runtime server, monitor, paper reports
RandysLab              # baseline strategies and data utilities
```

Do not split now unless dependency or deployment pain becomes real.

## Server Agent Handoff

The server agent should operate only from explicit deployment instructions. It should not improvise live-trading
features.

The minimal operational handoff is maintained in `SERVER_AGENT_DEPLOYMENT.md`.

### Must Not Do

- Do not add exchange order placement.
- Do not add private trading API keys.
- Do not expose runtime admin endpoints to the public internet.
- Do not auto-promote newly mined factors into active runtime strategies.
- Do not change research algorithms while the paper runtime process is being debugged.

### First Deployment Target

Run a minimal paper observation system:

1. Start `runtime_server` bound to `127.0.0.1` or private network only.
2. Start a Binance 4h market feeder.
3. Feed BTCUSDT OHLCV plus funding rate into runtime.
4. Run 2-5 approved factors plus one simple multi-factor blend.
5. Poll `/v1/snapshot` and write daily paper reports.
6. Keep RandysLab baseline results nearby for comparison.

### Server Environment

Recommended server baseline:

- Ubuntu 22.04 or newer;
- Python 3.10+;
- long-running process manager such as `systemd`, `supervisor`, or `tmux` for the first trial;
- no trading credentials;
- outbound network access to public market-data endpoints and LLM provider if mining runs on the server;
- persistent storage for reports, snapshots, logs, and downloaded market data.

### Deployment Commands

Current runtime server startup is documented in `RUNTIME_SERVER.md`.

Expected first commands:

```bash
cd QuantumRandy
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export QUANTUMRANDY_ADMIN_TOKEN='long-random-admin-token'
export QUANTUMRANDY_INGEST_TOKEN='long-random-ingest-token'
python scripts/runtime_server.py --config configs/runtime_server.yaml
```

The market feeder script is `scripts/binance_feeder.py`. It should:

- pull recent BTCUSDT 4h kline candles;
- pull the latest funding rate or funding history aligned to the 4h bar;
- post one or more bars to `/v1/market/bars`;
- re-post the current unfinished candle safely, since runtime de-duplicates by timestamp;
- log every accepted timestamp;
- alert if no new completed 4h bar arrives on schedule.

Current default behavior is more conservative than the full wish list above: it posts only completed 4h candles unless
`include_unclosed` is enabled in `configs/binance_feeder.yaml`.

The monitor/reporter script is `scripts/runtime_monitor.py`. It polls `/health` and `/v1/snapshot`, writes
`snapshots.jsonl`, writes `latest_snapshot.json`, and renders `runtime_report_YYYYMMDD.md` under
`reports/runtime_live/`.

The manual publisher script is `scripts/publish_factors.py`. It reads a research `leaderboard.json`, selects passed
factors, writes a complete runtime update payload plus an audit report, and only calls the runtime admin API when
`--submit` is explicitly provided.

## Application Layer Before Algorithm Layer

Do the application layer first.

Reason:

- Without stable real-data ingestion and paper reporting, better algorithms have no clean place to be observed.
- Runtime isolation prevents future LLM/MCTS changes from contaminating live paper results.
- A paper observation baseline creates a hard target for algorithm improvements.
- Server process management, stale-data detection, and report persistence are practical risks that should be solved early.

Algorithm work should continue after the observation loop is stable, not before.

## Timeline

### Phase 0: Freeze Boundaries (0.5 day)

Goal: make the separation explicit.

Tasks:

- Keep QuantumRandy and RandysLab in one workspace for now.
- Write down process boundaries and safety rules.
- Confirm runtime server remains paper-only.
- Pick initial approved factors and RandysLab baseline strategies.

Exit criteria:

- This document exists.
- Server agent can understand what to run and what not to touch.

### Phase 1: Minimum Server Paper Loop (1-2 days)

Goal: real K-line data enters runtime and produces paper snapshots.

Tasks:

- Implement Binance 4h feeder.
- Add feeder config, logging, retry, and stale-bar checks.
- Run runtime locally with synthetic or recently fetched bars.
- Add snapshot polling/report script if needed.
- Prepare server startup notes for the server agent.

Exit criteria:

- Runtime accepts real BTCUSDT bars.
- `/health` shows a latest timestamp.
- `/v1/snapshot` shows factor values, exposures, and paper equity.
- Re-running the feeder does not duplicate bars.

### Phase 2: Server Trial (2-4 days)

Goal: let the system run on the server without strategy churn.

Tasks for server agent:

- Deploy runtime server.
- Deploy feeder.
- Keep only initial factors active.
- Save logs and daily snapshots.
- Report stale data, crashes, or abnormal output.

Tasks for local/research agent:

- Do not change active runtime strategies during the first smoke period unless there is a bug.
- Compare live paper snapshots with equivalent delayed backtests.
- Document differences.

Exit criteria:

- Runs continuously for at least 48 hours.
- No missing 4h bars.
- Daily report is readable.
- Restart procedure is known.

### Phase 3: Controlled Research + Manual Factor Publishing (1 week)

Goal: mining and paper observation run side by side.

Tasks:

- Continue QuantumRandy mining.
- Run walk-forward validation on accepted candidates.
- Run multi-asset robustness where data exists.
- Build a manual factor publisher.
- Add generation-guarded runtime updates.
- Store each factor promotion with metrics and timestamp.

Exit criteria:

- A candidate factor can move from leaderboard to runtime manifest through a documented manual flow.
- Runtime rejects stale generation updates.
- Factor promotion can be rolled forward by submitting a new manifest.

Current status: first manual publisher implementation exists in `scripts/publish_factors.py`.

### Phase 4: First Multi-Factor Strategy Layer (1-2 weeks)

Goal: move beyond single-factor observation.

Current status: first offline research builder exists in `quantumrandy/portfolio.py` and
`scripts/build_portfolio.py`. It creates research-only equal-weight, rank-IC-weighted, and Sharpe-weighted artifacts
after correlation filtering. Runtime publication of any blend still requires manual review and the controlled publisher
flow.

Tasks:

- Build equal-weight accepted-factor portfolios after correlation filtering.
- Build fixed IC-weighted or Sharpe-weighted portfolios.
- Backtest portfolio-level returns, drawdown, turnover, and cost.
- Add factor contribution analysis.
- Add runtime strategies for one or two fixed blends.

Exit criteria:

- Multi-factor strategy beats or usefully diversifies RandysLab baselines in validation.
- Runtime paper blend has clear components and weights.
- Daily report separates factor-level and portfolio-level performance.

### Phase 5: Algorithm Upgrades (after Phases 1-3 are stable)

Goal: improve mining quality using the existing paper observation system as feedback.

Priority order:

1. Alpha portfolio layer.
2. LLM proposal schema v2 with hypothesis, expected edge, failure mode, and rewrite plan.
3. Failure memory library.
4. Pareto MCTS archive instead of single scalar winner logic.
5. DSL/data expansion: open interest, basis, taker volume, liquidation data, cross-asset returns.
6. Execution stress testing and richer cost sensitivity.

Exit criteria:

- Algorithm changes improve validated candidates, not just training leaderboard scores.
- New candidates survive walk-forward and manual promotion.
- Paper runtime remains stable while research code changes.

### Phase 6: Live Execution Interface Planning (after stable multi-factor paper)

Goal: reserve a clean path toward live execution without weakening the current paper-only safety boundary.

Status: planning only. No live trading code should be added during the v0.8 server-paper beta.

Prerequisites:

- 48h server paper trial completes without process or data-feed instability.
- Multi-factor paper blend runs for a longer observation window with documented baseline comparison.
- Promotion evidence exists for every active component factor and blend weight.
- Operator-runbook exists for halt, restart, rollback, stale data, abnormal drawdown, and token rotation.

Design requirements:

- Implement live execution as a separate `execution_adapter` process, not inside the research miner or current paper
  runtime.
- Support dry-run mode first, then tiny-capital live mode only after explicit approval.
- Use separate exchange credentials with least privilege and hard account-level limits.
- Add order-size caps, exposure caps, max daily loss, stale-data halt, generation pinning, and a manual kill switch.
- Persist an append-only order-intent and order-result audit log.
- Never let newly mined factors, LLM output, or unreviewed portfolio artifacts reach the execution adapter directly.

Exit criteria:

- A formal interface spec exists for target exposures, risk checks, order intents, fills, and audit events.
- Paper runtime and execution adapter can be tested end-to-end in dry-run mode without exchange trading permissions.
- The server agent has separate deployment instructions for paper observation and live execution.

## Complete Multi-Factor Strategy: Missing Pieces

The current system has enough pieces to observe fixed multi-factor blends, but not yet a complete research-grade
multi-factor strategy pipeline.

Missing pieces:

1. Factor admission policy:
   - minimum train/validation/blind metrics;
   - walk-forward survival threshold;
   - maximum correlation to active factor pool;
   - maximum turnover and drawdown limits.

2. Portfolio construction:
   - equal-weight baseline;
   - IC-weighted and Sharpe-weighted variants;
   - turnover penalty;
   - factor correlation clustering;
   - optional regularized weights.

3. Portfolio validation:
   - portfolio-level walk-forward;
   - multi-asset robustness;
   - cost stress;
   - contribution and ablation analysis.

4. Runtime publishing:
   - convert portfolio weights into runtime strategy components;
   - persist manifest generation;
   - record promotion evidence.

5. Monitoring:
   - daily equity and drawdown report;
   - stale-data detection;
   - realized turnover and cost report;
   - factor decay watchlist.

## Initial Runtime Candidate Set

Start small. Suggested initial paper set:

- one RandysLab baseline or proxy strategy if available;
- `neg(zscore(funding_rate,42))`;
- one price/volume correlation factor that survived blind validation;
- one EMA trend factor that survived blind validation;
- one fixed two- or three-factor blend.

Do not start with a large zoo in runtime. A small set is easier to audit.

## Decision Summary

Recommended order:

1. Application layer and server paper loop.
2. Controlled factor promotion flow.
3. Multi-factor portfolio layer.
4. Algorithm upgrades.

The short version: put the observation lab online first, then improve the scientist working inside it.
