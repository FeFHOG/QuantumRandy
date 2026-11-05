from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from randyslab.holdout import HOLDOUT_START

from quantumrandy.xsection.evaluate import basket_weights, buffered_weights, quantile_weights
from quantumrandy.xsection.family_2b import TRIALS
from quantumrandy.xsection.panel import Panel, load_metrics, load_panel


def _scores(days: int = 120, names: int = 30, seed: int = 0, persistence: float = 0.9) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    values = np.zeros((days, names))
    values[0] = rng.normal(size=names)
    for t in range(1, days):
        values[t] = persistence * values[t - 1] + np.sqrt(1 - persistence**2) * rng.normal(size=names)
    index = pd.date_range("2023-01-01", periods=days, freq="1D", tz="UTC")
    return pd.DataFrame(values, index=index, columns=[f"S{i:02d}USDT" for i in range(names)])


def test_basket_book_is_dollar_neutral_without_concentrated_shorts():
    scores = _scores()
    mask = pd.DataFrame(True, index=scores.index, columns=scores.columns)
    weights = basket_weights(scores, mask)
    assert weights.sum(axis=1).abs().max() == pytest.approx(0.0, abs=1e-12)
    assert weights.abs().sum(axis=1).to_numpy() == pytest.approx(1.0)
    day = scores.index[50]
    top = scores.loc[day].nlargest(6).index
    assert (weights.loc[day, top] > 0).all()
    assert (weights.loc[day].drop(top) < 0).all()
    assert weights.loc[day].min() == pytest.approx(-0.5 / 30 / 0.8)  # 1/n of the short side, scaled to gross 1
    assert not basket_weights(scores, mask.iloc[:, :5].reindex(columns=scores.columns, fill_value=False)).any().any()


def test_buffered_book_holds_names_within_the_outer_band_and_trades_less():
    scores = _scores()
    mask = pd.DataFrame(True, index=scores.index, columns=scores.columns)
    buffered = buffered_weights(scores, mask)
    plain = quantile_weights(scores, mask)
    assert (buffered > 0).sum(axis=1).eq(6).all() and (buffered < 0).sum(axis=1).eq(6).all()
    assert buffered.abs().sum(axis=1).to_numpy() == pytest.approx(1.0)
    assert buffered.diff().abs().sum(axis=1).mean() < 0.7 * plain.diff().abs().sum(axis=1).mean()
    ranks = scores.rank(axis=1, ascending=False)
    longs = buffered > 0
    assert (ranks[longs] <= 12).sum().sum() == longs.sum().sum()  # never outside the top 2k
    shorts = buffered < 0
    assert (ranks[shorts] >= 30 - 12 + 1).sum().sum() == shorts.sum().sum()
    first = scores.index[0]
    assert set(buffered.columns[longs.loc[first]]) == set(scores.loc[first].nlargest(6).index)


def _write_daily(root: Path, symbol: str, days: pd.DatetimeIndex) -> None:
    for dataset in ("klines_1d", "funding", "premium_1d"):
        (root / dataset).mkdir(exist_ok=True)
    pd.DataFrame(
        {"timestamp": days, "open": 1.0, "high": 1.0, "low": 1.0, "close": np.linspace(1.0, 2.0, len(days)),
         "volume": 1.0, "quote_volume": 10.0, "taker_buy_quote_volume": 5.0}
    ).to_csv(root / "klines_1d" / f"{symbol}.csv", index=False)
    stamps = pd.date_range(days[0], days[-1] + pd.Timedelta(hours=16), freq="8h")
    pd.DataFrame({"timestamp": stamps, "funding_rate": 1e-4, "funding_interval_hours": 8}).to_csv(
        root / "funding" / f"{symbol}.csv", index=False
    )
    pd.DataFrame({"timestamp": days, "open": 0.0, "high": 0.0, "low": 0.0, "close": 0.001}).to_csv(
        root / "premium_1d" / f"{symbol}.csv", index=False
    )


def test_load_panel_hands_a_missing_days_funding_to_the_next_bar(tmp_path: Path):
    days = pd.date_range("2024-03-01", periods=6, freq="1D", tz="UTC")
    gap = days[2]
    for symbol in ("AUSDT", "BUSDT"):
        _write_daily(tmp_path, symbol, days.drop(gap))
    panel = load_panel(tmp_path)
    assert gap not in panel.index
    settled = panel["funding_settled"]["AUSDT"]
    assert settled.loc[days[1]] == pytest.approx(3e-4)
    assert settled.loc[days[3]] == pytest.approx(6e-4)  # its own three settlements and the missing day's three


def test_load_metrics_aligns_to_the_panel_and_stays_sealed(tmp_path: Path):
    days = pd.date_range(HOLDOUT_START - pd.Timedelta(days=4), periods=8, freq="1D", tz="UTC")
    _write_daily(tmp_path, "AUSDT", days)
    (tmp_path / "metrics_1d").mkdir()
    pd.DataFrame(
        {"timestamp": days, "sum_open_interest": np.arange(1.0, 9.0), "sum_toptrader_long_short_ratio": 2.0,
         "count_long_short_ratio": 1.0}
    ).to_csv(tmp_path / "metrics_1d" / "AUSDT.csv", index=False)
    panel = load_metrics(tmp_path, load_panel(tmp_path))
    assert panel.index.max() < HOLDOUT_START
    assert panel["open_interest"]["AUSDT"].tolist() == [1.0, 2.0, 3.0, 4.0]
    assert panel["global_ls_accounts"].shape == panel["close"].shape


def test_phase2b_scores_follow_the_protocol():
    index = pd.date_range("2023-01-01", periods=20, freq="1D", tz="UTC")
    rising = pd.Series(np.exp(np.linspace(0, 1, 20)), index=index)
    fields = {
        "close": pd.DataFrame({"AUSDT": 1.0, "BUSDT": 1.0}, index=index),
        "open_interest": pd.DataFrame({"AUSDT": rising, "BUSDT": 5.0}),
        "toptrader_ls_position": pd.DataFrame({"AUSDT": 2.0, "BUSDT": 1.0}, index=index),
        "global_ls_accounts": pd.DataFrame({"AUSDT": 1.0, "BUSDT": 1.0}, index=index),
        "quote_volume": pd.DataFrame({"AUSDT": 10.0, "BUSDT": 10.0}, index=index),
        "taker_buy_quote_volume": pd.DataFrame({"AUSDT": 6.0, "BUSDT": 4.0}, index=index),
    }
    panel = Panel(fields=fields, first_bar=pd.Series(index[0], index=["AUSDT", "BUSDT"]))
    oi = TRIALS["oi_growth_7d"].compute(panel)
    assert oi["AUSDT"].iloc[-1] == pytest.approx(-7 / 19) and oi["BUSDT"].iloc[-1] == pytest.approx(0.0)
    assert oi.iloc[:7].isna().all().all()
    smart = TRIALS["smart_minus_retail_7d"].compute(panel)
    assert smart["AUSDT"].iloc[-1] == pytest.approx(np.log(2.0)) and smart.iloc[:6].isna().all().all()
    taker = TRIALS["taker_14d"].compute(panel)
    assert taker["AUSDT"].iloc[-1] == pytest.approx(0.1) and taker.iloc[:13].isna().all().all()
    assert [trial.start is not None for trial in TRIALS.values()] == [False] * 5 + [True] * 2
