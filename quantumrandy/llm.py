from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from .candidate_selector import load_candidate_selector_prompt_context
from .expression import OPERATORS, validate_formula_shape
from .failure_memory import load_failure_prompt_context
from .fsa import violates_forbidden
from .proposals import LocalProposalEngine

try:
    from .config import LLMConfig, PromptConfig
except ImportError:
    LLMConfig = None  # type: ignore[assignment]
    PromptConfig = None  # type: ignore[assignment]

DESCRIPTION_MIN_LENGTH = 60
PROPOSAL_SCHEMA_FIELDS = [
    "hypothesis",
    "expected_edge",
    "expected_failure_mode",
    "rewrite_plan_if_killed",
]
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
    base_url: str = ""
    model: str = ""
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
        llm_config: "LLMConfig | None" = None,
    ) -> None:
        _load_env_file()
        if llm_config is not None and llm_config.use_proxy:
            os.environ.setdefault("LLM_PROXY", f"http://{llm_config.proxy_host}:{llm_config.proxy_port}")
        self.use_llm = use_llm
        self.settings = _settings_with_env(settings)
        self.local = LocalProposalEngine()
        self.events: list[dict[str, Any]] = []
        self.descriptions: dict[str, str] = {}
        self.proposal_metadata: dict[str, dict[str, str]] = {}
        self.max_formula_depth = max_formula_depth
        self.max_formula_operators = max_formula_operators
        self.prompt_config = prompt_config
        self.failure_prompt_context = load_failure_prompt_context(
            prompt_config.failure_memory_path if prompt_config else None,
            max_examples=prompt_config.failure_memory_examples if prompt_config else 0,
            max_clusters=prompt_config.failure_memory_clusters if prompt_config else 0,
        )
        self.candidate_selector_context = load_candidate_selector_prompt_context(
            prompt_config.candidate_selector_path if prompt_config else None,
            max_rewrite_targets=prompt_config.candidate_selector_rewrite_targets if prompt_config else 0,
            max_evidence_gaps=prompt_config.candidate_selector_evidence_gaps if prompt_config else 0,
            max_clusters=prompt_config.candidate_selector_clusters if prompt_config else 0,
        )

    def propose(self, base_formula: str, dimension: str, count: int, forbidden: list[str]) -> list[str]:
        if self.use_llm and _llm_api_key():
            existing = list(self.descriptions.keys())[-20:]
            formulas, error, llm_detail = self._llm_propose(base_formula, dimension, count, forbidden, existing)
            if formulas:
                self.events.append(
                    {
                        "source": "llm",
                        "base_formula": base_formula,
                        "dimension": dimension,
                        "requested": count,
                        "accepted": len(formulas),
                        "error": None,
                        "llm_response_snippet": llm_detail.get("response_snippet", ""),
                        "llm_duration_s": llm_detail.get("duration_s", 0),
                        "failure_memory_examples": llm_detail.get("failure_memory_examples", 0),
                        "failure_memory_clusters": llm_detail.get("failure_memory_clusters", 0),
                        "candidate_selector_rewrite_targets": llm_detail.get(
                            "candidate_selector_rewrite_targets", 0
                        ),
                        "candidate_selector_evidence_gaps": llm_detail.get("candidate_selector_evidence_gaps", 0),
                        "candidate_selector_clusters": llm_detail.get("candidate_selector_clusters", 0),
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
                    "error": error or "LLM returned no valid formulas.",
                    "llm_response_snippet": llm_detail.get("error_full", llm_detail.get("response_snippet", "")),
                    "llm_duration_s": llm_detail.get("duration_s", 0),
                }
            )
        elif self.use_llm and not _llm_api_key():
            self.events.append(
                {
                    "source": "fallback",
                    "base_formula": base_formula,
                    "dimension": dimension,
                    "requested": count,
                    "accepted": 0,
                    "error": "LLM_API_KEY is not set.",
                }
            )
        formulas = []
        for formula in self.local.propose(base_formula, dimension, count, forbidden):
            try:
                canonical = validate_formula_shape(formula, self.max_formula_depth, self.max_formula_operators).canonical()
            except ValueError:
                continue
            self.descriptions.setdefault(canonical, _local_description(canonical, dimension))
            self.proposal_metadata.setdefault(canonical, _local_metadata(canonical, dimension))
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

    def rewrite(
        self,
        formula: str,
        failed_gates: list[str],
        failure_detail: dict[str, Any],
        count: int,
        forbidden: list[str],
        disallowed_formulas: list[str] | None = None,
        allow_local_fallback: bool = True,
    ) -> list[str]:
        disallowed = set(disallowed_formulas or [])
        disallowed.add(formula)
        if self.use_llm and _llm_api_key():
            existing = list(self.descriptions.keys())[-20:]
            formulas, error, llm_detail = self._llm_rewrite(
                formula,
                failed_gates,
                failure_detail,
                count,
                forbidden,
                existing,
                disallowed,
            )
            if formulas:
                self.events.append(
                    {
                        "source": "llm_rewrite",
                        "base_formula": formula,
                        "failed_gates": failed_gates,
                        "requested": count,
                        "accepted": len(formulas),
                        "error": None,
                        "llm_response_snippet": llm_detail.get("response_snippet", ""),
                        "llm_duration_s": llm_detail.get("duration_s", 0),
                        "failure_memory_examples": llm_detail.get("failure_memory_examples", 0),
                        "failure_memory_clusters": llm_detail.get("failure_memory_clusters", 0),
                        "candidate_selector_rewrite_targets": llm_detail.get(
                            "candidate_selector_rewrite_targets", 0
                        ),
                        "candidate_selector_evidence_gaps": llm_detail.get("candidate_selector_evidence_gaps", 0),
                        "candidate_selector_clusters": llm_detail.get("candidate_selector_clusters", 0),
                        "disallowed_formula_count": llm_detail.get("disallowed_formula_count", 0),
                    }
                )
                if not allow_local_fallback:
                    for candidate in formulas:
                        self.proposal_metadata.setdefault(candidate, {})["generation_source"] = "llm_rewrite"
                    return formulas[:count]
                return self._fill_rewrite_candidates(
                    formulas,
                    formula,
                    failed_gates,
                    count,
                    forbidden,
                    disallowed,
                )
            self.events.append(
                {
                    "source": "rewrite_fallback",
                    "base_formula": formula,
                    "failed_gates": failed_gates,
                    "requested": count,
                    "accepted": 0,
                    "error": error or "LLM rewrite returned no valid formulas.",
                    "llm_response_snippet": llm_detail.get("error_full", llm_detail.get("response_snippet", "")),
                    "llm_duration_s": llm_detail.get("duration_s", 0),
                    "disallowed_formula_count": llm_detail.get("disallowed_formula_count", 0),
                }
            )

        if not allow_local_fallback:
            return []
        return self._fill_rewrite_candidates([], formula, failed_gates, count, forbidden, disallowed)

    def _fill_rewrite_candidates(
        self,
        formulas: list[str],
        base_formula: str,
        failed_gates: list[str],
        count: int,
        forbidden: list[str],
        disallowed_formulas: set[str] | None = None,
    ) -> list[str]:
        disallowed_formulas = disallowed_formulas or {base_formula}
        out = list(formulas)
        for formula in out:
            self.proposal_metadata.setdefault(formula, {})["generation_source"] = "llm_rewrite"
        need_non_funding = len(out) < count and any(_is_pure_funding_formula(item) for item in out)
        local_added: list[str] = []
        local_requested = max(count * 4, count)
        for candidate in self.local.rewrite_for_failure(base_formula, failed_gates, local_requested, forbidden):
            if len(out) >= count:
                break
            try:
                canonical = validate_formula_shape(candidate, self.max_formula_depth, self.max_formula_operators).canonical()
            except ValueError:
                continue
            if canonical in disallowed_formulas:
                continue
            if canonical in out:
                continue
            if need_non_funding and _is_pure_funding_formula(canonical):
                continue
            self.descriptions.setdefault(canonical, _local_rewrite_description(canonical, base_formula, failed_gates))
            self.proposal_metadata.setdefault(canonical, _local_rewrite_metadata(canonical, base_formula, failed_gates))
            self.proposal_metadata[canonical]["generation_source"] = "local_rewrite"
            out.append(canonical)
            local_added.append(canonical)
        if local_added or not formulas:
            self.events.append(
                {
                    "source": "local_rewrite",
                    "base_formula": base_formula,
                    "failed_gates": failed_gates,
                    "requested": max(0, count - len(formulas)),
                    "accepted": len(local_added),
                    "error": None,
                    "disallowed_formula_count": len(disallowed_formulas),
                }
            )
        return out

    def _llm_propose(self, base_formula: str, dimension: str, count: int, forbidden: list[str], existing: list[str] | None = None) -> tuple[list[str], str | None, dict]:
        detail: dict = {"response_snippet": "", "duration_s": 0}
        truncated_forbidden = forbidden[:5] if len(forbidden) > 5 else forbidden
        existing = existing or []
        failure_context = self.failure_prompt_context
        failure_examples = failure_context.get("examples", [])
        failure_clusters = failure_context.get("clusters", [])
        selector_context = self.candidate_selector_context
        rewrite_targets = selector_context.get("rewrite_targets", [])
        evidence_gaps = selector_context.get("evidence_gaps", [])
        selector_clusters = selector_context.get("clusters", [])
        detail["failure_memory_examples"] = len(failure_examples)
        detail["failure_memory_clusters"] = len(failure_clusters)
        detail["candidate_selector_rewrite_targets"] = len(rewrite_targets)
        detail["candidate_selector_evidence_gaps"] = len(evidence_gaps)
        detail["candidate_selector_clusters"] = len(selector_clusters)
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
            "operator_expansion_notes": {
                "clip": "cap a series between two constants to limit extreme signal values",
                "winsorize": "rolling outlier cap at roughly three standard deviations",
                "decay_linear": "linearly weighted moving average with more weight on recent bars",
                "ts_argmax": "position of the rolling maximum within the lookback window",
                "ts_argmin": "position of the rolling minimum within the lookback window",
                "skew": "rolling skewness to detect asymmetric return or flow regimes",
                "kurtosis": "rolling kurtosis to detect fat-tailed or jumpy regimes",
            },
            "shape_constraints": _shape_constraints(self.max_formula_depth, self.max_formula_operators),
            "avoid_subtrees": truncated_forbidden,
            "failure_memory": {
                "source": failure_context.get("source", ""),
                "negative_examples": failure_examples,
                "failed_subtree_clusters": failure_clusters,
                "instruction": (
                    "Treat these as failed research memories. Do not copy their formulas or shared failed subtrees. "
                    "Use the failed gates and rewrite plans to propose structurally different, simpler, or better-smoothed candidates."
                ),
            },
            "multi_asset_candidate_evidence": {
                "source": selector_context.get("source", ""),
                "rewrite_targets": rewrite_targets,
                "evidence_gaps": evidence_gaps,
                "weak_cross_asset_clusters": selector_clusters,
                "instruction": (
                    "Treat rewrite_targets as evidence that related structures were BTC-local or weak across the "
                    "universe. Prefer candidates with economic rationale that could plausibly survive BTC, ETH, SOL, "
                    "BNB, and AVAX. Do not copy formulas in evidence_gaps until they have multi-asset evidence."
                ),
            },
            "already_in_zoo": existing[-10:],
            "requirements": [
                (
                    "Return valid JSON: "
                    "{\"candidates\":[{\"formula\":\"<DSL expression>\","
                    "\"description\":\"<economic rationale>\","
                    "\"hypothesis\":\"<market behavior being tested>\","
                    "\"expected_edge\":\"<why this should predict future returns>\","
                    "\"expected_failure_mode\":\"<likely reason it may fail>\","
                    "\"rewrite_plan_if_killed\":\"<how to revise after a failed gate>\"}]}. "
                    "The four schema-v2 fields are required for every candidate."
                ),
                (
                    f"Hard shape rule: max formula depth {self.max_formula_depth}, "
                    f"max {self.max_formula_operators} operators. Obey shape_constraints exactly; formulas that "
                    "violate them are rejected before backtesting."
                ),
                "Prefer 1-3 operator formulas. Before returning JSON, self-check every formula against max_depth and max_operators.",
                f"Each description MUST be >= {desc_len} characters.",
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
            content = call_llm(
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
            metadata = _proposal_metadata_from_item(item if isinstance(item, dict) else {})
            metadata["generation_source"] = "llm_rewrite"
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
                self.proposal_metadata[canonical] = metadata
                out.append(canonical)
            else:
                rejected.append({"formula": canonical, "reason": "violates forbidden subtree"})
            if len(out) >= count:
                break
        if rejected:
            self.events.append({"source": "validator", "accepted": len(out), "rejected": rejected[:20]})
        if not out:
            reject_summary = "; ".join(f"{r['formula'][:60]}: {r['reason']}" for r in rejected[:5])
            return [], f"All {len(rejected)} LLM formulas rejected: {reject_summary}", detail
        return out, None, detail

    def _llm_rewrite(
        self,
        formula: str,
        failed_gates: list[str],
        failure_detail: dict[str, Any],
        count: int,
        forbidden: list[str],
        existing: list[str] | None = None,
        disallowed_formulas: set[str] | None = None,
    ) -> tuple[list[str], str | None, dict]:
        detail: dict = {"response_snippet": "", "duration_s": 0}
        truncated_forbidden = forbidden[:5] if len(forbidden) > 5 else forbidden
        existing = existing or []
        disallowed_formulas = disallowed_formulas or {formula}
        disallowed_sent = sorted(disallowed_formulas)[:10]
        failure_context = self.failure_prompt_context
        failure_examples = failure_context.get("examples", [])
        failure_clusters = failure_context.get("clusters", [])
        selector_context = self.candidate_selector_context
        rewrite_targets = selector_context.get("rewrite_targets", [])
        evidence_gaps = selector_context.get("evidence_gaps", [])
        selector_clusters = selector_context.get("clusters", [])
        parent_selector_target = _matching_selector_target(formula, rewrite_targets)
        detail["failure_memory_examples"] = len(failure_examples)
        detail["failure_memory_clusters"] = len(failure_clusters)
        detail["candidate_selector_rewrite_targets"] = len(rewrite_targets)
        detail["candidate_selector_evidence_gaps"] = len(evidence_gaps)
        detail["candidate_selector_clusters"] = len(selector_clusters)
        pc = self.prompt_config
        desc_len = pc.description_min_length if pc else DESCRIPTION_MIN_LENGTH
        temp = pc.temperature if pc else 0.7
        system_prompt = (
            pc.system_prompt
            if pc
            else "You are a quant alpha research assistant. Output valid JSON with detailed economic explanations for each formula."
        )
        prompt = {
            "task": "Rewrite a failed crypto alpha factor into better candidates for BTCUSDT 4h perpetual futures.",
            "failed_formula": formula,
            "failed_gates": failed_gates,
            "failure_detail": _compact_failure_detail(failure_detail),
            "rewrite_objective": {
                "primary_goal": (
                    "Improve cross-asset robustness without sacrificing profitability. A useful rewrite should target "
                    "pass_rate_delta > 0 and mean_sharpe_delta >= 0 versus the parent when universe evidence is available."
                ),
                "profitability_gate": (
                    "Do not treat a higher cross-asset pass count as sufficient if mean Sharpe falls below the parent. "
                    "Normalized range, volatility, and liquidity-regime candidates need an explicit Sharpe/profitability rationale."
                ),
                "failure_mode_prediction": (
                    "For every candidate, use expected_failure_mode to predict its most likely cross-asset failure mode, "
                    "including which field family or asset regime may break it."
                ),
            },
            "gate_rewrite_guidance": _rewrite_guidance(failed_gates),
            "available_fields": {
                "open": "opening price",
                "high": "highest price in bar",
                "low": "lowest price in bar",
                "close": "closing price",
                "volume": "trading volume",
                "funding_rate": "perpetual funding rate",
            },
            "available_operators": sorted(OPERATORS),
            "shape_constraints": _shape_constraints(self.max_formula_depth, self.max_formula_operators),
            "avoid_subtrees": truncated_forbidden,
            "disallowed_exact_formulas": disallowed_sent,
            "already_in_zoo": existing[-10:],
            "failure_memory": {
                "source": failure_context.get("source", ""),
                "negative_examples": failure_examples,
                "failed_subtree_clusters": failure_clusters,
            },
            "multi_asset_candidate_evidence": {
                "source": selector_context.get("source", ""),
                "parent_selector_target_evidence": parent_selector_target,
                "rewrite_targets": rewrite_targets,
                "evidence_gaps": evidence_gaps,
                "weak_cross_asset_clusters": selector_clusters,
                "instruction": (
                    "Use this selector evidence to avoid BTC-only lucky patterns and to rewrite toward simpler "
                    "cross-asset robust structures. If the failed formula resembles a deprioritized target, change "
                    "the economic family rather than only changing windows."
                ),
            },
            "candidate_diversity": {
                "instruction": (
                    "Do not return a batch where every candidate is funding_rate-only. At most one candidate may be "
                    "a pure funding/carry transform. Include at least one volatility, range, volume, or liquidity-regime "
                    "candidate when generating multiple candidates."
                ),
                "funding_family_examples": [
                    "neg(zscore(funding_rate,168))",
                    "neg(zscore(sma(funding_rate,72),168))",
                ],
                "non_funding_family_examples": [
                    "zscore(div(sub(high,low),close),96)",
                    "zscore(ema(volume,48),120)",
                    "zscore(ret(close,24),96)",
                ],
            },
            "requirements": [
                (
                    "Return valid JSON: "
                    "{\"candidates\":[{\"formula\":\"<DSL expression>\","
                    "\"description\":\"<economic rationale>\","
                    "\"hypothesis\":\"<market behavior being tested>\","
                    "\"expected_edge\":\"<why this should predict future returns>\","
                    "\"expected_failure_mode\":\"<likely reason it may fail>\","
                    "\"rewrite_plan_if_killed\":\"<how to revise after a failed gate>\"}]}. "
                    "The four schema-v2 fields are required for every candidate."
                ),
                f"Generate up to {count} candidates. Each description MUST be >= {desc_len} characters.",
                (
                    f"Hard shape rule: max formula depth {self.max_formula_depth}, "
                    f"max {self.max_formula_operators} operators. Obey shape_constraints exactly; formulas that "
                    "violate them are rejected before backtesting."
                ),
                "Prefer 1-3 operator formulas. Before returning JSON, self-check every formula against max_depth and max_operators.",
                "At most one returned candidate may be funding_rate-only; diversify across funding, volatility/range, volume/liquidity, or price-regime families.",
                (
                    "A higher pass_rate alone is not enough. Prefer candidates that can plausibly improve both "
                    "cross-asset pass_rate and mean Sharpe versus the parent evidence in failure_detail."
                ),
                (
                    "For normalized high-low range, volatility, or volume/liquidity candidates, explain why the signal "
                    "should be profitable after costs rather than merely present on more assets."
                ),
                "In expected_failure_mode, name the likely cross-asset failure pattern before backtesting.",
                "Do not copy the failed formula or any formula listed in disallowed_exact_formulas. Preserve economic intent only if the failed gate suggests it is salvageable.",
                "Prefer simple, interpretable changes: horizon, smoothing, field substitution, sign flip, or regime proxy.",
            ],
        }
        user_msg = json.dumps(prompt, ensure_ascii=False)
        detail["prompt_chars"] = len(user_msg)
        detail["forbidden_count"] = len(forbidden)
        detail["forbidden_sent"] = len(truncated_forbidden)
        detail["disallowed_formula_count"] = len(disallowed_formulas)
        try:
            t0 = time.time()
            content = call_llm(
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

        out, rejected = self._parse_candidate_payload(
            data,
            count,
            forbidden,
            disallow=disallowed_formulas,
            max_pure_funding=1 if count > 1 else None,
        )
        if rejected:
            self.events.append({"source": "rewrite_validator", "accepted": len(out), "rejected": rejected[:20]})
        if not out:
            reject_summary = "; ".join(f"{r['formula'][:60]}: {r['reason']}" for r in rejected[:5])
            return [], f"All {len(rejected)} LLM rewrite formulas rejected: {reject_summary}", detail
        return out, None, detail

    def _parse_candidate_payload(
        self,
        data: dict[str, Any],
        count: int,
        forbidden: list[str],
        *,
        disallow: set[str] | None = None,
        max_pure_funding: int | None = None,
    ) -> tuple[list[str], list[dict[str, str]]]:
        disallow = disallow or set()
        out: list[str] = []
        pure_funding_count = 0
        raw_candidates = data.get("candidates")
        if raw_candidates is None:
            raw_candidates = [{"formula": formula, "description": ""} for formula in data.get("formulas", [])]
        rejected = []
        for item in raw_candidates:
            formula = item.get("formula") if isinstance(item, dict) else str(item)
            description = item.get("description", "") if isinstance(item, dict) else ""
            metadata = _proposal_metadata_from_item(item if isinstance(item, dict) else {})
            try:
                canonical = validate_formula_shape(str(formula), self.max_formula_depth, self.max_formula_operators).canonical()
            except ValueError as exc:
                rejected.append({"formula": str(formula), "reason": str(exc)})
                continue
            if canonical in disallow:
                rejected.append({"formula": canonical, "reason": "copies disallowed failed formula"})
                continue
            desc_text = str(description).strip()
            if len(desc_text) < DESCRIPTION_MIN_LENGTH:
                rejected.append({"formula": canonical, "reason": f"description too short ({len(desc_text)} < {DESCRIPTION_MIN_LENGTH} chars)"})
                continue
            if not _has_economic_rationale(desc_text):
                rejected.append({"formula": canonical, "reason": "description lacks economic rationale"})
                continue
            if violates_forbidden(canonical, forbidden):
                rejected.append({"formula": canonical, "reason": "violates forbidden subtree"})
                continue
            if max_pure_funding is not None and _is_pure_funding_formula(canonical):
                if pure_funding_count >= max_pure_funding:
                    rejected.append({"formula": canonical, "reason": "too many pure funding-only candidates"})
                    continue
                pure_funding_count += 1
            self.descriptions[canonical] = desc_text
            self.proposal_metadata[canonical] = metadata
            out.append(canonical)
            if len(out) >= count:
                break
        return out, rejected


def call_llm(messages: list[dict[str, str]], settings: LLMSettings | None = None, temperature: float = 0.2) -> str:
    _load_env_file()
    api_key = _llm_api_key()
    if not api_key:
        raise RuntimeError("LLM_API_KEY is not set.")
    settings = _settings_with_env(settings)
    if not settings.base_url:
        raise RuntimeError("LLM_BASE_URL is not set.")
    if not settings.model:
        raise RuntimeError("LLM_MODEL is not set.")
    connect_timeout = 15.0
    read_timeout = float(settings.timeout_seconds)

    proxy_url = _env("LLM_PROXY", "", legacy="DEEPSEEK_PROXY") or os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
    proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None

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
                proxies=proxies,
            )
            try:
                resp.raise_for_status()
            except requests.HTTPError as exc:
                raise RuntimeError(f"LLM HTTP {resp.status_code}: {resp.text[:500]}") from exc
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
    raise RuntimeError(f"LLM request failed after {settings.max_retries + 1} attempts: {last_error_detail}")


def call_deepseek(messages: list[dict[str, str]], settings: LLMSettings | None = None, temperature: float = 0.2) -> str:
    return call_llm(messages, settings=settings, temperature=temperature)


def _env(name: str, default: str = "", *, legacy: str | None = None) -> str:
    value = os.getenv(name)
    if value:
        return value
    if legacy:
        value = os.getenv(legacy)
        if value:
            return value
    return default


def _llm_api_key() -> str:
    return _env("LLM_API_KEY", "", legacy="DEEPSEEK_API_KEY")


def _settings_with_env(settings: LLMSettings | None = None) -> LLMSettings:
    return LLMSettings(
        base_url=(settings.base_url if settings and settings.base_url else _env(
            "LLM_BASE_URL",
            _legacy_default_base_url(),
            legacy="DEEPSEEK_BASE_URL",
        )),
        model=(settings.model if settings and settings.model else _env(
            "LLM_MODEL",
            _legacy_default_model(),
            legacy="DEEPSEEK_MODEL",
        )),
        timeout_seconds=(
            settings.timeout_seconds
            if settings
            else int(_env("LLM_TIMEOUT_SECONDS", "120", legacy="DEEPSEEK_TIMEOUT_SECONDS"))
        ),
        max_retries=(
            settings.max_retries
            if settings
            else int(_env("LLM_MAX_RETRIES", "2", legacy="DEEPSEEK_MAX_RETRIES"))
        ),
        retry_sleep_seconds=settings.retry_sleep_seconds if settings else 3.0,
    )


def _legacy_default_base_url() -> str:
    if os.getenv("DEEPSEEK_API_KEY") and not os.getenv("LLM_API_KEY"):
        return "https://api.deepseek.com"
    return ""


def _legacy_default_model() -> str:
    if os.getenv("DEEPSEEK_API_KEY") and not os.getenv("LLM_API_KEY"):
        return "deepseek-chat"
    return ""


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


def _local_rewrite_description(formula: str, base_formula: str, failed_gates: list[str]) -> str:
    gates = ", ".join(failed_gates or ["unknown"])
    return (
        f"Local targeted rewrite of {base_formula} after failed gates {gates}: {formula}. "
        "It changes smoothing, horizon, field choice, or sign to preserve an interpretable market behavior while reducing the observed failure mode."
    )


def _proposal_metadata_from_item(item: dict[str, Any]) -> dict[str, str]:
    metadata = {field: str(item.get(field, "")).strip() for field in PROPOSAL_SCHEMA_FIELDS}
    description = str(item.get("description", "")).strip()
    if not metadata["hypothesis"]:
        metadata["hypothesis"] = description
    if not metadata["expected_edge"]:
        metadata["expected_edge"] = description
    if not metadata["expected_failure_mode"]:
        metadata["expected_failure_mode"] = "May fail due to weak validation, excessive turnover, crowding, or regime sensitivity."
    if not metadata["rewrite_plan_if_killed"]:
        metadata["rewrite_plan_if_killed"] = (
            "Use the failed brutal-filter gate to revise the horizon, smoothing, field choice, or regime conditioning."
        )
    return metadata


def _local_metadata(formula: str, dimension: str) -> dict[str, str]:
    return {
        "hypothesis": f"Local {dimension} proposal tests whether {formula} captures an interpretable crypto market state.",
        "expected_edge": "The signal may predict returns by summarizing momentum, reversal, funding pressure, volatility, or flow imbalance.",
        "expected_failure_mode": "It may fail if the relation is regime-specific, too correlated with existing factors, or too costly after delay and fees.",
        "rewrite_plan_if_killed": "Revise the field, horizon, smoothing, or sign based on the brutal-filter gate that rejects it.",
    }


def _local_rewrite_metadata(formula: str, base_formula: str, failed_gates: list[str]) -> dict[str, str]:
    gates = ", ".join(failed_gates or ["unknown"])
    return {
        "hypothesis": f"Targeted rewrite of {base_formula} after {gates} failure tests whether {formula} is a more robust expression.",
        "expected_edge": "The rewrite may keep the original economic idea while improving validation, turnover, diversity, or friction behavior.",
        "expected_failure_mode": "It may still fail if the original economic relation was spurious or if the rewrite remains too correlated or costly.",
        "rewrite_plan_if_killed": "Use the next failed gate to change horizon, smoothing, field family, or abandon the original economic idea.",
    }


def _shape_constraints(max_depth: int, max_operators: int) -> dict[str, Any]:
    return {
        "max_depth": max_depth,
        "max_operators": max_operators,
        "preferred_operator_count": "1 to 3 operators whenever possible",
        "preferred_templates": [
            "zscore(field, window)",
            "neg(zscore(field, window))",
            "zscore(ema(field, short_window), long_window)",
            "zscore(sma(field, short_window), long_window)",
            "zscore(ret(close, window), long_window)",
            "zscore(div(sub(high,low), close), window)",
            "corr(field_a, field_b, window)",
        ],
        "invalid_examples": [
            "neg(zscore(ema(winsorize(funding_rate,5),96),168))",
            "neg(zscore(div(sma(funding_rate,96),std(funding_rate,192)),192))",
            "neg(zscore(sma(div(sub(high,low),close),96),192))",
        ],
        "self_check": (
            "Count nested DSL function calls before returning. If a formula resembles an invalid example or exceeds "
            "max_depth/max_operators, simplify it instead of returning it."
        ),
    }


def _is_pure_funding_formula(formula: str) -> bool:
    if "funding_rate" not in formula:
        return False
    return not any(field in formula for field in ("open", "high", "low", "close", "volume"))


def _matching_selector_target(formula: str, rewrite_targets: list[Any]) -> dict[str, Any]:
    for target in rewrite_targets:
        if not isinstance(target, dict) or str(target.get("formula", "")) != formula:
            continue
        return {
            key: target.get(key)
            for key in [
                "factor_id",
                "selector_verdict",
                "rewrite_focus",
                "universe_pass_rate",
                "universe_mean_sharpe",
                "universe_median_rank_ic",
                "failed_assets",
            ]
            if key in target
        }
    return {}


def _rewrite_guidance(failed_gates: list[str]) -> dict[str, str]:
    guidance = {
        "predictive_power": "Change the information source, sign, or horizon. Do not merely smooth a non-predictive signal.",
        "homogeneity": "Preserve only the broad hypothesis; use a different field family or operator structure to reduce correlation.",
        "friction_audit": "Reduce turnover with slower windows, ema/sma smoothing, wider thresholds, or lower-churn funding/volume proxies.",
        "lifetime": "Improve regime stability with slower horizons, less reactive transforms, or a guard against transient market states.",
        "cross_asset_robustness": (
            "Avoid weak selector subtrees and shift toward funding, volatility, or liquidity regime signals that "
            "plausibly transfer across BTC, ETH, SOL, BNB, and AVAX."
        ),
        "cross_asset_profitability": (
            "Change the economic family or normalization so the signal can produce positive mean Sharpe across assets, "
            "not just a BTC-local fit."
        ),
    }
    return {gate: guidance.get(gate, "Make a simple interpretable rewrite tied to the failed metric.") for gate in failed_gates}


def _compact_failure_detail(detail: dict[str, Any]) -> dict[str, Any]:
    gates = detail.get("gates", {}) if isinstance(detail, dict) else {}
    compact = {}
    for name, value in gates.items():
        if isinstance(value, dict):
            compact[name] = {
                key: value.get(key)
                for key in ["pass", "rank_ic", "directional_win_rate", "max_corr_to_library", "cost_sharpe", "halflife_bars", "validation_sharpe", "rule"]
                if key in value
            }
    out = {
        "passed": detail.get("passed") if isinstance(detail, dict) else None,
        "brutal_score": detail.get("brutal_score") if isinstance(detail, dict) else None,
        "gates": compact,
    }
    if isinstance(detail, dict):
        universe = detail.get("universe")
        if isinstance(universe, dict):
            out["parent_multi_asset_evidence"] = {
                key: universe.get(key)
                for key in ["pass_rate", "mean_sharpe", "median_rank_ic", "failed_assets"]
                if key in universe
            }
        objective = detail.get("rewrite_objective")
        if isinstance(objective, dict):
            out["rewrite_objective"] = {
                key: objective.get(key)
                for key in [
                    "target_pass_rate_delta",
                    "target_mean_sharpe_delta",
                    "profitability_gate",
                    "failed_assets_instruction",
                ]
                if key in objective
            }
    return out
