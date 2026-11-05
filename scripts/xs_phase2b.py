"""Phase 2b: evaluate the refined cross-sectional family (docs/PHASE2B_CROSS_SECTIONAL_PROTOCOL.md).

Step 1, ``--metrics-spans PATH``: write the days of Binance metrics to download for each contract that enters the
Phase 2a development universe, from 30 days before its first universe day (not before 2021-12-01, when metrics
coverage begins for most contracts) to its last universe day. Feed the file to
``../RandysLab-STRICT4H/scripts/fetch_metrics.py --spans``.

Step 2 (default): evaluate the 7 trials on the main and robustness universes, apply the cumulative family statistics
(N = 18 with Phase 2a's 11 trials) and the holdout-candidate rule with Deflated Sharpe convention B, and write
reports/phase2b/. Refuses to run while the metrics download is incomplete. Holdout bars stay sealed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from randyslab import trial_ledger
from randyslab.accounting import CostRates
from randyslab.stats import benjamini_hochberg, deflated_sharpe_ratio, pbo_cscv, sharpe_ratio

from quantumrandy.xsection.evaluate import evaluate_factor, quantile_weights
from quantumrandy.xsection.family_2b import TRIALS
from quantumrandy.xsection.panel import load_metrics, load_panel
from quantumrandy.xsection.universe import liquid_universe

DATA = ROOT.parent / "RandysLab-STRICT4H" / "data"
COSTS = CostRates(fee_bps=4.0, slippage_bps=5.0)
UNIVERSE_SIZE = 50
ROBUSTNESS_CUTOFF = "2025-09-01"
METRICS_FIRST_DAY = pd.Timestamp("2021-12-01", tz="UTC")
METRICS_PAD_DAYS = 30
N_TRIALS = 18  # Phase 2a's 11 plus these 7
YEARS = {"default": ((2021, 2022, 2023, 2024, 2025), 4), "open_interest": ((2022, 2023, 2024, 2025), 3)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", default=str(DATA / "universe_1d_20261105"))
    ap.add_argument("--metrics", default=str(DATA / "metrics_1d_20261105"))
    ap.add_argument("--phase2a", default=str(ROOT / "reports" / "phase2a"))
    ap.add_argument("--out", default=str(ROOT / "reports" / "phase2b"))
    ap.add_argument("--metrics-spans", help="Only write {symbol: [first_day, last_day]} here and stop")
    args = ap.parse_args()

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
