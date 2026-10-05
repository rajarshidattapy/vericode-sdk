import json
import subprocess
import sys
from typing import Any, Optional

HARNESS = r'''
import io
import json
import os
import sys
import threading


def normalize(value):
    if isinstance(value, float):
        return round(value, 9)
    if isinstance(value, (list, tuple)):
        return [normalize(item) for item in value]
    if isinstance(value, dict):
        return {str(key): normalize(item) for key, item in value.items()}
    if value is None or isinstance(value, (bool, int, str)):
        return value
    return repr(value)


def emit(output, error, exit_code, coverage):
    payload = {"output": output, "error": error, "exit_code": exit_code, "coverage": sorted(coverage)}
    sys.__stdout__.write(json.dumps(payload) + "\n")
    sys.__stdout__.flush()


def guarded(task, timeout):
    box = {}

    def target():
        try:
            box["value"] = task()
        except BaseException as exc:
            box["error"] = f"{type(exc).__name__}: {exc}"

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        box["timeout"] = True
    return box


def call(func, args, lines, trace):
    def tracer(frame, event, arg):
        if frame.f_code.co_filename != "<candidate>":
            return None
        lines.add(frame.f_lineno)
        return tracer

    if trace:
        sys.settrace(tracer)
    try:
        return func(*args)
    finally:
        sys.settrace(None)


data = json.loads(sys.stdin.read())
sys.stdout = io.StringIO()
namespace = {"__name__": "candidate"}
loaded = guarded(lambda: exec(compile(data["code"], "<candidate>", "exec"), namespace), data["timeout"])
if "timeout" in loaded:
    for _ in data["inputs"]:
        emit(None, "Timeout", None, [])
    os._exit(0)
for args in data["inputs"]:
    if "error" in loaded:
        emit(None, loaded["error"], 1, [])
        continue
    lines = set()
    box = guarded(lambda: call(namespace[data["func"]], args, lines, data["trace"]), data["timeout"])
    if "timeout" in box:
        emit(None, "Timeout", None, lines)
        os._exit(0)
    if "error" in box:
        emit(None, box["error"], 1, lines)
    else:
        emit(normalize(box["value"]), None, 0, lines)
'''


def make_result(fuzz_input: list, output: Any, error: Optional[str], exit_code: Optional[int]) -> dict:
    return {"input": fuzz_input, "output": output, "error": error, "exit_code": exit_code}


def parse_lines(inputs: list[list], stdout: str, trace: bool) -> list[dict]:
    results = []
    for fuzz_input, line in zip(inputs, stdout.splitlines()):
        try:
            payload = json.loads(line)
        except ValueError:
            break
        result = make_result(fuzz_input, payload["output"], payload["error"], payload["exit_code"])
        if trace:
            result["coverage"] = payload["coverage"]
        results.append(result)
    return results


def run_batch(code: str, func_name: str, inputs: list[list], timeout: float, trace: bool) -> list[dict]:
    request = json.dumps({"code": code, "func": func_name, "inputs": inputs, "timeout": timeout, "trace": trace})
    try:
        proc = subprocess.run(
            [sys.executable, "-I", "-c", HARNESS],
            input=request,
            capture_output=True,
            text=True,
            timeout=timeout * (len(inputs) + 1) + 5,
        )
    except subprocess.TimeoutExpired:
        return [make_result(fuzz_input, None, "Timeout", None) for fuzz_input in inputs]
    results = parse_lines(inputs, proc.stdout, trace)
    if len(results) < len(inputs) and (not results or results[-1]["error"] != "Timeout"):
        error = proc.stderr.strip() or "ProcessFailure"
        results.append(make_result(inputs[len(results)], None, error, proc.returncode))
    return results


def run_fuzz_inputs(code: str, func_name: str, inputs: list[list], timeout: float = 2.0, trace: bool = False) -> list[dict]:
    inputs = [list(fuzz_input) for fuzz_input in inputs]
    results: list[dict] = []
    while len(results) < len(inputs):
        results += run_batch(code, func_name, inputs[len(results):], timeout, trace)
    return results


def run_fuzz_input(code: str, func_name: str, fuzz_input: list, timeout: float = 2.0, trace: bool = False) -> dict:
    return run_fuzz_inputs(code, func_name, [fuzz_input], timeout, trace)[0]
