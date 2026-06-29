from __future__ import annotations

import json
import math
import os
import re
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .backtest import run_formula_backtest, signal_from_factor, summarize_ledger
from .config import CostConfig, ExecutionConfig
from .expression import evaluate_formula, parse_formula

FACTOR_ID_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
MARKET_COLUMNS = ["open", "high", "low", "close", "volume", "funding_rate"]
MAX_INITIAL_CAPITAL_USD = 1_000.0


class RuntimeConflictError(ValueError):
    """Raised when a hot-update generation is stale."""


@dataclass(frozen=True)
class FactorDefinition:
    factor_id: str
    formula: str
    description: str = ""
    enabled: bool = True
    exposure_threshold: float | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> FactorDefinition:
        factor_id = str(raw.get("factor_id", "")).strip()
        if not FACTOR_ID_PATTERN.fullmatch(factor_id):
            raise ValueError(
                "factor_id must start with a letter and contain at most 64 letters, digits, underscores, or hyphens"
            )
        try:
            formula = parse_formula(str(raw.get("formula", ""))).canonical()
        except (SyntaxError, ValueError) as exc:
            raise ValueError(f"Invalid formula for {factor_id}: {exc}") from exc
        threshold = raw.get("exposure_threshold")
        if threshold is not None:
            threshold = float(threshold)
            if not math.isfinite(threshold) or not 0.0 <= threshold < 1.0:
                raise ValueError("exposure_threshold must be finite and in [0, 1)")
        return cls(
            factor_id=factor_id,
            formula=formula,
            description=str(raw.get("description", "")).strip(),
            enabled=bool(raw.get("enabled", True)),
            exposure_threshold=threshold,
        )


@dataclass(frozen=True)
class StrategyComponent:
    factor_id: str
    weight: float = 1.0


@dataclass(frozen=True)
class AdverseExecution:
    latency_bars: int = 1
    max_exposure_abs: float = 1.0
    exposure_threshold: float = 0.15
    base_slippage_bps: float = 1.0
    slippage_jitter_bps: float = 2.0
    adverse_slippage_bps: float = 3.0
    signal_noise_std: float = 0.05
    fill_probability: float = 0.98
    seed: int = 11

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> AdverseExecution:
        try:
            model = cls(**(raw or {}))
        except TypeError as exc:
            raise ValueError(f"Invalid execution_model: {exc}") from exc
        if model.latency_bars < 0:
            raise ValueError("latency_bars must not be negative")
        if not 0.0 < model.max_exposure_abs <= 1.0:
            raise ValueError("max_exposure_abs must be in (0, 1]")
        if not 0.0 <= model.exposure_threshold < 1.0:
            raise ValueError("exposure_threshold must be in [0, 1)")
        for name in ("base_slippage_bps", "slippage_jitter_bps", "adverse_slippage_bps", "signal_noise_std"):
            value = float(getattr(model, name))
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and non-negative")
        if not 0.0 <= model.fill_probability <= 1.0:
            raise ValueError("fill_probability must be in [0, 1]")
        return model


@dataclass(frozen=True)
class StrategyDefinition:
    strategy_id: str
    components: tuple[StrategyComponent, ...]
    initial_capital_usd: float = MAX_INITIAL_CAPITAL_USD
    description: str = ""
    enabled: bool = True
    execution_model: AdverseExecution = AdverseExecution()

    @classmethod
    def from_dict(cls, raw: dict[str, Any], factor_ids: set[str]) -> StrategyDefinition:
        strategy_id = str(raw.get("strategy_id", "")).strip()
        if not FACTOR_ID_PATTERN.fullmatch(strategy_id):
            raise ValueError(
                "strategy_id must start with a letter and contain at most 64 letters, digits, underscores, or hyphens"
            )
        raw_components = raw.get("components")
        if not isinstance(raw_components, list) or not raw_components:
            raise ValueError(f"Strategy {strategy_id} must contain at least one component")
        components = []
        for item in raw_components:
            factor_id = str(item.get("factor_id", "")).strip()
            if factor_id not in factor_ids:
                raise ValueError(f"Strategy {strategy_id} references unknown factor_id {factor_id}")
            weight = float(item.get("weight", 1.0))
            if not math.isfinite(weight) or weight == 0.0:
                raise ValueError("Strategy component weights must be finite and non-zero")
            components.append(StrategyComponent(factor_id=factor_id, weight=weight))
        if len({item.factor_id for item in components}) != len(components):
            raise ValueError(f"Strategy {strategy_id} contains duplicate factor components")
        capital = float(raw.get("initial_capital_usd", MAX_INITIAL_CAPITAL_USD))
        if not math.isfinite(capital) or not 0.0 < capital <= MAX_INITIAL_CAPITAL_USD:
            raise ValueError(f"initial_capital_usd must be in (0, {MAX_INITIAL_CAPITAL_USD:.0f}]")
        return cls(
            strategy_id=strategy_id,
            components=tuple(components),
            initial_capital_usd=capital,
            description=str(raw.get("description", "")).strip(),
            enabled=bool(raw.get("enabled", True)),
            execution_model=AdverseExecution.from_dict(raw.get("execution_model")),
        )


class FactorRuntime:
    """Thread-safe, deterministic factor execution without research or trading capabilities."""

    def __init__(
        self,
        factors_path: str | Path,
        *,
        costs: CostConfig | None = None,
        execution: ExecutionConfig | None = None,
        bar_hours: int = 4,
        max_bars: int = 5_000,
    ) -> None:
        if bar_hours <= 0:
            raise ValueError("bar_hours must be positive")
        if max_bars < 100:
            raise ValueError("max_bars must be at least 100")
        self.factors_path = Path(factors_path)
        self.costs = costs or CostConfig()
        self.execution = execution or ExecutionConfig()
        self.bar_hours = int(bar_hours)
        self.max_bars = int(max_bars)
        self._lock = threading.RLock()
        self._data = pd.DataFrame(columns=MARKET_COLUMNS, dtype=float)
        self._data.index = pd.DatetimeIndex([], name="timestamp", tz="UTC")
        self._factors: tuple[FactorDefinition, ...] = ()
        self._strategies: tuple[StrategyDefinition, ...] = ()
        self._generation = 0

    @property
    def generation(self) -> int:
        with self._lock:
            return self._generation

    def load(self) -> dict[str, Any]:
        raw = json.loads(self.factors_path.read_text(encoding="utf-8"))
        factors = raw.get("factors")
        if not isinstance(factors, list):
            raise ValueError("Factor file must contain a factors list")
        strategies = raw.get("strategies", [])
        if not isinstance(strategies, list):
            raise ValueError("Factor file strategies must be a list")
        definitions, strategy_definitions = self._validate_config_batch(factors, strategies)
        generation = int(raw.get("generation", 0))
        if generation < 0:
            raise ValueError("generation must not be negative")
        with self._lock:
            self._factors = definitions
            self._strategies = strategy_definitions
            self._generation = generation
        return self.factor_manifest()

    def replace_factors(
        self,
        raw_factors: list[dict[str, Any]],
        *,
        expected_generation: int,
    ) -> dict[str, Any]:
        with self._lock:
            raw_strategies = [_strategy_to_dict(item) for item in self._strategies]
        return self.replace_config(
            raw_factors,
            raw_strategies,
            expected_generation=expected_generation,
        )

    def replace_config(
        self,
        raw_factors: list[dict[str, Any]],
        raw_strategies: list[dict[str, Any]],
        *,
        expected_generation: int,
    ) -> dict[str, Any]:
        definitions, strategy_definitions = self._validate_config_batch(raw_factors, raw_strategies)
        with self._lock:
            if expected_generation != self._generation:
                raise RuntimeConflictError(
                    f"Generation conflict: expected {expected_generation}, current {self._generation}"
                )
            next_generation = self._generation + 1
            payload = {
                "generation": next_generation,
                "factors": [asdict(item) for item in definitions],
                "strategies": [_strategy_to_dict(item) for item in strategy_definitions],
            }
            _atomic_write_json(self.factors_path, payload)
            self._factors = definitions
            self._strategies = strategy_definitions
            self._generation = next_generation
        return self.factor_manifest()

    def reload(self, *, expected_generation: int) -> dict[str, Any]:
        raw = json.loads(self.factors_path.read_text(encoding="utf-8"))
        factors = raw.get("factors")
        if not isinstance(factors, list):
            raise ValueError("Factor file must contain a factors list")
        strategies = raw.get("strategies", [])
        if not isinstance(strategies, list):
            raise ValueError("Factor file strategies must be a list")
        return self.replace_config(factors, strategies, expected_generation=expected_generation)

    def ingest(self, raw_bars: list[dict[str, Any]]) -> dict[str, Any]:
        if not raw_bars:
            raise ValueError("At least one market bar is required")
        incoming = pd.DataFrame([_validated_bar(item) for item in raw_bars]).set_index("timestamp")
        with self._lock:
            combined = pd.concat([self._data, incoming])
            combined = combined[~combined.index.duplicated(keep="last")].sort_index()
            self._data = combined.tail(self.max_bars).astype(float)
            latest = self._data.index[-1]
            count = len(self._data)
        return {
            "accepted": len(incoming),
            "stored_bars": count,
            "latest_timestamp": latest.isoformat(),
            "generation": self.generation,
        }

    def factor_manifest(self) -> dict[str, Any]:
        with self._lock:
            return {
                "generation": self._generation,
                "factors": [asdict(item) for item in self._factors],
                "strategies": [_strategy_to_dict(item) for item in self._strategies],
            }

    def health(self) -> dict[str, Any]:
        with self._lock:
            latest = self._data.index[-1].isoformat() if len(self._data) else None
            return {
                "status": "ok",
                "generation": self._generation,
                "factor_count": len(self._factors),
                "strategy_count": len(self._strategies),
                "stored_bars": len(self._data),
                "latest_timestamp": latest,
            }

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            data = self._data.copy()
            factors = self._factors
            strategies = self._strategies
            generation = self._generation
        rows = [self._factor_snapshot(item, data) for item in factors if item.enabled]
        factor_map = {item.factor_id: item for item in factors if item.enabled}
        strategy_rows = [
            self._strategy_snapshot(item, factor_map, data)
            for item in strategies
            if item.enabled and all(component.factor_id in factor_map for component in item.components)
        ]
        return {
            "generation": generation,
            "timestamp": data.index[-1].isoformat() if len(data) else None,
            "stored_bars": len(data),
            "factors": rows,
            "strategies": strategy_rows,
        }

    def _validate_config_batch(
        self,
        raw_factors: list[dict[str, Any]],
        raw_strategies: list[dict[str, Any]],
    ) -> tuple[tuple[FactorDefinition, ...], tuple[StrategyDefinition, ...]]:
        definitions = tuple(FactorDefinition.from_dict(item) for item in raw_factors)
        ids = [item.factor_id for item in definitions]
        if len(ids) != len(set(ids)):
            raise ValueError("factor_id values must be unique")
        strategies = tuple(StrategyDefinition.from_dict(item, set(ids)) for item in raw_strategies)
        strategy_ids = [item.strategy_id for item in strategies]
        if len(strategy_ids) != len(set(strategy_ids)):
            raise ValueError("strategy_id values must be unique")
        with self._lock:
            data = self._data.copy()
        if len(data):
            for item in definitions:
                evaluate_formula(item.formula, data)
        return definitions, strategies

    def _factor_snapshot(self, factor: FactorDefinition, data: pd.DataFrame) -> dict[str, Any]:
        if data.empty:
            return {
                "factor_id": factor.factor_id,
                "formula": factor.formula,
                "description": factor.description,
                "factor_value": None,
                "target_signal": 0.0,
                "executed_exposure": 0.0,
                "metrics": {},
            }
        threshold = (
            factor.exposure_threshold if factor.exposure_threshold is not None else self.execution.exposure_threshold
        )
        execution = ExecutionConfig(
            delay_bars=self.execution.delay_bars,
            max_exposure_abs=self.execution.max_exposure_abs,
            exposure_threshold=threshold,
        )
        values = evaluate_formula(factor.formula, data)
        signals = signal_from_factor(values, threshold)
        ledger = run_formula_backtest(data, factor.formula, self.costs, execution)
        latest_value = values.iloc[-1]
        return {
            "factor_id": factor.factor_id,
            "formula": factor.formula,
            "description": factor.description,
            "factor_value": _finite_or_none(latest_value),
            "target_signal": float(signals.iloc[-1]),
            "executed_exposure": float(ledger["exposure"].iloc[-1]),
            "close": float(data["close"].iloc[-1]),
            "metrics": {key: _finite_or_none(value) for key, value in summarize_ledger(ledger, self.bar_hours).items()},
        }

    def _strategy_snapshot(
        self,
        strategy: StrategyDefinition,
        factors: dict[str, FactorDefinition],
        data: pd.DataFrame,
    ) -> dict[str, Any]:
        if data.empty:
            return {
                "strategy_id": strategy.strategy_id,
                "mode": "single_factor" if len(strategy.components) == 1 else "multi_factor",
                "initial_capital_usd": strategy.initial_capital_usd,
                "equity_usd": strategy.initial_capital_usd,
                "pnl_usd": 0.0,
                "metrics": {},
            }
        ledger = _simulate_strategy(data, strategy, factors, self.costs, self.execution.exposure_threshold)
        metrics = summarize_ledger(ledger, self.bar_hours)
        equity = strategy.initial_capital_usd * (1.0 + ledger["r_net"]).cumprod()
        return {
            "strategy_id": strategy.strategy_id,
            "description": strategy.description,
            "mode": "single_factor" if len(strategy.components) == 1 else "multi_factor",
            "components": [asdict(item) for item in strategy.components],
            "initial_capital_usd": strategy.initial_capital_usd,
            "equity_usd": _finite_or_none(equity.iloc[-1]),
            "pnl_usd": _finite_or_none(equity.iloc[-1] - strategy.initial_capital_usd),
            "return_pct": _finite_or_none((equity.iloc[-1] / strategy.initial_capital_usd - 1.0) * 100.0),
            "target_exposure": float(ledger["target_exposure"].iloc[-1]),
            "executed_exposure": float(ledger["exposure"].iloc[-1]),
            "missed_rebalances": int(ledger["missed_rebalance"].sum()),
            "execution_cost_usd": _finite_or_none(
                strategy.initial_capital_usd * (ledger["c_fee"] + ledger["c_slip"]).sum()
            ),
            "metrics": {key: _finite_or_none(value) for key, value in metrics.items()},
            "execution_model": asdict(strategy.execution_model),
        }


def _simulate_strategy(
    data: pd.DataFrame,
    strategy: StrategyDefinition,
    factors: dict[str, FactorDefinition],
    costs: CostConfig,
    default_threshold: float,
) -> pd.DataFrame:
    model = strategy.execution_model
    rng = np.random.default_rng(model.seed)
    combined = pd.Series(0.0, index=data.index)
    has_valid_factor = pd.Series(False, index=data.index)
    weight_total = sum(abs(component.weight) for component in strategy.components)
    for component in strategy.components:
        factor = factors[component.factor_id]
        threshold = factor.exposure_threshold if factor.exposure_threshold is not None else default_threshold
        values = evaluate_formula(factor.formula, data)
        has_valid_factor |= values.notna()
        combined += component.weight * signal_from_factor(values, threshold)
    combined /= weight_total
    combined[~has_valid_factor] = np.nan
    noisy_score = combined + pd.Series(rng.normal(0.0, model.signal_noise_std, len(data)), index=data.index)
    target = pd.Series(0.0, index=data.index)
    target[noisy_score > model.exposure_threshold] = model.max_exposure_abs
    target[noisy_score < -model.exposure_threshold] = -model.max_exposure_abs
    requested = target.shift(model.latency_bars).fillna(0.0)

    exposure_values: list[float] = []
    missed: list[float] = []
    current = 0.0
    fill_draws = rng.random(len(data))
    for desired, fill_draw in zip(requested.to_numpy(), fill_draws, strict=True):
        changed = not math.isclose(float(desired), current)
        was_missed = changed and fill_draw > model.fill_probability
        if changed and not was_missed:
            current = float(desired)
        exposure_values.append(current)
        missed.append(float(was_missed))
    exposure = pd.Series(exposure_values, index=data.index)
    delta = exposure.diff().fillna(exposure)
    turnover = delta.abs()
    slippage_bps = (
        model.base_slippage_bps
        + model.adverse_slippage_bps
        + np.abs(rng.normal(0.0, model.slippage_jitter_bps, len(data)))
    )
    close = data["close"].astype(float)
    r_mkt = close.pct_change().fillna(0.0)
    c_fee = turnover * costs.taker_bps / 10_000.0
    c_slip = turnover * pd.Series(slippage_bps, index=data.index) / 10_000.0
    c_fund = exposure * data["funding_rate"].fillna(0.0) * 0.5 * costs.funding_multiplier
    r_raw = exposure * r_mkt
    r_net = (r_raw - c_fee - c_slip - c_fund).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    return pd.DataFrame(
        {
            "factor": combined,
            "target_exposure": target,
            "exposure": exposure,
            "delta_exposure": delta,
            "missed_rebalance": missed,
            "r_mkt": r_mkt,
            "r_raw": r_raw,
            "c_fee": c_fee,
            "c_slip": c_slip,
            "c_fund": c_fund,
            "r_net": r_net,
        },
        index=data.index,
    )


def _validated_bar(raw: dict[str, Any]) -> dict[str, Any]:
    try:
        timestamp = pd.Timestamp(raw["timestamp"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("timestamp must be an ISO-8601 value") from exc
    if timestamp.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    timestamp = timestamp.tz_convert("UTC")
    values: dict[str, float] = {}
    for column in MARKET_COLUMNS:
        try:
            value = float(raw[column])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"{column} must be numeric") from exc
        if not math.isfinite(value):
            raise ValueError(f"{column} must be finite")
        values[column] = value
    if values["volume"] < 0:
        raise ValueError("volume must not be negative")
    if values["high"] < max(values["open"], values["close"], values["low"]):
        raise ValueError("high must be greater than or equal to open, close, and low")
    if values["low"] > min(values["open"], values["close"], values["high"]):
        raise ValueError("low must be less than or equal to open, close, and high")
    return {"timestamp": timestamp, **values}


def _finite_or_none(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def _strategy_to_dict(strategy: StrategyDefinition) -> dict[str, Any]:
    return {
        "strategy_id": strategy.strategy_id,
        "components": [asdict(item) for item in strategy.components],
        "initial_capital_usd": strategy.initial_capital_usd,
        "description": strategy.description,
        "enabled": strategy.enabled,
        "execution_model": asdict(strategy.execution_model),
    }


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()
