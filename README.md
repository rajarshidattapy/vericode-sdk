# vericode-sdk
small SDK that runs LLM-generated code through fuzzing and formal verification to catch issues, find counterexamples, or prove it’s correct before execution..

## Install

```bash
pip install vericode-sdk
```

```python
from vericode import differential_analysis, generate_candidates, select_candidate, spec_from_contract, verify

candidates = generate_candidates("Return the area of a circle", llm, n=5, func_name="area")
chosen = select_candidate(differential_analysis(candidates, "area", arity=1))
spec = spec_from_contract("area", ["r"], "r >= 0\nresult == pi * r * r")

print(verify(chosen["code"], spec))
```

`llm` is any callable that takes a prompt string and returns a completion string.

## Release

**Automatic (recommended):** one-time, add a trusted publisher on PyPI
(owner `rajarshidattapy`, repo `vericode-sdk`, workflow `publish.yml`, environment `pypi`).
Then bump `version` in `pyproject.toml` + `src/vericode/__init__.py`, tag, and publish a GitHub release.

**Manual:**

```bash
pip install -e ".[dev]"
pytest
python -m build
twine upload dist/*   # username: __token__, password: your PyPI API token
```
