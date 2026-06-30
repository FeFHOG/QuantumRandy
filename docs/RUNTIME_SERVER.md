# Deterministic Factor Runtime Server

The runtime server executes approved QuantumRandy formulas against externally supplied market bars. It contains no LLM,
MCTS, factor discovery, order routing, exchange credentials, or live-trading capability.

## Safety boundary

- Paper simulation only. The server cannot submit, cancel, or query exchange orders.
- Initial simulated capital is hard-capped at USD 1,000 per strategy.
- The default listener is `127.0.0.1:8787`.
- Market ingestion and administrative hot updates use separate tokens.
- Factor and strategy updates are validated and committed as one atomic generation.
- Execution noise is deterministic for a given strategy seed, so a run can be reproduced.

## Ubuntu-compatible startup

Python 3.10 or newer is required.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export QUANTUMRANDY_ADMIN_TOKEN='replace-with-a-long-random-value'
export QUANTUMRANDY_INGEST_TOKEN='replace-with-a-different-long-random-value'
python scripts/preflight_server.py --require-tokens
python scripts/runtime_server.py --config configs/runtime_server.yaml
```

This starts the service but does not deploy it or expose it to the public internet.

## API

Read-only endpoints:

- `GET /health`: process health, active generation, factor count, strategy count, and latest bar.
- `GET /v1/factors`: the complete active factor and strategy manifest.
- `GET /v1/snapshot`: latest factor signals, simulated strategy exposures, equity, PnL, costs, and metrics.

Market ingestion:

```bash
curl -X POST http://127.0.0.1:8787/v1/market/bars \
  -H 'Content-Type: application/json' \
  -H "X-Ingest-Token: $QUANTUMRANDY_INGEST_TOKEN" \
  -d '{
    "timestamp":"2026-06-29T12:00:00Z",
    "open":61000,"high":61500,"low":60750,"close":61300,
    "volume":1250,"funding_rate":0.0001
  }'
```

The request may also be `{"bars": [...]}` or a top-level JSON array. Timestamps must be timezone-aware. Re-sending a
timestamp replaces that bar, which supports updating an unfinished candle without duplicating it.

## Single-factor and multi-factor strategies

A strategy has one or more weighted factor components. One component is reported as `single_factor`; two or more are
reported as `multi_factor`. Component signals are combined by normalized absolute weight before the execution model is
applied.

```json
{
  "strategy_id": "funding_momentum_blend",
  "initial_capital_usd": 1000.0,
  "components": [
    {"factor_id": "funding_reversal_42", "weight": 0.65},
    {"factor_id": "price_momentum_6", "weight": 0.35}
  ],
  "execution_model": {
    "latency_bars": 2,
    "max_exposure_abs": 0.75,
    "exposure_threshold": 0.20,
    "base_slippage_bps": 1.5,
    "slippage_jitter_bps": 3.0,
    "adverse_slippage_bps": 5.0,
    "signal_noise_std": 0.08,
    "fill_probability": 0.95,
    "seed": 29
  }
}
```

The adverse execution model supports bar latency, bounded exposure, baseline slippage, random slippage jitter, an
always-adverse slippage surcharge, signal noise, and missed rebalance attempts. Trading fees and funding costs are also
deducted. No simulated strategy may start with more than USD 1,000.

## Controlled hot update

Read the current generation, then submit a complete factor and strategy configuration:

```bash
curl http://127.0.0.1:8787/v1/factors

curl -X PUT http://127.0.0.1:8787/v1/admin/config \
  -H 'Content-Type: application/json' \
  -H "X-Admin-Token: $QUANTUMRANDY_ADMIN_TOKEN" \
  --data-binary @new-runtime-config.json
```

`new-runtime-config.json` must contain `expected_generation`, `factors`, and `strategies`. A stale generation returns
HTTP 409. Invalid formulas, duplicate IDs, missing factor references, capital above USD 1,000, or invalid execution
settings reject the entire update. A successful update is atomically persisted and becomes the next generation.

`POST /v1/admin/reload` with `{"expected_generation": N}` revalidates the on-disk manifest before switching.

## Data ownership

The server intentionally uses push ingestion. A separate collector may read a public exchange feed, a licensed data
vendor, or recorded test data and post normalized bars to this service. Keeping collection outside the executor makes
the execution process deterministic and prevents exchange-specific networking from becoming a hidden trading path.

## Binance 4h feeder

The first public-data collector is `scripts/binance_feeder.py`. It pulls recent Binance USDT perpetual 4h candles and
funding history, aligns the latest prior funding rate to each bar, then posts normalized bars to the runtime ingest API.
It does not contain strategy logic and cannot place orders.

```bash
export QUANTUMRANDY_INGEST_TOKEN='same-token-used-by-runtime'
python scripts/binance_feeder.py --config configs/binance_feeder.yaml --once
```

For a long-running process, omit `--once`:

```bash
python scripts/binance_feeder.py --config configs/binance_feeder.yaml
```

By default the feeder posts only completed 4h candles. Re-posting a recent lookback window is safe because the runtime
replaces bars with the same timestamp. This lets the process recover from restarts or short data outages without keeping
local state.

## Runtime monitor

The lightweight monitor polls `/health` and `/v1/snapshot`, appends every observation to JSONL, writes the latest
snapshot, and renders a daily Markdown paper report.

```bash
python scripts/runtime_monitor.py --config configs/runtime_monitor.yaml --once
```

For long-running monitoring, omit `--once`:

```bash
python scripts/runtime_monitor.py --config configs/runtime_monitor.yaml
```

Default outputs are written under `reports/runtime_live/`:

- `snapshots.jsonl`: append-only runtime observations.
- `latest_snapshot.json`: latest health and snapshot payload.
- `runtime_report_YYYYMMDD.md`: daily human-readable paper report.

The monitor only reads runtime APIs. It cannot update factors and cannot place orders.

### RandysLab baseline comparison

The monitor can optionally render a RandysLab control-group table in the daily report. Configure the exported
`baseline_summary.json` path in `configs/runtime_monitor.yaml`:

```yaml
baseline:
  summary_path: "../RandysLab-STRICT4H/reports/quantumrandy_baselines/baseline_summary.json"
```

This is read-only report context. RandysLab baseline exports are not QuantumRandy runtime publish payloads and must not
bypass the manual factor or portfolio promotion flow. If the file is missing, the monitor still writes the runtime report
with a load-error note instead of mutating runtime state.

## Suggested first server run

Use three separate shells or process-manager units:

```bash
# 1. Paper runtime
export QUANTUMRANDY_ADMIN_TOKEN='long-random-admin-token'
export QUANTUMRANDY_INGEST_TOKEN='long-random-ingest-token'
python scripts/runtime_server.py --config configs/runtime_server.yaml

# 2. Public market-data feeder
export QUANTUMRANDY_INGEST_TOKEN='same-ingest-token'
python scripts/binance_feeder.py --config configs/binance_feeder.yaml

# 3. Read-only paper monitor
python scripts/runtime_monitor.py --config configs/runtime_monitor.yaml
```

Keep the runtime bound to `127.0.0.1` or a private interface unless authentication, firewalling, and operational
controls are deliberately added.

## Manual factor publishing

Research output should not automatically mutate the paper runtime. Use `scripts/publish_factors.py` to build an auditable
runtime update from a `leaderboard.json` file.

Dry-run proposal:

```bash
python scripts/publish_factors.py \
  --leaderboard reports/research_live/leaderboard.json \
  --runtime-manifest configs/runtime_factors.json \
  --max-factors 5 \
  --out reports/runtime_publish/proposed_runtime_config.json
```

This writes:

- `proposed_runtime_config.json`: complete payload with `expected_generation`, `factors`, and `strategies`.
- `proposed_runtime_config_audit.md`: human-readable selection audit.

After reviewing the audit, submit to a running runtime server:

```bash
export QUANTUMRANDY_ADMIN_TOKEN='same-admin-token-used-by-runtime'
python scripts/publish_factors.py \
  --leaderboard reports/research_live/leaderboard.json \
  --runtime-url http://127.0.0.1:8787 \
  --max-factors 5 \
  --out reports/runtime_publish/proposed_runtime_config.json \
  --submit
```

The publisher fetches the current runtime generation before submitting. If another update lands first, the runtime
rejects stale updates with HTTP 409. This is deliberate: review the current manifest and rerun the publisher.

### Portfolio research proposal

Portfolio research artifacts from `scripts/build_portfolio.py` can also be converted into a reviewable runtime proposal.
This remains a manual dry run unless `--submit` is explicitly provided.

`scripts/build_portfolio.py` can include RandysLab baseline rows in `PORTFOLIO_REPORT.md` with the report-only
`--baseline-summary` option:

```bash
python scripts/build_portfolio.py \
  --leaderboard reports/research_live/leaderboard.json \
  --out reports/portfolio \
  --baseline-summary ../RandysLab-STRICT4H/reports/quantumrandy_baselines/baseline_summary.json
```

The baseline comparison is a control-group section only. It is written into the research manifest as provenance, but it
does not change selected portfolio weights and it is not accepted by the runtime publisher as a strategy definition.

```bash
python scripts/publish_factors.py \
  --portfolio-manifest reports/portfolio/portfolio_manifest.json \
  --portfolio-factors reports/portfolio/portfolio_factors.csv \
  --portfolio-id equal_weight_accepted \
  --runtime-manifest configs/runtime_factors.json \
  --out reports/runtime_publish/portfolio_proposal.json
```

This writes a complete runtime config payload plus an audit file. It does not call the runtime admin API without
`--submit`. Review the source portfolio report, factor metrics, contribution analysis, and audit before submitting.

## Local end-to-end paper trial

Use `scripts/run_paper_trial.py` to exercise the full local paper path without touching the checked-in runtime manifest
or any exchange endpoint:

```bash
python scripts/run_paper_trial.py \
  --portfolio-manifest reports/portfolio/portfolio_manifest.json \
  --portfolio-factors reports/portfolio/portfolio_factors.csv \
  --portfolio-id equal_weight_accepted \
  --out reports/paper_trial
```

The trial starts a localhost runtime on an ephemeral port, copies the runtime manifest into the output directory,
submits the reviewed portfolio proposal to that temporary runtime, pushes local historical bars from the research config,
and runs the monitor once. Outputs include `paper_trial_summary.json`, the proposal/audit files, the temporary runtime
manifest, and a runtime monitor report.
