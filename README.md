# QuantumRandy

LLM + MCTS formulaic alpha mining for crypto perpetual futures (BTC, ETH, SOL, etc.).

Inspired by [arXiv-2505.11122v3](https://arxiv.org/abs/2505.11122) — LLM generates and refines alpha formulas, MCTS (Monte Carlo Tree Search) guides the search, and rigorous backtesting scores each formula.

## Quick Start

```powershell
# 1. Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Set your API key
copy .env.example .env
notepad .env          # fill in your DeepSeek key

# 3. Verify DeepSeek
python scripts\check_deepseek.py

# 4. Mine factors
python scripts\mine.py --config configs\btcusdt.yaml --iterations 50 --use-llm --out reports\btc_llm_50
```

Without LLM (local template-based generator):

```powershell
python scripts\mine.py --config configs\btcusdt.yaml --iterations 20 --out reports\btc_mcts
```

## Project Structure

```text
QuantumRandy/
  .env.example              # API key template (real .env is gitignored)
  requirements.txt
  pyproject.toml
  configs/
    btcusdt.yaml            # BTCUSDT 4h config
  quantumrandy/
    expression.py           # Formula DSL parser & evaluator
    backtest.py             # 4h perpetual strict backtest
    evaluator.py            # Multi-dim factor scoring
    mcts.py                 # MCTS search with UCT + zoo cap
    fsa.py                  # Frequent subtree avoidance
    llm.py                  # DeepSeek API + local fallback
    proposals.py            # Template engine (46% funding_rate coverage)
    lab.py                  # 4-gate brutal filter + kill diagnosis
    research.py             # Background research session + auto-purge
    dashboard.py            # HTTP dashboard backend + kill/research review panels
    walk_forward.py         # Rolling train/validation/test survival validation
    universe.py             # Multi-asset robustness evaluation
    data_readiness.py       # Read-only multi-asset config/data coverage checks
    portfolio.py            # Fixed-weight factor portfolio research
    portfolio_walk_forward.py # Fixed-blend portfolio walk-forward validation
    pareto.py               # Pareto archive ranking for multi-objective alpha review
    config.py               # YAML config reader
    data.py                 # OHLCV/funding data loader
    io_utils.py             # File I/O utilities
  scripts/
    mine.py                 # Batch alpha mining
    eval_formula.py         # Evaluate a single formula
    backtest_all.py         # One-click backtest ALL factors
    data_readiness.py       # Check local asset configs/CSVs before universe runs
    walk_forward.py         # Walk-forward validation for fixed formulas
    eval_universe.py        # Evaluate fixed formulas across repeated asset configs
    build_portfolio.py      # Build fixed-weight accepted-factor portfolios
    portfolio_walk_forward.py # Validate fixed portfolio blends across rolling windows
    build_failure_memory.py # Build research-only memory from killed candidates
    build_admission.py      # Build research-only factor admission decisions
    run_btc.py              # One-command BTC mining
    dashboard.py            # Launch research dashboard
    check_deepseek.py       # Verify DeepSeek connectivity
  tests/
    test_smoke.py
  CHANGELOG.md              # Version history
```

## Formula DSL

Available fields: `open`, `high`, `low`, `close`, `volume`, `funding_rate`

Available operators (28): `abs`, `add`, `clip`, `corr`, `decay_linear`, `delay`, `delta`, `div`, `ema`,
`kurtosis`, `log`, `max`, `min`, `mul`, `neg`, `rank`, `ret`, `rsi`, `sign`, `skew`, `sma`, `sqrt`, `std`,
`sub`, `ts_argmax`, `ts_argmin`, `winsorize`, `zscore`

Examples:

```text
zscore(sub(sma(close,12), sma(close,48)), 48)   # MA crossover, z-scored
neg(zscore(funding_rate, 42))                     # Funding rate mean-reversion
zscore(corr(ret(close,6), ret(volume,6), 48), 72) # Price-volume correlation
```

On 4h bars: window `42` ≈ 1 week, `180` ≈ 1 month.

## Evaluate a Single Formula

```powershell
python scripts\eval_formula.py --config configs\btcusdt.yaml --formula "zscore(sub(sma(close,12),sma(close,48)),48)"
```

## Research Dashboard

24h research workbench with a web UI:

```powershell
python scripts\dashboard.py --config configs\btcusdt.yaml --out reports\research_live --port 8765
```

Open `http://127.0.0.1:8765` — controls for start/stop/backup/emergency-stop.

## Deterministic Runtime Server

An isolated Ubuntu-compatible HTTP service can execute approved single-factor and weighted multi-factor paper
strategies against pushed market bars. It has no intelligence or exchange order integration. Simulated starting capital
is hard-capped at USD 1,000 per strategy, with configurable latency, slippage jitter, adverse slippage, signal noise, and
missed fills. Factor and strategy manifests support atomic, generation-guarded hot updates.

See [docs/RUNTIME_SERVER.md](docs/RUNTIME_SERVER.md) for the API and local startup instructions.

## 4-Gate Brutal Filter

Every candidate factor passes through four gates:

| Gate | Criterion | Threshold |
|------|-----------|-----------|
| Predictive power | Rank IC AND directional win rate | IC ≥ 0.01 AND win rate ≥ 0.49 |
| Homogeneity | Max correlation to library | < 0.70 |
| Friction audit | Sharpe after taker fees + slippage + funding | ≥ 0.30 |
| Lifespan | Validation Sharpe + IC half-life | Sharpe ≥ 0, halflife ≥ 1 bar |

All thresholds are configurable in `configs/btcusdt.yaml` → `filter`.

## Key Design Decisions

- **Max depth limit**: formulas capped at 5 depth / 6 operators — no meaningless nesting like `Log(Abs(Exp(...)))`.
- **Forced explanation**: LLM must output ≥60 char economic rationale with finance keywords (momentum, reversal, volatility, etc.).
- **Occam's razor**: exponential operator penalty — when two formulas backtest similarly, the simpler one wins.
- **API cooldown**: minimum 30s between DeepSeek calls to control cost (~$1-2 per 8h night run).
- **Funding rate focus**: local templates weight funding_rate at 35% (up from 20%) — it has the highest pass rate through the brutal filter.
- **FSA whitelist**: funding_rate patterns are exempt from subtree bans — effective structures shouldn't be blocked.
- **Auto-purge**: killed non-seed factors removed from zoo each iteration to prevent homogeneity drift.

## Blind Validation (2026 Out-of-Sample)

The dashboard includes a one-click blind validation feature. Download fresh data and test any factor:

```powershell
# Download 2026 blind data
cd ../RandysLab-STRICT4H
python scripts/fetch_binance.py --start 2026-01-01 --end 2026-05-01 --file-prefix BTCUSDT_2026 --outdir data

# Start dashboard, click any factor → "一键验证(2026盲测)"
cd ../QuantumRandy  
python scripts/dashboard.py --config configs/btcusdt.yaml --out reports/research_live --port 8765
```

The validation popup shows:
- 12 metrics (Sharpe, CAGR, maxDD, IC, Rank IC, win rate, turnover, trades, etc.)
- Equity curve + drawdown chart (Chart.js)
- Trade-by-trade ledger with PnL
- SURVIVED / WEAK / DEAD verdict with color coding

Results are also batch-saved to `reports/research_live/blind_2026_validation.json`.

## One-Click Backtest All Factors

Backtest every factor in a leaderboard at once:

```powershell
python scripts/backtest_all.py --leaderboard reports/research_live/leaderboard.json --config configs/btcusdt.yaml --out reports/backtest_all

# With 2026 blind out-of-sample validation
python scripts/backtest_all.py --leaderboard reports/research_live/leaderboard.json --blind
```

Outputs `all_factors_backtest.csv` + `.json` with train/val/blind metrics, pass/kill status, and kill reasons.

## Walk-Forward Validation

Validate fixed formulas across rolling train/validation/test windows:

```powershell
python scripts\walk_forward.py `
  --leaderboard reports\research_live\leaderboard.json `
  --config configs\btcusdt.yaml `
  --passed-only `
  --out reports\walk_forward
```

You can also validate ad hoc formulas:

```powershell
python scripts\walk_forward.py `
  --formula "neg(zscore(funding_rate,42))" `
  --formula "zscore(sub(sma(close,12),sma(close,48)),48)" `
  --out reports\walk_forward_probe
```

Default windows are `18m train / 6m validation / 3m test`, stepped every 3 months. A segment passes when
`rank_ic >= filter.min_rank_ic`, `directional_win_rate >= filter.min_directional_win_rate`, and
`sharpe >= filter.min_validation_sharpe`. A window survives only when both validation and test pass.

Outputs:

- `walk_forward_details.csv`: formula x window x segment metrics.
- `walk_forward_summary.csv`: formula-level survival ranking.
- `walk_forward_windows.json`: exact date boundaries.
- `WALK_FORWARD_REPORT.md`: concise human-readable report.

## Multi-Asset Robustness

Before running a universe evaluation, check whether the expected local configs and CSV files are ready:

```powershell
python scripts\data_readiness.py --out reports\data_readiness
```

By default this checks `BTCUSDT`, `ETHUSDT`, `SOLUSDT`, `BNBUSDT`, and `AVAXUSDT` config paths under `configs/`. It
does not download market data, call exchange APIs, publish factors, or touch the runtime. Outputs:

- `data_readiness.csv`: config/data coverage, window coverage, 4h gap checks, and funding alignment.
- `data_readiness_manifest.json`: machine-readable readiness artifact.
- `DATA_READINESS_REPORT.md`: concise runbook-style summary.
- `DATA_FETCH_RUNBOOK.md`: read-only RandysLab fetch command plan for missing or under-covered local data.

If new asset configs are missing, scaffold research-only configs from the BTC template:

```powershell
python scripts\data_readiness.py --write-missing-configs --out reports\data_readiness
```

The scaffolded configs point at `../..\RandysLab-STRICT4H\data\<SYMBOL>_4h.csv` and
`../..\RandysLab-STRICT4H\data\<SYMBOL>_funding.csv`; the script still only checks local files and never fetches market
data.

Evaluate the same formula set across repeated asset configs:

```powershell
python scripts\eval_universe.py `
  --config configs\btcusdt.yaml `
  --config configs\ethusdt.yaml `
  --config configs\solusdt.yaml `
  --leaderboard reports\research_live\leaderboard.json `
  --passed-only `
  --out reports\universe_eval
```

You can also probe ad hoc formulas:

```powershell
python scripts\eval_universe.py `
  --config configs\btcusdt.yaml `
  --formula "neg(zscore(funding_rate,42))" `
  --formula "zscore(sub(sma(close,12),sma(close,48)),48)" `
  --out reports\universe_probe
```

Outputs:

- `universe_details.csv`: every formula x asset metric row.
- `universe_summary.csv`: formula-level robustness ranking.
- `universe_report.json`: run metadata plus machine-readable ranking.
- `UNIVERSE_REPORT.md`: concise human-readable report.

## Alpha Portfolio Research

Build fixed-weight factor portfolios from accepted formulas:

```powershell
python scripts\build_portfolio.py `
  --config configs\btcusdt.yaml `
  --leaderboard reports\research_live\leaderboard.json `
  --passed-only `
  --out reports\portfolio
```

You can also probe ad hoc formulas:

```powershell
python scripts\build_portfolio.py `
  --formula "neg(zscore(funding_rate,42))" `
  --formula "zscore(ret(close,6),48)" `
  --out reports\portfolio_probe
```

The builder evaluates each factor, applies correlation filtering, and reports equal-weight, rank-IC-weighted, and
Sharpe-weighted variants. Outputs are research artifacts only, not runtime publish payloads:

- `portfolio_factors.csv`: evaluated factor metrics.
- `portfolio_selection.csv`: correlation-filter decisions.
- `portfolio_summary.csv`: portfolio-level metrics.
- `portfolio_contribution.csv`: leave-one-factor-out contribution analysis.
- `portfolio_manifest.json`: research-only components and weights.
- `PORTFOLIO_REPORT.md`: concise human-readable report.

## Portfolio Walk-Forward

Validate a fixed portfolio blend from `scripts\build_portfolio.py` across rolling train/validation/test windows:

```powershell
python scripts\portfolio_walk_forward.py `
  --config configs\btcusdt.yaml `
  --portfolio-manifest reports\portfolio\portfolio_manifest.json `
  --portfolio-factors reports\portfolio\portfolio_factors.csv `
  --portfolio-id equal_weight_accepted `
  --out reports\portfolio_walk_forward
```

This checks whether a selected fixed blend is stable across windows. It does not retrain weights, publish runtime
strategies, or mutate active paper runtime state.

Outputs:

- `portfolio_walk_forward_details.csv`: portfolio x window x segment metrics.
- `portfolio_walk_forward_summary.csv`: portfolio-level survival and stability summary.
- `portfolio_walk_forward_manifest.json`: research-only run metadata.
- `PORTFOLIO_WALK_FORWARD_REPORT.md`: concise human-readable report.

## Failure Memory

Build a research-only memory artifact from killed candidates:

```powershell
python scripts\build_failure_memory.py `
  --leaderboard reports\research_live\leaderboard.json `
  --out reports\failure_memory
```

The output preserves schema-v2 proposal context, failed gates, metrics, and shared subtree fingerprints. It is for
negative examples and targeted rewrites only; it is not a runtime publish payload.

To feed this memory back into LLM proposals, set `prompt.failure_memory_path` in the research config:

```yaml
prompt:
  failure_memory_path: "reports/failure_memory"
  failure_memory_examples: 5
  failure_memory_clusters: 5
```

Outputs:

- `failure_memory.csv`: failed formula rows with schema-v2 proposal context.
- `failure_clusters.csv`: repeated failed subtree patterns.
- `failure_memory_manifest.json`: machine-readable artifact metadata.
- `FAILURE_MEMORY_REPORT.md`: concise human-readable report.

When research mining runs, killed non-seed factors can also trigger a small targeted rewrite pass. The rewrite prompt is
gate-aware:

- `predictive_power`: change information source, sign, or horizon.
- `homogeneity`: keep only the broad hypothesis and change field/operator structure.
- `friction_audit`: reduce turnover through slower windows or smoothing.
- `lifetime`: prefer slower, more regime-stable transforms.

## Factor Admission

Combine leaderboard, walk-forward, universe, and portfolio evidence into one research-only admission report:

```powershell
python scripts\build_admission.py `
  --leaderboard reports\research_live\leaderboard.json `
  --walk-forward-summary reports\walk_forward\walk_forward_summary.csv `
  --universe-summary reports\universe_eval\universe_summary.csv `
  --portfolio-selection reports\portfolio\portfolio_selection.csv `
  --portfolio-walk-forward-summary reports\portfolio_walk_forward\portfolio_walk_forward_summary.csv `
  --out reports\admission
```

Outputs:

- `admission_decisions.csv`: per-factor gates, evidence, score, and decision.
- `admission_manifest.json`: machine-readable policy and run summary.
- `ADMISSION_REPORT.md`: concise human-readable report.

## Kill Diagnosis

The dashboard shows a **Kill Breakdown** panel — which of the 4 brutal-filter gates kills the most factors. Hover any KILL badge to see the specific gates that failed. Click a factor row for a detail modal with per-gate actual values vs thresholds.

Kill reasons are stored in `leaderboard.json` -> `kill_reasons` field (e.g. `["predictive_power", "friction_audit"]`).

The dashboard also shows a read-only **Research Review** panel when admission, failure-memory, or portfolio
walk-forward artifacts exist under `reports/`. It summarizes admission decisions, repeated failed subtree clusters, and
fixed-blend walk-forward stability. When `pareto_archive.json` exists, it also summarizes the current nondominated alpha
front. This panel does not mutate runtime or publish strategies.

## Pareto Archive

Every MCTS save writes a research-only Pareto archive alongside the usual zoo/tree artifacts:

- `pareto_archive.csv`: all zoo alphas with Pareto rank and objective metrics.
- `pareto_archive.json`: machine-readable nondominated front and objective metadata.

The first archive ranks tradeoffs across Rank IC, Sharpe, turnover, drawdown, diversity, simplicity, and operator count.
It is a review aid only; MCTS selection still uses the configured scalar reward.

## v0.7 "Funding Rate Renaissance" (2026-05-20)

Key improvements after diagnosing the 74% kill rate:

- **Proposal templates**: funding_rate presence 14% → 46%. Fields split into price (close/high/low) for ret/delta/rsi and any-field for sma/ema/zscore/corr.
- **FSA whitelist**: funding_rate subtree patterns can no longer be banned.
- **Auto-purge**: killed non-seed factors are automatically removed from zoo each iteration.
- **Zoo cap**: max 50 non-seed entries to prevent homogeneity gate inflation.
- **Kill diagnosis**: `lab.kill_reasons()` returns which gates killed a factor.

See `CHANGELOG.md` for full details.

## Extending to Other Coins

```powershell
# Scaffold or refresh research configs without downloading data
python scripts\data_readiness.py --write-missing-configs --out reports\data_readiness

# Run
python scripts\mine.py --config configs\ethusdt.yaml --iterations 50 --out reports\eth_mcts
```

## Limitations

- Research/backtest framework only — not a live trading system.
- Currently default data is BTCUSDT 4h only; multi-asset evaluation requires additional asset configs/data files.
- Portfolio construction and portfolio walk-forward validation are fixed-weight research only; runtime publication still
  requires manual review/publishing.

## Configuration

All parameters in `configs/btcusdt.yaml`:

```yaml
mcts:
  exploration_weight: 1.4
  proposal_count: 4       # candidates per iteration
  eval_workers: 4         # parallel backtest threads
  max_formula_depth: 5
  max_formula_operators: 6
  complexity_penalty: 0.02
  api_cooldown_seconds: 30

filter:
  min_rank_ic: 0.01
  min_directional_win_rate: 0.49
  max_corr: 0.70
  min_cost_sharpe: 0.30
  min_validation_sharpe: 0.0
  min_halflife_bars: 1

prompt:
  temperature: 0.75        # LLM temperature
```

## License

MIT
