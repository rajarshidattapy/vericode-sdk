# vericode-sdk
small SDK that runs LLM-generated code through fuzzing and formal verification to catch issues, find counterexamples, or prove it’s correct before execution..

## Install

```bash
pip install vericode-sdk
```

```python
from vericode import verify

print(verify("def f(x): return x + 1"))
```

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
