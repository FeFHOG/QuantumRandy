# Server Connection And Setup Record, 2026-11-06

Date: 2026-11-06 (UTC)

Status: the server is reachable and the daily routine is installed and tested there; the first scheduled run is
2026-11-06 11:07 UTC. The connection test was read-only; the setup that followed is described under "Setup".

This repository is public, so the record leaves out the server's address, host name, account names and authentication
details. The owner keeps them.

## Why

The two forward paper observations (`taker_7d` from 2026-11-06, `taker_30d` from 2026-11-07) run on the owner's server,
not on the research machine, as two daily commands (`PHASE2B_TAKER_30D_FORWARD_PREREGISTRATION.md`, "Run"). On
2026-11-06 the owner registered that server in their coding agent as a remote host (added at 00:59 UTC; connected, with
the agent's server component installed, by 01:06 UTC). This record tests the connection, then installs and tests the
daily routine.

## Connection Test

Run from the research machine between about 01:10 and 01:25 UTC. Read-only: every command only reports state.

| Check | Result |
|---|---|
| SSH port reachable | yes |
| Host keys against the ones the research machine already trusts | identical for all three key types |
| Login with a non-root, key-based account | works |
| A second key-based account configured earlier | rejected: its key is not accepted |
| Files of the earlier v1.3 observation | not visible: the administrator's home is closed to the non-root account |
| Registration in the coding agent | present; installed; last seen online at 01:06 UTC; **not exercised** (see below) |

The test used the research machine's own SSH client with the non-root account. A session cannot switch itself onto a
registered remote host, so the registration's own connection path was not exercised, and no stored credential was used.

## The Server Before The Setup

| Item | Value |
|---|---|
| OS | Ubuntu 24.04 LTS, x86-64 |
| CPU, memory | 2 vCPU; 3.8 GiB RAM with 1.9 GiB available; 1.4 GiB swap |
| Disk | 16 GB free of 35 GB |
| Clock | UTC, NTP-synchronised |
| Python | 3.12.3 system interpreter (`.python-version` says 3.13; `requires-python` is `>=3.10`) |
| Python packages | PyYAML and requests present; numpy, pandas, scipy, ccxt and pytest absent |
| Virtualenv | `python3 -m venv` works without root; the system pip refuses installs outside a venv (PEP 668) |
| Tools | git 2.43, curl, flock, tmux, screen, jq, gcc; no `uv` |
| Scheduler | cron is running and open to the account, which had no crontab; user-level systemd lingering is off |
| Sharing | other services run on the same machine (web, container and proxy workloads) |

## Outbound Reachability From The Server

Each probe is one request or one short WebSocket connection; nothing was recorded or downloaded.

| Endpoint | Needed for | Result |
|---|---|---|
| `fapi.binance.com` REST | nothing (geo-blocked from the research machine) | HTTP 451, blocked here too |
| `data.binance.vision` and its S3 listing | `fetch_daily.py` | HTTP 200, about 0.1 s |
| Binance CMS announcement API | `preregistrations/forward_exclusions.json` | HTTP 200 |
| `fstream.binance.com` liquidations | a data recorder | `/ws`: handshake only, no data; `/market/ws`: delivers |
| Deribit public API | a data recorder | HTTP 200 |
| Hyperliquid info API | a data recorder | HTTP 200 |
| GitHub over HTTPS | `git clone`, `git pull` | HTTP 200; `git ls-remote` reads this repository |
| PyPI | `pip install` | HTTP 200 on the index; HTTP 200 on a HEAD of a real numpy wheel (cp312, manylinux) |

A completed handshake proves nothing for Binance's futures streams: the legacy `/ws` and `/stream` paths answer 101 and
then never send a byte, even for `aggTrade`, from this server and from the research machine alike. Only the `/market`
routes deliver. The streams were therefore checked by counting messages, not by the handshake.

## Setup

Done afterwards on 2026-11-06 with the same non-root account, inside its home directory. No system package, no other
service and nothing outside the home directory was touched. The owner chose to leave the earlier v1.3 setup alone: it
is not needed and lies outside the account's permissions.

`scripts/xs_forward_taker.py` reads `universe_1d_20261105` (219 MB) and `forward_1d` under
`../RandysLab-STRICT4H/data/`. Both sit under the git-ignored `data/` directory, so a clone does not bring them.

- **Layout.** One directory holds both repositories as siblings, on `phase2/cross-sectional` and pinned at the commits
  of the registrations (QuantumRandy `dcf4d7e`, RandysLab `4977fe4`); a virtualenv built from `requirements.txt`
  (Python 3.12.3; numpy 2.5.4, pandas 3.1.1 and scipy 1.18.1, the same versions as on the research machine); the base
  data; a wrapper script; and the logs.
- **Base data.** Copied from the research machine and checked file by file against a SHA-256 manifest (3,659 files).
  `forward_1d` then grows with each run.
- **Wrapper.** `run_forward_daily.sh`, kept outside the repository, runs the two commands in order from the
  QuantumRandy checkout. It only schedules and logs: it never pulls or edits code, refuses to run if a tracked file in
  either repository is modified, logs both HEADs on every run, and uses `flock` (no overlapping runs), `nice` and
  `ionice` (the machine is shared), time limits, and GNU `time` for wall time and peak memory. The exit statuses and the
  log path go to `last_run.json`.
- **Schedule.** Cron, daily at 11:07 UTC (19:07 Asia/Shanghai). Binance uploaded the daily klines of 2026-11-01 to
  2026-11-04 as one batch each morning, between 08:03 and 09:36 UTC (four symbols sampled; each day's files landed
  within two minutes of each other); 11:07 leaves about 90 minutes after the latest. Both commands are idempotent and
  the record is rebuilt from the archive on every run, so a missed or repeated run costs nothing.

## Verification

- **Same results.** On identical inputs the server's `reports/forward_taker_7d` and `reports/forward_taker_30d` (four
  files each) equal the research machine's, apart from line endings; the registration SHA-256s agree.
- **Download path.** A scratch fetch of two symbols equals the copied data.
- **Cron.** A one-shot entry made cron run the wrapper at 02:00 UTC, in cron's minimal environment; both commands exited
  0. The fetch took 8.5 s with 100 MB peak memory and the runner 47.7 s with 142 MB (1.9 GiB was available). The entry
  was removed afterwards.

## What To Expect

- The first scheduled run, 2026-11-06 11:07 UTC, is still a dry run for both observations (data through 2026-11-05).
  `taker_7d`'s first P&L day, 2026-11-06, appears in the run of 2026-11-07, and `taker_30d`'s in the run after it.
- No day is final before its month's funding file is published, a few days after the month ends, so STATUS.md shows only
  the provisional preview through November. That follows the registrations; it is not a fault.

## Operating Notes

- Nothing pulls. Code changes only by the owner's decision, for instance a registered bug fix listed in a registration's
  Changes table; the HEADs in each log show when code moved.
- To check a run: `last_run.json` and `latest.log` in the logs directory, and STATUS.md under each
  `reports/forward_<factor>/`.
- The records are rebuilt from the archive and the code, so any machine can recreate them.

## Open Questions For The Owner

- Whether the server follows `phase2/cross-sectional` or `main` once the phase branches are merged; no pull request to
  `main` is open for them. Merging does not change the server unless someone pulls there.
- How a failed run should reach the owner. The routine writes logs and `last_run.json` only; there is no alert.
