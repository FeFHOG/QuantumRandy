from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quantumrandy.stats import finite_float, spearman_corr


def test_spearman_corr_uses_rank_correlation_without_scipy() -> None:
    left = pd.Series([1.0, 2.0, 3.0, 4.0])
    right = pd.Series([10.0, 5.0, 2.0, -1.0])

    assert spearman_corr(left, right) == pytest.approx(-1.0)


def test_spearman_corr_returns_zero_for_constant_or_too_short_inputs() -> None:
    assert spearman_corr(pd.Series([1.0]), pd.Series([2.0])) == 0.0
    assert spearman_corr(pd.Series([1.0, 1.0, 1.0]), pd.Series([1.0, 2.0, 3.0])) == 0.0


def test_finite_float_converts_nan_and_infinity_to_zero() -> None:
    assert finite_float(np.nan) == 0.0
    assert finite_float(np.inf) == 0.0
    assert finite_float(-np.inf) == 0.0
    assert finite_float(0.25) == 0.25
