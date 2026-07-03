from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class CryptoFeatureSpec:
    feature: str
    description: str
    required_columns: tuple[str, ...]
    filename_patterns: tuple[str, ...]


CRYPTO_FEATURE_SPECS = [
    CryptoFeatureSpec(
        "open_interest",
        "Point-in-time futures open interest.",
        ("timestamp", "open_interest"),
        ("*open_interest*.csv", "*oi*.csv"),
    ),
    CryptoFeatureSpec(
        "basis_perp_spot_spread",
        "Point-in-time perpetual versus spot basis or spread.",
        ("timestamp", "basis"),
        ("*basis*.csv", "*perp_spot*.csv", "*spread*.csv"),
    ),
    CryptoFeatureSpec(
        "funding_term_structure",
        "Multiple contract funding-rate curve or term-structure observations.",
        ("timestamp", "contract", "funding_rate"),
        ("*funding_term_structure*.csv", "*funding_curve*.csv"),
    ),
    CryptoFeatureSpec(
        "liquidation_imbalance",
        "Point-in-time liquidation notional or buy/sell liquidation imbalance.",
        ("timestamp", "long_liquidation_notional", "short_liquidation_notional"),
        ("*liquidation*.csv", "*liquidations*.csv"),
    ),
    CryptoFeatureSpec(
        "taker_buy_sell_imbalance",
        "Point-in-time taker buy and taker sell participation imbalance.",
        ("timestamp", "taker_buy_volume", "taker_sell_volume"),
        ("*taker_imbalance*.csv", "*taker_flow*.csv", "*aggtrade*.csv"),
    ),
    CryptoFeatureSpec(
        "order_book_depth",
        "Point-in-time order-book depth or bid/ask imbalance proxy.",
        ("timestamp", "bid_depth", "ask_depth"),
        ("*order_book*.csv", "*orderbook*.csv", "*depth*.csv"),
    ),
]


def run_crypto_feature_readiness(data_roots: list[str | Path]) -> pd.DataFrame:
    roots = [Path(root) for root in data_roots]
    rows = [_inspect_feature(spec, roots) for spec in CRYPTO_FEATURE_SPECS]
    return pd.DataFrame(rows)


def feature_readiness_manifest(frame: pd.DataFrame, data_roots: list[str | Path]) -> dict[str, object]:
    eligible = int((frame["status"] == "eligible_for_candidate_design").sum()) if not frame.empty else 0
    return {
        "artifact": "crypto_feature_readiness",
        "research_only": True,
        "not_runtime_publish_payload": True,
        "does_not_download_data": True,
        "data_roots": [str(Path(root)) for root in data_roots],
        "feature_count": int(len(frame)),
        "eligible_for_candidate_design_count": eligible,
        "ready_for_formula_profile_admission": False,
        "formula_profile_action": "No new base fields are admitted by this audit.",
        "rows": frame.to_dict(orient="records"),
    }


def feature_readiness_report(frame: pd.DataFrame, manifest: dict[str, object]) -> str:
    status_counts = frame["status"].value_counts().to_dict() if "status" in frame else {}
    lines = [
        "# Crypto-Native Feature Readiness Report",
        "",
        "This is a read-only research artifact. It does not download data, call exchange APIs, store credentials,",
        "publish factors, admit formula fields, or mutate runtime state.",
        "",
        "## Summary",
        "",
        f"- Features checked: `{manifest['feature_count']}`",
        f"- Eligible for candidate design: `{manifest['eligible_for_candidate_design_count']}`",
        f"- Ready for formula profile admission: `{manifest['ready_for_formula_profile_admission']}`",
        "- No new base fields are admitted by this audit.",
        f"- Status counts: `{status_counts}`",
        "",
        "## Features",
        "",
        "| Feature | Status | Point-In-Time Ready | Formula Profile Action | Required Columns | Observed Files | Reason |",
        "|---|---|---:|---|---|---|---|",
    ]
    for row in frame.to_dict(orient="records"):
        lines.append(
            "| "
            f"`{row['feature']}` | `{row['status']}` | `{row['point_in_time_ready']}` | "
            f"`{row['formula_profile_action']}` | `{row['required_columns']}` | "
            f"`{row['observed_files']}` | `{row['reason']}` |"
        )
    lines.extend(
        [
            "",
            "## Formula Profile Decision",
            "",
            "Current admitted formula fields remain `open`, `high`, `low`, `close`, `volume`, and `funding_rate`.",
            "Open interest, basis, funding term structure, liquidations, taker imbalance, and order-book depth remain",
            "outside formula execution until a separate profile-admission pass approves them.",
        ]
    )
    return "\n".join(lines) + "\n"


def _inspect_feature(spec: CryptoFeatureSpec, roots: list[Path]) -> dict[str, object]:
    files = _matching_files(spec, roots)
    required = set(spec.required_columns)
    row = {
        "feature": spec.feature,
        "description": spec.description,
        "status": "missing_source",
        "reason": "no local source file matched expected patterns",
        "observed_files": "",
        "required_columns": ",".join(spec.required_columns),
        "observed_columns": "",
        "missing_columns": ",".join(spec.required_columns),
        "row_count": 0,
        "point_in_time_ready": False,
        "formula_profile_action": "do_not_admit",
    }
    if not files:
        return row

    observed_columns: set[str] = set()
    total_rows = 0
    read_errors: list[str] = []
    for path in files:
        try:
            frame = pd.read_csv(path, nrows=25)
        except Exception as exc:
            read_errors.append(f"{path.name}:{exc}")
            continue
        observed_columns.update(str(column) for column in frame.columns)
        total_rows += len(frame)

    missing = sorted(required - observed_columns)
    row.update(
        {
            "observed_files": ";".join(str(path) for path in files),
            "observed_columns": ",".join(sorted(observed_columns)),
            "missing_columns": ",".join(missing),
            "row_count": int(total_rows),
        }
    )
    if read_errors:
        row["status"] = "present_schema_incomplete"
        row["reason"] = "read errors: " + ";".join(read_errors)
        return row
    if missing:
        row["status"] = "present_schema_incomplete"
        row["reason"] = "missing required columns"
        return row
    row["status"] = "eligible_for_candidate_design"
    row["reason"] = "local source schema contains required point-in-time columns"
    row["point_in_time_ready"] = True
    row["formula_profile_action"] = "requires_separate_profile_admission"
    return row


def _matching_files(spec: CryptoFeatureSpec, roots: list[Path]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for pattern in spec.filename_patterns:
            files.extend(path for path in root.glob(pattern) if path.is_file())
    return sorted(set(files))
