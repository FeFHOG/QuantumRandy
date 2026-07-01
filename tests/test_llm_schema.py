from __future__ import annotations

import os
import json

import pandas as pd

from quantumrandy.candidate_selector import write_candidate_selector_report
from quantumrandy.config import PromptConfig
from quantumrandy.expression import validate_formula_shape
from quantumrandy.failure_memory import write_failure_memory
from quantumrandy.llm import FormulaGenerator, LLMSettings, _llm_api_key


def test_local_proposals_record_schema_v2_metadata() -> None:
    generator = FormulaGenerator(use_llm=False)

    formulas = generator.propose("zscore(close,12)", "effectiveness", 2, [])

    assert formulas
    for formula in formulas:
        metadata = generator.proposal_metadata[formula]
        assert metadata["hypothesis"]
        assert metadata["expected_edge"]
        assert metadata["expected_failure_mode"]
        assert metadata["rewrite_plan_if_killed"]


def test_llm_api_key_prefers_generic_env(monkeypatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "generic-key")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "legacy-key")

    assert _llm_api_key() == "generic-key"


def test_llm_api_key_accepts_legacy_env(monkeypatch) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "legacy-key")

    assert _llm_api_key() == "legacy-key"


def test_llm_schema_v2_metadata_is_parsed(monkeypatch) -> None:
    response = {
        "candidates": [
            {
                "formula": "neg(zscore(funding_rate,42))",
                "description": (
                    "Funding pressure mean reversion: extreme positive funding can indicate crowded long positioning "
                    "and a later reversal as leverage demand normalizes."
                ),
                "hypothesis": "Crowded funding pressure reverses after extreme long-side demand.",
                "expected_edge": "The factor can predict future returns when expensive long carry unwinds.",
                "expected_failure_mode": "It may fail in strong trending regimes where high funding persists.",
                "rewrite_plan_if_killed": (
                    "If killed by lifespan or predictive power, lengthen the zscore window or add trend guards."
                ),
            }
        ]
    }

    captured = {}

    def fake_call_llm(*args, **kwargs) -> str:
        import json

        captured["settings"] = kwargs.get("settings")
        return json.dumps(response)

    monkeypatch.setattr("quantumrandy.llm.call_llm", fake_call_llm)
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://llm.example/v1")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    generator = FormulaGenerator(use_llm=True, settings=LLMSettings(max_retries=0))

    formulas = generator.propose("zscore(close,12)", "diversity", 1, [])

    assert formulas == ["neg(zscore(funding_rate,42))"]
    metadata = generator.proposal_metadata[formulas[0]]
    assert metadata["hypothesis"].startswith("Crowded funding")
    assert "expensive long carry" in metadata["expected_edge"]
    assert "trending regimes" in metadata["expected_failure_mode"]
    assert "trend guards" in metadata["rewrite_plan_if_killed"]
    assert captured["settings"].base_url == "https://llm.example/v1"
    assert captured["settings"].model == "test-model"
    os.environ.pop("LLM_API_KEY", None)
    os.environ.pop("LLM_BASE_URL", None)
    os.environ.pop("LLM_MODEL", None)


def test_llm_prompt_includes_failure_memory(monkeypatch, tmp_path) -> None:
    write_failure_memory(
        [
            {
                "formula": "zscore(ret(close,6),48)",
                "passed": False,
                "kill_reasons": ["friction_audit"],
                "expected_failure_mode": "Turnover is too expensive after fees.",
                "rewrite_plan_if_killed": "Smooth the return signal.",
            },
            {
                "formula": "zscore(ret(close,12),48)",
                "passed": False,
                "kill_reasons": ["friction_audit"],
            },
        ],
        tmp_path,
    )
    captured = {}

    def fake_call_llm(messages, *args, **kwargs) -> str:
        captured["prompt"] = messages[-1]["content"]
        import json

        return json.dumps(
            {
                "candidates": [
                    {
                        "formula": "neg(zscore(funding_rate,42))",
                        "description": (
                            "Funding pressure mean reversion captures crowded carry positioning and possible reversal "
                            "after extreme perpetual funding dislocations."
                        ),
                        "hypothesis": "Crowded funding pressure reverses.",
                        "expected_edge": "Funding extremes can precede return reversal.",
                        "expected_failure_mode": "Trend regimes can overwhelm funding mean reversion.",
                        "rewrite_plan_if_killed": "Add slower smoothing or trend filters.",
                    }
                ]
            }
        )

    monkeypatch.setattr("quantumrandy.llm.call_llm", fake_call_llm)
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    generator = FormulaGenerator(
        use_llm=True,
        settings=LLMSettings(max_retries=0),
        prompt_config=PromptConfig(
            failure_memory_path=str(tmp_path),
            failure_memory_examples=1,
            failure_memory_clusters=1,
        ),
    )

    formulas = generator.propose("zscore(close,12)", "diversity", 1, [])

    assert formulas == ["neg(zscore(funding_rate,42))"]
    assert "failure_memory" in captured["prompt"]
    assert "shape_constraints" in captured["prompt"]
    assert "zscore(ret(close,6),48)" in captured["prompt"]
    assert "friction_audit" in captured["prompt"]
    assert generator.events[-1]["failure_memory_examples"] == 1
    assert generator.events[-1]["failure_memory_clusters"] == 1
    os.environ.pop("LLM_API_KEY", None)


def test_llm_prompt_includes_candidate_selector_context(monkeypatch, tmp_path) -> None:
    write_candidate_selector_report(
        [
            {
                "factor_id": "weak_momentum",
                "formula": "zscore(ret(close,6),48)",
                "passed": True,
                "brutal_score": 60.0,
            },
            {
                "factor_id": "evidence_gap",
                "formula": "zscore(volume,48)",
                "passed": False,
                "brutal_score": 5.0,
            },
        ],
        tmp_path,
        universe_summary=pd.DataFrame(
            [
                {
                    "factor_id": "weak_momentum",
                    "formula": "zscore(ret(close,6),48)",
                    "pass_rate": 0.2,
                    "evaluated_assets": 5,
                    "mean_sharpe": 0.1,
                    "median_rank_ic": 0.0,
                    "failed_assets": "ETHUSDT,SOLUSDT,BNBUSDT,AVAXUSDT",
                }
            ]
        ),
    )
    captured = {}

    def fake_call_llm(messages, *args, **kwargs) -> str:
        captured["prompt"] = messages[-1]["content"]
        import json

        return json.dumps(
            {
                "candidates": [
                    {
                        "formula": "neg(zscore(funding_rate,42))",
                        "description": (
                            "Funding pressure mean reversion captures crowded carry positioning and possible reversal "
                            "after extreme perpetual funding dislocations."
                        ),
                        "hypothesis": "Crowded funding pressure reverses.",
                        "expected_edge": "Funding extremes can precede return reversal.",
                        "expected_failure_mode": "Trend regimes can overwhelm funding mean reversion.",
                        "rewrite_plan_if_killed": "Add slower smoothing or trend filters.",
                    }
                ]
            }
        )

    monkeypatch.setattr("quantumrandy.llm.call_llm", fake_call_llm)
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    generator = FormulaGenerator(
        use_llm=True,
        settings=LLMSettings(max_retries=0),
        prompt_config=PromptConfig(
            candidate_selector_path=str(tmp_path),
            candidate_selector_rewrite_targets=1,
            candidate_selector_evidence_gaps=1,
        ),
    )

    formulas = generator.propose("zscore(close,12)", "diversity", 1, [])

    assert formulas == ["neg(zscore(funding_rate,42))"]
    assert "multi_asset_candidate_evidence" in captured["prompt"]
    assert "weak_momentum" in captured["prompt"]
    assert "evidence_gap" in captured["prompt"]
    assert generator.events[-1]["candidate_selector_rewrite_targets"] == 1
    assert generator.events[-1]["candidate_selector_evidence_gaps"] == 1
    os.environ.pop("LLM_API_KEY", None)


def test_local_rewrite_records_schema_v2_metadata() -> None:
    generator = FormulaGenerator(use_llm=False)

    formulas = generator.rewrite(
        "zscore(ret(close,6),48)",
        ["friction_audit"],
        {"passed": False},
        2,
        [],
    )

    assert formulas
    assert generator.events[-1]["source"] == "local_rewrite"
    for formula in formulas:
        assert "Targeted rewrite" in generator.proposal_metadata[formula]["hypothesis"]
        assert generator.descriptions[formula]


def test_llm_rewrite_prompt_uses_failed_gate_guidance(monkeypatch) -> None:
    captured = {}

    def fake_call_llm(messages, *args, **kwargs) -> str:
        captured["prompt"] = messages[-1]["content"]
        import json

        return json.dumps(
            {
                "candidates": [
                    {
                        "formula": "zscore(ema(ret(close,6),48),72)",
                        "description": (
                            "Momentum continuation with slower EMA smoothing reduces turnover while preserving "
                            "the trend-following behavior of short-horizon price pressure."
                        ),
                        "hypothesis": "Smoothing momentum can preserve edge with lower trading churn.",
                        "expected_edge": "Trend pressure may persist after smoothing removes noisy flips.",
                        "expected_failure_mode": "The smoother signal may lag abrupt regime changes.",
                        "rewrite_plan_if_killed": "If killed again, switch fields or abandon price momentum.",
                    }
                ]
            }
        )

    monkeypatch.setattr("quantumrandy.llm.call_llm", fake_call_llm)
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    generator = FormulaGenerator(use_llm=True, settings=LLMSettings(max_retries=0))

    formulas = generator.rewrite(
        "zscore(ret(close,6),48)",
        ["friction_audit"],
        {"gates": {"friction_audit": {"cost_sharpe": -0.2, "rule": "cost_sharpe >= 0.3"}}},
        1,
        [],
    )

    assert formulas == ["zscore(ema(ret(close,6),48),72)"]
    assert "Rewrite a failed crypto alpha factor" in captured["prompt"]
    assert "shape_constraints" in captured["prompt"]
    assert "max_depth" in captured["prompt"]
    assert "invalid_examples" in captured["prompt"]
    assert "neg(zscore(ema(winsorize(funding_rate,5),96),168))" in captured["prompt"]
    assert "candidate_diversity" in captured["prompt"]
    assert "max_pure_funding_candidates" in captured["prompt"]
    assert "Pure funding-rate-only candidate limit for this parent" in captured["prompt"]
    assert "rewrite_objective" in captured["prompt"]
    assert "pass_rate_delta > 0" in captured["prompt"]
    assert "mean_sharpe_delta >= 0" in captured["prompt"]
    assert "higher pass_rate alone is not enough" in captured["prompt"]
    assert "likely cross-asset failure pattern" in captured["prompt"]
    assert "friction_audit" in captured["prompt"]
    assert "Reduce turnover" in captured["prompt"]
    prompt = json.loads(captured["prompt"])
    for example in prompt["candidate_diversity"]["non_funding_family_examples"]:
        validate_formula_shape(example)
    assert generator.events[-1]["source"] == "llm_rewrite"
    os.environ.pop("LLM_API_KEY", None)


def test_llm_rewrite_can_disable_local_fill(monkeypatch) -> None:
    def fake_call_llm(messages, *args, **kwargs) -> str:
        import json

        return json.dumps(
            {
                "candidates": [
                    {
                        "formula": "zscore(ema(ret(close,6),48),72)",
                        "description": (
                            "Momentum continuation with slower EMA smoothing reduces turnover while preserving "
                            "the trend-following behavior of short-horizon price pressure."
                        ),
                        "hypothesis": "Smoothing momentum can preserve edge with lower trading churn.",
                        "expected_edge": "Trend pressure may persist after smoothing removes noisy flips.",
                        "expected_failure_mode": "The smoother signal may lag abrupt regime changes.",
                        "rewrite_plan_if_killed": "If killed again, switch fields or abandon price momentum.",
                    }
                ]
            }
        )

    monkeypatch.setattr("quantumrandy.llm.call_llm", fake_call_llm)
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    generator = FormulaGenerator(use_llm=True, settings=LLMSettings(max_retries=0))

    formulas = generator.rewrite(
        "zscore(ret(close,6),48)",
        ["friction_audit"],
        {"passed": False},
        2,
        [],
        allow_local_fallback=False,
    )

    assert formulas == ["zscore(ema(ret(close,6),48),72)"]
    assert [event["source"] for event in generator.events] == ["llm_rewrite"]
    assert generator.proposal_metadata[formulas[0]]["generation_source"] == "llm_rewrite"
    os.environ.pop("LLM_API_KEY", None)


def test_llm_rewrite_parser_limits_pure_funding_candidates() -> None:
    generator = FormulaGenerator(use_llm=False)

    out, rejected = generator._parse_candidate_payload(
        {
            "candidates": [
                {
                    "formula": "neg(zscore(funding_rate,168))",
                    "description": "Funding pressure mean reversion captures crowded carry and possible reversal.",
                },
                {
                    "formula": "neg(zscore(sma(funding_rate,72),168))",
                    "description": "Funding carry pressure remains a crowding proxy but should be capped per batch.",
                },
                {
                    "formula": "zscore(volume,96)",
                    "description": "Volume pressure can proxy liquidity regime changes across crypto markets.",
                },
            ]
        },
        3,
        [],
        max_pure_funding=1,
    )

    assert out == ["neg(zscore(funding_rate,168))", "zscore(volume,96)"]
    assert rejected[-1]["reason"] == "pure funding-only candidate exceeds family limit (1)"


def test_llm_rewrite_parser_can_disallow_pure_funding_candidates() -> None:
    generator = FormulaGenerator(use_llm=False)

    out, rejected = generator._parse_candidate_payload(
        {
            "candidates": [
                {
                    "formula": "neg(zscore(funding_rate,168))",
                    "description": "Funding pressure mean reversion captures crowded carry and possible reversal.",
                },
                {
                    "formula": "zscore(volume,96)",
                    "description": "Volume pressure can proxy liquidity regime changes across crypto markets.",
                },
            ]
        },
        2,
        [],
        max_pure_funding=0,
    )

    assert out == ["zscore(volume,96)"]
    assert rejected[0]["reason"] == "pure funding-only candidate exceeds family limit (0)"


def test_llm_rewrite_prompt_includes_candidate_selector_context(monkeypatch, tmp_path) -> None:
    write_candidate_selector_report(
        [
            {
                "factor_id": "weak_conviction",
                "formula": "zscore(corr(sub(close,open),volume,48),72)",
                "passed": True,
                "brutal_score": 40.0,
            }
        ],
        tmp_path,
        universe_summary=pd.DataFrame(
            [
                {
                    "factor_id": "weak_conviction",
                    "formula": "zscore(corr(sub(close,open),volume,48),72)",
                    "pass_rate": 0.2,
                    "evaluated_assets": 5,
                    "mean_sharpe": 0.2,
                    "median_rank_ic": 0.0,
                    "failed_assets": "BTCUSDT,ETHUSDT,BNBUSDT,AVAXUSDT",
                }
            ]
        ),
    )
    captured = {}

    def fake_call_llm(messages, *args, **kwargs) -> str:
        captured["prompt"] = messages[-1]["content"]
        import json

        return json.dumps(
            {
                "candidates": [
                    {
                        "formula": "winsorize(zscore(volume,96),96)",
                        "description": (
                            "Volume pressure regimes can capture broad liquidity expansion across assets while "
                            "winsorization reduces extreme noisy turnover and fragile single-asset spikes."
                        ),
                        "hypothesis": "Smoothed volume pressure can generalize across crypto assets.",
                        "expected_edge": "Liquidity expansion may precede persistent risk appetite.",
                        "expected_failure_mode": "The signal may lag sudden liquidity regime changes.",
                        "rewrite_plan_if_killed": "Switch to funding or volatility fields if volume remains fragile.",
                    }
                ]
            }
        )

    monkeypatch.setattr("quantumrandy.llm.call_llm", fake_call_llm)
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    generator = FormulaGenerator(
        use_llm=True,
        settings=LLMSettings(max_retries=0),
        prompt_config=PromptConfig(candidate_selector_path=str(tmp_path), candidate_selector_rewrite_targets=1),
    )

    formulas = generator.rewrite(
        "zscore(corr(sub(close,open),volume,48),72)",
        ["lifetime"],
        {"gates": {"lifetime": {"validation_sharpe": -0.1}}},
        1,
        [],
    )

    assert formulas == ["winsorize(zscore(volume,96),96)"]
    assert "multi_asset_candidate_evidence" in captured["prompt"]
    assert "weak_conviction" in captured["prompt"]
    assert "parent_selector_target_evidence" in captured["prompt"]
    assert "universe_mean_sharpe" in captured["prompt"]
    assert generator.events[-1]["candidate_selector_rewrite_targets"] == 1
    os.environ.pop("LLM_API_KEY", None)


def test_llm_rewrite_prompt_includes_selector_negative_evidence(monkeypatch, tmp_path) -> None:
    pd.DataFrame(
        [
            {
                "parent_formula_family": "price",
                "candidate_formula_family": "volume_liquidity",
                "negative_count": 3,
                "avg_pass_rate_delta": -0.1,
                "avg_mean_sharpe_delta": -0.7,
                "worst_mean_sharpe_delta": -1.0,
                "example_formula": "zscore(volume,120)",
                "run_ids": "run_a",
            },
            {
                "parent_formula_family": "price",
                "candidate_formula_family": "range_volatility",
                "negative_count": 2,
                "avg_pass_rate_delta": 0.0,
                "avg_mean_sharpe_delta": -0.8,
                "worst_mean_sharpe_delta": -1.1,
                "example_formula": "neg(zscore(std(close,24),120))",
                "run_ids": "run_a|run_b",
            }
        ]
    ).to_csv(tmp_path / "selector_pipeline_negative_candidate_summary.csv", index=False)
    captured = {}

    def fake_call_llm(messages, *args, **kwargs) -> str:
        captured["prompt"] = messages[-1]["content"]
        return json.dumps(
            {
                "candidates": [
                    {
                        "formula": "neg(zscore(std(close,24),120))",
                        "description": "This repeats a failed volatility stress proxy and should be rejected by negative memory.",
                        "hypothesis": "Repeated volatility stress might still work.",
                        "expected_edge": "This should not be accepted because it copies negative evidence.",
                        "expected_failure_mode": "It repeats the prior family failure.",
                        "rewrite_plan_if_killed": "Use a different formula.",
                    },
                    {
                        "formula": "zscore(volume,96)",
                        "description": "Volume liquidity pressure can capture participation regimes without repeating failed volatility stress proxies.",
                        "hypothesis": "Liquidity participation may transfer better than failed volatility stress rewrites.",
                        "expected_edge": "Volume expansion can proxy broad risk appetite and persistent flow.",
                        "expected_failure_mode": "Volume may remain exchange-specific on lower-liquidity assets.",
                        "rewrite_plan_if_killed": "Switch to price-volume interaction or abandon this family.",
                    }
                ]
            }
        )

    monkeypatch.setattr("quantumrandy.llm.call_llm", fake_call_llm)
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    generator = FormulaGenerator(
        use_llm=True,
        settings=LLMSettings(max_retries=0),
        prompt_config=PromptConfig(selector_evidence_path=str(tmp_path), selector_negative_examples=1),
    )

    formulas = generator.rewrite(
        "zscore(sub(sma(close,12),sma(close,48)),48)",
        ["cross_asset_profitability"],
        {"rewrite_objective": {"max_pure_funding_candidates": 0}},
        2,
        [],
        allow_local_fallback=False,
    )

    assert formulas == ["zscore(volume,96)"]
    assert "selector_negative_evidence" in captured["prompt"]
    assert "range_volatility" in captured["prompt"]
    assert "neg(zscore(std(close,24),120))" in captured["prompt"]
    validator_event = next(event for event in generator.events if event["source"] == "rewrite_validator")
    assert validator_event["rejected"][0]["reason"] == "copies disallowed failed formula"
    assert generator.events[-1]["selector_negative_examples"] == 1
    assert generator.events[-1]["selector_negative_families"] == 2
    assert generator.events[-1]["selector_negative_disallowed_formulas"] == 2
    os.environ.pop("LLM_API_KEY", None)
