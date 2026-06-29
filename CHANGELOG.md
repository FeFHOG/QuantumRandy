# QuantumRandy Changelog

## Unreleased

### Factor-mining correctness

- Preserve rolling warm-up values as missing observations instead of replacing them with zero.
- Compute IC, rank IC, and directional win rate only from valid factor/forward-return pairs, and report `predictive_observations` for auditability.
- Validate operator arity and rolling-window semantics before an LLM proposal reaches the backtester.
- Preserve MCTS node indexes when purging rejected factors from the zoo and skip proposals already present in the search tree.
- Replace the uncentered raw RSI seed with a rolling z-scored RSI factor.
- Add regression tests for warm-up handling, formula validation, predictive samples, and MCTS purge integrity.

## 2026-05-20 — v0.7 "Funding Rate Renaissance"

### Problem
MCTS mining was producing 74% killed factors. Root cause analysis:

1. **Proposal templates ignored funding_rate** — only 1 of 15 local templates used it. Most hardcoded `close`, missing the most effective alpha source.
2. **FSA banned effective patterns** — `zscore(funding_rate,...)` became a frequent subtree and was banned, preventing further funding_rate exploration.
3. **Zoo bloat** — killed factors accumulated in zoo, making the homogeneity gate progressively stricter (malicious cycle).
4. **Templates didn't respond to dimension hints** — MCTS correctly identified weak dimensions, but templates generated unrelated random formulas.

### Changes

#### 1. Proposal templates overhaul (`proposals.py`)
- Split fields into `PRICE_FIELDS` (close/high/low — for ret/delta/rsi) and `ALL_FIELDS` (includes funding_rate/volume — for sma/ema/zscore/corr)
- Funding rate weighted at 35% in field selection (was equal 20%)
- Each dimension now has 5 templates (was 3), all dimension-relevant:
  - **effectiveness**: added `div(funding_rate, std(close))` and `corr(funding_rate, ret(close))`
  - **stability**: added `ema(funding_rate)`, funding rate EMA crossover
  - **turnover**: added ultra-slow funding rate, volume-normalized base formula
  - **diversity**: added `corr(funding_rate, volume)`, `div(funding_rate, sma(volume))`
  - **overfit_risk**: uses `{af}` (any field) broadly, added `rsi(price_field)`
- Result: funding_rate presence in proposals went from 14% → 46%

#### 2. FSA whitelist (`mcts.py`)
- Funding rate patterns are now whitelisted — `funding_rate` subtrees cannot be banned
- This prevents FSA from killing the most effective signal category

#### 3. Auto-purge (`research.py`, `mcts.py`)
- Research loop now auto-purges killed non-seed factors after each brutal filter pass
- Zoo capped at 50 non-seed entries (prevents homogeneity gate bloat)
- Manual "Purge Killed" button still available in dashboard

#### 4. Kill diagnosis (`lab.py`, `dashboard.py`)
- Added `kill_reasons()` — returns which of the 4 gates killed a factor
- `row_from_alpha()` now includes `kill_reasons` in leaderboard output
- Dashboard shows Kill Breakdown panel with per-gate kill counts
- Detail modal highlights which specific gates killed each factor
- Hover tooltip on KILL status shows gate names

#### 5. One-click backtest (`scripts/backtest_all.py`)
- New script: backtests ALL factors from any leaderboard.json
- Outputs consolidated CSV + JSON with train/val/blind metrics
- Supports --blind flag for 2026 out-of-sample validation
- Usage: `python scripts/backtest_all.py --leaderboard reports/research_live/leaderboard.json`

### Files Changed
| File | Change |
|------|--------|
| `quantumrandy/proposals.py` | Full rewrite — 25 templates with proper field typing |
| `quantumrandy/mcts.py` | FSA whitelist + zoo size cap |
| `quantumrandy/research.py` | Auto-purge in research loop |
| `quantumrandy/lab.py` | Added `kill_reasons()`, updated `row_from_alpha()` |
| `quantumrandy/dashboard.py` | Kill breakdown panel, simplified modal, tooltip |
| `scripts/backtest_all.py` | NEW — one-click factor backtest |
