from __future__ import annotations

import bisect
import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib import request

import pandas as pd
import requests


BINANCE_DEFAULT_BASE_URL = "https://fapi.binance.com"


@dataclass(frozen=True)
class BinanceFeederConfig:
    runtime_url: str = "http://127.0.0.1:8787"
    ingest_token_env: str = "QUANTUMRANDY_INGEST_TOKEN"
    base_url: str = BINANCE_DEFAULT_BASE_URL
    symbol: str = "BTCUSDT"
    interval: str = "4h"
    lookback_bars: int = 120
    include_unclosed: bool = False
    poll_seconds: float = 300.0
    request_timeout_seconds: float = 20.0
    retries: int = 5
    retry_sleep_seconds: float = 1.0
    proxy: str | None = None


def config_from_dict(raw: dict[str, Any]) -> BinanceFeederConfig:
    runtime = raw.get("runtime") or {}
    binance = raw.get("binance") or {}
    polling = raw.get("polling") or {}
    return BinanceFeederConfig(
        runtime_url=str(runtime.get("url", "http://127.0.0.1:8787")).rstrip("/"),
        ingest_token_env=str(runtime.get("ingest_token_env", "QUANTUMRANDY_INGEST_TOKEN")),
        base_url=str(binance.get("base_url", BINANCE_DEFAULT_BASE_URL)).rstrip("/"),
        symbol=_market_id(str(binance.get("symbol", "BTCUSDT"))),
        interval=str(binance.get("interval", "4h")),
        lookback_bars=int(binance.get("lookback_bars", 120)),
        include_unclosed=bool(binance.get("include_unclosed", False)),
        poll_seconds=float(polling.get("poll_seconds", 300.0)),
        request_timeout_seconds=float(polling.get("request_timeout_seconds", 20.0)),
        retries=int(polling.get("retries", 5)),
        retry_sleep_seconds=float(polling.get("retry_sleep_seconds", 1.0)),
        proxy=binance.get("proxy"),
    )


def run_feeder(config: BinanceFeederConfig, *, once: bool = False) -> None:
    session = requests.Session()
    if config.proxy:
        session.proxies.update({"http": config.proxy, "https": config.proxy})
    token = os.environ.get(config.ingest_token_env, "")
    if not token:
        raise RuntimeError(f"Set non-empty {config.ingest_token_env} before starting the feeder")

    while True:
        bars = fetch_recent_bars(session, config)
        if bars:
            result = post_bars(config.runtime_url, token, bars, timeout=config.request_timeout_seconds)
            print(
                "posted "
                f"{len(bars)} bars; runtime stored={result.get('stored_bars')} "
                f"latest={result.get('latest_timestamp')}",
                flush=True,
            )
        else:
            print("no completed bars available to post", flush=True)
        if once:
            return
        time.sleep(config.poll_seconds)


def fetch_recent_bars(session: requests.Session, config: BinanceFeederConfig) -> list[dict[str, Any]]:
    klines = _get_json(
        session,
        f"{config.base_url}/fapi/v1/klines",
        {
            "symbol": config.symbol,
            "interval": config.interval,
            "limit": max(1, min(config.lookback_bars, 1500)),
        },
        timeout=config.request_timeout_seconds,
        retries=config.retries,
        retry_sleep_seconds=config.retry_sleep_seconds,
    )
    if not isinstance(klines, list):
        raise RuntimeError("Binance klines response was not a list")
    now_ms = int(pd.Timestamp.utcnow().timestamp() * 1000)
    selected = [
        item
        for item in klines
        if config.include_unclosed or (isinstance(item, list) and len(item) > 6 and int(item[6]) < now_ms)
    ]
    if not selected:
        return []
    start_ms = int(selected[0][0]) - 24 * 60 * 60 * 1000
    end_ms = int(selected[-1][6]) + 1
    funding = _get_json(
        session,
        f"{config.base_url}/fapi/v1/fundingRate",
        {
            "symbol": config.symbol,
            "startTime": start_ms,
            "endTime": end_ms,
            "limit": 1000,
        },
        timeout=config.request_timeout_seconds,
        retries=config.retries,
        retry_sleep_seconds=config.retry_sleep_seconds,
    )
    if not isinstance(funding, list):
        raise RuntimeError("Binance funding response was not a list")
    return bars_from_binance(selected, funding)


def bars_from_binance(klines: list[list[Any]], funding_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    funding_times: list[int] = []
    funding_rates: list[float] = []
    for row in sorted(funding_rows, key=lambda item: int(item["fundingTime"])):
        funding_times.append(int(row["fundingTime"]))
        funding_rates.append(float(row["fundingRate"]))

    bars = []
    for row in sorted(klines, key=lambda item: int(item[0])):
        open_time = int(row[0])
        idx = bisect.bisect_right(funding_times, open_time) - 1
        funding_rate = funding_rates[idx] if idx >= 0 else 0.0
        bars.append(
            {
                "timestamp": pd.to_datetime(open_time, unit="ms", utc=True).isoformat(),
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5]),
                "funding_rate": float(funding_rate),
            }
        )
    return bars


def post_bars(runtime_url: str, ingest_token: str, bars: list[dict[str, Any]], *, timeout: float) -> dict[str, Any]:
    payload = json.dumps({"bars": bars}, ensure_ascii=True).encode("utf-8")
    req = request.Request(
        f"{runtime_url.rstrip('/')}/v1/market/bars",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-Ingest-Token": ingest_token,
        },
        method="POST",
    )
    with request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get_json(
    session: requests.Session,
    url: str,
    params: dict[str, Any],
    *,
    timeout: float,
    retries: int,
    retry_sleep_seconds: float,
) -> Any:
    last_error: Exception | None = None
    for attempt in range(max(1, retries)):
        try:
            response = session.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            last_error = exc
            wait = min(retry_sleep_seconds * (2**attempt), 30.0)
            print(f"request failed: {exc}; retrying in {wait:.1f}s", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"request failed after {retries} attempts: {last_error}") from last_error


def _market_id(symbol: str) -> str:
    return symbol.split(":")[0].replace("/", "").upper()
