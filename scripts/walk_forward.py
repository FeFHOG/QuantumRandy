from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantumrandy.config import load_config
from quantumrandy.data import load_market_frame
from quantumrandy.io_utils import safe_write_csv, safe_write_json, safe_write_text
from quantumrandy.walk_forward import build_walk_forward_windows, load_formula_entries, run_walk_forward


def main() -> None:
    ap = argparse.ArgumentParser(description="Walk-forward validation for fixed QuantumRandy formulas")
    ap.add_argument("--config", default="configs/btcusdt.yaml", help="Path to config yaml")
    ap.add_argument("--leaderboard", help="Path to leaderboard.json")
    ap.add_argument("--formula", action="append", default=[], help="Formula to validate; can be repeated")
    ap.add_argument("--out", default="reports/walk_forward", help="Output directory")
    ap.add_argument("--top", type=int, help="Use only first N formulas after filtering")
    ap.add_argument("--passed-only", action="store_true", help="Only use leaderboard entries where passed is not false")
    ap.add_argument("--train-months", type=int, default=18)
    ap.add_argument("--validation-months", type=int, default=6)
    ap.add_argument("--test-months", type=int, default=3)
    ap.add_argument("--step-months", type=int, default=3)
    ap.add_argument("--start", help="Optional UTC start date, e.g. 2019-09-08")
    ap.add_argument("--end", help="Optional UTC exclusive end date, e.g. 2025-11-24")
    ap.add_argument("--min-bars", type=int, default=120, help="Minimum bars required per segment")
    args = ap.parse_args()

    cfg = load_config(args.config)
    data = load_market_frame(cfg.ohlcv_csv, cfg.funding_csv)
    entries = load_formula_entries(args.leaderboard, args.formula, passed_only=args.passed_only, top=args.top)
    if not entries:
        entries = [{"formula": formula, "description": "seed formula", "source": "config_seed", "passed": None} for formula in cfg.mcts.seed_formulas]

    windows = build_walk_forward_windows(
        data,
        train_months=args.train_months,
        validation_months=args.validation_months,
        test_months=args.test_months,
        step_months=args.step_months,
        start=args.start or cfg.windows.training_start,
        end=args.end or cfg.windows.validation_end,
        min_bars=args.min_bars,
    )
    if not windows:
        raise SystemExit("No walk-forward windows produced. Try reducing --min-bars or using a wider date range.")

    print(f"Loaded {len(entries)} formulas and built {len(windows)} walk-forward windows")
    details, summary = run_walk_forward(data, entries, cfg, windows)
    summary = summary.sort_values(
        ["survival_rate", "test_sharpe_median", "test_rank_ic_median"],
        ascending=[False, False, False],
    )

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    safe_write_csv(out / "walk_forward_details.csv", details, out / "events.jsonl")
    safe_write_csv(out / "walk_forward_summary.csv", summary, out / "events.jsonl")
    safe_write_json(out / "walk_forward_windows.json", [_window_dict(w) for w in windows], out / "events.jsonl")
    safe_write_json(out / "walk_forward_config.json", _run_config(args, cfg, len(entries), len(windows)), out / "events.jsonl")
    safe_write_text(out / "WALK_FORWARD_REPORT.md", _report(args, cfg, summary, windows), out / "events.jsonl")

    print(f"Output: {out.resolve()}")
    print("Top formulas:")
    for row in summary.head(5).to_dict(orient="records"):
        print(
            f"survival={row['survival_rate']:.2f} "
            f"test_sharpe_median={row['test_sharpe_median']:.2f} "
            f"test_rank_ic_median={row['test_rank_ic_median']:.4f} "
            f"{row['formula']}"
        )


def _window_dict(window) -> dict:
    return {
        "window_id": window.window_id,
        "train_start": window.train_start.isoformat(),
        "train_end": window.train_end.isoformat(),
        "validation_start": window.validation_start.isoformat(),
        "validation_end": window.validation_end.isoformat(),
        "test_start": window.test_start.isoformat(),
        "test_end": window.test_end.isoformat(),
    }


def _run_config(args: argparse.Namespace, cfg, formula_count: int, window_count: int) -> dict:
    return {
        "symbol": cfg.symbol,
        "bar_hours": cfg.bar_hours,
        "ohlcv_csv": str(cfg.ohlcv_csv),
        "funding_csv": str(cfg.funding_csv),
        "leaderboard": args.leaderboard,
        "formula_count": formula_count,
        "window_count": window_count,
        "train_months": args.train_months,
        "validation_months": args.validation_months,
        "test_months": args.test_months,
        "step_months": args.step_months,
        "min_bars": args.min_bars,
        "pass_rule": {
            "rank_ic_gte": cfg.filter.min_rank_ic,
            "directional_win_rate_gte": cfg.filter.min_directional_win_rate,
            "sharpe_gte": cfg.filter.min_validation_sharpe,
            "survived_window": "validation_pass_basic AND test_pass_basic",
        },
    }


def _report(args: argparse.Namespace, cfg, summary, windows) -> str:
    lines = [
        "# QuantumRandy Walk-Forward Report",
        "",
        "## Run",
        "",
        f"- Symbol: `{cfg.symbol}`",
        f"- Bar hours: `{cfg.bar_hours}`",
        f"- Windows: `{len(windows)}`",
        f"- Formula count: `{len(summary)}`",
        f"- Window shape: `{args.train_months}m train / {args.validation_months}m validation / {args.test_months}m test`, step `{args.step_months}m`",
        "",
        "## Pass Rule",
        "",
        f"- Segment pass: `rank_ic >= {cfg.filter.min_rank_ic}` AND `directional_win_rate >= {cfg.filter.min_directional_win_rate}` AND `sharpe >= {cfg.filter.min_validation_sharpe}`",
        "- Window survival: validation segment passes AND test segment passes.",
        "",
        "## Top Formulas",
        "",
    ]
    if summary.empty:
        lines.append("No formulas evaluated.")
    else:
        lines.append("| Rank | Survival | Test Pass | Median Test Sharpe | Median Test Rank IC | Formula |")
        lines.append("|---:|---:|---:|---:|---:|---|")
        for rank, row in enumerate(summary.head(20).to_dict(orient="records"), start=1):
            lines.append(
                "| "
                f"{rank} | {row['survival_rate']:.2f} | {row['test_pass_rate']:.2f} | "
                f"{row['test_sharpe_median']:.2f} | {row['test_rank_ic_median']:.4f} | `{row['formula']}` |"
            )
    lines.extend(
        [
            "",
            "## Files",
            "",
            "- `walk_forward_details.csv`: every formula x window x segment metric row.",
            "- `walk_forward_summary.csv`: formula-level survival ranking.",
            "- `walk_forward_windows.json`: exact train/validation/test date boundaries.",
            "- `walk_forward_config.json`: run parameters and pass rule.",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()

