"""Estimate how many candidates were evaluated before the trial ledger existed.

Scans local report artifacts of QuantumRandy and RandysLab for formulas and parameter sets, adds cohort sizes that are
documented but whose raw outputs are not in this workspace, and writes a lower bound on the trial count for Deflated
Sharpe. Purged zoos, unsaved search trees and server-only outputs mean the true count is higher.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from quantumrandy.expression import parse_formula

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
CSV_FIELD_LIMIT = 10_000_000

# Cohorts whose raw outputs stayed on the research server; sizes from their reports in docs/.
DOCUMENTED_NOT_LOCAL = [
    ("research_v0_9b", 5, "candidates", "RESEARCH_V0_9B_FUNDING_PRESSURE_REPORT.md"),
    ("research_v0_9d", 48, "candidates", "RESEARCH_V0_9D_STRICT_CANDIDATE_DISCOVERY_REPORT.md"),
    ("research_1_0_replication", 60, "candidate x variant rankings", "RESEARCH_1_0_CANDIDATE_REPLICATION_REPORT.md"),
    (
        "research_v1_1",
        50,
        "candidate x variant rankings",
        "RESEARCH_V1_1_INDEPENDENT_SCOPED_FAMILY_REPLICATION_REPORT.md",
    ),
    ("research_v1_2", 60, "candidate x variant rankings", "RESEARCH_V1_2_FAILURE_GUIDED_SCOPED_RESPEC_REPORT.md"),
    ("research_v1_3", 80, "candidate x variant rankings", "RESEARCH_V1_3_FUNDING_ADJACENT_SCOPED_RESPEC_REPORT.md"),
]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--randyslab", default=str(ROOT.parent / "RandysLab-STRICT4H"))
    ap.add_argument("--out", default=str(ROOT / "reports" / "trial_ledger"))
    args = ap.parse_args()

    csv.field_size_limit(CSV_FIELD_LIMIT)
    roots = {"QuantumRandy": ROOT / "reports", "RandysLab": Path(args.randyslab) / "reports"}
    by_campaign: dict[str, set[str]] = {}
    for repo, reports in roots.items():
        for path in sorted(reports.rglob("*")):
            if not _scannable(path) or "trial_ledger" in path.parts:
                continue
            campaign = f"{repo}/{path.relative_to(reports).parts[0]}"
            for raw in _formulas_in(path):
                canonical = _canonical(raw)
                if canonical:
                    by_campaign.setdefault(campaign, set()).add(canonical)

    distinct = set().union(*by_campaign.values()) if by_campaign else set()
    stage1 = _stage1_parameter_sets(Path(args.randyslab) / "reports")
    documented = [
        {"cohort": cohort, "trials": trials, "unit": unit, "source": f"docs/{doc}"}
        for cohort, trials, unit, doc in DOCUMENTED_NOT_LOCAL
    ]
    documented_trials = sum(item["trials"] for item in documented)
    payload = {
        "artifact_type": "historical_trial_backfill",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": "Lower bound. Zoo purges, unsaved search trees and server-only outputs make the true count higher.",
        "local_distinct_formulas": len(distinct),
        "local_distinct_formulas_by_campaign": {key: len(value) for key, value in sorted(by_campaign.items())},
        "documented_not_local": documented,
        "documented_not_local_trials": documented_trials,
        # Use this for Deflated Sharpe of QuantumRandy factor candidates.
        "lower_bound_formula_trials": len(distinct) + documented_trials,
        # RandysLab Stage I baseline parameter search is a separate selection campaign.
        "randyslab_stage1_parameter_sets": stage1,
    }
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "historical_backfill.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (out / "historical_formulas.txt").write_text("\n".join(sorted(distinct)) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in payload if key != "local_distinct_formulas_by_campaign"}, indent=2))


def _scannable(path: Path) -> bool:
    if not path.is_file() or path.suffix not in {".json", ".jsonl", ".csv"}:
        return False
    if "ledger" in path.name and path.suffix == ".csv":
        return False  # bar-level ledgers carry no formulas
    return path.stat().st_size <= MAX_FILE_BYTES


def _formulas_in(path: Path) -> Iterator[str]:
    try:
        if path.suffix == ".csv":
            with path.open(encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                keys = [key for key in reader.fieldnames or [] if key in FORMULA_KEYS]
                if not keys:
                    return
                for row in reader:
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


def _canonical(raw: str) -> str | None:
    try:
        return parse_formula(raw.strip()).canonical()
    except (SyntaxError, ValueError, TypeError):
        return None


def _stage1_parameter_sets(reports: Path) -> int:
    seen: set[str] = set()
    for path in reports.rglob("trials.csv"):
        with path.open(encoding="utf-8", newline="") as handle:
            seen.update(row["theta"] for row in csv.DictReader(handle) if row.get("theta"))
    return len(seen)


if __name__ == "__main__":
    main()
