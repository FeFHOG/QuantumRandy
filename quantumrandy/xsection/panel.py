"""Wide daily panels (days x symbols) built from RandysLab's universe download (``scripts/fetch_universe.py``)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from randyslab.accounting import STANDARD_FUNDING_INTERVAL_HOURS, funding_settled_per_bar, normalize_funding_events
from randyslab.holdout import open_holdout, seal

KLINE_FIELDS = ("open", "high", "low", "close", "volume", "quote_volume", "taker_buy_quote_volume")
BAR_HOURS = 24.0


@dataclass(frozen=True)
class Panel:
    """Named days x symbols frames plus each symbol's first bar (listing date)."""

    fields: dict[str, pd.DataFrame]
    first_bar: pd.Series

    def __getitem__(self, name: str) -> pd.DataFrame:
        return self.fields[name]

    @property
    def index(self) -> pd.DatetimeIndex:
        return self.fields["close"].index

    @property
    def symbols(self) -> list[str]:
        return list(self.fields["close"].columns)


def load_panel(
    root: str | Path,
    *,
    symbols: list[str] | None = None,
    preregistration: str | Path | None = None,
) -> Panel:
    """Load daily klines, funding and premium index for ``symbols`` (default: every downloaded symbol).

    Fields: the kline columns, ``premium`` (premium-index close), ``funding_rate`` (mean 8h-equivalent rate of the
    settlements during the day, all known by its close) and ``funding_settled`` (settled rates charged to the position
    held during the day). Holdout bars are dropped unless ``preregistration`` opens the holdout.
    """
    root = Path(root)
    names = symbols or sorted(path.stem for path in (root / "klines_1d").glob("*.csv"))
    columns: dict[str, dict[str, pd.Series]] = {
        name: {} for name in (*KLINE_FIELDS, "premium", "funding_rate", "funding_settled")
    }
    for symbol in names:
        klines = _read(root / "klines_1d" / f"{symbol}.csv")
        if klines.empty:
            continue
        for field in KLINE_FIELDS:
            columns[field][symbol] = klines[field].astype(float)
        premium = _read(root / "premium_1d" / f"{symbol}.csv")
        if not premium.empty:
            columns["premium"][symbol] = premium["close"].astype(float)
        funding = _read(root / "funding" / f"{symbol}.csv")
        if not funding.empty:
            events = normalize_funding_events(funding)
            daily, settled = _daily_funding(klines.index, events)
            columns["funding_rate"][symbol] = daily
            columns["funding_settled"][symbol] = settled

    close = pd.DataFrame(columns["close"]).sort_index()
    close = seal(close) if preregistration is None else open_holdout(close, preregistration)
    fields = {
        name: pd.DataFrame(series).reindex(index=close.index, columns=close.columns)
        for name, series in columns.items()
    }
    fields["close"] = close
    first_bar = close.apply(lambda column: column.first_valid_index())
    return Panel(fields=fields, first_bar=first_bar)


def _daily_funding(index: pd.DatetimeIndex, events: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Mean 8h-equivalent rate settled during each day, and the settled cost of holding through each day."""
    rate_8h = events["funding_rate"] * STANDARD_FUNDING_INTERVAL_HOURS / events["interval_hours"]
    daily = rate_8h.groupby(events.index.floor("1D")).mean().reindex(index)
    return daily, funding_settled_per_bar(index, events, BAR_HOURS)


def _read(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path)
    if frame.empty:
        return frame
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, format="mixed")
    return frame.drop_duplicates("timestamp").set_index("timestamp").sort_index()
