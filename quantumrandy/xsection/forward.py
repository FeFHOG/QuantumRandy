"""Forward paper observation (docs/PHASE2A_TAKER_FORWARD_PREREGISTRATION.md and the registrations that follow it):
point-in-time panel and daily record.

The panel joins the monthly universe download (through 2026-10) with the daily archive kept by RandysLab
``scripts/fetch_daily.py``. Holdout bars are read only as lookback inputs: once new listings are classified, every price
before the day preceding the observation start is replaced by a presence flag, so no return inside the holdout can be
computed from the panel.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from randyslab.accounting import CostRates, build_portfolio_ledger, normalize_funding_events
from randyslab.holdout import HOLDOUT_END

from .evaluate import held_weights, quantile_weights
from .factors import FACTORS
from .family_2b import TRIALS
from .panel import Panel, _read, funding_on_calendar
from .sequential import BettingSpec
from .universe import NON_CRYPTO, base_asset

DAY = pd.Timedelta(days=1)
FIELDS = ("close", "quote_volume", "taker_buy_quote_volume")
LOOKBACK_DAYS = 120
GAP_GRACE_DAYS = 7  # a bar still missing this long after its day is treated as never published

# The factors a forward registration may name: each needs only FIELDS, and is the definition its protocol fixed.
FORWARD_FACTORS: dict[str, Callable[[Panel], pd.DataFrame]] = {
    "taker_7d": FACTORS["taker_7d"].compute,
    "taker_30d": TRIALS["taker_30d"].compute,
}


@dataclass(frozen=True)
class Registration:
    spec: dict[str, Any]
    sha256: str  # of the file with LF line endings, so checkouts with CRLF conversion hash the same

    @classmethod
    def load(cls, path: str | Path) -> Registration:
        raw = Path(path).read_bytes().replace(b"\r\n", b"\n")
        return cls(spec=json.loads(raw.decode("utf-8")), sha256=hashlib.sha256(raw).hexdigest())

    @property
    def factor(self) -> str:
        """The registered factor: one the forward panel can compute, and the registration's only candidate."""
        name = self.spec["factor"]["name"]
        if name not in FORWARD_FACTORS or self.spec["candidates"] != [name]:
            raise ValueError(f"{self.spec['id']} names {name!r}; forward factors are {sorted(FORWARD_FACTORS)}")
        return name

    @property
    def drawdown_flag(self) -> float:
        """The paper drawdown that triggers an owner review, as the registered monitoring flag states it."""
        for flag in self.spec["decision_rules"]["monitoring_flags"]:
            found = re.search(r"drawdown deeper than ([0-9.]+)", flag)
            if found:
                return float(found.group(1))
        raise ValueError(f"{self.spec['id']} has no drawdown monitoring flag")

    @property
    def start(self) -> pd.Timestamp:
        """First day whose net return is observed."""
        return pd.Timestamp(self.spec["first_pnl_day"], tz="UTC")

    @property
    def betting(self) -> BettingSpec:
        test = self.spec["test"]
        keys = ("mean0", "sigma0", "kelly_fraction", "halflife_days", "stake_cap", "threshold")
        return BettingSpec(**{key: float(test[key]) for key in keys})

    @property
    def costs(self) -> CostRates:
        return CostRates(self.spec["costs"]["fee_bps"], self.spec["costs"]["slippage_bps"])


@dataclass(frozen=True)
class ForwardPanel:
    panel: Panel
    first_bar: pd.Series  # first bar ever, from the full history
    sixtieth_bar: pd.Series  # day of the 60th bar (NaT with fewer), when a contract can first be eligible
    weekend_ratio: pd.Series  # Phase 2a weekend test on the first 60 bars (NaN with fewer)


def load_forward_panel(
    base: str | Path,
    daily: str | Path,
    start: pd.Timestamp,
    *,
    lookback_days: int = LOOKBACK_DAYS,
) -> ForwardPanel:
    """Close, quote volume, taker-buy quote volume and settled funding from ``start - lookback_days``.

    Days missing for every contract are not trading days: the next bar spans them and pays their funding.
    """
    if start <= HOLDOUT_END:
        raise ValueError("a forward observation starts after the holdout window")
    base, daily = Path(base), Path(daily)
    window = start - lookback_days * DAY
    names = sorted({p.stem for root in (base, daily) for p in (root / "klines_1d").glob("*.csv")})
    columns: dict[str, dict[str, pd.Series]] = {field: {} for field in FIELDS}
    events: dict[str, pd.DataFrame] = {}
    first_bar, sixtieth, ratio = {}, {}, {}
    for symbol in names:
        klines = _combined(base / "klines_1d" / f"{symbol}.csv", daily / "klines_1d" / f"{symbol}.csv")
        if klines.empty:
            continue
        first_bar[symbol] = klines.index[0]
        sixtieth[symbol] = klines.index[59] if len(klines) >= 60 else pd.NaT
        ratio[symbol] = weekend_ratio(klines["close"].iloc[:60]) if len(klines) >= 60 else np.nan
        recent = klines.loc[window:]
        if recent.empty:
            continue
        for field in FIELDS:
            columns[field][symbol] = recent[field].astype(float)
        funding = _combined(base / "funding" / f"{symbol}.csv", daily / "funding" / f"{symbol}.csv")
        if not funding.empty:
            events[symbol] = normalize_funding_events(funding.loc[window:])

    close = pd.DataFrame(columns["close"]).sort_index()
    fields = {name: pd.DataFrame(series).reindex(index=close.index, columns=close.columns) for name, series in
              columns.items()}
    fields["funding_settled"] = funding_on_calendar(close.index, events, close.columns)
    before = fields["close"].index < start - DAY
    fields["close"].loc[before] = fields["close"].loc[before].notna().astype(float).replace(0.0, np.nan)
    first = pd.Series(first_bar)
    return ForwardPanel(
        panel=Panel(fields=fields, first_bar=first.reindex(close.columns)),
        first_bar=first,
        sixtieth_bar=pd.Series(sixtieth, dtype="datetime64[ns, UTC]"),
        weekend_ratio=pd.Series(ratio, dtype=float),
    )


def weekend_ratio(close: pd.Series) -> float:
    """Median absolute daily return on Saturday and Sunday bars divided by that on weekday bars."""
    moves = close.pct_change(fill_method=None).abs().dropna()
    weekend = moves.index.day_of_week >= 5
    if weekend.sum() < 4 or (~weekend).sum() < 10:
        return float("nan")
    weekday = moves[~weekend].median()
    return float(moves[weekend].median() / weekday) if weekday > 0 else float("nan")


def excluded_contracts(
    data: ForwardPanel,
    *,
    reviewed: set[str],
    name_exclusions: list[dict[str, str]],
    weekend_min: float,
    new_listing_cutoff: pd.Timestamp,
) -> dict[str, str]:
    """Contracts kept out of the forward universe, with the rule that excludes each."""
    names = {entry["base"]: pd.Timestamp(entry["added"], tz="UTC") for entry in name_exclusions}
    excluded = {}
    for symbol, first in data.first_bar.items():
        base = base_asset(symbol)
        if base in NON_CRYPTO:
            excluded[symbol] = "non_crypto_list"
        elif symbol in reviewed:
            continue
        elif base in names and (pd.isna(data.sixtieth_bar.get(symbol)) or names[base] < data.sixtieth_bar[symbol]):
            excluded[symbol] = "name_exclusion"
        elif first >= new_listing_cutoff and not data.weekend_ratio.get(symbol, np.nan) >= weekend_min:
            excluded[symbol] = "weekend_test" if np.isfinite(data.weekend_ratio.get(symbol, np.nan)) else "unclassified"
    return excluded


def forward_record(
    panel: Panel,
    mask: pd.DataFrame,
    start: pd.Timestamp,
    costs: CostRates,
    funding_final_through: pd.Timestamp,
    *,
    factor: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Daily record from ``start`` (net returns at 1x and 2x costs, components, finality), target weights and scores
    of the quintile long-short book of ``factor`` (one of ``FORWARD_FACTORS``).

    A day is final when its funding is published (its bar ends on or before ``funding_final_through``) and no contract
    meant to be held lacks a bar that may still be published.
    """
    if factor not in FORWARD_FACTORS:
        raise ValueError(f"{factor!r} is not a forward factor; forward factors are {sorted(FORWARD_FACTORS)}")
    scores = FORWARD_FACTORS[factor](panel)
    target = quantile_weights(scores, mask)
    weights = held_weights(target, panel)
    weights.loc[weights.index < start] = 0.0
    stressed = CostRates(costs.fee_bps * 2.0, costs.slippage_bps * 2.0, costs.funding_multiplier)
    ledger = build_portfolio_ledger(weights, panel["close"], panel["funding_settled"], costs).loc[start:]
    stress = build_portfolio_ledger(weights, panel["close"], panel["funding_settled"], stressed).loc[start:]

    record = ledger[["r_net", "r_gross", "c_fee", "c_slip", "c_fund", "turnover", "gross_exposure", "positions"]].copy()
    record.insert(1, "r_net_2x_costs", stress["r_net"])
    intended = target.shift(1).fillna(0.0).ne(0.0) & panel["close"].isna()
    latest = panel.index[-1] if len(panel.index) else start
    pending = intended & (panel.index > latest - GAP_GRACE_DAYS * DAY)[:, None]
    record["missing_bars"] = intended.loc[start:].sum(axis=1).astype(int)
    record["final"] = (record.index + DAY <= funding_final_through) & ~pending.loc[start:].any(axis=1)
    return record, target, scores


def discover_registrations(directory: str | Path) -> list[Path]:
    """Every forward registration (``*_forward.json``) in ``directory``, in name order."""
    return sorted(Path(directory).glob("*_forward.json"))


def funding_final_through(base_last_month: str, published_months: list[str]) -> pd.Timestamp:
    """Last settlement instant covered by published funding files: the end of the latest published month.

    A day's bar pays the settlements in (day, day + 1], so the last day of a month waits for the next month's file.
    """
    month = max([base_last_month, *published_months])
    return (pd.Period(month, freq="M") + 1).start_time.tz_localize("UTC") - pd.Timedelta(minutes=1)


def _combined(*paths: Path) -> pd.DataFrame:
    frames = [frame for frame in (_read(path) for path in paths) if not frame.empty]
    if not frames:
        return pd.DataFrame()
    frame = pd.concat(frames)
    return frame[~frame.index.duplicated(keep="last")].sort_index()
