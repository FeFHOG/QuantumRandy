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
from .io_utils import append_jsonl, safe_write_csv, safe_write_json
from .lab import row_from_alpha, run_brutal_filter
from .llm import FormulaGenerator
from .mcts import AlphaMCTS


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

    def start(self, hours: float = 24.0, use_llm: bool = True) -> dict:
        with self.lock:
            if self.thread and self.thread.is_alive():
                return self.snapshot()
            self.state = ResearchState(
                status="running",
                started_at=_now(),
                updated_at=_now(),
                target_seconds=hours * 3600.0,
                use_llm=use_llm,
                output_dir=str(self.output_dir),
                message="Research started.",
            )
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self._write_state_locked()
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()
            return self.snapshot()

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
                    self.state.message = "Running four-gate brutal filter and AutoQuant-style audit."
                    self.state.updated_at = _now()
                    self._write_state_locked()
                t0 = time.time()
                self._audit_new_alphas()
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
            _os.environ["DEEPSEEK_TIMEOUT_SECONDS"] = "120"
            _os.environ["DEEPSEEK_MAX_RETRIES"] = "1"
        generator = FormulaGenerator(
            use_llm=self.state.use_llm,
            max_formula_depth=cfg.mcts.max_formula_depth,
            max_formula_operators=cfg.mcts.max_formula_operators,
            prompt_config=cfg.prompt,
        )
        self.cfg = cfg
        self.train_data = train
        self.validation_data = validation
        self.mcts = AlphaMCTS(train, cfg.costs, cfg.execution, cfg.bar_hours, cfg.mcts, generator)
        with self.lock:
            self.state.phase = "initializing"
            self.state.message = "Initializing seed factors and first audit."
            self.state.updated_at = _now()
            self._write_state_locked()
        self.mcts.initialize()
        self._audit_new_alphas()
        with self.lock:
            self.state.symbol = cfg.symbol
            self.state.candidate_count = len(self.mcts.zoo)
            self.state.updated_at = _now()
            best = self._best_alpha()
            if best:
                self.state.best_formula = best.get("formula")
                self.state.best_score = best.get("brutal_score", best.get("mcts_score"))
            self.state.phase = "running"
            self.state.message = "Seed factors initialized. Research loop is running."
            self._save_outputs_locked()

    def _audit_new_alphas(self) -> None:
        assert self.mcts is not None and self.cfg is not None and self.train_data is not None and self.validation_data is not None
        from .lab import FilterThresholds
        thresholds = FilterThresholds.from_config(self.cfg.filter)
        accepted = [formula for formula, item in self.brutal_results.items() if item.get("passed")]
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
        with self.lock:
            self.state.accepted_count = len(accepted)

    def _leaderboard_rows(self) -> list[dict]:
        if not self.mcts:
            return []
        rows = []
        for alpha in self.mcts.zoo:
            rows.append(row_from_alpha(alpha, self.brutal_results.get(alpha.formula)))
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
            killed = [f for f, r in self.brutal_results.items() if not r.get("passed")]
            for formula in killed:
                self.brutal_results.pop(formula, None)
                if self.mcts:
                    self.mcts.zoo = [a for a in self.mcts.zoo if a.formula not in killed]
                    self.mcts.nodes = [n for n in self.mcts.nodes if n.formula not in killed]
            self.state.message = f"Purged {len(killed)} killed factors."
            self._write_state_locked()
            self._save_outputs_locked()
            _log(f"Purged {len(killed)} killed factors from zoo", C_YELLOW)
            return self.snapshot()

    def test_deepseek(self) -> dict:
        import os as _os
        from .llm import _load_env_file, call_deepseek, LLMSettings
        _load_env_file()
        api_key = _os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            return {"ok": False, "message": "DEEPSEEK_API_KEY not set in .env. Check QuantumRandy/.env has DEEPSEEK_API_KEY=sk-..."}
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
            return {"ok": True, "message": f"OK ({dur:.1f}s) — {content[:80].strip()}"}
        except Exception as exc:
            dur = time.time() - t0
            return {"ok": False, "message": f"Failed after {dur:.1f}s: {exc}"}

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
