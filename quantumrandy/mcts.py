from __future__ import annotations

import json
import math
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from pathlib import Path

import pandas as pd

from .config import CostConfig, ExecutionConfig, MCTSConfig
from .evaluator import AlphaResult, evaluate_alpha
from .fsa import frequent_subtrees
from .llm import FormulaGenerator
from .io_utils import safe_write_csv, safe_write_json


DIMENSIONS = ["effectiveness", "stability", "turnover", "diversity", "overfit_risk"]


@dataclass
class Node:
    formula: str
    result: AlphaResult
    parent: int | None
    action: str
    depth: int
    visits: int = 1
    value: float = 0.0
    children: list[int] = field(default_factory=list)


class AlphaMCTS:
    def __init__(
        self,
        data: pd.DataFrame,
        costs: CostConfig,
        execution: ExecutionConfig,
        bar_hours: int,
        config: MCTSConfig,
        generator: FormulaGenerator,
    ) -> None:
        self.data = data
        self.costs = costs
        self.execution = execution
        self.bar_hours = bar_hours
        self.config = config
        self.generator = generator
        self.random = random.Random(11)
        self.nodes: list[Node] = []
        self.zoo: list[AlphaResult] = []
        self.log_path: Path | None = None

    def initialize(self) -> None:
        for formula in self.config.seed_formulas:
            description = self.generator.descriptions.get(formula, "Seed formula from the configured initial alpha set.")
            metadata = self.generator.proposal_metadata.get(formula, {})
            result = evaluate_alpha(
                formula,
                self.data,
                self.costs,
                self.execution,
                self.bar_hours,
                self.zoo,
                description=description,
                hypothesis=metadata.get("hypothesis", ""),
                expected_edge=metadata.get("expected_edge", ""),
                expected_failure_mode=metadata.get("expected_failure_mode", ""),
                rewrite_plan_if_killed=metadata.get("rewrite_plan_if_killed", ""),
                complexity_penalty=self.config.complexity_penalty,
            )
            node = Node(formula=result.formula, result=result, parent=None, action="seed", depth=0, value=result.score)
            self.nodes.append(node)
            self._maybe_add_to_zoo(result)

    def run(self, iterations: int) -> list[AlphaResult]:
        if not self.nodes:
            self.initialize()
        for _ in range(iterations):
            idx = self._select_node()
            self._expand(idx)
        return sorted(self.zoo, key=lambda item: item.score, reverse=True)

    def _select_node(self) -> int:
        expandable = [i for i, n in enumerate(self.nodes) if n.depth < self.config.max_depth]
        if not expandable:
            return max(range(len(self.nodes)), key=lambda i: self.nodes[i].result.score)
        return max(expandable, key=self._uct)

    def _uct(self, idx: int) -> float:
        node = self.nodes[idx]
        parent_visits = self.nodes[node.parent].visits if node.parent is not None else sum(n.visits for n in self.nodes)
        exploit = node.value
        explore = self.config.exploration_weight * math.sqrt(math.log(max(parent_visits, 2)) / max(node.visits, 1))
        virtual_expand_bonus = 0.04 / (1 + len(node.children))
        return exploit + explore + virtual_expand_bonus

    def _expand(self, idx: int) -> None:
        node = self.nodes[idx]
        forbidden = frequent_subtrees([a.formula for a in self.zoo], self.config.fsa_top_k)
        # Whitelist funding_rate patterns — they are effective, don't ban them.
        forbidden = [p for p in forbidden if "funding_rate" not in p]
        dimension = self._sample_weak_dimension(node.result.dimensions)
        proposals = self.generator.propose(node.formula, dimension, self.config.proposal_count, forbidden)
        results = self._evaluate_proposals(proposals)
        for result in results:
            child = Node(
                formula=result.formula,
                result=result,
                parent=idx,
                action=f"improve_{dimension}",
                depth=node.depth + 1,
                value=result.score,
            )
            child_idx = len(self.nodes)
            self.nodes.append(child)
            node.children.append(child_idx)
            self._backpropagate(child_idx, result.score)
            self._maybe_add_to_zoo(result)

    def _evaluate_proposals(self, proposals: list[str]) -> list[AlphaResult]:
        known_formulas = {node.formula for node in self.nodes}
        proposals = list(dict.fromkeys(formula for formula in proposals if formula not in known_formulas))
        if not proposals:
            return []
        workers = max(int(self.config.eval_workers), 1)
        if workers == 1 or len(proposals) == 1:
            results = []
            for formula in proposals:
                try:
                    results.append(self._evaluate_one(formula))
                except Exception:
                    continue
            return results
        results: list[AlphaResult] = []
        with ThreadPoolExecutor(max_workers=min(workers, len(proposals))) as pool:
            futures = [
                pool.submit(self._evaluate_one, formula) for formula in proposals
            ]
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception:
                    continue
        return sorted(results, key=lambda result: result.score, reverse=True)

    def _evaluate_one(self, formula: str) -> AlphaResult:
        metadata = self.generator.proposal_metadata.get(formula, {})
        return evaluate_alpha(
            formula,
            self.data,
            self.costs,
            self.execution,
            self.bar_hours,
            self.zoo,
            description=self.generator.descriptions.get(formula, ""),
            hypothesis=metadata.get("hypothesis", ""),
            expected_edge=metadata.get("expected_edge", ""),
            expected_failure_mode=metadata.get("expected_failure_mode", ""),
            rewrite_plan_if_killed=metadata.get("rewrite_plan_if_killed", ""),
            complexity_penalty=self.config.complexity_penalty,
        )

    def _sample_weak_dimension(self, dimensions: dict[str, float]) -> str:
        weights = []
        for dim in DIMENSIONS:
            value = float(dimensions.get(dim, 0.5))
            if not math.isfinite(value):
                value = 0.5
            weights.append(max(1.0 - value, 0.05))
        return self.random.choices(DIMENSIONS, weights=weights, k=1)[0]

    def _backpropagate(self, idx: int, reward: float) -> None:
        current: int | None = idx
        while current is not None:
            node = self.nodes[current]
            node.visits += 1
            if self.config.backup_strategy == "average":
                node.value += (reward - node.value) / node.visits
            else:
                node.value = max(node.value, reward)
            current = node.parent

    def _maybe_add_to_zoo(self, result: AlphaResult) -> None:
        if any(existing.formula == result.formula for existing in self.zoo):
            return
        if result.depth == 0 or result.metrics["ic"] > 0 or result.score >= 0.55:
            self.zoo.append(result)
            # Cap zoo size: keep top 50 by score, plus all depth-0 seeds
            if len(self.zoo) > 50:
                seeds = [a for a in self.zoo if a.depth == 0]
                non_seeds = sorted(
                    [a for a in self.zoo if a.depth > 0],
                    key=lambda a: a.score,
                    reverse=True,
                )
                self.zoo = seeds + non_seeds[:50]

    def save(self, out_dir: str | Path) -> None:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        rows = []
        for alpha in sorted(self.zoo, key=lambda item: item.score, reverse=True):
            rows.append(
                {
                    "formula": alpha.formula,
                    "description": alpha.description,
                    "hypothesis": alpha.hypothesis,
                    "expected_edge": alpha.expected_edge,
                    "expected_failure_mode": alpha.expected_failure_mode,
                    "rewrite_plan_if_killed": alpha.rewrite_plan_if_killed,
                    "depth": alpha.depth,
                    "operators": alpha.operators,
                    "score": alpha.score,
                    **alpha.dimensions,
                    **alpha.metrics,
                }
            )
        safe_write_csv(out / "alphas.csv", pd.DataFrame(rows), out / "events.jsonl")
        tree = [
            {
                "id": i,
                "formula": node.formula,
                "description": node.result.description,
                "hypothesis": node.result.hypothesis,
                "expected_edge": node.result.expected_edge,
                "expected_failure_mode": node.result.expected_failure_mode,
                "rewrite_plan_if_killed": node.result.rewrite_plan_if_killed,
                "depth": node.result.depth,
                "operators": node.result.operators,
                "parent": node.parent,
                "action": node.action,
                "depth": node.depth,
                "visits": node.visits,
                "value": node.value,
                "score": node.result.score,
                "children": node.children,
            }
            for i, node in enumerate(self.nodes)
        ]
        safe_write_json(out / "tree.json", tree, out / "events.jsonl")
        safe_write_json(out / "zoo.json", [asdict(a) for a in self.zoo], out / "events.jsonl")
