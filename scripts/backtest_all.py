from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from quantumrandy.backtest import run_formula_backtest, summarize_ledger
from quantumrandy.config import load_config
from quantumrandy.data import load_market_frame, slice_window
from quantumrandy.dashboard import _load_blind_data, _run_blind_validate
from quantumrandy.io_utils import safe_write_csv, safe_write_json


def main() -> None:
    ap = argparse.ArgumentParser(description="One-click backtest all factors from a leaderboard")
    ap.add_argument("--leaderboard", required=True, help="Path to leaderboard.json")
    ap.add_argument("--config", default="configs/btcusdt.yaml", help="Path to config yaml")
    ap.add_argument("--out", default="reports/backtest_all", help="Output directory")
    ap.add_argument("--blind", action="store_true", help="Also run 2026 blind backtest (slower)")
    args = ap.parse_args()

    lb_path = Path(args.leaderboard)
    if not lb_path.exists():
        raise SystemExit(f"Leaderboard not found: {lb_path}")

    leaderboard = json.loads(lb_path.read_text(encoding="utf-8"))
    print(f"Loaded {len(leaderboard)} factors from {lb_path}")

    cfg = load_config(args.config)
    data = load_market_frame(cfg.ohlcv_csv, cfg.funding_csv)
    train_data = slice_window(data, cfg.windows.training_start, cfg.windows.training_end)
    val_data = slice_window(data, cfg.windows.validation_start, cfg.windows.validation_end)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    rows = []
    for i, entry in enumerate(leaderboard):
        formula = entry["formula"]
        passed = entry.get("passed", None)
        kill_reasons = entry.get("kill_reasons", [])
        if not kill_reasons and passed is False:
            kill_reasons = _derive_kill_reasons(entry)
        print(f"[{i + 1}/{len(leaderboard)}] {formula[:70]}...", end=" ", flush=True)

        try:
            train_ledger = run_formula_backtest(train_data, formula, cfg.costs, cfg.execution)
            train_metrics = summarize_ledger(train_ledger, cfg.bar_hours)

            val_ledger = run_formula_backtest(val_data, formula, cfg.costs, cfg.execution)
            val_metrics = summarize_ledger(val_ledger, cfg.bar_hours)

            row = {
                "formula": formula,
                "description": entry.get("description", ""),
                "depth": entry.get("depth", entry.get("operators", 0)),
                "operators": entry.get("operators", 0),
                "passed": passed,
                "kill_reasons": kill_reasons,
                "mcts_score": entry.get("mcts_score", 0),
                "brutal_score": entry.get("brutal_score", 0),
                "train_sharpe": round(train_metrics["sharpe"], 4),
                "train_cagr": round(train_metrics["cagr"], 4),
                "train_max_dd": round(train_metrics["max_dd"], 4),
                "train_rank_ic": round(train_metrics["rank_ic"], 6),
                "train_ic": round(train_metrics["ic"], 6),
                "train_win_rate": round(train_metrics["directional_win_rate"], 4),
                "train_turnover": round(train_metrics["turnover"], 4),
                "val_sharpe": round(val_metrics["sharpe"], 4),
                "val_cagr": round(val_metrics["cagr"], 4),
                "val_max_dd": round(val_metrics["max_dd"], 4),
                "val_rank_ic": round(val_metrics["rank_ic"], 6),
                "val_ic": round(val_metrics["ic"], 6),
                "val_win_rate": round(val_metrics["directional_win_rate"], 4),
            }
            status = "PASS" if passed else "KILL"
            print(f"{status} train_sharpe={row['train_sharpe']:.2f} val_sharpe={row['val_sharpe']:.2f}")
        except Exception as exc:
            print(f"ERROR: {exc}")
            row = {
                "formula": formula,
                "description": entry.get("description", ""),
                "passed": passed,
                "kill_reasons": kill_reasons,
                "error": str(exc),
            }
        rows.append(row)

    df = pd.DataFrame(rows)
    safe_write_csv(out / "all_factors_backtest.csv", df, out / "events.jsonl")

    if args.blind:
        print(f"\nRunning 2026 blind backtests...")
        blind_data, blind_bar_hours, blind_costs, blind_exec = _load_blind_data()
        for i, row in enumerate(rows):
            if row.get("error"):
                continue
            formula = row["formula"]
            print(f"[blind {i + 1}/{len(rows)}] {formula[:70]}...", end=" ", flush=True)
            try:
                blind_ledger = run_formula_backtest(blind_data, formula, blind_costs, blind_exec)
                blind_metrics = summarize_ledger(blind_ledger, blind_bar_hours)
                row["blind_sharpe"] = round(blind_metrics["sharpe"], 4)
                row["blind_cagr"] = round(blind_metrics["cagr"], 4)
                row["blind_max_dd"] = round(blind_metrics["max_dd"], 4)
                row["blind_rank_ic"] = round(blind_metrics["rank_ic"], 6)
                row["blind_ic"] = round(blind_metrics["ic"], 6)
                row["blind_win_rate"] = round(blind_metrics["directional_win_rate"], 4)
                row["blind_turnover"] = round(blind_metrics["turnover"], 4)
                print(f"blind_sharpe={row['blind_sharpe']:.2f}")
            except Exception as exc:
                row["blind_error"] = str(exc)
                print(f"ERROR: {exc}")
        df = pd.DataFrame(rows)
        safe_write_csv(out / "all_factors_backtest.csv", df, out / "events.jsonl")

    safe_write_json(out / "all_factors_backtest.json", rows, out / "events.jsonl")

    passed_count = sum(1 for r in rows if r.get("passed"))
    killed_count = len(rows) - passed_count
    print(f"\nDone. {len(rows)} factors: {passed_count} PASS, {killed_count} KILL")
    print(f"Output: {out.resolve()}")


def _derive_kill_reasons(entry: dict) -> list[str]:
    gate_keys = {
        "gate_predictive_power": "predictive_power",
        "gate_homogeneity": "homogeneity",
        "gate_friction_audit": "friction_audit",
        "gate_lifetime": "lifetime",
    }
    return [label for key, label in gate_keys.items() if entry.get(key) is False]


if __name__ == "__main__":
    main()
