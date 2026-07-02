from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .expression import validate_formula_shape
from .io_utils import safe_write_csv, safe_write_json, safe_write_text
from .llm import FormulaGenerator
from .walk_forward import stable_factor_id


@dataclass(frozen=True)
class CandidateRewritePolicy:
    max_targets: int = 5
    candidates_per_target: int = 2
    avoid_selector_failed_subtrees: bool = True
    max_selector_forbidden_subtrees: int = 8
    allow_local_fallback: bool = True
    disallow_pure_funding_rewrite_for_non_funding_parent: bool = True


def load_rewrite_targets(path: str | Path, *, max_targets: int | None = None) -> list[dict[str, Any]]:
    root = Path(path)
    target_path = root / "rewrite_targets.csv" if root.is_dir() else root
    frame = pd.read_csv(target_path).fillna("")
    if "rewrite_priority" in frame.columns:
        frame = frame.sort_values(["rewrite_priority", "selector_score"], ascending=[True, False])
    elif "selector_score" in frame.columns:
        frame = frame.sort_values("selector_score", ascending=False)
    if max_targets is not None and max_targets > 0:
        frame = frame.head(max_targets)
    return [row for row in frame.to_dict(orient="records") if row.get("formula")]


def load_selector_forbidden_subtrees(path: str | Path, *, max_subtrees: int = 8) -> list[str]:
    if max_subtrees <= 0:
        return []
    root = Path(path)
    if root.is_dir():
        candidate_path = root / "candidate_selector.csv"
        rewrite_path = root / "rewrite_targets.csv"
        cluster_path = root / "multi_asset_failure_clusters.csv"
    else:
        candidate_path = root
        rewrite_path = root.with_name("rewrite_targets.csv")
        cluster_path = root.with_name("multi_asset_failure_clusters.csv")

    out: list[str] = []
    out.extend(_cluster_subtrees(cluster_path))
    out.extend(_matched_failed_subtrees(rewrite_path))
    out.extend(_matched_failed_subtrees(candidate_path))
    return _dedupe_subtrees(out)[:max_subtrees]


def build_selector_rewrite_candidates(
    rewrite_targets: list[dict[str, Any]],
    generator: FormulaGenerator,
    *,
    policy: CandidateRewritePolicy | None = None,
    forbidden: list[str] | None = None,
    selector_forbidden_subtrees: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    policy = policy or CandidateRewritePolicy()
    forbidden = forbidden or []
    selector_forbidden_subtrees = selector_forbidden_subtrees or []
    candidate_rows: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []
    seen_formulas: set[str] = set()
    known_selector_formulas = _known_selector_formulas(rewrite_targets)

    for target_index, target in enumerate(rewrite_targets[: policy.max_targets], start=1):
        formula = str(target.get("formula", ""))
        if not formula:
            continue
        failed_gates = _failed_gates_for_focus(str(target.get("rewrite_focus", "")))
        detail = _target_failure_detail(
            target,
            disallow_pure_funding_for_non_funding_parent=(
                policy.disallow_pure_funding_rewrite_for_non_funding_parent
            ),
        )
        target_failed_subtrees = _split_subtrees(target.get("matched_failed_subtrees", ""))
        effective_forbidden = _dedupe_subtrees(
            [
                *forbidden,
                *(selector_forbidden_subtrees if policy.avoid_selector_failed_subtrees else []),
                *(target_failed_subtrees if policy.avoid_selector_failed_subtrees else []),
            ]
        )
        before_events = len(generator.events)
        proposals = generator.rewrite(
            formula,
            failed_gates,
            detail,
            policy.candidates_per_target,
            effective_forbidden,
            disallowed_formulas=known_selector_formulas,
            allow_local_fallback=policy.allow_local_fallback,
        )
        for event in generator.events[before_events:]:
            event_rows.append(
                {
                    "target_index": target_index,
                    "parent_factor_id": target.get("factor_id", ""),
                    "parent_formula": formula,
                    "source": event.get("source", ""),
                    "requested": event.get("requested", ""),
                    "accepted": event.get("accepted", ""),
                    "error": event.get("error", ""),
                    "candidate_selector_rewrite_targets": event.get("candidate_selector_rewrite_targets", ""),
                    "candidate_selector_evidence_gaps": event.get("candidate_selector_evidence_gaps", ""),
                    "candidate_selector_clusters": event.get("candidate_selector_clusters", ""),
                    "selector_negative_examples": event.get("selector_negative_examples", ""),
                    "selector_negative_families": event.get("selector_negative_families", ""),
                    "selector_negative_disallowed_formulas": event.get(
                        "selector_negative_disallowed_formulas",
                        "",
                    ),
                    "selector_negative_blocked_family_pairs": event.get(
                        "selector_negative_blocked_family_pairs",
                        "",
                    ),
                    "selector_forbidden_subtree_count": len(effective_forbidden),
                    "selector_forbidden_subtrees": "|".join(effective_forbidden[:10]),
                    "known_selector_formula_count": len(known_selector_formulas),
                    "disallowed_formula_count": event.get("disallowed_formula_count", len(known_selector_formulas)),
                    "parent_formula_family": detail.get("rewrite_objective", {}).get("parent_formula_family", ""),
                    "max_pure_funding_candidates": detail.get("rewrite_objective", {}).get(
                        "max_pure_funding_candidates",
                        "",
                    ),
                }
            )
        for proposal in proposals:
            if proposal in seen_formulas:
                continue
            seen_formulas.add(proposal)
            metadata = generator.proposal_metadata.get(proposal, {})
            candidate_rows.append(
                {
                    "factor_id": stable_factor_id(proposal),
                    "formula": proposal,
                    "description": generator.descriptions.get(proposal, ""),
                    "passed": None,
                    "source": "candidate_selector_rewrite",
                    "rewrite_generation_source": metadata.get("generation_source", ""),
                    "parent_factor_id": target.get("factor_id", ""),
                    "parent_formula": formula,
                    "parent_selector_verdict": target.get("selector_verdict", ""),
                    "parent_rewrite_focus": target.get("rewrite_focus", ""),
                    "parent_universe_pass_rate": target.get("universe_pass_rate", ""),
                    "parent_universe_mean_sharpe": target.get("universe_mean_sharpe", ""),
                    "parent_failed_assets": target.get("failed_assets", ""),
                    "parent_matched_failed_subtrees": "|".join(target_failed_subtrees),
                    "selector_forbidden_subtree_count": len(effective_forbidden),
                    "selector_forbidden_subtrees": "|".join(effective_forbidden[:10]),
                    "known_selector_formula_count": len(known_selector_formulas),
                    "rewrite_failed_gates": ",".join(failed_gates),
                    "parent_formula_family": detail.get("rewrite_objective", {}).get("parent_formula_family", ""),
                    "max_pure_funding_candidates": detail.get("rewrite_objective", {}).get(
                        "max_pure_funding_candidates",
                        "",
                    ),
                    "hypothesis": metadata.get("hypothesis", ""),
                    "expected_edge": metadata.get("expected_edge", ""),
                    "expected_failure_mode": metadata.get("expected_failure_mode", ""),
                    "rewrite_plan_if_killed": metadata.get("rewrite_plan_if_killed", ""),
                }
            )

    candidates = pd.DataFrame(candidate_rows)
    events = pd.DataFrame(event_rows)
    manifest = {
        "artifact_type": "quantumrandy_selector_rewrite_candidates",
        "schema_version": 1,
        "safety": {
            "research_only": True,
            "not_runtime_publish_payload": True,
            "does_not_update_runtime": True,
            "does_not_auto_admit_factors": True,
        },
        "policy": asdict(policy),
        "target_count": min(len(rewrite_targets), policy.max_targets),
        "candidate_count": len(candidates),
        "event_count": len(events),
        "event_source_counts": _event_source_counts(events),
        "candidate_generation_source_counts": _value_counts(candidates, "rewrite_generation_source"),
        "allow_local_fallback": policy.allow_local_fallback,
        "llm_error_count": _llm_error_count(events),
        "llm_error_summary": _llm_error_summary(events),
        "llm_rewrite_accepted": _accepted_by_source(events, {"llm_rewrite"}),
        "fallback_rewrite_accepted": _accepted_by_source(
            events,
            {"rewrite_fallback", "local_rewrite", "local", "fallback"},
        ),
        "known_selector_formula_count": len(known_selector_formulas),
        "known_selector_formulas": known_selector_formulas[:20],
        "selector_forbidden_subtree_count": len(selector_forbidden_subtrees),
        "selector_forbidden_subtrees": selector_forbidden_subtrees[: policy.max_selector_forbidden_subtrees],
        "usage": [
            "Evaluate these candidates with universe and portfolio-universe research scripts before admission review.",
            "Do not publish these candidates to runtime without separate evidence and manual approval.",
        ],
    }
    return candidates, events, manifest


def write_selector_rewrite_report(
    rewrite_targets: list[dict[str, Any]],
    generator: FormulaGenerator,
    out_dir: str | Path,
    *,
    policy: CandidateRewritePolicy | None = None,
    forbidden: list[str] | None = None,
    selector_forbidden_subtrees: list[str] | None = None,
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    candidates, events, manifest = build_selector_rewrite_candidates(
        rewrite_targets,
        generator,
        policy=policy,
        forbidden=forbidden,
        selector_forbidden_subtrees=selector_forbidden_subtrees,
    )
    candidate_rows = candidates.to_dict(orient="records") if not candidates.empty else []
    safe_write_json(out / "selector_rewrite_candidates.json", candidate_rows, out / "events.jsonl")
    safe_write_csv(out / "selector_rewrite_candidates.csv", candidates, out / "events.jsonl")
    safe_write_csv(out / "selector_rewrite_events.csv", events, out / "events.jsonl")
    safe_write_json(out / "selector_rewrite_manifest.json", manifest, out / "events.jsonl")
    safe_write_text(
        out / "SELECTOR_REWRITE_REPORT.md",
        render_selector_rewrite_report(manifest, candidates),
        out / "events.jsonl",
    )
    return manifest


def render_selector_rewrite_report(manifest: dict[str, Any], candidates: pd.DataFrame) -> str:
    lines = [
        "# QuantumRandy Selector Rewrite Candidates",
        "",
        "This is a research artifact only. It is not a runtime publish payload and does not admit factors.",
        "",
        "## Summary",
        "",
        f"- Rewrite targets: `{manifest['target_count']}`",
        f"- Candidate formulas: `{manifest['candidate_count']}`",
        f"- Known selector formulas disallowed: `{manifest.get('known_selector_formula_count', 0)}`",
        f"- Selector forbidden subtrees: `{manifest.get('selector_forbidden_subtree_count', 0)}`",
        f"- Local fallback allowed: `{manifest.get('allow_local_fallback', True)}`",
        f"- LLM rewrite accepted: `{manifest.get('llm_rewrite_accepted', 0)}`",
        f"- Fallback/local accepted: `{manifest.get('fallback_rewrite_accepted', 0)}`",
    ]
    source_counts = manifest.get("candidate_generation_source_counts") or {}
    if source_counts:
        lines.append(f"- Candidate source mix: `{_format_counts(source_counts)}`")
    error_summary = manifest.get("llm_error_summary") or []
    if error_summary:
        lines.extend(
            [
                f"- LLM rewrite errors: `{manifest.get('llm_error_count', len(error_summary))}`",
                "",
                "## LLM Error Summary",
                "",
            ]
        )
        for error in error_summary[:5]:
            lines.append(f"- {error}")
    lines.extend(["", "## Candidates", ""])
    if candidates.empty:
        lines.append("No candidates were generated.")
    else:
        lines.append("| Factor | Parent | Focus | Formula |")
        lines.append("|---|---|---|---|")
        for row in candidates.head(30).to_dict(orient="records"):
            lines.append(
                "| "
                f"`{row['factor_id']}` | `{row['parent_factor_id']}` | `{row['parent_rewrite_focus']}` | "
                f"`{row['formula']}` |"
            )
    lines.extend(
        [
            "",
            "## Files",
            "",
            "- `selector_rewrite_candidates.json`: leaderboard-style candidate rows for downstream research "
            "evaluation.",
            "- `selector_rewrite_candidates.csv`: tabular candidate rows with parent evidence.",
            "- `selector_rewrite_events.csv`: LLM or local generation audit events.",
            "- `selector_rewrite_manifest.json`: machine-readable safety and run metadata.",
        ]
    )
    return "\n".join(lines) + "\n"


def load_json_rows(path: str | Path) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Expected JSON list: {path}")
    return [item for item in payload if isinstance(item, dict) and item.get("formula")]


def _event_source_counts(events: pd.DataFrame) -> dict[str, int]:
    if events.empty or "source" not in events.columns:
        return {}
    return {str(key): int(value) for key, value in events["source"].fillna("").value_counts().to_dict().items()}


def _accepted_by_source(events: pd.DataFrame, sources: set[str]) -> int:
    if events.empty or "source" not in events.columns or "accepted" not in events.columns:
        return 0
    total = 0
    for row in events.fillna("").to_dict(orient="records"):
        if str(row.get("source", "")) not in sources:
            continue
        try:
            total += int(float(row.get("accepted", 0) or 0))
        except (TypeError, ValueError):
            continue
    return total


def _value_counts(frame: pd.DataFrame, column: str) -> dict[str, int]:
    if frame.empty or column not in frame.columns:
        return {}
    return {str(key): int(value) for key, value in frame[column].fillna("").value_counts().to_dict().items() if str(key)}


def _format_counts(counts: dict[str, int]) -> str:
    return "|".join(f"{key}:{value}" for key, value in counts.items()) if counts else "none"


def _llm_error_count(events: pd.DataFrame) -> int:
    if events.empty or "source" not in events.columns or "error" not in events.columns:
        return 0
    count = 0
    for row in events.fillna("").to_dict(orient="records"):
        if str(row.get("source", "")) != "rewrite_fallback":
            continue
        if str(row.get("error", "")).strip():
            count += 1
    return count


def _llm_error_summary(events: pd.DataFrame, *, max_items: int = 5, max_chars: int = 280) -> list[str]:
    if events.empty or "source" not in events.columns or "error" not in events.columns:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for row in events.fillna("").to_dict(orient="records"):
        if str(row.get("source", "")) != "rewrite_fallback":
            continue
        error = " ".join(str(row.get("error", "")).split())
        if not error:
            continue
        if len(error) > max_chars:
            error = error[: max_chars - 3].rstrip() + "..."
        if error in seen:
            continue
        seen.add(error)
        out.append(error)
        if len(out) >= max_items:
            break
    return out


def _failed_gates_for_focus(rewrite_focus: str) -> list[str]:
    if rewrite_focus == "avoid_repeated_failed_subtrees":
        return ["cross_asset_robustness", "homogeneity"]
    if rewrite_focus == "improve_cross_asset_robustness":
        return ["cross_asset_profitability", "cross_asset_robustness", "lifetime"]
    if rewrite_focus == "improve_cross_asset_profitability":
        return ["cross_asset_profitability", "predictive_power"]
    if rewrite_focus == "abandon_or_change_economic_family":
        return ["cross_asset_robustness", "predictive_power", "lifetime"]
    return ["predictive_power"]


def _target_failure_detail(
    target: dict[str, Any],
    *,
    disallow_pure_funding_for_non_funding_parent: bool = True,
) -> dict[str, Any]:
    failed_assets = target.get("failed_assets", "")
    formula = str(target.get("formula", ""))
    parent_family = _formula_family(formula)
    disallow_pure_funding = (
        disallow_pure_funding_for_non_funding_parent
        and parent_family != "pure_funding"
    )
    return {
        "passed": False,
        "selector_verdict": target.get("selector_verdict", ""),
        "rewrite_focus": target.get("rewrite_focus", ""),
        "universe": {
            "pass_rate": target.get("universe_pass_rate", ""),
            "mean_sharpe": target.get("universe_mean_sharpe", ""),
            "median_rank_ic": target.get("universe_median_rank_ic", ""),
            "failed_assets": failed_assets,
        },
        "rewrite_objective": {
            "target_pass_rate_delta": "> 0",
            "target_mean_sharpe_delta": ">= 0",
            "parent_formula_family": parent_family,
            "max_pure_funding_candidates": 0 if disallow_pure_funding else 1,
            "formula_family_constraint": (
                "Pure funding-rate-only rewrites are disallowed for this non-funding parent. Use funding only as an "
                "interaction with price, range, or volume, or choose a non-funding economic family."
                if disallow_pure_funding
                else "At most one pure funding-rate-only rewrite may be returned for this parent."
            ),
            "negative_repeat_memory": (
                "Recent hard-gated selector repeats showed that slow pure funding-only variants can pass LLM parsing "
                "while materially reducing five-asset mean Sharpe. Do not use slow funding carry as a generic escape "
                "from weak price, volume, or range parents."
            ),
            "profitability_gate": (
                "A rewrite is not a useful improvement if it only raises pass_rate while mean Sharpe falls versus "
                "the parent. Normalized range, volatility, and liquidity candidates must justify expected Sharpe."
            ),
            "failed_assets_instruction": (
                f"Predict and address why the parent failed on these assets: {failed_assets}."
                if failed_assets
                else "Predict which assets or regimes are most likely to fail before returning the candidate."
            ),
        },
    }


def _formula_family(formula: str) -> str:
    text = str(formula)
    has_funding = "funding_rate" in text
    has_price = any(field in text for field in ("open", "high", "low", "close"))
    has_volume = "volume" in text
    if has_funding and not has_price and not has_volume:
        return "pure_funding"
    if has_funding:
        return "funding_interaction"
    if has_volume:
        return "volume_liquidity"
    if any(field in text for field in ("high", "low")):
        return "range_volatility"
    if has_price:
        return "price"
    return "other"


def _cluster_subtrees(path: Path) -> list[str]:
    if not path.exists():
        return []
    try:
        frame = pd.read_csv(path).fillna("")
    except pd.errors.EmptyDataError:
        return []
    if "subtree" not in frame.columns:
        return []
    if {"count", "avg_universe_pass_rate", "avg_universe_mean_sharpe"}.issubset(frame.columns):
        frame = frame.sort_values(
            ["count", "avg_universe_pass_rate", "avg_universe_mean_sharpe"],
            ascending=[False, True, True],
        )
    return [str(value) for value in frame["subtree"].tolist() if str(value)]


def _matched_failed_subtrees(path: Path) -> list[str]:
    if not path.exists():
        return []
    try:
        frame = pd.read_csv(path).fillna("")
    except pd.errors.EmptyDataError:
        return []
    if "matched_failed_subtrees" not in frame.columns:
        return []
    out: list[str] = []
    for raw in frame["matched_failed_subtrees"].tolist():
        out.extend(_split_subtrees(raw))
    return out


def _split_subtrees(value: Any) -> list[str]:
    return [item.strip() for item in str(value or "").split("|") if item and item.strip()]


def _dedupe_subtrees(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def _known_selector_formulas(rewrite_targets: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for target in rewrite_targets:
        formula = str(target.get("formula", "")).strip()
        if not formula:
            continue
        try:
            canonical = validate_formula_shape(formula).canonical()
        except ValueError:
            canonical = formula
        if canonical in seen:
            continue
        seen.add(canonical)
        out.append(canonical)
    return out
