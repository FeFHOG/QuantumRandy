"""Phase 2a: evaluate the pre-committed cross-sectional factor family (docs/PHASE2A_CROSS_SECTIONAL_PROTOCOL.md).

Step 1, ``--review-universe``: list recently listed contracts that ever enter the universe, so the non-crypto exclusion
list can be finalized before any factor is evaluated. Step 2 (default): evaluate the 11 factors on the main and the
pre-2025-09 robustness universes, apply the family statistics and the holdout-candidate rule, and write
reports/phase2a/. Holdout bars stay sealed.
"""

from __future__ import annotations

import argparse
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

from quantumrandy.xsection.evaluate import evaluate_book, evaluate_factor, held_weights
from quantumrandy.xsection.factors import FACTORS
from quantumrandy.xsection.panel import load_panel
from quantumrandy.xsection.universe import liquid_universe

COSTS = CostRates(fee_bps=4.0, slippage_bps=5.0)
UNIVERSE_SIZE = 50
ROBUSTNESS_CUTOFF = "2025-09-01"
FULL_DEV_YEARS = (2021, 2022, 2023, 2024, 2025)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", default=str(ROOT.parent / "RandysLab-STRICT4H" / "data" / "universe_1d_20261105"))
    ap.add_argument("--out", default=str(ROOT / "reports" / "phase2a"))
    ap.add_argument("--review-universe", action="store_true")
    args = ap.parse_args()

    panel = load_panel(args.data)
    main_mask = liquid_universe(panel, top_n=UNIVERSE_SIZE)
    start = main_mask.index[main_mask.sum(axis=1).ge(UNIVERSE_SIZE).argmax()]
    span = f"{panel.index[0].date()} .. {panel.index[-1].date()}"
    print(f"{len(panel.symbols)} symbols, {span}; dev start {start.date()}")

    if args.review_universe:
        _review(panel, main_mask)
        return

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    trial_ledger.configure_default(ROOT, context={"entry_point": "xs_phase2a", "protocol": "phase2a_v1"})
    robust_mask = liquid_universe(panel, top_n=UNIVERSE_SIZE, listed_before=ROBUSTNESS_CUTOFF)

    rows, returns = [], {}
    for name, factor in FACTORS.items():
        scores = factor.compute(panel)
        result = evaluate_factor(scores, panel, main_mask, COSTS, start)
        robust = evaluate_factor(scores, panel, robust_mask, COSTS, start)
        returns[name] = result.pop("returns")
        robust.pop("returns")
        row = {"factor": name, "description": factor.description, **_flatten(result)}
        row.update({f"robust_{key}": value for key, value in _flatten(robust).items() if key != "ic_by_year"})
        rows.append(row)
        trial_ledger.record(
            source="qr_xs_factor",
            candidate={"factor": name, "definition": factor.description, "universe": f"top{UNIVERSE_SIZE}"},
            window={"start": str(start), "end": str(panel.index[-1])},
            metrics={key: row[key] for key in ("ic_mean", "ic_tstat", "sharpe", "sharpe_2x_costs", "max_dd")},
        )
        print(f"  {name:11s} IC {row['ic_mean']:+.4f} (t {row['ic_tstat']:+.2f})  Sharpe {row['sharpe']:+.2f} "
              f"(2x {row['sharpe_2x_costs']:+.2f})  robust IC t {row['robust_ic_tstat']:+.2f}", flush=True)

    table = pd.DataFrame(rows)
    _family_statistics(table, returns)
    table["holdout_candidate"] = table.apply(_qualifies, axis=1)
    benchmarks = _benchmarks(panel, main_mask, start)
    pbo = pbo_cscv(pd.DataFrame(returns).dropna(), n_partitions=16)

    table.to_csv(out / "factors.csv", index=False)
    pd.DataFrame(returns).to_csv(out / "long_short_returns.csv")
    summary = {
        "protocol": "docs/PHASE2A_CROSS_SECTIONAL_PROTOCOL.md",
        "dev_window": [str(start), str(panel.index[-1])],
        "universe_size": UNIVERSE_SIZE,
        "costs_bps": {"fee": COSTS.fee_bps, "slippage": COSTS.slippage_bps},
        "family_pbo": pbo["pbo"],
        "family_pbo_prob_oos_loss": pbo["prob_oos_loss"],
        "holdout_candidates": table.loc[table["holdout_candidate"], "factor"].tolist(),
        "benchmarks": benchmarks,
        "factors": table.drop(columns=["description"]).to_dict(orient="records"),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=_json_default) + "\n", encoding="utf-8")
    print(f"family PBO {pbo['pbo']:.2f}; holdout candidates: {summary['holdout_candidates'] or 'none'}")
    print(f"benchmarks: {json.dumps(benchmarks, default=_json_default)}")


def _review(panel, mask: pd.DataFrame) -> None:
    ever = mask.any()
    recent = [s for s in ever[ever].index if panel.first_bar[s] >= pd.Timestamp(ROBUSTNESS_CUTOFF, tz="UTC")]
    print(f"{int(ever.sum())} contracts ever in the universe; listed since {ROBUSTNESS_CUTOFF}: {len(recent)}")
    for symbol in sorted(recent, key=lambda s: panel.first_bar[s]):
        days = int(mask[symbol].sum())
        print(f"  {symbol:20s} first bar {panel.first_bar[symbol].date()}  days in universe {days}")


def _family_statistics(table: pd.DataFrame, returns: dict[str, pd.Series]) -> None:
    pvalues = np.array([_two_sided_p(t) for t in table["ic_tstat"]])
    discoveries, adjusted = benjamini_hochberg(pvalues, q=0.05)
    table["ic_pvalue"] = pvalues
    table["bh_discovery_q05"] = discoveries
    table["bh_adjusted_p"] = adjusted
    variance = float(np.var([sharpe_ratio(series) for series in returns.values()], ddof=1))
    table["dsr_n11"] = [deflated_sharpe_ratio(returns[name], len(returns), variance)["dsr"] for name in table["factor"]]


def _qualifies(row: pd.Series) -> bool:
    years = [row.get(f"ic_year_{year}") for year in FULL_DEV_YEARS]
    positive_years = sum(1 for value in years if value is not None and not math.isnan(value) and value > 0)
    return bool(
        row["ic_tstat"] >= 3.0
        and row["bh_discovery_q05"]
        and row["sharpe"] >= 0.5
        and row["sharpe_2x_costs"] >= 0.0
        and positive_years >= 4
        and row["dsr_n11"] >= 0.95
    )


def _benchmarks(panel, mask: pd.DataFrame, start: pd.Timestamp) -> dict:
    members = mask.sum(axis=1).replace(0, np.nan)
    equal_weight = held_weights(mask.astype(float).div(members, axis=0).fillna(0.0), panel)
    btc = pd.DataFrame(0.0, index=panel.index, columns=panel.symbols)
    btc["BTCUSDT"] = 1.0
    out = {}
    for name, weights in (("equal_weight_universe_long", equal_weight), ("btc_buy_and_hold", held_weights(btc, panel))):
        result = evaluate_book(weights, panel, COSTS, start)
        out[name] = {key: result[key] for key in ("sharpe", "sharpe_ex_regimes", "cagr", "max_dd", "turnover")}
    return out


def _flatten(result: dict) -> dict:
    flat = {key: value for key, value in result.items() if key != "ic_by_year"}
    flat.update({f"ic_year_{year}": value for year, value in result.get("ic_by_year", {}).items()})
    return flat


def _two_sided_p(tstat: float) -> float:
    return float(2.0 * (1.0 - NormalDist().cdf(abs(tstat)))) if math.isfinite(tstat) else 1.0


def _json_default(value):
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return str(value)


if __name__ == "__main__":
    main()
