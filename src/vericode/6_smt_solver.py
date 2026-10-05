import ast
from fractions import Fraction
from importlib import import_module

import z3

Spec = import_module(".5_formal_specification", __package__).Spec

PI_BOUNDS = ("3.14159265", "3.14159266")

BINARY = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
}

COMPARE = {
    ast.Eq: lambda a, b: a == b,
    ast.NotEq: lambda a, b: a != b,
    ast.Lt: lambda a, b: a < b,
    ast.LtE: lambda a, b: a <= b,
    ast.Gt: lambda a, b: a > b,
    ast.GtE: lambda a, b: a >= b,
}


def unsupported(node: ast.AST) -> ValueError:
    return ValueError(f"Unsupported syntax for SMT encoding: {ast.unparse(node)}")


def encode_constant(value: object) -> z3.ExprRef:
    if isinstance(value, bool):
        return z3.BoolVal(value)
    if isinstance(value, (int, float)):
        number = Fraction(str(value))
        return z3.RealVal(f"{number.numerator}/{number.denominator}")
    raise ValueError(f"Unsupported constant: {value!r}")


def encode_power(node: ast.BinOp, env: dict) -> z3.ExprRef:
    exponent = node.right
    if not (isinstance(exponent, ast.Constant) and isinstance(exponent.value, int) and exponent.value >= 0):
        raise unsupported(node)
    base = to_z3(node.left, env)
    result = z3.RealVal(1)
    for _ in range(exponent.value):
        result = result * base
    return result


def encode_call(node: ast.Call, env: dict) -> z3.ExprRef:
    name = node.func.id if isinstance(node.func, ast.Name) else None
    args = [to_z3(arg, env) for arg in node.args]
    if name == "abs" and len(args) == 1:
        return z3.If(args[0] >= 0, args[0], -args[0])
    if name in ("min", "max") and len(args) >= 2:
        result = args[0]
        for arg in args[1:]:
            result = z3.If(arg < result, arg, result) if name == "min" else z3.If(arg > result, arg, result)
        return result
    raise unsupported(node)


def encode_compare(node: ast.Compare, env: dict) -> z3.ExprRef:
    terms = [to_z3(node.left, env)] + [to_z3(item, env) for item in node.comparators]
    checks = []
    for op, left, right in zip(node.ops, terms, terms[1:]):
        if type(op) not in COMPARE:
            raise unsupported(node)
        checks.append(COMPARE[type(op)](left, right))
    return z3.And(*checks) if len(checks) > 1 else checks[0]


def to_z3(node: ast.AST, env: dict) -> z3.ExprRef:
    if isinstance(node, ast.Constant):
        return encode_constant(node.value)
    if isinstance(node, ast.Name) and node.id in env:
        return env[node.id]
    if isinstance(node, ast.Attribute) and node.attr == "pi":
        return env["pi"]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
        return encode_power(node, env)
    if isinstance(node, ast.BinOp) and type(node.op) in BINARY:
        return BINARY[type(node.op)](to_z3(node.left, env), to_z3(node.right, env))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -to_z3(node.operand, env)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.UAdd):
        return to_z3(node.operand, env)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return z3.Not(to_z3(node.operand, env))
    if isinstance(node, ast.BoolOp):
        values = [to_z3(value, env) for value in node.values]
        return z3.And(*values) if isinstance(node.op, ast.And) else z3.Or(*values)
    if isinstance(node, ast.Compare):
        return encode_compare(node, env)
    if isinstance(node, ast.IfExp):
        return z3.If(to_z3(node.test, env), to_z3(node.body, env), to_z3(node.orelse, env))
    if isinstance(node, ast.Call):
        return encode_call(node, env)
    raise unsupported(node)


def encode_block(stmts: list[ast.stmt], env: dict) -> tuple[z3.ExprRef, z3.BoolRef]:
    for index, stmt in enumerate(stmts):
        if isinstance(stmt, (ast.Import, ast.ImportFrom, ast.Pass)):
            continue
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
            continue
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
            env[stmt.targets[0].id] = to_z3(stmt.value, env)
            continue
        if isinstance(stmt, ast.Return) and stmt.value is not None:
            return to_z3(stmt.value, env), z3.BoolVal(True)
        if isinstance(stmt, ast.Raise):
            return z3.RealVal(0), z3.BoolVal(False)
        if isinstance(stmt, ast.If):
            rest = stmts[index + 1:]
            then_value, then_ok = encode_block(stmt.body + rest, dict(env))
            else_value, else_ok = encode_block(stmt.orelse + rest, dict(env))
            test = to_z3(stmt.test, env)
            return z3.If(test, then_value, else_value), z3.If(test, then_ok, else_ok)
        raise unsupported(stmt)
    raise ValueError("Function does not return a value on every path")


def find_function(code: str, func_name: str) -> ast.FunctionDef:
    for node in ast.walk(ast.parse(code)):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            return node
    raise ValueError(f"Function `{func_name}` not found")


def encode_program(code: str, func_name: str, params: list[z3.ExprRef], pi: z3.ExprRef) -> tuple[z3.ExprRef, z3.BoolRef]:
    function = find_function(code, func_name)
    env = {"pi": pi}
    env.update({arg.arg: param for arg, param in zip(function.args.args, params)})
    return encode_block(function.body, env)


def encode_conditions(conditions: list[str], env: dict) -> z3.BoolRef:
    encoded = [to_z3(ast.parse(text, mode="eval").body, env) for text in conditions]
    return z3.And(*encoded) if encoded else z3.BoolVal(True)


def verification_condition(code: str, spec: Spec) -> tuple[z3.BoolRef, dict]:
    env = {name: z3.Real(name) for name in spec.params}
    env["pi"] = z3.Real("pi")
    env["result"] = z3.Real("result")
    pi_range = z3.And(env["pi"] > z3.RealVal(PI_BOUNDS[0]), env["pi"] < z3.RealVal(PI_BOUNDS[1]))
    value, returns = encode_program(code, spec.func_name, [env[p] for p in spec.params], env["pi"])
    pre = encode_conditions(spec.preconditions, env)
    post = encode_conditions(spec.postconditions + spec.invariants, env)
    violation = z3.Or(z3.Not(returns), z3.And(env["result"] == value, z3.Not(post)))
    return z3.And(pi_range, pre, violation), env


def solve(code: str, spec: Spec, timeout_ms: int = 5000) -> dict:
    condition, symbols = verification_condition(code, spec)
    solver = z3.Solver()
    solver.set("timeout", timeout_ms)
    solver.add(condition)
    status = solver.check()
    return {
        "status": status,
        "model": solver.model() if status == z3.sat else None,
        "symbols": symbols,
        "reason": solver.reason_unknown() if status == z3.unknown else None,
    }
