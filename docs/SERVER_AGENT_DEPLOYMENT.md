# Server Agent Deployment Notes

Last updated: 2026-06-30

This note is the minimal handoff for running the QuantumRandy paper observation loop on a server. It is intentionally
operational and conservative. The server agent should not add trading features while following this document.

## Scope

Run four local processes:

1. `scripts/runtime_server.py`
2. `scripts/binance_feeder.py`
3. `scripts/runtime_monitor.py`
4. `scripts/runtime_dashboard.py`

The first deployment target is BTCUSDT 4h Binance USD-M perpetual public market data, approved runtime factors from
`configs/runtime_factors.json`, read-only paper reports under `reports/runtime_live/`, and a local read-only dashboard.

## Hard Safety Rules

- Do not place live orders.
- Do not add exchange trading API keys.
- Do not expose admin endpoints to the public internet.
- Do not auto-promote research or mined factors into runtime.
- Do not modify research/mining algorithms while debugging the paper runtime.
- Bind the runtime to `127.0.0.1` or a private interface unless separate firewalling and operational controls are
  deliberately added.

The Binance feeder uses public market-data endpoints only. It does not need exchange credentials.

## Server Baseline

- Ubuntu 22.04 or newer.
- Python 3.10 or newer.
- Persistent disk for logs and reports.
- Outbound network access to Binance public futures endpoints.
- A process manager such as `systemd`, `supervisor`, or `tmux` for the first smoke run.

## Install

```bash
cd QuantumRandy
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Use long random values for both tokens. Keep the admin token local to the runtime host.

```bash
export QUANTUMRANDY_ADMIN_TOKEN='replace-with-a-long-random-admin-token'
export QUANTUMRANDY_INGEST_TOKEN='replace-with-a-different-long-random-ingest-token'
```

## Preflight

Before starting the long-running paper loop, run the read-only preflight:

```bash
python scripts/preflight_server.py --require-tokens
```

It checks local/private runtime binding, environment-token configuration, runtime manifest validity, public-data feeder
settings, monitor baseline availability, and the absence of exchange trading-key requirements. It does not start the
runtime server, ingest market bars, submit admin updates, or place orders.

## Start The Paper Loop

Start each command in its own managed process.

```bash
python scripts/runtime_server.py --config configs/runtime_server.yaml
```

```bash
python scripts/binance_feeder.py --config configs/binance_feeder.yaml
```

```bash
python scripts/runtime_monitor.py --config configs/runtime_monitor.yaml
```

```bash
python scripts/runtime_dashboard.py --monitor-config configs/runtime_monitor.yaml --host 127.0.0.1 --port 8790
```

For a one-shot smoke test, add `--once` to the feeder and monitor commands.

View the dashboard from a workstation with an SSH tunnel, for example:

```bash
ssh -L 8790:127.0.0.1:8790 user@server
```

Then open `http://127.0.0.1:8790`. The dashboard reads monitor output files only. It has no admin update endpoint and
does not place orders.

## Health Checks

```bash
curl http://127.0.0.1:8787/health
curl http://127.0.0.1:8787/v1/factors
curl http://127.0.0.1:8787/v1/snapshot
```

Expected first-run behavior:

- `/health` returns `status: ok`.
- `factor_count` and `strategy_count` match `configs/runtime_factors.json`.
- `latest_timestamp` is populated after the feeder posts at least one completed 4h bar.
- Re-running the feeder over its lookback window does not duplicate stored timestamps.

## Outputs To Preserve

The monitor writes:

- `reports/runtime_live/snapshots.jsonl`
- `reports/runtime_live/latest_snapshot.json`
- `reports/runtime_live/runtime_report_YYYYMMDD.md`

Keep process stdout/stderr logs together with these files. They are part of the paper-run audit trail. The dashboard is
a read-only view over the same files.

## Factor Updates

Do not edit runtime factors directly during the first smoke period unless fixing a runtime bug.

When a reviewed research leaderboard is ready, use `scripts/publish_factors.py` from an operator-controlled shell. The
publisher is manual by default and only submits when `--submit` is explicitly provided. Runtime updates are guarded by
`expected_generation`; HTTP 409 means another update landed first and the proposal must be regenerated.

## RandysLab Baseline Comparison

Keep RandysLab baseline exports nearby as control artifacts. They are not trading signals for the runtime server and
must not be auto-published into QuantumRandy.

A typical layout is:

```text
QuantumRandy/reports/runtime_live/
RandysLab/reports/quantumrandy_baselines/
```

Use the runtime daily report for live paper observations and RandysLab exported baseline summaries for the traditional
strategy floor.

`configs/runtime_monitor.yaml` may point at the RandysLab export:

```yaml
baseline:
  summary_path: "../RandysLab-STRICT4H/reports/quantumrandy_baselines/baseline_summary.json"
```

The monitor only reads this file and renders a comparison table in `runtime_report_YYYYMMDD.md`. If the path is absent on
the server, fix the path or generate the RandysLab export; do not treat baseline rows as approved runtime strategies.

## Paper Blend Promotion Checklist

Before submitting any portfolio blend to the runtime paper server:

- Confirm the source artifact is `quantumrandy_portfolio_research`, not a live runtime manifest.
- Review `PORTFOLIO_REPORT.md`, `portfolio_summary.csv`, `portfolio_contribution.csv`, and the publisher audit.
- Compare the selected blend against the RandysLab baseline export for the same symbol and window when available.
- Confirm every component factor passed the intended admission gates, including the friction audit gate.
- Confirm the blend has a small fixed component set with explicit weights and no automatic mining dependency.
- Run `scripts/publish_factors.py` without `--submit` first and inspect the generated payload.
- Submit only from an operator-controlled shell with `--submit` after the audit is accepted.
- Record the runtime generation before and after the update, plus the reason for promotion.
