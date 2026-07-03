# QuantumRandy 48h Server Paper Trial Runbook

Last updated: 2026-06-30

This runbook is the operator-facing checklist for the first 48-hour QuantumRandy paper runtime trial on an Ubuntu
server. It is intentionally narrow: deploy the existing paper observation loop, preserve logs and reports, and do not
change active strategies unless fixing a runtime bug.

## Safety Boundary

- Paper runtime only.
- No live exchange orders.
- No exchange trading API keys.
- Binance feeder uses public market-data endpoints only.
- Runtime and dashboard stay bound to `127.0.0.1` or a private interface.
- Do not expose runtime admin endpoints to the public internet.
- Do not auto-promote mined factors or portfolio research artifacts into runtime.
- Do not edit active runtime factors during the first 48 hours unless fixing a runtime bug.
- Future live execution remains Phase 6 planning only and must not be implemented during this beta trial.

## Prerequisites

- Ubuntu 22.04 or newer.
- Python 3.10 or newer.
- `git`, `tmux`, and outbound HTTPS access to Binance public futures endpoints.
- Checked-out repositories in a common parent directory:

```text
QuantumRandy/
RandysLab-STRICT4H/
```

Use the `QuantumRandy` branch intended for the beta trial:

```bash
cd QuantumRandy
git fetch --all --prune
git checkout codex/multi-asset-robustness
git status --short --branch
```

The expected branch line is:

```text
## codex/multi-asset-robustness...origin/codex/multi-asset-robustness
```

## Install

```bash
cd QuantumRandy
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
mkdir -p logs reports/runtime_live
```

Set long random local-only tokens. Do not commit them, paste them into tickets, or reuse them for exchange accounts.

```bash
cat > ~/.quantumrandy-paper-env <<EOF
export QR_HOME="$(pwd)"
export QUANTUMRANDY_ADMIN_TOKEN="$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
)"
export QUANTUMRANDY_INGEST_TOKEN="$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
)"
EOF
chmod 600 ~/.quantumrandy-paper-env
source ~/.quantumrandy-paper-env
```

This operator-owned shell snippet sits outside the repo so detached shells and future restarts can load the same runtime
tokens without committing secrets.

## Preflight

Run the read-only server preflight before starting long-running processes:

```bash
source .venv/bin/activate
source ~/.quantumrandy-paper-env 2>/dev/null || true
python scripts/preflight_server.py --require-tokens
```

Expected result:

```text
Overall status: `PASS`
```

The preflight must confirm:

- runtime binding is local/private;
- admin and ingest token environment variables are present;
- `configs/runtime_factors.json` is valid;
- feeder posts to local runtime and uses Binance public market data;
- monitor reads local runtime;
- RandysLab baseline export is available or clearly reported as missing;
- no exchange trading keys are required.

Do not continue a 48-hour trial from a failed preflight.

## Start With tmux

For the first trial, `tmux` is sufficient and easy to inspect. Use a real process manager later if the beta run needs to
be repeated for longer windows.

Start the paper runtime:

```bash
tmux new-session -d -s qr-runtime \
  "source ~/.quantumrandy-paper-env && cd \"\$QR_HOME\" && source .venv/bin/activate && \
   python scripts/runtime_server.py --config configs/runtime_server.yaml 2>&1 | tee -a logs/runtime_server.log"
```

Start the public-data feeder:

```bash
tmux new-session -d -s qr-feeder \
  "source ~/.quantumrandy-paper-env && cd \"\$QR_HOME\" && source .venv/bin/activate && \
   python scripts/binance_feeder.py --config configs/binance_feeder.yaml 2>&1 | tee -a logs/binance_feeder.log"
```

Start the read-only monitor:

```bash
tmux new-session -d -s qr-monitor \
  "source ~/.quantumrandy-paper-env && cd \"\$QR_HOME\" && source .venv/bin/activate && \
   python scripts/runtime_monitor.py --config configs/runtime_monitor.yaml 2>&1 | tee -a logs/runtime_monitor.log"
```

Start the read-only dashboard on localhost:

```bash
tmux new-session -d -s qr-dashboard \
  "source ~/.quantumrandy-paper-env && cd \"\$QR_HOME\" && source .venv/bin/activate && \
   python scripts/runtime_dashboard.py --monitor-config configs/runtime_monitor.yaml --host 127.0.0.1 --port 8790 \
   2>&1 | tee -a logs/runtime_dashboard.log"
```

Confirm all four sessions exist:

```bash
tmux ls
```

Expected sessions:

```text
qr-runtime
qr-feeder
qr-monitor
qr-dashboard
```

## Smoke Checks

After 1-2 minutes, check runtime health:

```bash
curl -s http://127.0.0.1:8787/health
curl -s http://127.0.0.1:8787/v1/factors
curl -s http://127.0.0.1:8787/v1/snapshot
```

Run one monitor poll if the long-running monitor has not written output yet:

```bash
python scripts/runtime_monitor.py --config configs/runtime_monitor.yaml --once
```

Expected output files:

```text
reports/runtime_live/snapshots.jsonl
reports/runtime_live/latest_snapshot.json
reports/runtime_live/runtime_report_YYYYMMDD.md
```

View the dashboard from a workstation through SSH:

```bash
ssh -L 8790:127.0.0.1:8790 user@server
```

Then open:

```text
http://127.0.0.1:8790
```

The dashboard is read-only and must not expose admin update controls.

## During The 48 Hours

Preserve these files as audit artifacts:

- `logs/runtime_server.log`
- `logs/binance_feeder.log`
- `logs/runtime_monitor.log`
- `logs/runtime_dashboard.log`
- `reports/runtime_live/snapshots.jsonl`
- `reports/runtime_live/latest_snapshot.json`
- `reports/runtime_live/runtime_report_YYYYMMDD.md`

Operational checks:

```bash
tmux ls
tail -n 80 logs/runtime_server.log
tail -n 80 logs/binance_feeder.log
tail -n 80 logs/runtime_monitor.log
tail -n 80 logs/runtime_dashboard.log
curl -s http://127.0.0.1:8787/health
```

Do not change runtime strategies during the 48-hour window. If a runtime bug forces a restart or patch, record:

- UTC time;
- git commit before and after;
- command used to stop and restart;
- reason for the change;
- whether any 4h bars were missed.

## Stop Or Restart

Stop all trial processes:

```bash
tmux kill-session -t qr-dashboard
tmux kill-session -t qr-monitor
tmux kill-session -t qr-feeder
tmux kill-session -t qr-runtime
```

Restart by repeating the `tmux new-session` commands above. The feeder can safely repost its recent lookback window
because the runtime replaces bars by timestamp.

## 48h Acceptance Review

After the trial window, inspect:

- all four processes remained running or any restart was documented;
- no unexpected public binding appeared in runtime or dashboard configuration;
- feeder accepted completed 4h BTCUSDT bars without gaps;
- stale-bar flags are reasonable for the 4h schedule;
- `snapshots.jsonl` has a continuous monitor trail;
- `latest_snapshot.json` is readable;
- daily runtime Markdown report is readable;
- paper equity, drawdown, PnL, costs, and exposure fields are present;
- RandysLab baseline comparison is present when `baseline_summary.json` is available;
- no active runtime strategies were changed during the trial.

Use these quick checks:

```bash
wc -l reports/runtime_live/snapshots.jsonl
python -m json.tool reports/runtime_live/latest_snapshot.json >/tmp/latest_snapshot.pretty.json
ls -lh reports/runtime_live/
grep -R "ERROR\|Traceback\|Exception" logs || true
```

If the 48-hour paper loop is stable, the next action is to prepare v0.8 beta release notes. Algorithm work such as
multi-asset robustness, walk-forward portfolios, LLM proposal schema v2, failure memory, and Pareto MCTS should resume
only after the runtime trial result is documented.
