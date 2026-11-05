"""Phase 1 evidence re-score: what survives the fixed engine, honest statistics and an equal-budget random baseline.

Re-scores, on the configured validation window, every formula the May 2026 research_live run scored, the hand-built
Research 1.0 and v1.3 survivors, and simple benchmarks, using the shared RandysLab accounting core, scale-free positions
and warm-up from the full history. Selection statistics: Deflated Sharpe at the historical trial count, HAC t-stats of
rank IC with Benjamini-Hochberg FDR, PBO via CSCV, and results with and without labelled stress regimes.
Writes reports/phase1_rescore/. Nothing here reads the sealed holdout.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from dataclasses import replace
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from randyslab import metrics as strict_metrics
from randyslab import trial_ledger
from randyslab.accounting import build_ledger
from randyslab.config import CostProfile
from randyslab.engine import run_strict4h
from randyslab.formula_candidates import judge_factor_candidate
from randyslab.regimes import outside_regimes
from randyslab.stats import benjamini_hochberg, deflated_sharpe_ratio, pbo_cscv, rank_ic_with_hac, sharpe_ratio

from quantumrandy.backtest import run_formula_backtest
from quantumrandy.config import load_config
from quantumrandy.data import load_market_frame, slice_window
from quantumrandy.expression import evaluate_formula
from quantumrandy.lab import FilterThresholds
from quantumrandy.random_search import draw_random_formulas, gate_row
from quantumrandy.trial_backfill import canonical, scan_formulas

BARS_PER_YEAR = 365.0 * 24.0 / 4.0
VOL_CAP_FORMULA = "zscore(std(close,48),144)"
SURVIVORS = [
    {
        "name": "research_1_0_survivor",
        "candidate_id": "qr_v09d_funding_return_long_001",
        "formula": "zscore(corr(funding_rate,ret(close,42),120),72)",
        "signal_mode": "long_short",
        "volatility_cap_max": None,
    },
    {
        "name": "v1_3_primary_long_short",
        "candidate_id": "qr_v13_funding_range_norm_001",
        "formula": "neg(zscore(div(ema(funding_rate,12),div(sub(max(high,96),min(low,96)),close)),120))",
        "signal_mode": "long_short",
        "volatility_cap_max": 1.5,
    },
    {
        "name": "v1_3_paired_long_flat",
        "candidate_id": "qr_v13_funding_range_norm_001",
        "formula": "neg(zscore(div(ema(funding_rate,12),div(sub(max(high,96),min(low,96)),close)),120))",
        "signal_mode": "long_flat",
        "volatility_cap_max": 1.5,
    },
]
DOCUMENTED_SURVIVOR_COHORT_TRIALS = 250  # variant rankings of the Research 1.0 replication and v1.1-v1.3 cohorts


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default=str(ROOT / "configs" / "btcusdt.yaml"))
    ap.add_argument("--mined", default=str(ROOT / "reports" / "research_live"))
    ap.add_argument("--backfill", default=str(ROOT / "reports" / "trial_ledger" / "historical_backfill.json"))
    ap.add_argument("--randyslab", default=str(ROOT.parent / "RandysLab-STRICT4H"))
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default=str(ROOT / "reports" / "phase1_rescore"))
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cfg = load_config(args.config)
    full = load_market_frame(cfg.ohlcv_csv, cfg.funding_csv)
    train = slice_window(full, cfg.windows.training_start, cfg.windows.training_end)
    validation = slice_window(full, cfg.windows.validation_start, cfg.windows.validation_end)
    research = slice_window(full, cfg.windows.training_start, cfg.windows.validation_end)
    historical_trials = int(json.loads(Path(args.backfill).read_text(encoding="utf-8"))["lower_bound_formula_trials"])
    legacy = _legacy_verdicts(Path(args.mined) / "leaderboard.json")

    mined_formulas = sorted(scan_formulas(args.mined))
    budget = len(mined_formulas)
    random_formulas = draw_random_formulas(
        budget, args.seed, cfg.mcts.max_formula_depth, cfg.mcts.max_formula_operators
    )
    print(f"mined={budget} random={len(random_formulas)} historical trials >= {historical_trials}", flush=True)

    trial_ledger.configure_default(ROOT, context={"entry_point": "rescore_phase1", "campaign": "mined_rescore"})
    mined = _evaluate_set(mined_formulas, cfg, train, validation, research, full, "mined")
    legacy_cfg = replace(cfg, execution=replace(cfg.execution, signal_mode="legacy_tanh"))
    mined_legacy_signals = _evaluate_set(mined_formulas, legacy_cfg, train, validation, research, full, "mined_legacy")
    trial_ledger.configure_default(
        ROOT, context={"entry_point": "rescore_phase1", "campaign": "random_search_baseline"}
    )
    rand = _evaluate_set(random_formulas, cfg, train, validation, research, full, "random")

    sets = {"mined": mined, "random": rand, "mined_legacy_signals": mined_legacy_signals}
    summary = {
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(),
        "config": Path(args.config).name,
        "validation_window": [cfg.windows.validation_start, cfg.windows.validation_end],
        "costs": {"taker_bps": cfg.costs.taker_bps, "slippage_bps": cfg.costs.slippage_bps},
        "historical_formula_trials_lower_bound": historical_trials,
        "equal_budget": budget,
        "legacy_leaderboard": legacy["summary"],
        "sets": {
            name: _set_summary(result, historical_trials if name == "mined" else budget)
            for name, result in sets.items()
        },
    }
    summary["legacy_leaderboard"]["passed_under_fixed_engine"] = int(
        sum(1 for row in mined["rows"] if row["formula"] in legacy["passed"] and row["passed"])
    )

    pooled_variance = _pooled_sr_variance(mined["sr"], rand["sr"])
    survivors = _survivors(research, validation, historical_trials, pooled_variance)
    benchmarks = _benchmarks(research, validation, cfg, Path(args.randyslab))
    summary["survivors"] = survivors
    summary["benchmarks"] = benchmarks

    for name, result in sets.items():
        pd.DataFrame(result["rows"]).to_csv(out / f"{name}.csv", index=False)
    pd.DataFrame(survivors).to_csv(out / "survivors.csv", index=False)
    pd.DataFrame(benchmarks).to_csv(out / "benchmarks.csv", index=False)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=_json_default) + "\n", encoding="utf-8")
    print(json.dumps({key: summary[key] for key in ("sets", "legacy_leaderboard")}, indent=2, default=_json_default))


def _evaluate_set(formulas, cfg, train, validation, research, full, label) -> dict:
    thresholds = FilterThresholds.from_config(cfg.filter)
    accepted: list[str] = []
    rows, sr, research_returns = [], {}, {}
    started = time.time()
    for index, formula in enumerate(formulas, start=1):
        row = gate_row(formula, cfg, train, validation, full, accepted, thresholds)
        if row["passed"]:
            accepted.append(formula)
        if "error" not in row:
            try:
                ledger = run_formula_backtest(validation, formula, cfg.costs, cfg.execution, history=full)
                hac = rank_ic_with_hac(ledger["score"], ledger["r_mkt"].shift(-1))
                inside = outside_regimes(ledger.index)
                row.update(
                    validation_ic_tstat=hac["tstat"],
                    validation_ic_pvalue=_two_sided_p(hac["tstat"]),
                    validation_sharpe_ex_regimes=strict_metrics.sharpe(ledger["r_net"][inside], 0.03, BARS_PER_YEAR),
                    validation_long_share=float((ledger["exposure"] > 0).mean()),
                )
                sr[formula] = ledger["r_net"]
                research_returns[formula] = run_formula_backtest(
                    research, formula, cfg.costs, cfg.execution, history=full
                )["r_net"]
            except Exception as exc:  # a formula that cannot be evaluated is a failed trial
                row["error"] = str(exc)[:200]
        rows.append(row)
        if index % 25 == 0:
            print(f"  {label}: {index}/{len(formulas)} ({time.time() - started:.0f}s)", flush=True)
    return {"rows": rows, "sr": sr, "research_returns": research_returns}


def _set_summary(result: dict, n_trials: int) -> dict:
    rows = [row for row in result["rows"] if "error" not in row]
    val_sharpe = pd.Series([row["validation_sharpe"] for row in rows], dtype=float)
    pvalues = np.array([row.get("validation_ic_pvalue", np.nan) for row in rows], dtype=float)
    discoveries, _ = benjamini_hochberg(pvalues, q=0.10) if len(pvalues) else (np.array([]), None)
    per_period = {formula: sharpe_ratio(returns) for formula, returns in result["sr"].items()}
    variance = float(np.var(list(per_period.values()), ddof=1)) if len(per_period) > 1 else 0.0
    best = max(rows, key=lambda row: row["validation_sharpe"]) if rows else None
    dsr = deflated_sharpe_ratio(result["sr"][best["formula"]], n_trials, variance) if best else {}
    perf = pd.DataFrame(result["research_returns"])
    pbo = pbo_cscv(perf, n_partitions=16) if perf.shape[1] >= 2 else {}
    return {
        "candidates": len(result["rows"]),
        "evaluation_errors": len(result["rows"]) - len(rows),
        "passed_four_gates": int(sum(1 for row in rows if row["passed"])),
        "validation_sharpe_median": float(val_sharpe.median()) if len(val_sharpe) else None,
        "validation_sharpe_p90": float(val_sharpe.quantile(0.9)) if len(val_sharpe) else None,
        "validation_sharpe_max": float(val_sharpe.max()) if len(val_sharpe) else None,
        "share_validation_sharpe_above_0_5": float((val_sharpe > 0.5).mean()) if len(val_sharpe) else None,
        "fdr_discoveries_q10": int(np.sum(discoveries)) if len(pvalues) else 0,
        "best_formula": best["formula"] if best else None,
        "best_validation_sharpe": best["validation_sharpe"] if best else None,
        "best_validation_sharpe_ex_regimes": best.get("validation_sharpe_ex_regimes") if best else None,
        "best_dsr_n_trials": n_trials,
        "best_dsr": dsr.get("dsr"),
        "best_dsr_sr0_annualized": dsr.get("sr0", math.nan) * math.sqrt(BARS_PER_YEAR) if dsr else None,
        "pbo": pbo.get("pbo"),
        "pbo_prob_oos_loss": pbo.get("prob_oos_loss"),
    }


def _survivors(research, validation, historical_trials, pooled_variance) -> list[dict]:
    rows = []
    ohlcv = research.drop(columns=["funding_rate"])
    for spec in SURVIVORS:
        result = judge_factor_candidate(
            {"candidate_id": spec["candidate_id"], "formula": spec["formula"]},
            ohlcv=ohlcv,
            funding=research["funding_rate"],
            costs=CostProfile(taker_bps=4.0, slippage_bps=2.0),
            risk_free_rate=0.03,
            signal_threshold=0.0,
            signal_mode=spec["signal_mode"],
            max_exposure_abs=0.5,
            volatility_cap_formula=VOL_CAP_FORMULA if spec["volatility_cap_max"] else None,
            volatility_cap_max=spec["volatility_cap_max"],
        )
        returns = result["ledger"]["r_net"].loc[validation.index]
        factor = evaluate_formula(spec["formula"], research).loc[validation.index]
        hac = rank_ic_with_hac(factor, validation["close"].pct_change().shift(-1))
        row = {
            "name": spec["name"],
            "formula": spec["formula"],
            "variant": f"{spec['signal_mode']}, cap 0.5, vol cap {spec['volatility_cap_max'] or 'none'}",
            "validation_sharpe": strict_metrics.sharpe(returns, 0.03, BARS_PER_YEAR),
            "validation_sharpe_ex_regimes": strict_metrics.sharpe(
                returns[outside_regimes(returns.index)], 0.03, BARS_PER_YEAR
            ),
            "validation_cagr": strict_metrics.cagr(returns, BARS_PER_YEAR),
            "validation_max_dd": strict_metrics.max_drawdown(returns),
            "validation_ic": hac["ic"],
            "validation_ic_tstat": hac["tstat"],
        }
        for label, n in (("cohort", DOCUMENTED_SURVIVOR_COHORT_TRIALS), ("all_history", historical_trials)):
            row[f"dsr_{label}_n{n}"] = deflated_sharpe_ratio(returns, n, pooled_variance)["dsr"]
        rows.append(row)
    return rows


def _benchmarks(research, validation, cfg, randyslab_root: Path) -> list[dict]:
    close = research["close"]
    r_mkt = close.pct_change()
    vol = r_mkt.rolling(180, min_periods=90).std() * math.sqrt(BARS_PER_YEAR)
    exposures = {
        "buy_and_hold": pd.Series(1.0, index=research.index),
        "vol_target_40pct": (0.40 / vol).clip(upper=1.0).shift(1).fillna(0.0),
        "funding_carry": -np.sign(research["funding_rate"]).shift(1).fillna(0.0),
    }
    rows = []
    for name, exposure in exposures.items():
        ledger = build_ledger(close, exposure, research["funding_settled"], cfg.costs)
        rows.append(_benchmark_row(name, ledger["r_net"].loc[validation.index]))
    profile = CostProfile(taker_bps=cfg.costs.taker_bps, slippage_bps=cfg.costs.slippage_bps)
    ohlcv = research.drop(columns=["funding_rate"])
    for strategy in ("ma_cross", "bb_breakout"):
        theta = json.loads((randyslab_root / "configs" / "strategies" / f"{strategy}.json").read_text(encoding="utf-8"))
        ledger = run_strict4h(ohlcv, research["funding_rate"], theta, profile)
        rows.append(_benchmark_row(f"randyslab_{strategy}", ledger["r_net"].loc[validation.index]))
    return rows


def _benchmark_row(name: str, returns: pd.Series) -> dict:
    return {
        "name": name,
        "validation_sharpe": strict_metrics.sharpe(returns, 0.03, BARS_PER_YEAR),
        "validation_sharpe_ex_regimes": strict_metrics.sharpe(
            returns[outside_regimes(returns.index)], 0.03, BARS_PER_YEAR
        ),
        "validation_cagr": strict_metrics.cagr(returns, BARS_PER_YEAR),
        "validation_max_dd": strict_metrics.max_drawdown(returns),
        "validation_final_equity": float(strict_metrics.equity_curve(returns).iloc[-1]),
    }


def _legacy_verdicts(path: Path) -> dict:
    rows = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    passed = {canonical(row["formula"]) for row in rows if row.get("passed") and canonical(row["formula"])}
    return {"passed": passed, "summary": {"leaderboard_rows": len(rows), "legacy_passed": len(passed)}}


def _pooled_sr_variance(*returns_by_formula: dict) -> float:
    values = [sharpe_ratio(series) for group in returns_by_formula for series in group.values()]
    return float(np.var(values, ddof=1)) if len(values) > 1 else 0.0


def _two_sided_p(tstat: float) -> float:
    return float(2.0 * (1.0 - NormalDist().cdf(abs(tstat)))) if math.isfinite(tstat) else math.nan


def _json_default(value):
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return str(value)


if __name__ == "__main__":
    main()
