from __future__ import annotations

import pandas as pd

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
    result = evaluate_alpha("zscore(ret(close,6),48)", data, CostConfig(), ExecutionConfig(), 4)
    assert 0.0 <= result.score <= 1.0
