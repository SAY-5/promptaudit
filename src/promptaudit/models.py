"""Shared result models across all gates."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class Verdict(StrEnum):
    """Overall pass/fail for a gate or an audit."""

    PASS = "pass"
    FAIL = "fail"


class GateResult(BaseModel):
    """The outcome of running one gate over its inputs."""

    gate: str
    total: int = Field(ge=0)
    passed: int = Field(ge=0)
    verdict: Verdict
    # Free-form per-gate detail (e.g. failing prompt ids, category hits).
    details: dict[str, object] = Field(default_factory=dict)

    @property
    def pass_rate(self) -> float:
        """Fraction of inputs that passed, in [0, 1]. Empty input is a perfect 1.0."""
        if self.total == 0:
            return 1.0
        return self.passed / self.total
