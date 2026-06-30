from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantumrandy.factor_publisher import (
    admin_token_from_env,
    build_update_payload,
    fetch_runtime_manifest,
    load_json,
    select_runtime_factors,
    submit_runtime_config,
    write_publish_artifacts,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build or submit a manual QuantumRandy runtime factor update.")
    parser.add_argument("--leaderboard", required=True, help="Path to research leaderboard.json")
    parser.add_argument("--runtime-manifest", default="configs/runtime_factors.json", help="Local runtime manifest for dry-run generation")
    parser.add_argument("--runtime-url", default="http://127.0.0.1:8787")
    parser.add_argument("--admin-token-env", default="QUANTUMRANDY_ADMIN_TOKEN")
    parser.add_argument("--out", default="reports/runtime_publish/proposed_runtime_config.json")
    parser.add_argument("--max-factors", type=int, default=5)
    parser.add_argument("--include-unpassed", action="store_true", help="Allow factors without passed=true")
    parser.add_argument("--min-brutal-score", type=float, default=None)
    parser.add_argument("--exposure-threshold", type=float, default=0.15)
    parser.add_argument("--strategy-id", default="published_equal_weight_blend")
    parser.add_argument("--initial-capital-usd", type=float, default=1000.0)
    parser.add_argument("--submit", action="store_true", help="Submit to runtime admin API after writing artifacts")
    args = parser.parse_args()

    leaderboard = load_json(args.leaderboard)
    if not isinstance(leaderboard, list):
        raise SystemExit("leaderboard must be a JSON list")

    selection = select_runtime_factors(
        leaderboard,
        max_factors=args.max_factors,
        include_unpassed=args.include_unpassed,
        min_brutal_score=args.min_brutal_score,
        exposure_threshold=args.exposure_threshold,
        strategy_id=args.strategy_id,
        initial_capital_usd=args.initial_capital_usd,
    )
    if args.submit:
        current = fetch_runtime_manifest(args.runtime_url)
        expected_generation = int(current.get("generation", 0))
    else:
        current = load_json(args.runtime_manifest)
        expected_generation = int(current.get("generation", 0))

    payload = build_update_payload(
        expected_generation=expected_generation,
        factors=selection.factors,
        strategies=selection.strategies,
    )
    audit_path = write_publish_artifacts(args.out, payload, selection.selected_rows)
    print(f"Wrote proposal: {Path(args.out).resolve()}")
    print(f"Wrote audit: {Path(audit_path).resolve()}")
    print(f"Selected {len(selection.selected_rows)} factors for expected generation {expected_generation}")

    if args.submit:
        token = admin_token_from_env(args.admin_token_env)
        result = submit_runtime_config(args.runtime_url, token, payload)
        print(f"Submitted runtime update. New generation: {result.get('generation')}")
    else:
        print("Dry run only. Re-run with --submit to call the runtime admin API.")


if __name__ == "__main__":
    main()
