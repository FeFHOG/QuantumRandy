from __future__ import annotations

import json
import shutil
import sys
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .backtest import run_formula_backtest
from .config import ProjectConfig, load_config
from .data import load_market_frame, slice_window
from .evaluator import AlphaResult
from .fsa import frequent_subtrees
from .io_utils import append_jsonl, safe_write_csv, safe_write_json
from .lab import kill_reasons, row_from_alpha, run_brutal_filter
from .llm import FormulaGenerator
from .mcts import AlphaMCTS
from .pareto import build_pareto_archive


@dataclass
class ResearchState:
    status: str = "idle"
    symbol: str = "BTCUSDT"
    started_at: str | None = None
    updated_at: str | None = None
    elapsed_seconds: float = 0.0
    target_seconds: float = 24 * 3600.0
    iterations_done: int = 0
    use_llm: bool = True
    graceful_stop_requested: bool = False
    emergency_stop_requested: bool = False
    message: str = "Ready."
    phase: str = "idle"
    output_dir: str = "reports/research_live"
    best_formula: str | None = None
    best_score: float | None = None
    accepted_count: int = 0
    candidate_count: int = 0
    llm_wait_started_at: str | None = None
    last_llm_status: str = ""


class ResearchSession:
    def __init__(self, config_path: str | Path, output_dir: str | Path = "reports/research_live") -> None:
        self.root = Path(__file__).resolve().parents[1]
        self.config_path = Path(config_path)
        self.output_dir = Path(output_dir)
        if not self.output_dir.is_absolute():
            self.output_dir = self.root / self.output_dir
        self.state = ResearchState(output_dir=str(self.output_dir))
        self.lock = threading.RLock()
        self.thread: threading.Thread | None = None
        self.mcts: AlphaMCTS | None = None
        self.cfg: ProjectConfig | None = None
        self.train_data: pd.DataFrame | None = None
        self.validation_data: pd.DataFrame | None = None
        self.brutal_results: dict[str, dict] = {}
        self.rewrite_attempted: set[str] = set()

    def start(self, hours: float = 24.0, use_llm: bool = True) -> dict:
        with self.lock:
            if self.thread and self.thread.is_alive():
                return self.snapshot()
            # Preserve previous state if resuming
            prev_leaderboard = self.output_dir / "leaderboard.json"
            prev_state = self.output_dir / "state.json"
            prev_iter = 0
            if prev_leaderboard.exists():
                try:
                    prev = json.loads(prev_leaderboard.read_text(encoding="utf-8"))
                    prev_iter = max(p.get("iterations_done", 0) for p in [self._load_prev_state(), {"iterations_done": 0}])
                except Exception:
                    prev_iter = 0
            self.state = ResearchState(
                status="running",
                started_at=_now(),
                updated_at=_now(),
                iterations_done=prev_iter,
                target_seconds=hours * 3600.0,
                use_llm=use_llm,
                output_dir=str(self.output_dir),
                message="Resuming from previous session." if prev_iter > 0 else "Research started.",
            )
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self._write_state_locked()
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()
            return self.snapshot()

    def _load_prev_state(self) -> dict:
        path = self.output_dir / "state.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {}

    def request_stop(self) -> dict:
        with self.lock:
            self.state.graceful_stop_requested = True
            self.state.message = "Graceful stop requested. The current iteration will finish and save."
            self._write_stop_file("STOP_REQUESTED")
            self._write_state_locked()
            return self.snapshot()

    def emergency_stop(self) -> dict:
        with self.lock:
            self.state.emergency_stop_requested = True
            self.state.graceful_stop_requested = True
            self.state.message = "Emergency stop requested. Saving immediately after current blocking call returns."
            self._write_stop_file("EMERGENCY_STOP")
            self._write_state_locked()
            return self.snapshot()

    def save_now(self) -> dict:
        with self.lock:
            self._save_outputs_locked()
            backup_dir = self._backup_locked()
            self.state.message = f"Saved and backed up to {backup_dir.name}."
            self._write_state_locked()
            return self.snapshot()

    def snapshot(self) -> dict:
        with self.lock:
            if self.thread and not self.thread.is_alive() and self.state.status == "running":
                self.state.status = "stopped"
                self.state.phase = "stopped"
                self.state.message = "Worker is no longer alive. Last saved state is shown."
                self._write_state_locked()
            return asdict(self.state)

    def factors(self) -> list[dict[str, Any]]:
        path = self.output_dir / "leaderboard.json"
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    def _run_loop(self) -> None:
        start = time.time()
        try:
            self._initialize()
            while True:
                with self.lock:
                    should_stop = self.state.graceful_stop_requested or self.state.emergency_stop_requested
                    elapsed = time.time() - start
                    time_done = elapsed >= self.state.target_seconds
                if should_stop or time_done:
                    break
                assert self.mcts is not None
                with self.lock:
                    iter_no = self.state.iterations_done + 1
                    use_llm = self.state.use_llm
                    self.state.phase = "llm_or_local_proposal"
                    if use_llm:
                        self.state.message = f"Calling DeepSeek API (connect 15s, read 120s, 2 attempts)..."
                    else:
                        self.state.message = "Generating local template formulas..."
                    self.state.llm_wait_started_at = _now()
                    self.state.last_llm_status = "calling" if use_llm else "local"
                    self.state.updated_at = _now()
                    self._write_state_locked()
                t0 = time.time()
                prev_event_count = len(self.mcts.generator.events)
                self.mcts.run(1)
                proposal_dur = time.time() - t0
                src = "local"
                llm_status = "local"
                for evt in self.mcts.generator.events[prev_event_count:]:
                    src = evt.get("source", src)
                    acc = evt.get("accepted", 0)
                    req = evt.get("requested", 0)
                    snippet = evt.get("llm_response_snippet", "")
                    dur = evt.get("llm_duration_s", 0)
                    err = evt.get("error", "")
                    if src == "deepseek":
                        llm_status = f"ok ({acc}/{req} accepted, {dur}s)"
                        _log(f"[iter {iter_no}] DeepSeek: {acc}/{req} accepted in {dur}s | {snippet[:120]}", C_GREEN)
                    elif src == "fallback":
                        err_detail = evt.get("error", "")
                        err_snippet = evt.get("llm_response_snippet", "")
                        llm_status = f"fallback ({dur}s): {err_detail[:80]}"
                        _log(f"[iter {iter_no}] DeepSeek FAIL ({dur}s): {err_detail[:200]}", C_RED)
                        if err_snippet:
                            _log(f"[iter {iter_no}] Detail: {err_snippet[:250]}", C_YELLOW)
                    elif src == "validator":
                        rejected = evt.get("rejected", [])
                        if rejected:
                            reasons = "; ".join(f"{r['formula'][:50]}->{r['reason']}" for r in rejected[:3])
                            _log(f"[iter {iter_no}] DS rejected {len(rejected)}: {reasons}", C_YELLOW)
                with self.lock:
                    self.state.last_llm_status = llm_status
                    self.state.llm_wait_started_at = None
                _log(f"[iter {iter_no}] proposal phase took {proposal_dur:.1f}s | zoo size: {len(self.mcts.zoo)} | src: {src}", C_CYAN)
                if use_llm and self.cfg is not None:
                    cooldown = max(0.0, self.cfg.mcts.api_cooldown_seconds - proposal_dur)
                    if cooldown > 0:
                        _log(f"[iter {iter_no}] cooldown {cooldown:.0f}s before next API call...", C_RESET)
                        time.sleep(cooldown)
                with self.lock:
                    self.state.phase = "brutal_filter"
                    self.state.message = "Running four-gate brutal filter and friction audit."
                    self.state.updated_at = _now()
                    self._write_state_locked()
                t0 = time.time()
                self._audit_new_alphas()
                self._auto_purge_killed()
                audit_dur = time.time() - t0
                with self.lock:
                    self.state.iterations_done += 1
                    self.state.elapsed_seconds = elapsed
                    self.state.updated_at = _now()
                    self.state.candidate_count = len(self.mcts.zoo)
                    self.state.accepted_count = sum(1 for v in self.brutal_results.values() if v.get("passed"))
                    self.state.phase = "saving"
                    best = self._best_alpha()
                    if best:
                        self.state.best_formula = best.get("formula")
                        self.state.best_score = best.get("brutal_score", best.get("mcts_score"))
                    self._save_outputs_locked()
                    _log(f"[iter {iter_no}] audit took {audit_dur:.1f}s | accepted: {self.state.accepted_count}/{self.state.candidate_count} | best: {self.state.best_formula} (score={self.state.best_score})", C_GREEN if self.state.accepted_count > 0 else C_YELLOW)
                    self.state.phase = "running"
                    self.state.message = f"Iteration {self.state.iterations_done} saved."
                    self._write_state_locked()
        except Exception as exc:
            with self.lock:
                self.state.status = "error"
                self.state.message = str(exc)
                self.state.updated_at = _now()
                self._write_state_locked()
            return
        with self.lock:
            self.state.status = "stopped" if self.state.graceful_stop_requested else "completed"
            self.state.phase = self.state.status
            self.state.elapsed_seconds = time.time() - start
            self.state.updated_at = _now()
            self._save_outputs_locked()
            backup = self._backup_locked()
            self.state.message = f"Research {self.state.status}. Final backup: {backup.name}."
            self._write_state_locked()

    def _initialize(self) -> None:
        import os as _os
        cfg = load_config(self.config_path)
        data = load_market_frame(cfg.ohlcv_csv, cfg.funding_csv)
        train = slice_window(data, cfg.windows.training_start, cfg.windows.training_end)
        validation = slice_window(data, cfg.windows.validation_start, cfg.windows.validation_end)
        if self.state.use_llm:
            # Respect .env settings if present, otherwise use faster defaults
            _os.environ.setdefault("DEEPSEEK_TIMEOUT_SECONDS", "60")
            _os.environ.setdefault("DEEPSEEK_MAX_RETRIES", "1")
        generator = FormulaGenerator(
            use_llm=self.state.use_llm,
            max_formula_depth=cfg.mcts.max_formula_depth,
            max_formula_operators=cfg.mcts.max_formula_operators,
            prompt_config=cfg.prompt,
            llm_config=cfg.llm,
        )
        self.cfg = cfg
        self.train_data = train
        self.validation_data = validation
        self.mcts = AlphaMCTS(train, cfg.costs, cfg.execution, cfg.bar_hours, cfg.mcts, generator)
        with self.lock:
            self.state.phase = "initializing"
            self.state.message = "Checking for previous session..."
            self.state.updated_at = _now()
            self._write_state_locked()

        # Check for existing zoo to resume from
        zoo_path = self.output_dir / "zoo.json"
        leaderboard_path = self.output_dir / "leaderboard.json"
        resumed = False
        if zoo_path.exists():
            try:
                saved_zoo = json.loads(zoo_path.read_text(encoding="utf-8"))
                for item in saved_zoo:
                    alpha = AlphaResult(
                        formula=item["formula"],
                        score=item.get("score", 0),
                        dimensions=item.get("dimensions", {}),
                        metrics=item.get("metrics", {}),
                        description=item.get("description", ""),
                        hypothesis=item.get("hypothesis", ""),
                        expected_edge=item.get("expected_edge", ""),
                        expected_failure_mode=item.get("expected_failure_mode", ""),
                        rewrite_plan_if_killed=item.get("rewrite_plan_if_killed", ""),
                        depth=item.get("depth", 0),
                        operators=item.get("operators", 0),
                        generated_at=item.get("generated_at", _now()),
                    )
                    self.mcts.zoo.append(alpha)
                _log(f"Resumed {len(self.mcts.zoo)} zoo entries from previous session.", C_GREEN)
                resumed = True
            except Exception as exc:
                _log(f"Failed to load zoo, starting fresh: {exc}", C_YELLOW)

        # Restore brutal_results from leaderboard
        if leaderboard_path.exists() and resumed:
            try:
                prev_lb = json.loads(leaderboard_path.read_text(encoding="utf-8"))
                for row in prev_lb:
                    formula = row.get("formula", "")
                    if "passed" in row:
                        self.brutal_results[formula] = {
                            "formula": formula,
                            "passed": row.get("passed", False),
                            "brutal_score": row.get("brutal_score", 0),
                            "gates": {
                                "predictive_power": {"pass": row.get("gate_predictive_power", False), "rank_ic": row.get("rank_ic", 0), "directional_win_rate": row.get("directional_win_rate", 0)},
                                "homogeneity": {"pass": row.get("gate_homogeneity", False), "max_corr_to_library": row.get("max_corr_to_library", 0)},
                                "friction_audit": {"pass": row.get("gate_friction_audit", False), "cost_sharpe": row.get("sharpe", 0)},
                                "lifetime": {"pass": row.get("gate_lifetime", False), "halflife_bars": row.get("halflife_bars", 0), "validation_sharpe": row.get("validation_sharpe", 0)},
                            },
                            "train": {"rank_ic": row.get("rank_ic", 0), "sharpe": row.get("sharpe", 0), "cagr": row.get("cagr", 0), "max_dd": row.get("max_dd", 0)},
                            "validation": {"sharpe": row.get("validation_sharpe", 0), "rank_ic": row.get("validation_rank_ic", 0)},
                        }
                _log(f"Restored {len(self.brutal_results)} brutal filter results.", C_GREEN)
            except Exception as exc:
                _log(f"Failed to load brutal results: {exc}", C_YELLOW)

        # Seed if starting fresh OR if zoo is empty (all factors killed/purged)
        if not resumed or len(self.mcts.zoo) == 0:
            with self.lock:
                self.state.message = "Initializing seed factors and first audit."
                self._write_state_locked()
            self.mcts.initialize()
            self._audit_new_alphas()
        else:
            with self.lock:
                self.state.message = "Resumed from previous session."
                accepted = sum(1 for v in self.brutal_results.values() if v.get("passed"))

        with self.lock:
            self.state.symbol = cfg.symbol
            self.state.candidate_count = len(self.mcts.zoo)
            self.state.updated_at = _now()
            best = self._best_alpha()
            if best:
                self.state.best_formula = best.get("formula")
                self.state.best_score = best.get("brutal_score", best.get("mcts_score"))
            if resumed:
                accepted = sum(1 for v in self.brutal_results.values() if v.get("passed"))
                self.state.accepted_count = accepted
            self.state.phase = "running"
            self.state.message = "Resumed from previous session." if resumed else "Seed factors initialized. Research loop is running."
            self._save_outputs_locked()

    def _audit_new_alphas(self) -> None:
        assert self.mcts is not None and self.cfg is not None and self.train_data is not None and self.validation_data is not None
        from .lab import FilterThresholds
        thresholds = FilterThresholds.from_config(self.cfg.filter)
        accepted = [formula for formula, item in self.brutal_results.items() if item.get("passed")]
        rewrite_queue: list[tuple[str, list[str], dict]] = []
        for alpha in self.mcts.zoo:
            if alpha.formula in self.brutal_results:
                continue
            self.brutal_results[alpha.formula] = run_brutal_filter(
                alpha.formula,
                self.train_data,
                self.validation_data,
                self.cfg.costs,
                self.cfg.execution,
                self.cfg.bar_hours,
                accepted,
                thresholds=thresholds,
            )
            if self.brutal_results[alpha.formula]["passed"]:
                accepted.append(alpha.formula)
            else:
                reasons = kill_reasons(self.brutal_results[alpha.formula]["gates"])
                if alpha.depth > 0 and alpha.formula not in self.rewrite_attempted:
                    rewrite_queue.append((alpha.formula, reasons, self.brutal_results[alpha.formula]))

        self._rewrite_failed_alphas(rewrite_queue, accepted, thresholds)
        with self.lock:
            self.state.accepted_count = len(accepted)

    def _rewrite_failed_alphas(
        self,
        rewrite_queue: list[tuple[str, list[str], dict]],
        accepted: list[str],
        thresholds,
    ) -> None:
        assert self.mcts is not None and self.cfg is not None and self.train_data is not None and self.validation_data is not None
        if not rewrite_queue:
            return
        seed_formulas = set(self.cfg.mcts.seed_formulas)
        for formula, reasons, detail in rewrite_queue:
            if formula in seed_formulas or formula in self.rewrite_attempted:
                continue
            self.rewrite_attempted.add(formula)
            forbidden = frequent_subtrees([a.formula for a in self.mcts.zoo], self.cfg.mcts.fsa_top_k)
            forbidden = [item for item in forbidden if "funding_rate" not in item]
            candidates = self.mcts.generator.rewrite(
                formula,
                reasons,
                detail,
                max(1, min(2, self.cfg.mcts.proposal_count)),
                forbidden,
            )
            for candidate in candidates:
                if any(alpha.formula == candidate for alpha in self.mcts.zoo):
                    continue
                try:
                    alpha = self.mcts._evaluate_one(candidate)
                except Exception:
                    continue
                self.mcts._maybe_add_to_zoo(alpha)
                if alpha.formula in self.brutal_results:
                    continue
                self.brutal_results[alpha.formula] = run_brutal_filter(
                    alpha.formula,
                    self.train_data,
                    self.validation_data,
                    self.cfg.costs,
                    self.cfg.execution,
                    self.cfg.bar_hours,
                    accepted,
                    thresholds=thresholds,
                )
                if self.brutal_results[alpha.formula]["passed"]:
                    accepted.append(alpha.formula)

    def _leaderboard_rows(self) -> list[dict]:
        if not self.mcts:
            return []
        pareto_frame, _ = build_pareto_archive(self.mcts.zoo)
        pareto_by_formula = {}
        if not pareto_frame.empty:
            pareto_by_formula = {
                str(row["formula"]): {
                    "pareto_rank": int(row.get("pareto_rank", 0)),
                    "pareto_front": bool(row.get("pareto_front", False)),
                }
                for row in pareto_frame.to_dict(orient="records")
            }
        rows = []
        for alpha in self.mcts.zoo:
            row = row_from_alpha(alpha, self.brutal_results.get(alpha.formula))
            row.update(pareto_by_formula.get(alpha.formula, {}))
            rows.append(row)
        return sorted(rows, key=lambda row: row.get("brutal_score", row.get("mcts_score", 0.0)), reverse=True)

    def _best_alpha(self) -> dict | None:
        rows = self._leaderboard_rows()
        return rows[0] if rows else None

    def _save_outputs_locked(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if self.mcts:
            self.mcts.save(self.output_dir)
            safe_write_json(self.output_dir / "llm_events.json", self.mcts.generator.events, self.output_dir / "events.jsonl")
        rows = self._leaderboard_rows()
        safe_write_json(self.output_dir / "leaderboard.json", rows, self.output_dir / "events.jsonl")
        if rows:
            safe_write_csv(self.output_dir / "leaderboard.csv", pd.DataFrame(rows), self.output_dir / "events.jsonl")
            best_formula = rows[0]["formula"]
            if self.cfg is not None and self.train_data is not None and self.validation_data is not None:
                safe_write_csv(
                    self.output_dir / "best_ledger_train.csv",
                    run_formula_backtest(self.train_data, best_formula, self.cfg.costs, self.cfg.execution).reset_index(names="timestamp"),
                    self.output_dir / "events.jsonl",
                )
                safe_write_csv(
                    self.output_dir / "best_ledger_validation.csv",
                    run_formula_backtest(self.validation_data, best_formula, self.cfg.costs, self.cfg.execution).reset_index(names="timestamp"),
                    self.output_dir / "events.jsonl",
                )
        self._write_state_locked()

    def _backup_locked(self) -> Path:
        backup_root = self.root / "backups"
        backup_root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = backup_root / f"{self.output_dir.name}_{stamp}"
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(self.output_dir, target)
        return target

    def _write_state_locked(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        safe_write_json(self.output_dir / "state.json", asdict(self.state), self.output_dir / "events.jsonl")

    def _write_stop_file(self, name: str) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / name).write_text(_now(), encoding="utf-8")

    def purge_killed(self) -> dict:
        with self.lock:
            killed_count = self._purge_killed_locked()
            self.state.message = f"Purged {killed_count} killed factors."
            self._write_state_locked()
            self._save_outputs_locked()
            _log(f"Purged {killed_count} killed factors from zoo (seeds preserved)", C_YELLOW)
            return self.snapshot()

    def _auto_purge_killed(self) -> int:
        """Auto-purge killed non-seed factors from zoo after each brutal filter pass.
        This prevents zoo bloat from making the homogeneity gate impossibly strict."""
        with self.lock:
            return self._purge_killed_locked()

    def _purge_killed_locked(self) -> int:
        seed_formulas = set(self.cfg.mcts.seed_formulas) if self.cfg else set()
        killed = [f for f, r in self.brutal_results.items() if not r.get("passed") and f not in seed_formulas]
        for formula in killed:
            self.brutal_results.pop(formula, None)
        if self.mcts:
            self.mcts.zoo = [a for a in self.mcts.zoo if a.formula not in killed]
            # Nodes use positional parent/child indexes. Keep the search tree intact;
            # removing arbitrary nodes would corrupt those indexes. The zoo is the
            # only collection used by the homogeneity gate.
        if killed:
            _log(f"Auto-purged {len(killed)} killed factors from zoo", C_YELLOW)
        return len(killed)

    def test_deepseek(self) -> dict:
        import os as _os
        from .llm import _load_env_file, call_deepseek, LLMSettings
        _load_env_file()
        api_key = _os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            result = {"ok": False, "message": "DEEPSEEK_API_KEY not set in .env. Check QuantumRandy/.env has DEEPSEEK_API_KEY=sk-..."}
            self._log_llm_event("deepseek_test", result)
            return result
        settings = LLMSettings(
            base_url=_os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            model=_os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            timeout_seconds=10,
            max_retries=0,
        )
        t0 = time.time()
        try:
            content = call_deepseek(
                messages=[
                    {"role": "user", "content": "Reply with exactly: OK"},
                ],
                settings=settings,
                temperature=0.0,
            )
            dur = time.time() - t0
            result = {"ok": True, "message": f"OK ({dur:.1f}s) — {content[:80].strip()}"}
            self._log_llm_event("deepseek_test", result)
            return result
        except Exception as exc:
            dur = time.time() - t0
            result = {"ok": False, "message": f"Failed after {dur:.1f}s: {exc}"}
            self._log_llm_event("deepseek_test", result)
            return result

    def _log_llm_event(self, source: str, detail: dict) -> None:
        if self.mcts is not None:
            self.mcts.generator.events.append({
                "source": source,
                "accepted": 0,
                "requested": 0,
                "error": detail.get("message", "") if not detail.get("ok") else "",
                "llm_response_snippet": detail.get("message", "")[:200],
                "llm_duration_s": 0,
            })

    def llm_log(self) -> list[dict[str, Any]]:
        if self.mcts is None:
            return []
        return self.mcts.generator.events[-20:]

    def log_ui_event(self, event: str, detail: dict[str, Any] | None = None) -> None:
        append_jsonl(self.output_dir / "events.jsonl", {"event": event, "detail": detail or {}})


C_RESET = "\033[0m"
C_BLUE = "\033[34m"
C_GREEN = "\033[32m"
C_YELLOW = "\033[33m"
C_RED = "\033[31m"
C_CYAN = "\033[36m"


def _log(msg: str, color: str = C_RESET) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{color}[{ts}] {msg}{C_RESET}", flush=True)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
