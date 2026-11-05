from __future__ import annotations

import json
from pathlib import Path

from quantumrandy.expression import validate_formula_shape
from quantumrandy.random_search import draw_random_formulas
from quantumrandy.trial_backfill import scan_formulas


def test_random_formulas_are_distinct_valid_and_reproducible():
    first = draw_random_formulas(60, seed=3, max_depth=5, max_operators=6)
    assert len(set(first)) == 60
    for formula in first:
        validate_formula_shape(formula, 5, 6)
    assert draw_random_formulas(60, seed=3, max_depth=5, max_operators=6) == first
    assert draw_random_formulas(60, seed=4, max_depth=5, max_operators=6) != first


def test_scan_formulas_reads_json_jsonl_csv_and_skips_ledgers(tmp_path: Path):
    zoo = [{"formula": "zscore(close,10)"}, {"x": {"best_formula": "abs(close)"}}]
    (tmp_path / "zoo.json").write_text(json.dumps(zoo))
    (tmp_path / "events.jsonl").write_text(json.dumps({"rewrite_formula": "neg(close)"}) + "\nnot json\n")
    (tmp_path / "alphas.csv").write_text("formula,score\nzscore(close,10),1\nnot a formula,2\n")
    (tmp_path / "top_ledger.csv").write_text("formula\nsqrt(close)\n")
    assert scan_formulas(tmp_path) == {"zscore(close,10)", "abs(close)", "neg(close)"}
