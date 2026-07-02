# QuantumRandy Research Roadmap

Last updated: 2026-07-02

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
Read-only config/data readiness checks and config scaffolding are also implemented in
`QuantumRandy/quantumrandy/data_readiness.py` and `QuantumRandy/scripts/data_readiness.py`.

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
- `scripts/data_readiness.py`: implemented as a local config/CSV coverage preflight with CSV, JSON, and Markdown outputs;
  it can also scaffold missing research configs from the BTC template and write a RandysLab fetch runbook without
  downloading market data.
- dashboard symbol breakdown for each factor

Priority: P0.

### 3. Alpha Portfolio Layer

Status: first offline implementation complete in `QuantumRandy/quantumrandy/portfolio.py`,
`QuantumRandy/scripts/build_portfolio.py`, and fixed-blend walk-forward validation in
`QuantumRandy/quantumrandy/portfolio_walk_forward.py` / `QuantumRandy/scripts/portfolio_walk_forward.py`.

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
- `scripts/portfolio_walk_forward.py`: implemented for fixed-blend rolling train/validation/test stability checks.
- dashboard portfolio equity curve and factor contribution panel: not started.

Priority: P0/P1.

### 3B. Factor Admission Policy

Status: first implementation complete in `QuantumRandy/quantumrandy/admission.py` and
`QuantumRandy/scripts/build_admission.py`. A research-only candidate selector is also implemented in
`QuantumRandy/quantumrandy/candidate_selector.py` and `QuantumRandy/scripts/build_candidate_selector.py` to rank
leaderboard formulas with universe, portfolio-universe, and failure-memory evidence before further rewrite effort.

Why it matters:

Individual reports are useful, but promotion decisions need one explicit evidence policy. Admission should combine
brutal-filter status, validation metrics, walk-forward survival, multi-asset robustness, turnover, drawdown, and
correlation evidence before a factor reaches manual runtime-publishing review.

Deliverable:

- `admission_decisions.csv`: implemented.
- `admission_manifest.json`: implemented.
- `ADMISSION_REPORT.md`: implemented.
- `candidate_selector.csv`, `rewrite_targets.csv`, and `multi_asset_failure_clusters.csv`: implemented as research-only
  evidence artifacts for rewrite prioritization and BTC-only pattern triage.
- optional portfolio-level walk-forward evidence ingestion: implemented.
- dashboard admission / failure-cluster / portfolio walk-forward review panel: implemented.

Priority: P0/P1.

### 4. Pareto MCTS Archive

Status: first archive implementation complete in `QuantumRandy/quantumrandy/pareto.py` and MCTS save outputs.

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

- Pareto archive: implemented.
- `pareto_rank` in factor rows: implemented for zoo/tree/leaderboard outputs.
- dashboard review card for nondominated front: implemented.
- dashboard toggle: score rank vs Pareto rank: not started.

Priority: P1.

### 5. LLM Research Loop

Status: schema-v2 proposal context, failure-memory-aware prompting, and first targeted rewrite loop are implemented.

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

- LLM event schema v2: implemented.
- prompt templates for generate, diagnose, and rewrite: generate and rewrite prompts implemented; separate diagnose prompt
  not started.
- failure-aware proposal history: implemented through schema-v2 fields, failure memory artifacts, and rewrite events.

Priority: P1.

### 6. Failure Memory Library

Status: first implementation complete in `QuantumRandy/quantumrandy/failure_memory.py` and
`QuantumRandy/scripts/build_failure_memory.py`.

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

- `failure_memory.csv`: implemented.
- `failure_clusters.csv`: implemented.
- `failure_memory_manifest.json`: implemented.
- `FAILURE_MEMORY_REPORT.md`: implemented.
- retrieval function by failed gate and formula similarity: failure-memory and candidate-selector prompt context loaders
  implemented; richer API not started.
- dashboard failed-cluster view: not started.

Priority: P1.

### 7. DSL And Data Expansion

Status: current DSL has 28 operators and fields: OHLCV plus funding rate. First operator expansion added
`clip`, `winsorize`, `decay_linear`, `ts_argmax`, `ts_argmin`, `skew`, and `kurtosis`; new crypto-specific data fields
remain future work.

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

- `winsorize(x, window)`: implemented.
- `neutralize(x, y, window)`
- `clip(x, low, high)`: implemented.
- `decay_linear(x, window)`: implemented.
- `ts_argmax(x, window)`: implemented.
- `ts_argmin(x, window)`: implemented.
- `skew(x, window)`: implemented.
- `kurtosis(x, window)`: implemented.
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
5. Add factor admission policy. Status: first research-only admission report implemented.
6. Upgrade LLM proposal schema and failure-aware rewrite loop. Status: schema-v2 proposal context, failure-memory-aware
   generation, and first targeted rewrite loop implemented.
7. Add failure memory library. Status: first artifact builder and prompt context loader implemented.
8. Expand data fields and DSL. Status: not started.
9. Add execution stress testing and richer dashboard panels. Status: not started.

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

### 2026-06-30

- Implemented LLM proposal schema v2 metadata:
  - added hypothesis, expected edge, expected failure mode, and rewrite plan fields;
  - persisted the fields through MCTS results, zoo/tree outputs, and leaderboard rows;
  - added tests in `QuantumRandy/tests/test_llm_schema.py`.
- Implemented first-version failure memory artifacts:
  - added `QuantumRandy/quantumrandy/failure_memory.py`;
  - added `QuantumRandy/scripts/build_failure_memory.py`;
  - added tests in `QuantumRandy/tests/test_failure_memory.py`;
  - outputs failed formula rows, repeated failed subtree clusters, manifest metadata, and a Markdown report.
- Connected failure memory to LLM proposal context:
  - `prompt.failure_memory_path` can point to a failure memory output directory or CSV;
  - DeepSeek prompts include negative examples and repeated failed subtree clusters;
  - LLM proposal events record the number of failure examples and clusters sent.
- Implemented first targeted rewrite loop:
  - killed non-seed factors can trigger a small gate-aware rewrite pass;
  - local fallback rewrites by failed gate when LLM is unavailable;
  - DeepSeek rewrite prompts include failed gates, compact gate metrics, failure memory, and schema-v2 requirements;
  - rewrite candidates still go through the normal evaluation and brutal-filter path.
- Implemented first factor admission policy artifact:
  - added `QuantumRandy/quantumrandy/admission.py`;
  - added `QuantumRandy/scripts/build_admission.py`;
  - added tests in `QuantumRandy/tests/test_admission.py`;
  - combines leaderboard, walk-forward, universe, and portfolio evidence into `approve`, `review`, or `reject`
    research decisions.
- Implemented first portfolio-level walk-forward validation:
  - added `QuantumRandy/quantumrandy/portfolio_walk_forward.py`;
  - added `QuantumRandy/scripts/portfolio_walk_forward.py`;
  - added tests in `QuantumRandy/tests/test_portfolio_walk_forward.py`;
  - validates fixed portfolio blends from research manifests across rolling train/validation/test windows;
  - outputs portfolio detail rows, summary stability metrics, windows, manifest, and a Markdown report.
- Connected portfolio-level walk-forward evidence to factor admission:
  - `scripts/build_admission.py` accepts `--portfolio-walk-forward-summary`;
  - component factors inherit evidence from fixed blends that include their factor id;
  - admission decisions record best blend survival, window count, and median test Sharpe evidence.
- Added a read-only research review panel to the mining dashboard:
  - loads latest admission, failure-memory, and portfolio walk-forward artifacts from `reports/`;
  - summarizes admission counts, repeated failed subtrees, and fixed-blend stability;
  - does not submit runtime updates or publish strategies.
- Added first Pareto archive for MCTS alpha review:
  - added `QuantumRandy/quantumrandy/pareto.py`;
  - MCTS saves `pareto_archive.csv` and `pareto_archive.json`;
  - zoo/tree/leaderboard rows carry `pareto_rank` and `pareto_front`;
  - dashboard research review summarizes the nondominated front when present.
- Added first DSL operator expansion:
  - added `clip`, `winsorize`, `decay_linear`, `ts_argmax`, `ts_argmin`, `skew`, and `kurtosis`;
  - updated parser validation, expression evaluation, LLM operator notes, README, and tests;
  - no new data fields or runtime publishing behavior were added.
- Added a read-only multi-asset data readiness preflight:
  - added `QuantumRandy/quantumrandy/data_readiness.py`;
  - added `QuantumRandy/scripts/data_readiness.py`;
  - added tests in `QuantumRandy/tests/test_data_readiness.py`;
  - checks expected BTC/ETH/SOL/BNB/AVAX config presence, OHLCV/funding CSV columns, row counts, 4h gaps, configured
    training/validation window coverage, and funding alignment;
  - writes `data_readiness.csv`, `data_readiness_manifest.json`, and `DATA_READINESS_REPORT.md`;
  - also writes `DATA_FETCH_RUNBOOK.md` with explicit RandysLab public-data fetch commands for missing or under-covered
    local datasets;
  - does not download data, call exchange APIs, publish factors, or mutate runtime state.
- Added ETH/SOL/BNB/AVAX research config scaffolds under `QuantumRandy/configs/`, pointing at expected RandysLab local
  OHLCV/funding CSV names. Current local readiness still reports those CSV files as missing until the data layer is
  populated deliberately.
- Populated the local RandysLab data layer from Binance public archive files and moved BTC/ETH/SOL/BNB/AVAX configs to
  a shared `2022-05-01` to `2025-11-24` research window. `scripts/data_readiness.py` now reports all five configs ready
  on the local archive dataset, and a two-formula universe smoke has run successfully as a research artifact.
- Added stable factor IDs and research-only manifest metadata to multi-asset universe artifacts. A formal
  BTC/ETH/SOL/BNB/AVAX archive evaluation of passed `reports/research_live/leaderboard.json` candidates was run locally
  into `reports/universe_archive_eval`, and its summary can now feed factor admission by stable factor ID.
- Added a research-only candidate selector:
  - added `QuantumRandy/quantumrandy/candidate_selector.py`;
  - added `QuantumRandy/scripts/build_candidate_selector.py`;
  - added tests in `QuantumRandy/tests/test_candidate_selector.py`;
  - combines leaderboard, universe robustness, portfolio-universe robustness, and optional failure-memory evidence;
  - writes `candidate_selector.csv`, `rewrite_targets.csv`, `multi_asset_failure_clusters.csv`,
    `candidate_selector_manifest.json`, and `CANDIDATE_SELECTOR_REPORT.md`;
  - separates `rewrite`, `deprioritize`, and `needs_evidence` verdicts without changing admission policy or runtime
    state.
- Connected candidate selector evidence to LLM prompts:
  - `prompt.candidate_selector_path` can point to a candidate selector output directory or CSV;
  - DeepSeek generate and rewrite prompts include rewrite targets, evidence gaps, and weak cross-asset clusters;
  - LLM events record how many selector rewrite targets, evidence gaps, and clusters were sent;
  - this remains prompt context only and does not auto-admit, auto-publish, or update runtime strategies.
- Added a research-only selector rewrite batch:
  - added `QuantumRandy/quantumrandy/candidate_rewrite.py`;
  - added `QuantumRandy/scripts/rewrite_selector_candidates.py`;
  - added tests in `QuantumRandy/tests/test_candidate_rewrite.py`;
  - writes leaderboard-style `selector_rewrite_candidates.json` plus CSV, event, manifest, and Markdown artifacts;
  - local archive smoke generated 6 candidates from the top 3 selector rewrite targets and evaluated them across
    BTC/ETH/SOL/BNB/AVAX into `reports/selector_rewrite_universe_archive_eval`;
  - the local fallback rewrite smoke did not improve robustness materially: best pass rate was `0.20`, so the next
    useful experiment should be a small LLM rewrite batch with selector context or a stronger local rewrite policy.
- Strengthened and orchestrated the selector rewrite evidence loop:
  - selector rewrite now converts selector weak clusters and matched failed subtrees into forbidden rewrite evidence;
  - local fallback rewrite has explicit cross-asset robustness/profitability gates biased toward funding, volatility,
    and liquidity regime hypotheses rather than repeating fragile price-only structures;
  - added `QuantumRandy/quantumrandy/selector_pipeline.py`;
  - added `QuantumRandy/scripts/run_selector_rewrite_pipeline.py`;
  - added tests in `QuantumRandy/tests/test_selector_pipeline.py`;
  - the pipeline writes a research-only selector rewrite batch and, when asset configs are provided, evaluates the
    candidates through universe evidence plus fixed-blend portfolio-universe evidence;
  - writes `review/selector_pipeline_review.csv` and `SELECTOR_PIPELINE_REVIEW.md` to compare each parent target with
    its best rewrite candidate using pass-rate and mean-Sharpe deltas;
  - review verdicts now separate `coverage_only` rewrites from true improvements, so candidates that raise cross-asset
    pass rate while reducing parent mean Sharpe are not treated as acceptable improvements;
  - parent-level review selection now ranks candidates by improvement-gate quality before raw pass rate, preventing
    coverage-only candidates from hiding lower-pass but genuinely Sharpe-improving rewrites;
  - review rows now include per-parent candidate verdict counts and a best-candidate rank reason, making it easier to
    audit whether an improved parent also had rejected or coverage-only alternatives;
  - the review stage also writes `selector_pipeline_candidate_review.csv`, a candidate-level parent-vs-rewrite table
    with per-candidate verdicts and deltas before parent-level best-candidate aggregation;
  - the review stage also writes `selector_pipeline_candidate_highlights.csv`, a compact machine-readable audit queue
    for true improvements, coverage-only traps, and Sharpe-improved/no-pass-lift candidates;
  - the review stage writes `SELECTOR_CANDIDATE_HIGHLIGHTS.md`, a standalone research-only handoff summary of those
    compact queues; `scripts/summarize_selector_highlights.py` can rebuild or export the same summary from an existing
    review directory;
  - the top-level selector rewrite pipeline manifest and report summarize candidate verdict and highlight mixes so a
    handoff can audit rewrite quality without opening the review subdirectory first;
  - the mining dashboard review payload reads the candidate-level selector review when present and summarizes
    candidate verdict counts plus top candidate-level rows with failed-asset and formula context, without changing
    runtime or admission behavior;
  - when `selector_pipeline_candidate_highlights.csv` is present, the dashboard surfaces those compact audit queues
    directly before falling back to generic candidate-level rows;
  - `SELECTOR_PIPELINE_REVIEW.md` now includes candidate-level verdict counts and highlight tables for true improved
    candidates, coverage-only traps, and Sharpe-improved/no-pass-lift candidates so the same review can be audited
    without opening the dashboard or raw CSV.
  - v0.8.2 local fallback baseline evidence is recorded in `docs/SELECTOR_REWRITE_V0_8_2_BASELINE.md`; it found one
    true improved candidate and one coverage-only trap, but it is not LLM policy evidence because no LLM credentials or
    proxy variables were available in the session.
  - selector rewrite manifests and pipeline reports now expose LLM/fallback accepted counts and an explicit
    `is_llm_policy_evidence` flag, so fallback runs cannot be mistaken for LLM rewrite validation.
  - `scripts/run_selector_rewrite_pipeline.py --require-llm-evidence` exits non-zero unless `--use-llm` produced at
    least one accepted LLM rewrite, which makes future LLM-vs-local comparisons less ambiguous.
  - the mining dashboard surfaces the same LLM evidence flag and accepted-count split in its selector pipeline review
    panel.
  - selector rewrite prompts now ask LLM candidates to optimize both `pass_rate_delta > 0` and
    `mean_sharpe_delta >= 0`, justify normalized range/volatility profitability, and predict likely cross-asset failure
    modes before evaluation;
  - all outputs remain offline research artifacts and do not admit, publish, or update runtime strategies.

### 2026-07-02

- Continued the v0.8.2 LLM-only selector rewrite audit with hard-gated repeats 7 and 8:
  - both runs used `--llm-only --require-llm-evidence --require-llm-true-improvement`;
  - both completed rewrite, universe, portfolio, portfolio-universe, and review stages;
  - both produced valid LLM policy evidence with local fallback disabled;
  - both were correctly rejected by the true-improvement hard gate because all accepted candidates were
    `not_improved`.
- Refreshed the multi-run selector evidence summary across attempts 4 through 8:
  - runs: `5`;
  - LLM policy evidence runs: `5`;
  - LLM true-improvement evidence runs: `2`;
  - coverage-only trap runs: `0`;
  - distinct highlighted candidates: `3`.
- Current interpretation: the LLM-only audit path is repeatable and attribution-clean, but the positive candidates are
  not stable across repeats. Attempts 7 and 8 drifted toward weak slow-funding variants and should be treated as
  research-only negative controls, not admission or runtime publish evidence.
- Tightened selector rewrite family discipline after the slow-funding drift:
  - non-funding selector parents now default to `max_pure_funding_candidates=0`;
  - pure funding parents still allow at most one pure funding-rate-only rewrite;
  - the family limit is included in LLM rewrite prompts and enforced by the parser;
  - rewrite artifacts record `parent_formula_family` and `max_pure_funding_candidates`;
  - invalid non-funding prompt examples that exceeded the DSL depth limit were replaced with shape-valid range and
    realized-volatility examples.
- Ran a policy-guarded LLM-only repeat:
  - output: `reports/selector_rewrite_pipeline_llm_v082_evidence9_policy_guarded_shape_fixed`;
  - `llm_rewrite_accepted=3`, `fallback_rewrite_accepted=0`, `is_llm_policy_evidence=true`;
  - all candidates were still `not_improved`, with no LLM true-improved highlight;
  - the failure mode shifted from weak pure funding variants to weak realized-volatility stress proxies, so the hard gate
    again rejected the run correctly.
- Refreshed the multi-run selector evidence summary across attempts 4 through 9:
  - runs: `6`;
  - LLM policy evidence runs: `6`;
  - LLM true-improvement evidence runs: `2`;
  - coverage-only trap runs: `0`.
- Added selector negative evidence memory:
  - `scripts/summarize_selector_evidence.py` now also writes
    `selector_pipeline_negative_candidate_summary.csv`;
  - negative rows aggregate LLM-sourced `not_improved`, `coverage_only`, and hard-gate-rejected `mixed`
    candidates by parent formula family and candidate formula family;
  - `--selector-evidence-path` can pass this summary into selector rewrite LLM prompts;
  - exact negative example formulas are added to rewrite `disallowed_formulas`, so prior failed candidates cannot be
    accepted again by the LLM parser.
- Ran negative-memory repeats:
  - attempt 10 used negative memory as prompt context but still allowed exact negative repeats, and was rejected by the
    hard gate with no LLM true-improved highlight;
  - attempt 11 added exact negative disallow, completed with `llm_rewrite_accepted=2`, and produced one LLM-sourced
    true-improved highlight;
  - the repeated true-improved candidate was `qr_cd595899ee`,
    `zscore(corr(sub(close,open),volume,36),96)`, with pass-rate delta `+0.20` and mean-Sharpe delta `+0.04900644`.
- Refreshed the multi-run selector evidence summary across attempts 4 through 11:
  - runs: `8`;
  - LLM policy evidence runs: `8`;
  - LLM true-improvement evidence runs: `3`;
  - coverage-only trap runs: `0`;
  - highlighted candidate rows: `4`;
  - distinct highlighted candidates: `3`;
  - negative candidate family rows: `10`.
- Continued negative-memory hard-gated repeats:
  - attempt 12 passed the hard gate and repeated `qr_cd595899ee`, making it the first LLM-sourced true-improved
    candidate to appear in three separate runs;
  - attempt 12 also showed that prompt-facing negative examples were too small for exact blocking, because a lower-ranked
    negative formula could still repeat;
  - selector negative prompt context now separates compact prompt examples/families from a wider mechanical exact
    disallow formula list, defaulting to up to `20` formulas.
- Ran attempt 13 with the wider exact-negative disallow list:
  - output: `reports/selector_rewrite_pipeline_llm_v082_evidence13_negative_memory_wide_disallow`;
  - `llm_rewrite_accepted=4`, `fallback_rewrite_accepted=0`, `is_llm_policy_evidence=true`;
  - one LLM-sourced true-improved highlight, no coverage-only traps;
  - new highlighted candidate: `qr_655fb2a53d`, `zscore(corr(sub(close,open),volume,36),84)`, pass-rate delta
    `+0.40`, mean-Sharpe delta `+0.16858771`.
- Refreshed the multi-run selector evidence summary across attempts 4 through 13:
  - runs: `10`;
  - LLM policy evidence runs: `10`;
  - LLM true-improvement evidence runs: `5`;
  - coverage-only trap runs: `0`;
  - highlighted candidate rows: `6`;
  - distinct highlighted candidates: `4`;
  - negative candidate family rows: `12`.
- Ran negative-memory attempt 14 as another hard-gated repeat:
  - output: `reports/selector_rewrite_pipeline_llm_v082_evidence14_negative_memory_repeat`;
  - the run remained valid LLM policy evidence with `llm_rewrite_accepted=2` and `fallback_rewrite_accepted=0`;
  - the true-improvement hard gate correctly rejected the run because `llm_true_improved_count=0`;
  - highlight mix was `sharpe_improved_no_pass_lift:1|coverage_only_trap:1`;
  - repeated price-volume candidate `qr_cd595899ee`, `zscore(corr(sub(close,open),volume,36),96)`, improved mean
    Sharpe by `+0.12454568` in this run but had no pass-rate lift;
  - new coverage-only trap `qr_9a30f357c2`, `zscore(corr(sub(high,low),volume,48),96)`, raised pass rate by `+0.20`
    but reduced mean Sharpe by `-0.30235366`;
  - rewrite events recorded `selector_negative_disallowed_formulas=12`, and rejected two over-depth LLM formulas before
    candidate review.
- Refreshed the multi-run selector evidence summary across attempts 4 through 14:
  - runs: `11`;
  - LLM policy evidence runs: `11`;
  - LLM true-improvement evidence runs: `5`;
  - coverage-only trap runs: `1`;
  - highlighted candidate rows: `8`;
  - distinct highlighted candidates: `6`;
  - negative candidate rows: `29`;
  - negative candidate family rows: `12`.
- Ran negative-memory attempt 15 after refreshing memory with the attempt 14 coverage-only trap:
  - output: `reports/selector_rewrite_pipeline_llm_v082_evidence15_negative_memory_after_trap`;
  - the run remained valid LLM policy evidence with `llm_rewrite_accepted=1` and `fallback_rewrite_accepted=0`;
  - the true-improvement hard gate correctly rejected the run because `llm_true_improved_count=0`;
  - no candidate highlight rows were produced;
  - the only reviewed candidate was `qr_a3c34a6150`, `neg(corr(funding_rate,sub(close,open),72))`, with pass-rate
    delta `0.00` and mean-Sharpe delta `-0.65077117`;
  - two target attempts produced only rejected LLM formulas, caught by formula-depth and DSL validation guards;
  - this added another `price` parent to `funding_interaction` negative example for selector prompt memory.
- Refreshed the multi-run selector evidence summary across attempts 4 through 15:
  - runs: `12`;
  - LLM policy evidence runs: `12`;
  - LLM true-improvement evidence runs: `5`;
  - coverage-only trap runs: `1`;
  - highlighted candidate rows: `8`;
  - distinct highlighted candidates: `6`;
  - negative candidate rows: `30`;
  - negative candidate family rows: `12`.
- Ran negative-memory attempt 16 as another hard-gated repeat:
  - output: `reports/selector_rewrite_pipeline_llm_v082_evidence16_negative_memory_repeat`;
  - the run remained valid LLM policy evidence with `llm_rewrite_accepted=4` and `fallback_rewrite_accepted=0`;
  - the true-improvement hard gate correctly rejected the run because all four reviewed candidates were
    `not_improved`;
  - no candidate highlight rows were produced;
  - the price-parent target rejected one exact disallowed failed formula and one over-depth formula before review;
  - accepted candidates reinforced negative memory against pure-funding parents drifting into funding-price or
    volume-shock reversals, and against volume-liquidity parents drifting into funding-volume interactions;
  - new or reinforced negative formulas included `neg(corr(funding_rate,sub(close,open),96))`,
    `neg(zscore(delta(volume,24),120))`, `neg(corr(funding_rate,volume,96))`, and
    `neg(zscore(delta(volume,12),96))`.
- Refreshed the multi-run selector evidence summary across attempts 4 through 16:
  - runs: `13`;
  - LLM policy evidence runs: `13`;
  - LLM true-improvement evidence runs: `5`;
  - coverage-only trap runs: `1`;
  - highlighted candidate rows: `8`;
  - distinct highlighted candidates: `6`;
  - negative candidate rows: `34`;
  - negative candidate family rows: `13`.
- Promoted repeated selector negative family memory from prompt-only guidance to a conservative parser rule:
  - `PromptConfig.selector_negative_block_families` defaults to `20`;
  - `PromptConfig.selector_negative_block_min_count` defaults to `3`;
  - selector negative memory now returns `blocked_family_pairs` when a parent/candidate family pair has enough negative
    rows and negative average mean-Sharpe delta;
  - LLM rewrite prompts expose `blocked_candidate_family_pairs`, and the rewrite parser rejects candidates whose
    parent/candidate family pair is mechanically blocked;
  - rewrite events now record `selector_negative_blocked_family_pairs`.
- Ran attempt 17 with negative family-pair blocking active:
  - output: `reports/selector_rewrite_pipeline_llm_v082_evidence17_family_block`;
  - the run remained valid LLM policy evidence with `llm_rewrite_accepted=4` and `fallback_rewrite_accepted=0`;
  - rewrite events recorded `selector_negative_blocked_family_pairs=6` and
    `selector_negative_disallowed_formulas=13`;
  - the true-improvement hard gate correctly rejected the run because `llm_true_improved_count=0`;
  - highlight mix was `sharpe_improved_no_pass_lift:1`, repeating `qr_cd595899ee` for the pure-funding parent with
    mean-Sharpe delta `+0.12454568` but pass-rate delta `0.00`;
  - no coverage-only traps were produced.
- Refreshed the multi-run selector evidence summary across attempts 4 through 17:
  - runs: `14`;
  - LLM policy evidence runs: `14`;
  - LLM true-improvement evidence runs: `5`;
  - coverage-only trap runs: `1`;
  - highlighted candidate rows: `9`;
  - distinct highlighted candidates: `6`;
  - negative candidate rows: `37`;
  - negative candidate family rows: `13`.
- Added selector rewrite rejection-audit columns:
  - `selector_rewrite_events.csv` now records `rejected_count`, `rejected_reason_mix`, and
    `rejected_formula_examples`;
  - these fields make validator behavior visible without opening in-memory LLM events, including exact disallow,
    formula-depth, DSL signature, and future family-pair block rejections.
- Ran attempt 18 with rejection-audit fields active:
  - output: `reports/selector_rewrite_pipeline_llm_v082_evidence18_rejection_audit`;
  - the run remained valid LLM policy evidence with `llm_rewrite_accepted=3` and `fallback_rewrite_accepted=0`;
  - the true-improvement hard gate correctly rejected the run because all three reviewed candidates were
    `not_improved`;
  - no candidate highlight rows or coverage-only traps were produced;
  - rewrite events recorded `selector_negative_blocked_family_pairs=7` and
    `selector_negative_disallowed_formulas=13`;
  - new rejection-audit rows captured one invalid `ret(close,1)` signature, one depth violation, and one exact
    disallowed formula repeat.
- Refreshed the multi-run selector evidence summary across attempts 4 through 18:
  - runs: `15`;
  - LLM policy evidence runs: `15`;
  - LLM true-improvement evidence runs: `5`;
  - coverage-only trap runs: `1`;
  - highlighted candidate rows: `9`;
  - distinct highlighted candidates: `6`;
  - negative candidate rows: `40`;
  - negative candidate family rows: `14`.
- Ran attempt 19 as a rejection-audit repeat:
  - output: `reports/selector_rewrite_pipeline_llm_v082_evidence19_rejection_audit_repeat`;
  - the run remained valid LLM policy evidence with `llm_rewrite_accepted=4` and `fallback_rewrite_accepted=0`;
  - the true-improvement hard gate correctly rejected the run because `llm_true_improved_count=0`;
  - highlight mix was `coverage_only_trap:1`;
  - new coverage-only trap: `qr_5d66b52699`, `neg(zscore(ts_argmax(close,72),120))`, with pass-rate delta `+0.20`
    but mean-Sharpe delta `-0.30446903`;
  - rewrite events recorded `selector_negative_blocked_family_pairs=9` and
    `selector_negative_disallowed_formulas=14`;
  - rejection-audit rows captured one formula-depth violation and one exact disallowed formula repeat.
- Refreshed the multi-run selector evidence summary across attempts 4 through 19:
  - runs: `16`;
  - LLM policy evidence runs: `16`;
  - LLM true-improvement evidence runs: `5`;
  - coverage-only trap runs: `2`;
  - highlighted candidate rows: `10`;
  - distinct highlighted candidates: `7`;
  - negative candidate rows: `44`;
  - negative candidate family rows: `14`.
- Ran attempt 20 as another rejection-audit repeat:
  - output: `reports/selector_rewrite_pipeline_llm_v082_evidence20_rejection_audit_repeat`;
  - the run remained valid LLM policy evidence with `llm_rewrite_accepted=4` and `fallback_rewrite_accepted=0`;
  - the true-improvement hard gate correctly rejected the run because `llm_true_improved_count=0`;
  - highlight mix was `sharpe_improved_no_pass_lift:1`;
  - new highlighted-but-not-true-improved candidate: `qr_8096823a14`, `zscore(ret(close,48),120)`, with pass-rate
    delta `-0.20` and mean-Sharpe delta `+0.03912457`;
  - rewrite events recorded `selector_negative_blocked_family_pairs=11` and
    `selector_negative_disallowed_formulas=14`;
  - rejection-audit rows captured one formula-depth violation and one exact disallowed formula repeat.
- Refreshed the multi-run selector evidence summary across attempts 4 through 20:
  - runs: `17`;
  - LLM policy evidence runs: `17`;
  - LLM true-improvement evidence runs: `5`;
  - coverage-only trap runs: `2`;
  - highlighted candidate rows: `11`;
  - distinct highlighted candidates: `8`;
  - negative candidate rows: `47`;
  - negative candidate family rows: `15`.
- Added mixed-verdict selector negative memory:
  - LLM-sourced `mixed` candidates, surfaced as `sharpe_improved_no_pass_lift` highlights, now enter the negative
    candidate family summary alongside `not_improved` and `coverage_only`;
  - the negative family summary now records `sharpe_only_count`;
  - refreshing attempts 4 through 20 raised negative candidate rows from `47` to `50` and made Sharpe-only failures
    available to exact negative disallow and family-pair blocking.
- Ran attempt 21 with mixed negative memory active:
  - output: `reports/selector_rewrite_pipeline_llm_v082_evidence21_mixed_negative_memory`;
  - the run remained valid LLM policy evidence with `llm_rewrite_accepted=2` and `fallback_rewrite_accepted=0`;
  - the true-improvement hard gate correctly rejected the run because both reviewed candidates were `not_improved`;
  - no candidate highlight rows or coverage-only traps were produced;
  - rewrite events recorded `selector_negative_blocked_family_pairs=13` and
    `selector_negative_disallowed_formulas=15`;
  - rejection-audit rows captured family-pair blocks for `volume_liquidity->range_volatility` and
    `pure_funding->range_volatility`, plus exact disallowed formula repeats.
- Refreshed the multi-run selector evidence summary across attempts 4 through 21:
  - runs: `18`;
  - LLM policy evidence runs: `18`;
  - LLM true-improvement evidence runs: `5`;
  - coverage-only trap runs: `2`;
  - highlighted candidate rows: `11`;
  - distinct highlighted candidates: `8`;
  - negative candidate rows: `52`;
  - negative candidate family rows: `15`.
- Ran attempt 22 as a mixed-negative-memory repeat:
  - output: `reports/selector_rewrite_pipeline_llm_v082_evidence22_mixed_negative_memory_repeat`;
  - the run remained valid LLM policy evidence with `llm_rewrite_accepted=1` and `fallback_rewrite_accepted=0`;
  - the true-improvement hard gate correctly rejected the run because the only reviewed candidate was `not_improved`;
  - no candidate highlight rows or coverage-only traps were produced;
  - the reviewed candidate was `qr_a885e72b5e`, `neg(zscore(rsi(close,48),144))`, with pass-rate delta `-0.20` and
    mean-Sharpe delta `-0.99873822`;
  - rewrite events recorded `selector_negative_blocked_family_pairs=14` and
    `selector_negative_disallowed_formulas=15`;
  - rejection-audit rows captured family-pair blocks for `volume_liquidity->range_volatility`,
    `pure_funding->range_volatility`, and `price->volume_liquidity`, plus exact disallowed formula repeats.
- Refreshed the multi-run selector evidence summary across attempts 4 through 22:
  - runs: `19`;
  - LLM policy evidence runs: `19`;
  - LLM true-improvement evidence runs: `5`;
  - coverage-only trap runs: `2`;
  - highlighted candidate rows: `11`;
  - distinct highlighted candidates: `8`;
  - negative candidate rows: `53`;
  - negative candidate family rows: `15`.
- Ran attempts 23 and 24 as mixed-negative-memory repeats:
  - outputs: `reports/selector_rewrite_pipeline_llm_v082_evidence23_mixed_negative_memory_repeat` and
    `reports/selector_rewrite_pipeline_llm_v082_evidence24_mixed_negative_memory_repeat`;
  - both commands exited with code `2` because no LLM rewrite candidates were accepted;
  - every proposed formula was rejected before review by exact negative formula copies, blocked selector-memory family
    pairs, or formula-depth limits;
  - universe, portfolio, portfolio-universe, and review stages were skipped because there were no candidate formulas.
- Added a research-only mechanical rejection guard to the selector rewrite prompt:
  - prompts now expose parent formula family, blocked/allowed candidate families, family-classification rules, and
    depth-safe templates;
  - this does not loosen validator, admission, publishing, or runtime behavior.
- Ran attempt 25 with the prompt guard:
  - output: `reports/selector_rewrite_pipeline_llm_v082_evidence25_mechanical_guard`;
  - the command still exited with code `2` because current top targets had no allowed primary candidate families left
    under selector negative memory.
- Added exhausted-target skipping for LLM-only selector rewrites:
  - if selector negative memory blocks every primary candidate family for a parent family, the loop records a
    `selector_target_skip` audit row and continues to later selector targets;
  - `max_targets` now counts non-exhausted targets attempted by the rewrite loop rather than blindly truncating the
    selector file before skip checks.
- Ran attempt 26 with exhausted-target skipping:
  - output: `reports/selector_rewrite_pipeline_llm_v082_evidence26_exhausted_target_skip`;
  - the run restored valid LLM policy evidence with `llm_rewrite_accepted=2` and `fallback_rewrite_accepted=0`;
  - rewrite events recorded `selector_target_skip:7`, showing that saturated top targets were bypassed;
  - the true-improvement hard gate correctly rejected the run because `llm_true_improved_count=0`;
  - highlight mix was `sharpe_improved_no_pass_lift:1`;
  - highlighted-but-not-true-improved candidate: `qr_d4f351fd82`, `corr(volume,ret(close,12),72)`, with pass-rate
    delta `0.00` and mean-Sharpe delta `+0.25326526`.
- Refreshed the multi-run selector evidence summary across attempts 4 through 26, excluding the superseded
  `evidence9_policy_guarded` failed directory and retaining `evidence9_policy_guarded_shape_fixed`:
  - runs: `23`;
  - LLM policy evidence runs: `20`;
  - LLM true-improvement evidence runs: `5`;
  - coverage-only trap runs: `2`;
  - highlighted candidate rows: `12`;
  - distinct highlighted candidates: `9`;
  - negative candidate rows: `55`;
  - negative candidate family rows: `17`.
- Ran attempt 27 as an exhausted-target-skip repeat:
  - output: `reports/selector_rewrite_pipeline_llm_v082_evidence27_exhausted_target_skip_repeat`;
  - the run remained valid LLM policy evidence with `llm_rewrite_accepted=3` and `fallback_rewrite_accepted=0`;
  - rewrite events recorded `selector_target_skip:7`, confirming saturated top targets were still bypassed;
  - the true-improvement hard gate correctly rejected the run because `llm_true_improved_count=0`;
  - highlight mix was `sharpe_improved_no_pass_lift:1`;
  - highlighted-but-not-true-improved candidate: `qr_a853a7393b`, `corr(sub(close,open),volume,96)`, with pass-rate
    delta `0.00` and mean-Sharpe delta `+0.19930544`.
- Refreshed the multi-run selector evidence summary across attempts 4 through 27:
  - runs: `24`;
  - LLM policy evidence runs: `21`;
  - LLM true-improvement evidence runs: `5`;
  - negative candidate rows: `58`;
  - negative candidate family rows: `17`.
- Ran attempt 28 with the updated selector negative memory:
  - output: `reports/selector_rewrite_pipeline_llm_v082_evidence28_exhausted_target_skip_repeat`;
  - the run passed the LLM true-improvement hard gate with `llm_rewrite_accepted=4`,
    `fallback_rewrite_accepted=0`, and `llm_true_improved_count=2`;
  - rewrite events recorded `selector_target_skip:7`, so the same saturated top targets were skipped before later
    selector targets were evaluated;
  - true-improved candidates:
    `qr_e23cfc8ae6`, `zscore(std(close,48),144)`, pass-rate delta `+0.80`, mean-Sharpe delta `+1.49835622`;
    `qr_a2cd9fd69f`, `zscore(ema(volume,48),120)`, pass-rate delta `+0.60`, mean-Sharpe delta `+0.77176916`;
  - one additional Sharpe-only/no-pass-lift highlight was recorded for `qr_1a08a872ec`, `zscore(volume,120)`.
- Refreshed the multi-run selector evidence summary across attempts 4 through 28:
  - runs: `25`;
  - LLM policy evidence runs: `22`;
  - LLM true-improvement evidence runs: `6`;
  - coverage-only trap runs: `2`;
  - highlighted candidate rows: `16`;
  - distinct highlighted candidates: `13`;
  - negative candidate rows: `60`;
  - negative candidate family rows: `18`.
- Ran attempt 29 as another exhausted-target-skip repeat:
  - output: `reports/selector_rewrite_pipeline_llm_v082_evidence29_exhausted_target_skip_repeat`;
  - the run remained valid LLM policy evidence with `llm_rewrite_accepted=3` and `fallback_rewrite_accepted=0`;
  - rewrite events recorded `selector_target_skip:7`;
  - the true-improvement hard gate correctly rejected the run because all reviewed candidates were `not_improved`.
- Refreshed the multi-run selector evidence summary across attempts 4 through 29:
  - runs: `26`;
  - LLM policy evidence runs: `23`;
  - LLM true-improvement evidence runs: `6`;
  - negative candidate rows: `63`;
  - negative candidate family rows: `19`.
- Added conflict-aware selector negative memory:
  - `selector_pipeline_negative_candidate_summary.csv` now records family-level true-improved evidence alongside
    negative counts;
  - family-pair blocking no longer blocks an entire parent/candidate family pair when that pair has LLM true-improved
    evidence;
  - exact failed formulas remain disallowed, and pure-negative family-pair blocking remains active.
- Ran attempt 30 with conflict-aware memory:
  - output: `reports/selector_rewrite_pipeline_llm_v082_evidence30_conflict_aware_memory`;
  - the run passed the LLM true-improvement hard gate with `llm_rewrite_accepted=4`,
    `fallback_rewrite_accepted=0`, and `llm_true_improved_count=4`;
  - skipped exhausted targets dropped from `7` to `4`, allowing the price parent `qr_7a765d304b` to be tried again;
  - true-improved candidates:
    `qr_a2cd9fd69f`, `zscore(ema(volume,48),120)`, pass-rate delta `+0.80`, mean-Sharpe delta `+0.44211152`;
    `qr_e23cfc8ae6`, `zscore(std(close,48),144)`, pass-rate delta `+0.60`, mean-Sharpe delta `+1.06153455`;
    `qr_f61439dfd5`, `zscore(ema(volume,24),144)`, pass-rate delta `+0.40`, mean-Sharpe delta `+0.73177118`;
    `qr_1aa34f4735`, `corr(sub(close,open),volume,48)`, pass-rate delta `+0.40`, mean-Sharpe delta `+0.68271748`.
- Refreshed the multi-run selector evidence summary across attempts 4 through 30:
  - runs: `27`;
  - LLM policy evidence runs: `24`;
  - LLM true-improvement evidence runs: `7`;
  - coverage-only trap runs: `2`;
  - highlighted candidate rows: `20`;
  - distinct highlighted candidates: `17`;
  - negative candidate rows: `63`;
  - negative candidate family rows: `19`.
- Ran attempt 31 as a conflict-aware-memory repeat:
  - output: `reports/selector_rewrite_pipeline_llm_v082_evidence31_conflict_aware_memory_repeat`;
  - the run passed the LLM true-improvement hard gate with `llm_rewrite_accepted=4`,
    `fallback_rewrite_accepted=0`, and `llm_true_improved_count=1`;
  - rewrite events recorded `selector_target_skip:4`, `llm_rewrite:3`, and `rewrite_validator:2`;
  - true-improved candidate:
    `qr_a2cd9fd69f`, `zscore(ema(volume,48),120)`, pass-rate delta `+0.60`, mean-Sharpe delta `+0.77176916`,
    failed asset `BTCUSDT`;
  - the three non-improved LLM candidates added negative evidence for weak short-horizon price reversal, raw volume
    fade, and negative realized-volatility shapes.
- Refreshed the multi-run selector evidence summary across attempts 4 through 31:
  - runs: `28`;
  - LLM policy evidence runs: `25`;
  - LLM true-improvement evidence runs: `8`;
  - coverage-only trap runs: `2`;
  - highlighted candidate rows: `21`;
  - distinct highlighted candidates: `17`;
  - negative candidate rows: `66`;
  - negative candidate family rows: `19`.
- Current interpretation: conflict-aware selector negative memory is still useful after a repeat. It avoids
  over-blocking family pairs with prior true-improved evidence while exact failed formulas and pure-negative family
  blocking continue to suppress repeated failures. The repeated positive remains research-only and requires separate
  walk-forward, admission, portfolio, and manual runtime-publishing review before any runtime consideration.
- Ran attempt 32 as another conflict-aware-memory repeat:
  - output: `reports/selector_rewrite_pipeline_llm_v082_evidence32_conflict_aware_memory_repeat`;
  - the run passed the LLM true-improvement hard gate with `llm_rewrite_accepted=4`,
    `fallback_rewrite_accepted=0`, and `llm_true_improved_count=3`;
  - rewrite events recorded `selector_target_skip:4`, `llm_rewrite:3`, and `rewrite_validator:2`;
  - candidate highlight mix was `true_improved:3|sharpe_improved_no_pass_lift:1`;
  - true-improved candidates:
    `qr_a2cd9fd69f`, `zscore(ema(volume,48),120)`, pass-rate delta `+0.80`, mean-Sharpe delta `+0.44211152`;
    `qr_edd31d7e32`, `zscore(std(ret(close,4),24),120)`, pass-rate delta `+0.60`, mean-Sharpe delta `+0.97526250`;
    `qr_33f1508627`, `zscore(sma(volume,24),96)`, pass-rate delta `+0.60`, mean-Sharpe delta `+0.80809019`;
  - the Sharpe-only/no-pass-lift candidate was `qr_cd595899ee`,
    `zscore(corr(sub(close,open),volume,36),96)`, pass-rate delta `0.00`, mean-Sharpe delta `+0.37866408`;
  - the rewrite validator rejected `neg(zscore(std(ret(close,1),36),144))`, preserving the existing DSL window guard.
- Refreshed the multi-run selector evidence summary across attempts 4 through 32:
  - runs: `29`;
  - LLM policy evidence runs: `26`;
  - LLM true-improvement evidence runs: `9`;
  - coverage-only trap runs: `2`;
  - highlighted candidate rows: `25`;
  - distinct highlighted candidates: `20`;
  - negative candidate rows: `67`;
  - negative candidate family rows: `19`.
- Current interpretation: conflict-aware selector memory has now produced two consecutive hard-gate passes after
  attempt 30. The repeated `zscore(ema(volume,48),120)` candidate is becoming the most stable positive selector
  rewrite artifact, while attempt 32 adds two one-off true-improved candidates that still need repeat evidence. The
  mixed `qr_cd595899ee` row is a reminder that prior formula-level positives are not universally positive across
  parents; parent-specific review should remain part of the selector audit loop.
- Ran attempt 33 as another conflict-aware-memory repeat:
  - output: `reports/selector_rewrite_pipeline_llm_v082_evidence33_conflict_aware_memory_repeat`;
  - the run passed the LLM true-improvement hard gate with `llm_rewrite_accepted=6`,
    `fallback_rewrite_accepted=0`, and `llm_true_improved_count=2`;
  - rewrite events recorded `selector_target_skip:4` and `llm_rewrite:3`, with no LLM candidate requiring validator
    rejection;
  - candidate highlight mix was `true_improved:2`;
  - true-improved candidates:
    `qr_f5f52b2594`, `zscore(sma(volume,36),144)`, pass-rate delta `+1.00`, mean-Sharpe delta `+1.24213645`,
    failed assets `none`;
    `qr_295d2e9ee2`, `zscore(ema(volume,24),120)`, pass-rate delta `+0.60`, mean-Sharpe delta `+0.65493676`;
  - the four not-improved candidates added negative evidence for negative realized-volatility stress, volume
    acceleration, negative slow volume crowding, and negative range stress.
- Refreshed the multi-run selector evidence summary across attempts 4 through 33:
  - runs: `30`;
  - LLM policy evidence runs: `27`;
  - LLM true-improvement evidence runs: `10`;
  - coverage-only trap runs: `2`;
  - highlighted candidate rows: `27`;
  - distinct highlighted candidates: `22`;
  - negative candidate rows: `71`;
  - negative candidate family rows: `19`.
- Current interpretation: the positive selector rewrite evidence is concentrating around smoothed positive
  volume-liquidity regimes. `zscore(sma(volume,36),144)` is now the strongest single highlighted candidate by
  pass-rate delta, but it remains a one-run artifact. Negative variants from the same broad family show the effect is
  sign and smoothing sensitive, so conflict-aware family memory should continue to keep exact negative formulas blocked
  without mechanically banning the whole volume-liquidity family.
- Ran attempt 34 as another conflict-aware-memory repeat:
  - output: `reports/selector_rewrite_pipeline_llm_v082_evidence34_conflict_aware_memory_repeat`;
  - the run passed the LLM true-improvement hard gate with `llm_rewrite_accepted=6`,
    `fallback_rewrite_accepted=0`, and `llm_true_improved_count=4`;
  - rewrite events recorded `selector_target_skip:4` and `llm_rewrite:3`, with no LLM candidate requiring validator
    rejection;
  - candidate highlight mix was `true_improved:4`;
  - true-improved candidates:
    `qr_a2cd9fd69f`, `zscore(ema(volume,48),120)`, pass-rate delta `+0.80`, mean-Sharpe delta `+0.44211152`;
    `qr_c3ccb8e228`, `zscore(std(close,48),120)`, pass-rate delta `+0.60`, mean-Sharpe delta `+0.84810419`;
    `qr_aded180101`, `zscore(ema(volume,24),96)`, pass-rate delta `+0.60`, mean-Sharpe delta `+0.67117528`;
    `qr_6cab970b52`, `zscore(std(close,12),120)`, pass-rate delta `+0.20`, mean-Sharpe delta `+0.29108682`;
  - the two not-improved candidates were volume-acceleration variants:
    `zscore(delta(volume,48),144)` and `zscore(delta(volume,6),96)`.
- Refreshed the multi-run selector evidence summary across attempts 4 through 34:
  - runs: `31`;
  - LLM policy evidence runs: `28`;
  - LLM true-improvement evidence runs: `11`;
  - coverage-only trap runs: `2`;
  - highlighted candidate rows: `31`;
  - distinct highlighted candidates: `25`;
  - negative candidate rows: `73`;
  - negative candidate family rows: `19`.
- Current interpretation: `zscore(ema(volume,48),120)` now has three true-improved highlights against the price
  parent in the aggregate summary, while `qr_cd595899ee` remains the earlier three-repeat cluster. The latest positives
  also reinforce that some range-volatility shapes can help funding-interaction parents, but volume acceleration
  remains repeatedly negative. Keep the selector memory conflict-aware rather than mechanically blocking whole
  volume-liquidity or range-volatility families.
- Ran attempt 35 as another conflict-aware-memory repeat:
  - output: `reports/selector_rewrite_pipeline_llm_v082_evidence35_conflict_aware_memory_repeat`;
  - the run passed the LLM true-improvement hard gate with `llm_rewrite_accepted=5`,
    `fallback_rewrite_accepted=0`, and `llm_true_improved_count=3`;
  - rewrite events recorded `selector_target_skip:4`, `rewrite_validator:1`, and `llm_rewrite:3`;
  - candidate highlight mix was `true_improved:3`;
  - true-improved candidates:
    `qr_3cdea28d1b`, `zscore(ema(volume,36),144)`, pass-rate delta `+1.00`, mean-Sharpe delta `+1.20305771`,
    failed assets `none`;
    `qr_a2cd9fd69f`, `zscore(ema(volume,48),120)`, pass-rate delta `+0.80`, mean-Sharpe delta `+0.44211152`;
    `qr_295d2e9ee2`, `zscore(ema(volume,24),120)`, pass-rate delta `+0.60`, mean-Sharpe delta `+0.65493676`;
  - the two not-improved candidates were range-volatility variants:
    `zscore(std(close,12),120)` and `neg(zscore(std(close,24),120))`.
- Refreshed the multi-run selector evidence summary across attempts 4 through 35:
  - runs: `32`;
  - LLM policy evidence runs: `29`;
  - LLM true-improvement evidence runs: `12`;
  - coverage-only trap runs: `2`;
  - highlighted candidate rows: `34`;
  - distinct highlighted candidates: `26`;
  - negative candidate rows: `75`;
  - negative candidate family rows: `19`.
- Current interpretation: smoothed positive volume participation is the strongest repeated selector rewrite theme.
  `zscore(ema(volume,48),120)` now has four true-improved highlights against the price parent, and
  `zscore(ema(volume,24),120)` has repeated twice for a funding-interaction parent. The 36/144 participation smoother
  now has two all-asset positive variants across attempts 33 and 35: `zscore(sma(volume,36),144)` and
  `zscore(ema(volume,36),144)`. Range-volatility remains mixed, so it should stay conflict-aware rather than
  mechanically blocked or universally preferred.
- Ran attempt 36 as another conflict-aware-memory repeat:
  - output: `reports/selector_rewrite_pipeline_llm_v082_evidence36_conflict_aware_memory_repeat`;
  - the run passed the LLM true-improvement hard gate with `llm_rewrite_accepted=4`,
    `fallback_rewrite_accepted=0`, and `llm_true_improved_count=4`;
  - rewrite events recorded `selector_target_skip:4`, `rewrite_validator:2`, and `llm_rewrite:3`;
  - candidate highlight mix was `true_improved:4`, with no coverage-only or Sharpe-only highlights;
  - true-improved candidates:
    `qr_7a81ad156d`, `zscore(sma(volume,36),120)`, pass-rate delta `+0.80`, mean-Sharpe delta `+1.15668668`;
    `qr_a2cd9fd69f`, `zscore(ema(volume,48),120)`, pass-rate delta `+0.80`, mean-Sharpe delta `+0.44211152`;
    `qr_aded180101`, `zscore(ema(volume,24),96)`, pass-rate delta `+0.60`, mean-Sharpe delta `+0.67117528`;
    `qr_b49066f917`, `zscore(std(close,24),120)`, pass-rate delta `+0.40`, mean-Sharpe delta `+0.79389268`;
  - the rewrite validator rejected `neg(zscore(std(ret(close,4),60),144))` for exceeding the depth limit.
- Refreshed the multi-run selector evidence summary across attempts 4 through 36:
  - runs: `33`;
  - LLM policy evidence runs: `30`;
  - LLM true-improvement evidence runs: `13`;
  - coverage-only trap runs: `2`;
  - highlighted candidate rows: `38`;
  - distinct highlighted candidates: `28`;
  - negative candidate rows: `75`;
  - negative candidate family rows: `19`.
- Current interpretation: attempt 36 is a clean positive repeat. `zscore(ema(volume,48),120)` now has five
  true-improved highlights against the price parent, making it the strongest repeated selector rewrite artifact by
  count. The broader 36-bar smoothed participation family is also strengthening through SMA/EMA and 120/144
  normalization variants. Range-volatility has positive evidence but remains more mixed than smoothed volume, so keep
  conflict-aware memory and exact-formula blocking rather than whole-family blocking.
- Ran attempt 37 as another conflict-aware-memory repeat:
  - output: `reports/selector_rewrite_pipeline_llm_v082_evidence37_conflict_aware_memory_repeat`;
  - the run passed the LLM true-improvement hard gate with `llm_rewrite_accepted=3`,
    `fallback_rewrite_accepted=0`, and `llm_true_improved_count=1`;
  - rewrite events recorded `selector_target_skip:4`, `rewrite_validator:3`, and `llm_rewrite:3`;
  - candidate verdict mix was `not_improved:2|improved:1`;
  - candidate highlight mix was `true_improved:1`, with no coverage-only or Sharpe-only highlights;
  - true-improved candidate:
    `qr_a2cd9fd69f`, `zscore(ema(volume,48),120)`, pass-rate delta `+0.80`, mean-Sharpe delta `+0.44211152`;
  - the two not-improved candidates were volume/range coupling variants:
    `zscore(corr(volume,sub(high,low),72),96)` and `neg(corr(volume,sub(high,low),96))`.
- Refreshed the multi-run selector evidence summary across attempts 4 through 37:
  - runs: `34`;
  - LLM policy evidence runs: `31`;
  - LLM true-improvement evidence runs: `14`;
  - coverage-only trap runs: `2`;
  - highlighted candidate rows: `39`;
  - distinct highlighted candidates: `28`;
  - negative candidate rows: `77`;
  - negative candidate family rows: `19`.
- Current interpretation: attempt 37 is a narrower positive repeat. The price-parent
  `zscore(ema(volume,48),120)` row now has six true-improved highlights, and the same formula has eight
  true-improved highlights across the two reviewed parent contexts. Smoothed positive volume participation remains the
  strongest repeated selector rewrite theme. The new negative volume/range coupling rows reinforce that
  range-volatility should remain conflict-aware rather than mechanically preferred or mechanically banned.

## Next Session Prompt

If continuing this work in a new session, use this prompt:

```text
Please continue QuantumRandy from docs/QuantumRandy_research_roadmap.md.
Do not start by rereading every paper. First inspect the current repo state, then implement the next milestone:
multi-asset robustness evaluation for accepted factors, reusing the walk-forward validation outputs where helpful.
Keep source edits scoped and run tests before finishing.
```
