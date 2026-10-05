from vericode import (
    differential_analysis,
    generate_candidates,
    run_fuzz_input,
    run_fuzz_inputs,
    select_candidate,
    spec_from_contract,
    verify,
)

GOOD = "import math\ndef area(r):\n    return math.pi * r * r"
ROUGH = "def area(r):\n    return 3.14 * r * r"
SPEC = spec_from_contract("area", ["r"], "r >= 0\nresult == pi * r * r")


def test_generate_extracts_code():
    cands = generate_candidates("circle area", lambda p: f"```python\n{GOOD}\n```", n=2, func_name="area")
    assert cands == [GOOD, GOOD]


def test_run_outcomes():
    assert run_fuzz_input(GOOD, "area", [1])["exit_code"] == 0
    assert run_fuzz_input("def area(r):\n    return 1 / r", "area", [0])["error"].startswith("ZeroDivisionError")


def test_timeout_does_not_block_batch():
    code = "def f(x):\n    while x == 0:\n        pass\n    return x"
    results = run_fuzz_inputs(code, "f", [[1], [0], [2]], timeout=0.5)
    assert [r["output"] for r in results] == [1, None, 2]
    assert results[1]["error"] == "Timeout"


def test_cluster_selects_majority():
    analysis = differential_analysis([ROUGH, GOOD, GOOD], "area", inputs=[[1], [2], [3]])
    assert select_candidate(analysis)["selected"] == 1


def test_verify_sat_and_unsat():
    assert verify(GOOD, SPEC)["status"] == "UNSAT"
    result = verify(ROUGH, SPEC)
    assert result["status"] == "SAT" and result["counterexample"]["r"] >= 0
