"""Forward paper observation of the registered taker-flow books (docs/PHASE2A_TAKER_FORWARD_PREREGISTRATION.md for
taker_7d, docs/PHASE2B_TAKER_30D_FORWARD_PREREGISTRATION.md for taker_30d).

For every preregistrations/*_forward.json (or the --registration given), rebuilds the daily record from the first P&L
day on every run, applies the betting test to final days, and writes reports/forward_<factor>/: record.csv (one row per
observed day), next_book.csv (positions for the day after the latest close), summary.json and STATUS.md. Run
../RandysLab-STRICT4H/scripts/fetch_daily.py first.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from randyslab import metrics as strict_metrics
from randyslab import trial_ledger

from quantumrandy.xsection.forward import (
    Registration,
    discover_registrations,
    excluded_contracts,
    forward_record,
    funding_final_through,
    load_forward_panel,
)
from quantumrandy.xsection.sequential import decision, eprocesses
from quantumrandy.xsection.universe import base_asset, liquid_universe

DATA = ROOT.parent / "RandysLab-STRICT4H" / "data"
BASE_LAST_MONTH = "2026-10"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--registration", action="append", help="a forward registration (repeatable); default: all of them")
    ap.add_argument("--exclusions", default=str(ROOT / "preregistrations" / "forward_exclusions.json"))
    ap.add_argument("--base", default=str(DATA / "universe_1d_20261105"))
    ap.add_argument("--daily", default=str(DATA / "forward_1d"))
    ap.add_argument("--out", help="report directory for a single registration (default: reports/forward_<factor>)")
    args = ap.parse_args()

    paths = [Path(path) for path in args.registration or []] or discover_registrations(ROOT / "preregistrations")
    if not paths:
        ap.error("no forward registrations found")
    if args.out and len(paths) > 1:
        ap.error("--out needs exactly one --registration")
    for path in paths:
        observe(path, args)


def observe(path: Path, args: argparse.Namespace) -> None:
    reg = Registration.load(path)
    spec, rules = reg.betting, reg.spec["universe"]
    daily_manifest = json.loads((Path(args.daily) / "manifest.json").read_text(encoding="utf-8"))
    data = load_forward_panel(args.base, args.daily, reg.start)
    excluded = excluded_contracts(
        data,
        reviewed=set(rules["reviewed_symbols"]),
        name_exclusions=json.loads(Path(args.exclusions).read_text(encoding="utf-8"))["entries"],
        weekend_min=float(rules["new_listing_rule"]["weekend_ratio_min"]),
        new_listing_cutoff=pd.Timestamp("2025-09-01", tz="UTC"),
    )
    mask = liquid_universe(
        data.panel,
        top_n=int(rules["top_n"]),
        lookback=int(rules["volume_lookback_days"]),
        min_history=int(rules["min_history_bars"]),
        excluded=frozenset(base_asset(symbol) for symbol in excluded),
    )
    final_through = funding_final_through(BASE_LAST_MONTH, daily_manifest.get("funding_months", []))
    record, target, scores = forward_record(
        data.panel, mask, reg.start, reg.costs, final_through, factor=reg.factor
    )

    final = eprocesses(record.loc[record["final"], "r_net"], spec)
    preview = eprocesses(record["r_net"], spec)
    verdict = decision(final, spec)
    latest_close = data.panel.index[-1]
    book = _next_book(target, scores, latest_close, reg.factor)

    out = Path(args.out) if args.out else ROOT / "reports" / f"forward_{reg.factor}"
    out.mkdir(parents=True, exist_ok=True)
    record.join(preview[["stake", "e_edge", "e_futility"]].add_prefix("preview_")).join(
        final[["stake", "e_edge", "e_futility", "bound_ok"]]
    ).to_csv(out / "record.csv")
    book.to_csv(out / "next_book.csv")
    summary = {
        "registration": {"id": reg.spec["id"], "sha256": reg.sha256, "first_pnl_day": str(reg.start.date())},
        "latest_close": str(latest_close.date()),
        "funding_final_through": str(final_through),
        "days_observed": int(len(record)),
        "days_final": int(record["final"].sum()),
        "decision": verdict,
        "preview": {
            "e_edge": float(preview["e_edge"].iloc[-1]) if len(preview) else 1.0,
            "e_futility": float(preview["e_futility"].iloc[-1]) if len(preview) else 1.0,
        },
        "final_stats": _stats(record.loc[record["final"]]),
        "all_days_stats": _stats(record),
        "flags": {
            "drawdown_beyond_backtest": _stats(record).get("max_dd", 0.0) > reg.drawdown_flag,
            "bound_violation": not verdict["bound_ok"],
            "days_with_missing_bars": int((record["missing_bars"] > 0).sum()),
        },
        "universe": {
            "members_latest_close": int(mask.loc[latest_close].sum()),
            "excluded_by_rule": pd.Series(excluded).value_counts().to_dict(),
            "excluded_new_listings": sorted(s for s, why in excluded.items() if why != "non_crypto_list"),
        },
        "daily_archive_latest_day": daily_manifest.get("latest_day"),
        "funding_months_published": daily_manifest.get("funding_months", []),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=_json_default) + "\n", encoding="utf-8")
    (out / "STATUS.md").write_text(_status(summary, book, reg), encoding="utf-8")
    _record_trial(reg, summary)
    print(_status(summary, book, reg))


def _next_book(target: pd.DataFrame, scores: pd.DataFrame, close: pd.Timestamp, factor: str) -> pd.DataFrame:
    weights = target.loc[close]
    held = weights[weights != 0.0]
    return pd.DataFrame(
        {"weight": held, f"{factor}_score": scores.loc[close, held.index]}
    ).sort_values("weight", ascending=False).rename_axis("symbol")


def _stats(record: pd.DataFrame) -> dict:
    returns = record["r_net"] if len(record) else pd.Series(dtype=float)
    if len(returns) < 2:
        return {"days": int(len(returns))}
    return {
        "days": int(len(returns)),
        "cumulative_net": float((1.0 + returns).prod() - 1.0),
        "mean_daily": float(returns.mean()),
        "sharpe_no_rf": float(returns.mean() / returns.std() * math.sqrt(365.0)) if returns.std() > 0 else None,
        "max_dd": float(strict_metrics.max_drawdown(returns)),
        "turnover_daily": float(record["turnover"].mean()),
        "funding_annual": float(-record["c_fund"].mean() * 365.0),
    }


def _status(summary: dict, book: pd.DataFrame, reg: Registration) -> str:
    d, s = summary["decision"], summary["all_days_stats"]
    lines = [
        f"# {reg.factor} forward observation ({summary['latest_close']} close)",
        "",
        f"Registration `{reg.spec['id']}` sha256 `{reg.sha256[:12]}`; "
        f"first P&L day {summary['registration']['first_pnl_day']}.",
        "",
        f"- Verdict: **{d['verdict']}** (final days {summary['days_final']} of {summary['days_observed']} observed; "
        f"funding final through {summary['funding_final_through'][:10]})",
        f"- e_edge {d['e_edge']:.3g} / e_futility {d['e_futility']:.3g} on final days "
        f"(threshold {reg.betting.threshold:g}); "
        f"preview with all days {summary['preview']['e_edge']:.3g} / {summary['preview']['e_futility']:.3g}",
    ]
    if s.get("days", 0) >= 2:
        lines.append(
            f"- All days: cumulative net {s['cumulative_net']:+.2%}, mean {s['mean_daily'] * 1e4:+.1f} bps/day, "
            f"max drawdown {s['max_dd']:.1%}, turnover {s['turnover_daily']:.2f}/day"
        )
    flags = [name for name, value in summary["flags"].items() if value]
    lines += [
        f"- Flags: {', '.join(flags) or 'none'}",
        f"- Universe at the latest close: {summary['universe']['members_latest_close']} contracts",
        "",
        f"Book for the day after {summary['latest_close']}: {int((book['weight'] > 0).sum())} long, "
        f"{int((book['weight'] < 0).sum())} short",
        "",
    ]
    if pd.Timestamp(summary["latest_close"], tz="UTC") < pd.Timestamp(summary["registration"]["first_pnl_day"],
                                                                          tz="UTC") - pd.Timedelta(days=1):
        lines.insert(2, "Dry run: the latest close precedes the first decision close, so nothing is observed yet.\n")
    return "\n".join(lines) + "\n"


def _record_trial(reg: Registration, summary: dict) -> None:
    """One ledger row whenever the number of final days changes; daily re-runs are not new trials."""
    path = trial_ledger.configure_default(ROOT, context={"entry_point": "xs_forward_taker", "protocol": reg.spec["id"]})
    rows = trial_ledger.load(path) if path.exists() else []
    previous = [row for row in rows if row.get("source") == "forward_observation" and
                row.get("extra_registration_sha256") == reg.sha256]
    if previous and previous[-1].get("metrics", {}).get("days_final") == summary["days_final"]:
        return
    trial_ledger.record(
        source="forward_observation",
        candidate={"factor": reg.factor, "registration": reg.spec["id"]},
        window={"start": summary["registration"]["first_pnl_day"], "end": summary["latest_close"]},
        metrics={"days_final": summary["days_final"], "e_edge": summary["decision"]["e_edge"],
                 "e_futility": summary["decision"]["e_futility"]},
        passed={"edge_confirmed": True, "retire": False}.get(summary["decision"]["verdict"]),
        extra={"extra_registration_sha256": reg.sha256},
    )


def _json_default(value):
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return str(value)


if __name__ == "__main__":
    main()
