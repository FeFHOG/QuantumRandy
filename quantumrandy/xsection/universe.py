"""Point-in-time liquid crypto universe for cross-sectional research."""

from __future__ import annotations

import pandas as pd

from .panel import Panel

# Binance USD-M perpetuals whose underlying is not a crypto asset (Phase 2a protocol amendment of 2026-11-05):
# equities, ETFs and equity indices, commodities and commodity-backed tokens, FX, pre-IPO contracts, and composite
# crypto indices. Compiled from symbol names and listing dates before any factor was evaluated; exchangeInfo's
# underlyingType is geo-blocked from the research machine.
NON_CRYPTO = frozenset(
    {
        # US-listed equities and ADRs
        "AAOI", "AAPL", "ABBV", "ACN", "ADBE", "AKAM", "ALAB", "AMAT", "AMC", "AMD", "AMGN", "AMZN", "ANET", "APLD",
        "APP", "ARM", "ASML", "ASTS", "AVGO", "AXTI", "BABA", "BAC", "BMNR", "BRKB", "CEG", "CIEN", "COHR", "COIN",
        "COST", "CRCL", "CRDO", "CRM", "CRML", "CRWD", "CRWV", "CSCO", "CVNA", "CVX", "DDOG", "DELL", "DIS", "DJT",
        "DKNG", "EBAY", "EQT", "FLNC", "GEV", "GLW", "GME", "GOOGL", "GPRO", "GS", "GTLB", "HD", "HIMS", "HOOD", "HPE",
        "HUT", "IBKR", "IBM", "INTC", "IONQ", "IREN", "JPM", "KLAC", "KO", "LITE", "LLY", "LRCX", "MARA", "MCD", "MDB",
        "MELI", "META", "MRK", "MRNA", "MRVL", "MSFT", "MSTR", "MU", "NBIS", "NET", "NFLX", "NKE", "NOK", "NOW", "NVDA",
        "NVO", "OKLO", "ONDS", "ORCL", "OXY", "PANW", "PDD", "PFE", "PLTR", "PYPL", "QCOM", "RDDT", "RDW", "RIVN",
        "RKLB", "SHOP", "SMCI", "SMR", "SNDK", "SNOW", "SNPS", "SOFI", "SONY", "TEAM", "TEM", "TSLA", "TSM", "TTWO",
        "TWST", "TXN", "UBER", "UNH", "USAR", "VKTX", "VRT", "WDC", "WMT", "XOM", "ZM", "ZS",
        # ETFs, leveraged ETFs and equity indices
        "BITO", "BWET", "CSOPSAMSUNG2L", "CSOPSKHYNIX2L", "EIDO", "EWJ", "EWT", "EWY", "EWZ", "EWZS", "GDX", "IWM",
        "KODEX200", "KORU", "MSTU", "NVDL", "QQQ", "SLX", "SMH", "SOXL", "SOXS", "SPY", "SQQQ", "TMF", "TQQQ", "TSLL",
        "TZA", "URNM", "UVXY", "XBI", "XLE",
        # Korean, Hong Kong and Chinese equities
        "BYD", "CXMT", "HANMI", "HK0625", "HK0700", "HK0992", "HK1810", "HYUNDAI", "KUAISHOU", "LGELECTRONICS",
        "MEITUAN", "MINIMAX", "NAVER", "POPMART", "SAMSUNG", "SAMSUNGEM", "SKHY", "SKHYNIX", "TENCENT", "UNITREE",
        "ZHIPU", "ZHONGJI",
        # Commodities, commodity-backed tokens and FX
        "COPPER", "NATGAS", "PAXG", "USDBRL", "XAG", "XAU", "XAUT", "XPD", "XPT",
        # Pre-IPO contracts
        "ANTHROPIC", "OPENAI",
        # Composite crypto indices (not single assets)
        "BLUEBIRD", "BTCDOM", "DEFI", "FOOTBALL",
    }
)


def base_asset(symbol: str) -> str:
    return symbol[: -len("USDT")] if symbol.endswith("USDT") else symbol


def liquid_universe(
    panel: Panel,
    *,
    top_n: int = 50,
    lookback: int = 30,
    min_history: int = 60,
    excluded: frozenset[str] = NON_CRYPTO,
    listed_before: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Boolean days x symbols mask: on each day the ``top_n`` crypto contracts by median quote volume over the
    ``lookback`` days ending that day, among those with at least ``min_history`` bars and a price that day.

    Uses only data up to each day's close. ``listed_before`` keeps only contracts whose first bar precedes it.
    """
    close = panel["close"]
    keep = [symbol for symbol in close.columns if base_asset(symbol) not in excluded]
    if listed_before is not None:
        cutoff = pd.Timestamp(listed_before)
        cutoff = cutoff.tz_localize("UTC") if cutoff.tzinfo is None else cutoff
        keep = [symbol for symbol in keep if pd.notna(panel.first_bar[symbol]) and panel.first_bar[symbol] < cutoff]
    close = close[keep]
    volume = panel["quote_volume"][keep]
    median_volume = volume.rolling(lookback, min_periods=max(lookback // 2, 1)).median()
    history = close.notna().cumsum()
    eligible = close.notna() & (history >= min_history) & median_volume.notna()
    rank = median_volume.where(eligible).rank(axis=1, ascending=False, method="first")
    mask = rank.le(top_n)
    return mask.reindex(columns=panel["close"].columns, fill_value=False)
