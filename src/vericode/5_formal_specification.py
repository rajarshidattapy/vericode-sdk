import re
from dataclasses import dataclass, field
from importlib import import_module

natural_generation = import_module(".1_natural_generation", __package__)
LLM = natural_generation.LLM

LABELS = {"pre": "preconditions", "post": "postconditions", "inv": "invariants"}

TEMPLATE = (
    "Write a formal contract for this requirement.\n"
    "Parameters: {params}. Use `result` for the return value and `pi` for pi.\n"
    "Output one Python boolean expression per line, prefixed with `pre:`, `post:` or `inv:`.\n"
    "Output nothing else.\n\n"
    "Requirement: {requirement}\n"
)


@dataclass
class Spec:
    func_name: str
    params: list[str]
    preconditions: list[str] = field(default_factory=list)
    postconditions: list[str] = field(default_factory=list)
    invariants: list[str] = field(default_factory=list)
    requirement: str = ""


def parse_contract(text: str) -> dict[str, list[str]]:
    contract: dict[str, list[str]] = {name: [] for name in LABELS.values()}
    for line in (raw.strip() for raw in text.splitlines()):
        if not line:
            continue
        label, _, body = line.partition(":")
        if label.strip() in LABELS and body.strip():
            contract[LABELS[label.strip()]].append(body.strip())
        elif re.search(r"\bresult\b", line):
            contract["postconditions"].append(line)
        else:
            contract["preconditions"].append(line)
    return contract


def spec_from_contract(func_name: str, params: list[str], contract: str, requirement: str = "") -> Spec:
    return Spec(func_name, list(params), requirement=requirement, **parse_contract(contract))


def spec_from_requirement(requirement: str, func_name: str, params: list[str], llm: LLM = natural_generation.llm) -> Spec:
    contract = llm(TEMPLATE.format(params=", ".join(params), requirement=requirement))
    return spec_from_contract(func_name, params, contract, requirement)
