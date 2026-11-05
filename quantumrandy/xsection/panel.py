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
    held during the day). A day missing for every contract (Binance omitted 2026-10-28) is not a trading day: the next
    bar spans it and pays its funding. Holdout bars are dropped unless ``preregistration`` opens the holdout.
    """
    root = Path(root)
    names = symbols or sorted(path.stem for path in (root / "klines_1d").glob("*.csv"))
    columns: dict[str, dict[str, pd.Series]] = {name: {} for name in (*KLINE_FIELDS, "premium", "funding_rate")}
    events: dict[str, pd.DataFrame] = {}
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
            events[symbol] = normalize_funding_events(funding)
            columns["funding_rate"][symbol] = _daily_funding_rate(klines.index, events[symbol])

    close = pd.DataFrame(columns["close"]).sort_index()
    close = seal(close) if preregistration is None else open_holdout(close, preregistration)
    fields = {
        name: pd.DataFrame(series).reindex(index=close.index, columns=close.columns)
        for name, series in columns.items()
    }
    fields["close"] = close
    fields["funding_settled"] = funding_on_calendar(close.index, events, close.columns)
    first_bar = close.apply(lambda column: column.first_valid_index())
    return Panel(fields=fields, first_bar=first_bar)


METRICS_FIELDS = {
    "open_interest": "sum_open_interest",
    "toptrader_ls_position": "sum_toptrader_long_short_ratio",
    "global_ls_accounts": "count_long_short_ratio",
}


def load_metrics(root: str | Path, panel: Panel) -> Panel:
    """``panel`` plus the daily Binance metrics written by RandysLab ``scripts/fetch_metrics.py``.

    Adds ``open_interest`` (contracts), ``toptrader_ls_position`` (top traders' long/short position ratio) and
    ``global_ls_accounts`` (long/short ratio of all accounts), each the day's last snapshot, aligned to the panel's
    days and symbols. Days beyond the panel (such as sealed holdout days) are dropped with it.
    """
    root = Path(root)
    columns: dict[str, dict[str, pd.Series]] = {name: {} for name in METRICS_FIELDS}
    for symbol in panel.symbols:
        metrics = _read(root / "metrics_1d" / f"{symbol}.csv")
        if metrics.empty:
            continue
        for name, column in METRICS_FIELDS.items():
            columns[name][symbol] = pd.to_numeric(metrics[column], errors="coerce")
    fields = dict(panel.fields)
    for name, series in columns.items():
        fields[name] = pd.DataFrame(series).reindex(index=panel.index, columns=panel.symbols)
    return Panel(fields=fields, first_bar=panel.first_bar)


def funding_on_calendar(calendar: pd.DatetimeIndex, events: dict[str, pd.DataFrame], symbols: pd.Index) -> pd.DataFrame:
    """Settled funding per trading day; a day missing for every contract hands its settlements to the next bar.

    A contract without a bar on a trading day is flat that day, so the settlements assigned to that day cost nothing.
    """
    if not len(calendar):
        return pd.DataFrame(index=calendar, columns=symbols, dtype=float)
    days = pd.date_range(calendar[0], calendar[-1], freq="1D")
    owner = calendar[calendar.searchsorted(days, side="left")]
    settled = {
        symbol: funding_settled_per_bar(days, frame, BAR_HOURS).groupby(owner).sum() for symbol, frame in events.items()
    }
    return pd.DataFrame(settled).reindex(index=calendar, columns=symbols).fillna(0.0)


def _daily_funding_rate(index: pd.DatetimeIndex, events: pd.DataFrame) -> pd.Series:
    """Mean 8h-equivalent rate settled during each day."""
    rate_8h = events["funding_rate"] * STANDARD_FUNDING_INTERVAL_HOURS / events["interval_hours"]
    return rate_8h.groupby(events.index.floor("1D")).mean().reindex(index)


def _read(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path)
    if frame.empty:
        return frame
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, format="mixed")
    return frame.drop_duplicates("timestamp").set_index("timestamp").sort_index()
