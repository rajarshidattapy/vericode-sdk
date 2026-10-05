import json
import os
import re
import urllib.request
from pathlib import Path
from typing import Callable

LLM = Callable[[str], str]

LLM_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

TEMPLATE = (
    "Write a Python function named `{func_name}` that solves the task below.\n"
    "Return only the code in a single ```python block.\n\n"
    "Task: {prompt}\n"
)


def load_env(path: str = ".env") -> None:
    file = Path(path)
    if not file.exists():
        return
    for line in file.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.partition("=")
        if sep and key.strip():
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def llm(prompt: str, temperature: float = 0.8) -> str:
    load_env()
    model = os.environ.get("LLM_MODEL", "gemini-2.5-flash")
    body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": temperature}}
    request = urllib.request.Request(
        LLM_URL.format(model=model),
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": os.environ["LLM_API_KEY"]},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        data = json.load(response)
    return "".join(part.get("text", "") for part in data["candidates"][0]["content"]["parts"])


def build_prompt(prompt: str, func_name: str) -> str:
    return TEMPLATE.format(prompt=prompt, func_name=func_name)


def extract_code(text: str) -> str:
    match = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
    return (match.group(1) if match else text).strip()


def generate_candidates(prompt: str, llm: LLM = llm, n: int = 5, func_name: str = "solution") -> list[str]:
    request = build_prompt(prompt, func_name)
    return [extract_code(llm(request)) for _ in range(n)]
