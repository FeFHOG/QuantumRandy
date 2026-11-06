# Server Connection Record, 2026-11-06

Date: 2026-11-06 (UTC)

Status: the server can be reached, and the account tested has the network access the daily routine needs, but the
routine is not installed there. Nothing on the server was changed.

This repository is public, so the record leaves out the server's address, host name, account names and authentication
details. The owner keeps them.

## Why

The two forward paper observations (`taker_7d` from 2026-11-06, `taker_30d` from 2026-11-07) run on the owner's server,
not on the research machine, as two daily commands (`PHASE2B_TAKER_30D_FORWARD_PREREGISTRATION.md`, "Run"). On
2026-11-06 the owner registered that server in their coding agent as a remote host (added at 00:59 UTC; connected, with
the agent's server component installed, by 01:06 UTC). This record tests the connection and lists what stands between
the server and the daily routine.

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

## The Server

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
| Scheduler | cron is running and open to the account, which has no crontab; user-level systemd lingering is off |
| Sharing | other services run on the same machine (web, container and proxy workloads) |

## Outbound Reachability From The Server

Each probe is one request or one WebSocket handshake; nothing was recorded or downloaded.

| Endpoint | Needed for | Result |
|---|---|---|
| `fapi.binance.com` REST | nothing (geo-blocked from the research machine) | HTTP 451, blocked here too |
| `data.binance.vision` and its S3 listing | `fetch_daily.py` | HTTP 200, about 0.1 s |
| Binance CMS announcement API | `preregistrations/forward_exclusions.json` | HTTP 200 |
| `fstream.binance.com` liquidations | a future recorder (none yet) | handshake 101, same as the research machine |
| Deribit public API | a future recorder | HTTP 200 |
| Hyperliquid info API | a future recorder | HTTP 200 |
| GitHub over HTTPS | `git clone`, `git pull` | HTTP 200; `git ls-remote` reads this repository |
| PyPI | `pip install` | HTTP 200 on the index; HTTP 200 on a HEAD of a real numpy wheel (cp312, manylinux) |

The first WebSocket probe printed nothing because curl negotiated HTTP/2, which has no Upgrade; with HTTP/1.1 the
handshake succeeds. That was a flaw in the probe, not a block.

## What The Daily Routine Needs

`scripts/xs_forward_taker.py` reads two directories under `../RandysLab-STRICT4H/data/`: `universe_1d_20261105` (219 MB,
daily klines through 2026-10-31) and `forward_1d` (written by `fetch_daily.py`). Both sit under the git-ignored `data/`
directory, so a clone does not bring them.

Missing on the server:

1. **Checkouts.** Both repositories as siblings, on `phase2/cross-sectional`, not `main`: the runner and the
   registrations exist only on that branch. `RESEARCH_V1_3_SERVER_OBSERVATION_RUNBOOK.md` stops unless both repositories
   are on `main`, so the new routine needs its own procedure.
2. **Environment.** A virtualenv from `requirements.txt`, which installs both repositories editable and pins numpy
   2.5.4, pandas 3.1.1 and scipy 1.18.1 on Python 3.12 and later (the same pins as on 3.13).
3. **Base data.** `universe_1d_20261105`, copied from the research machine or rebuilt with
   `RandysLab-STRICT4H/scripts/fetch_universe.py` (resumable, checksum-verified). `forward_1d` is rebuilt by
   `fetch_daily.py` from 2026-11-01.
4. **A resource check.** The first run should record peak memory and duration: 1.9 GiB is available beside the other
   services, and the runner's footprint has not been measured.
5. **A schedule.** Cron works for the account. The archive publishes each day's files the next morning (UTC), and the
   record is rebuilt from the archive on every run, so a missed day costs nothing. An overlap lock (`flock`) keeps two
   runs from overlapping, as the v1.3 wrapper did.

## Not Done

Nothing was installed, cloned, copied or scheduled on the server, no file was created there, and no data was recorded.
Scheduling stays the owner's call.

## Open Questions For The Owner

- Which account and directory will host the routine.
- Whether the server follows `phase2/cross-sectional` or `main` once the phase branches are merged; no pull request to
  `main` is open for them.
- What to do with the earlier v1.3 setup, which this record could not see.
