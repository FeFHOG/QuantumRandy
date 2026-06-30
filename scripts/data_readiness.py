from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantumrandy.data_readiness import (
    DEFAULT_UNIVERSE_SYMBOLS,
    ReadinessPolicy,
    build_config_targets,
    readiness_manifest,
    readiness_report,
    run_data_readiness,
    scaffold_asset_configs,
)
from quantumrandy.io_utils import safe_write_csv, safe_write_json, safe_write_text


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read-only config/data readiness check for multi-asset QuantumRandy research"
    )
    parser.add_argument(
        "--symbol",
        action="append",
        default=[],
        help="Expected symbol to check. Defaults to BTC/ETH/SOL/BNB/AVAX when --config is not supplied.",
    )
    parser.add_argument("--config", action="append", default=[], help="Config YAML to check; can be repeated.")
    parser.add_argument("--config-dir", default="configs", help="Directory used for symbol-derived config paths.")
    parser.add_argument(
        "--write-missing-configs",
        action="store_true",
        help="Create missing research configs from the BTC template before checking readiness.",
    )
    parser.add_argument("--reference-config", default="configs/btcusdt.yaml")
    parser.add_argument("--data-root", default="../../RandysLab-STRICT4H/data")
    parser.add_argument("--overwrite-configs", action="store_true", help="Rewrite scaffolded configs if they exist.")
    parser.add_argument("--out", default="reports/data_readiness", help="Output directory.")
    parser.add_argument("--min-total-bars", type=int, default=180)
    parser.add_argument("--min-window-bars", type=int, default=30)
    args = parser.parse_args()

    policy = ReadinessPolicy(min_total_bars=args.min_total_bars, min_window_bars=args.min_window_bars)
    symbols = [symbol.upper() for symbol in args.symbol] if args.symbol else DEFAULT_UNIVERSE_SYMBOLS
    scaffold_rows = []
    if args.write_missing_configs and not args.config:
        scaffold_rows = scaffold_asset_configs(
            symbols,
            config_dir=args.config_dir,
            reference_config=args.reference_config,
            data_root=args.data_root,
            overwrite=args.overwrite_configs,
        )
    targets = build_config_targets(symbols, config_dir=args.config_dir, config_paths=args.config)
    frame = run_data_readiness(targets, policy=policy)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    safe_write_csv(out / "data_readiness.csv", frame, out / "events.jsonl")
    safe_write_json(
        out / "data_readiness_manifest.json",
        {**readiness_manifest(frame, targets, policy), "scaffolded_configs": scaffold_rows},
        out / "events.jsonl",
    )
    safe_write_text(out / "DATA_READINESS_REPORT.md", readiness_report(frame, policy), out / "events.jsonl")

    ready_count = int(frame["ready"].sum()) if "ready" in frame else 0
    if scaffold_rows:
        written = sum(1 for row in scaffold_rows if row["written"])
        print(f"Config scaffold: wrote={written}; skipped={len(scaffold_rows) - written}")
    print(f"Checked {len(frame)} asset configs; ready={ready_count}; incomplete={len(frame) - ready_count}")
    print(f"Output: {out.resolve()}")
    for row in frame.to_dict(orient="records"):
        symbol = row.get("expected_symbol") or row.get("symbol") or row.get("config_path")
        print(f"{symbol}: {row.get('status')} {row.get('reasons')}")


if __name__ == "__main__":
    main()
