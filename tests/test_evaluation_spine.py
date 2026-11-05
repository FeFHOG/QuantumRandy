from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from quantumrandy import dashboard
from quantumrandy.backtest import run_formula_backtest, signal_from_factor, summarize_ledger
from quantumrandy.config import CostConfig, ExecutionConfig, FilterConfig, MCTSConfig, ProjectConfig, WindowConfig
from quantumrandy.data import load_market_frame
from quantumrandy.expression import evaluate_formula
from quantumrandy.lab import estimate_halflife_bars, passes_basic
from quantumrandy.research import restore_killed_history
from quantumrandy.walk_forward import build_walk_forward_windows, run_walk_forward


def _market(n: int = 1500, seed: int = 11) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    index = pd.date_range("2022-01-01", periods=n, freq="4h", tz="UTC")
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.01, n)))
    return pd.DataFrame(
        {
            "open": close,
            "high": close * 1.005,
            "low": close * 0.995,
            "close": close,
            "volume": rng.uniform(1.0, 2.0, n),
            "funding_rate": rng.normal(1e-4, 1e-4, n),
        },
        index=index,
    )


def test_positions_no_longer_follow_a_formulas_raw_level():
    data = _market()
    formula = "div(close,sma(close,48))"  # hovers around 1.0, so tanh(raw) > 0.15 almost always
    legacy = run_formula_backtest(data, formula, CostConfig(), ExecutionConfig(signal_mode="legacy_tanh"))
    fixed = run_formula_backtest(data, formula, CostConfig(), ExecutionConfig())
    assert (legacy["exposure"] > 0).mean() > 0.95
    assert 0.2 < (fixed["exposure"] > 0).mean() < 0.8

    factor = evaluate_formula(formula, data)
    scaled = signal_from_factor(3.0 * factor + 5.0, 0.15)
    assert (signal_from_factor(factor, 0.15) != scaled).mean() < 0.001


def test_history_warm_up_matches_full_run_without_look_ahead():
    data = _market()
    window = data.iloc[800:1100]
    formula = "zscore(ret(close,6),48)"
    execution = ExecutionConfig()
    full = run_formula_backtest(data, formula, CostConfig(), execution)
    warm = run_formula_backtest(window, formula, CostConfig(), execution, history=data)
    cold = run_formula_backtest(window, formula, CostConfig(), execution)

    assert warm["exposure"].equals(full["exposure"].loc[window.index])
    assert cold["exposure"].iloc[:50].eq(0.0).all()
    truncated = run_formula_backtest(window, formula, CostConfig(), execution, history=data.loc[: window.index[-1]])
    assert truncated["r_net"].equals(warm["r_net"])
    assert warm["delta_exposure"].iloc[0] == warm["exposure"].iloc[0]


def test_settled_funding_drives_costs_and_legacy_frames_keep_the_old_approximation():
    data = _market(300)
    execution = ExecutionConfig(signal_mode="legacy_tanh", exposure_threshold=0.0)
    settled = run_formula_backtest(data.assign(funding_settled=0.002), "abs(close)", CostConfig(), execution)
    held = settled["exposure"] != 0
    assert held.any()
    assert settled.loc[held, "c_fund"].to_numpy() == pytest.approx(0.002 * settled.loc[held, "exposure"].to_numpy())

    legacy = run_formula_backtest(data, "abs(close)", CostConfig(), execution)
    assert legacy["c_fund"].to_numpy() == pytest.approx((legacy["exposure"] * data["funding_rate"] * 0.5).to_numpy())


def test_load_market_frame_floors_settlement_stamps(tmp_path: Path):
    index = pd.date_range("2024-01-01", periods=6, freq="4h", tz="UTC")
    pd.DataFrame(
        {"timestamp": index, "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0}
    ).to_csv(tmp_path / "ohlcv.csv", index=False)
    pd.DataFrame({"timestamp": ["2024-01-01T08:00:00.008Z"], "funding_rate": [0.001]}).to_csv(
        tmp_path / "funding.csv", index=False
    )
    frame = load_market_frame(tmp_path / "ohlcv.csv", tmp_path / "funding.csv")
    assert frame["funding_settled"].tolist() == pytest.approx([0.0, 0.001, 0.0, 0.0, 0.0, 0.0])
    assert frame["funding_rate"].tolist() == pytest.approx([0.0, 0.0, 0.001, 0.001, 0.001, 0.001])


def test_resume_never_restores_pass_verdicts():
    rows = [
        {"formula": "in_zoo_passed", "passed": True},
        {"formula": "left_zoo_passed", "passed": True},
        {"formula": "left_zoo_killed", "passed": False, "gate_predictive_power": False},
        {"formula": "in_zoo_killed", "passed": False},
    ]
    restored = restore_killed_history(rows, {"in_zoo_passed", "in_zoo_killed"})
    assert set(restored) == {"left_zoo_killed"}
    assert restored["left_zoo_killed"]["passed"] is False
    assert restored["left_zoo_killed"]["restored_from_leaderboard"] is True


def test_halflife_counts_a_sign_flip_as_decay():
    rng = np.random.default_rng(5)
    n = 5000
    factor = pd.Series(rng.normal(size=n))
    lagged = 0.3 * factor.shift(1).fillna(0.0) - 0.3 * factor.shift(2).fillna(0.0)
    returns = lagged + pd.Series(rng.normal(scale=0.5, size=n))
    # One bar ahead the factor predicts +, two bars ahead it predicts -: that is decay, not persistence.
    assert estimate_halflife_bars(factor, returns) == 2


def test_shared_pass_rule_uses_cost_sharpe_in_sample_and_validation_sharpe_out_of_sample():
    filters = FilterConfig(
        min_rank_ic=0.0, min_directional_win_rate=0.0, min_cost_sharpe=0.3, min_validation_sharpe=0.0
    )
    metrics = {"rank_ic": 0.01, "directional_win_rate": 0.5, "sharpe": 0.1}
    assert passes_basic(metrics, filters, in_sample=False)
    assert not passes_basic(metrics, filters, in_sample=True)


def test_walk_forward_separates_test_segments_after_the_selection_end():
    data = _market(3000)
    cfg = ProjectConfig(
        symbol="BTCUSDT",
        bar_hours=4,
        ohlcv_csv=Path("unused.csv"),
        funding_csv=Path("unused.csv"),
        costs=CostConfig(),
        execution=ExecutionConfig(),
        windows=WindowConfig(),
        mcts=MCTSConfig(),
    )
    windows = build_walk_forward_windows(
        data, train_months=3, validation_months=2, test_months=1, step_months=1, min_bars=50
    )
    selection_end = windows[len(windows) // 2].test_start
    _, summary = run_walk_forward(
        data, [{"formula": "zscore(ret(close,6),48)"}], cfg, windows, selection_end=selection_end
    )
    expected = sum(1 for window in windows if window.test_start >= selection_end)
    assert 0 < expected < len(windows)
    assert int(summary.loc[0, "oos_windows"]) == expected


def test_summary_reports_score_based_and_raw_rank_ic():
    ledger = run_formula_backtest(_market(), "div(close,sma(close,48))", CostConfig(), ExecutionConfig())
    metrics = summarize_ledger(ledger, 4)
    assert {"rank_ic", "rank_ic_raw", "final_equity"} <= set(metrics)


def test_blind_validation_refuses_to_fall_back_to_full_history(tmp_path: Path):
    (tmp_path / "BTCUSDT_4h.csv").write_text("timestamp,open,high,low,close,volume\n", encoding="utf-8")
    (tmp_path / "BTCUSDT_funding.csv").write_text("timestamp,funding_rate\n", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="2026 blind data not found"):
        dashboard._load_blind_data(tmp_path)
