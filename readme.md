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
    mcts.py                 # MCTS search with UCT
    fsa.py                  # Frequent subtree avoidance
    llm.py                  # DeepSeek API + local fallback
    proposals.py            # Template-based formula generator
    lab.py                  # 4-gate brutal filter
    research.py             # Background research session
    dashboard.py            # HTTP dashboard backend
    config.py               # YAML config reader
    data.py                 # OHLCV/funding data loader
    io_utils.py             # File I/O utilities
  scripts/
    mine.py                 # Batch alpha mining
    eval_formula.py         # Evaluate a single formula
    run_btc.py              # One-command BTC mining
    dashboard.py            # Launch research dashboard
    check_deepseek.py       # Verify DeepSeek connectivity
  tests/
    test_smoke.py
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
- Currently default data is BTCUSDT 4h only.
- No multi-asset portfolio, walk-forward validation, or alpha combination yet.

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
