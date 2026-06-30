# QuantumRandy Research Roadmap

Last updated: 2026-06-29

This note is a handoff document for future Codex sessions. It records the research ideas, literature map, and current progress for improving `QuantumRandy` without requiring the next session to rediscover the same context.

## Current Project Position

`QuantumRandy` is currently an LLM + MCTS formulaic alpha mining system for crypto perpetual futures. Its core loop is:

1. Generate or rewrite formulaic alpha candidates.
2. Evaluate each formula through the expression DSL and strict perpetual futures backtest.
3. Use MCTS to guide search.
4. Keep an alpha zoo with diversity controls.
5. Apply a four-gate brutal filter: predictive power, homogeneity, cost/friction audit, and lifespan validation.
6. Expose mining and validation through scripts and a local dashboard.

The strongest existing design choices are interpretability, strict cost-aware backtesting, funding-rate awareness, kill diagnostics, and a dashboard-driven research loop.

The main current limitations are:

- single-symbol default workflow, currently BTC-focused;
- mostly single-factor discovery rather than portfolio-level alpha combination;
- no true walk-forward research protocol yet;
- limited cross-asset robustness checks;
- LLM currently acts mostly as a formula generator, not a full research loop with hypothesis, failure-mode prediction, and targeted revision;
- execution modeling is strict for 4h perpetual backtests, but not yet a microstructure/execution simulator;
- paper and project artifacts are not yet organized as a reusable research knowledge base.

## Literature Map

Primary papers already present under `docs/papers/`:

| Priority | Local file | Topic | Use for QuantumRandy |
|---|---|---|---|
| P0 | `Navigating the Alpha Jungle An LLM-Powered MCTS Framework for Formulaic Factor Mining.pdf` | LLM + MCTS formulaic alpha mining | Core method reference: LLM proposal, MCTS selection, alpha zoo, correlation retrieval, formula mining loop |
| P0 | `2512.22476v1.pdf` | Execution-constrained crypto perpetual tuning | Use as execution-audit layer after QuantumRandy generates formulas |
| P1 | `2511.02136v1.pdf` | GPU-accelerated multi-agent RL for high-frequency trading | Long-term reference for market simulation and execution realism |
| P1 | `2511.15262v1.pdf` | Queue-reactive RL for optimal execution | Long-term reference for execution reward and simulated order-book response |
| P1 | `2511.02518v2.pdf` | Option market making with hedging-induced market impact | Reference for inventory risk, market impact, and policy optimization thinking |
| P2 | `2511.22101v1.pdf` | Uniswap V3 liquidity provision with DDQN/Mamba | Reference for DeFi market making and chain-native extension ideas |
| P2 | `2512.23386v1.pdf` | Arbitrum Timeboost / transaction ordering | Reference for MEV, priority access, and short-horizon volatility features |
| P2 | `2508.03474v1.pdf` | Polymarket arbitrage | Reference for prediction-market arbitrage and combinatorial mispricing |
| P2 | `2512.04603v1.pdf` | FX market making with internal liquidity | Reference for internalization, multi-objective execution, and liquidity matching |
| P2 | `2512.14134v2.pdf` | High volume return premium | Reference for volume-return features and nonlinear investor-intensity effects |
| P3 | `2512.01354v3.pdf` | Cognitive boundedness / model collapse | Indirect LLM research reference, not central to alpha mining |

Books already present under `docs/books/`:

- `101 Formulaic Alphas.pdf`: formulaic alpha inspiration and DSL expansion reference.
- `Advances in Financial Machine Learning...epub`: walk-forward, purged validation, feature importance, overfitting control.
- `Inside the Black Box...`: systematic investing process and model governance.
- `Market Microstructure Theory`: execution, liquidity, and market microstructure foundations.
- `Quantitative Equity Portfolio Management...`: portfolio construction and alpha combination reference.

## Research Ideas

### 1. Walk-Forward Validation

Status: first implementation complete in `QuantumRandy/quantumrandy/walk_forward.py` and `QuantumRandy/scripts/walk_forward.py`.

Why it matters:

Single train/validation/blind splits are too easy to overfit by repeated human and model inspection. A walk-forward protocol makes the output more credible and closer to a publishable research standard.

Suggested design:

- Define rolling windows such as `train 18 months -> validation 6 months -> blind/test 3 months`.
- Support fixed crypto regimes: bull, bear, chop, high funding, funding-neutral, high volatility.
- For every factor, produce:
  - per-window Sharpe;
  - per-window rank IC;
  - per-window max drawdown;
  - per-window turnover;
  - survival rate;
  - IC decay profile;
  - factor half-life stability;
  - pass/fail reason per window.

Deliverable:

- `walk_forward_details.csv`: implemented.
- `walk_forward_summary.csv`: implemented.
- `walk_forward_windows.json`: implemented.
- `WALK_FORWARD_REPORT.md`: implemented.
- dashboard panel: not started.

Priority: P0.

### 2. Multi-Asset Robustness

Status: first implementation complete in `QuantumRandy/quantumrandy/universe.py` and `QuantumRandy/scripts/eval_universe.py`.

Why it matters:

If a formula works only on BTC, it may be a local historical artifact. If it survives BTC, ETH, SOL, BNB, and maybe AVAX with related but not identical behavior, it is more likely to capture a real crypto market structure.

Suggested design:

- Add a universe config listing symbols and data paths.
- Evaluate the same formula across all symbols.
- Score with:
  - mean cost Sharpe;
  - median rank IC;
  - worst-symbol drawdown;
  - cross-symbol variance penalty;
  - number of symbols passed.

Candidate universe:

- BTCUSDT
- ETHUSDT
- SOLUSDT
- BNBUSDT
- AVAXUSDT

Deliverable:

- `run_universe_evaluation`
- `scripts/eval_universe.py`
- dashboard symbol breakdown for each factor

Priority: P0.

### 3. Alpha Portfolio Layer

Status: first offline implementation complete in `QuantumRandy/quantumrandy/portfolio.py` and
`QuantumRandy/scripts/build_portfolio.py`.

Why it matters:

The current system mostly ranks single factors. In real quantitative research, the valuable object is usually not one formula but a low-correlation combination of many weak signals.

Suggested phases:

1. Equal-weight accepted factors after correlation filtering.
2. IC-weighted or Sharpe-weighted combination.
3. Risk-adjusted weighting with turnover penalty.
4. Regularized portfolio weights using ridge/lasso-style shrinkage.
5. Walk-forward retraining of weights.

Metrics:

- portfolio Sharpe and drawdown;
- factor contribution;
- marginal IC;
- marginal turnover;
- correlation cluster exposure;
- weight stability.

Deliverable:

- `portfolio.py`: implemented for fixed equal-weight, rank-IC-weighted, and Sharpe-weighted portfolios after correlation
  filtering.
- `scripts/build_portfolio.py`: implemented.
- dashboard portfolio equity curve and factor contribution panel: not started.

Priority: P0/P1.

### 4. Pareto MCTS Instead Of Single Reward

Status: not started.

Why it matters:

A single scalar reward can hide important tradeoffs. A factor with great training Sharpe but high turnover, high correlation, or weak validation stability should not dominate the search tree too easily.

Suggested design:

Track a Pareto frontier over:

- rank IC;
- cost Sharpe;
- validation Sharpe;
- turnover;
- max correlation to zoo;
- formula complexity;
- half-life;
- drawdown.

MCTS can still use a scalar acquisition score, but the alpha zoo should preserve nondominated candidates rather than only the highest score.

Deliverable:

- Pareto archive;
- `pareto_rank` in factor rows;
- dashboard toggle: score rank vs Pareto rank.

Priority: P1.

### 5. LLM Research Loop

Status: partially started through current LLM formula proposal and descriptions; not yet a full loop.

Current behavior:

- LLM proposes formulas.
- Description must contain economic rationale.
- Existing formulas and forbidden subtrees can be passed into prompt.

Proposed upgraded behavior:

Each LLM proposal should include:

- `hypothesis`: market behavior the formula tries to capture;
- `formula`: DSL expression;
- `expected_edge`: why it should predict future returns;
- `expected_failure_mode`: cost, crowding, regime sensitivity, funding distortion, etc.;
- `rewrite_plan_if_killed`: how to revise if a specific gate fails.

After brutal filter, feed failure reasons back into a targeted rewrite prompt:

- killed by predictive power -> change information source or horizon;
- killed by homogeneity -> preserve economics but change construction;
- killed by cost -> smooth signal, reduce turnover, increase window;
- killed by lifespan -> add regime guard or use slower horizon;
- killed by validation -> penalize training-only structures.

Deliverable:

- LLM event schema v2;
- prompt templates for generate, diagnose, and rewrite;
- failure-aware proposal history.

Priority: P1.

### 6. Failure Memory Library

Status: not started.

Why it matters:

The system currently knows what was killed, but it can do more with that knowledge. Failed factors should become negative examples for future generation.

Suggested design:

Store each failed factor with:

- formula;
- subtree fingerprints;
- factor value correlations;
- failed gates;
- metrics at failure;
- LLM rationale;
- timestamp and dataset window.

Use this library for:

- avoiding repeated structural mistakes;
- prompting the LLM with negative few-shot examples;
- identifying clusters of failure;
- comparing whether a new formula is a meaningful rewrite or just a cosmetic mutation.

Deliverable:

- `failure_memory.jsonl`
- retrieval function by failed gate and formula similarity
- dashboard failed-cluster view

Priority: P1.

### 7. DSL And Data Expansion

Status: current DSL has 21 operators and fields: OHLCV plus funding rate.

Most valuable new data fields for crypto perpetuals:

- open interest;
- basis / perp-spot spread;
- long-short ratio;
- taker buy/sell volume;
- liquidation volume;
- order book imbalance, if available;
- cross-asset returns;
- BTC dominance or market-wide risk proxy;
- realized volatility regime flag;
- funding-rate term structure, if multiple venues are available.

Most useful new operators:

- `winsorize(x, window)`
- `neutralize(x, y, window)`
- `clip(x, low, high)`
- `decay_linear(x, window)`
- `ts_argmax(x, window)`
- `ts_argmin(x, window)`
- `skew(x, window)`
- `kurtosis(x, window)`
- `reg_beta(y, x, window)`
- `resid(y, x, window)`

Priority: P1/P2.

### 8. Execution-Aware Reward

Status: basic strict backtest exists; deeper execution simulator not started.

Why it matters:

At 4h bars, taker fees, slippage, funding, and delay are already modeled. But for more serious research, reward should become sensitive to execution constraints and liquidity regimes.

Ideas from the HFT/execution papers:

- simulate adverse slippage based on volatility and volume;
- make missed fills probabilistic;
- punish signal flips during high-volatility periods;
- add capacity proxy using turnover and volume;
- support maker/taker execution profiles;
- stress test fee, slippage, and funding assumptions.

Deliverable:

- execution profile matrix;
- cost-stress leaderboard;
- dashboard friction sensitivity chart.

Priority: P1/P2.

### 9. Research Artifact System

Status: partially present through reports, leaderboard, events, and audit reports.

Goal:

Make every run reproducible and future-readable.

Each serious run should save:

- config snapshot;
- git commit hash;
- data file hashes;
- train/validation/blind windows;
- full formula list;
- killed and accepted factors;
- failure reasons;
- LLM prompts and responses, with API keys removed;
- walk-forward outputs;
- portfolio outputs;
- charts and final markdown report.

Priority: P1.

## Suggested Implementation Order

Recommended path:

1. Write research docs and organize papers. Status: complete.
2. Implement walk-forward validation. Status: first version complete.
3. Implement multi-asset evaluator. Status: first version complete.
4. Implement alpha portfolio layer. Status: first offline fixed-weight version complete.
5. Upgrade LLM proposal schema and failure-aware rewrite loop. Status: not started.
6. Add failure memory library. Status: not started.
7. Expand data fields and DSL. Status: not started.
8. Add execution stress testing and richer dashboard panels. Status: not started.

Minimum viable next milestone:

- Add dashboard symbol breakdown and run the multi-asset evaluator on BTC/ETH/SOL/BNB/AVAX configs once those config/data files are present.

Expected value:

- It will quickly reveal whether the current factors are robust or just lucky.
- It gives the next LLM/MCTS improvements a reliable target.
- It makes the project much easier to explain in a paper, README, or future GitHub release.

## Current Progress Log

### 2026-06-29

- Reviewed local `docs/papers` and `docs/books` inventory.
- Confirmed the most relevant local paper is `Navigating the Alpha Jungle`, which matches QuantumRandy's LLM + MCTS + formulaic factor mining design.
- Confirmed `2512.22476v1.pdf` is the strongest companion paper for cost-aware, auditable crypto perpetual backtesting.
- Identified that the remaining papers mostly support longer-term execution, microstructure, DeFi, and market-making extensions rather than the immediate alpha-mining core.
- Decided not to modify source code in this step.
- Created this roadmap as a future-session handoff.
- Implemented first-version walk-forward validation:
  - added `QuantumRandy/quantumrandy/walk_forward.py`;
  - added `QuantumRandy/scripts/walk_forward.py`;
  - added tests in `QuantumRandy/tests/test_walk_forward.py`;
  - outputs detail CSV, summary CSV, window JSON, config JSON, and markdown report;
  - smoke-tested two seed formulas over 9 rolling windows in `reports/walk_forward_smoke`.
- Implemented first-version multi-asset robustness evaluation:
  - added `QuantumRandy/quantumrandy/universe.py`;
  - added `QuantumRandy/scripts/eval_universe.py`;
  - added tests in `QuantumRandy/tests/test_universe.py`;
  - outputs detail CSV, summary CSV, JSON report, and markdown report.
- Implemented first-version offline portfolio research:
  - added `QuantumRandy/quantumrandy/portfolio.py`;
  - added `QuantumRandy/scripts/build_portfolio.py`;
  - added tests in `QuantumRandy/tests/test_portfolio.py`;
  - outputs evaluated factor metrics, correlation-filter decisions, equal/IC/Sharpe portfolio summaries, a research-only
    manifest, and a markdown report.

## Next Session Prompt

If continuing this work in a new session, use this prompt:

```text
Please continue QuantumRandy from docs/QuantumRandy_research_roadmap.md.
Do not start by rereading every paper. First inspect the current repo state, then implement the next milestone:
multi-asset robustness evaluation for accepted factors, reusing the walk-forward validation outputs where helpful.
Keep source edits scoped and run tests before finishing.
```
