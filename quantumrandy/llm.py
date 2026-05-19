from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from .expression import OPERATORS, validate_formula_shape
from .fsa import violates_forbidden
from .proposals import LocalProposalEngine

try:
    from .config import PromptConfig
except ImportError:
    PromptConfig = None  # type: ignore[assignment]

DESCRIPTION_MIN_LENGTH = 60
ECON_KEYWORDS = [
    "momentum", "reversal", "mean reversion", "trend", "volatility",
    "volume", "funding", "carry", "premium", "discount", "pressure",
    "oversold", "overbought", "divergence", "convergence", "spread",
    "liquidity", "flow", "sentiment", "risk", "arbitrage", "supply",
    "demand", "breakout", "range", "support", "resistance",
    "资金", "动量", "反转", "波动", "趋势", "费率", "溢价",
]


@dataclass(frozen=True)
class LLMSettings:
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    timeout_seconds: int = 120
    max_retries: int = 2
    retry_sleep_seconds: float = 3.0


class FormulaGenerator:
    def __init__(
        self,
        use_llm: bool = False,
        settings: LLMSettings | None = None,
        max_formula_depth: int = 4,
        max_formula_operators: int = 8,
        prompt_config: "PromptConfig | None" = None,
    ) -> None:
        _load_env_file()
        self.use_llm = use_llm
        self.settings = settings or LLMSettings(
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            timeout_seconds=int(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "120")),
            max_retries=int(os.getenv("DEEPSEEK_MAX_RETRIES", "2")),
        )
        self.local = LocalProposalEngine()
        self.events: list[dict[str, Any]] = []
        self.descriptions: dict[str, str] = {}
        self.max_formula_depth = max_formula_depth
        self.max_formula_operators = max_formula_operators
        self.prompt_config = prompt_config

    def propose(self, base_formula: str, dimension: str, count: int, forbidden: list[str]) -> list[str]:
        if self.use_llm and os.getenv("DEEPSEEK_API_KEY"):
            existing = list(self.descriptions.keys())[-20:]
            formulas, error, llm_detail = self._deepseek_propose(base_formula, dimension, count, forbidden, existing)
            if formulas:
                self.events.append(
                    {
                        "source": "deepseek",
                        "base_formula": base_formula,
                        "dimension": dimension,
                        "requested": count,
                        "accepted": len(formulas),
                        "error": None,
                        "llm_response_snippet": llm_detail.get("response_snippet", ""),
                        "llm_duration_s": llm_detail.get("duration_s", 0),
                    }
                )
                return formulas
            self.events.append(
                {
                    "source": "fallback",
                    "base_formula": base_formula,
                    "dimension": dimension,
                    "requested": count,
                    "accepted": 0,
                    "error": error or "DeepSeek returned no valid formulas.",
                    "llm_response_snippet": llm_detail.get("error_full", llm_detail.get("response_snippet", "")),
                    "llm_duration_s": llm_detail.get("duration_s", 0),
                }
            )
        elif self.use_llm and not os.getenv("DEEPSEEK_API_KEY"):
            self.events.append(
                {
                    "source": "fallback",
                    "base_formula": base_formula,
                    "dimension": dimension,
                    "requested": count,
                    "accepted": 0,
                    "error": "DEEPSEEK_API_KEY is not set.",
                }
            )
        formulas = []
        for formula in self.local.propose(base_formula, dimension, count, forbidden):
            try:
                canonical = validate_formula_shape(formula, self.max_formula_depth, self.max_formula_operators).canonical()
            except ValueError:
                continue
            self.descriptions.setdefault(canonical, _local_description(canonical, dimension))
            formulas.append(canonical)
        self.events.append(
            {
                "source": "local",
                "base_formula": base_formula,
                "dimension": dimension,
                "requested": count,
                "accepted": len(formulas),
                "error": None,
            }
        )
        return formulas

    def _deepseek_propose(self, base_formula: str, dimension: str, count: int, forbidden: list[str], existing: list[str] | None = None) -> tuple[list[str], str | None, dict]:
        detail: dict = {"response_snippet": "", "duration_s": 0}
        truncated_forbidden = forbidden[:5] if len(forbidden) > 5 else forbidden
        existing = existing or []
        pc = self.prompt_config
        desc_len = pc.description_min_length if pc else DESCRIPTION_MIN_LENGTH
        temp = pc.temperature if pc else 0.7
        system_prompt = (
            pc.system_prompt
            if pc
            else "You are a quant alpha research assistant. Output valid JSON with detailed economic explanations for each formula."
        )
        dim_hints = {
            "effectiveness": "aim for higher rank IC — consider momentum, trend-following, or funding-carry signals",
            "stability": "aim for smooth PnL with low drawdowns — consider mean-reversion at extremes, or vol-targeted signals",
            "turnover": "keep trading frequency low — use slower moving averages (sma/ema with 24-120 bar windows) or zscore with long lookbacks",
            "diversity": "explore unconventional combinations — correlate different fields (close vs volume, high-low range, funding_rate), use corr() or div() creatively",
            "overfit_risk": "keep it simple — prefer single-field transforms with one or two operators, avoid stacking many nested functions",
        }
        prompt = {
            "task": "Design novel crypto alpha factors for BTCUSDT 4h perpetual futures backtesting.",
            "base_formula": base_formula,
            "target_dimension": dimension,
            "dimension_hint": dim_hints.get(dimension, "improve this dimension"),
            "available_fields": {
                "open": "opening price",
                "high": "highest price in bar",
                "low": "lowest price in bar",
                "close": "closing price",
                "volume": "trading volume",
                "funding_rate": "perpetual funding rate (positive = longs pay shorts)",
            },
            "available_operators": sorted(OPERATORS),
            "operator_meanings": {
                "sma": "simple moving average — smooth trend",
                "ema": "exponential moving average — recent-weighted trend",
                "std": "standard deviation — volatility",
                "zscore": "normalize to mean 0, std 1 — mean-reversion indicator",
                "corr": "correlation between two series — regime/relationship change",
                "ret": "percentage return over N bars — momentum",
                "delta": "price difference over N bars — absolute momentum",
                "rank": "rolling percentile rank 0-1 — overbought/oversold relative to window",
                "delay": "lag series by N bars — avoid look-ahead bias or create lagged signals",
                "sign": "sign of series (+1/-1/0) — direction classifier",
                "rsi": "RSI indicator 0-100 — momentum oscillator, overbought>70, oversold<30",
                "div": "ratio — relative value or normalization",
                "neg": "negation — flip sign for inverse signals",
                "abs": "absolute value — magnitude only",
                "log": "natural log — compress extremes",
                "sqrt": "square root — dampen outliers",
                "min": "rolling minimum — support level",
                "max": "rolling maximum — resistance level",
            },
            "avoid_subtrees": truncated_forbidden,
            "already_in_zoo": existing[-10:],
            "requirements": [
                f"Return valid JSON: {{\"candidates\":[{{\"formula\":\"<DSL expression>\",\"description\":\"<economic rationale>\"}}]}}.",
                f"Max formula depth {self.max_formula_depth}, max {self.max_formula_operators} operators. Each description MUST be >= {desc_len} characters.",
                "Description must cite specific market behaviors: momentum continuation / mean reversion / funding pressure / volatility regime / liquidity dynamics.",
                "Prefer interpretable structures. Do NOT stack meaningless transforms like log(abs(exp(...))). Each operator must serve an economic purpose.",
                "Generate formulas that are DIFFERENT from already_in_zoo. Vary the operators, fields, and window lengths.",
            ],
        }
        user_msg = json.dumps(prompt, ensure_ascii=False)
        detail["prompt_chars"] = len(user_msg)
        detail["forbidden_count"] = len(forbidden)
        detail["forbidden_sent"] = len(truncated_forbidden)
        try:
            t0 = time.time()
            content = call_deepseek(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
                settings=self.settings,
                temperature=temp,
            )
            detail["duration_s"] = round(time.time() - t0, 2)
            detail["response_snippet"] = content[:400]
            data = _extract_json(content)
        except Exception as exc:
            detail["error_full"] = str(exc)[:300]
            return [], str(exc), detail

        out: list[str] = []
        raw_candidates = data.get("candidates")
        if raw_candidates is None:
            raw_candidates = [{"formula": formula, "description": ""} for formula in data.get("formulas", [])]
        rejected = []
        for item in raw_candidates:
            formula = item.get("formula") if isinstance(item, dict) else str(item)
            description = item.get("description", "") if isinstance(item, dict) else ""
            try:
                canonical = validate_formula_shape(str(formula), self.max_formula_depth, self.max_formula_operators).canonical()
            except ValueError as exc:
                rejected.append({"formula": formula, "reason": str(exc)})
                continue
            desc_text = str(description).strip()
            if len(desc_text) < DESCRIPTION_MIN_LENGTH:
                rejected.append({"formula": canonical, "reason": f"description too short ({len(desc_text)} < {DESCRIPTION_MIN_LENGTH} chars)"})
                continue
            if not _has_economic_rationale(desc_text):
                rejected.append({"formula": canonical, "reason": "description lacks economic rationale"})
                continue
            if not violates_forbidden(canonical, forbidden):
                self.descriptions[canonical] = desc_text
                out.append(canonical)
            else:
                rejected.append({"formula": canonical, "reason": "violates forbidden subtree"})
            if len(out) >= count:
                break
        if rejected:
            self.events.append({"source": "validator", "accepted": len(out), "rejected": rejected[:20]})
        if not out:
            reject_summary = "; ".join(f"{r['formula'][:60]}: {r['reason']}" for r in rejected[:5])
            return [], f"All {len(rejected)} DeepSeek formulas rejected: {reject_summary}", detail
        return out, None, detail


def call_deepseek(messages: list[dict[str, str]], settings: LLMSettings | None = None, temperature: float = 0.2) -> str:
    _load_env_file()
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not set.")
    settings = settings or LLMSettings(
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        timeout_seconds=int(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "120")),
        max_retries=int(os.getenv("DEEPSEEK_MAX_RETRIES", "2")),
    )
    connect_timeout = 15.0
    read_timeout = float(settings.timeout_seconds)
    last_error: Exception | None = None
    last_error_detail: str = ""
    for attempt in range(settings.max_retries + 1):
        try:
            resp = requests.post(
                f"{settings.base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.model,
                    "messages": messages,
                    "temperature": temperature,
                },
                timeout=(connect_timeout, read_timeout),
            )
            try:
                resp.raise_for_status()
            except requests.HTTPError as exc:
                raise RuntimeError(f"DeepSeek HTTP {resp.status_code}: {resp.text[:500]}") from exc
            payload = resp.json()
            return payload["choices"][0]["message"]["content"]
        except requests.ConnectionError as exc:
            last_error = exc
            last_error_detail = f"ConnectionError: {exc}"
            if attempt >= settings.max_retries:
                break
            time.sleep(settings.retry_sleep_seconds * (attempt + 1))
        except requests.Timeout as exc:
            last_error = exc
            last_error_detail = f"Timeout after connect={connect_timeout}s / read={read_timeout}s"
            if attempt >= settings.max_retries:
                break
            time.sleep(settings.retry_sleep_seconds * (attempt + 1))
        except RuntimeError as exc:
            last_error = exc
            last_error_detail = str(exc)
            if attempt >= settings.max_retries:
                break
            time.sleep(settings.retry_sleep_seconds * (attempt + 1))
    raise RuntimeError(f"DeepSeek request failed after {settings.max_retries + 1} attempts: {last_error_detail}")


def _extract_json(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        idx = text.find("{")
        if idx < 0:
            raise
        obj, _ = json.JSONDecoder().raw_decode(text[idx:])
        return obj


def _load_env_file() -> None:
    for path in [Path.cwd() / ".env", Path(__file__).resolve().parents[1] / ".env"]:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _has_economic_rationale(description: str) -> bool:
    desc_lower = description.lower()
    return any(kw in desc_lower for kw in ECON_KEYWORDS)


def _local_description(formula: str, dimension: str) -> str:
    return (
        f"Local fallback candidate for {dimension}: {formula}. "
        "It uses simple price, volume, or funding transformations to capture interpretable crypto momentum, reversal, volatility, or carry pressure."
    )
