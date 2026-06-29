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
    dashboard.py            # HTTP dashboard backend + kill breakdown
    walk_forward.py         # Rolling train/validation/test survival validation
    universe.py             # Multi-asset robustness evaluation
    config.py               # YAML config reader
    data.py                 # OHLCV/funding data loader
    io_utils.py             # File I/O utilities
  scripts/
    mine.py                 # Batch alpha mining
    eval_formula.py         # Evaluate a single formula
    backtest_all.py         # One-click backtest ALL factors
    walk_forward.py         # Walk-forward validation for fixed formulas
    eval_universe.py        # Evaluate fixed formulas across repeated asset configs
    run_btc.py              # One-command BTC mining
    dashboard.py            # Launch research dashboard
    check_deepseek.py       # Verify DeepSeek connectivity
  tests/
    test_smoke.py
  CHANGELOG.md              # Version history
```

## Formula DSL

Available fields: `open`, `high`, `low`, `close`, `volume`, `funding_rate`

Available operators (21): `abs`, `add`, `corr`, `delay`, `delta`, `div`, `ema`, `log`, `max`, `min`, `mul`, `neg`, `rank`, `ret`, `rsi`, `sign`, `sma`, `sqrt`, `std`, `sub`, `zscore`

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
cd ../AutoQuant
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

## Kill Diagnosis

The dashboard shows a **Kill Breakdown** panel — which of the 4 brutal-filter gates kills the most factors. Hover any KILL badge to see the specific gates that failed. Click a factor row for a detail modal with per-gate actual values vs thresholds.

Kill reasons are stored in `leaderboard.json` → `kill_reasons` field (e.g. `["predictive_power", "autoquant_audit"]`).

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
# Copy config, update symbol + data paths
copy configs\btcusdt.yaml configs\ethusdt.yaml
# Edit: symbol, ohlcv_csv, funding_csv

# Run
python scripts\mine.py --config configs\ethusdt.yaml --iterations 50 --out reports\eth_mcts
```

## Limitations

- Research/backtest framework only — not a live trading system.
- Currently default data is BTCUSDT 4h only; multi-asset evaluation requires additional asset configs/data files.
- No multi-asset portfolio or alpha combination yet.

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
