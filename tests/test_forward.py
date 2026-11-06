from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from randyslab.accounting import CostRates
from randyslab.holdout import HOLDOUT_END

from quantumrandy.xsection.forward import (
    Registration,
    discover_registrations,
    excluded_contracts,
    forward_record,
    funding_final_through,
    load_forward_panel,
    weekend_ratio,
)
from quantumrandy.xsection.universe import base_asset, liquid_universe

START = pd.Timestamp("2026-11-06", tz="UTC")
GAP = pd.Timestamp("2026-10-28", tz="UTC")
PREREGISTRATIONS = Path(__file__).resolve().parents[1] / "preregistrations"
CRYPTO = [f"C{i:02d}USDT" for i in range(14)]


def _write(root: Path, symbol: str, days: pd.DatetimeIndex, rng: np.random.Generator, weekend_scale: float = 1.0):
    moves = rng.normal(0, 0.03, len(days)) * np.where(days.day_of_week >= 5, weekend_scale, 1.0)
    close = 100.0 * np.exp(np.cumsum(moves))
    volume = rng.lognormal(16, 0.3, len(days))
    (root / "klines_1d").mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {"timestamp": days, "close": close, "quote_volume": volume,
         "taker_buy_quote_volume": volume * rng.uniform(0.4, 0.6, len(days))}
    ).to_csv(root / "klines_1d" / f"{symbol}.csv", index=False)
    stamps = pd.date_range(days[0], days[-1] + pd.Timedelta(hours=16), freq="8h")
    (root / "funding").mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"timestamp": stamps, "funding_rate": 1e-4, "funding_interval_hours": 8}).to_csv(
        root / "funding" / f"{symbol}.csv", index=False
    )


def _dirs(tmp_path: Path) -> tuple[Path, Path]:
    rng = np.random.default_rng(0)
    base, daily = tmp_path / "base", tmp_path / "daily"
    old = pd.date_range("2026-01-01", "2026-10-31", freq="1D", tz="UTC").drop(GAP)  # the archive omits 2026-10-28
    new = pd.date_range("2026-11-01", "2026-11-12", freq="1D", tz="UTC")
    listings = {
        **{symbol: ("2026-01-01", 1.0) for symbol in CRYPTO},
        "AAPLUSDT": ("2026-01-01", 1.0),  # Phase 2a NON_CRYPTO list
        "NEWSTKUSDT": ("2026-08-01", 0.1),  # stock-like: quiet weekends
        "NEWCRYUSDT": ("2026-08-01", 1.0),
        "YOUNGUSDT": ("2026-10-20", 1.0),  # fewer than 60 bars
        "OURAUSDT": ("2026-09-23", 1.0),  # named before its 60th bar
        "LATEUSDT": ("2026-06-01", 1.0),  # named after its 60th bar: the entry does not count
    }
    for symbol, (first, weekend_scale) in listings.items():
        _write(base, symbol, old[old >= pd.Timestamp(first, tz="UTC")], rng, weekend_scale)
        _write(daily, symbol, new, rng, weekend_scale)
    return base, daily


def test_panel_hides_holdout_prices_and_spans_archive_gaps(tmp_path: Path):
    base, daily = _dirs(tmp_path)
    data = load_forward_panel(base, daily, START)
    close = data.panel["close"]
    assert GAP not in close.index
    before = close.loc[: START - pd.Timedelta(days=2)]
    assert set(np.unique(before.to_numpy()[~np.isnan(before.to_numpy())])) == {1.0}  # presence flags only
    assert close.loc[START - pd.Timedelta(days=1)].gt(1.5).all()  # real prices from the day before the start
    assert data.panel["quote_volume"].loc[: START - pd.Timedelta(days=2)].gt(1.0).any().any()
    # Settlements during the missing day move to the next bar: three of its own plus three from 2026-10-28.
    funding = data.panel["funding_settled"]["C00USDT"]
    assert funding.loc[pd.Timestamp("2026-10-29", tz="UTC")] == pytest.approx(6e-4)
    assert funding.loc[pd.Timestamp("2026-10-30", tz="UTC")] == pytest.approx(3e-4)
    with pytest.raises(ValueError, match="after the holdout"):
        load_forward_panel(base, daily, pd.Timestamp("2026-10-15", tz="UTC"))


def test_weekend_ratio_separates_closed_markets():
    days = pd.date_range("2026-01-01", periods=60, freq="1D", tz="UTC")
    rng = np.random.default_rng(1)
    quiet = np.where(days.day_of_week >= 5, 0.1, 1.0)
    assert weekend_ratio(pd.Series(np.exp(np.cumsum(rng.normal(0, 0.02, 60) * quiet)), index=days)) < 0.45
    assert weekend_ratio(pd.Series(np.exp(np.cumsum(rng.normal(0, 0.02, 60))), index=days)) > 0.45


def test_new_listing_rules(tmp_path: Path):
    base, daily = _dirs(tmp_path)
    data = load_forward_panel(base, daily, START)
    excluded = excluded_contracts(
        data,
        reviewed=set(CRYPTO),
        name_exclusions=[{"base": "OURA", "added": "2026-11-05"}, {"base": "LATE", "added": "2026-11-05"}],
        weekend_min=0.45,
        new_listing_cutoff=pd.Timestamp("2025-09-01", tz="UTC"),
    )
    assert excluded == {
        "AAPLUSDT": "non_crypto_list",
        "NEWSTKUSDT": "weekend_test",
        "YOUNGUSDT": "unclassified",
        "OURAUSDT": "name_exclusion",
    }
    mask = liquid_universe(data.panel, top_n=12, excluded=frozenset(base_asset(s) for s in excluded))
    assert not mask[list(excluded)].any().any()
    assert mask["LATEUSDT"].any() and mask["NEWCRYUSDT"].any()


def test_record_starts_flat_and_marks_final_days(tmp_path: Path):
    base, daily = _dirs(tmp_path)
    data = load_forward_panel(base, daily, START)
    mask = liquid_universe(data.panel, top_n=12, excluded=frozenset({"AAPL", "NEWSTK", "YOUNG", "OURA"}))
    record, target, _ = forward_record(
        data.panel, mask, START, CostRates(4.0, 5.0), funding_final_through("2026-10", ["2026-11"]), factor="taker_7d"
    )
    assert record.index[0] == START and record.index[-1] == pd.Timestamp("2026-11-12", tz="UTC")
    assert record["turnover"].iloc[0] == pytest.approx(1.0)  # the book is built from flat on the first day
    assert record["gross_exposure"].eq(1.0).all()
    assert record["final"].all()
    assert (record["r_net_2x_costs"] <= record["r_net"]).all()
    assert record["r_net"].iloc[0] - record["r_net_2x_costs"].iloc[0] == pytest.approx(9e-4)  # 9 bps on unit turnover
    held = target.loc[START].ne(0.0)
    assert held.sum() == 4  # 12 names, 20% per leg
    pending = funding_final_through("2026-10", [])
    unpublished = forward_record(data.panel, mask, START, CostRates(4.0, 5.0), pending, factor="taker_7d")[0]
    assert not unpublished["final"].any()


def test_record_uses_the_registered_factor(tmp_path: Path):
    base, daily = _dirs(tmp_path)
    data = load_forward_panel(base, daily, START)
    mask = liquid_universe(data.panel, top_n=12, excluded=frozenset({"AAPL", "NEWSTK", "YOUNG", "OURA"}))
    final, costs = funding_final_through("2026-10", ["2026-11"]), CostRates(4.0, 5.0)
    share = data.panel["taker_buy_quote_volume"] / data.panel["quote_volume"].replace(0.0, np.nan)
    for factor, days in (("taker_7d", 7), ("taker_30d", 30)):
        _, target, scores = forward_record(data.panel, mask, START, costs, final, factor=factor)
        pd.testing.assert_frame_equal(scores, share.rolling(days, min_periods=days).mean() - 0.5)
        assert target.loc[START - pd.Timedelta(days=1)].ne(0.0).sum() == 4
    with pytest.raises(ValueError, match="not a forward factor"):
        forward_record(data.panel, mask, START, costs, final, factor="mom_7d")


def test_registration_properties_are_checked():
    spec = {"id": "x", "factor": {"name": "taker_30d"}, "candidates": ["taker_30d"],
            "decision_rules": {"monitoring_flags": ["a day outside the bound", "paper drawdown deeper than 0.214"]}}
    reg = Registration(spec=spec, sha256="")
    assert reg.factor == "taker_30d" and reg.drawdown_flag == pytest.approx(0.214)
    with pytest.raises(ValueError, match="forward factors"):
        _ = Registration(spec={**spec, "factor": {"name": "mom_7d"}, "candidates": ["mom_7d"]}, sha256="").factor
    with pytest.raises(ValueError, match="forward factors"):
        _ = Registration(spec={**spec, "candidates": ["taker_30d", "taker_7d"]}, sha256="").factor
    with pytest.raises(ValueError, match="drawdown"):
        _ = Registration(spec={**spec, "decision_rules": {"monitoring_flags": []}}, sha256="").drawdown_flag


def test_discovery_finds_only_forward_registrations(tmp_path: Path):
    for name in ("b_taker_forward.json", "a_taker_forward.json", "forward_exclusions.json", "phase2b_holdout.json"):
        (tmp_path / name).write_text("{}")
    assert [path.name for path in discover_registrations(tmp_path)] == ["a_taker_forward.json", "b_taker_forward.json"]


def test_registered_observations_agree_where_they_must():
    regs = {reg.factor: reg for reg in map(Registration.load, discover_registrations(PREREGISTRATIONS))}
    assert set(regs) == {"taker_7d", "taker_30d"}
    for reg in regs.values():
        assert reg.start > HOLDOUT_END  # observes bars after the holdout only
        assert reg.betting.threshold == 20.0 and 0.0 < reg.betting.mean0 < reg.betting.sigma0
        decision_close = pd.Timestamp(reg.spec["first_decision_close"], tz="UTC")
        assert reg.start == decision_close + pd.Timedelta(days=1)  # the position is set at that day's close
    slow, fast = regs["taker_30d"], regs["taker_7d"]
    assert (slow.drawdown_flag, fast.drawdown_flag) == (pytest.approx(0.214), pytest.approx(0.344))
    assert slow.start > fast.start
    for key in ("universe", "book", "costs"):  # one universe, book and cost model for every observation
        assert slow.spec[key] == fast.spec[key]
    assert {k: v for k, v in slow.spec["data"].items() if k != "holdout"} == \
        {k: v for k, v in fast.spec["data"].items() if k != "holdout"}


def test_funding_month_end_waits_for_the_next_file():
    through = funding_final_through("2026-10", ["2026-11"])
    assert pd.Timestamp("2026-11-29", tz="UTC") + pd.Timedelta(days=1) <= through
    assert pd.Timestamp("2026-11-30", tz="UTC") + pd.Timedelta(days=1) > through
