"""Equal-budget random-search baseline for the miner.

Random formulas are drawn uniformly from the same DSL and shape limits the miner uses and pass through the same gates.
If mined candidates do no better than this at the same number of candidates, the search adds nothing over chance; an
audited agent on BTC perpetuals matched random search exactly (arXiv 2608.25348).
"""

from __future__ import annotations

import random
from typing import Any

import pandas as pd

from .config import ProjectConfig
from .expression import FIELDS, parse_formula, validate_formula_shape
from .lab import FilterThresholds, kill_reasons, run_brutal_filter

WINDOWS = (6, 12, 24, 42, 48, 72, 96, 120, 180)
ROLLING = ("sma", "ema", "std", "zscore", "min", "max", "delta", "ret", "rank", "rsi", "decay_linear", "skew")
UNARY = ("neg", "abs", "log", "sqrt", "sign")
BINARY = ("add", "sub", "mul", "div")


def random_formula(rng: random.Random, max_depth: int, max_operators: int) -> str:
    """A random formula within the miner's shape limits (root is always an operator)."""
    for _ in range(1000):
        text = _node(rng, depth=1, max_depth=max_depth)
        try:
            validate_formula_shape(text, max_depth, max_operators)
        except ValueError:
            continue
        return parse_formula(text).canonical()
    raise RuntimeError("could not draw a formula within the shape limits")


def draw_random_formulas(budget: int, seed: int, max_depth: int, max_operators: int) -> list[str]:
    """``budget`` distinct random formulas; gate them with ``gate_row`` exactly as mined formulas are gated."""
    rng = random.Random(seed)
    formulas: list[str] = []
    seen: set[str] = set()
    while len(formulas) < budget:
        formula = random_formula(rng, max_depth, max_operators)
        if formula not in seen:
            seen.add(formula)
            formulas.append(formula)
    return formulas


def gate_row(
    formula: str,
    cfg: ProjectConfig,
    train: pd.DataFrame,
    validation: pd.DataFrame,
    history: pd.DataFrame | None,
    accepted: list[str],
    thresholds: FilterThresholds,
) -> dict[str, Any]:
    """Run the research loop's four gates on one formula and flatten the verdict into a row."""
    try:
        result = run_brutal_filter(
            formula,
            train,
            validation,
            cfg.costs,
            cfg.execution,
            cfg.bar_hours,
            accepted,
            thresholds=thresholds,
            history=history,
        )
    except Exception as exc:  # malformed numerics in a random formula are a failed trial, not a crash
        return {"formula": formula, "passed": False, "error": str(exc)[:200]}
    return {
        "formula": formula,
        "passed": bool(result["passed"]),
        "kill_reasons": ";".join(kill_reasons(result["gates"])),
        "train_rank_ic": result["train"]["rank_ic"],
        "train_sharpe": result["train"]["sharpe"],
        "validation_rank_ic": result["validation"]["rank_ic"],
        "validation_sharpe": result["validation"]["sharpe"],
        "validation_max_dd": result["validation"]["max_dd"],
        "validation_turnover": result["validation"]["turnover"],
    }


def _node(rng: random.Random, depth: int, max_depth: int) -> str:
    if depth > 1 and (depth >= max_depth or rng.random() < 0.3):
        return rng.choice(sorted(FIELDS))
    draw = rng.random()
    if draw < 0.55:
        return f"{rng.choice(ROLLING)}({_node(rng, depth + 1, max_depth)},{rng.choice(WINDOWS)})"
    if draw < 0.75:
        left, right = _node(rng, depth + 1, max_depth), _node(rng, depth + 1, max_depth)
        return f"{rng.choice(BINARY)}({left},{right})"
    if draw < 0.9:
        return f"{rng.choice(UNARY)}({_node(rng, depth + 1, max_depth)})"
    left, right = _node(rng, depth + 1, max_depth), _node(rng, depth + 1, max_depth)
    return f"corr({left},{right},{rng.choice(WINDOWS)})"
