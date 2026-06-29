from __future__ import annotations

from types import SimpleNamespace

from quantumrandy.evaluator import AlphaResult
from quantumrandy.mcts import Node
from quantumrandy.research import ResearchSession


def _alpha(formula: str, depth: int) -> AlphaResult:
    return AlphaResult(formula=formula, score=0.1, dimensions={}, metrics={}, depth=depth)


def test_purge_killed_preserves_mcts_node_indexes() -> None:
    seed = _alpha("close", depth=0)
    killed = _alpha("zscore(close,12)", depth=2)
    nodes = [
        Node(seed.formula, seed, parent=None, action="seed", depth=0, children=[1]),
        Node(killed.formula, killed, parent=0, action="expand", depth=1),
    ]
    session = object.__new__(ResearchSession)
    session.cfg = SimpleNamespace(mcts=SimpleNamespace(seed_formulas=[seed.formula]))
    session.mcts = SimpleNamespace(zoo=[seed, killed], nodes=nodes)
    session.brutal_results = {
        seed.formula: {"passed": False},
        killed.formula: {"passed": False},
    }

    assert session._purge_killed_locked() == 1
    assert [alpha.formula for alpha in session.mcts.zoo] == [seed.formula]
    assert session.mcts.nodes == nodes
    assert session.mcts.nodes[0].children == [1]
    assert session.mcts.nodes[1].parent == 0
