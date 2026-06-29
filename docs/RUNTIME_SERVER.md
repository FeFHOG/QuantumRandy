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
