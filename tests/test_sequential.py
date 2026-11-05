from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quantumrandy.xsection.sequential import BettingSpec, decision, eprocesses, operating_characteristics


def _returns(mean: float, days: int = 2000, seed: int = 0) -> pd.Series:
    rng = np.random.default_rng(seed)
    index = pd.date_range("2026-11-06", periods=days, freq="1D", tz="UTC")
    return pd.Series(mean + 0.015 * rng.standard_t(5, days) / np.sqrt(5 / 3), index=index)


def test_stakes_are_predictable_and_wealth_compounds():
    returns = _returns(0.001, days=300)
    spec = BettingSpec(mean0=0.001, sigma0=0.015)
    frame = eprocesses(returns, spec)
    assert frame["stake"].iloc[0] == pytest.approx(0.5 * (0.001 / 0.015) / 0.015)
    shocked = returns.copy()
    shocked.iloc[150] = 0.2
    after = eprocesses(shocked, spec)
    assert after["stake"].iloc[:151].equals(frame["stake"].iloc[:151])  # a day's own return never sets its stake
    assert after["stake"].iloc[151] < frame["stake"].iloc[151]  # a large move lowers later stakes
    assert frame["stake"].max() <= spec.stake_cap
    expected = np.cumprod(1.0 + frame["stake"] * returns)
    assert frame["e_edge"].to_numpy() == pytest.approx(expected.to_numpy())
    assert frame["bound_ok"].all()


def test_error_rates_stay_below_alpha_when_checked_every_day():
    dev = _returns(0.0012, days=2000, seed=1)
    spec = BettingSpec(mean0=float(dev.mean()), sigma0=float(dev.std()))
    table = operating_characteristics(
        dev, spec, true_means={"no_edge": 0.0, "as_backtest": spec.mean0}, horizons_days=(3650,), paths=1500
    ).set_index("scenario")
    assert table.loc["no_edge", "edge_by_10y"] <= 0.05
    assert table.loc["as_backtest", "retire_by_10y"] <= 0.05
    assert table.loc["as_backtest", "edge_by_10y"] > 0.8
    assert table.loc["no_edge", "retire_by_10y"] > 0.8


def test_decision_reports_the_first_crossing():
    spec = BettingSpec(mean0=0.001, sigma0=0.015)
    index = pd.date_range("2026-11-06", periods=4, freq="1D", tz="UTC")
    frame = pd.DataFrame(
        {"e_edge": [1.0, 25.0, 30.0, 10.0], "e_futility": [1.0, 0.5, 0.2, 0.1], "bound_ok": True}, index=index
    )
    assert decision(frame, spec)["verdict"] == "edge_confirmed"
    assert decision(frame, spec)["edge_confirmed_on"] == "2026-11-07"
    frame["e_edge"] = [1.0, 2.0, 3.0, 4.0]
    assert decision(frame, spec)["verdict"] == "continue"
    frame["e_futility"] = [1.0, 5.0, 21.0, 30.0]
    assert decision(frame, spec) | {"e_edge": None, "e_futility": None} == {
        "verdict": "retire",
        "edge_confirmed_on": None,
        "futility_on": "2026-11-08",
        "e_edge": None,
        "e_futility": None,
        "bound_ok": True,
    }
