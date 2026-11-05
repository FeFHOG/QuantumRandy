"""Find the formulas recorded in historical report artifacts (JSON, JSONL and CSV), for trial-count backfills."""

from __future__ import annotations

import csv
import json
from collections.abc import Iterator
from pathlib import Path

from .expression import parse_formula

FORMULA_KEYS = {
    "formula",
    "best_formula",
    "parent_formula",
    "rewrite_formula",
    "candidate_formula",
    "selected_formula",
    "best_candidate_formula",
}
MAX_FILE_BYTES = 20_000_000
csv.field_size_limit(10_000_000)


def scan_formulas(root: str | Path) -> set[str]:
    """Distinct canonical formulas found in artifacts under ``root`` (bar-level ledgers and trial ledgers skipped)."""
    found: set[str] = set()
    for path in sorted(Path(root).rglob("*")):
        if not scannable(path) or "trial_ledger" in path.parts:
            continue
        for raw in formulas_in(path):
            formula = canonical(raw)
            if formula:
                found.add(formula)
    return found


def scannable(path: Path) -> bool:
    if not path.is_file() or path.suffix not in {".json", ".jsonl", ".csv"}:
        return False
    if "ledger" in path.name and path.suffix == ".csv":
        return False
    return path.stat().st_size <= MAX_FILE_BYTES


def formulas_in(path: Path) -> Iterator[str]:
    try:
        if path.suffix == ".csv":
            with path.open(encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                keys = [key for key in reader.fieldnames or [] if key in FORMULA_KEYS]
                for row in reader if keys else []:
                    for key in keys:
                        if row.get(key):
                            yield row[key]
        elif path.suffix == ".jsonl":
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    yield from _walk(json.loads(line))
        else:
            yield from _walk(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, csv.Error):
        return


def canonical(raw: str) -> str | None:
    try:
        return parse_formula(raw.strip()).canonical()
    except (SyntaxError, ValueError, TypeError):
        return None


def _walk(node: object) -> Iterator[str]:
    if isinstance(node, dict):
        for key, value in node.items():
            if key in FORMULA_KEYS and isinstance(value, str):
                yield value
            else:
                yield from _walk(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk(item)
