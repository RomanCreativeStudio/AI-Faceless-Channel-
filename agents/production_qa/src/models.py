"""Production-QA-specific data model."""
from __future__ import annotations

from dataclasses import dataclass, field

VALID_VERDICTS = {"PASS", "REVISION_REQUIRED", "BLOCKED", "SYSTEM_ERROR"}


@dataclass
class CheckResult:
    area: str
    check: str
    passed: bool
    note: str = ""


@dataclass
class ProductionQAResult:
    content_id: str
    production_id: str
    qa_id: str
    filename: str
    verdict: str
    checks: list[CheckResult]
    reasons: list[str]
    aborted: bool = False
    abort_reason: str = ""
    blocked: bool = False
    blocked_reason: str = ""
    qa_path: str = ""
    production_path: str = ""

    @property
    def produced(self) -> bool:
        return bool(self.qa_path)

    @property
    def failed_checks(self) -> list[CheckResult]:
        return [c for c in self.checks if not c.passed]
