from __future__ import annotations

from types import SimpleNamespace

import math

from quantumrandy.evaluator import AlphaResult
from quantumrandy.mcts import DIMENSIONS, AlphaMCTS, Node
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


def test_rewrite_failed_alphas_adds_and_audits_candidate(monkeypatch) -> None:
    killed = _alpha("zscore(ret(close,6),48)", depth=1)
    rewritten = _alpha("zscore(ema(ret(close,6),48),72)", depth=2)
    generator = SimpleNamespace(
        rewrite=lambda formula, reasons, detail, count, forbidden: [rewritten.formula],
    )
    mcts = SimpleNamespace(
        zoo=[killed],
        generator=generator,
        _evaluate_one=lambda formula: rewritten,
    )

    def maybe_add(alpha):
        mcts.zoo.append(alpha)

    mcts._maybe_add_to_zoo = maybe_add
    session = object.__new__(ResearchSession)
    session.cfg = SimpleNamespace(
        mcts=SimpleNamespace(seed_formulas=[], fsa_top_k=8, proposal_count=2),
        costs=SimpleNamespace(),
        execution=SimpleNamespace(),
        bar_hours=4,
    )
    session.train_data = SimpleNamespace()
    session.validation_data = SimpleNamespace()
    session.mcts = mcts
    session.brutal_results = {}
    session.rewrite_attempted = set()

    def fake_filter(formula, *args, **kwargs):
        return {
            "passed": formula == rewritten.formula,
            "brutal_score": 1.0,
            "gates": {
                "predictive_power": {"pass": True},
                "homogeneity": {"pass": True},
                "friction_audit": {"pass": True},
                "lifetime": {"pass": True},
            },
            "validation": {"sharpe": 0.1, "rank_ic": 0.02},
        }

    monkeypatch.setattr("quantumrandy.research.run_brutal_filter", fake_filter)

    session._rewrite_failed_alphas(
        [(killed.formula, ["friction_audit"], {"passed": False})],
        [],
        thresholds=SimpleNamespace(),
    )

    assert killed.formula in session.rewrite_attempted
    assert rewritten in mcts.zoo
    assert session.brutal_results[rewritten.formula]["passed"] is True


def test_mcts_sample_weak_dimension_tolerates_nan_scores() -> None:
    mcts = object.__new__(AlphaMCTS)
    import random

    mcts.random = random.Random(1)
    choice = mcts._sample_weak_dimension({dim: math.nan for dim in DIMENSIONS})

    assert choice in DIMENSIONS
