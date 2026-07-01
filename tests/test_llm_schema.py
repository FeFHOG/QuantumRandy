from __future__ import annotations

import os

import pandas as pd

from quantumrandy.candidate_selector import write_candidate_selector_report
from quantumrandy.config import PromptConfig
from quantumrandy.failure_memory import write_failure_memory
from quantumrandy.llm import FormulaGenerator, LLMSettings


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


def test_deepseek_schema_v2_metadata_is_parsed(monkeypatch) -> None:
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

    def fake_call_deepseek(*args, **kwargs) -> str:
        import json

        return json.dumps(response)

    monkeypatch.setattr("quantumrandy.llm.call_deepseek", fake_call_deepseek)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    generator = FormulaGenerator(use_llm=True, settings=LLMSettings(max_retries=0))

    formulas = generator.propose("zscore(close,12)", "diversity", 1, [])

    assert formulas == ["neg(zscore(funding_rate,42))"]
    metadata = generator.proposal_metadata[formulas[0]]
    assert metadata["hypothesis"].startswith("Crowded funding")
    assert "expensive long carry" in metadata["expected_edge"]
    assert "trending regimes" in metadata["expected_failure_mode"]
    assert "trend guards" in metadata["rewrite_plan_if_killed"]
    os.environ.pop("DEEPSEEK_API_KEY", None)


def test_deepseek_prompt_includes_failure_memory(monkeypatch, tmp_path) -> None:
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

    def fake_call_deepseek(messages, *args, **kwargs) -> str:
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

    monkeypatch.setattr("quantumrandy.llm.call_deepseek", fake_call_deepseek)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
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
    assert "zscore(ret(close,6),48)" in captured["prompt"]
    assert "friction_audit" in captured["prompt"]
    assert generator.events[-1]["failure_memory_examples"] == 1
    assert generator.events[-1]["failure_memory_clusters"] == 1
    os.environ.pop("DEEPSEEK_API_KEY", None)


def test_deepseek_prompt_includes_candidate_selector_context(monkeypatch, tmp_path) -> None:
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

    def fake_call_deepseek(messages, *args, **kwargs) -> str:
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

    monkeypatch.setattr("quantumrandy.llm.call_deepseek", fake_call_deepseek)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
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
    os.environ.pop("DEEPSEEK_API_KEY", None)


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


def test_deepseek_rewrite_prompt_uses_failed_gate_guidance(monkeypatch) -> None:
    captured = {}

    def fake_call_deepseek(messages, *args, **kwargs) -> str:
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

    monkeypatch.setattr("quantumrandy.llm.call_deepseek", fake_call_deepseek)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
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
    assert "friction_audit" in captured["prompt"]
    assert "Reduce turnover" in captured["prompt"]
    assert generator.events[-1]["source"] == "deepseek_rewrite"
    os.environ.pop("DEEPSEEK_API_KEY", None)


def test_deepseek_rewrite_prompt_includes_candidate_selector_context(monkeypatch, tmp_path) -> None:
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

    def fake_call_deepseek(messages, *args, **kwargs) -> str:
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

    monkeypatch.setattr("quantumrandy.llm.call_deepseek", fake_call_deepseek)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
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
    assert generator.events[-1]["candidate_selector_rewrite_targets"] == 1
    os.environ.pop("DEEPSEEK_API_KEY", None)
