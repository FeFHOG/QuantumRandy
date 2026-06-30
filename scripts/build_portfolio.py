from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantumrandy.config import load_config
from quantumrandy.data import load_market_frame, slice_window
from quantumrandy.io_utils import safe_write_csv, safe_write_json, safe_write_text
from quantumrandy.portfolio import build_portfolio_research, render_portfolio_report
from quantumrandy.walk_forward import load_formula_entries


def main() -> None:
    ap = argparse.ArgumentParser(description="Build fixed-weight QuantumRandy factor portfolios for research.")
    ap.add_argument("--config", default="configs/btcusdt.yaml", help="Path to config yaml")
    ap.add_argument("--leaderboard", help="Path to leaderboard.json")
    ap.add_argument("--formula", action="append", default=[], help="Formula to include; can be repeated")
    ap.add_argument("--out", default="reports/portfolio", help="Output directory")
    ap.add_argument("--top", type=int, help="Use only first N formulas after filtering")
    ap.add_argument("--passed-only", action="store_true", help="Only use leaderboard entries where passed is not false")
    ap.add_argument("--window", choices=["training", "validation", "all"], default="validation")
    ap.add_argument("--max-corr", type=float, help="Maximum absolute pairwise factor correlation after selection")
    ap.add_argument("--min-factors", type=int, default=1, help="Minimum factors to keep even if correlation is high")
    args = ap.parse_args()

    cfg = load_config(args.config)
    data = load_market_frame(cfg.ohlcv_csv, cfg.funding_csv)
    data = _slice_data(data, cfg, args.window)
    entries = load_formula_entries(args.leaderboard, args.formula, passed_only=args.passed_only, top=args.top)
    if not entries:
        entries = [
            {"formula": formula, "description": "seed formula", "source": "config_seed", "passed": None}
            for formula in cfg.mcts.seed_formulas
        ]

    print(f"Loaded {len(entries)} formulas over {len(data)} bars")
    factors, selection, portfolios, manifest = build_portfolio_research(
        data,
        entries,
        cfg,
        max_corr=args.max_corr,
        min_factors=args.min_factors,
    )
    manifest["window"] = args.window
    manifest["config"] = str(Path(args.config))

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    safe_write_csv(out / "portfolio_factors.csv", factors, out / "events.jsonl")
    safe_write_csv(out / "portfolio_selection.csv", selection, out / "events.jsonl")
    safe_write_csv(out / "portfolio_summary.csv", portfolios, out / "events.jsonl")
    safe_write_json(out / "portfolio_manifest.json", manifest, out / "events.jsonl")
    safe_write_text(
        out / "PORTFOLIO_REPORT.md",
        render_portfolio_report(manifest, factors, selection, portfolios),
        out / "events.jsonl",
    )

    print(f"Output: {out.resolve()}")
    print("Portfolios:")
    for row in portfolios.to_dict(orient="records"):
        print(
            f"{row['portfolio_id']}: factors={row['factor_count']} "
            f"sharpe={row['sharpe']:.2f} rank_ic={row['rank_ic']:.4f} max_dd={row['max_dd']:.4f}"
        )


def _slice_data(data, cfg, window: str):
    if window == "training":
        return slice_window(data, cfg.windows.training_start, cfg.windows.training_end)
    if window == "validation":
        return slice_window(data, cfg.windows.validation_start, cfg.windows.validation_end)
    if window == "all":
        return data.copy()
    raise ValueError("Unsupported window")


if __name__ == "__main__":
    main()
