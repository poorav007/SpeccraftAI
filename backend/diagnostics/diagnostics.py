
from dataclasses import dataclass

VALID_CODES = {
    "SC-W001", "SC-W002", "SC-W003", "SC-W004",
    "SC-W005", "SC-W006", "SC-W007", "SC-W008",
    "SC-E001", "SC-E002"
}


@dataclass
class Diagnostic:
    code: str
    severity: str
    message: str
    file: str
    line: int
    hint: str

    def __post_init__(self):
        if self.code not in VALID_CODES:
            raise ValueError(f"Invalid diagnostic code: {self.code}")

        if self.severity not in {"warning", "error"}:
            raise ValueError("Severity must be warning or error")

        if self.line < 1:
            raise ValueError("Line number must be positive")

