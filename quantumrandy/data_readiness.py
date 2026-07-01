from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import yaml

from .config import ProjectConfig, load_config
from .data import REQUIRED_OHLCV, slice_window

DEFAULT_UNIVERSE_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "AVAXUSDT"]
REQUIRED_FUNDING = {"timestamp", "funding_rate"}
DEFAULT_REFERENCE_CONFIG = Path("configs/btcusdt.yaml")
DEFAULT_DATA_ROOT = Path("../../RandysLab-STRICT4H/data")


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


def scaffold_asset_configs(
    symbols: list[str] | None = None,
    *,
    config_dir: str | Path = "configs",
    reference_config: str | Path = DEFAULT_REFERENCE_CONFIG,
    data_root: str | Path = DEFAULT_DATA_ROOT,
    overwrite: bool = False,
) -> list[dict[str, object]]:
    reference_config = Path(reference_config)
    raw = yaml.safe_load(reference_config.read_text(encoding="utf-8")) or {}
    config_dir = Path(config_dir)
    data_root = Path(data_root)
    config_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, object]] = []
    for symbol in symbols or DEFAULT_UNIVERSE_SYMBOLS:
        symbol = symbol.upper()
        path = config_dir / f"{symbol.lower()}.yaml"
        existed = path.exists()
        written = False
        if overwrite or not existed:
            next_raw = _asset_config_from_template(raw, symbol, data_root)
            path.write_text(_asset_config_yaml(next_raw), encoding="utf-8")
            written = True
        rows.append(
            {
                "symbol": symbol,
                "config_path": str(path),
                "existed": existed,
                "written": written,
                "overwrite": overwrite,
            }
        )
    return rows


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
        "ohlcv_file_size_bytes": 0,
        "ohlcv_file_mtime": "",
        "ohlcv_sha256_16": "",
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
        "funding_file_size_bytes": 0,
        "funding_file_mtime": "",
        "funding_sha256_16": "",
        "funding_rows": 0,
        "funding_start": "",
        "funding_end": "",
        "funding_missing_columns": "",
        "funding_duplicate_timestamps": 0,
        "funding_alignment_coverage": 0.0,
        "funding_expected_observations": 0,
        "funding_observations_in_window": 0,
        "funding_raw_coverage": 0.0,
        "funding_max_staleness_hours": 0.0,
        "research_bars": 0,
        "research_expected_bars": 0,
        "research_coverage_ratio": 0.0,
        "training_bars": 0,
        "training_expected_bars": 0,
        "training_coverage_ratio": 0.0,
        "training_missing_bars": 0,
        "validation_bars": 0,
        "validation_expected_bars": 0,
        "validation_coverage_ratio": 0.0,
        "validation_missing_bars": 0,
        "training_window_covered": False,
        "validation_window_covered": False,
        "training_start": "",
        "training_end": "",
        "validation_start": "",
        "validation_end": "",
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
            "training_start": cfg.windows.training_start or "",
            "training_end": cfg.windows.training_end or "",
            "validation_start": cfg.windows.validation_start or "",
            "validation_end": cfg.windows.validation_end or "",
        }
    )
    _merge_file_stats(row, "ohlcv", cfg.ohlcv_csv)
    _merge_file_stats(row, "funding", cfg.funding_csv)
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
        research_frame = slice_window(ohlcv_frame, cfg.windows.training_start, cfg.windows.validation_end)
        interval_stats = _interval_stats(research_frame.index, cfg.bar_hours, policy)
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
            coverage_index = research_frame.index if len(research_frame) else ohlcv_frame.index
            funding_stats = _funding_quality_stats(
                funding_frame,
                coverage_index,
                cfg.windows.training_start,
                cfg.windows.validation_end,
            )
            row.update(funding_stats)
            if float(funding_stats["funding_alignment_coverage"]) < 0.95:
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


def data_fetch_plan(frame: pd.DataFrame, *, randyslab_dir: str = "../RandysLab-STRICT4H") -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in frame.to_dict(orient="records"):
        symbol = str(row.get("symbol") or row.get("expected_symbol") or "").upper()
        if not symbol or not bool(row.get("config_exists")):
            continue
        missing_ohlcv = not bool(row.get("ohlcv_exists"))
        missing_funding = not bool(row.get("funding_exists"))
        incomplete_window = (
            not bool(row.get("training_window_covered")) or not bool(row.get("validation_window_covered"))
        )
        if not (missing_ohlcv or missing_funding or incomplete_window):
            continue
        start = str(row.get("training_start") or "2019-09-08")
        end = str(row.get("validation_end") or "2025-11-24")
        rows.append(
            {
                "symbol": symbol,
                "market_symbol": _binance_usdm_symbol(symbol),
                "file_prefix": symbol,
                "missing_ohlcv": missing_ohlcv,
                "missing_funding": missing_funding,
                "incomplete_window": incomplete_window,
                "start": start,
                "end": end,
                "command": (
                    f"cd {randyslab_dir} && python scripts/fetch_binance.py "
                    f"--symbol {_binance_usdm_symbol(symbol)} --file-prefix {symbol} --start {start} --end {end} "
                    "--method archive"
                ),
                "proxy_command": (
                    f"cd {randyslab_dir} && python scripts/fetch_binance.py "
                    f"--symbol {_binance_usdm_symbol(symbol)} --file-prefix {symbol} --start {start} --end {end} "
                    "--method archive --proxy http://127.0.0.1:7890"
                ),
            }
        )
    return rows


def data_fetch_runbook(plan: list[dict[str, object]]) -> str:
    lines = [
        "# QuantumRandy Multi-Asset Data Fetch Runbook",
        "",
        "This is a read-only planning artifact. It lists public Binance USD-M historical data commands for RandysLab,",
        (
            "but it does not download data, call exchange APIs, store credentials, publish factors, "
            "or mutate runtime state."
        ),
        "",
        "## Commands",
        "",
    ]
    if not plan:
        lines.append("No missing local OHLCV/funding files were detected for configured assets.")
    else:
        for item in plan:
            lines.extend(
                [
                    f"### {item['symbol']}",
                    "",
                    f"- Missing OHLCV: `{item['missing_ohlcv']}`",
                    f"- Missing funding: `{item['missing_funding']}`",
                    f"- Configured window incomplete: `{item['incomplete_window']}`",
                    f"- Window: `{item['start']}` to `{item['end']}`",
                    "",
                    "```powershell",
                    str(item["command"]).replace(" && ", "; "),
                    "```",
                    "",
                    "With a local proxy:",
                    "",
                    "```powershell",
                    str(item["proxy_command"]).replace(" && ", "; "),
                    "```",
                    "",
                ]
            )
    lines.extend(
        [
            "## After Fetching",
            "",
            "Run the readiness check again:",
            "",
            "```powershell",
            "python scripts\\data_readiness.py --out reports\\data_readiness",
            "```",
            "",
            "When assets become ready, run the universe evaluator with the same configs.",
        ]
    )
    return "\n".join(lines) + "\n"


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
        "| Expected | Symbol | Status | Research Coverage | Missing Bars | Funding Align | Funding Stale Hrs | CSV Hashes | Reasons |",
        "|---|---|---|---:|---:|---:|---:|---|---|",
    ]
    for row in frame.to_dict(orient="records"):
        expected = row.get("expected_symbol", "") or row.get("symbol", "")
        lines.append(
            "| "
            f"`{expected}` | `{row.get('symbol', '')}` | `{row.get('status', '')}` | "
            f"{float(row.get('research_coverage_ratio') or 0.0):.2%} | "
            f"{int(row.get('ohlcv_missing_bars') or 0)} | "
            f"{float(row.get('funding_alignment_coverage') or 0.0):.2%} | "
            f"{float(row.get('funding_max_staleness_hours') or 0.0):.1f} | "
            f"`ohlcv:{row.get('ohlcv_sha256_16', '')} funding:{row.get('funding_sha256_16', '')}` | "
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


def _merge_file_stats(row: dict[str, object], prefix: str, path: Path) -> None:
    stats = _file_stats(path)
    row[f"{prefix}_file_size_bytes"] = stats["size_bytes"]
    row[f"{prefix}_file_mtime"] = stats["mtime"]
    row[f"{prefix}_sha256_16"] = stats["sha256_16"]


def _file_stats(path: Path) -> dict[str, object]:
    if not path.exists() or not path.is_file():
        return {"size_bytes": 0, "mtime": "", "sha256_16": ""}
    stat = path.stat()
    return {
        "size_bytes": int(stat.st_size),
        "mtime": pd.Timestamp(stat.st_mtime, unit="s", tz="UTC").isoformat(),
        "sha256_16": _sha256_16(path),
    }


def _sha256_16(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()[:16]


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
    research = slice_window(data, cfg.windows.training_start, cfg.windows.validation_end)
    training_expected = _expected_bar_count(cfg.windows.training_start, cfg.windows.training_end, cfg.bar_hours)
    validation_expected = _expected_bar_count(cfg.windows.validation_start, cfg.windows.validation_end, cfg.bar_hours)
    research_expected = _expected_bar_count(cfg.windows.training_start, cfg.windows.validation_end, cfg.bar_hours)
    return {
        "research_bars": len(research),
        "research_expected_bars": research_expected,
        "research_coverage_ratio": _coverage_ratio(len(research), research_expected),
        "training_bars": len(training),
        "training_expected_bars": training_expected,
        "training_coverage_ratio": _coverage_ratio(len(training), training_expected),
        "training_missing_bars": max(training_expected - len(training), 0),
        "validation_bars": len(validation),
        "validation_expected_bars": validation_expected,
        "validation_coverage_ratio": _coverage_ratio(len(validation), validation_expected),
        "validation_missing_bars": max(validation_expected - len(validation), 0),
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
    if start and _utc_timestamp(start) < index_min:
        return False
    if end and _utc_timestamp(end) - pd.Timedelta(hours=bar_hours) > index_max:
        return False
    return True


def _expected_bar_count(start: str | None, end: str | None, bar_hours: int) -> int:
    if not start or not end:
        return 0
    start_ts = _utc_timestamp(start)
    end_ts = _utc_timestamp(end)
    last_ts = end_ts - pd.Timedelta(hours=bar_hours)
    if last_ts < start_ts:
        return 0
    return len(pd.date_range(start_ts, last_ts, freq=f"{bar_hours}h", tz="UTC"))


def _coverage_ratio(actual: int, expected: int) -> float:
    if expected <= 0:
        return 0.0
    return round(min(float(actual) / float(expected), 1.0), 6)


def _funding_quality_stats(
    funding: pd.DataFrame,
    coverage_index: pd.DatetimeIndex,
    start: str | None,
    end: str | None,
) -> dict[str, object]:
    if len(coverage_index) == 0:
        return {
            "funding_alignment_coverage": 0.0,
            "funding_expected_observations": 0,
            "funding_observations_in_window": 0,
            "funding_raw_coverage": 0.0,
            "funding_max_staleness_hours": 0.0,
        }
    start_ts = _utc_timestamp(start) if start else coverage_index.min()
    end_ts = _utc_timestamp(end) if end else coverage_index.max() + pd.Timedelta(hours=4)
    expected_funding = _expected_bar_count(str(start_ts), str(end_ts), 8)
    funding_in_window = funding[(funding.index >= start_ts) & (funding.index < end_ts)]

    bars = pd.DataFrame({"bar_ts": pd.DatetimeIndex(coverage_index).sort_values()})
    events = pd.DataFrame({"funding_ts": pd.DatetimeIndex(funding.index).sort_values()})
    merged = pd.merge_asof(bars, events, left_on="bar_ts", right_on="funding_ts", direction="backward")
    has_funding = merged["funding_ts"].notna()
    staleness = (merged.loc[has_funding, "bar_ts"] - merged.loc[has_funding, "funding_ts"]).dt.total_seconds().div(3600)
    return {
        "funding_alignment_coverage": round(float(has_funding.mean()), 6),
        "funding_expected_observations": expected_funding,
        "funding_observations_in_window": int(len(funding_in_window)),
        "funding_raw_coverage": _coverage_ratio(len(funding_in_window), expected_funding),
        "funding_max_staleness_hours": round(float(staleness.max()), 6) if not staleness.empty else 0.0,
    }


def _utc_timestamp(value: object) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        return ts.tz_localize("UTC")
    return ts.tz_convert("UTC")


def _asset_config_from_template(raw: dict[str, object], symbol: str, data_root: Path) -> dict[str, object]:
    out = dict(raw)
    out["symbol"] = symbol
    out["ohlcv_csv"] = (data_root / f"{symbol}_4h.csv").as_posix()
    out["funding_csv"] = (data_root / f"{symbol}_funding.csv").as_posix()
    if isinstance(out.get("prompt"), dict):
        prompt = dict(out["prompt"])
        system_prompt = str(prompt.get("system_prompt", ""))
        if system_prompt:
            prompt["system_prompt"] = system_prompt.replace("BTCUSDT", symbol)
        out["prompt"] = prompt
    return out


def _binance_usdm_symbol(symbol: str) -> str:
    if symbol.endswith("USDT"):
        return f"{symbol[:-4]}/USDT:USDT"
    return symbol


def _asset_config_yaml(raw: dict[str, object]) -> str:
    ordered_keys = ["symbol", "bar_hours", "ohlcv_csv", "funding_csv"]
    lines: list[str] = []
    for key in ordered_keys:
        if key in raw:
            lines.append(f"{key}: {raw[key]}")
    rest = {key: value for key, value in raw.items() if key not in ordered_keys}
    if rest:
        lines.append("")
        lines.append(yaml.dump(rest, Dumper=_ReadableConfigDumper, sort_keys=False, allow_unicode=True).rstrip())
    return "\n".join(lines) + "\n"


class _ReadableConfigDumper(yaml.SafeDumper):
    pass


def _represent_readable_string(dumper: _ReadableConfigDumper, value: str):
    style = "|" if "\n" in value else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)


_ReadableConfigDumper.add_representer(str, _represent_readable_string)
