"""Anytime-valid sequential tests for forward paper observation (testing by betting).

A bettor stakes ``stake_t`` times its wealth on each day's return, choosing the stake only from earlier days. If the
null holds (every day's return has conditional mean at most the null mean), its wealth is a nonnegative supermartingale,
so by Ville's inequality the chance that the wealth *ever* reaches ``threshold`` is at most ``1 / threshold``. The test
can be checked every day and stopped at any time without inflating that error rate (Shafer 2021, "Testing by betting";
Waudby-Smith and Ramdas 2024, "Estimating means of bounded random variables by betting").

Two bettors run side by side on the same stakes:

- ``e_edge`` bets that the mean daily net return is above 0. Reaching the threshold rejects "no edge".
- ``e_futility`` bets that it is below the development-window mean. Reaching the threshold rejects "the edge is as large
  as the backtest says".

The stake is a fraction of the Kelly bet implied by the development-window Sharpe ratio, rescaled by an EWMA estimate of
the current daily volatility. Wealth stays nonnegative as long as no day moves more than ``1 / stake_cap``.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class BettingSpec:
    mean0: float  # development-window mean daily net return
    sigma0: float  # development-window standard deviation of daily net returns
    kelly_fraction: float = 0.5
    halflife_days: float = 60.0
    stake_cap: float = 3.0
    threshold: float = 20.0  # 1 / alpha

    @property
    def sharpe0(self) -> float:
        return self.mean0 / self.sigma0

    @property
    def decay(self) -> float:
        return 1.0 - 0.5 ** (1.0 / self.halflife_days)

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


def eprocesses(returns: pd.Series, spec: BettingSpec) -> pd.DataFrame:
    """Per day: the stake set before the day, the volatility estimate it used, and both bettors' wealth after it."""
    x = returns.astype(float).to_numpy()
    sigma_hat, stake = _stakes(x[None, :], spec)
    edge = np.cumprod(1.0 + stake[0] * x)
    futility = np.cumprod(1.0 - stake[0] * (x - spec.mean0))
    return pd.DataFrame(
        {
            "net_return": x,
            "sigma_hat": sigma_hat[0],
            "stake": stake[0],
            "e_edge": edge,
            "e_futility": futility,
            "bound_ok": (1.0 + stake[0] * x > 0.0) & (1.0 - stake[0] * (x - spec.mean0) > 0.0),
        },
        index=returns.index,
    )


def decision(frame: pd.DataFrame, spec: BettingSpec) -> dict[str, object]:
    """First day each bettor reached the threshold (None if not yet) and the verdict it implies."""

    def first(column: str) -> str | None:
        hit = frame.index[frame[column].to_numpy() >= spec.threshold]
        return str(hit[0].date()) if len(hit) else None

    edge_day, futility_day = first("e_edge"), first("e_futility")
    if edge_day and (not futility_day or edge_day <= futility_day):
        verdict = "edge_confirmed"
    elif futility_day:
        verdict = "retire"
    else:
        verdict = "continue"
    return {
        "verdict": verdict,
        "edge_confirmed_on": edge_day,
        "futility_on": futility_day,
        "e_edge": float(frame["e_edge"].iloc[-1]) if len(frame) else 1.0,
        "e_futility": float(frame["e_futility"].iloc[-1]) if len(frame) else 1.0,
        "bound_ok": bool(frame["bound_ok"].all()) if len(frame) else True,
    }


def operating_characteristics(
    dev_returns: pd.Series,
    spec: BettingSpec,
    *,
    true_means: dict[str, float],
    horizons_days: tuple[int, ...] = (365, 730, 1095, 1825, 3650),
    paths: int = 2000,
    mean_block: int = 20,
    seed: int = 7,
) -> pd.DataFrame:
    """Chance of each verdict by each horizon when the true mean is each of ``true_means``.

    Paths are stationary-bootstrap resamples of the development returns (mean block ``mean_block`` days, which keeps
    volatility clustering and fat tails), shifted to the scenario's mean.
    """
    base = dev_returns.dropna().astype(float).to_numpy()
    days = max(horizons_days)
    index = _stationary_bootstrap(len(base), paths, days, mean_block, np.random.default_rng(seed))
    rows = []
    for name, mean in true_means.items():
        x = base[index] - base.mean() + mean
        _, stake = _stakes(x, spec)
        log_edge = np.cumsum(np.log(np.maximum(1.0 + stake * x, 1e-300)), axis=1)
        log_futility = np.cumsum(np.log(np.maximum(1.0 - stake * (x - spec.mean0), 1e-300)), axis=1)
        level = math.log(spec.threshold)
        edge_time = _first_crossing(log_edge >= level)
        futility_time = _first_crossing(log_futility >= level)
        sharpe = mean / base.std() * 365**0.5
        row: dict[str, object] = {"scenario": name, "true_mean_daily": mean, "annual_sharpe": sharpe}
        for horizon in horizons_days:
            years = f"{horizon / 365:g}y"
            row[f"edge_by_{years}"] = float(np.mean((edge_time < horizon) & (edge_time <= futility_time)))
            row[f"retire_by_{years}"] = float(np.mean((futility_time < horizon) & (futility_time < edge_time)))
        rows.append(row)
    return pd.DataFrame(rows)


def _stakes(x: np.ndarray, spec: BettingSpec) -> tuple[np.ndarray, np.ndarray]:
    """EWMA volatility known before each day (seeded with ``sigma0``) and the stake it implies, for paths x days."""
    variance = np.empty_like(x)
    current = np.full(x.shape[0], spec.sigma0**2)
    for t in range(x.shape[1]):
        variance[:, t] = current
        current = (1.0 - spec.decay) * current + spec.decay * x[:, t] ** 2
    sigma_hat = np.sqrt(variance)
    stake = np.minimum(spec.kelly_fraction * spec.sharpe0 / sigma_hat, spec.stake_cap)
    return sigma_hat, stake


def _stationary_bootstrap(n: int, paths: int, days: int, mean_block: int, rng: np.random.Generator) -> np.ndarray:
    index = np.empty((paths, days), dtype=np.int64)
    index[:, 0] = rng.integers(0, n, paths)
    restart = rng.random((paths, days)) < 1.0 / mean_block
    fresh = rng.integers(0, n, (paths, days))
    for t in range(1, days):
        index[:, t] = np.where(restart[:, t], fresh[:, t], (index[:, t - 1] + 1) % n)
    return index


def _first_crossing(hit: np.ndarray) -> np.ndarray:
    """Index of the first True per row, or a sentinel beyond the last day."""
    any_hit = hit.any(axis=1)
    return np.where(any_hit, hit.argmax(axis=1), hit.shape[1] + 1)
