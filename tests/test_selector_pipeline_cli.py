from __future__ import annotations

import sys

import pytest

from scripts import run_selector_rewrite_pipeline


def _manifest(*, llm_evidence: bool, llm_true_improvement: bool = False) -> dict:
    return {
        "rewrite": {
            "candidate_count": 2,
            "use_llm_requested": True,
            "llm_rewrite_accepted": 1 if llm_evidence else 0,
            "fallback_rewrite_accepted": 0 if llm_evidence else 2,
            "allow_local_fallback": True,
            "is_llm_policy_evidence": llm_evidence,
        },
        "universe": {"status": "skipped"},
        "portfolio_universe": {"status": "skipped"},
        "review": {
            "status": "completed",
            "llm_true_improved_count": 1 if llm_true_improvement else 0,
            "candidate_highlight_generation_source_counts": {"llm_rewrite": 1} if llm_true_improvement else {},
            "is_llm_true_improvement_evidence": llm_true_improvement,
        },
    }


def test_selector_pipeline_cli_can_require_llm_evidence(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(run_selector_rewrite_pipeline, "run_selector_rewrite_pipeline", lambda **kwargs: _manifest(llm_evidence=False))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_selector_rewrite_pipeline.py",
            "--selector",
            str(tmp_path / "selector"),
            "--out",
            str(tmp_path / "out"),
            "--use-llm",
            "--require-llm-evidence",
        ],
    )

    with pytest.raises(SystemExit) as exc:
        run_selector_rewrite_pipeline.main()

    assert exc.value.code == 2
    assert "did not produce LLM policy evidence" in capsys.readouterr().err


def test_selector_pipeline_cli_accepts_true_llm_evidence(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(run_selector_rewrite_pipeline, "run_selector_rewrite_pipeline", lambda **kwargs: _manifest(llm_evidence=True))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_selector_rewrite_pipeline.py",
            "--selector",
            str(tmp_path / "selector"),
            "--out",
            str(tmp_path / "out"),
            "--use-llm",
            "--require-llm-evidence",
        ],
    )

    run_selector_rewrite_pipeline.main()

    assert "llm_evidence=True" in capsys.readouterr().out


def test_selector_pipeline_cli_can_require_llm_true_improvement(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(
        run_selector_rewrite_pipeline,
        "run_selector_rewrite_pipeline",
        lambda **kwargs: _manifest(llm_evidence=True, llm_true_improvement=False),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_selector_rewrite_pipeline.py",
            "--selector",
            str(tmp_path / "selector"),
            "--out",
            str(tmp_path / "out"),
            "--use-llm",
            "--require-llm-true-improvement",
        ],
    )

    with pytest.raises(SystemExit) as exc:
        run_selector_rewrite_pipeline.main()

    assert exc.value.code == 3
    assert "did not produce LLM true-improvement evidence" in capsys.readouterr().err


def test_selector_pipeline_cli_accepts_llm_true_improvement(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(
        run_selector_rewrite_pipeline,
        "run_selector_rewrite_pipeline",
        lambda **kwargs: _manifest(llm_evidence=True, llm_true_improvement=True),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_selector_rewrite_pipeline.py",
            "--selector",
            str(tmp_path / "selector"),
            "--out",
            str(tmp_path / "out"),
            "--use-llm",
            "--require-llm-true-improvement",
        ],
    )

    run_selector_rewrite_pipeline.main()

    assert "llm_true_improvement=True" in capsys.readouterr().out


def test_selector_pipeline_cli_can_disable_local_fallback(monkeypatch, tmp_path) -> None:
    captured = {}

    def fake_run_selector_rewrite_pipeline(**kwargs):
        captured.update(kwargs)
        return _manifest(llm_evidence=True)

    monkeypatch.setattr(run_selector_rewrite_pipeline, "run_selector_rewrite_pipeline", fake_run_selector_rewrite_pipeline)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_selector_rewrite_pipeline.py",
            "--selector",
            str(tmp_path / "selector"),
            "--out",
            str(tmp_path / "out"),
            "--use-llm",
            "--llm-only",
            "--require-llm-evidence",
        ],
    )

    run_selector_rewrite_pipeline.main()

    assert captured["allow_local_fallback"] is False
