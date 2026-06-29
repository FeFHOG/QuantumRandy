from __future__ import annotations

import random

from .fsa import violates_forbidden


# price-like fields: safe for ret(), delta(), rsi()
PRICE_FIELDS = ["close", "high", "low"]
# all fields including non-price
ALL_FIELDS = ["close", "volume", "funding_rate", "high", "low"]
WINDOWS = [3, 6, 12, 24, 42, 48, 72, 120]
FAST_POOL = WINDOWS[:5]   # 3, 6, 12, 24, 42
SLOW_POOL = WINDOWS[3:]   # 24, 42, 48, 72, 120


class LocalProposalEngine:
    def __init__(self, seed: int = 7) -> None:
        self.random = random.Random(seed)

    def propose(self, base_formula: str, dimension: str, count: int, forbidden: list[str]) -> list[str]:
        candidates: list[str] = []
        attempts = 0
        while len(candidates) < count and attempts < count * 20:
            attempts += 1
            formula = self._one(base_formula, dimension)
            if formula not in candidates and not violates_forbidden(formula, forbidden):
                candidates.append(formula)
        return candidates

    def _price_field(self) -> str:
        return self.random.choice(PRICE_FIELDS)

    def _any_field(self) -> str:
        # Weight funding_rate 35% — underused but has best pass rate.
        return self.random.choices(
            ALL_FIELDS,
            weights=[0.30, 0.10, 0.35, 0.125, 0.125],  # close, volume, fr, high, low
            k=1,
        )[0]

    def _pick_windows(self) -> tuple[int, int, int]:
        fast = self.random.choice(FAST_POOL)
        slow = self.random.choice([w for w in WINDOWS if w > fast])
        vol_win = self.random.choice(SLOW_POOL)
        return fast, slow, vol_win

    def _one(self, base_formula: str, dimension: str) -> str:
        pf = self._price_field()     # for ret(), delta(), rsi()
        af = self._any_field()       # for raw zscore, sma, ema
        fast, slow, vol_win = self._pick_windows()

        templates: dict[str, list[str]] = {
            # ---- effectiveness: maximize rank_ic / predictive power ----
            "effectiveness": [
                # momentum on price field
                f"zscore(ret({pf},{fast}),{vol_win})",
                # MA crossover — trend following on any field
                f"zscore(sub(sma({af},{fast}),sma({af},{slow})),{vol_win})",
                # Bollinger-like: price distance from MA vol-normalized
                f"zscore(div(sub(close,sma(close,{slow})),std(close,{slow})),{vol_win})",
                # funding rate / volatility — risk-adjusted carry pressure
                f"zscore(div(funding_rate,std(close,{vol_win})),{vol_win})",
                # funding-momentum alignment: are flows aligned with price trend?
                f"zscore(corr(funding_rate,ret(close,{fast}),{slow}),{vol_win})",
            ],

            # ---- stability: smooth PnL, low drawdown, consistent returns ----
            "stability": [
                # EMA-smoothed momentum
                f"zscore(ema(ret({pf},{fast}),{slow}),{vol_win})",
                # EMA crossover (smoother than SMA)
                f"zscore(sub(ema({af},{fast}),ema({af},{slow})),{vol_win})",
                # smoothed funding rate — naturally mean-reverting
                f"zscore(ema(funding_rate,{slow}),{vol_win})",
                # funding rate momentum: diff of two EMAs
                f"zscore(sub(ema(funding_rate,{fast}),ema(funding_rate,{slow})),{vol_win})",
                # vol-normalized delta, longer window = stabler
                f"zscore(div(delta({pf},{slow}),std({pf},{slow})),{vol_win})",
            ],

            # ---- turnover: reduce trading frequency with slower signals ----
            "turnover": [
                # ultra-slow MA cross
                f"zscore(sub(sma({af},{slow}),sma({af},{slow * 2})),{vol_win})",
                # wrap base formula in SLOW ema → reduces signal churn
                f"zscore(ema({base_formula},{slow}),{vol_win})",
                # wrap base formula in SLOW sma
                f"zscore(sma({base_formula},{slow}),{vol_win})",
                # ultra-slow funding rate — very low turnover
                f"zscore(funding_rate,{slow * 2})",
                # volume-normalized: only signal on high-conviction bars
                f"zscore(div({base_formula},sma(volume,{slow})),{vol_win})",
            ],

            # ---- diversity: unconventional combos, low correlation to zoo ----
            "diversity": [
                f"neg(zscore(funding_rate,{slow}))",
                # price-volume return correlation — regime detection
                f"zscore(corr(ret(close,{fast}),ret(volume,{fast}),{slow}),{vol_win})",
                # high-low range / close — intra-bar volatility
                f"zscore(div(sub(high,low),close),{vol_win})",
                # funding-volume correlation: speculative flow alignment
                f"zscore(corr(funding_rate,volume,{slow}),{vol_win})",
                # funding per unit of volume — leverage demand intensity
                f"zscore(div(funding_rate,sma(volume,{slow})),{vol_win})",
            ],

            # ---- overfit_risk: simplest possible structures, 1-2 operators ----
            "overfit_risk": [
                # raw field zscore — simplest factor
                f"zscore({af},{vol_win})",
                # simple return zscore
                f"zscore(ret({pf},{slow}),{vol_win})",
                # simple MA cross, short vol window
                f"zscore(sub(sma({af},{fast}),sma({af},{slow})),{slow})",
                # single-operator funding rate
                f"neg(zscore(funding_rate,{slow}))",
                # RSI on price — classic, low overfit risk
                f"zscore(rsi({pf},{slow}),{vol_win})",
            ],
        }

        pool = templates.get(dimension, templates["effectiveness"])
        return self.random.choice(pool)
