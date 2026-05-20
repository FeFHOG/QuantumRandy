from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from .backtest import run_formula_backtest, summarize_ledger
from .config import load_config
from .data import load_market_frame, slice_window
from .evaluator import evaluate_alpha
from .io_utils import safe_write_csv, safe_write_json, safe_write_text
from .llm import FormulaGenerator
from .mcts import AlphaMCTS


def mine_main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/btcusdt.yaml")
    ap.add_argument("--iterations", type=int, default=20)
    ap.add_argument("--window", choices=["training", "validation", "all"], default="training")
    ap.add_argument("--out", default="reports/btc_mcts")
    ap.add_argument("--use-llm", action="store_true")
    ap.add_argument("--save-every", type=int, default=1)
    args = ap.parse_args()

    cfg = load_config(args.config)
    data = load_market_frame(cfg.ohlcv_csv, cfg.funding_csv)
    if args.window == "training":
        data = slice_window(data, cfg.windows.training_start, cfg.windows.training_end)
    elif args.window == "validation":
        data = slice_window(data, cfg.windows.validation_start, cfg.windows.validation_end)

    mcts = AlphaMCTS(
        data=data,
        costs=cfg.costs,
        execution=cfg.execution,
        bar_hours=cfg.bar_hours,
        config=cfg.mcts,
        generator=FormulaGenerator(
            use_llm=args.use_llm,
            max_formula_depth=cfg.mcts.max_formula_depth,
            max_formula_operators=cfg.mcts.max_formula_operators,
            llm_config=cfg.llm,
        ),
    )
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    alphas = []
    print(f"Starting mining: iterations={args.iterations}, use_llm={args.use_llm}, out={out}", flush=True)
    for i in range(args.iterations):
        alphas = mcts.run(1)
        if (i + 1) % max(args.save_every, 1) == 0 or i + 1 == args.iterations:
            _save_interim(out, cfg, mcts, i + 1)
        best = alphas[0] if alphas else None
        if best:
            print(
                f"[{i + 1}/{args.iterations}] best score={best.score:.4f} "
                f"rank_ic={best.metrics.get('rank_ic', 0.0):.4f} sharpe={best.metrics['sharpe']:.2f} {best.formula}",
                flush=True,
            )
        else:
            print(f"[{i + 1}/{args.iterations}] no alpha yet", flush=True)
    validation_rows = []
    if args.window in {"training", "all"} and cfg.windows.validation_start and cfg.windows.validation_end:
        validation = slice_window(
            load_market_frame(cfg.ohlcv_csv, cfg.funding_csv),
            cfg.windows.validation_start,
            cfg.windows.validation_end,
        )
        for alpha in alphas[:20]:
            result = evaluate_alpha(
                alpha.formula,
                validation,
                cfg.costs,
                cfg.execution,
                cfg.bar_hours,
                description=alpha.description,
                complexity_penalty=cfg.mcts.complexity_penalty,
            )
            validation_rows.append(
                {
                    "formula": result.formula,
                    "train_score": alpha.score,
                    "validation_score": result.score,
                    **{f"validation_{k}": v for k, v in result.dimensions.items()},
                    **{f"validation_{k}": v for k, v in result.metrics.items()},
                }
            )
        safe_write_csv(out / "validation_alphas.csv", pd.DataFrame(validation_rows), out / "events.jsonl")
        if alphas:
            train_ledger = run_formula_backtest(data, alphas[0].formula, cfg.costs, cfg.execution)
            validation_ledger = run_formula_backtest(validation, alphas[0].formula, cfg.costs, cfg.execution)
            safe_write_csv(out / "top_ledger_train.csv", train_ledger.reset_index(names="timestamp"), out / "events.jsonl")
            safe_write_csv(out / "top_ledger_validation.csv", validation_ledger.reset_index(names="timestamp"), out / "events.jsonl")
    _write_run_report(out, args, cfg, alphas, validation_rows, mcts.generator.events)
    print(f"Saved {len(alphas)} alphas to {out}")
    deepseek_events = [e for e in mcts.generator.events if e["source"] == "deepseek"]
    fallback_events = [e for e in mcts.generator.events if e["source"] == "fallback"]
    print(f"DeepSeek accepted batches: {len(deepseek_events)}; fallback batches: {len(fallback_events)}")
    if fallback_events:
        print(f"Last fallback reason: {fallback_events[-1]['error']}")
    for alpha in alphas[:5]:
        print(f"{alpha.score:.4f} ic={alpha.metrics['ic']:.4f} sharpe={alpha.metrics['sharpe']:.2f} {alpha.formula}")


def _save_interim(out: Path, cfg: object, mcts: AlphaMCTS, iteration: int) -> None:
    mcts.save(out)
    cfg_dict = _json_safe(asdict(cfg))
    safe_write_json(out / "config.json", cfg_dict, out / "events.jsonl")
    safe_write_json(out / "llm_events.json", mcts.generator.events, out / "events.jsonl")
    safe_write_json(out / "progress.json", {"iterations_done": iteration}, out / "events.jsonl")


def _json_safe(obj: object) -> object:
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, Path):
        return str(obj)
    return obj


def eval_formula_main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/btcusdt.yaml")
    ap.add_argument("--formula", required=True)
    ap.add_argument("--window", choices=["training", "validation", "all"], default="training")
    args = ap.parse_args()

    cfg = load_config(args.config)
    data = load_market_frame(cfg.ohlcv_csv, cfg.funding_csv)
    if args.window == "training":
        data = slice_window(data, cfg.windows.training_start, cfg.windows.training_end)
    elif args.window == "validation":
        data = slice_window(data, cfg.windows.validation_start, cfg.windows.validation_end)

    result = evaluate_alpha(args.formula, data, cfg.costs, cfg.execution, cfg.bar_hours)
    ledger = run_formula_backtest(data, result.formula, cfg.costs, cfg.execution)
    print(json.dumps({"formula": result.formula, "score": result.score, **result.dimensions, **result.metrics}, indent=2))
    print(json.dumps(summarize_ledger(ledger, cfg.bar_hours), indent=2))


def _write_run_report(out: Path, args: argparse.Namespace, cfg: object, alphas: list, validation_rows: list[dict], events: list[dict]) -> None:
    deepseek_events = [e for e in events if e["source"] == "deepseek"]
    fallback_events = [e for e in events if e["source"] == "fallback"]
    local_events = [e for e in events if e["source"] == "local"]
    lines = [
        "# QuantumRandy Run Report",
        "",
        "## Run",
        "",
        f"- Symbol: `{cfg.symbol}`",
        f"- Window: `{args.window}`",
        f"- Iterations: `{args.iterations}`",
        f"- Use LLM: `{args.use_llm}`",
        f"- Output: `{out}`",
        "",
        "## LLM Status",
        "",
        f"- DeepSeek accepted batches: `{len(deepseek_events)}`",
        f"- Fallback batches: `{len(fallback_events)}`",
        f"- Local proposal batches: `{len(local_events)}`",
    ]
    if fallback_events:
        lines.append(f"- Last fallback reason: `{fallback_events[-1]['error']}`")
    lines.extend(["", "## Top Training Alphas", ""])
    if alphas:
        lines.append("| Rank | Score | IC | Sharpe | CAGR | Max DD | Formula |")
        lines.append("|---:|---:|---:|---:|---:|---:|---|")
        for rank, alpha in enumerate(alphas[:10], start=1):
            lines.append(
                "| "
                f"{rank} | {alpha.score:.4f} | {alpha.metrics['ic']:.4f} | {alpha.metrics['sharpe']:.2f} | "
                f"{alpha.metrics['cagr']:.4f} | {alpha.metrics['max_dd']:.4f} | `{alpha.formula}` |"
            )
    else:
        lines.append("No alpha found.")
    if validation_rows:
        lines.extend(["", "## Validation Check", ""])
        lines.append("| Rank | Train Score | Validation Score | Validation IC | Validation Sharpe | Formula |")
        lines.append("|---:|---:|---:|---:|---:|---|")
        for rank, row in enumerate(validation_rows[:10], start=1):
            lines.append(
                "| "
                f"{rank} | {row['train_score']:.4f} | {row['validation_score']:.4f} | "
                f"{row['validation_ic']:.4f} | {row['validation_sharpe']:.2f} | `{row['formula']}` |"
            )
    lines.extend(
        [
            "",
            "## Files",
            "",
            "- `alphas.csv`: training alpha ranking.",
            "- `validation_alphas.csv`: validation metrics for top training alphas.",
            "- `top_ledger_train.csv`: train ledger for best training alpha.",
            "- `top_ledger_validation.csv`: validation ledger for best training alpha.",
            "- `llm_events.json`: DeepSeek/local proposal events and fallback reasons.",
            "- `tree.json`: MCTS tree.",
        ]
    )
    safe_write_text(out / "RUN_REPORT.md", "\n".join(lines) + "\n", out / "events.jsonl")
