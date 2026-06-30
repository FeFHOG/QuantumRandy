from __future__ import annotations

import json

from quantumrandy.failure_memory import build_failure_memory, load_failure_prompt_context, write_failure_memory


def test_build_failure_memory_preserves_schema_v2_and_clusters() -> None:
    rows = [
        {
            "formula": "zscore(ret(close,6),48)",
            "description": "Momentum candidate.",
            "hypothesis": "Short-horizon price momentum persists.",
            "expected_edge": "Continuation after strong 4h returns.",
            "expected_failure_mode": "High turnover and fragile validation.",
            "rewrite_plan_if_killed": "Smooth the return or lengthen the lookback.",
            "passed": False,
            "kill_reasons": ["friction_audit", "lifetime"],
            "brutal_score": 12.0,
            "rank_ic": 0.001,
            "sharpe": -0.2,
        },
        {
            "formula": "zscore(ret(close,12),48)",
            "description": "Momentum candidate variant.",
            "passed": False,
            "gate_predictive_power": False,
            "gate_friction_audit": False,
        },
        {
            "formula": "neg(zscore(funding_rate,42))",
            "passed": True,
        },
    ]

    failures, clusters, manifest = build_failure_memory(rows)

    assert manifest["artifact_type"] == "quantumrandy_failure_memory"
    assert manifest["failure_count"] == 2
    assert set(failures["formula"]) == {"zscore(ret(close,6),48)", "zscore(ret(close,12),48)"}
    first = failures[failures["formula"] == "zscore(ret(close,6),48)"].iloc[0].to_dict()
    assert first["hypothesis"] == "Short-horizon price momentum persists."
    assert first["failed_gates"] == "friction_audit,lifetime"
    assert not clusters.empty
    assert "zscore(ret(close,n),n)" in set(clusters["subtree"])


def test_write_failure_memory_outputs_report(tmp_path) -> None:
    rows = [
        {
            "formula": "zscore(volume,48)",
            "passed": False,
            "kill_reasons": ["predictive_power"],
        }
    ]

    manifest = write_failure_memory(rows, tmp_path)

    assert manifest["failure_count"] == 1
    assert (tmp_path / "failure_memory.csv").exists()
    assert (tmp_path / "failure_clusters.csv").exists()
    payload = json.loads((tmp_path / "failure_memory_manifest.json").read_text(encoding="utf-8"))
    assert payload["safety"]["not_runtime_publish_payload"] is True
    assert "research artifact only" in (tmp_path / "FAILURE_MEMORY_REPORT.md").read_text(encoding="utf-8")


def test_load_failure_prompt_context_reads_examples_and_clusters(tmp_path) -> None:
    rows = [
        {"formula": "zscore(ret(close,6),48)", "passed": False, "kill_reasons": ["friction_audit"]},
        {"formula": "zscore(ret(close,12),48)", "passed": False, "kill_reasons": ["lifetime"]},
    ]
    write_failure_memory(rows, tmp_path)

    context = load_failure_prompt_context(tmp_path, max_examples=1, max_clusters=1)

    assert context["available"] is True
    assert len(context["examples"]) == 1
    assert len(context["clusters"]) == 1
    assert context["examples"][0]["formula"] == "zscore(ret(close,6),48)"
