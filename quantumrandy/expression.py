from __future__ import annotations

import ast
from dataclasses import dataclass

import numpy as np
import pandas as pd


FIELDS = {"open", "high", "low", "close", "volume", "funding_rate"}
ROLLING_OPERATORS = {"sma", "ema", "std", "zscore", "min", "max", "delta", "ret", "rank", "delay", "rsi"}
OPERATORS = {
    "add",
    "sub",
    "mul",
    "div",
    "neg",
    "abs",
    "log",
    "sqrt",
    "sign",
    "corr",
    *ROLLING_OPERATORS,
}


@dataclass(frozen=True)
class ExprNode:
    name: str
    args: tuple["ExprNode | float | int | str", ...] = ()

    def canonical(self) -> str:
        if not self.args:
            return self.name
        return f"{self.name}({','.join(_canonical_arg(arg) for arg in self.args)})"

    def abstract(self) -> str:
        if self.name in ROLLING_OPERATORS:
            args = tuple("n" if isinstance(arg, (int, float)) else arg for arg in self.args)
        else:
            args = self.args
        if not args:
            return self.name
        return f"{self.name}({','.join(_abstract_arg(arg) for arg in args)})"

    def depth(self) -> int:
        child_depths = [arg.depth() for arg in self.args if isinstance(arg, ExprNode)]
        return 1 + (max(child_depths) if child_depths else 0)

    def operator_count(self) -> int:
        own = 0 if self.name in FIELDS else 1
        return own + sum(arg.operator_count() for arg in self.args if isinstance(arg, ExprNode))

    def field_count(self) -> int:
        own = 1 if self.name in FIELDS else 0
        return own + sum(arg.field_count() for arg in self.args if isinstance(arg, ExprNode))


def _canonical_arg(arg: ExprNode | float | int | str) -> str:
    if isinstance(arg, ExprNode):
        return arg.canonical()
    if isinstance(arg, float) and arg.is_integer():
        return str(int(arg))
    return str(arg)


def _abstract_arg(arg: ExprNode | float | int | str) -> str:
    if isinstance(arg, ExprNode):
        return arg.abstract()
    if isinstance(arg, (int, float)):
        return "n"
    return str(arg)


def parse_formula(formula: str) -> ExprNode:
    tree = ast.parse(formula.strip(), mode="eval")
    return _convert(tree.body)


def formula_depth(formula: str) -> int:
    return parse_formula(formula).depth()


def formula_complexity(formula: str) -> int:
    node = parse_formula(formula)
    return node.operator_count()


def validate_formula_shape(formula: str, max_depth: int = 4, max_operators: int = 8) -> ExprNode:
    node = parse_formula(formula)
    if node.depth() > max_depth:
        raise ValueError(f"Formula depth {node.depth()} exceeds max_depth={max_depth}: {formula}")
    if node.operator_count() > max_operators:
        raise ValueError(f"Formula operators {node.operator_count()} exceeds max_operators={max_operators}: {formula}")
    return node


def _convert(node: ast.AST) -> ExprNode | int | float | str:
    if isinstance(node, ast.Name):
        if node.id not in FIELDS:
            raise ValueError(f"Unknown field: {node.id}")
        return ExprNode(node.id)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        value = _convert(node.operand)
        if not isinstance(value, (int, float)):
            raise ValueError("Unary minus is only allowed for numeric constants; use neg(x) for series")
        return -value
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        name = node.func.id.lower()
        if name not in OPERATORS:
            raise ValueError(f"Unknown operator: {name}")
        args = tuple(_convert(arg) for arg in node.args)
        return ExprNode(name, args)
    raise ValueError(f"Unsupported formula syntax: {ast.dump(node)}")


def evaluate_formula(formula: str, data: pd.DataFrame) -> pd.Series:
    node = parse_formula(formula)
    result = _eval(node, data)
    return result.replace([np.inf, -np.inf], np.nan).fillna(0.0).astype(float)


def _eval(value: ExprNode | float | int | str, data: pd.DataFrame) -> pd.Series | float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        raise ValueError(f"Unexpected raw string argument: {value}")
    if value.name in FIELDS:
        return data[value.name].astype(float)

    args = [_eval(arg, data) for arg in value.args]
    name = value.name
    if name == "add":
        return args[0] + args[1]
    if name == "sub":
        return args[0] - args[1]
    if name == "mul":
        return args[0] * args[1]
    if name == "div":
        denom = _as_series(args[1], data).replace(0, np.nan)
        return _as_series(args[0], data) / denom
    if name == "neg":
        return -_as_series(args[0], data)
    if name == "abs":
        return _as_series(args[0], data).abs()
    if name == "log":
        return np.log(_as_series(args[0], data).abs().replace(0, np.nan))
    if name == "sqrt":
        return np.sqrt(_as_series(args[0], data).clip(lower=0))
    if name == "sma":
        return _as_series(args[0], data).rolling(_window(args[1]), min_periods=_window(args[1])).mean()
    if name == "ema":
        return _as_series(args[0], data).ewm(span=_window(args[1]), adjust=False).mean()
    if name == "std":
        return _as_series(args[0], data).rolling(_window(args[1]), min_periods=_window(args[1])).std(ddof=0)
    if name == "zscore":
        x = _as_series(args[0], data)
        win = _window(args[1])
        mean = x.rolling(win, min_periods=win).mean()
        std = x.rolling(win, min_periods=win).std(ddof=0).replace(0, np.nan)
        return (x - mean) / std
    if name == "min":
        return _as_series(args[0], data).rolling(_window(args[1]), min_periods=_window(args[1])).min()
    if name == "max":
        return _as_series(args[0], data).rolling(_window(args[1]), min_periods=_window(args[1])).max()
    if name == "delta":
        return _as_series(args[0], data).diff(_window(args[1]))
    if name == "ret":
        return _as_series(args[0], data).pct_change(_window(args[1]))
    if name == "corr":
        return _as_series(args[0], data).rolling(_window(args[2]), min_periods=_window(args[2])).corr(_as_series(args[1], data))
    if name == "rank":
        win = _window(args[1])
        def _rank_pct(x):
            n = len(x)
            if n < 2:
                return 0.5
            return float((x[:-1] < x[-1]).sum()) / max(n - 1, 1)
        return _as_series(args[0], data).rolling(win, min_periods=win).apply(_rank_pct, raw=True)
    if name == "delay":
        return _as_series(args[0], data).shift(_window(args[1]))
    if name == "sign":
        s = _as_series(args[0], data)
        return pd.Series(np.where(s.values > 0, 1.0, np.where(s.values < 0, -1.0, 0.0)), index=s.index, dtype=float)
    if name == "rsi":
        x = _as_series(args[0], data).diff()
        win = _window(args[1])
        gain = x.clip(lower=0).rolling(win, min_periods=win).mean()
        loss = (-x).clip(lower=0).rolling(win, min_periods=win).mean()
        rs = gain / loss.replace(0, np.nan)
        return 100.0 - (100.0 / (1.0 + rs))
    raise ValueError(f"Unsupported operator: {name}")


def _as_series(value: pd.Series | float, data: pd.DataFrame) -> pd.Series:
    if isinstance(value, pd.Series):
        return value
    return pd.Series(float(value), index=data.index)


def _window(value: pd.Series | float) -> int:
    if isinstance(value, pd.Series):
        raise ValueError("Window argument must be a numeric constant")
    return max(int(value), 2)


def subtrees(formula: str) -> list[str]:
    node = parse_formula(formula)
    found: list[str] = []

    def walk(current: ExprNode) -> None:
        found.append(current.abstract())
        for arg in current.args:
            if isinstance(arg, ExprNode):
                walk(arg)

    walk(node)
    return found
