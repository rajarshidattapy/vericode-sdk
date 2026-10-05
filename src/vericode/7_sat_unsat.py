from importlib import import_module
from typing import Any

import z3

Spec = import_module(".5_formal_specification", __package__).Spec
solve = import_module(".6_smt_solver", __package__).solve


def to_python(value: z3.ExprRef) -> Any:
    if z3.is_true(value) or z3.is_false(value):
        return z3.is_true(value)
    if z3.is_int_value(value):
        return value.as_long()
    if z3.is_rational_value(value):
        return float(value.as_fraction())
    if z3.is_algebraic_value(value):
        return float(value.approx(12).as_fraction())
    return str(value)


def counterexample(model: z3.ModelRef, symbols: dict) -> dict:
    return {name: to_python(model.eval(symbol, model_completion=True)) for name, symbol in symbols.items()}


def interpret(raw: dict) -> dict:
    if raw["status"] == z3.sat:
        return {"status": "SAT", "verified": False, "counterexample": counterexample(raw["model"], raw["symbols"])}
    if raw["status"] == z3.unsat:
        return {"status": "UNSAT", "verified": True, "counterexample": None}
    return {"status": "UNKNOWN", "verified": False, "counterexample": None}


def verify(code: str, spec: Spec, timeout_ms: int = 5000) -> dict:
    return interpret(solve(code, spec, timeout_ms))
