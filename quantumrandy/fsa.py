from __future__ import annotations

from collections import Counter

from .expression import subtrees


def frequent_subtrees(formulas: list[str], top_k: int = 8) -> list[str]:
    if not formulas:
        return []
    counter: Counter[str] = Counter()
    for formula in formulas:
        counter.update(item for item in set(subtrees(formula)) if "(" in item)
    return [item for item, _ in counter.most_common(top_k)]


def violates_forbidden(formula: str, forbidden: list[str]) -> bool:
    found = set(subtrees(formula))
    return any(item in found for item in forbidden)
