from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class CostConfig:
    taker_bps: float = 4.0
    slippage_bps: float = 1.0
    funding_multiplier: float = 1.0


@dataclass(frozen=True)
class ExecutionConfig:
    delay_bars: int = 1
    max_exposure_abs: float = 1.0
    exposure_threshold: float = 0.15


@dataclass(frozen=True)
class WindowConfig:
    training_start: str | None = None
    training_end: str | None = None
    validation_start: str | None = None
    validation_end: str | None = None


@dataclass(frozen=True)
class MCTSConfig:
    exploration_weight: float = 1.4
    max_depth: int = 4
    proposal_count: int = 4
    eval_workers: int = 4
    max_formula_depth: int = 3
    max_formula_operators: int = 6
    complexity_penalty: float = 0.02
    fsa_top_k: int = 8
    api_cooldown_seconds: float = 30.0
    seed_formulas: list[str] = field(default_factory=lambda: ["neg(zscore(funding_rate,42))"])


@dataclass(frozen=True)
class FilterConfig:
    min_rank_ic: float = 0.01
    min_directional_win_rate: float = 0.49
    max_corr: float = 0.70
    min_cost_sharpe: float = 0.30
    min_validation_sharpe: float = 0.00
    min_halflife_bars: int = 1


@dataclass(frozen=True)
class PromptConfig:
    temperature: float = 0.75
    system_prompt: str = (
        "You are a senior quantitative alpha researcher at a top-tier crypto hedge fund. "
        "You design formulaic alpha factors for BTCUSDT 4h perpetual futures. "
        "You understand market microstructure, behavioral biases, funding rate dynamics, "
        "volatility regimes, and cross-sectional patterns in crypto markets."
    )
    description_min_length: int = 60


@dataclass(frozen=True)
class ProjectConfig:
    symbol: str
    bar_hours: int
    ohlcv_csv: Path
    funding_csv: Path
    costs: CostConfig
    execution: ExecutionConfig
    windows: WindowConfig
    mcts: MCTSConfig
    filter: FilterConfig = field(default_factory=FilterConfig)
    prompt: PromptConfig = field(default_factory=PromptConfig)


def _resolve_path(base: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (base / path).resolve()


def load_config(path: str | Path) -> ProjectConfig:
    cfg_path = Path(path).resolve()
    raw: dict[str, Any] = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    base = cfg_path.parent
    return ProjectConfig(
        symbol=str(raw.get("symbol", "BTCUSDT")),
        bar_hours=int(raw.get("bar_hours", 4)),
        ohlcv_csv=_resolve_path(base, raw["ohlcv_csv"]),
        funding_csv=_resolve_path(base, raw["funding_csv"]),
        costs=CostConfig(**(raw.get("costs") or {})),
        execution=ExecutionConfig(**(raw.get("execution") or {})),
        windows=WindowConfig(**(raw.get("windows") or {})),
        mcts=MCTSConfig(**(raw.get("mcts") or {})),
        filter=FilterConfig(**(raw.get("filter") or {})),
        prompt=PromptConfig(**(raw.get("prompt") or {})),
    )
