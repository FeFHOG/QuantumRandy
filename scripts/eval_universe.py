from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantumrandy.io_utils import safe_write_csv, safe_write_json, safe_write_text
from quantumrandy.universe import load_asset_dataset, run_universe_evaluation
from quantumrandy.walk_forward import load_formula_entries


def main() -> None:
    ap = argparse.ArgumentParser(description="Evaluate fixed QuantumRandy formulas across multiple asset configs")
    ap.add_argument("--config", action="append", default=[], help="Asset config yaml; repeat for BTC/ETH/SOL/etc.")
    ap.add_argument("--leaderboard", help="Path to leaderboard.json")
    ap.add_argument("--formula", action="append", default=[], help="Formula to evaluate; can be repeated")
    ap.add_argument("--out", default="reports/universe_eval", help="Output directory")
    ap.add_argument("--top", type=int, help="Use only first N formulas after filtering")
    ap.add_argument("--passed-only", action="store_true", help="Only use leaderboard entries where passed is not false")
    ap.add_argument("--window", choices=["training", "validation", "all"], default="validation")
    args = ap.parse_args()

    config_paths = args.config or ["configs/btcusdt.yaml"]
    assets = [load_asset_dataset(path, window=args.window) for path in config_paths]
    if not assets:
        raise SystemExit("No asset configs loaded.")

    entries = load_formula_entries(args.leaderboard, args.formula, passed_only=args.passed_only, top=args.top)
    if not entries:
        first_cfg = assets[0].cfg
        entries = [
            {"formula": formula, "description": "seed formula", "source": "config_seed", "passed": None}
            for formula in first_cfg.mcts.seed_formulas
        ]

    print(f"Loaded {len(entries)} formulas across {len(assets)} asset configs")
    details, summary = run_universe_evaluation(assets, entries)
    summary = summary.sort_values(
        ["robustness_score", "pass_rate", "mean_sharpe", "median_rank_ic"],
        ascending=[False, False, False, False],
    )

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    safe_write_csv(out / "universe_details.csv", details, out / "events.jsonl")
    safe_write_csv(out / "universe_summary.csv", summary, out / "events.jsonl")
    safe_write_json(out / "universe_report.json", _json_report(args, assets, summary), out / "events.jsonl")
    safe_write_text(out / "UNIVERSE_REPORT.md", _markdown_report(args, assets, summary), out / "events.jsonl")

    print(f"Output: {out.resolve()}")
    print("Top formulas:")
    for row in summary.head(5).to_dict(orient="records"):
        print(
            f"score={row['robustness_score']:.2f} "
            f"pass_rate={row['pass_rate']:.2f} "
            f"mean_sharpe={row['mean_sharpe']:.2f} "
            f"median_rank_ic={row['median_rank_ic']:.4f} "
            f"{row['formula']}"
        )


def _json_report(args: argparse.Namespace, assets, summary) -> dict:
    return {
        "window": args.window,
        "asset_count": len(assets),
        "assets": [
            {
                "symbol": asset.name,
                "config": asset.config_path,
                "bars": len(asset.data),
                "ohlcv_csv": str(asset.cfg.ohlcv_csv),
                "funding_csv": str(asset.cfg.funding_csv),
            }
            for asset in assets
        ],
        "formula_count": len(summary),
        "ranking": summary.to_dict(orient="records"),
        "score": "mean_sharpe + 10*median_rank_ic + pass_rate - sharpe_variance - worst_max_dd",
    }


def _markdown_report(args: argparse.Namespace, assets, summary) -> str:
    lines = [
        "# QuantumRandy Multi-Asset Robustness Report",
        "",
        "## Run",
        "",
        f"- Window: `{args.window}`",
        f"- Asset configs: `{len(assets)}`",
        f"- Formula count: `{len(summary)}`",
        "- Robustness score: `mean_sharpe + 10*median_rank_ic + pass_rate - sharpe_variance - worst_max_dd`",
        "",
        "## Assets",
        "",
        "| Asset | Bars | Config |",
        "|---|---:|---|",
    ]
    for asset in assets:
        lines.append(f"| `{asset.name}` | {len(asset.data)} | `{asset.config_path}` |")

    lines.extend(["", "## Top Formulas", ""])
    if summary.empty:
        lines.append("No formulas evaluated.")
    else:
        lines.append(
            "| Rank | Score | Pass Rate | Passed Assets | Mean Sharpe | Median Rank IC | Worst Max DD | Formula |"
        )
        lines.append("|---:|---:|---:|---:|---:|---:|---:|---|")
        for rank, row in enumerate(summary.head(20).to_dict(orient="records"), start=1):
            lines.append(
                "| "
                f"{rank} | {row['robustness_score']:.2f} | {row['pass_rate']:.2f} | "
                f"{row['passed_assets']}/{row['asset_count']} | {row['mean_sharpe']:.2f} | "
                f"{row['median_rank_ic']:.4f} | {row['worst_max_dd']:.4f} | `{row['formula']}` |"
            )

    lines.extend(
        [
            "",
            "## Files",
            "",
            "- `universe_details.csv`: every formula x asset metric row.",
            "- `universe_summary.csv`: formula-level robustness ranking.",
            "- `universe_report.json`: run metadata plus machine-readable ranking.",
            "- `UNIVERSE_REPORT.md`: this report.",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
