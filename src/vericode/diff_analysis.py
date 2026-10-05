import json
import random
from typing import Callable, Optional

from .run_fuzz_input import run_fuzz_inputs

Fuzzer = Callable[[str, str, list[list]], list[list]]


def random_inputs(arity: int, count: int, low: int = -100, high: int = 100, seed: int = 0) -> list[list]:
    rng = random.Random(seed)
    return [[rng.randint(low, high) for _ in range(arity)] for _ in range(count)]


def mutate(args: list, rng: random.Random) -> list:
    child = list(args)
    if not child:
        return child
    index = rng.randrange(len(child))
    value = child[index]
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        child[index] = rng.choice([value + 1, value - 1, -value, value * 2, 0])
    return child


def coverage_guided_inputs(
    code: str, func_name: str, seeds: list[list], rounds: int = 4, batch: int = 5, seed: int = 0
) -> list[list]:
    rng = random.Random(seed)
    corpus = [list(args) for args in seeds]
    seen: set[int] = set()
    for result in run_fuzz_inputs(code, func_name, corpus, trace=True):
        seen |= set(result.get("coverage", []))
    for _ in range(rounds):
        children = [mutate(rng.choice(corpus), rng) for _ in range(batch)]
        for result in run_fuzz_inputs(code, func_name, children, trace=True):
            covered = set(result.get("coverage", []))
            if not covered <= seen:
                seen |= covered
                corpus.append(result["input"])
    return corpus


def behavior(result: dict) -> tuple:
    if result["error"] is None:
        return ("ok", json.dumps(result["output"], sort_keys=True))
    return ("error", result["error"].split(":")[0])


def agreement(results: list[dict], reference: list[dict]) -> float:
    if not results:
        return 1.0
    same = sum(behavior(a) == behavior(b) for a, b in zip(results, reference))
    return same / len(results)


def differential_analysis(
    candidates: list[str],
    func_name: str,
    arity: int = 1,
    inputs: Optional[list[list]] = None,
    reference: int = 0,
    fuzzer: Fuzzer = coverage_guided_inputs,
    timeout: float = 2.0,
) -> dict:
    if inputs is None:
        inputs = fuzzer(candidates[reference], func_name, random_inputs(arity, 10))
    results = [run_fuzz_inputs(code, func_name, inputs, timeout) for code in candidates]
    return {
        "candidates": candidates,
        "func_name": func_name,
        "reference": reference,
        "inputs": inputs,
        "results": results,
        "agreement": [agreement(r, results[reference]) for r in results],
    }
