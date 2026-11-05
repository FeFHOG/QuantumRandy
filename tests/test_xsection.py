from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from randyslab.accounting import CostRates
from randyslab.holdout import HOLDOUT_START

from quantumrandy.xsection.evaluate import (
    cross_sectional_ic,
    evaluate_factor,
    forward_returns,
    held_weights,
    quantile_weights,
)
from quantumrandy.xsection.factors import FACTORS
from quantumrandy.xsection.panel import Panel, load_panel
from quantumrandy.xsection.universe import liquid_universe


def _panel(days: int = 240, symbols: int = 30, seed: int = 0) -> Panel:
    rng = np.random.default_rng(seed)
    index = pd.date_range("2022-01-01", periods=days, freq="1D", tz="UTC")
    names = [f"S{i:02d}USDT" for i in range(symbols)] + ["AAPLUSDT"]
    shape = (days, len(names))
    close = pd.DataFrame(100.0 * np.exp(np.cumsum(rng.normal(0, 0.03, shape), axis=0)), index=index, columns=names)
    close.iloc[:150, 3] = np.nan  # listed late
    volume = pd.DataFrame(rng.lognormal(15, 1, shape) * np.linspace(1, 3, len(names)), index=index, columns=names)
    volume["AAPLUSDT"] *= 100  # most liquid, but not crypto
    funding = pd.DataFrame(rng.normal(1e-4, 2e-4, shape), index=index, columns=names)
    fields = {
        "close": close,
        "quote_volume": volume.where(close.notna()),
        "taker_buy_quote_volume": (volume * rng.uniform(0.45, 0.55, shape)).where(close.notna()),
        "funding_rate": funding,
        "funding_settled": funding * 3.0,
        "premium": pd.DataFrame(rng.normal(0, 1e-3, shape), index=index, columns=names),
    }
    return Panel(fields=fields, first_bar=close.apply(lambda c: c.first_valid_index()))


def test_universe_is_point_in_time_and_excludes_non_crypto_and_young_contracts():
    panel = _panel()
    mask = liquid_universe(panel, top_n=10)
    assert not mask["AAPLUSDT"].any()
    assert not mask.iloc[:209, 3].any()  # needs 60 bars after listing on day 150
    cut = panel.index[180]
    truncated = Panel({k: v.loc[:cut] for k, v in panel.fields.items()}, panel.first_bar)
    assert liquid_universe(truncated, top_n=10).equals(mask.loc[:cut])
    assert mask.iloc[100:].sum(axis=1).eq(10).all()
    late = liquid_universe(panel, top_n=10, listed_before=panel.index[100])
    assert not late["S03USDT"].any()


def test_cross_sectional_ic_matches_per_day_spearman():
    panel = _panel()
    mask = liquid_universe(panel, top_n=20)
    scores = FACTORS["mom_7d"].compute(panel)
    forward = forward_returns(panel)
    ic = cross_sectional_ic(scores, forward, mask)
    day = panel.index[120]
    members = mask.loc[day] & scores.loc[day].notna() & forward.loc[day].notna()
    expected = scores.loc[day, members].corr(forward.loc[day, members], method="spearman")
    assert ic.loc[day] == pytest.approx(expected)


def test_quantile_books_are_dollar_neutral_with_unit_gross():
    panel = _panel()
    mask = liquid_universe(panel, top_n=20)
    weights = quantile_weights(FACTORS["carry_3d"].compute(panel), mask)
    active = weights.abs().sum(axis=1) > 0
    assert active.sum() > 100
    assert weights[active].sum(axis=1).abs().max() == pytest.approx(0.0, abs=1e-12)
    assert weights[active].abs().sum(axis=1).to_numpy() == pytest.approx(1.0)
    assert (weights[active] > 0).sum(axis=1).eq(4).all()  # 20 names x 20%


def test_planted_signal_is_found_and_delisted_assets_go_flat():
    panel = _panel()
    mask = liquid_universe(panel, top_n=20)
    rng = np.random.default_rng(3)
    planted = forward_returns(panel) + rng.normal(0, 0.01, panel["close"].shape)
    noise = pd.DataFrame(rng.normal(size=panel["close"].shape), index=panel.index, columns=panel.symbols)
    start = panel.index[100]
    found = evaluate_factor(planted, panel, mask, CostRates(4.0, 5.0), start)
    blank = evaluate_factor(noise, panel, mask, CostRates(4.0, 5.0), start)
    assert found["ic_mean"] > 0.5 and found["sharpe"] > 3.0
    assert abs(blank["ic_mean"]) < 0.05
    panel["close"].iloc[200:, 5] = np.nan  # delisted while possibly held
    assert held_weights(quantile_weights(planted, mask), panel).iloc[200:, 5].eq(0.0).all()
    evaluate_factor(planted, panel, mask, CostRates(4.0, 5.0), start)  # no stranded-weight error


def test_load_panel_daily_funding_and_holdout_seal(tmp_path: Path):
    days = pd.date_range(HOLDOUT_START - pd.Timedelta(days=3), periods=5, freq="1D", tz="UTC")
    for dataset in ("klines_1d", "funding", "premium_1d"):
        (tmp_path / dataset).mkdir()
    pd.DataFrame(
        {
            "timestamp": days, "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0,
            "quote_volume": 10.0, "taker_buy_quote_volume": 5.0,
        }
    ).to_csv(tmp_path / "klines_1d" / "XUSDT.csv", index=False)
    stamps = pd.date_range(days[0], periods=15, freq="8h", tz="UTC")
    rates = np.arange(1, 16) * 1e-4
    pd.DataFrame({"timestamp": stamps, "funding_rate": rates, "funding_interval_hours": 8}).to_csv(
        tmp_path / "funding" / "XUSDT.csv", index=False
    )
    pd.DataFrame({"timestamp": days, "open": 0.0, "high": 0.0, "low": 0.0, "close": 0.001}).to_csv(
        tmp_path / "premium_1d" / "XUSDT.csv", index=False
    )
    panel = load_panel(tmp_path)
    assert panel.index.max() < HOLDOUT_START and len(panel.index) == 3
    # Day 0 holds settlements at 00:00, 08:00 and 16:00 (rates 1-3 bp): feature = their mean, all known by its close.
    assert panel["funding_rate"].iloc[0, 0] == pytest.approx(2e-4)
    # The position held through day 0 pays the 08:00, 16:00 and next 00:00 settlements (rates 2-4 bp).
    assert panel["funding_settled"].iloc[0, 0] == pytest.approx(9e-4)
    assert panel["premium"].iloc[0, 0] == pytest.approx(0.001)
