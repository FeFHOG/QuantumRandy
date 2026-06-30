from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quantumrandy.backtest import summarize_ledger
from quantumrandy.config import CostConfig, ExecutionConfig
from quantumrandy.evaluator import evaluate_alpha
from quantumrandy.expression import evaluate_formula, parse_formula


def test_formula_parser_canonicalizes() -> None:
    assert parse_formula("zscore(sub(sma(close,12),sma(close,48)),48)").canonical() == (
        "zscore(sub(sma(close,12),sma(close,48)),48)"
    )


def test_formula_evaluation_and_scoring_smoke() -> None:
    idx = pd.date_range("2024-01-01", periods=160, freq="4h", tz="UTC")
    close = pd.Series(range(160), index=idx, dtype=float) + 100
    data = pd.DataFrame(
        {
            "open": close,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": 1000.0,
            "funding_rate": 0.0001,
        },
        index=idx,
    )
    factor = evaluate_formula("zscore(ret(close,6),48)", data)
    assert len(factor) == len(data)
    assert factor.iloc[:53].isna().all()
    assert factor.iloc[53:].notna().all()
    result = evaluate_alpha("zscore(ret(close,6),48)", data, CostConfig(), ExecutionConfig(), 4)
    assert 0.0 <= result.score <= 1.0


@pytest.mark.parametrize(
    "formula",
    [
        "clip(zscore(close,12),-2,2)",
        "winsorize(close,12)",
        "decay_linear(close,12)",
        "ts_argmax(close,12)",
        "ts_argmin(close,12)",
        "skew(close,12)",
        "kurtosis(close,12)",
    ],
)
def test_formula_evaluation_supports_expanded_operators(formula: str) -> None:
    idx = pd.date_range("2024-01-01", periods=80, freq="4h", tz="UTC")
    close = pd.Series(np.sin(np.arange(80) / 5.0), index=idx, dtype=float) + 100
    data = pd.DataFrame(
        {
            "open": close,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": 1000.0 + np.arange(80),
            "funding_rate": 0.0001,
        },
        index=idx,
    )

    result = evaluate_formula(formula, data)

    assert len(result) == len(data)
    assert result.iloc[-10:].notna().any()


@pytest.mark.parametrize(
    "formula, message",
    [
        ("sma(close)", "expects 2 arguments"),
        ("corr(close,volume)", "expects 3 arguments"),
        ("zscore(close,1)", "integer window >= 2"),
        ("ret(close,2.5)", "integer window >= 2"),
        ("clip(close,high,1)", "numeric constant arguments"),
        ("clip(close,2,-2)", "lower <= upper"),
    ],
)
def test_formula_parser_rejects_invalid_operator_signatures(formula: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        parse_formula(formula)


def test_predictive_metrics_exclude_warmup_rows() -> None:
    idx = pd.date_range("2024-01-01", periods=5, freq="4h", tz="UTC")
    ledger = pd.DataFrame(
        {
            "factor": [np.nan, np.nan, 1.0, -1.0, 1.0],
            "r_mkt": [0.0, 0.0, 0.01, 0.02, -0.03],
            "r_net": 0.0,
            "delta_exposure": 0.0,
        },
        index=idx,
    )
    metrics = summarize_ledger(ledger, bar_hours=4)
    assert metrics["predictive_observations"] == 2.0
    assert metrics["directional_win_rate"] == 1.0
