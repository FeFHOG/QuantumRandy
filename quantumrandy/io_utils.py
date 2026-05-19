from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def append_jsonl(path: str | Path, event: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {"ts": datetime.now().isoformat(timespec="seconds"), **event}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def safe_write_text(path: str | Path, text: str, log_path: str | Path | None = None) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(path)
        return path
    except PermissionError as exc:
        fallback = path.with_name(f"{path.stem}_{timestamp()}{path.suffix}")
        fallback.write_text(text, encoding="utf-8")
        print(f"[WARN] Permission denied: {path} -> writing to {fallback} instead ({exc})", flush=True)
        if log_path:
            append_jsonl(log_path, {"event": "permission_fallback", "path": str(path), "fallback": str(fallback), "error": str(exc)})
        return fallback
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def safe_write_json(path: str | Path, obj: Any, log_path: str | Path | None = None) -> Path:
    return safe_write_text(path, json.dumps(obj, ensure_ascii=False, indent=2), log_path)


def safe_write_csv(path: str | Path, frame: pd.DataFrame, log_path: str | Path | None = None) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        frame.to_csv(tmp, index=False)
        tmp.replace(path)
        return path
    except PermissionError as exc:
        fallback = path.with_name(f"{path.stem}_{timestamp()}{path.suffix}")
        frame.to_csv(fallback, index=False)
        print(f"[WARN] Permission denied: {path} -> writing to {fallback} instead ({exc})", flush=True)
        if log_path:
            append_jsonl(log_path, {"event": "permission_fallback", "path": str(path), "fallback": str(fallback), "error": str(exc)})
        return fallback
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
