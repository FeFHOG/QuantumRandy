from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantumrandy.feature_readiness import (  # noqa: E402
    feature_readiness_manifest,
    feature_readiness_report,
    run_crypto_feature_readiness,
)
from quantumrandy.io_utils import safe_write_csv, safe_write_json, safe_write_text  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only crypto-native feature readiness audit")
    parser.add_argument("--data-root", action="append", default=[], help="Local data directory to inspect.")
    parser.add_argument("--out", default="reports/research_1_0_feature_readiness", help="Output directory.")
    args = parser.parse_args()

    data_roots = args.data_root or ["../RandysLab-STRICT4H/data"]
    frame = run_crypto_feature_readiness(data_roots)
    manifest = feature_readiness_manifest(frame, data_roots)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    safe_write_csv(out / "crypto_feature_readiness.csv", frame, out / "events.jsonl")
    safe_write_json(out / "crypto_feature_readiness_manifest.json", manifest, out / "events.jsonl")
    safe_write_text(
        out / "CRYPTO_FEATURE_READINESS_REPORT.md",
        feature_readiness_report(frame, manifest),
        out / "events.jsonl",
    )

    print(f"Checked {len(frame)} crypto-native feature groups")
    print(f"Eligible for candidate design: {manifest['eligible_for_candidate_design_count']}")
    print("Formula profile admission: false")
    print(f"Output: {out.resolve()}")


if __name__ == "__main__":
    main()
