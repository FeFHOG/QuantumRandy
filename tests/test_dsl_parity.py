"""QuantumRandy's formula evaluator and RandysLab's judge interpreter are independent implementations of the same DSL.

Each checks the other: any formula both accept must produce the same factor values.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from randyslab.formula_candidates import SUPPORTED_FUNCTIONS
from randyslab.formula_candidates import evaluate_formula as judge_evaluate

from quantumrandy.expression import OPERATORS
from quantumrandy.expression import evaluate_formula as miner_evaluate

PARITY_CORPUS = [
    "neg(zscore(funding_rate,42))",
    "zscore(ret(close,6),48)",
    "zscore(sub(sma(close,12),sma(close,48)),48)",
    "zscore(div(sub(close,sma(close,24)),std(close,24)),48)",
    "zscore(volume,48)",
    "zscore(corr(funding_rate,ret(close,42),120),72)",
    "neg(zscore(div(ema(funding_rate,12),div(sub(max(high,96),min(low,96)),close)),120))",
    "zscore(sub(ema(close,24),ema(close,96)),72)",
    "zscore(ema(volume,48),120)",
    "div(close,sma(close,48))",
    "rsi(close,14)",
    "zscore(rsi(close,14),72)",
    "sign(delta(close,6))",
    "mul(sign(ret(close,12)),abs(zscore(volume,24)))",
    "log(div(volume,sma(volume,48)))",
    "sqrt(abs(ret(close,24)))",
    "add(zscore(funding_rate,42),zscore(ret(close,24),42))",
    "corr(ret(close,6),ret(volume,6),48)",
    "div(sub(high,low),close)",
    "zscore(mul(funding_rate,10000),180)",
    "sub(max(close,24),min(close,24))",
    "neg(ret(open,3))",
]


def _market(n: int = 900, seed: int = 21) -> tuple[pd.DataFrame, pd.Series]:
    rng = np.random.default_rng(seed)
    index = pd.date_range("2023-01-01", periods=n, freq="4h", tz="UTC")
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.01, n)))
    frame = pd.DataFrame(
        {
            "open": close * (1.0 + rng.normal(0.0, 0.001, n)),
            "high": close * 1.004,
            "low": close * 0.996,
            "close": close,
            "volume": rng.lognormal(0.0, 0.3, n),
        },
        index=index,
    )
    funding = pd.Series(rng.normal(1e-4, 2e-4, n), index=index, name="funding_rate")
    return frame, funding


@pytest.mark.parametrize("formula", PARITY_CORPUS)
def test_miner_and_judge_evaluate_formulas_identically(formula: str):
    ohlcv, funding = _market()
    miner = miner_evaluate(formula, ohlcv.assign(funding_rate=funding))
    judge = judge_evaluate(formula, ohlcv, funding)
    assert miner.index.equals(judge.index)
    np.testing.assert_allclose(miner.to_numpy(), judge.to_numpy(), rtol=1e-9, atol=1e-12, equal_nan=True)


def test_judge_operator_gap_is_known():
    # Formulas using these miner operators cannot be judged by RandysLab until the judge supports them.
    assert set(OPERATORS) - set(SUPPORTED_FUNCTIONS) == {
        "clip",
        "decay_linear",
        "delay",
        "kurtosis",
        "rank",
        "skew",
        "ts_argmax",
        "ts_argmin",
        "winsorize",
    }
