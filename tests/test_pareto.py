from __future__ import annotations

import json
from types import SimpleNamespace

from quantumrandy.evaluator import AlphaResult
from quantumrandy.mcts import AlphaMCTS, Node
from quantumrandy.pareto import build_pareto_archive, pareto_ranks


def _alpha(
    formula: str,
    *,
    rank_ic: float,
    sharpe: float,
    turnover: float,
    max_dd: float,
    diversity: float = 0.8,
    simplicity: float = 0.8,
    operators: int = 3,
    score: float = 0.5,
) -> AlphaResult:
    return AlphaResult(
        formula=formula,
        score=score,
        dimensions={"diversity": diversity, "simplicity": simplicity},
        metrics={"rank_ic": rank_ic, "sharpe": sharpe, "turnover": turnover, "max_dd": max_dd},
        operators=operators,
    )


def test_pareto_ranks_keep_tradeoff_front() -> None:
    rows = [
        {"rank_ic": 0.04, "sharpe": 1.0, "turnover": 0.1, "max_dd": 0.1, "diversity": 0.8, "simplicity": 0.8, "operators": 3},
        {"rank_ic": 0.03, "sharpe": 0.8, "turnover": 0.2, "max_dd": 0.2, "diversity": 0.7, "simplicity": 0.7, "operators": 4},
        {"rank_ic": 0.02, "sharpe": 1.2, "turnover": 0.05, "max_dd": 0.08, "diversity": 0.9, "simplicity": 0.6, "operators": 5},
    ]

    ranks = pareto_ranks(rows)

    assert ranks == [1, 2, 1]


def test_build_pareto_archive_outputs_front_and_rank_counts() -> None:
    frame, rank_counts = build_pareto_archive(
        [
            _alpha("strong", rank_ic=0.04, sharpe=1.0, turnover=0.1, max_dd=0.1),
            _alpha("dominated", rank_ic=0.03, sharpe=0.8, turnover=0.2, max_dd=0.2, diversity=0.7, simplicity=0.7, operators=4),
            _alpha("tradeoff", rank_ic=0.02, sharpe=1.2, turnover=0.05, max_dd=0.08, diversity=0.9, simplicity=0.6, operators=5),
        ]
    )

    front = set(frame[frame["pareto_front"]]["formula"])
    assert front == {"strong", "tradeoff"}
    assert rank_counts == {"1": 2, "2": 1}


def test_mcts_save_writes_pareto_archive(tmp_path) -> None:
    mcts = object.__new__(AlphaMCTS)
    mcts.zoo = [
        _alpha("strong", rank_ic=0.04, sharpe=1.0, turnover=0.1, max_dd=0.1),
        _alpha("dominated", rank_ic=0.03, sharpe=0.8, turnover=0.2, max_dd=0.2, diversity=0.7, simplicity=0.7, operators=4),
    ]
    mcts.nodes = [Node(alpha.formula, alpha, parent=None, action="test", depth=0) for alpha in mcts.zoo]
    mcts.generator = SimpleNamespace(events=[])

    mcts.save(tmp_path)

    payload = json.loads((tmp_path / "pareto_archive.json").read_text(encoding="utf-8"))
    zoo = json.loads((tmp_path / "zoo.json").read_text(encoding="utf-8"))
    assert payload["artifact_type"] == "quantumrandy_pareto_mcts_archive"
    assert payload["safety"]["not_runtime_publish_payload"] is True
    assert payload["front_count"] == 1
    assert zoo[0]["pareto_rank"] == 1
    assert (tmp_path / "pareto_archive.csv").exists()
