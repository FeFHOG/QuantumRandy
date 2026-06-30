from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from .evaluator import AlphaResult


@dataclass(frozen=True)
class ParetoObjective:
    name: str
    higher_is_better: bool = True


DEFAULT_OBJECTIVES = [
    ParetoObjective("rank_ic", True),
    ParetoObjective("sharpe", True),
    ParetoObjective("turnover", False),
    ParetoObjective("max_dd", False),
    ParetoObjective("diversity", True),
    ParetoObjective("simplicity", True),
    ParetoObjective("operators", False),
]


def build_pareto_archive(
    alphas: list[AlphaResult],
    *,
    objectives: list[ParetoObjective] | None = None,
) -> tuple[pd.DataFrame, dict[str, int]]:
    objectives = objectives or DEFAULT_OBJECTIVES
    rows = [_alpha_row(alpha) for alpha in alphas]
    ranks = pareto_ranks(rows, objectives)
    for row, rank in zip(rows, ranks, strict=False):
        row["pareto_rank"] = rank
        row["pareto_front"] = rank == 1
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.sort_values(["pareto_rank", "mcts_score"], ascending=[True, False])
    rank_counts = frame["pareto_rank"].value_counts().sort_index().to_dict() if not frame.empty else {}
    return frame, {str(key): int(value) for key, value in rank_counts.items()}


def pareto_ranks(rows: list[dict[str, Any]], objectives: list[ParetoObjective] | None = None) -> list[int]:
    objectives = objectives or DEFAULT_OBJECTIVES
    remaining = set(range(len(rows)))
    ranks = [0 for _ in rows]
    rank = 1
    while remaining:
        front = []
        for idx in remaining:
            if not any(_dominates(rows[other], rows[idx], objectives) for other in remaining if other != idx):
                front.append(idx)
        for idx in front:
            ranks[idx] = rank
        remaining -= set(front)
        rank += 1
    return ranks


def _dominates(left: dict[str, Any], right: dict[str, Any], objectives: list[ParetoObjective]) -> bool:
    better_or_equal = True
    strictly_better = False
    for objective in objectives:
        left_value = _num(left.get(objective.name))
        right_value = _num(right.get(objective.name))
        if objective.higher_is_better:
            if left_value < right_value:
                better_or_equal = False
                break
            strictly_better = strictly_better or left_value > right_value
        else:
            if left_value > right_value:
                better_or_equal = False
                break
            strictly_better = strictly_better or left_value < right_value
    return better_or_equal and strictly_better


def _alpha_row(alpha: AlphaResult) -> dict[str, Any]:
    return {
        "formula": alpha.formula,
        "description": alpha.description,
        "hypothesis": alpha.hypothesis,
        "expected_edge": alpha.expected_edge,
        "expected_failure_mode": alpha.expected_failure_mode,
        "rewrite_plan_if_killed": alpha.rewrite_plan_if_killed,
        "mcts_score": alpha.score,
        "depth": alpha.depth,
        "operators": alpha.operators,
        **alpha.dimensions,
        **alpha.metrics,
    }


def _num(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if pd.notna(number) else 0.0
