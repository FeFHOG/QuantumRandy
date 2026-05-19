from __future__ import annotations

from pathlib import Path

import pandas as pd


REQUIRED_OHLCV = {"timestamp", "open", "high", "low", "close", "volume"}


def read_ohlcv(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = REQUIRED_OHLCV - set(df.columns)
    if missing:
        raise ValueError(f"OHLCV CSV missing columns: {sorted(missing)}")
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, format="mixed")
    df = df.sort_values("timestamp").drop_duplicates("timestamp")
    cols = ["open", "high", "low", "close", "volume"]
    return df.set_index("timestamp")[cols].astype(float)


def read_funding(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "timestamp" not in df or "funding_rate" not in df:
        raise ValueError("Funding CSV must contain timestamp,funding_rate")
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, format="mixed")
    df = df.sort_values("timestamp").drop_duplicates("timestamp")
    return df.set_index("timestamp")[["funding_rate"]].astype(float)


def align_funding_to_ohlcv(ohlcv: pd.DataFrame, funding: pd.DataFrame) -> pd.Series:
    aligned = funding.reindex(ohlcv.index.union(funding.index)).sort_index().ffill()
    return aligned.reindex(ohlcv.index)["funding_rate"].fillna(0.0)


def load_market_frame(ohlcv_path: str | Path, funding_path: str | Path) -> pd.DataFrame:
    ohlcv = read_ohlcv(ohlcv_path)
    funding = align_funding_to_ohlcv(ohlcv, read_funding(funding_path))
    out = ohlcv.copy()
    out["funding_rate"] = funding
    return out


def slice_window(df: pd.DataFrame, start: str | None, end: str | None) -> pd.DataFrame:
    out = df
    if start:
        out = out[out.index >= pd.Timestamp(start, tz="UTC")]
    if end:
        out = out[out.index < pd.Timestamp(end, tz="UTC")]
    return out.copy()
