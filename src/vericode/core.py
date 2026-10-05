from dataclasses import dataclass, field


@dataclass
class Result:
    ok: bool
    issues: list = field(default_factory=list)


def verify(code: str) -> Result:
    """Check that `code` at least compiles. Fuzzing / formal checks go here."""
    try:
        compile(code, "<vericode>", "exec")
    except SyntaxError as e:
        return Result(ok=False, issues=[f"SyntaxError: {e.msg} (line {e.lineno})"])
    return Result(ok=True)
