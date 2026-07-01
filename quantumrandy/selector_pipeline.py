from __future__ import annotations

from pathlib import Path
from typing import Any

from .candidate_rewrite import (
    CandidateRewritePolicy,
    load_rewrite_targets,
    load_selector_forbidden_subtrees,
    write_selector_rewrite_report,
)
from .config import PromptConfig
from .io_utils import safe_write_csv, safe_write_json, safe_write_text
from .llm import FormulaGenerator, LLMSettings
from .portfolio import build_portfolio_research, render_portfolio_report
from .portfolio_universe import run_portfolio_universe_evaluation, write_portfolio_universe_report
from .universe import AssetDataset, load_asset_dataset, run_universe_evaluation
from .walk_forward import load_formula_entries


def run_selector_rewrite_pipeline(
    *,
    selector_path: str | Path,
    out_dir: str | Path,
    config_paths: list[str | Path] | None = None,
    window: str = "validation",
    max_targets: int = 5,
    candidates_per_target: int = 2,
    use_llm: bool = False,
    failure_memory_path: str | Path | None = None,
    timeout_seconds: int = 120,
    run_universe: bool = True,
    run_portfolio_universe: bool = True,
    max_corr: float | None = None,
    min_portfolio_factors: int = 1,
) -> dict[str, Any]:
    selector = Path(selector_path)
    out = Path(out_dir)
    rewrite_out = out / "rewrite"
    universe_out = out / "universe"
    portfolio_out = out / "portfolio"
    portfolio_universe_out = out / "portfolio_universe"
    out.mkdir(parents=True, exist_ok=True)

    policy = CandidateRewritePolicy(max_targets=max_targets, candidates_per_target=candidates_per_target)
    targets = load_rewrite_targets(selector, max_targets=max_targets)
    selector_forbidden = load_selector_forbidden_subtrees(
        selector,
        max_subtrees=policy.max_selector_forbidden_subtrees,
    )
    generator = FormulaGenerator(
        use_llm=use_llm,
        settings=LLMSettings(timeout_seconds=timeout_seconds),
        prompt_config=PromptConfig(
            candidate_selector_path=str(selector),
            failure_memory_path=str(failure_memory_path) if failure_memory_path else None,
        ),
    )
    rewrite_manifest = write_selector_rewrite_report(
        targets,
        generator,
        rewrite_out,
        policy=policy,
        selector_forbidden_subtrees=selector_forbidden,
    )

    candidate_path = rewrite_out / "selector_rewrite_candidates.json"
    candidates = load_formula_entries(candidate_path)
    manifest: dict[str, Any] = {
        "artifact_type": "quantumrandy_selector_rewrite_research_pipeline",
        "schema_version": 1,
        "safety": {
            "research_only": True,
            "not_runtime_publish_payload": True,
            "does_not_update_runtime": True,
            "does_not_auto_admit_factors": True,
            "requires_manual_review_before_runtime": True,
        },
        "selector_path": selector.as_posix(),
        "window": window,
        "config_paths": [Path(path).as_posix() for path in config_paths or []],
        "rewrite": {
            "status": "completed",
            "out_dir": rewrite_out.as_posix(),
            "candidate_path": candidate_path.as_posix(),
            "target_count": rewrite_manifest.get("target_count", 0),
            "candidate_count": rewrite_manifest.get("candidate_count", 0),
            "selector_forbidden_subtree_count": rewrite_manifest.get("selector_forbidden_subtree_count", 0),
        },
        "universe": {"status": "skipped", "reason": ""},
        "portfolio": {"status": "skipped", "reason": ""},
        "portfolio_universe": {"status": "skipped", "reason": ""},
        "outputs": {
            "rewrite_candidates": (rewrite_out / "selector_rewrite_candidates.json").as_posix(),
            "manifest": (out / "selector_rewrite_pipeline_manifest.json").as_posix(),
        },
    }

    assets = _load_assets(config_paths or [], window=window)
    if not candidates:
        reason = "selector rewrite produced no candidate formulas"
        manifest["universe"] = {"status": "skipped", "reason": reason}
        manifest["portfolio"] = {"status": "skipped", "reason": reason}
        manifest["portfolio_universe"] = {"status": "skipped", "reason": reason}
    elif run_universe and assets:
        details, summary = run_universe_evaluation(assets, candidates)
        summary = summary.sort_values(
            ["robustness_score", "pass_rate", "mean_sharpe", "median_rank_ic"],
            ascending=[False, False, False, False],
        )
        _write_universe_outputs(universe_out, details=details, summary=summary, assets=assets, window=window)
        manifest["universe"] = {
            "status": "completed",
            "out_dir": universe_out.as_posix(),
            "summary_rows": len(summary),
            "top_factor_ids": [str(row.get("factor_id", "")) for row in summary.head(10).to_dict(orient="records")],
        }
        manifest["outputs"]["universe_summary"] = (universe_out / "universe_summary.csv").as_posix()
    elif run_universe:
        manifest["universe"] = {"status": "skipped", "reason": "no asset config paths provided"}
    else:
        manifest["universe"] = {"status": "skipped", "reason": "disabled by caller"}

    if candidates and run_portfolio_universe and assets:
        factors, selection, portfolios, contribution, portfolio_manifest = build_portfolio_research(
            assets[0].data,
            candidates,
            assets[0].cfg,
            max_corr=max_corr,
            min_factors=min_portfolio_factors,
        )
        portfolio_manifest["window"] = window
        portfolio_manifest["source_selector_rewrite_candidates"] = candidate_path.as_posix()
        _write_portfolio_outputs(
            portfolio_out,
            factors=factors,
            selection=selection,
            portfolios=portfolios,
            contribution=contribution,
            manifest=portfolio_manifest,
        )
        manifest["portfolio"] = {
            "status": "completed",
            "out_dir": portfolio_out.as_posix(),
            "portfolio_count": len(portfolios),
            "selected_factor_ids": portfolio_manifest.get("selected_factor_ids", []),
        }
        manifest["outputs"]["portfolio_manifest"] = (portfolio_out / "portfolio_manifest.json").as_posix()

        details, summary, portfolio_universe_manifest = run_portfolio_universe_evaluation(
            assets,
            portfolio_manifest,
            factors.to_dict(orient="records"),
        )
        summary = summary.sort_values(
            ["robustness_score", "pass_rate", "mean_sharpe", "median_rank_ic"],
            ascending=[False, False, False, False],
        )
        portfolio_universe_manifest.update(
            {
                "window": window,
                "source_selector_rewrite_candidates": candidate_path.as_posix(),
                "source_portfolio_manifest_path": (portfolio_out / "portfolio_manifest.json").as_posix(),
            }
        )
        write_portfolio_universe_report(
            portfolio_universe_out,
            details=details,
            summary=summary,
            manifest=portfolio_universe_manifest,
        )
        manifest["portfolio_universe"] = {
            "status": "completed",
            "out_dir": portfolio_universe_out.as_posix(),
            "summary_rows": len(summary),
            "portfolio_ids": [str(row.get("portfolio_id", "")) for row in summary.to_dict(orient="records")],
        }
        manifest["outputs"]["portfolio_universe_summary"] = (
            portfolio_universe_out / "portfolio_universe_summary.csv"
        ).as_posix()
    elif candidates and run_portfolio_universe:
        manifest["portfolio"] = {"status": "skipped", "reason": "no asset config paths provided"}
        manifest["portfolio_universe"] = {"status": "skipped", "reason": "no asset config paths provided"}
    elif not run_portfolio_universe:
        manifest["portfolio"] = {"status": "skipped", "reason": "disabled by caller"}
        manifest["portfolio_universe"] = {"status": "skipped", "reason": "disabled by caller"}

    safe_write_json(out / "selector_rewrite_pipeline_manifest.json", manifest, out / "events.jsonl")
    safe_write_text(out / "SELECTOR_REWRITE_PIPELINE_REPORT.md", render_pipeline_report(manifest), out / "events.jsonl")
    return manifest


def render_pipeline_report(manifest: dict[str, Any]) -> str:
    lines = [
        "# QuantumRandy Selector Rewrite Research Pipeline",
        "",
        "This is a research artifact only. It is not a runtime publish payload and does not admit factors.",
        "",
        "## Summary",
        "",
        f"- Selector: `{manifest['selector_path']}`",
        f"- Window: `{manifest['window']}`",
        f"- Rewrite candidates: `{manifest['rewrite']['candidate_count']}`",
        f"- Selector forbidden subtrees: `{manifest['rewrite']['selector_forbidden_subtree_count']}`",
        "",
        "## Stages",
        "",
        "| Stage | Status | Detail |",
        "|---|---|---|",
    ]
    for stage in ["rewrite", "universe", "portfolio", "portfolio_universe"]:
        payload = manifest.get(stage, {})
        detail = payload.get("out_dir") or payload.get("reason") or ""
        lines.append(f"| `{stage}` | `{payload.get('status', '')}` | `{detail}` |")
    lines.extend(
        [
            "",
            "## Files",
            "",
            "- `rewrite/selector_rewrite_candidates.json`: leaderboard-style research candidates.",
            "- `universe/universe_summary.csv`: formula-level multi-asset evidence when configs are provided.",
            "- `portfolio/portfolio_manifest.json`: fixed-blend research portfolio when configs are provided.",
            "- `portfolio_universe/portfolio_universe_summary.csv`: portfolio-level multi-asset evidence.",
            "- `selector_rewrite_pipeline_manifest.json`: machine-readable stage provenance and safety metadata.",
        ]
    )
    return "\n".join(lines) + "\n"


def _load_assets(config_paths: list[str | Path], *, window: str) -> list[AssetDataset]:
    return [load_asset_dataset(path, window=window) for path in config_paths]


def _write_universe_outputs(
    out: Path,
    *,
    details,
    summary,
    assets: list[AssetDataset],
    window: str,
) -> None:
    out.mkdir(parents=True, exist_ok=True)
    manifest = {
        "artifact_type": "quantumrandy_universe_robustness",
        "schema_version": 1,
        "safety": {
            "research_only": True,
            "not_runtime_publish_payload": True,
            "does_not_update_runtime": True,
            "requires_manual_review_before_runtime": True,
        },
        "window": window,
        "asset_count": len(assets),
        "assets": [
            {
                "symbol": asset.name,
                "config": asset.config_path,
                "bars": len(asset.data),
                "ohlcv_csv": str(asset.cfg.ohlcv_csv),
                "funding_csv": str(asset.cfg.funding_csv),
            }
            for asset in assets
        ],
        "summary_rows": len(summary),
        "score": "mean_sharpe + 10*median_rank_ic + pass_rate - sharpe_variance - worst_max_dd",
    }
    safe_write_csv(out / "universe_details.csv", details, out / "events.jsonl")
    safe_write_csv(out / "universe_summary.csv", summary, out / "events.jsonl")
    safe_write_json(out / "universe_manifest.json", manifest, out / "events.jsonl")


def _write_portfolio_outputs(
    out: Path,
    *,
    factors,
    selection,
    portfolios,
    contribution,
    manifest: dict[str, Any],
) -> None:
    out.mkdir(parents=True, exist_ok=True)
    safe_write_csv(out / "portfolio_factors.csv", factors, out / "events.jsonl")
    safe_write_csv(out / "portfolio_selection.csv", selection, out / "events.jsonl")
    safe_write_csv(out / "portfolio_summary.csv", portfolios, out / "events.jsonl")
    safe_write_csv(out / "portfolio_contribution.csv", contribution, out / "events.jsonl")
    safe_write_json(out / "portfolio_manifest.json", manifest, out / "events.jsonl")
    safe_write_text(
        out / "PORTFOLIO_REPORT.md",
        render_portfolio_report(manifest, factors, selection, portfolios, contribution),
        out / "events.jsonl",
    )
