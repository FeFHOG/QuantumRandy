from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .config import ProjectConfig, load_config
from .data import REQUIRED_OHLCV, slice_window

DEFAULT_UNIVERSE_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "AVAXUSDT"]
REQUIRED_FUNDING = {"timestamp", "funding_rate"}


@dataclass(frozen=True)
class ReadinessPolicy:
    min_total_bars: int = 180
    min_window_bars: int = 30
    max_gap_multiple: float = 1.5


def build_config_targets(
    symbols: list[str] | None = None,
    *,
    config_dir: str | Path = "configs",
    config_paths: list[str | Path] | None = None,
) -> list[dict[str, object]]:
    if config_paths:
        return [{"expected_symbol": "", "config_path": str(Path(path))} for path in config_paths]
    return [
        {"expected_symbol": symbol.upper(), "config_path": str(Path(config_dir) / f"{symbol.lower()}.yaml")}
        for symbol in (symbols or DEFAULT_UNIVERSE_SYMBOLS)
    ]


def run_data_readiness(
    targets: list[dict[str, object]],
    *,
    policy: ReadinessPolicy | None = None,
) -> pd.DataFrame:
    policy = policy or ReadinessPolicy()
    rows = [
        inspect_asset_readiness(
            str(target.get("config_path", "")),
            str(target.get("expected_symbol", "")),
            policy,
        )
        for target in targets
    ]
    return pd.DataFrame(rows)


def inspect_asset_readiness(
    config_path: str | Path,
    expected_symbol: str = "",
    policy: ReadinessPolicy | None = None,
) -> dict[str, object]:
    policy = policy or ReadinessPolicy()
    config_path = Path(config_path)
    row: dict[str, object] = {
        "expected_symbol": expected_symbol,
        "symbol": "",
        "status": "missing_config",
        "ready": False,
        "config_path": str(config_path),
        "config_exists": config_path.exists(),
        "bar_hours": None,
        "ohlcv_csv": "",
        "ohlcv_exists": False,
        "ohlcv_rows": 0,
        "ohlcv_start": "",
        "ohlcv_end": "",
        "ohlcv_missing_columns": "",
        "ohlcv_duplicate_timestamps": 0,
        "ohlcv_missing_bars": 0,
        "ohlcv_max_gap_hours": 0.0,
        "ohlcv_interval_ok": False,
        "funding_csv": "",
        "funding_exists": False,
        "funding_rows": 0,
        "funding_start": "",
        "funding_end": "",
        "funding_missing_columns": "",
        "funding_duplicate_timestamps": 0,
        "funding_alignment_coverage": 0.0,
        "training_bars": 0,
        "validation_bars": 0,
        "training_window_covered": False,
        "validation_window_covered": False,
        "reasons": "",
    }
    reasons: list[str] = []
    if not config_path.exists():
        reasons.append("config_missing")
        row["reasons"] = ";".join(reasons)
        return row

    try:
        cfg = load_config(config_path)
    except Exception as exc:
        row["status"] = "config_error"
        row["reasons"] = f"config_error:{exc}"
        return row

    row.update(
        {
            "symbol": cfg.symbol,
            "bar_hours": cfg.bar_hours,
            "ohlcv_csv": str(cfg.ohlcv_csv),
            "ohlcv_exists": cfg.ohlcv_csv.exists(),
            "funding_csv": str(cfg.funding_csv),
            "funding_exists": cfg.funding_csv.exists(),
        }
    )
    if expected_symbol and cfg.symbol.upper() != expected_symbol.upper():
        reasons.append("symbol_mismatch")

    ohlcv = _inspect_csv(cfg.ohlcv_csv, REQUIRED_OHLCV)
    funding = _inspect_csv(cfg.funding_csv, REQUIRED_FUNDING)
    _merge_csv_stats(row, "ohlcv", ohlcv)
    _merge_csv_stats(row, "funding", funding)
    reasons.extend(f"ohlcv_{reason}" for reason in ohlcv["reasons"])
    reasons.extend(f"funding_{reason}" for reason in funding["reasons"])

    if ohlcv["frame"] is not None:
        ohlcv_frame = ohlcv["frame"]
        assert isinstance(ohlcv_frame, pd.DataFrame)
        interval_stats = _interval_stats(ohlcv_frame.index, cfg.bar_hours, policy)
        row.update(interval_stats)
        if not bool(interval_stats["ohlcv_interval_ok"]):
            reasons.append("ohlcv_interval_not_4h_regular")
        if len(ohlcv_frame) < policy.min_total_bars:
            reasons.append("ohlcv_too_few_bars")

        row.update(_window_stats(ohlcv_frame, cfg, policy))
        if not bool(row["training_window_covered"]):
            reasons.append("training_window_not_covered")
        if not bool(row["validation_window_covered"]):
            reasons.append("validation_window_not_covered")

        funding_frame = funding["frame"]
        if isinstance(funding_frame, pd.DataFrame):
            aligned_funding = funding_frame.reindex(ohlcv_frame.index.union(funding_frame.index)).sort_index().ffill()
            coverage = aligned_funding.reindex(ohlcv_frame.index)["funding_rate"].notna().mean()
            row["funding_alignment_coverage"] = round(float(coverage), 6)
            if coverage < 0.95:
                reasons.append("funding_alignment_low")

    ready = not reasons
    row["ready"] = ready
    row["status"] = "ready" if ready else "incomplete"
    row["reasons"] = ";".join(reasons)
    return row


def readiness_manifest(
    frame: pd.DataFrame,
    targets: list[dict[str, object]],
    policy: ReadinessPolicy,
) -> dict[str, object]:
    ready_count = int(frame["ready"].sum()) if "ready" in frame else 0
    return {
        "artifact": "data_readiness",
        "research_only": True,
        "target_count": len(targets),
        "ready_count": ready_count,
        "incomplete_count": len(frame) - ready_count,
        "policy": {
            "min_total_bars": policy.min_total_bars,
            "min_window_bars": policy.min_window_bars,
            "max_gap_multiple": policy.max_gap_multiple,
        },
        "targets": targets,
        "rows": frame.to_dict(orient="records"),
    }


def readiness_report(frame: pd.DataFrame, policy: ReadinessPolicy) -> str:
    ready_count = int(frame["ready"].sum()) if not frame.empty else 0
    lines = [
        "# QuantumRandy Data Readiness Report",
        "",
        "This is a read-only research artifact. It checks whether asset configs and local CSV files are ready for",
        (
            "`scripts/eval_universe.py`; it does not download data, call exchange APIs, publish factors, "
            "or mutate runtime state."
        ),
        "",
        "## Summary",
        "",
        f"- Targets checked: `{len(frame)}`",
        f"- Ready: `{ready_count}`",
        f"- Incomplete: `{len(frame) - ready_count}`",
        f"- Minimum total bars: `{policy.min_total_bars}`",
        f"- Minimum configured-window bars: `{policy.min_window_bars}`",
        "",
        "## Assets",
        "",
        "| Expected | Symbol | Status | Total Bars | Training Bars | Validation Bars | Funding Coverage | Reasons |",
        "|---|---|---|---:|---:|---:|---:|---|",
    ]
    for row in frame.to_dict(orient="records"):
        lines.append(
            "| "
            f"`{row.get('expected_symbol', '')}` | `{row.get('symbol', '')}` | `{row.get('status', '')}` | "
            f"{int(row.get('ohlcv_rows') or 0)} | {int(row.get('training_bars') or 0)} | "
            f"{int(row.get('validation_bars') or 0)} | {float(row.get('funding_alignment_coverage') or 0.0):.2f} | "
            f"`{row.get('reasons', '')}` |"
        )

    lines.extend(
        [
            "",
            "## Files",
            "",
            "- `data_readiness.csv`: one row per expected asset config.",
            "- `data_readiness_manifest.json`: policy, targets, and machine-readable rows.",
            "- `DATA_READINESS_REPORT.md`: this report.",
        ]
    )
    return "\n".join(lines) + "\n"


def _inspect_csv(path: Path, required_columns: set[str]) -> dict[str, object]:
    out: dict[str, object] = {
        "rows": 0,
        "start": "",
        "end": "",
        "missing_columns": "",
        "duplicate_timestamps": 0,
        "frame": None,
        "reasons": [],
    }
    reasons: list[str] = []
    if not path.exists():
        reasons.append("missing")
        out["reasons"] = reasons
        return out
    try:
        raw = pd.read_csv(path)
    except Exception as exc:
        reasons.append(f"read_error:{exc}")
        out["reasons"] = reasons
        return out

    missing = sorted(required_columns - set(raw.columns))
    out["rows"] = len(raw)
    out["missing_columns"] = ",".join(missing)
    if missing:
        reasons.append("missing_columns")
        out["reasons"] = reasons
        return out

    try:
        raw["timestamp"] = pd.to_datetime(raw["timestamp"], utc=True, format="mixed")
    except Exception as exc:
        reasons.append(f"timestamp_parse_error:{exc}")
        out["reasons"] = reasons
        return out

    duplicates = int(raw["timestamp"].duplicated().sum())
    out["duplicate_timestamps"] = duplicates
    if duplicates:
        reasons.append("duplicate_timestamps")

    raw = raw.sort_values("timestamp").drop_duplicates("timestamp")
    value_columns = [col for col in required_columns if col != "timestamp"]
    frame = raw.set_index("timestamp")[value_columns].astype(float)
    out["rows"] = len(frame)
    if len(frame):
        out["start"] = frame.index.min().isoformat()
        out["end"] = frame.index.max().isoformat()
    else:
        reasons.append("empty")
    out["frame"] = frame
    out["reasons"] = reasons
    return out


def _merge_csv_stats(row: dict[str, object], prefix: str, stats: dict[str, object]) -> None:
    row[f"{prefix}_rows"] = stats["rows"]
    row[f"{prefix}_start"] = stats["start"]
    row[f"{prefix}_end"] = stats["end"]
    row[f"{prefix}_missing_columns"] = stats["missing_columns"]
    row[f"{prefix}_duplicate_timestamps"] = stats["duplicate_timestamps"]


def _interval_stats(index: pd.DatetimeIndex, bar_hours: int, policy: ReadinessPolicy) -> dict[str, object]:
    if len(index) < 2:
        return {"ohlcv_missing_bars": 0, "ohlcv_max_gap_hours": 0.0, "ohlcv_interval_ok": False}
    deltas = index.to_series().diff().dropna().dt.total_seconds().div(3600)
    max_gap_hours = float(deltas.max()) if not deltas.empty else 0.0
    expected = pd.date_range(index.min(), index.max(), freq=f"{bar_hours}h", tz="UTC")
    missing_bars = max(len(expected.difference(index)), 0)
    return {
        "ohlcv_missing_bars": int(missing_bars),
        "ohlcv_max_gap_hours": round(max_gap_hours, 6),
        "ohlcv_interval_ok": missing_bars == 0 and max_gap_hours <= bar_hours * policy.max_gap_multiple,
    }


def _window_stats(data: pd.DataFrame, cfg: ProjectConfig, policy: ReadinessPolicy) -> dict[str, object]:
    training = slice_window(data, cfg.windows.training_start, cfg.windows.training_end)
    validation = slice_window(data, cfg.windows.validation_start, cfg.windows.validation_end)
    return {
        "training_bars": len(training),
        "validation_bars": len(validation),
        "training_window_covered": _window_covered(
            data,
            cfg.windows.training_start,
            cfg.windows.training_end,
            len(training),
            cfg.bar_hours,
            policy,
        ),
        "validation_window_covered": _window_covered(
            data,
            cfg.windows.validation_start,
            cfg.windows.validation_end,
            len(validation),
            cfg.bar_hours,
            policy,
        ),
    }


def _window_covered(
    data: pd.DataFrame,
    start: str | None,
    end: str | None,
    bars: int,
    bar_hours: int,
    policy: ReadinessPolicy,
) -> bool:
    if bars < policy.min_window_bars or data.empty:
        return False
    index_min = data.index.min()
    index_max = data.index.max()
    if start and pd.Timestamp(start, tz="UTC") < index_min:
        return False
    if end and pd.Timestamp(end, tz="UTC") - pd.Timedelta(hours=bar_hours) > index_max:
        return False
    return True
