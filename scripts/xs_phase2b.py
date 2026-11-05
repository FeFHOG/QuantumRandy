"""Phase 2b: evaluate the refined cross-sectional family (docs/PHASE2B_CROSS_SECTIONAL_PROTOCOL.md).

Step 1, ``--metrics-spans PATH``: write the days of Binance metrics to download for each contract that enters the
Phase 2a development universe, from 30 days before its first universe day (not before 2021-12-01, when metrics
coverage begins for most contracts) to its last universe day. Feed the file to
``../RandysLab-STRICT4H/scripts/fetch_metrics.py --spans``.

Step 2 (default): evaluate the 7 trials on the main and robustness universes, apply the cumulative family statistics
(N = 18 with Phase 2a's 11 trials) and the holdout-candidate rule with Deflated Sharpe convention B, and write
reports/phase2b/. Refuses to run while the metrics download is incomplete. Holdout bars stay sealed. If any trial
qualifies, it also writes the holdout pre-registration ``preregistrations/phase2b_holdout.json`` mechanically.

Step 3, ``--open-holdout PATH``: once that pre-registration is committed, open the holdout through the guard (recorded
in the trial ledger; only one pre-registration can ever open it) and apply the sign check to every candidate. Listings
that were never reviewed are classified with the forward registration's new-listing rule.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from randyslab import trial_ledger
from randyslab.accounting import CostRates
from randyslab.holdout import HOLDOUT_END, HOLDOUT_START, load_preregistration
from randyslab.stats import benjamini_hochberg, deflated_sharpe_ratio, pbo_cscv, sharpe_ratio

from quantumrandy.xsection.evaluate import (
    cross_sectional_ic,
    evaluate_book,
    evaluate_factor,
    forward_returns,
    held_weights,
    quantile_weights,
)
from quantumrandy.xsection.family_2b import TRIALS
from quantumrandy.xsection.forward import ForwardPanel, excluded_contracts, weekend_ratio
from quantumrandy.xsection.panel import Panel, load_metrics, load_panel
from quantumrandy.xsection.universe import NON_CRYPTO, base_asset, liquid_universe

DATA = ROOT.parent / "RandysLab-STRICT4H" / "data"
COSTS = CostRates(fee_bps=4.0, slippage_bps=5.0)
UNIVERSE_SIZE = 50
ROBUSTNESS_CUTOFF = "2025-09-01"
METRICS_FIRST_DAY = pd.Timestamp("2021-12-01", tz="UTC")
METRICS_PAD_DAYS = 30
N_TRIALS = 18  # Phase 2a's 11 plus these 7
YEARS = {"default": ((2021, 2022, 2023, 2024, 2025), 4), "open_interest": ((2022, 2023, 2024, 2025), 3)}
PREREGISTRATION = ROOT / "preregistrations" / "phase2b_holdout.json"
FORWARD_REGISTRATION = ROOT / "preregistrations" / "phase2a_taker_7d_forward.json"
FORWARD_EXCLUSIONS = ROOT / "preregistrations" / "forward_exclusions.json"
NEW_LISTING_CUTOFF = pd.Timestamp("2025-09-01", tz="UTC")  # the forward registration's new_listing_rule


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", default=str(DATA / "universe_1d_20261105"))
    ap.add_argument("--metrics", default=str(DATA / "metrics_1d_20261105"))
    ap.add_argument("--phase2a", default=str(ROOT / "reports" / "phase2a"))
    ap.add_argument("--out", default=str(ROOT / "reports" / "phase2b"))
    ap.add_argument("--metrics-spans", help="Only write {symbol: [first_day, last_day]} here and stop")
    ap.add_argument("--open-holdout", help="Step 3: open the holdout once with this committed pre-registration")
    ap.add_argument("--preregistration", default=str(PREREGISTRATION), help="Where step 2 writes the pre-registration")
    args = ap.parse_args()
    if args.open_holdout:
        open_holdout_step(Path(args.open_holdout), args)
        return

    panel = load_panel(args.data)
    mask = liquid_universe(panel, top_n=UNIVERSE_SIZE)
    if args.metrics_spans:
        spans = metrics_spans(mask)
        Path(args.metrics_spans).write_text(json.dumps(spans, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        days = sum((pd.Timestamp(b) - pd.Timestamp(a)).days + 1 for a, b in spans.values())
        print(f"{len(spans)} contracts, {days} contract-days -> {args.metrics_spans}")
        return

    _require_complete_metrics(Path(args.metrics), metrics_spans(mask))
    panel = load_metrics(args.metrics, panel)
    start = mask.index[mask.sum(axis=1).ge(UNIVERSE_SIZE).argmax()]
    robust_mask = liquid_universe(panel, top_n=UNIVERSE_SIZE, listed_before=ROBUSTNESS_CUTOFF)
    span = f"{panel.index[0].date()} .. {panel.index[-1].date()}"
    print(f"{len(panel.symbols)} symbols, {span}; dev start {start.date()}")
    trial_ledger.configure_default(ROOT, context={"entry_point": "xs_phase2b", "protocol": "phase2b_v1"})

    rows, returns, scores_by_trial = [], {}, {}
    for name, trial in TRIALS.items():
        scores = trial.compute(panel)
        window = max(start, trial.start) if trial.start is not None else start
        result = evaluate_factor(scores, panel, mask, COSTS, window, trial.weights)
        robust = evaluate_factor(scores, panel, robust_mask, COSTS, window, trial.weights)
        returns[name] = result.pop("returns")
        robust.pop("returns")
        scored = (scores.notna() & mask).loc[window:].sum(axis=1)
        row = {
            "factor": name,
            "description": trial.description,
            "book": trial.weights.__name__,
            "window_start": str(window.date()),
            "names_scored_median": float(scored.median()),
            **_flatten(result),
        }
        row.update({f"robust_{key}": value for key, value in _flatten(robust).items() if not key.startswith("ic_year")})
        rows.append(row)
        scores_by_trial[name] = scores
        trial_ledger.record(
            source="qr_xs_factor",
            candidate={"factor": name, "definition": trial.description, "book": row["book"], "universe": "top50"},
            window={"start": str(window), "end": str(panel.index[-1])},
            metrics={key: row[key] for key in ("ic_mean", "ic_tstat", "sharpe", "sharpe_2x_costs", "max_dd")},
        )
        print(f"  {name:22s} IC {row['ic_mean']:+.4f} (t {row['ic_tstat']:+.2f})  Sharpe {row['sharpe']:+.2f} "
              f"(2x {row['sharpe_2x_costs']:+.2f})  turnover {row['turnover']:.2f}  names {scored.median():.0f}",
              flush=True)

    table = pd.DataFrame(rows)
    phase2a = _phase2a(Path(args.phase2a))
    _family_statistics(table, returns, phase2a)
    table["holdout_candidate"] = table.apply(_qualifies, axis=1)
    candidates = table.loc[table["holdout_candidate"], "factor"].tolist()
    composite = _composite(candidates, scores_by_trial, panel, mask, start) if len(candidates) >= 2 else None
    pbo = pbo_cscv(pd.DataFrame(returns).dropna(), n_partitions=16)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out / "factors.csv", index=False)
    pd.DataFrame(returns).to_csv(out / "long_short_returns.csv")
    summary = {
        "protocol": "docs/PHASE2B_CROSS_SECTIONAL_PROTOCOL.md",
        "dev_window": [str(start), str(panel.index[-1])],
        "n_trials_cumulative": N_TRIALS,
        "dsr_convention": "B: null sampling variance 1/(T-1); convention A (cross-trial variance) reported",
        "family_pbo": pbo["pbo"],
        "family_pbo_prob_oos_loss": pbo["prob_oos_loss"],
        "holdout_candidates": candidates + (["composite"] if composite else []),
        "composite": composite,
        "taker_7d_reference": phase2a["taker_7d"],
        "inputs": {
            "phase2a_summary_sha256": phase2a["sha256"],
            "metrics_manifest_sha256": _sha256(Path(args.metrics) / "manifest.json"),
        },
        "factors": table.drop(columns=["description"]).to_dict(orient="records"),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=_json_default) + "\n", encoding="utf-8")
    print(f"family PBO {pbo['pbo']:.2f}; holdout candidates: {summary['holdout_candidates'] or 'none'}")
    if candidates:
        _write_preregistration(Path(args.preregistration), candidates, composite, _sha256(out / "summary.json"))


def _write_preregistration(path: Path, candidates: list[str], composite: dict | None, summary_sha: str) -> None:
    """The holdout pre-registration, derived mechanically from the candidate rule's output; never overwritten."""
    if path.exists():
        print(f"{path} already exists; left unchanged")
        return
    entries = [
        {"name": name, "definition": TRIALS[name].description, "book": TRIALS[name].weights.__name__}
        for name in candidates
    ]
    if composite:
        entries.append({"name": "composite", "members": composite["members"], "book": "quantile_weights",
                        "definition": "equal-weight average of the members' cross-sectional rank scores"})
    payload = {
        "id": "phase2b_holdout_v1",
        "protocol": "docs/PHASE2B_CROSS_SECTIONAL_PROTOCOL.md",
        "created": datetime.now(timezone.utc).date().isoformat(),
        "hypothesis": "Each candidate's book has a positive mean daily net return at 1x costs over the holdout.",
        "candidates": entries,
        "holdout": [str(HOLDOUT_START.date()), str((HOLDOUT_END - pd.Timedelta(days=1)).date())],
        "decision_rule": "A candidate passes if its mean daily net return over the holdout days is above zero at 1x "
                         "costs. Passing candidates move to forward paper observation under their own pre-registration "
                         "with the same betting test; failing candidates are retired.",
        "development_summary_sha256": summary_sha,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {path}: commit and push it before running --open-holdout")


def open_holdout_step(path: Path, args: argparse.Namespace) -> None:
    """Open the holdout once with a committed pre-registration and apply the sign check to each candidate."""
    prereg = load_preregistration(path)
    where = path.resolve().parent
    git = {"cwd": where, "capture_output": True, "text": True}
    status = subprocess.run(["git", "status", "--porcelain", "--", path.name], **git)
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", "--", path.name], **git)
    if status.stdout.strip() or tracked.returncode != 0:
        raise SystemExit(f"{path} must be committed, unchanged, before the holdout is opened")
    members = {name for entry in prereg["candidates"] for name in entry.get("members", [entry["name"]])}
    needs_metrics = any(TRIALS[name].start is not None for name in members)
    if needs_metrics:
        _require_holdout_metrics(Path(args.data), Path(args.metrics))
    trial_ledger.configure_default(ROOT, context={"entry_point": "xs_phase2b_holdout", "protocol": "phase2b_v1"})
    panel = load_panel(args.data, preregistration=path)  # the guard records the opening and stops at HOLDOUT_END
    mask, excluded = holdout_universe(panel)
    if needs_metrics:
        panel = load_metrics(args.metrics, panel)

    results = {}
    for entry in prereg["candidates"]:
        name = entry["name"]
        if name == "composite":
            ranks = [TRIALS[m].compute(panel).where(mask).rank(axis=1, pct=True) for m in entry["members"]]
            scores, weights = sum(ranks) / len(ranks), quantile_weights
        else:
            scores, weights = TRIALS[name].compute(panel), TRIALS[name].weights
        book = evaluate_book(held_weights(weights(scores, mask), panel), panel, COSTS, HOLDOUT_START)
        returns = book["returns"]
        ic = cross_sectional_ic(scores, forward_returns(panel), mask).loc[HOLDOUT_START:].dropna()
        passed = bool(returns.mean() > 0.0)
        results[name] = {
            "days": int(len(returns)),
            "mean_daily_net": float(returns.mean()),
            "cumulative_net": float((1.0 + returns).prod() - 1.0),
            "sharpe": book["sharpe"],
            "turnover": book["turnover"],
            "ic_mean": float(ic.mean()) if len(ic) else None,
            "passed": passed,
        }
        trial_ledger.record(
            source="phase2b_holdout",
            candidate=entry,
            window={"start": str(HOLDOUT_START), "end": str(panel.index[-1])},
            metrics=results[name],
            passed=passed,
            holdout_access=True,
        )
        print(f"  {name:22s} {len(returns)} days  mean {returns.mean() * 1e4:+.1f} bps/day  "
              f"cumulative {results[name]['cumulative_net']:+.2%}  {'PASS' if passed else 'fail'}", flush=True)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    report = {
        "preregistration": prereg["path"],
        "sha256": prereg["sha256"],
        "holdout_days": [str(day.date()) for day in panel.index[panel.index >= HOLDOUT_START][[0, -1]]],
        "excluded_new_listings": {s: why for s, why in sorted(excluded.items()) if why != "non_crypto_list"},
        "results": results,
    }
    (out / "holdout.json").write_text(json.dumps(report, indent=2, default=_json_default) + "\n", encoding="utf-8")


def holdout_universe(panel: Panel) -> tuple[pd.DataFrame, dict[str, str]]:
    """The top-50 universe through the holdout, with every contract classified as the forward observation classifies it.

    NON_CRYPTO was checked with the weekend test on contracts that entered the development universe. Every other
    contract gets the forward registration's new-listing rule: an unreviewed contract first listed on or after
    2025-09-01 needs a weekend ratio of at least 0.45 over its first 60 bars, which are complete on the day it becomes
    eligible. Development-window days are unchanged. Returns the mask and {symbol: exclusion rule}.
    """
    rules = json.loads(FORWARD_REGISTRATION.read_text(encoding="utf-8"))["universe"]
    history = int(rules["min_history_bars"])
    close = panel["close"]
    bars = close.notna().cumsum()
    seasoned = bars.iloc[-1] >= history
    listings = ForwardPanel(
        panel=panel,
        first_bar=panel.first_bar.dropna(),
        sixtieth_bar=bars.ge(history).idxmax().where(seasoned),
        weekend_ratio=pd.Series({s: weekend_ratio(close[s].dropna().iloc[:history]) for s in close.columns[seasoned]},
                                dtype=float),
    )
    excluded = excluded_contracts(
        listings,
        reviewed=set(rules["reviewed_symbols"]),
        name_exclusions=json.loads(FORWARD_EXCLUSIONS.read_text(encoding="utf-8"))["entries"],
        weekend_min=float(rules["new_listing_rule"]["weekend_ratio_min"]),
        new_listing_cutoff=NEW_LISTING_CUTOFF,
    )
    mask = liquid_universe(panel, top_n=UNIVERSE_SIZE, min_history=history,
                           excluded=frozenset(base_asset(symbol) for symbol in excluded))
    return mask, excluded


def _require_holdout_metrics(data: Path, root: Path) -> None:
    """Open-interest candidates need holdout metrics for every crypto contract trading in the holdout.

    The contracts come from bar timestamps alone, so this runs before the holdout is opened. Writes the spans to fetch
    and stops if any are missing.
    """
    first = str((HOLDOUT_START - pd.Timedelta(days=METRICS_PAD_DAYS)).date())
    last = str((HOLDOUT_END - pd.Timedelta(days=1)).date())
    spans = {}
    for path in sorted((data / "klines_1d").glob("*.csv")):
        stamps = pd.to_datetime(pd.read_csv(path, usecols=["timestamp"])["timestamp"], utc=True, format="mixed")
        if base_asset(path.stem) not in NON_CRYPTO and ((stamps >= HOLDOUT_START) & (stamps < HOLDOUT_END)).any():
            spans[path.stem] = [first, last]
    entries = json.loads((root / "manifest.json").read_text(encoding="utf-8")).get("symbols", {})
    if any(entries.get(s, {}).get("span") != span or entries[s].get("failed_days") for s, span in spans.items()):
        (root / "holdout_spans.json").write_text(json.dumps(spans, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        raise SystemExit(f"fetch holdout metrics first: RandysLab scripts/fetch_metrics.py --spans "
                         f"{root / 'holdout_spans.json'} --out {root}; then rerun --open-holdout")


def metrics_spans(mask: pd.DataFrame) -> dict[str, list[str]]:
    spans = {}
    for symbol in mask.columns[mask.any()]:
        days = mask.index[mask[symbol]]
        first = max(days[0] - pd.Timedelta(days=METRICS_PAD_DAYS), METRICS_FIRST_DAY)
        if days[-1] >= METRICS_FIRST_DAY:
            spans[symbol] = [str(first.date()), str(days[-1].date())]
    return spans


def _require_complete_metrics(root: Path, spans: dict[str, list[str]]) -> None:
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    entries = manifest.get("symbols", {})
    missing = [s for s in spans if s not in entries or "error" in entries[s]]
    failed = sum(len(entries[s].get("failed_days", [])) for s in spans if s in entries)
    if missing or failed:
        raise SystemExit(f"metrics download incomplete: {len(missing)} contracts missing, {failed} failed days; "
                         f"rerun RandysLab scripts/fetch_metrics.py first")


def _phase2a(root: Path) -> dict:
    """Phase 2a IC t-stats and daily Sharpe ratios (counted in the cumulative family) and the taker_7d reference row."""
    raw = (root / "summary.json").read_bytes()
    summary = json.loads(raw)
    returns = pd.read_csv(root / "long_short_returns.csv", index_col=0, parse_dates=True)
    factors = {row["factor"]: row for row in summary["factors"]}
    keep = ("ic_mean", "ic_tstat", "sharpe", "sharpe_2x_costs", "turnover", "max_dd", "dsr_n11")
    return {
        "ic_tstats": [factors[name]["ic_tstat"] for name in returns.columns],
        "daily_sharpes": [sharpe_ratio(returns[name].dropna()) for name in returns.columns],
        "taker_7d": {key: factors["taker_7d"][key] for key in keep},
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _family_statistics(table: pd.DataFrame, returns: dict[str, pd.Series], phase2a: dict) -> None:
    """Benjamini-Hochberg over all 18 IC p-values, and Deflated Sharpe with N = 18 under conventions B and A."""
    pvalues = np.array([_two_sided_p(t) for t in [*phase2a["ic_tstats"], *table["ic_tstat"]]])
    discoveries, adjusted = benjamini_hochberg(pvalues, q=0.05)
    own = slice(len(phase2a["ic_tstats"]), None)
    table["ic_pvalue"] = pvalues[own]
    table["bh_discovery_q05_n18"] = discoveries[own]
    table["bh_adjusted_p_n18"] = adjusted[own]
    sharpes = [*phase2a["daily_sharpes"], *(sharpe_ratio(returns[name].dropna()) for name in table["factor"])]
    cross_trial = float(np.var(sharpes, ddof=1))
    table["dsr_b_n18"] = [
        deflated_sharpe_ratio(returns[name].dropna(), N_TRIALS, 1.0 / (len(returns[name].dropna()) - 1))["dsr"]
        for name in table["factor"]
    ]
    table["dsr_a_n18"] = [deflated_sharpe_ratio(returns[name].dropna(), N_TRIALS, cross_trial)["dsr"]
                          for name in table["factor"]]


def _qualifies(row: pd.Series) -> bool:
    years, needed = YEARS["open_interest" if row["window_start"] >= "2022-01-01" else "default"]
    positive = sum(1 for year in years if _positive(row.get(f"ic_year_{year}")))
    return bool(
        row["ic_tstat"] >= 3.0
        and row["bh_discovery_q05_n18"]
        and row["sharpe"] >= 0.5
        and row["sharpe_2x_costs"] >= 0.0
        and positive >= needed
        and row["dsr_b_n18"] >= 0.95
    )


def _composite(names, scores_by_trial, panel, mask, start) -> dict:
    """Equal-weight average of the qualifying trials' cross-sectional rank scores, quintile long-short."""
    ranks = [scores_by_trial[name].where(mask).rank(axis=1, pct=True) for name in names]
    scores = sum(ranks) / len(ranks)
    window = max([start, *(pd.Timestamp(TRIALS[name].start or start) for name in names)])
    result = evaluate_factor(scores, panel, mask, COSTS, window, quantile_weights)
    result.pop("returns")
    trial_ledger.record(
        source="qr_xs_factor",
        candidate={"factor": "composite", "members": names, "book": "quantile_weights", "universe": "top50"},
        window={"start": str(window), "end": str(panel.index[-1])},
        metrics={key: result[key] for key in ("ic_mean", "ic_tstat", "sharpe", "sharpe_2x_costs", "max_dd")},
    )
    return {"members": names, "window_start": str(window.date()), **_flatten(result)}


def _flatten(result: dict) -> dict:
    flat = {key: value for key, value in result.items() if key != "ic_by_year"}
    flat.update({f"ic_year_{year}": value for year, value in result.get("ic_by_year", {}).items()})
    return flat


def _positive(value) -> bool:
    return value is not None and not (isinstance(value, float) and math.isnan(value)) and value > 0


def _two_sided_p(tstat: float) -> float:
    return float(2.0 * (1.0 - NormalDist().cdf(abs(tstat)))) if math.isfinite(tstat) else 1.0


def _sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def _json_default(value):
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return str(value)


if __name__ == "__main__":
    main()
