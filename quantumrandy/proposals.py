from __future__ import annotations

import random

from .fsa import violates_forbidden


FIELDS = ["close", "volume", "funding_rate", "high", "low"]
WINDOWS = [3, 6, 12, 24, 42, 48, 72, 120]


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

    def _one(self, base_formula: str, dimension: str) -> str:
        field = self.random.choice(FIELDS)
        fast = self.random.choice(WINDOWS[:5])
        slow = self.random.choice([w for w in WINDOWS if w > fast])
        vol_win = self.random.choice(WINDOWS[2:])
        templates = {
            "effectiveness": [
                f"zscore(ret(close,{fast}),{vol_win})",
                f"zscore(sub(sma(close,{fast}),sma(close,{slow})),{vol_win})",
                f"zscore(div(sub(close,sma(close,{slow})),std(close,{slow})),{vol_win})",
            ],
            "stability": [
                f"zscore(ema(ret(close,{fast}),{fast}),{vol_win})",
                f"zscore(sub(ema(close,{fast}),ema(close,{slow})),{vol_win})",
                f"zscore(div(delta(close,{fast}),std(close,{slow})),{vol_win})",
            ],
            "turnover": [
                f"zscore(sub(sma(close,{slow}),sma(close,{slow * 2})),{vol_win})",
                f"zscore(ema({base_formula},{fast}),{vol_win})",
                f"zscore(sma({base_formula},{fast}),{vol_win})",
            ],
            "diversity": [
                f"neg(zscore(funding_rate,{slow}))",
                f"zscore(corr(ret(close,{fast}),ret(volume,{fast}),{slow}),{vol_win})",
                f"zscore(div(sub(high,low),close),{vol_win})",
            ],
            "overfit_risk": [
                f"zscore({field},{vol_win})",
                f"zscore(ret(close,{slow}),{vol_win})",
                f"zscore(sub(sma(close,{fast}),sma(close,{slow})),{slow})",
            ],
        }
        return self.random.choice(templates.get(dimension, templates["effectiveness"]))
