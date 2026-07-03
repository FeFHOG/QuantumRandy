# Research v1.3 Server Paper Observation Runbook

Date: 2026-07-04

Status: server-agent handoff ready; paper observation not started.

This runbook is the server-side execution companion to
`docs/RESEARCH_V1_3_PAPER_OBSERVATION_PROTOCOL.md`. It prepares and observes the v1.3 survivor family on paper only.
It is not a runtime deployment, not a runtime publish payload, not live trading, not RandyPortfolio, and not factor
admission.

## Operational Verdict

```text
research_v1_3_server_observation_runbook_ready_paper_only
```

Use this file, not the archived runtime-beta runbooks, as the handoff document for a server agent.

## Hard Boundaries

The server agent must stop and report instead of crossing any of these boundaries:

- Do not run `scripts/publish_factors.py`.
- Do not edit `configs/runtime_factors.json`.
- Do not start QuantumRandy runtime server processes for this observation.
- Do not create a RandyPortfolio repository or directory.
- Do not connect exchange private keys.
- Do not place live orders.
- Do not change the v1.3 formula, variants, exposure cap, volatility cap, or declared scope.
- Do not treat ETH/SOL/BNB/AVAX diagnostics as approval for non-BTC deployment.
- Do not run selector evidence61 or add new formula base fields.

## Expected Repository Layout

Run from a common parent that contains both repositories:

```text
Quant/
  QuantumRandy/
  RandysLab-STRICT4H/
```

The QuantumRandy side supplies the frozen v1.3 research export and starter packet. The RandysLab side supplies the
strict judge and frozen variant execution semantics.

## Server-Agent Prompt

Copy this prompt to the server agent:

```text
You are executing Research v1.3 paper observation only.

Read QuantumRandy/docs/RESEARCH_V1_3_SERVER_OBSERVATION_RUNBOOK.md first and follow it exactly. Keep the work
paper-only and research-only. Do not run publish_factors.py, do not edit configs/runtime_factors.json, do not start the
runtime server, do not create RandyPortfolio, do not connect exchange private keys, and do not place live orders.

Prepare the v1.3 paper-observation starter packet, verify its manifest, then run the frozen RandysLab paper observation
sweep for BTCUSDT 4h only. Record the output paths, latest data timestamps, fresh bar count since the observation start,
primary and paired diagnostic signal/exposure intent, drawdown/fee/funding metrics if available, and any data gaps.

If any required repo, data file, Python dependency, or command is missing, stop and report the exact missing item.
Do not patch project code or invent a runtime deployment path.
```

## Phase 0: Repo And Data Sanity

From the common parent:

```bash
export WORKSPACE="${WORKSPACE:-$PWD}"

git -C "$WORKSPACE/QuantumRandy" fetch origin
git -C "$WORKSPACE/QuantumRandy" status --short --branch
git -C "$WORKSPACE/RandysLab-STRICT4H" fetch origin
git -C "$WORKSPACE/RandysLab-STRICT4H" status --short --branch
git -C "$WORKSPACE/QuantumRandy" branch --show-current
git -C "$WORKSPACE/RandysLab-STRICT4H" branch --show-current
```

If either repo is not on `main`, or either repo has unexpected tracked changes, stop and report the status before
proceeding. Ignored `reports/` outputs are allowed.

If both repos are clean and on `main`, fast-forward them:

```bash
git -C "$WORKSPACE/QuantumRandy" pull --ff-only
git -C "$WORKSPACE/RandysLab-STRICT4H" pull --ff-only
git -C "$WORKSPACE/QuantumRandy" rev-parse --short HEAD
git -C "$WORKSPACE/RandysLab-STRICT4H" rev-parse --short HEAD
```

Confirm the BTCUSDT data files exist on the server:

```bash
test -s "$WORKSPACE/RandysLab-STRICT4H/data/BTCUSDT_4h.csv"
test -s "$WORKSPACE/RandysLab-STRICT4H/data/BTCUSDT_funding.csv"
```

If the data feed is stale or missing, stop and report `paper_observation_blocked_missing_fresh_data`.

## Phase 1: Prepare The QuantumRandy Starter Packet

Use the server's Python. If the server uses a virtualenv, set `PY` to that interpreter before running these commands.

```bash
cd "$WORKSPACE/QuantumRandy"
PY="${PY:-python3}"

$PY -m pytest tests/test_v1_3_funding_adjacent_respec.py -q
$PY scripts/prepare_v1_3_paper_observation.py
```

Verify the generated manifest:

```bash
$PY - <<'PY'
import json
from pathlib import Path

p = Path("reports/paper_observation/research_v1_3_funding_adjacent/paper_observation_manifest.json")
m = json.loads(p.read_text(encoding="utf-8"))
assert m["artifact_type"] == "quantumrandy_v1_3_paper_observation_start_packet"
assert m["status"] == "ready_not_started"
assert m["frozen_rules"]["scope"] == "BTCUSDT_4h"
assert m["frozen_rules"]["out_of_scope_policy"] == "diagnostic_only"
assert m["frozen_rules"]["formula"] == "neg(zscore(div(ema(funding_rate,12),div(sub(max(high,96),min(low,96)),close)),120))"
assert m["safety"]["research_only"] is True
assert m["safety"]["paper_only"] is True
assert m["safety"]["not_runtime_publish_payload"] is True
assert m["safety"]["does_not_update_runtime"] is True
assert m["safety"]["does_not_create_randyportfolio"] is True
assert m["safety"]["no_live_trading"] is True
assert len(m["candidates"]) == 2
print("v1.3 paper starter verified:", p)
PY
```

This phase prepares ignored files under `reports/paper_observation/research_v1_3_funding_adjacent/`. It does not start
observation by itself.

## Phase 2: Run The Frozen RandysLab Paper Sweep

Run the sweep from RandysLab with the frozen v1.3 knobs:

```bash
cd "$WORKSPACE/RandysLab-STRICT4H"
PY="${PY:-python3}"
OBS_DATE="$(date -u +%Y-%m-%d)"
OUT="reports/paper_observation/research_v1_3_funding_adjacent/server_daily_${OBS_DATE}"

$PY scripts/sweep_factor_candidates.py \
  --candidates ../QuantumRandy/reports/factor_candidate_exports/research_v1_3_funding_adjacent_scoped_respec/factor_candidates.jsonl \
  --out "$OUT" \
  --asset BTCUSDT:data/BTCUSDT_4h.csv:data/BTCUSDT_funding.csv \
  --window all \
  --threshold 0.0 \
  --signal-mode long_short \
  --signal-mode long_flat \
  --exposure-cap 0.5 \
  --volatility-cap 'calm_vol_lte_1p5:zscore(std(close,48),144):1.5'
```

The expected observation rows are:

```text
qr_v13_funding_range_norm_001::thr_0p0_long_short_cap_0p5_calm_vol_lte_1p5
qr_v13_funding_range_norm_001::thr_0p0_long_flat_cap_0p5_calm_vol_lte_1p5
```

Filter the sweep output to those two rows and attach the result to the daily note. The sweep may evaluate the broader
v1.3 export, but the observation decision is restricted to the two reviewed survivor rows above.

Use this filter command:

```bash
OUT="$OUT" "$PY" - <<'PY'
import os
from pathlib import Path

import pandas as pd

out = Path(os.environ["OUT"])
detail = pd.read_csv(out / "factor_candidate_sensitivity_detail.csv")
targets = detail[
    detail["candidate_id"].eq("qr_v13_funding_range_norm_001")
    & detail["variant_id"].isin(
        [
            "thr_0p0_long_short_cap_0p5_calm_vol_lte_1p5",
            "thr_0p0_long_flat_cap_0p5_calm_vol_lte_1p5",
        ]
    )
].copy()
assert len(targets) == 2, f"expected two v1.3 survivor rows, got {len(targets)}"
targets.to_csv(out / "v1_3_survivor_observation_rows.csv", index=False)
print("filtered survivor rows:", out / "v1_3_survivor_observation_rows.csv")
PY
```

## Phase 3: Daily Note

Create or update a daily note under ignored QuantumRandy reports:

```bash
cd "$WORKSPACE/QuantumRandy"
OBS_DATE="$(date -u +%Y-%m-%d)"
mkdir -p reports/paper_observation/research_v1_3_funding_adjacent/daily
cp reports/paper_observation/research_v1_3_funding_adjacent/DAILY_NOTE_TEMPLATE.md \
  "reports/paper_observation/research_v1_3_funding_adjacent/daily/${OBS_DATE}.md"
```

Fill the note with:

- latest complete BTCUSDT 4h bar timestamp;
- latest funding timestamp;
- fresh BTCUSDT 4h bars since observation start;
- primary long-short signal and paper exposure intent;
- paired long-flat diagnostic signal and paper exposure intent;
- paper equity, drawdown, fees, and funding impact if the local paper sweep provides them;
- data gaps, delayed funding updates, or formula parse issues;
- boundary exceptions attempted, which should remain `none`.

Do not commit ignored daily notes unless explicitly requested. Return the note path and the filtered sweep output path
to the coordinating agent.

## Phase 4: Minimum Window And Stop Rules

Minimum window:

```text
30 calendar days or at least 120 fresh BTCUSDT 4h bars, whichever is longer.
```

Extend the observation if fewer than 20 non-flat signal events occur, the data feed is unstable, or the server misses
material 4h bars.

Stop early and report failure if:

- live trading, private keys, runtime publishing, or runtime server startup is attempted;
- formula, variant, exposure cap, volatility cap, or scope mutation is required to make the result look viable;
- data gaps make the observation unrecoverable;
- drawdown exceeds the v1.3 robustness envelope without a documented data issue;
- diagnostics are treated as deployment approval outside BTCUSDT 4h.

## Final Return Package

After the minimum window, return these items to the coordinating agent:

- QuantumRandy and RandysLab commit SHAs used on the server;
- starter manifest verification output;
- daily note paths or archive;
- filtered RandysLab sweep outputs for the two survivor rows, especially `v1_3_survivor_observation_rows.csv`;
- final bar count and observation date range;
- boundary confirmation;
- one recommended verdict:

```text
research_v1_3_paper_observation_pass_ready_for_third_project_planning
research_v1_3_paper_observation_extend
research_v1_3_paper_observation_fail_return_to_research
```

The coordinating agent writes `docs/RESEARCH_V1_3_PAPER_OBSERVATION_REPORT.md`; the server agent should not publish
runtime factors or open RandyPortfolio planning on its own.
