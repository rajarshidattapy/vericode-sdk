import re
from typing import Callable

LLM = Callable[[str], str]

TEMPLATE = (
    "Write a Python function named `{func_name}` that solves the task below.\n"
    "Return only the code in a single ```python block.\n\n"
    "Task: {prompt}\n"
)


def build_prompt(prompt: str, func_name: str) -> str:
    return TEMPLATE.format(prompt=prompt, func_name=func_name)


def extract_code(text: str) -> str:
    match = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
    return (match.group(1) if match else text).strip()


def generate_candidates(prompt: str, llm: LLM, n: int = 5, func_name: str = "solution") -> list[str]:
    request = build_prompt(prompt, func_name)
    return [extract_code(llm(request)) for _ in range(n)]
